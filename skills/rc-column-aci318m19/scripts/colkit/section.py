"""Step 1 — section, materials, bar layout.  KB: chapter-10 §10.3, chapter-20, chapter-22 §22.2."""
from __future__ import annotations

import math

ES = 200_000.0          # 20.2.2.2
EPS_CU = 0.003          # 22.2.2.1
FY_CAP = 550.0          # Table 22.4.2.1 / 20.2.2.4(a): fy used for strength ≤ 550 MPa
FYT_SHEAR_CAP = 420.0   # Table 20.2.2.4(a): stirrups/ties for shear ≤ 420 MPa


def area(db: float) -> float:
    return math.pi * db * db / 4.0


def beta1(fc: float) -> float:
    """Table 22.2.2.4.3 (SI)."""
    if fc <= 28.0:
        return 0.85
    if fc >= 55.0:
        return 0.65
    return 0.85 - 0.05 * (fc - 28.0) / 7.0


class Column:
    """Rectangle b (along x) × h (along y), origin at the centroid.
    nx bars on each face parallel to x (including corners), ny on each face
    parallel to y (including corners).  cover = clear cover to the tie."""

    def __init__(self, b, h, fc, fy, db, nx, ny, cover=40.0, tie_db=10.0,
                 fyt=None, eps_ty_420=False):
        if nx < 2 or ny < 2:
            raise ValueError("ต้องมีเหล็กอย่างน้อย 2 เส้นต่อด้าน (มุม)")
        self.b, self.h, self.fc = float(b), float(h), float(fc)
        self.fy_spec = float(fy)
        self.fy = min(float(fy), FY_CAP)
        self.fyt = float(fyt if fyt is not None else fy)
        self.db, self.nx, self.ny = float(db), int(nx), int(ny)
        self.cover, self.tie_db = float(cover), float(tie_db)
        self.b1 = beta1(self.fc)
        self.eps_ty = 0.002 if (eps_ty_420 and abs(self.fy - 420) < 1e-6) else self.fy / ES
        self.e = self.cover + self.tie_db + self.db / 2.0       # face to bar centre
        self.bars = self._layout()
        self.Ab = area(self.db)
        self.Ast = self.Ab * len(self.bars)
        self.Ag = self.b * self.h

    def _layout(self):
        e, b, h = self.e, self.b, self.h
        xs = [-b / 2 + e + i * (b - 2 * e) / (self.nx - 1) for i in range(self.nx)]
        ys = [-h / 2 + e + j * (h - 2 * e) / (self.ny - 1) for j in range(self.ny)]
        pts = {(round(x, 9), round(y, 9)) for x in xs for y in (ys[0], ys[-1])}
        pts |= {(round(x, 9), round(y, 9)) for x in (xs[0], xs[-1]) for y in ys}
        return sorted(pts)

    @property
    def corners(self):
        b, h = self.b / 2, self.h / 2
        return [(-b, -h), (b, -h), (b, h), (-b, h)]

    @property
    def clear_x(self):
        """Clear spacing between bars along a face parallel to x."""
        return (self.b - 2 * self.e) / (self.nx - 1) - self.db

    @property
    def clear_y(self):
        return (self.h - 2 * self.e) / (self.ny - 1) - self.db

    @property
    def Po(self):
        """22.4.2.2"""
        return 0.85 * self.fc * (self.Ag - self.Ast) + self.fy * self.Ast

    @property
    def phiPn_max(self):
        """Table 22.4.2.1(a) tied: Pn,max = 0.80Po; φ = 0.65 (compression-controlled)."""
        return 0.65 * 0.80 * self.Po

    @property
    def phiPn_min(self):
        """Pure tension: φ = 0.90, Pn = −fy·Ast."""
        return -0.90 * self.fy * self.Ast

    def label(self):
        return f"{len(self.bars)}-DB{self.db:g} ({self.nx}×{self.ny})"
