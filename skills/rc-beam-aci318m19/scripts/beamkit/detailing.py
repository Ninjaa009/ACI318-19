"""Steps 5–8 — serviceability limits, detailing, seismic beam rules, bar cut-off, development,
integrity.  KB: chapter-09 §9.3.1, §9.7, chapter-24 §24.3, chapter-25, chapter-18 §18.3.2, §18.4.2."""
from __future__ import annotations

import math

from .rcsi import ld_tension, ldh, ldc, lap_tension, lap_compression


def crack_smax(beam, cc):
    """Table 24.3.2 with fs = 2/3 fy (24.3.2.1)."""
    fs = 2.0 * beam.fy_spec / 3.0
    return min(380.0 * 280.0 / fs - 2.5 * cc, 300.0 * 280.0 / fs)


def min_depth(ln, support, fy):
    """Table 9.3.1.1 + 9.3.1.1.1 (normalweight)."""
    div = {"simple": 16.0, "one_end": 18.5, "both_ends": 21.0, "cantilever": 8.0}[support]
    h = ln / div
    return h * (0.4 + fy / 700.0) if abs(fy - 420.0) > 1e-6 else h


def comp_tie_smax(beam, db_comp):
    """9.7.6.4.2–3 / 25.7.2.1: closed ties around compression bars."""
    return min(16 * db_comp, 48 * beam.ds, min(beam.b, beam.h))


def imf_hoop_smax(d, db_min, ds):
    """§18.4.2.4: hoops over 2h from each face, first ≤ 50 mm."""
    return min(d / 4.0, 8 * db_min, 24 * ds, 300.0)


def parabola(ML, Mm, MR, ln):
    """M(x) through (0, ML), (ln/2, Mm), (ln, MR) — uniform-load shape."""
    k = 4.0 * (Mm - (ML + MR) / 2.0) / ln ** 2

    def M(x):
        return ML + (MR - ML) * x / ln + k * x * (ln - x)
    return M


def neg_extent(combos_M, ln, side, cap=0.0, n=400):
    """Distance from the support face over which some combo's hogging moment exceeds `cap`
    (contiguous from the face), using the 3-point parabola of each combo."""
    far = 0.0
    for ML, Mm, MR in combos_M:
        M = parabola(ML, Mm, MR, ln)
        g = lambda xs: -M(xs if side == "left" else ln - xs) - cap        # > 0 while still hogging
        if g(0.0) <= 1e-6:
            continue
        prev = 0.0
        for i in range(1, n + 1):
            xs = ln * i / n
            if g(xs) <= 1e-6:
                lo, hi = prev, xs                                          # refine the crossing
                for _ in range(50):
                    mid = 0.5 * (lo + hi)
                    lo, hi = (mid, hi) if g(mid) > 1e-6 else (lo, mid)
                far = max(far, hi)
                break
            prev = xs
        else:
            far = ln
    return far


def development(beam, db, top, epoxy=None, lam=1.0, good=True):
    L = ld_tension(db, beam.fy_spec, beam.fc, top, epoxy, lam, good)
    return {"ld": L["ld"], "k": L["k"], "psi_t": L["psi_t"], "psi_e": L["psi_e"], "psi_g": L["psi_g"],
            "ldh": ldh(db, beam.fy_spec, beam.fc, lam, bool(epoxy))["ldh"],
            "ldc": ldc(db, beam.fy_spec, beam.fc, lam),
            "lap_A": lap_tension(L["ld"], "A"), "lap_B": lap_tension(L["ld"], "B"),
            "lap_c": lap_compression(db, beam.fy_spec, beam.fc)}
