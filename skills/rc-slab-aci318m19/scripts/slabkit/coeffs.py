"""Moment coefficients.

Two-way panels (m = S/L ≥ 0.5): "Method 2" coefficient table (ACI 318-63 Appendix A,
Table A3 — also the table in Thai EIT practice).  It is NOT text of ACI 318-19; 318-19
§8.2.1 allows any procedure that satisfies equilibrium and compatibility, and this
classical method is used as such an analysis.  M = C·w·S² per unit width, S = short span.
Self-consistency kept from the source table: positive ≈ 0.75 × negative-continuous,
negative-discontinuous = 2/3 × positive.

One-way panels (m < 0.5): ACI 318-19 Table 6.5.2 coefficients × wu·ℓn².
"""
from __future__ import annotations

M_COLS = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5)

# case → (neg_cont, neg_disc, pos) for the SHORT span at m = 1.0 … 0.5;  long span constant
SHORT = {
    1: ((0.033, 0.040, 0.048, 0.055, 0.063, 0.083), None,
        (0.025, 0.030, 0.036, 0.041, 0.047, 0.062)),
    2: ((0.041, 0.048, 0.055, 0.062, 0.069, 0.085), (0.021, 0.024, 0.027, 0.031, 0.035, 0.042),
        (0.031, 0.036, 0.041, 0.047, 0.052, 0.064)),
    3: ((0.049, 0.057, 0.064, 0.071, 0.078, 0.090), (0.025, 0.028, 0.032, 0.036, 0.039, 0.045),
        (0.037, 0.043, 0.048, 0.054, 0.059, 0.068)),
    4: ((0.058, 0.066, 0.074, 0.082, 0.090, 0.098), (0.029, 0.033, 0.037, 0.041, 0.045, 0.049),
        (0.044, 0.050, 0.056, 0.062, 0.068, 0.074)),
    5: (None, (0.033, 0.038, 0.043, 0.047, 0.053, 0.055),
        (0.050, 0.057, 0.064, 0.072, 0.080, 0.083)),
}
LONG = {1: (0.033, None, 0.025), 2: (0.041, 0.021, 0.031), 3: (0.049, 0.025, 0.037),
        4: (0.058, 0.029, 0.044), 5: (None, 0.033, 0.050)}

CASE_NAME = {1: "แผงภายใน (ต่อเนื่อง 4 ด้าน)", 2: "ไม่ต่อเนื่อง 1 ด้าน", 3: "ไม่ต่อเนื่อง 2 ด้าน",
             4: "ไม่ต่อเนื่อง 3 ด้าน", 5: "ไม่ต่อเนื่อง 4 ด้าน"}


def _interp(row, m):
    m = max(0.5, min(1.0, m))
    for k in range(len(M_COLS) - 1):
        a, b = M_COLS[k], M_COLS[k + 1]
        if b <= m <= a:
            return row[k + 1] + (row[k] - row[k + 1]) * (m - b) / (a - b)
    return row[-1]


def two_way(case, m):
    """→ {'short': (neg_cont, neg_disc, pos), 'long': (...)}; None where not applicable."""
    s = SHORT[case]
    short = tuple(None if r is None else _interp(r, m) for r in s)
    return {"short": short, "long": LONG[case]}


def beam_load_factors(m):
    """Method 2 load on supporting beams per unit length: short-span beams w·S/3,
    long-span beams w·S/3·(3 − m²)/2."""
    return 1.0 / 3.0, (3.0 - m * m) / 6.0


def one_way(cont_a, cont_b, n_spans=3, ln=None):
    """ACI 318-19 Table 6.5.2 for a one-way panel spanning between edges a and b
    (True = continuous).  Discontinuous ends are assumed cast integrally with a spandrel
    beam (1/24).  First interior support: 1/9 for two spans, 1/10 for more.
    Spans ≤ 10 ft (3.05 m) → 1/12 at all supports.  → (neg_a, neg_b, pos)."""
    if not cont_a and not cont_b:
        return 1 / 24, 1 / 24, 1 / 8           # single span: statics wℓ²/8, nominal top steel
    short = ln is not None and ln <= 3048.0
    if cont_a and cont_b:
        neg = 1 / 12 if short else 1 / 11
        return neg, neg, 1 / 16
    neg_c = 1 / 12 if short else (1 / 9 if n_spans == 2 else 1 / 10)
    neg_d = 1 / 12 if short else 1 / 24
    return (neg_c, neg_d, 1 / 14) if cont_a else (neg_d, neg_c, 1 / 14)
