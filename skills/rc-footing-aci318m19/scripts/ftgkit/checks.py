"""Steps 5–9 — strength of the footing (factored loads, net pressure).
KB: chapter-13 §13.2.6–13.3.3, chapter-22 §22.5, 22.6, 22.8, chapter-08 §8.4.4, 8.6.1, 8.7.2,
chapter-16 §16.3, chapter-25 §25.4."""
from __future__ import annotations

import math

from .rcsi import PHI_V, SQRT_FC_MAX, area, beta1, phi_tied, ld_tension, ldh, ldc
from .pressure import integrate


class Footing:
    """B along x, L along y (mm); column cx × cy at the centre; bars: x-bars span B."""

    def __init__(self, B, L, h, cx, cy, fc, fy, cover=75.0, dbx=16.0, dby=16.0, sx=None, sy=None):
        self.B, self.L, self.h, self.cx, self.cy = map(float, (B, L, h, cx, cy))
        self.fc, self.fy, self.cover = float(fc), float(fy), float(cover)
        self.dbx, self.dby, self.sx, self.sy = float(dbx), float(dby), sx, sy
        # bars spanning the longer plan dimension go in the bottom layer
        self.x_bottom = self.B >= self.L
        if self.x_bottom:
            self.dx = h - cover - dbx / 2
            self.dy = h - cover - dbx - dby / 2
        else:
            self.dy = h - cover - dby / 2
            self.dx = h - cover - dby - dbx / 2
        self.d = (self.dx + self.dy) / 2                       # 22.6.2.1

    def As(self, direction):
        """Provided steel (mm²) of the bars spanning `direction` across the full width."""
        db, s, w = (self.dbx, self.sx, self.L) if direction == "x" else (self.dby, self.sy, self.B)
        if not s:
            return 0.0
        n = math.floor((w - 2 * self.cover - db) / s) + 1
        return n * area(db)


def face_moment(f, sol, direction):
    """Mu at the column face (Table 13.2.7.1), max of the two sides, full width."""
    B, L, cx, cy = f.B, f.L, f.cx, f.cy
    if direction == "x":
        r = integrate(sol, cx / 2, B / 2, -L / 2, L / 2, lambda x, y: x - cx / 2)
        l = integrate(sol, -B / 2, -cx / 2, -L / 2, L / 2, lambda x, y: -cx / 2 - x)
    else:
        r = integrate(sol, -B / 2, B / 2, cy / 2, L / 2, lambda x, y: y - cy / 2)
        l = integrate(sol, -B / 2, B / 2, -L / 2, -cy / 2, lambda x, y: -cy / 2 - y)
    return max(r, l)


def one_way_vu(f, sol, direction):
    """Vu at d from the column face (§7.4.3 / 8.4.3), max of the two sides."""
    B, L, cx, cy = f.B, f.L, f.cx, f.cy
    if direction == "x":
        a = cx / 2 + f.dx
        return max(integrate(sol, a, B / 2, -L / 2, L / 2), integrate(sol, -B / 2, -a, -L / 2, L / 2))
    a = cy / 2 + f.dy
    return max(integrate(sol, -B / 2, B / 2, a, L / 2), integrate(sol, -B / 2, B / 2, -L / 2, -a))


def flexure_required(f, Mu, direction):
    """As for Mu (singly reinforced, φ = 0.9) — None if the section is too thin."""
    b, d = (f.L, f.dx) if direction == "x" else (f.B, f.dy)
    if Mu <= 0:
        return 0.0
    Rn = Mu / (0.9 * b * d * d)
    disc = 1 - 2 * Rn / (0.85 * f.fc)
    if disc <= 0:
        return None
    return 0.85 * f.fc / f.fy * (1 - math.sqrt(disc)) * b * d


def flexure_check(f, Mu, direction, As):
    b, d = (f.L, f.dx) if direction == "x" else (f.B, f.dy)
    a = As * f.fy / (0.85 * f.fc * b)
    c = a / beta1(f.fc)
    eps_t = 0.003 * (d - c) / c if c > 0 else 1.0
    phi = phi_tied(eps_t, f.fy / 200000.0)
    phiMn = phi * As * f.fy * (d - a / 2)
    As_min = 0.0018 * b * f.h                                   # 8.6.1.1 (all grades)
    return {"b": b, "d": d, "As": As, "a": a, "eps_t": eps_t, "phi": phi, "phiMn": phiMn, "Mu": Mu,
            "As_min": As_min, "ok": phiMn >= Mu * (1 - 1e-9) and As >= As_min * (1 - 1e-9)}


def one_way_check(f, Vu, direction, As):
    """Table 22.5.5.1(c) — footing without stirrups (Av < Av,min); λs = 1 (§13.2.6.2)."""
    b, d = (f.L, f.dx) if direction == "x" else (f.B, f.dy)
    rho = As / (b * d)
    sq = min(math.sqrt(f.fc), SQRT_FC_MAX)
    Vc = min(0.66 * rho ** (1 / 3) * sq * b * d, 0.42 * sq * b * d)
    return {"b": b, "d": d, "rho": rho, "Vc": Vc, "phiVc": PHI_V * Vc, "Vu": Vu,
            "ok": Vu <= PHI_V * Vc * (1 + 1e-9)}


