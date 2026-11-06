"""Shared ACI 318M-19 SI core for the RC skills (colkit, beamkit).

CANONICAL COPY: skills/_shared/rcsi.py — tools/build_skills.py copies it into each
skill package.  Edit here only, then run the build so both skills stay identical.
Units: N, mm, MPa.  Constants verified against ACI 318M-19 (references/si-constants-318m.md).
"""
from __future__ import annotations

import math

G = 9.80665              # kgf → N
KSC = 0.0980665          # ksc → MPa
ES = 200_000.0           # 20.2.2.2
EPS_CU = 0.003           # 22.2.2.1
FY_CAP = 550.0           # 20.2.2.4(a) / Table 22.4.2.1: fy for strength ≤ 550 MPa
FYT_SHEAR_CAP = 420.0    # Table 20.2.2.4(a): shear reinforcement ≤ 420 MPa
PHI_V = 0.75             # Table 21.2.1(b)
SQRT_FC_MAX = 8.3        # 22.5.3.1, 25.4.1.4
SMALL_BAR = 19.5         # "No. 19 and smaller" (19.1 mm) — DB20 is a larger bar


def area(db):
    return math.pi * db * db / 4.0


def beta1(fc):
    """Table 22.2.2.4.3."""
    if fc <= 28.0:
        return 0.85
    if fc >= 55.0:
        return 0.65
    return 0.85 - 0.05 * (fc - 28.0) / 7.0


def eps_ty(fy, grade420_exception=False):
    """21.2.2.1: εty = fy/Es; Grade 420 may use 0.002."""
    return 0.002 if (grade420_exception and abs(fy - 420.0) < 1e-6) else fy / ES


def phi_tied(eps_t, eps_ty_):
    """Table 21.2.2, other (tied) transverse reinforcement."""
    if eps_t <= eps_ty_:
        return 0.65
    if eps_t >= eps_ty_ + 0.003:
        return 0.90
    return 0.65 + 0.25 * (eps_t - eps_ty_) / 0.003


def lambda_s(d):
    """Eq. 22.5.5.1.3."""
    return min(1.0, math.sqrt(2.0 / (1.0 + 0.004 * d)))


def av_min_s(fc, bw, fyt):
    """Table 9.6.3.4 / 10.6.2.2: max(0.062√f′c, 0.35)·bw/fyt."""
    return max(0.062 * math.sqrt(fc), 0.35) * bw / min(fyt, FYT_SHEAR_CAP)


def s_max_shear(Vs, fc, bw, d):
    """Table 9.7.6.2.2 / 10.7.6.5.2 (nonprestressed): (along length, across width)."""
    if Vs <= 0.33 * math.sqrt(fc) * bw * d:
        return min(d / 2.0, 600.0), min(d, 600.0)
    return min(d / 4.0, 300.0), min(d / 2.0, 300.0)


def psi_g(fy):
    """Table 25.4.2.5."""
    return 1.0 if fy <= 420 + 1e-6 else (1.15 if fy <= 550 + 1e-6 else 1.3)


def ld_tension(db, fy, fc, top=False, epoxy=None, lam=1.0, good=True):
    """Simplified ℓd, Table 25.4.2.3.  good = clear spacing/cover/ties meet row 1."""
    sq = min(math.sqrt(fc), SQRT_FC_MAX)
    pt = 1.3 if top else 1.0
    pe = {"near": 1.5, "other": 1.2}.get(epoxy, 1.0)
    small = db <= SMALL_BAR
    k = (2.1 if small else 1.7) if good else (1.4 if small else 1.1)
    calc = fy * min(pt * pe, 1.7) * psi_g(fy) / (k * lam * sq) * db
    return {"ld": max(calc, 300.0), "k": k, "psi_t": pt, "psi_e": pe, "psi_g": psi_g(fy)}


def ldh(db, fy, fc, lam=1.0, epoxy=False, psi_r=1.6, psi_o=1.25):
    """25.4.3 standard hook; ψr, ψo conservative unless confinement/side cover confirmed."""
    pc = fc / 105.0 + 0.6 if fc < 42.0 else 1.0
    pe = 1.2 if epoxy else 1.0
    sq = min(math.sqrt(fc), SQRT_FC_MAX)
    calc = fy * pe * psi_r * psi_o * pc / (23.0 * lam * sq) * db ** 1.5
    return {"ldh": max(calc, 8 * db, 150.0), "psi_c": pc, "psi_r": psi_r, "psi_o": psi_o}


def ldc(db, fy, fc, lam=1.0):
    """25.4.9.2."""
    sq = min(math.sqrt(fc), SQRT_FC_MAX)
    return max(max(0.24 * fy / (lam * sq), 0.043 * fy) * db, 200.0)


def lap_tension(ld, cls="B"):
    """Table 25.5.2.1."""
    return max((1.0 if cls == "A" else 1.3) * ld, 300.0)


def lap_compression(db, fy, fc):
    """25.5.5.1–25.5.5.2."""
    if fy <= 420 + 1e-6:
        v = 0.071 * fy * db
    elif fy <= 550 + 1e-6:
        v = (0.13 * fy - 24.0) * db
    else:
        return None
    return max(v, 300.0) * (4.0 / 3.0 if fc < 21 else 1.0)


class Fmt:
    """Report formatting: SI value with the kgf-m equivalent when the input was kgf-m."""

    def __init__(self, units):
        self.kgf = units == "kgf-m"

    def F(self, n):
        if math.isinf(n):
            return "∞"
        return f"{n / 1e3:,.1f} kN" + (f" ({n / G / 1e3:,.2f} tf)" if self.kgf else "")

    def M(self, nmm):
        if math.isinf(nmm):
            return "∞"
        return f"{nmm / 1e6:,.1f} kN·m" + (f" ({nmm / G / 1e6:,.2f} tf·m)" if self.kgf else "")

    def S(self, mpa):
        return f"{mpa:.1f} MPa" + (f" ({mpa / KSC:,.0f} ksc)" if self.kgf else "")

    @staticmethod
    def A(mm2):
        return f"{mm2:,.0f} mm² ({mm2 / 100:,.2f} cm²)"


def ok(v):
    return "✅" if v else "❌"


def ref(*items):
    return "\n_อ้างอิง: " + " · ".join(items) + "_\n"
