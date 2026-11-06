"""Per-metre strip checks.  KB: chapter-07 §7.3, 7.6, 7.7; chapter-08 §8.3.1.2, 8.6.1, 8.7.2, 8.7.3;
chapter-22 §22.2–22.3, 22.5; chapter-24 §24.3, 24.4.3."""
from __future__ import annotations

import math

from .rcsi import PHI_V, SQRT_FC_MAX, area, beta1, phi_tied, lambda_s

B = 1000.0       # strip width, mm


def as_required(Mu, d, fc, fy):
    """As (mm²/m) for Mu (N·mm per metre); None if the slab is too thin."""
    if Mu <= 0:
        return 0.0
    Rn = Mu / (0.9 * B * d * d)
    disc = 1 - 2 * Rn / (0.85 * fc)
    if disc <= 0:
        return None
    return 0.85 * fc / fy * (1 - math.sqrt(disc)) * B * d


def flexure(Mu, d, h, fc, fy, db, s):
    As = area(db) * B / s
    a = As * fy / (0.85 * fc * B)
    c = a / beta1(fc)
    eps_t = 0.003 * (d - c) / c
    phi = phi_tied(eps_t, fy / 200000.0)
    phiMn = phi * As * fy * (d - a / 2)
    As_min = 0.0018 * B * h                                    # 7.6.1.1 / 8.6.1.1 / 24.4.3.2
    return {"As": As, "phiMn": phiMn, "phi": phi, "eps_t": eps_t, "As_min": As_min,
            "ok": phiMn >= Mu * (1 - 1e-9) and As >= As_min * (1 - 1e-9)}


def choose(Mu, d_of, h, fc, fy, opts, s_max):
    """Lightest bar/spacing (s multiple of 25 mm, 100 … s_max) that passes; d_of(db) → d."""
    best = None
    for db in opts:
        req = as_required(Mu, d_of(db), fc, fy)
        if req is None:
            continue
        need = max(req, 0.0018 * B * h)
        s = math.floor(min(area(db) * B / need, s_max) / 25.0) * 25.0
        if s < 100:
            continue
        As = area(db) * B / s
        cand = (As, -s, db, s, req)
        if best is None or cand < best:
            best = cand
    return best and {"db": best[2], "s": best[3], "As": best[0], "As_req": best[4]}


def shear(Vu, d, As, fc, lam=1.0):
    """One-way, no stirrups: T22.5.5.1(c) with λs (slabs keep λs)."""
    rho = As / (B * d)
    sq = min(math.sqrt(fc), SQRT_FC_MAX)
    Vc = min(0.66 * lambda_s(d) * lam * rho ** (1 / 3) * sq * B * d, 0.42 * lam * sq * B * d)
    return {"Vu": Vu, "Vc": Vc, "phiVc": PHI_V * Vc, "rho": rho, "ok": Vu <= PHI_V * Vc * (1 + 1e-9)}


def h_min_two_way(ln_long, ln_short, fy, alpha_fm=None):
    """Table 8.3.1.2 (SI: 0.8 + fy/1400; 125 mm / 90 mm).  alpha_fm None → assume > 2."""
    beta = ln_long / ln_short
    k = 0.8 + fy / 1400.0
    if alpha_fm is None or alpha_fm > 2.0:
        return max(ln_long * k / (36 + 9 * beta), 90.0), "αfm > 2" + (" (สมมติ — คานแข็ง)" if alpha_fm is None else "")
    if alpha_fm > 0.2:
        return max(ln_long * k / (36 + 5 * beta * (alpha_fm - 0.2)), 125.0), "0.2 < αfm ≤ 2"
    return None, "αfm ≤ 0.2 → ใช้ §8.3.1.1 (พื้นไร้คาน) — นอกขอบเขต"


def h_min_one_way(span, n_cont, fy):
    """Table 7.3.1.1: ℓ/20, ℓ/24, ℓ/28 by continuous ends; × (0.4 + fy/700) when fy ≠ 420."""
    div = {0: 20.0, 1: 24.0, 2: 28.0}[n_cont]
    h = span / div
    return h * (0.4 + fy / 700.0) if abs(fy - 420.0) > 1e-6 else h


def crack_smax(fy, cc):
    """Table 24.3.2 (one-way slabs), fs = 2/3 fy."""
    fs = 2.0 * fy / 3.0
    return min(380.0 * 280.0 / fs - 2.5 * cc, 300.0 * 280.0 / fs)
