#!/usr/bin/env python3
"""RC rectangular tied column — design/check per ACI 318M-19, organised by the
project knowledge base (kb/chapter-XX.md). SI internal: N, mm, MPa.

Workflow steps (same numbering as SKILL.md and the report):
 0 seismic system (Ch.18)      5 axial + biaxial bending (Ch.22, 21)
 1 section / materials         6 shear (Ch.22, 10, 18)
 2 forces from analysis        7 detailing (Ch.10, 25, 18)
 3 sway / non-sway (Ch.6)      8 splices (Ch.10, 25)
 4 slenderness (Ch.6)          9 joints, floor concrete, footing (Ch.15, 16)

Scope: rectangular section, perimeter bars, rectilinear ties, non-sway,
OMF or IMF (SMF stops), normalweight concrete.

Usage:
    python3 column.py input.json            -> markdown report
    python3 column.py input.json --json     -> raw results
"""
from __future__ import annotations

import json
import math
import sys

G = 9.80665
KSC_TO_MPA = 0.0980665
ES = 200_000.0
ECU = 0.003
PHI_V = 0.75
SQRT_FC_MAX = 8.3        # 22.5.3.1 / 25.4.1.4
FY_MAX = 550.0           # Table 22.4.2.1 note: fy ≤ 550 MPa (used throughout, conservative)
FYT_SHEAR_MAX = 420.0    # Table 20.2.2.4(a)
SMALL_BAR_MAX = 19.5     # "No. 19 and smaller"; DB20 is treated as a larger bar

# Where each step lives in the knowledge base bundled with the skill
KB = {
    0: "kb/chapter-18.md §18.2, 18.3, 18.4",
    1: "kb/chapter-10.md §10.3; kb/chapter-20.md Table 20.2.2.4(a)",
    3: "kb/chapter-06.md §6.6.4.3",
    4: "kb/chapter-06.md §6.2.5, 6.6.4.4–6.6.4.5",
    5: "kb/chapter-22.md §22.4; kb/chapter-21.md Table 21.2.2",
    6: "kb/chapter-22.md §22.5; kb/chapter-10.md §10.6.2, 10.7.6.5; kb/chapter-18.md §18.3.3, 18.4.3.1",
    7: "kb/chapter-10.md §10.6.1, 10.7; kb/chapter-25.md §25.2, 25.7.2; kb/chapter-18.md §18.4.3",
    8: "kb/chapter-10.md §10.7.5; kb/chapter-25.md §25.4.2, 25.5",
    9: "kb/chapter-15.md §15.3, 15.5; kb/chapter-16.md §16.3.4",
}


def bar_area(db):
    return math.pi * db * db / 4.0


def beta1(fc):
    if fc <= 28.0:
        return 0.85
    if fc >= 55.0:
        return 0.65
    return 0.85 - 0.05 * (fc - 28.0) / 7.0


# ---------------------------------------------------------------------------
# Section
# ---------------------------------------------------------------------------

class Section:
    """x along b, y along h, origin at centroid. Bars around the perimeter:
    nx bars on each face parallel to x (top/bottom, incl. corners),
    ny bars on each face parallel to y (left/right, incl. corners)."""

    def __init__(self, b, h, fc, fy, db, nx, ny, cover, ds, cover_to="tie",
                 grade420_exception=False):
        self.b, self.h, self.fc = b, h, fc
        self.fy_in = fy
        self.fy = min(fy, FY_MAX)
        self.db, self.nx, self.ny, self.ds = db, nx, ny, ds
        self.cover_tie = cover if cover_to == "tie" else cover - ds
        self.edge = self.cover_tie + ds + db / 2.0           # face -> bar centre
        self.b1 = beta1(fc)
        self.ety = (0.002 if grade420_exception and abs(fy - 420) < 1e-6
                    else self.fy / ES)
        xs = self._row(b, nx)
        ys = self._row(h, ny)
        bars = set()
        for x in xs:
            bars.add((round(x, 6), round(h / 2 - self.edge, 6)))
            bars.add((round(x, 6), round(-h / 2 + self.edge, 6)))
        for y in ys:
            bars.add((round(b / 2 - self.edge, 6), round(y, 6)))
            bars.add((round(-b / 2 + self.edge, 6), round(y, 6)))
        self.bars = sorted(bars)
        self.Ab = bar_area(db)
        self.Ast = len(self.bars) * self.Ab
        self.Ag = b * h
        self.Po = 0.85 * fc * (self.Ag - self.Ast) + self.fy * self.Ast
        self.Pn_max = 0.80 * self.Po                           # Table 22.4.2.1(a)
        self.corners = [(-b / 2, -h / 2), (b / 2, -h / 2), (b / 2, h / 2), (-b / 2, h / 2)]

    def _row(self, L, n):
        a = -L / 2 + self.edge
        if n < 2:
            raise ValueError("ต้องมีอย่างน้อย 2 เส้นต่อด้าน")
        return [a + i * (L - 2 * self.edge) / (n - 1) for i in range(n)]


