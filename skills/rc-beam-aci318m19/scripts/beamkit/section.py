"""Step 1 — section, materials, bar layers.  KB: chapter-09 §9.2, chapter-20, chapter-25 §25.2."""
from __future__ import annotations

from .rcsi import FY_CAP, area, beta1, eps_ty

LAYER_GAP = 25.0        # 25.2.2: clear distance between layers ≥ 25 mm


class Beam:
    def __init__(self, b, h, fc, fy, fyt=None, cover=40.0, ds=10.0, dagg=20.0, g420=False):
        self.b, self.h, self.fc = float(b), float(h), float(fc)
        self.fy_spec = float(fy)
        self.fy = min(float(fy), FY_CAP)
        self.fyt = float(fyt if fyt is not None else fy)
        self.cover, self.ds, self.dagg = float(cover), float(ds), float(dagg)
        self.b1 = beta1(self.fc)
        self.eps_ty = eps_ty(self.fy, g420)
        self.Ag = self.b * self.h

    def clear_min(self, db):
        """25.2.1: max(25, db, 4/3 dagg)."""
        return max(25.0, db, 4.0 / 3.0 * self.dagg)

    def per_layer(self, db):
        """Bars that fit in one layer."""
        sc = self.clear_min(db)
        w = self.b - 2 * (self.cover + self.ds)
        return max(2, int((w + sc) // (db + sc)))

    def layers(self, bars):
        """bars = [[n, db], ...] outermost layer first → [(area, y from that face, n, db)]."""
        out, y, prev = [], self.cover + self.ds, None
        for n, db in bars:
            y += db / 2.0 if prev is None else prev / 2.0 + LAYER_GAP + db / 2.0
            out.append((n * area(db), y, n, db))
            prev = db
        return out

    def spacing_outer(self, bars):
        """c/c spacing of the outer layer (for crack control) and clear spacing."""
        n, db = bars[0]
        w = self.b - 2 * (self.cover + self.ds) - db
        cc = w / (n - 1) if n > 1 else float("inf")
        return cc, cc - db


def As(bars):
    return sum(n * area(db) for n, db in bars)


def label(bars):
    return " + ".join(f"{n}-DB{db:g}" for n, db in bars) if bars else "—"


def split(n, db, beam, max_layers=2):
    """n bars of one size → layers (fill the outer layer first). None if they do not fit."""
    m = beam.per_layer(db)
    if n > m * max_layers:
        return None
    out = []
    while n > 0:
        k = min(n, m)
        out.append([k, db])
        n -= k
    return out
