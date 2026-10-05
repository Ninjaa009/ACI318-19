"""Step 4 — one-way shear with vertical stirrups, by zone.  KB: chapter-22 §22.5, chapter-09 §9.4.3,
§9.6.3, §9.7.6.2, chapter-21 (φ = 0.75)."""
from __future__ import annotations

import math

from .rcsi import FYT_SHEAR_CAP, PHI_V, SQRT_FC_MAX, area, av_min_s, lambda_s, s_max_shear


def vc(beam, d, As, has_min, eq="a", lam=1.0):
    """Table 22.5.5.1 (Nu = 0)."""
    bw = beam.b
    rho = As / (bw * d)
    sq = math.sqrt(beam.fc) if has_min else min(math.sqrt(beam.fc), SQRT_FC_MAX)  # 22.5.3.1–2
    va = 0.17 * lam * sq * bw * d
    vb = 0.66 * lam * rho ** (1 / 3) * sq * bw * d
    vcc = 0.66 * lambda_s(d) * lam * rho ** (1 / 3) * sq * bw * d
    vmax = 0.42 * lam * sq * bw * d                                               # 22.5.5.1.1
    if has_min:
        val, used = {"a": (va, "(a)"), "b": (vb, "(b)"), "max": max((va, "(a)"), (vb, "(b)"))}[eq]
    else:
        val, used = vcc, "(c)"
    return {"Vc": min(val, vmax), "eq": used, "capped": val > vmax, "rho_w": rho,
            "lambda_s": lambda_s(d)}


def exempt_9631(beam, integral_slab=False, tf=None):
    """Table 9.6.3.1 geometric exemptions."""
    h, bw = beam.h, beam.b
    if h <= 250.0:
        return "h ≤ 250 mm"
    if integral_slab and tf and h <= max(2.5 * tf, 0.5 * bw) and h <= 600.0:
        return "หล่อเป็นเนื้อเดียวกับพื้น h ≤ max(2.5tf, 0.5bw) และ ≤ 600 mm"
    return None


def zone(beam, Vu, d, As, ds, legs, s, eq="a", lam=1.0, exempt=None, s_extra=None):
    """Check one stirrup zone.  s_extra = (limit, reason) from other clauses."""
    fyt = min(beam.fyt, FYT_SHEAR_CAP)                                    # 20.2.2.4(a)
    bw = beam.b
    Av = legs * area(ds)
    amin = av_min_s(beam.fc, bw, fyt)
    has_min = Av / s >= amin * (1 - 1e-9)
    trig = PHI_V * 0.083 * lam * math.sqrt(beam.fc) * bw * d              # 9.6.3.1
    V = vc(beam, d, As, has_min, eq, lam)
    Vs = Av * fyt * d / s                                                 # 22.5.8.5.3
    phiVn = PHI_V * (V["Vc"] + Vs)
    s_long, s_trans = s_max_shear(Vs, beam.fc, bw, d)
    leg_sp = (bw - 2 * beam.cover - ds) / (legs - 1) if legs > 1 else math.inf
    need_min = Vu > trig and not (exempt and Vu <= PHI_V * V["Vc"])
    sec = PHI_V * (V["Vc"] + 0.66 * math.sqrt(beam.fc) * bw * d)          # 22.5.1.2
    checks = {"φVn ≥ Vu": phiVn >= Vu * (1 - 1e-9),
              "§22.5.1.2 ขนาดหน้าตัด": Vu <= sec,
              "Av ≥ Av,min (§9.6.3)": (not need_min) or has_min,
              "s ตามยาว (T9.7.6.2.2)": s <= s_long + 1e-9,
              "ระยะขาตามขวาง (T9.7.6.2.2)": leg_sp <= s_trans + 1e-9}
    if s_extra:
        lim, why = s_extra
        checks[f"s ≤ {lim:.0f} ({why})"] = s <= lim + 1e-9
    return {"Vu": Vu, "d": d, "Av": Av, "s": s, "legs": legs, "ds": ds, "fyt": fyt,
            "Av_min_s": amin, "has_min": has_min, "trigger": trig, "need_min": need_min,
            "Vc": V["Vc"], "eq": V["eq"], "capped": V["capped"], "Vs": Vs, "phiVn": phiVn,
            "s_long": s_long, "s_trans": s_trans, "leg_sp": leg_sp, "section_limit": sec,
            "checks": checks, "ok": all(checks.values()),
            "ratio": Vu / phiVn if phiVn > 0 else math.inf}


def design_zone(beam, Vu, d, As, ds, legs_min, eq="a", lam=1.0, exempt=None, s_extra=None,
                step=25.0, s_floor=75.0):
    """Largest spacing (multiple of 25 mm, ≥ 75 mm) that passes; add legs if needed.
    Always provides at least nominal stirrups (closed, to restrain compression bars)."""
    for legs in range(legs_min, 7):
        s = math.floor(600.0 / step) * step
        while s >= s_floor:
            z = zone(beam, Vu, d, As, ds, legs, s, eq, lam, exempt, s_extra)
            if z["ok"]:
                return z
            s -= step
    return zone(beam, Vu, d, As, ds, legs_min, s_floor, eq, lam, exempt, s_extra) | {"failed": True}
