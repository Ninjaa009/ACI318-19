"""Steps 7–9 — reinforcement limits, ties, IMF end zones, splices, joints, footing.
KB: chapter-10 §10.6–10.7, chapter-25 §25.2, 25.4, 25.5, 25.7.2, chapter-18 §18.4.3,
chapter-15 §15.3, 15.5, chapter-16 §16.3.4."""
from __future__ import annotations

import math

from .section import area

SMALL_BAR = 19.5        # "No. 19 and smaller" (19.1 mm); DB20 counts as a larger bar


def longitudinal_limits(col, dagg=20.0, rho_max=0.08):
    rho = col.Ast / col.Ag
    clear_min = max(40.0, 1.5 * col.db, 4.0 / 3.0 * dagg)                # 25.2.3
    clear = min(col.clear_x, col.clear_y)
    return {"rho": rho, "rho_ok": 0.01 - 1e-12 <= rho <= rho_max + 1e-12,  # 10.6.1.1
            "rho_max": rho_max, "n": len(col.bars), "n_ok": len(col.bars) >= 4,  # 10.7.3.1
            "clear": clear, "clear_min": clear_min, "clear_ok": clear >= clear_min - 1e-9}


def supported_interior(m, clear):
    """§25.7.2.3: corners and alternate bars supported; an unsupported bar may
    be at most 150 mm clear from a supported one.  m = interior bars on a face."""
    if m <= 0:
        return 0
    return m if clear > 150.0 else m // 2


def tie_limits(col, s):
    tie_min = 10.0 if col.db <= 32.0 else 12.0                           # 25.7.2.2
    s_max = min(16 * col.db, 48 * col.tie_db, min(col.b, col.h))         # 25.7.2.1
    need_y = supported_interior(col.nx - 2, col.clear_x)   # crossties running in y
    need_x = supported_interior(col.ny - 2, col.clear_y)   # crossties running in x
    return {"tie_min": tie_min, "tie_ok": col.tie_db >= tie_min - 0.6,   # DB10 ≈ No.10 (9.5 mm)
            "s": s, "s_max": s_max, "s_ok": s <= s_max + 1e-9,
            "crossties_y": need_y, "crossties_x": need_x}


def imf_end_zone(col, lu, so):
    """§18.4.3.3–18.4.3.4 (SI from 8 in., 6 in., 18 in.)."""
    so_bar = min(8 * col.db, 200.0) if col.fy_spec <= 420 + 1e-6 else min(6 * col.db, 150.0)
    so_max = min(so_bar, 0.5 * min(col.b, col.h))
    lo = max(lu / 6.0, max(col.b, col.h), 450.0)
    return {"so": so, "so_max": so_max, "so_ok": so <= so_max + 1e-9,
            "lo": lo, "first": so_max / 2.0}


def psi_g(fy):
    """Table 25.4.2.5: Grade 280/420 → 1.0, 550 → 1.15, 690 → 1.3."""
    return 1.0 if fy <= 420 + 1e-6 else (1.15 if fy <= 550 + 1e-6 else 1.3)


def splices(col, s, legs_x, legs_y):
    fy, db = col.fy_spec, col.db
    sq = min(math.sqrt(col.fc), 8.3)                                     # 25.4.1.4
    k = 2.1 if db <= SMALL_BAR else 1.7                                  # Table 25.4.2.3 (ties ≥ code min)
    ld = max(fy * psi_g(fy) / (k * sq) * db, 300.0)                      # ψt = ψe = 1.0
    if fy <= 420 + 1e-6:
        lsc = 0.071 * fy * db                                            # 25.5.5.1(a)
    elif fy <= 550 + 1e-6:
        lsc = (0.13 * fy - 24.0) * db                                    # 25.5.5.1(b)
    else:
        lsc = None
    if lsc is not None:
        lsc = max(lsc, 300.0) * (4.0 / 3.0 if col.fc < 21 else 1.0)      # 25.5.5.2
    At = area(col.tie_db)
    # §10.7.5.2.1(a): legs perpendicular to the dimension considered
    ok_h = legs_x * At >= 0.0015 * col.h * s
    ok_b = legs_y * At >= 0.0015 * col.b * s
    red = bool(lsc) and ok_h and ok_b
    return {"ld": ld, "k": k, "psi_g": psi_g(fy), "class_A": max(ld, 300.0),
            "class_B": max(1.3 * ld, 300.0), "lsc": lsc,
            "lsc_red": max(0.83 * lsc, 300.0) if red else lsc, "reduced": red,
            "Ktr_rule": fy >= 550 - 1e-6}                                # 10.7.1.3


def floor_concrete(fc_col, fc_floor, beams_4_sides=False):
    """§15.5.1."""
    if fc_floor is None:
        return None
    need = fc_floor < 0.7 * fc_col
    eq = 0.75 * min(fc_col, 2.5 * fc_floor) + 0.35 * fc_floor if (need and beams_4_sides) else None
    return {"fc_floor": fc_floor, "ratio": fc_floor / fc_col, "required": need, "fc_equiv": eq}


def footing_dowels(col):
    """§16.3.4.1: As across the column–footing interface ≥ 0.005Ag."""
    req = 0.005 * col.Ag
    return {"As_req": req, "n": max(4, math.ceil(req / col.Ab)), "all_bars_enough": col.Ast >= req}
