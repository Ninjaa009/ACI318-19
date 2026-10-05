"""Step 5 — axial force + biaxial bending by strain compatibility.
KB: chapter-22 §22.2 (assumptions), §22.4 (axial), chapter-21 Table 21.2.2 (φ)."""
from __future__ import annotations

import math

from .section import ES, EPS_CU


def phi_tied(eps_t: float, eps_ty: float) -> float:
    """Table 21.2.2, transverse reinforcement other than spirals."""
    if eps_t <= eps_ty:
        return 0.65
    if eps_t >= eps_ty + 0.003:
        return 0.90
    return 0.65 + 0.25 * (eps_t - eps_ty) / 0.003


def _clip_halfplane(poly, nx, ny, t0):
    """Part of convex polygon where p·n ≥ t0."""
    out = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        dp = p[0] * nx + p[1] * ny - t0
        dq = q[0] * nx + q[1] * ny - t0
        if dp >= 0:
            out.append(p)
        if (dp >= 0) != (dq >= 0):
            r = dp / (dp - dq)
            out.append((p[0] + r * (q[0] - p[0]), p[1] + r * (q[1] - p[1])))
    return out


def _polygon(poly):
    """Area and centroid (shoelace)."""
    if len(poly) < 3:
        return 0.0, 0.0, 0.0
    a = cx = cy = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        k = x0 * y1 - x1 * y0
        a += k
        cx += (x0 + x1) * k
        cy += (y0 + y1) * k
    if abs(a) < 1e-12:
        return 0.0, 0.0, 0.0
    return abs(a) / 2, cx / (3 * a), cy / (3 * a)


def section_forces(col, theta, c):
    """Nominal forces for a neutral axis at angle theta and depth c.
    theta = 0: compression at +y face (bending about x).  theta = π/2:
    compression at +x face (bending about y).
    Returns Pn (+compression), Mnx = ΣF·y, Mny = ΣF·x, εt (tension +), φ."""
    nx, ny = math.sin(theta), math.cos(theta)
    top = max(px * nx + py * ny for px, py in col.corners)
    a = col.b1 * c                                         # 22.2.2.4.1
    comp = _clip_halfplane(col.corners, nx, ny, top - a)
    Ac, xc, yc = _polygon(comp)
    Cc = 0.85 * col.fc * Ac                                # 22.2.2.4.1
    P, Mx, My = Cc, Cc * yc, Cc * xc
    eps_min = math.inf
    for bx, by in col.bars:
        t = bx * nx + by * ny
        eps = EPS_CU * (c - (top - t)) / c                 # + compression
        fs = max(-col.fy, min(col.fy, ES * eps))           # 20.2.2.1
        if top - t <= a:                                   # bar inside the block
            fs -= 0.85 * col.fc
        F = fs * col.Ab
        P += F
        Mx += F * by
        My += F * bx
        eps_min = min(eps_min, eps)
    eps_t = -eps_min
    return {"Pn": P, "Mnx": Mx, "Mny": My, "eps_t": eps_t,
            "phi": phi_tied(eps_t, col.eps_ty), "c": c, "theta": theta}


def _solve_c(col, theta, target, factored=True):
    """Neutral-axis depth giving (φ)Pn = target; bisection on a monotone bracket."""
    def f(c):
        r = section_forces(col, theta, c)
        return (r["phi"] if factored else 1.0) * r["Pn"] - target

    lo, hi = 1e-4 * max(col.b, col.h), 20.0 * max(col.b, col.h)
    flo, fhi = f(lo), f(hi)
    if flo > 0 or fhi < 0:
        return None
    for _ in range(90):
        mid = 0.5 * (lo + hi)
        if f(mid) >= 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def capacity(col, Pu, Mux, Muy):
    """Biaxial check at constant axial force: find the neutral-axis angle whose
    design moment vector points in the direction of (|Mux|, |Muy|).
    Valid for doubly symmetric layouts.  ratio = |Mu| / |φMn|."""
    if Pu > col.phiPn_max * (1 + 1e-9):
        return {"ok": False, "ratio": math.inf, "reason": "Pu > φPn,max (Table 22.4.2.1)"}
    if Pu < col.phiPn_min:
        return {"ok": False, "ratio": math.inf, "reason": "แรงดึงเกิน φPn ของเหล็กทั้งหมด"}
    mx, my = abs(Mux), abs(Muy)
    gamma = math.atan2(my, mx) if (mx or my) else 0.0

    def at(theta):
        c = _solve_c(col, theta, Pu)
        r = section_forces(col, theta, c)
        r["phiMnx"], r["phiMny"] = r["phi"] * r["Mnx"], r["phi"] * r["Mny"]
        return r

    if gamma <= 1e-12:
        r = at(0.0)
    elif gamma >= math.pi / 2 - 1e-12:
        r = at(math.pi / 2)
    else:
        lo, hi = 0.0, math.pi / 2
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            r = at(mid)
            if math.atan2(r["phiMny"], r["phiMnx"]) < gamma:
                lo = mid
            else:
                hi = mid
        r = at(0.5 * (lo + hi))
    cap = math.hypot(r["phiMnx"], r["phiMny"])
    mres = math.hypot(mx, my)
    return {"ok": mres <= cap * (1 + 1e-9), "ratio": mres / cap if cap > 0 else math.inf,
            "phiMcap": cap, "Mres": mres, "load_deg": math.degrees(gamma),
            "cap_deg": math.degrees(math.atan2(r["phiMny"], r["phiMnx"])),
            "phi": r["phi"], "eps_t": r["eps_t"], "c": r["c"],
            "theta_deg": math.degrees(r["theta"])}


def nominal_moment(col, axis, Pn):
    """Mn about one axis at a given nominal axial force (no φ) — for §18.3.3/18.4.3.1."""
    theta = 0.0 if axis == "x" else math.pi / 2
    c = _solve_c(col, theta, Pn, factored=False)
    if c is None:
        return 0.0
    r = section_forces(col, theta, c)
    return abs(r["Mnx"] if axis == "x" else r["Mny"])