def _clip(poly, ux, uy, t0):
    """Keep part of polygon with p·u >= t0 (Sutherland-Hodgman, one edge)."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        tp = p[0] * ux + p[1] * uy - t0
        tq = q[0] * ux + q[1] * uy - t0
        if tp >= 0:
            out.append(p)
        if (tp >= 0) != (tq >= 0):
            r = tp / (tp - tq)
            out.append((p[0] + r * (q[0] - p[0]), p[1] + r * (q[1] - p[1])))
    return out


def _area_centroid(poly):
    if len(poly) < 3:
        return 0.0, 0.0, 0.0
    A = cx = cy = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        cr = x0 * y1 - x1 * y0
        A += cr
        cx += (x0 + x1) * cr
        cy += (y0 + y1) * cr
    A *= 0.5
    if abs(A) < 1e-9:
        return 0.0, 0.0, 0.0
    return abs(A), cx / (6 * A), cy / (6 * A)


def phi_tied(eps_t, ety):
    """Table 21.2.2 (other than spirals)."""
    if eps_t <= ety:
        return 0.65
    if eps_t >= ety + 0.003:
        return 0.90
    return 0.65 + 0.25 * (eps_t - ety) / 0.003


def point(sec, beta, c):
    """Nominal point. beta = angle of compression direction from +y towards +x
    (beta = 0 -> bending about x, top in compression). Returns dict with
    Pn (+compression), Mnx = ΣF·y, Mny = ΣF·x, eps_t, phi."""
    ux, uy = math.sin(beta), math.cos(beta)
    tmax = max(px * ux + py * uy for px, py in sec.corners)
    tna = tmax - c
    a = sec.b1 * c
    poly = _clip(sec.corners, ux, uy, tmax - a)
    Ac, cx, cy = _area_centroid(poly)
    Cc = 0.85 * sec.fc * Ac
    P, Mx, My = Cc, Cc * cy, Cc * cx
    tmin_bar = None
    eps_min = 1e9
    for bx, by in sec.bars:
        t = bx * ux + by * uy
        es = ECU * (t - tna) / c
        fs = max(-sec.fy, min(sec.fy, ES * es))
        if es > 0 and t >= tmax - a:
            fs -= 0.85 * sec.fc
        F = sec.Ab * fs
        P += F
        Mx += F * by
        My += F * bx
        if es < eps_min:
            eps_min = es
    eps_t = -eps_min                       # tension positive
    phi = phi_tied(eps_t, sec.ety)
    return {"Pn": P, "Mnx": Mx, "Mny": My, "eps_t": eps_t, "phi": phi, "c": c}


def _c_for_P(sec, beta, target, use_phi=True):
    """Smallest c giving (phi)Pn = target. Scan then bisect."""
    cmax = 4.0 * max(sec.b, sec.h) + 1.0

    def f(c):
        p = point(sec, beta, c)
        return (p["phi"] if use_phi else 1.0) * p["Pn"] - target

    N = 300
    prev_c, prev_f = 1e-3, f(1e-3)
    if prev_f >= 0:
        return 1e-3
    for i in range(1, N + 1):
        c = 1e-3 + (cmax - 1e-3) * (i / N) ** 2
        fc_ = f(c)
        if fc_ >= 0:
            lo, hi = prev_c, c
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                if f(mid) >= 0:
                    hi = mid
                else:
                    lo = mid
            return 0.5 * (lo + hi)
        prev_c, prev_f = c, fc_
    return None


def phiPn_max(sec):
    return 0.65 * sec.Pn_max


def capacity_at(sec, Pu, Mux, Muy):
    """3D interaction check at axial load Pu (N, +comp). Finds neutral-axis
    angle whose capacity moment direction matches the load direction."""
    if Pu > phiPn_max(sec) + 1e-6:
        return {"ok": False, "reason": "Pu > φPn,max", "ratio": float("inf")}
    ax, ay = abs(Mux), abs(Muy)
    Mres = math.hypot(ax, ay)
    gamma_t = math.atan2(ay, ax)          # target angle from Mx axis

    def cap(beta):
        c = _c_for_P(sec, beta, Pu)
        if c is None:
            return None
        p = point(sec, beta, c)
        mx, my = p["phi"] * p["Mnx"], p["phi"] * p["Mny"]
        return math.atan2(my, mx), math.hypot(mx, my), p

    lo, hi = 0.0, math.pi / 2
    best = None
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        g, M, p = cap(mid)
        best = (mid, g, M, p)
        if g < gamma_t:
            lo = mid
        else:
            hi = mid
    beta, g, M, p = best
    if Mres == 0:
        g0, M0, p0 = cap(0.0)
        return {"ok": True, "phiMcap": M0, "Mres": 0.0, "ratio": 0.0,
                "beta_deg": 0.0, "load_deg": 0.0, "eps_t": p0["eps_t"], "phi": p0["phi"]}
    return {"ok": True, "phiMcap": M, "Mres": Mres, "ratio": Mres / M,
            "beta_deg": math.degrees(beta), "load_deg": math.degrees(gamma_t),
            "cap_deg": math.degrees(g), "eps_t": p["eps_t"], "phi": p["phi"],
            "c": p["c"]}


def Mn_at_Pn(sec, axis, Pn):
    """Nominal moment (no φ) at Pn = given (used by 18.3.3)."""
    beta = 0.0 if axis == "x" else math.pi / 2
    c = _c_for_P(sec, beta, Pn, use_phi=False)
    p = point(sec, beta, c)
    return abs(p["Mnx"] if axis == "x" else p["Mny"])


# ---------------------------------------------------------------------------
# Stability / slenderness (non-sway)
# ---------------------------------------------------------------------------

def stability_index(sumPu, delta_o, Vus, lc):
    """6.6.4.4.1  Q = ΣPu·Δo/(Vus·lc)."""
    return sumPu * delta_o / (Vus * lc)


def curvature(Mt, Mb, V=None, L=None, given=None):
    """Return (M1/M2, how). M1/M2 < 0 single curvature, > 0 double (6.2.5.1).
    Decided by explicit 'given' or by shear equilibrium |V|·L."""
    a, b_ = abs(Mt), abs(Mb)
    M2, M1 = max(a, b_), min(a, b_)
    if M2 == 0:
        return -1.0, "M1 = M2 = 0 → ใช้ M1/M2 = −1 (กติกาสกิล, อนุรักษ์)"
    r = M1 / M2
    if given in ("single", "double"):
        return (-r if given == "single" else r), f"ระบุโดยผู้ใช้: {'โค้งทางเดียว' if given == 'single' else 'โค้งสองทาง'}"
    if V is not None and L:
        VL = abs(V) * L
        dd = abs(VL - (a + b_))
        ds_ = abs(VL - abs(a - b_))
        if dd < ds_:
            return r, f"|V|·L = {VL/1e6:.2f} ≈ |Mt|+|Mb| → โค้งสองทาง"
        return -r, f"|V|·L = {VL/1e6:.2f} ≈ ||Mt|−|Mb|| → โค้งทางเดียว"
    return -r, "ไม่มีข้อมูลทิศการดัด → สมมติโค้งทางเดียว (อนุรักษ์)"


def slenderness(sec, axis, Pu, Mt, Mb, lu, k=1.0, beta_dns=0.6, V=None, L=None,
                curv=None, r_method="sqrt", ei="a", transverse_load=False):
    """6.2.5, 6.6.4.4–6.6.4.5 (non-sway). axis 'x': bending about x (depth h)."""
    depth = sec.h if axis == "x" else sec.b
    width = sec.b if axis == "x" else sec.h
    Ig = width * depth ** 3 / 12.0
    r = math.sqrt(Ig / sec.Ag) if r_method == "sqrt" else 0.3 * depth
    ratio, how = curvature(Mt, Mb, V, L, curv)
    klr = k * lu / r
    limit = min(34.0 + 12.0 * ratio, 40.0)
    M2 = max(abs(Mt), abs(Mb))
    out = {"axis": axis, "r": r, "klu_r": klr, "M1_M2": ratio, "how": how,
           "limit": limit, "slender": klr > limit, "M2": M2, "Mc": M2,
           "delta": 1.0}
    if not out["slender"]:
        return out
    Ec = 4700.0 * math.sqrt(sec.fc)
    if ei == "b":
        Ise = sum(sec.Ab * ((by if axis == "x" else bx) ** 2) for bx, by in sec.bars)
        EI = (0.2 * Ec * Ig + ES * Ise) / (1 + beta_dns)
    else:
        EI = 0.4 * Ec * Ig / (1 + beta_dns)
    Pc = math.pi ** 2 * EI / (k * lu) ** 2
    M2min = Pu * (15.0 + 0.03 * depth)
    Cm = 1.0 if transverse_load else 0.6 - 0.4 * ratio
    M2u = M2
    if M2 < M2min:
        M2u, Cm = M2min, 1.0
    out.update(Ec=Ec, EI=EI, Pc=Pc, Cm=Cm, M2min=M2min)
    if Pu >= 0.75 * Pc:
        out.update(unstable=True, delta=float("inf"), Mc=float("inf"))
        return out
    delta = max(Cm / (1.0 - Pu / (0.75 * Pc)), 1.0)
    Mc = delta * M2u
    out.update(unstable=False, delta=delta, Mc=Mc,
               second_order_ok=Mc <= 1.4 * max(M2, M2min) + 1e-6)   # 6.2.5.3
    return out


# ---------------------------------------------------------------------------
# Shear
# ---------------------------------------------------------------------------

def lambda_s(d):
    return min(1.0, math.sqrt(2.0 / (1.0 + d / 250.0)))


def shear_dir(sec, direction, Vu, Nu, s, legs, fyt, lam=1.0):
    """direction 'y': shear along y (bw = b, depth h); 'x': along x."""
    bw = sec.b if direction == "y" else sec.h
    depth = sec.h if direction == "y" else sec.b
    d = depth - sec.edge
    coord = 1 if direction == "y" else 0
    As_half = sum(sec.Ab for bar in sec.bars if bar[coord] < -1e-6)
    rho_w = As_half / (bw * d)
    fyt_d = min(fyt, FYT_SHEAR_MAX)
    Av = legs * bar_area(sec.ds)
    avmin = max(0.062 * math.sqrt(sec.fc) * bw / fyt_d, 0.35 * bw / fyt_d)
    av_ok = Av / s >= avmin - 1e-9
    sfc = math.sqrt(sec.fc) if av_ok else min(math.sqrt(sec.fc), SQRT_FC_MAX)
    ax = min(Nu / (6 * sec.Ag), 0.05 * sec.fc) if Nu > 0 else Nu / (6 * sec.Ag)
    va = (0.17 * lam * sfc + ax) * bw * d
    vc_c = (0.66 * lambda_s(d) * lam * rho_w ** (1 / 3) * sfc + ax) * bw * d
    vmax = 0.42 * lam * sfc * bw * d
    Vc = max(0.0, min(va if av_ok else vc_c, vmax))
    Vc_noav = max(0.0, min(vc_c, vmax))
    Vs = Av * fyt_d * d / s
    phiVn = PHI_V * (Vc + Vs)
    need_min = Vu > 0.5 * PHI_V * Vc_noav                       # 10.6.2.1
    smax = min(d / 2, 600.0) if Vs <= 0.33 * math.sqrt(sec.fc) * bw * d else min(d / 4, 300.0)
    sec_lim = PHI_V * (Vc + 0.66 * math.sqrt(sec.fc) * bw * d)
    checks = {"strength": phiVn >= Vu, "section_22.5.1.2": Vu <= sec_lim,
              "Av_min_10.6.2": (not need_min) or av_ok,
              "s_10.7.6.5.2": (not need_min) or s <= smax + 1e-9}
    return {"dir": direction, "bw": bw, "d": d, "rho_w": rho_w, "Vc": Vc,
            "eq": "(a)" if av_ok else "(c)", "Vc_max": vmax,
            "capped": (va if av_ok else vc_c) > vmax, "Vs": Vs, "phiVn": phiVn,
            "Vu": Vu, "Av": Av, "Av_min_s": avmin, "need_min": need_min,
            "fyt_used": fyt_d, "smax": smax, "checks": checks,
            "ok": all(checks.values()), "Nu_term": ax}


def biaxial_shear(rx, ry):
    """22.5.1.10–22.5.1.11."""
    ux = rx["Vu"] / rx["phiVn"] if rx["phiVn"] else float("inf")
    uy = ry["Vu"] / ry["phiVn"] if ry["phiVn"] else float("inf")
    if ux <= 0.5 or uy <= 0.5:
        return {"required": False, "sum": ux + uy, "ok": True}
    return {"required": True, "sum": ux + uy, "ok": ux + uy <= 1.5}


# ---------------------------------------------------------------------------
# Detailing and splices
# ---------------------------------------------------------------------------

def supports_needed(m, clear):
    """Interior bars on a face that must be laterally supported (25.7.2.3)."""
    if m <= 0:
        return 0
    if clear > 150.0:
        return m
    return m // 2


def detailing(sec, s_tie, dagg=20.0, crossties_x=0, crossties_y=0):
    out = {}
    rho = sec.Ast / sec.Ag
    out["rho_g"] = rho
    out["rho_ok"] = 0.01 <= rho <= 0.08                          # 10.6.1.1
    out["n_bars"] = len(sec.bars)
    out["n_ok"] = len(sec.bars) >= 4                             # 10.7.3.1
    clear_min = max(40.0, 1.5 * sec.db, 4.0 / 3.0 * dagg)        # 25.2.3
    cx = (sec.b - 2 * sec.edge) / (sec.nx - 1) - sec.db
    cy = (sec.h - 2 * sec.edge) / (sec.ny - 1) - sec.db
    out.update(clear_min=clear_min, clear_x=cx, clear_y=cy,
               clear_ok=min(cx, cy) >= clear_min - 1e-9)
    tie_min = 10.0 if sec.db <= 32 else 12.0                     # 25.7.2.2
    out.update(tie_min=tie_min, tie_ok=sec.ds >= tie_min - 0.6)  # DB10 ok for No.10 (9.5)
    smax = min(16 * sec.db, 48 * sec.ds, min(sec.b, sec.h))      # 25.7.2.1
    out.update(s_tie=s_tie, s_tie_max=smax, s_tie_ok=s_tie <= smax + 1e-9)
    # lateral support: faces parallel to x (nx bars) need crossties running in y
    need_y = supports_needed(sec.nx - 2, cx)
    need_x = supports_needed(sec.ny - 2, cy)
    out.update(crossties_req_y=need_y, crossties_req_x=need_x,
               crossties_ok=crossties_y >= need_y and crossties_x >= need_x)
    out["Ktr_note"] = sec.fy_in >= 550.0                         # 10.7.1.3
    return out


def psi_g(fy):
    return 1.0 if fy <= 420 + 1e-6 else (1.15 if fy <= 550 + 1e-6 else 1.3)


def splices(sec, s_tie, legs_x, legs_y):
    """10.7.5 + 25.4.2 / 25.5.2 / 25.5.5."""
    fy, fc, db = sec.fy_in, sec.fc, sec.db
    sfc = min(math.sqrt(fc), SQRT_FC_MAX)
    k = 1.7 if db > SMALL_BAR_MAX else 2.1   # Table 25.4.2.3: 2.1 only for No. 19 (19.1 mm) and smaller
    ld = max(fy * psi_g(fy) / (k * sfc) * db, 300.0)
    lap_B = max(1.3 * ld, 300.0)
    lap_A = max(1.0 * ld, 300.0)
    if fy <= 420 + 1e-6:
        lc = 0.071 * fy * db
    elif fy <= 550 + 1e-6:
        lc = (0.13 * fy - 24.0) * db
    else:
        lc = None
    if lc is not None:
        lc = max(lc, 300.0)
        if fc < 21:
            lc *= 4.0 / 3.0
    # 10.7.5.2.1(a): factor 0.83 if tie legs area >= 0.0015 h s in both directions;
    # for each dimension count the legs perpendicular to it (legs_x run along x,
    # i.e. perpendicular to h; legs_y run along y, perpendicular to b)
    At = bar_area(sec.ds)
    ok_x = legs_x * At >= 0.0015 * sec.h * s_tie
    ok_y = legs_y * At >= 0.0015 * sec.b * s_tie
    lc_red = max(0.83 * lc, 300.0) if (lc and ok_x and ok_y) else lc
    return {"ld": ld, "lap_A": lap_A, "lap_B": lap_B, "lap_comp": lc,
            "lap_comp_reduced": lc_red, "factor_083": bool(lc and ok_x and ok_y),
            "psi_g": psi_g(fy)}


# ---------------------------------------------------------------------------
# Top level
# ---------------------------------------------------------------------------

def to_si(inp):
    u = inp.get("units", "kgf-m")
    s = json.loads(json.dumps(inp))
    if u == "kgf-m":
        s["b"], s["h"] = inp["b"] * 1000, inp["h"] * 1000
        for k in ("fc", "fy", "fyt", "fc_floor"):
            if inp.get(k) is not None:
                s[k] = inp[k] * KSC_TO_MPA
        for k in ("lu", "L", "lux", "luy"):
            if inp.get(k) is not None:
                s[k] = inp[k] * 1000
        fF, fM = G, G * 1000
    elif u == "SI":
        for k in ("lu", "L", "lux", "luy"):
            if inp.get(k) is not None:
                s[k] = inp[k] * 1000          # SI input: lengths in m
        fF, fM = 1e3, 1e6
    else:
        raise ValueError("units must be 'kgf-m' or 'SI'")
    for cb in s.get("combos", []):
        for k in ("Pu", "Vux", "Vuy", "Vu_omega_x", "Vu_omega_y"):
            if cb.get(k) is not None:
                cb[k] = cb[k] * fF
        for k in ("Mx_top", "Mx_bot", "My_top", "My_bot"):
            if cb.get(k) is not None:
                cb[k] = cb[k] * fM
    st = s.get("story")
    if st:
        st["sumPu"] = st["sumPu"] * fF
        st["Vus"] = st["Vus"] * fF
        st["lc"] = st["lc"] * 1000
    s["_fF"], s["_fM"] = fF, fM
    return s


# ---------------------------------------------------------------------------
# Step 0 / 6 / 7 — seismic system provisions (Ch.18)
# ---------------------------------------------------------------------------

def mn_max_over_combos(sec, axis, Pus):
    """Largest nominal moment (no φ) for the axial forces of the design combos
    (18.3.3 / 18.4.3.1(a): Pu chosen to develop the largest moment strength)."""
    best = 0.0
    for Pu in Pus:
        try:
            best = max(best, Mn_at_Pn(sec, axis, Pu))
        except Exception:
            continue
    return best


def seismic_shear(sec, axis, Pus, lu, system, Vu_omega=None):
    """OMF §18.3.3 (only when lu ≤ 5c1) and IMF §18.4.3.1: φVn ≥ lesser of
    (a) shear from Mn at both ends, (b) shear from combos with Ω0·E."""
    c1 = sec.h if axis == "x" else sec.b
    if system == "OMF" and lu > 5 * c1:
        return {"applies": False, "why": f"ℓu = {lu:.0f} > 5c1 = {5*c1:.0f} mm"}
    Mn = mn_max_over_combos(sec, axis, Pus)
    Va = 2 * Mn / lu
    Ve = min(Va, Vu_omega) if Vu_omega else Va
    return {"applies": True, "Mn": Mn, "V_from_Mn": Va, "Ve": Ve,
            "used_omega": bool(Vu_omega), "clause": "18.3.3" if system == "OMF" else "18.4.3.1"}


def imf_detailing(sec, lu, so, fy):
    """18.4.3.3–18.4.3.4 (SI values converted from 8 in., 6 in., 18 in.)."""
    if fy <= 420 + 1e-6:
        so_bar = min(8 * sec.db, 200.0)
        lbl = "Grade 420: min(8db, 200 mm)"
    else:
        so_bar = min(6 * sec.db, 150.0)
        lbl = "Grade 550: min(6db, 150 mm)"
    so_max = min(so_bar, 0.5 * min(sec.b, sec.h))
    lo = max(lu / 6.0, max(sec.b, sec.h), 450.0)
    return {"so": so, "so_max": so_max, "so_rule": lbl, "so_ok": so <= so_max + 1e-9,
            "lo": lo, "first_hoop": so_max / 2.0}


# ---------------------------------------------------------------------------
# Step 9 — joints, floor concrete, footing
# ---------------------------------------------------------------------------

def floor_concrete(fc_col, fc_floor, beams_4_sides=False):
    """§15.5.1: if f′c,floor < 0.7 f′c,col use (a) column concrete through floor
    extending 600 mm, (b) dowels/confinement at floor f′c, or (c) equivalent
    strength 0.75 f′c,col + 0.35 f′c,floor (joints confined by beams on 4 sides,
    f′c,col ≤ 2.5 f′c,floor)."""
    if fc_floor is None:
        return None
    need = fc_floor < 0.7 * fc_col
    out = {"fc_floor": fc_floor, "ratio": fc_floor / fc_col, "required": need}
    if need:
        eq = 0.75 * min(fc_col, 2.5 * fc_floor) + 0.35 * fc_floor
        out["fc_equiv_c"] = eq if beams_4_sides else None
    return out


def footing_dowels(sec):
    """§16.3.4.1: cast-in-place column to footing — As across interface ≥ 0.005Ag."""
    req = 0.005 * sec.Ag
    n = math.ceil(req / sec.Ab)
    return {"As_req": req, "n_bars": max(n, 4), "As_cont": sec.Ast,
            "ok_if_all_bars_dowelled": sec.Ast >= req}


# ---------------------------------------------------------------------------
# Top level
# ---------------------------------------------------------------------------

def design_column(inp):
    si = to_si(inp)
    sec = Section(si["b"], si["h"], si["fc"], si["fy"], si["bar_db"],
                  si["nx"], si["ny"], si.get("cover", 40.0),
                  si.get("tie_db", 10.0), si.get("cover_to", "tie"),
                  si.get("grade420_exception", False))
    fyt = si.get("fyt", si["fy"])
    s_tie = si.get("tie_s", 150.0)
    so = si.get("tie_s_end", s_tie)
    legs_x = si.get("tie_legs_x", 2)
    legs_y = si.get("tie_legs_y", 2)
    lux = si.get("lux", si.get("lu"))
    luy = si.get("luy", si.get("lu"))
    L = si.get("L")
    k = si.get("k", 1.0)
    system = si.get("system")
    res = {"input": inp, "sec": sec, "fyt": fyt, "messages": [], "system": system}

    # Step 0 — seismic system
    if system == "SMF":
        res["messages"].append(("FAIL", "18.7", "เสา SMF ต้องใช้ §18.7 ครบ (ΣMnc ≥ 1.2ΣMnb, Ash, ℓo, Ve จาก Mpr) — นอกขอบเขตสกิล"))
        res["stopped"] = True
        return res
    if system not in (None, "OMF", "IMF"):
        res["messages"].append(("FAIL", "18.2", f"ไม่รู้จักระบบ '{system}' — ใช้ OMF, IMF หรือไม่ระบุ (SDC A)"))
        res["stopped"] = True
        return res
    if k > 1.0:
        res["messages"].append(("WARN", "6.6.4.4.3", "non-sway ควรใช้ k ≤ 1.0"))

    # Step 3 — sway / non-sway
    st = si.get("story")
    if st:
        Q = stability_index(st["sumPu"], st["delta_o"], st["Vus"], st["lc"])
        res["Q"] = Q
        if Q > 0.05:
            res["messages"].append(("FAIL", "6.6.4.3", f"Q = {Q:.4f} > 0.05 → โครง sway ต้องใช้ §6.6.4.6 หรือวิเคราะห์ P-Δ (นอกขอบเขตสกิล)"))
            res["stopped"] = True
            return res

    # Step 5 — axial limit
    res["phiPn_max"] = phiPn_max(sec)

    # Steps 4–6 per combination
    rows = []
    for i, cb in enumerate(si["combos"]):
        name = cb.get("name", f"LC{i+1}")
        Pu = cb["Pu"]
        row = {"name": name, "Pu": Pu}
        sx = sy = None
        if lux:
            sx = slenderness(sec, "x", Pu, cb.get("Mx_top", 0), cb.get("Mx_bot", 0),
                             lux, k, si.get("beta_dns", 0.6), cb.get("Vuy"), L,
                             cb.get("curv_x"), si.get("r_method", "sqrt"),
                             si.get("ei", "a"), cb.get("transverse_load", False))
        if luy:
            sy = slenderness(sec, "y", Pu, cb.get("My_top", 0), cb.get("My_bot", 0),
                             luy, k, si.get("beta_dns", 0.6), cb.get("Vux"), L,
                             cb.get("curv_y"), si.get("r_method", "sqrt"),
                             si.get("ei", "a"), cb.get("transverse_load", False))
        row["slender_x"], row["slender_y"] = sx, sy
        pts = [("บน", cb.get("Mx_top", 0), cb.get("My_top", 0)),
               ("ล่าง", cb.get("Mx_bot", 0), cb.get("My_bot", 0))]
        if (sx and sx["slender"]) or (sy and sy["slender"]):
            mx = sx["Mc"] if sx and sx["slender"] else max(abs(cb.get("Mx_top", 0)), abs(cb.get("Mx_bot", 0)))
            my = sy["Mc"] if sy and sy["slender"] else max(abs(cb.get("My_top", 0)), abs(cb.get("My_bot", 0)))
            pts.append(("กลาง (ขยาย)", mx, my))
        chk = []
        for lbl, mx, my in pts:
            if math.isinf(mx) or math.isinf(my):
                chk.append({"at": lbl, "ok": False, "ratio": float("inf"),
                            "reason": "ไม่เสถียร Pu ≥ 0.75Pc"})
                continue
            c = capacity_at(sec, Pu, mx, my)
            c["at"], c["Mux"], c["Muy"] = lbl, mx, my
            chk.append(c)
        row["checks"] = chk
        row["ratio"] = max(c["ratio"] for c in chk)
        if cb.get("Vux") is not None or cb.get("Vuy") is not None:
            rx = shear_dir(sec, "x", abs(cb.get("Vux", 0)), Pu, s_tie, legs_x, fyt)
            ry = shear_dir(sec, "y", abs(cb.get("Vuy", 0)), Pu, s_tie, legs_y, fyt)
            row["shear"] = {"x": rx, "y": ry, "biaxial": biaxial_shear(rx, ry)}
        rows.append(row)
    res["rows"] = rows

    # Step 6 — seismic shear (OMF short column / IMF)
    if system in ("OMF", "IMF") and (lux or luy):
        Pus = [cb["Pu"] for cb in si["combos"]]
        Pmin = min(Pus)
        ss = {}
        for ax_, lu_ in (("x", lux), ("y", luy)):
            if not lu_:
                continue
            key = f"Vu_omega_{'y' if ax_ == 'x' else 'x'}"
            vo = max((cb.get(key) or 0 for cb in si["combos"]), default=0) or None
            r = seismic_shear(sec, ax_, Pus, lu_, system, vo)
            if r.get("applies"):
                dir_ = "y" if ax_ == "x" else "x"
                legs = legs_y if dir_ == "y" else legs_x
                s_use = so if system == "IMF" else s_tie
                r["check"] = shear_dir(sec, dir_, r["Ve"], Pmin, s_use, legs, fyt)
                r["s_used"] = s_use
            ss[ax_] = r
        res["seismic_shear"] = ss

    # Step 7 — detailing (+ IMF end zones)
    res["detail"] = detailing(sec, s_tie, si.get("dagg", 20.0),
                              si.get("crossties_x", 0), si.get("crossties_y", 0))
    if system == "IMF":
        lu_min = min(v for v in (lux, luy) if v) if (lux or luy) else None
        if lu_min:
            res["imf"] = imf_detailing(sec, lu_min, so, sec.fy_in)

    # Step 8 — splices
    res["splice"] = splices(sec, s_tie, legs_x, legs_y)

    # Step 9 — joint, floor concrete, footing
    res["floor"] = floor_concrete(sec.fc, si.get("fc_floor"), si.get("beams_4_sides", False))
    if si.get("base_on_footing"):
        res["dowels"] = footing_dowels(sec)
    return res


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _st(ok):
    return "✅ ผ่าน" if ok else "❌ ไม่ผ่าน"


def _kb(step):
    return f"_อ้างอิง: {KB[step]}_"


def report(res):
    inp = res["input"]
    kg = inp.get("units", "kgf-m") == "kgf-m"
    sec = res["sec"]
    system = res.get("system")

    def P(n):
        return f"{n/1e3:,.1f} kN" + (f" ({n/G/1000:,.2f} t)" if kg else "")

    def M(n):
        return f"{n/1e6:,.1f} kN·m" + (f" ({n/G/1000:,.0f} kgf·m)" if kg else "")

    L = ["# ผลออกแบบ/ตรวจสอบเสา RC — ACI 318M-19 (ตาม KB โครงการ)\n"]
    L.append("## 0. ระบบต้านแผ่นดินไหว")
    L.append(f"- ระบบ: **{system or 'ไม่ระบุ (SDC A / ไม่อยู่ในระบบต้านแผ่นดินไหว)'}**")
    L.append(_kb(0) + "\n")
    L.append("## 1. หน้าตัดและวัสดุ")
    L.append(f"- {sec.b:.0f}×{sec.h:.0f} mm · f′c = {sec.fc:.2f} MPa · fy = {sec.fy_in:.1f} MPa"
             + (f" (ใช้ {sec.fy:.0f} ตาม fy ≤ 550)" if sec.fy < sec.fy_in else "")
             + f" · fyt (เฉือน) = {min(res['fyt'], FYT_SHEAR_MAX):.1f} MPa")
    L.append(f"- เหล็กยืน {len(sec.bars)}-DB{sec.db:.0f} (ด้าน b {sec.nx} เส้น, ด้าน h {sec.ny} เส้น), "
             f"Ast = {sec.Ast:,.0f} mm² · ปลอก DB{sec.ds:.0f} @ {inp.get('tie_s', 150)} mm"
             + (f" (ปลายเสา @ {inp.get('tie_s_end')} mm)" if inp.get("tie_s_end") else "")
             + f" · ระยะผิวถึงศูนย์เหล็ก {sec.edge:.1f} mm")
    L.append(_kb(1) + "\n")
    for lvl, cl, msg in res["messages"]:
        L.append(f"- {'❌' if lvl == 'FAIL' else '⚠️'} §{cl}: {msg}")
    L.append("## 3. Sway หรือ non-sway")
    if "Q" in res:
        L.append(f"- Q = ΣPuΔo/(Vus·lc) = {res['Q']:.4f} {'≤' if res['Q'] <= 0.05 else '>'} 0.05 → "
                 + ("non-sway" if res['Q'] <= 0.05 else "sway"))
    else:
        L.append("- **ยังไม่ตรวจ** — ไม่มีข้อมูลชั้น สมมติ non-sway")
    L.append(_kb(3) + "\n")
    if res.get("stopped"):
        L.append("**หยุดการคำนวณ — อยู่นอกขอบเขต**")
        return "\n".join(L)

    L.append("## 4. ความชะลูด")
    for row in res["rows"]:
        for key in ("slender_x", "slender_y"):
            s = row[key]
            if not s:
                continue
            ax = "x (ความลึก h)" if s["axis"] == "x" else "y (ความลึก b)"
            line = (f"- {row['name']} แกน {ax}: kℓu/r = {s['klu_r']:.2f}, M1/M2 = {s['M1_M2']:+.3f} ({s['how']}), "
                    f"เกณฑ์ = {s['limit']:.1f} → ")
            if not s["slender"]:
                line += "ไม่ชะลูด"
            elif s.get("unstable"):
                line += f"**❌ ไม่เสถียร** (Pu ≥ 0.75Pc = {P(0.75*s['Pc'])})"
            else:
                line += (f"**ชะลูด**: Pc = {P(s['Pc'])}, Cm = {s['Cm']:.3f}, δ = {s['delta']:.3f}, "
                         f"M2,min = {M(s['M2min'])}, **Mc = {M(s['Mc'])}**"
                         + ("" if s["second_order_ok"] else " · ❌ Mc > 1.4M (§6.2.5.3) ต้องแก้ระบบ"))
            L.append(line)
    L.append(_kb(4) + "\n")

    L.append("## 5. แรงอัดร่วมดัดสองแกน")
    L.append(f"- Po = {P(sec.Po)}; **φPn,max = 0.65 × 0.80Po = {P(res['phiPn_max'])}** (Table 22.4.2.1)")
    L.append("\n| Combo | จุด | Pu (kN) | Mux | Muy | มุมโหลด | Mres | φMcap | φ | ratio |\n|---|---|---|---|---|---|---|---|---|---|")
    worst = (0.0, None)
    for row in res["rows"]:
        for c in row["checks"]:
            if c.get("reason"):
                L.append(f"| {row['name']} | {c['at']} | {row['Pu']/1e3:,.1f} | | | | | | | ❌ {c['reason']} |")
                worst = (float("inf"), row["name"])
                continue
            r = c["ratio"]
            L.append(f"| {row['name']} | {c['at']} | {row['Pu']/1e3:,.1f} | {abs(c['Mux'])/1e6:,.1f} | {abs(c['Muy'])/1e6:,.1f} | "
                     f"{c['load_deg']:.1f}° | {c['Mres']/1e6:,.1f} | {c['phiMcap']/1e6:,.1f} | {c['phi']:.3f} | "
                     + (f"**{r:.3f}**" if r > 1 else f"{r:.3f}") + " |")
            if r > worst[0]:
                worst = (r, row["name"])
    L.append("\n(kN·m · ratio = Mres/φMcap ที่ Pu เดียวกัน — 3D interaction, หามุมแกนสะเทินให้ทิศโมเมนต์ความจุตรงทิศโหลด)")
    L.append(_kb(5) + "\n")

    L.append("## 6. แรงเฉือน")
    sh_ok = True
    for row in res["rows"]:
        sh = row.get("shear")
        if not sh:
            continue
        for k_ in ("x", "y"):
            r = sh[k_]
            sh_ok &= r["ok"]
            L.append(f"- {row['name']} ทิศ {k_}: Vu = {P(r['Vu'])}, d = {r['d']:.0f}, Vc {r['eq']} = {P(r['Vc'])}"
                     + (" (= Vc,max)" if r["capped"] else "")
                     + f", Vs = {P(r['Vs'])}, **φVn = {P(r['phiVn'])}**, "
                     + (f"s,max = {r['smax']:.0f} mm" if r["need_min"] else "ไม่บังคับปลอกขั้นต่ำ")
                     + f" → {_st(r['ok'])}")
        bi = sh["biaxial"]
        if bi["required"]:
            sh_ok &= bi["ok"]
            L.append(f"  - สองทิศ §22.5.1.11: ผลรวม = {bi['sum']:.3f} ≤ 1.5 → {_st(bi['ok'])}")
    for ax_, o in (res.get("seismic_shear") or {}).items():
        if not o.get("applies"):
            L.append(f"- §18.3.3 แกน {ax_}: ไม่เข้าเงื่อนไขเสาสั้น ({o['why']})")
            continue
        ck = o["check"]
        ok = ck["phiVn"] >= o["Ve"] and ck["checks"]["section_22.5.1.2"]
        sh_ok &= ok
        L.append(f"- **§{o['clause']} ({system}) แกน {ax_}:** Mn สูงสุดในช่วง Pu ที่ออกแบบ (ไม่คูณ φ) = {M(o['Mn'])} → "
                 f"2Mn/ℓu = {P(o['V_from_Mn'])}"
                 + (f"; เทียบ Ω₀E แล้วใช้ค่าน้อยกว่า" if o["used_omega"] else " (ไม่มีกรณี Ω₀E → ใช้ค่านี้)")
                 + f" → Ve = {P(o['Ve'])}; φVn (s = {o['s_used']:.0f} mm, Pu ต่ำสุด) = {P(ck['phiVn'])} → {_st(ok)}")
    L.append(_kb(6) + "\n")

    d = res["detail"]
    L.append("## 7. รายละเอียดเหล็ก")
    L.append(f"- ρg = {d['rho_g']*100:.2f}% (1–8%, §10.6.1.1) → {_st(d['rho_ok'])}; จำนวน {d['n_bars']} ≥ 4 (§10.7.3.1) → {_st(d['n_ok'])}")
    L.append(f"- ระยะว่างเหล็กยืน {min(d['clear_x'], d['clear_y']):.0f} ≥ {d['clear_min']:.0f} mm (§25.2.3) → {_st(d['clear_ok'])}")
    L.append(f"- ขนาดปลอก ≥ DB{d['tie_min']:.0f} (§25.7.2.2) → {_st(d['tie_ok'])}; ระยะปลอก {d['s_tie']:.0f} ≤ min(16db, 48dt, ด้านแคบ) = {d['s_tie_max']:.0f} mm (§25.7.2.1) → {_st(d['s_tie_ok'])}")
    L.append(f"- crosstie §25.7.2.3: ต้องมีแนว y ≥ {d['crossties_req_y']}, แนว x ≥ {d['crossties_req_x']} → {_st(d['crossties_ok'])}")
    L.append("- ปลอกวงแรก/วงสุดท้าย ≤ s/2 จากผิวฐานราก/พื้น และใต้เหล็กล่างสุดของพื้น (§10.7.6.2)")
    imf_ok = True
    if res.get("imf"):
        im = res["imf"]
        imf_ok = im["so_ok"]
        L.append(f"- **IMF §18.4.3.3:** so = {im['so']:.0f} ≤ min({im['so_rule']}, ½ ด้านแคบ) = {im['so_max']:.0f} mm → {_st(im['so_ok'])}")
        L.append(f"- **IMF ℓo** ≥ max(ℓu/6, ด้านโตสุด, 450 mm) = **{im['lo']:.0f} mm** จากผิวจุดต่อทั้งสองปลาย; ปลอกวงแรก ≤ so/2 = {im['first_hoop']:.0f} mm (§18.4.3.4); นอก ℓo ตาม §10.7.6.5.2")
        L.append("  - ค่า 200 / 150 / 450 mm แปลงจาก 8 / 6 / 18 in. (Ch.18 ยังไม่ได้เทียบเล่ม 318M)")
    if d["Ktr_note"]:
        L.append("- ⚠️ fy ≥ 550 MPa → ช่วงฝังยึด/ทาบต้องมี Ktr ≥ 0.5db (§10.7.1.3)")
    L.append(_kb(7) + "\n")

    sp = res["splice"]
    L.append("## 8. ต่อทาบเหล็กยืน")
    if sp["lap_comp"]:
        L.append(f"- ทาบรับแรงอัด (§25.5.5.1) = {sp['lap_comp']:.0f} mm"
                 + (f" → ×0.83 (ขาปลอก ⊥ แต่ละด้าน ≥ 0.0015hs, §10.7.5.2.1) = **{sp['lap_comp_reduced']:.0f} mm**" if sp["factor_083"] else ""))
    L.append(f"- ทาบรับแรงดึง Class B = **{sp['lap_B']:.0f} mm** (ℓd = {sp['ld']:.0f} mm, ψg = {sp['psi_g']}) — ใช้เมื่อหน่วยแรงดึง > 0.5fy หรือทาบ > 50% ที่หน้าตัดเดียว (Table 10.7.5.2.2)")
    if system == "IMF":
        L.append("- ตำแหน่งทาบ: แนะนำครึ่งกลางของความสูงเสา (นอก ℓo)")
    L.append(_kb(8) + "\n")

    L.append("## 9. จุดต่อ คอนกรีตพื้น และฐานราก")
    fl = res.get("floor")
    if fl:
        if fl["required"]:
            L.append(f"- ❗ **§15.5.1:** f′c พื้น = {fl['fc_floor']:.1f} < 0.7f′c เสา (อัตราส่วน {fl['ratio']:.2f}) → ต้องเลือก (a) เทคอนกรีตเสาทะลุพื้น ยื่นจากผิวเสา ≥ 600 mm "
                     "(b) ใช้ f′c พื้นคำนวณเสา + dowel/เหล็กโอบรัด หรือ (c) "
                     + (f"f′c เทียบเท่า = **{fl['fc_equiv_c']:.1f} MPa** (คานครบ 4 ด้าน) แล้วตรวจกำลังใหม่" if fl.get("fc_equiv_c") else "f′c เทียบเท่า (ใช้ได้เฉพาะจุดต่อที่มีคานลึกใกล้เคียงกันครบ 4 ด้าน)"))
        else:
            L.append(f"- §15.5.1: f′c พื้น/เสา = {fl['ratio']:.2f} ≥ 0.7 → ไม่ต้องทำเพิ่ม")
    else:
        L.append("- §15.5.1: **ยังไม่ตรวจ** — ไม่ได้ระบุ f′c พื้น (`fc_floor`)")
    L.append("- รอยต่อคาน-เสา §15.3.1: ปลอกในรอยต่อ ≥ 2 ชั้นภายในความลึกคาน ระยะ ≤ 200 mm (ยกเว้นมีคานครบ 4 ด้านตาม §15.3.1.1)"
             + ("; IMF ใช้ระยะ ≤ so ตาม §18.4.4" if system == "IMF" else "") + " — **ยังไม่ตรวจแรงเฉือนในรอยต่อ**")
    dw = res.get("dowels")
    if dw:
        L.append(f"- §16.3.4.1 เหล็กข้ามผิวเสา-ฐานราก ≥ 0.005Ag = {dw['As_req']:,.0f} mm² → DB{sec.db:.0f} อย่างน้อย {dw['n_bars']} เส้น"
                 + f" (เหล็กยืนทั้งหมด {sec.Ast:,.0f} mm² {'พอถ้าเสียบลงฐานรากทุกเส้น' if dw['ok_if_all_bars_dowelled'] else 'ไม่พอ'})")
    L.append(_kb(9) + "\n")

    all_ok = (worst[0] <= 1.0 and sh_ok and d["rho_ok"] and d["n_ok"] and d["clear_ok"]
              and d["tie_ok"] and d["s_tie_ok"] and d["crossties_ok"] and imf_ok
              and not (fl and fl["required"]))
    L.append("## 10. สรุปสถานะ")
    L.append("| ขั้น | รายการ | สถานะ |\n|---|---|---|")
    L.append(f"| 0 | ระบบ | {system or 'ไม่ระบุ'} |")
    L.append(f"| 3 | Sway | {'non-sway (Q = %.4f)' % res['Q'] if 'Q' in res else '**ยังไม่ตรวจ**'} |")
    unstable = any(s and s.get("unstable") for r in res["rows"] for s in (r["slender_x"], r["slender_y"]))
    L.append(f"| 4 | ความชะลูด | {'❌ ไม่เสถียร' if unstable else 'ตรวจแล้ว'} |")
    L.append(f"| 5 | φPn,max และ 3D interaction (ratio สูงสุด {worst[0]:.3f} @ {worst[1]}) | {_st(worst[0] <= 1.0 and all(r['Pu'] <= res['phiPn_max'] for r in res['rows']))} |")
    L.append(f"| 6 | แรงเฉือน{' + ' + system if system else ''} | {_st(sh_ok)} |")
    L.append(f"| 7 | รายละเอียดเหล็ก | {_st(d['rho_ok'] and d['n_ok'] and d['clear_ok'] and d['tie_ok'] and d['s_tie_ok'] and d['crossties_ok'] and imf_ok)} |")
    L.append("| 8 | ต่อทาบ | คำนวณแล้ว — ระบุในแบบ |")
    L.append(f"| 9 | §15.5 คอนกรีตพื้น | {('❗ ต้องดำเนินการ' if fl['required'] else '✅') if fl else '**ยังไม่ตรวจ**'} |")
    L.append("| 9 | แรงเฉือนรอยต่อคาน-เสา (Ch.15) | **ยังไม่ตรวจ** |")
    L.append("")
    L.append(f"**{'ผ่านทุกรายการที่ตรวจ' if all_ok else 'มีรายการไม่ผ่านหรือต้องดำเนินการ'}** (ไม่รวมรายการที่ยังไม่ตรวจ)\n")
    sec_ety = sec.ety
    L.append("_สมมติฐาน: ACI 318M-19 · tied · non-sway · Es = 200,000 MPa · "
             f"εty = {sec_ety:.5f} · βdns = {inp.get('beta_dns', 0.6)} · (EI)eff สมการ ({inp.get('ei', 'a')}) · "
             "ค่าคงที่ SI ของ Ch.6, 10, 22, 25 เทียบเล่ม 318M-19 แล้ว · "
             "ผลนี้ใช้ประกอบรายการคำนวณ วิศวกรผู้รับผิดชอบต้องตรวจและลงนาม_")
    return "\n".join(L)


def _jsonable(o):
    if isinstance(o, Section):
        return {"b": o.b, "h": o.h, "Ast": o.Ast, "bars": o.bars}
    if isinstance(o, float) and math.isinf(o):
        return None
    raise TypeError(type(o))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    with open(argv[1], encoding="utf-8") as fh:
        inp = json.load(fh)
    res = design_column(inp)
    if "--json" in argv:
        print(json.dumps(res, default=_jsonable, ensure_ascii=False, indent=2))
    else:
        print(report(res))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
