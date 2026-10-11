"""Soil pressure under a rigid rectangular footing, no tension (step 2 and 4).
Plan axes: x along B, y along L, origin at the footing centre (= column centre).
My (moment about y) → eccentricity ex = My/P along x;  Mx → ey = Mx/P along y.
Moments enter as magnitudes: footing and column are concentric and symmetric."""
from __future__ import annotations

N_GRID = 140


def _cells(B, L, n=N_GRID):
    dx, dy = B / n, L / n
    for i in range(n):
        x = -B / 2 + (i + 0.5) * dx
        for j in range(n):
            yield x, -L / 2 + (j + 0.5) * dy, dx * dy


def solve(P, Mx, My, B, L):
    """→ {q0, gx, gy, qmax, qmin, ex, ey, full, contact, stable}  with q(x,y) = max(0, q0+gx·x+gy·y)."""
    Mx, My = abs(Mx), abs(My)
    if P <= 0:
        return {"stable": False, "reason": "แรงกดสุทธิ ≤ 0 (ฐานถูกยก)"}
    ex, ey = My / P, Mx / P
    A, Ix, Iy = B * L, B * L ** 3 / 12.0, L * B ** 3 / 12.0
    out = {"ex": ex, "ey": ey}
    if ex >= B / 2 or ey >= L / 2 or ex / B + ey / L >= 0.5:
        out.update(stable=False, reason="แรงลัพธ์อยู่นอกฐาน → พลิกคว่ำ")
        return out
    q0, gx, gy = P / A, My / Iy, Mx / Ix
    if 6 * ex / B + 6 * ey / L <= 1.0 + 1e-12:                 # inside the kern
        qmin = q0 - gx * B / 2 - gy * L / 2
        out.update(q0=q0, gx=gx, gy=gy, qmax=q0 + gx * B / 2 + gy * L / 2, qmin=max(qmin, 0.0),
                   full=True, contact=1.0, stable=True)
        return out
    cells = list(_cells(B, L))
    for _ in range(100):                                        # Newton on the contact plane
        S = [0.0] * 3
        J = [[0.0] * 3 for _ in range(3)]
        for x, y, a in cells:
            q = q0 + gx * x + gy * y
            if q > 0:
                v = (1.0, x, y)
                S[0] += q * a; S[1] += q * x * a; S[2] += q * y * a
                for r in range(3):
                    for c in range(3):
                        J[r][c] += v[r] * v[c] * a
        R = [S[0] - P, S[1] - My, S[2] - Mx]
        if max(abs(R[0]) / P, abs(R[1]) / max(My, 1e-9 * P * B), abs(R[2]) / max(Mx, 1e-9 * P * L)) < 1e-9:
            break
        dlt = _solve3(J, [-r for r in R])
        q0, gx, gy = q0 + dlt[0], gx + dlt[1], gy + dlt[2]
    corners = [q0 + gx * sx * B / 2 + gy * sy * L / 2 for sx in (-1, 1) for sy in (-1, 1)]
    contact = sum(a for x, y, a in cells if q0 + gx * x + gy * y > 0) / A
    out.update(q0=q0, gx=gx, gy=gy, qmax=max(corners), qmin=0.0, full=False, contact=contact, stable=True)
    return out


def _solve3(A, b):
    m = [row[:] + [bb] for row, bb in zip(A, b)]
    for i in range(3):
        p = max(range(i, 3), key=lambda r: abs(m[r][i]))
        m[i], m[p] = m[p], m[i]
        for r in range(3):
            if r != i:
                f = m[r][i] / m[i][i]
                for c in range(i, 4):
                    m[r][c] -= f * m[i][c]
    return [m[i][3] / m[i][i] for i in range(3)]


def integrate(sol, x1, x2, y1, y2, f=lambda x, y: 1.0, n=60):
    """∫∫ q(x,y)·f(x,y) dA over [x1,x2]×[y1,y2]."""
    if x2 <= x1 or y2 <= y1:
        return 0.0
    dx, dy = (x2 - x1) / n, (y2 - y1) / n
    s = 0.0
    for i in range(n):
        x = x1 + (i + 0.5) * dx
        for j in range(n):
            y = y1 + (j + 0.5) * dy
            q = sol["q0"] + sol["gx"] * x + sol["gy"] * y
            if q > 0:
                s += q * f(x, y)
    return s * dx * dy
