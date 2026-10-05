"""Step 3 — flexure by strain compatibility.  KB: chapter-22 §22.2–22.3, chapter-21 Table 21.2.2,
chapter-09 §9.3.3, §9.6.1."""
from __future__ import annotations

import math

from .rcsi import ES, EPS_CU, phi_tied


def analyze(beam, tension, compression):
    """tension/compression = [(area, y from own face, n, db)].  Depth is measured from the
    compression face; compression bars use their own y, tension bars use h − y."""
    h, b, fc, fy = beam.h, beam.b, beam.fc, beam.fy
    lay = [(A, y) for A, y, *_ in compression] + [(A, h - y) for A, y, *_ in tension]

    def forces(c):
        a = min(beam.b1 * c, h)
        Cc = 0.85 * fc * b * a
        F = []
        for A, y in lay:
            es = EPS_CU * (c - y) / c
            fs = max(-fy, min(fy, ES * es))                       # 20.2.2.1
            if es > 0 and y <= a:
                fs -= 0.85 * fc                                    # displaced concrete
            F.append(A * fs)
        return Cc, a, F

    lo, hi = 1e-6, 5.0 * h
    for _ in range(200):
        c = 0.5 * (lo + hi)
        Cc, a, F = forces(c)
        if Cc + sum(F) > 0:
            hi = c
        else:
            lo = c
    c = 0.5 * (lo + hi)
    Cc, a, F = forces(c)
    Mn = Cc * (h / 2 - a / 2) + sum(Fi * (h / 2 - y) for Fi, (A, y) in zip(F, lay))
    ten = [(A, h - y) for A, y, *_ in tension]
    At = sum(A for A, _ in ten)
    d = sum(A * y for A, y in ten) / At
    dt = max(y for _, y in ten)
    eps_t = EPS_CU * (dt - c) / c
    phi = phi_tied(eps_t, beam.eps_ty)
    return {"c": c, "a": a, "Mn": Mn, "phi": phi, "phiMn": phi * Mn, "eps_t": eps_t,
            "d": d, "dt": dt, "As": At,
            "tension_ok": eps_t >= beam.eps_ty + 0.003 - 1e-12}            # 9.3.3.1


def as_min(beam, d):
    """9.6.1.2 (fy ≤ 550 in the formula)."""
    fy = min(beam.fy_spec, 550.0)
    return max(0.25 * math.sqrt(beam.fc) / fy, 1.4 / fy) * beam.b * d


def check_face(beam, tension_bars, comp_bars, Mu):
    """Flexure check of one face at one section (Mu ≥ 0 magnitude)."""
    if not tension_bars:
        return {"ok": Mu <= 0, "phiMn": 0.0, "Mu": Mu, "none": True}
    r = analyze(beam, beam.layers(tension_bars), beam.layers(comp_bars) if comp_bars else [])
    amin = as_min(beam, r["d"])
    r.update(Mu=Mu, As_min=amin, ratio=Mu / r["phiMn"] if r["phiMn"] > 0 else math.inf,
             strength_ok=r["phiMn"] >= Mu * (1 - 1e-9),
             As_min_ok=(Mu <= 0) or r["As"] >= amin * (1 - 1e-9))
    r["ok"] = (Mu <= 0) or (r["strength_ok"] and r["tension_ok"] and r["As_min_ok"])
    return r
