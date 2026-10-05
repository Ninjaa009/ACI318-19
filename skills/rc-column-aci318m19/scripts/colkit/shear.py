"""Step 6 — shear (two directions, with axial force) and seismic shear demand.
KB: chapter-22 §22.5, chapter-10 §10.6.2, §10.7.6.5, chapter-18 §18.3.3, §18.4.3.1."""
from __future__ import annotations

import math

from .section import FYT_SHEAR_CAP, area
from .pmm import nominal_moment

PHI_V = 0.75            # Table 21.2.1(b)


def lambda_s(d):
    """Eq. 22.5.5.1.3 (SI)."""
    return min(1.0, math.sqrt(2.0 / (1.0 + 0.004 * d)))


def shear_direction(col, direction, Vu, Nu, s, legs, lam=1.0):
    """direction 'y' = shear along y (pairs with Mx): web width b, depth from h.
    legs = tie legs parallel to the shear."""
    bw = col.b if direction == "y" else col.h
    d = (col.h if direction == "y" else col.b) - col.e
    coord = 1 if direction == "y" else 0
    As_t = sum(col.Ab for p in col.bars if p[coord] < -1e-6)              # tension half
    rho_w = As_t / (bw * d)
    fyt = min(col.fyt, FYT_SHEAR_CAP)                                    # 20.2.2.4(a)
    Av = legs * area(col.tie_db)
    Av_min_s = max(0.062 * math.sqrt(col.fc), 0.35) * bw / fyt           # 10.6.2.2
    has_min = Av / s >= Av_min_s * (1 - 1e-9)
    sq = math.sqrt(col.fc) if has_min else min(math.sqrt(col.fc), 8.3)  # 22.5.3.1–2
    axial = min(Nu / (6 * col.Ag), 0.05 * col.fc) if Nu > 0 else Nu / (6 * col.Ag)  # 22.5.5.1.2
    Vc_a = (0.17 * lam * sq + axial) * bw * d                            # Table 22.5.5.1(a)
    Vc_c = (0.66 * lambda_s(d) * lam * rho_w ** (1 / 3) * sq + axial) * bw * d   # (c)
    Vc_max = 0.42 * lam * sq * bw * d                                    # 22.5.5.1.1
    Vc = max(0.0, min(Vc_a if has_min else Vc_c, Vc_max))
    Vc_without = max(0.0, min(Vc_c, Vc_max))
    Vs = Av * fyt * d / s                                                # 22.5.8.5.3
    phiVn = PHI_V * (Vc + Vs)
    needs_min = Vu > 0.5 * PHI_V * Vc_without                            # 10.6.2.1
    s_max = min(d / 2, 600.0) if Vs <= 0.33 * math.sqrt(col.fc) * bw * d else min(d / 4, 300.0)  # 10.7.6.5.2
    section_ok = Vu <= PHI_V * (Vc + 0.66 * math.sqrt(col.fc) * bw * d)  # 22.5.1.2
    checks = {"φVn ≥ Vu": phiVn >= Vu, "§22.5.1.2": section_ok,
              "Av,min (§10.6.2)": (not needs_min) or has_min,
              "s,max (§10.7.6.5.2)": (not needs_min) or s <= s_max + 1e-9}
    return {"dir": direction, "Vu": Vu, "bw": bw, "d": d, "rho_w": rho_w, "Vc": Vc,
            "eq": "(a)" if has_min else "(c)", "capped": (Vc_a if has_min else Vc_c) > Vc_max,
            "Vs": Vs, "phiVn": phiVn, "needs_min": needs_min, "s_max": s_max,
            "fyt": fyt, "Av_min_s": Av_min_s, "checks": checks, "ok": all(checks.values())}


def biaxial(rx, ry):
    """§22.5.1.10–11: if both ratios > 0.5, their sum ≤ 1.5."""
    ux = rx["Vu"] / rx["phiVn"] if rx["phiVn"] > 0 else math.inf
    uy = ry["Vu"] / ry["phiVn"] if ry["phiVn"] > 0 else math.inf
    req = ux > 0.5 and uy > 0.5
    return {"required": req, "sum": ux + uy, "ok": (ux + uy <= 1.5) if req else True}


def seismic_shear_demand(col, axis, Pu_list, lu, system, V_omega=None):
    """OMF §18.3.3 (only if lu ≤ 5c1) and IMF §18.4.3.1: design shear is the
    lesser of (a) 2Mn/lu with Mn (no φ) the largest over the design axial
    forces and (b) shear from combinations with Ω0·E."""
    c1 = col.h if axis == "x" else col.b
    if system == "OMF" and lu > 5 * c1:
        return {"applies": False, "note": f"ℓu = {lu:.0f} mm > 5c1 = {5 * c1:.0f} mm"}
    Mn = max(nominal_moment(col, axis, p) for p in Pu_list)
    V_mn = 2.0 * Mn / lu
    Ve = min(V_mn, V_omega) if V_omega else V_mn
    return {"applies": True, "Mn": Mn, "V_mn": V_mn, "Ve": Ve, "with_omega": bool(V_omega),
            "clause": "18.3.3" if system == "OMF" else "18.4.3.1"}