def punching(f, sol, Pu, Mux, Muy, alpha_s=40):
    """§22.6 with moment transfer §8.4.4.2; λs = 1 for footings (§13.2.6.2)."""
    d = f.d
    b1x, b1y = f.cx + d, f.cy + d                     # sides of the critical section
    bo = 2 * (b1x + b1y)
    Vu = Pu - integrate(sol, -b1x / 2, b1x / 2, -b1y / 2, b1y / 2)
    vuv = Vu / (bo * d)

    def transfer(M, b1, b2):                           # b1 ∥ direction of the moment arm
        gf = 1.0 / (1.0 + (2.0 / 3.0) * math.sqrt(b1 / b2))
        Jc = d * b1 ** 3 / 6 + b1 * d ** 3 / 6 + d * b2 * b1 ** 2 / 2
        return (1 - gf) * abs(M) * (b1 / 2) / Jc, 1 - gf

    vMy, gvx = transfer(Muy, b1x, b1y)                 # My → stresses vary along x
    vMx, gvy = transfer(Mux, b1y, b1x)
    vu = vuv + vMy + vMx
    beta = max(f.cx, f.cy) / min(f.cx, f.cy)
    sq = min(math.sqrt(f.fc), SQRT_FC_MAX)
    vc = min(0.33, 0.17 * (1 + 2 / beta), 0.083 * (2 + alpha_s * d / bo)) * sq   # Table 22.6.5.2
    return {"d": d, "bo": bo, "Vu": Vu, "vuv": vuv, "vM": vMy + vMx, "gv": (gvx, gvy), "vu": vu,
            "vc": vc, "phivc": PHI_V * vc, "beta": beta, "ok": vu <= PHI_V * vc * (1 + 1e-9)}


def bearing(f, Pu, fc_col, Ag_col):
    """§22.8 / §16.3.3 — column on footing, concentric frustum 1:2."""
    A1 = f.cx * f.cy
    k = min(f.B / f.cx, f.L / f.cy, (f.cx + 4 * f.h) / f.cx, (f.cy + 4 * f.h) / f.cy, 2.0)
    phi = 0.65                                                         # Table 21.2.1(d)
    Bn_ftg = k * 0.85 * f.fc * A1
    Bn_col = 0.85 * fc_col * A1
    phiBn = phi * min(Bn_ftg, Bn_col)
    As_dowel_bearing = max(0.0, (Pu - phiBn) / (phi * f.fy)) if Pu > phiBn else 0.0
    return {"A1": A1, "sqrtA2A1": k, "phiBn_ftg": phi * Bn_ftg, "phiBn_col": phi * Bn_col,
            "phiBn": phiBn, "ok": Pu <= phiBn, "As_extra": As_dowel_bearing,
            "As_min": 0.005 * Ag_col}                                  # 16.3.4.1


def development(f, direction, fy_spec):
    """Straight bar from the column face to the edge; else a standard hook (§13.2.8, 25.4)."""
    db, s, cant = (f.dbx, f.sx, (f.B - f.cx) / 2) if direction == "x" else (f.dby, f.sy, (f.L - f.cy) / 2)
    clear = (s - db) if s else 2 * db
    good = clear >= 2 * db and f.cover >= db                           # T25.4.2.3, no stirrups
    L = ld_tension(db, fy_spec, f.fc, good=good)
    avail = cant - f.cover
    hook = ldh(db, fy_spec, f.fc)["ldh"]
    return {"ld": L["ld"], "k": L["k"], "avail": avail, "straight_ok": avail >= L["ld"],
            "ldh": hook, "hook_ok": avail >= hook}


def column_tension(si_col, ultimate):
    """True if any factored combo puts the column section in tension at its base
    (uncracked P/A − Mx/Sx − My/Sy < 0) — dowels then need tension development."""
    cx, cy = si_col["cx"], si_col["cy"]
    A, Sx, Sy = cx * cy, cx * cy * cy / 6.0, cy * cx * cx / 6.0
    return any(cb["Pu"] / A - abs(cb.get("Mux") or 0) / Sx - abs(cb.get("Muy") or 0) / Sy < 0 for cb in ultimate)


def dowel_embedment(f, db, fy, As_req=None, As_prov=None, allow_reduction=False, why_not=None, tension=False):
    """ℓdc of the bars entering the footing must fit in its depth (§25.4.9);
    §25.4.10: ℓdc × As,required/As,provided, not below 200 mm, when permitted."""
    full = ldc(db, fy, f.fc)
    ratio = None
    if allow_reduction and As_req and As_prov and As_prov > As_req:
        ratio = As_req / As_prov
    need = max(full * ratio, 200.0) if ratio else full
    avail = f.h - f.cover - f.dbx - f.dby
    out = {"db": db, "ldc_full": full, "ratio": ratio, "ldc": need, "avail": avail, "ok": avail >= need,
           "why_not": why_not, "tension": tension}
    if tension:
        # bars in tension at the column base: 90° hooks resting on the bottom mat (§25.4.3);
        # ψo = 1.0 (side cover in a footing ≥ 6db), ψr = 1.6 (no confining ties assumed)
        hk = ldh(db, fy, f.fc, psi_o=1.0)["ldh"]
        out.update(ldh=hk, hook_ok=avail >= hk, ok=out["ok"] and avail >= hk)
    return out
