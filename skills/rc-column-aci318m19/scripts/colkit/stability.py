"""Steps 3–4 — sway check and slenderness of non-sway columns.
KB: chapter-06 §6.2.5, §6.6.4.3–6.6.4.5."""
from __future__ import annotations

import math

from .section import ES


def stability_index(sum_Pu, delta_o, Vus, lc):
    """Eq. 6.6.4.4.1 — Q ≤ 0.05 → non-sway (§6.6.4.3)."""
    return sum_Pu * delta_o / (Vus * lc)


def end_moment_ratio(Mtop, Mbot, V=None, L=None, curvature=None):
    """M1/M2 with the sign convention of §6.6.4.5.3: negative for single
    curvature, positive for double.  Curvature from user input, else from
    shear equilibrium (no load along the member): |V|·L ≈ |Mt| + |Mb| → double."""
    a, b = abs(Mtop), abs(Mbot)
    M2, M1 = max(a, b), min(a, b)
    if M2 == 0:
        return -1.0, "M1 = M2 = 0 → ใช้ M1/M2 = −1 (เผื่อปลอดภัย)"
    r = M1 / M2
    if curvature in ("single", "double"):
        return (r if curvature == "double" else -r), f"ผู้ใช้ระบุ{'โค้งสองทาง' if curvature == 'double' else 'โค้งทางเดียว'}"
    if V is not None and L:
        vl = abs(V) * L
        if abs(vl - (a + b)) < abs(vl - abs(a - b)):
            return r, f"|V|·L ≈ |Mt| + |Mb| → โค้งสองทาง"
        return -r, f"|V|·L ≈ ||Mt| − |Mb|| → โค้งทางเดียว"
    return -r, "ไม่มีข้อมูลทิศการดัด → สมมติโค้งทางเดียว (เผื่อปลอดภัย)"


def slenderness(col, axis, Pu, Mtop, Mbot, lu, k=1.0, beta_dns=0.6, V=None, L=None,
                curvature=None, ei="a", r_rule="sqrt", transverse_load=False):
    depth = col.h if axis == "x" else col.b
    width = col.b if axis == "x" else col.h
    Ig = width * depth ** 3 / 12.0
    r = math.sqrt(Ig / col.Ag) if r_rule == "sqrt" else 0.3 * depth      # 6.2.5.2
    m_ratio, how = end_moment_ratio(Mtop, Mbot, V, L, curvature)
    klr = k * lu / r
    limit = min(34.0 + 12.0 * m_ratio, 40.0)                             # 6.2.5.1(b),(c)
    M2 = max(abs(Mtop), abs(Mbot))
    out = {"axis": axis, "r": r, "klr": klr, "m_ratio": m_ratio, "how": how,
           "limit": limit, "slender": klr > limit, "M2": M2, "Mc": M2, "delta": 1.0}
    if not out["slender"]:
        return out
    Ec = 4700.0 * math.sqrt(col.fc)                                       # 19.2.2.1(b)
    if ei == "b":
        Ise = sum(col.Ab * ((y if axis == "x" else x) ** 2) for x, y in col.bars)
        EI = (0.2 * Ec * Ig + ES * Ise) / (1 + beta_dns)                  # 6.6.4.4.4(b)
    else:
        EI = 0.4 * Ec * Ig / (1 + beta_dns)                               # 6.6.4.4.4(a)
    Pc = math.pi ** 2 * EI / (k * lu) ** 2                                # 6.6.4.4.2
    M2min = Pu * (15.0 + 0.03 * depth)                                    # 6.6.4.5.4
    Cm = 1.0 if transverse_load else 0.6 - 0.4 * m_ratio                  # 6.6.4.5.3
    M2d = M2
    if M2 < M2min:
        M2d, Cm = M2min, 1.0
    out.update(Ec=Ec, EI=EI, Pc=Pc, Cm=Cm, M2min=M2min)
    if Pu >= 0.75 * Pc:
        out.update(unstable=True, delta=math.inf, Mc=math.inf)
        return out
    delta = max(Cm / (1.0 - Pu / (0.75 * Pc)), 1.0)                       # 6.6.4.5.2
    Mc = delta * M2d
    out.update(unstable=False, delta=delta, Mc=Mc,
               second_order_ok=Mc <= 1.4 * M2d * (1 + 1e-9))             # 6.2.5.3
    return out
