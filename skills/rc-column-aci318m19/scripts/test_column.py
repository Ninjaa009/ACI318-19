#!/usr/bin/env python3
"""Regression + independent closed-form tests for column.py.

Run: python3 test_column.py      (exit code 0 = all pass)
C8 values come from the hand-worked example references/example-slender-column.md
(computed separately from the solver). Others use closed-form arithmetic here.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from column import (Section, point, capacity_at, phiPn_max, stability_index,
                    curvature, slenderness, shear_dir, biaxial_shear, detailing,
                    splices, Mn_at_Pn, design_column, report, bar_area,
                    KSC_TO_MPA, G)

RESULTS = []


def check(name, got, exp, tol=0.005):
    ok = abs(got - exp) <= tol * max(1.0, abs(exp))
    RESULTS.append((name, got, exp, ok))


def check_true(name, cond):
    RESULTS.append((name, cond, True, bool(cond)))


S1 = Section(400, 400, 28, 420, 20, 3, 3, 40, 10)

# ---------------------------------------------------------------- C8 slender column S1
check("C8 Ast (mm²)", S1.Ast, 8 * bar_area(20))
check("C8 Q", stability_index(24000e3, 3.2, 900e3, 5000), 0.01707, 0.002)
check("C8 φPn,max (kN)", phiPn_max(S1) / 1e3, 2498.0, 0.001)
sx = slenderness(S1, "x", 1600e3, 90e6, 60e6, 4500, 1.0, 0.6, 6e3, 5000)
sy = slenderness(S1, "y", 1600e3, 30e6, 20e6, 4500, 1.0, 0.6, 10e3, 5000)
check("C8 M1/M2 x (single, from V·L)", sx["M1_M2"], -2 / 3)
check("C8 M1/M2 y (double, from V·L)", sy["M1_M2"], 2 / 3)
check("C8 klu/r", sx["klu_r"], 38.97, 0.001)
check_true("C8 x slender, y not", sx["slender"] and not sy["slender"])
check("C8 Pc (kN)", sx["Pc"] / 1e3, 6464.7, 0.001)
check("C8 δ", sx["delta"], 1.2935, 0.001)
check("C8 Mcx (kN·m)", sx["Mc"] / 1e6, 116.42, 0.001)
c0 = capacity_at(S1, 1600e3, 1e6, 0)
check("C8 φMnx uniaxial at Pu (kN·m)", c0["phiMcap"] / 1e6, 169.5, 0.002)
check("C8 c at Pu (mm)", c0["c"], 267.2, 0.002)
check("C8 ratio top end", capacity_at(S1, 1600e3, 90e6, 30e6)["ratio"], 0.600, 0.003)
check("C8 ratio midheight", capacity_at(S1, 1600e3, sx["Mc"], 30e6)["ratio"], 0.750, 0.003)
check("C8 ratio x only", capacity_at(S1, 1600e3, sx["Mc"], 0)["ratio"], 0.687, 0.003)
ry = shear_dir(S1, "y", 6e3, 1600e3, 250, 2, 420)
check("C8 Vc limited to Vc,max (kN)", ry["Vc"] / 1e3, 302.3, 0.002)
check_true("C8 Vc capped flag", ry["capped"])
check("C8 φVn (kN)", ry["phiVn"] / 1e3, 294.0, 0.002)
d8 = detailing(S1, 250, 20)
check_true("C8 detailing all pass", d8["rho_ok"] and d8["clear_ok"] and d8["s_tie_ok"]
           and d8["tie_ok"] and d8["crossties_ok"])

# ---------------------------------------------------------------- K1 independent uniaxial hand check
# 3 rows of steel, β1 = 0.85, at c from solver: recompute Pn, Mn by hand
c = c0["c"]
a = 0.85 * c
F = 0.85 * 28 * 400 * a
P = F
M = F * (200 - a / 2)
for n, y in ((3, 60), (2, 200), (3, 340)):
    es = 0.003 * (c - y) / c
    fs = max(-420, min(420, 200000 * es)) - (0.85 * 28 if y < a else 0)
    P += n * bar_area(20) * fs
    M += n * bar_area(20) * fs * (200 - y)
check("K1 hand φPn = Pu (kN)", 0.65 * P / 1e3, 1600.0, 0.001)
check("K1 hand φMn (kN·m)", 0.65 * M / 1e6, c0["phiMcap"] / 1e6, 0.001)

# ---------------------------------------------------------------- K2 pure axial & symmetry
p = point(S1, 0.0, 1e6)
check("K2 Pn at c→∞ = Po (kN)", p["Pn"] / 1e3, S1.Po / 1e3, 0.001)
ca = capacity_at(S1, 1000e3, 80e6, 40e6)
cb = capacity_at(S1, 1000e3, 40e6, 80e6)
check("K2 symmetric φMcap(α) = φMcap(90°−α)", ca["phiMcap"], cb["phiMcap"], 0.002)
check("K2 capacity direction = load direction (°)", ca["cap_deg"], ca["load_deg"], 0.002)
# point on surface → ratio 1
pt = point(S1, math.radians(30), 250)
Pu_s = pt["phi"] * pt["Pn"]
cs = capacity_at(S1, Pu_s, pt["phi"] * pt["Mnx"], pt["phi"] * pt["Mny"])
check("K2 point on surface ratio = 1", cs["ratio"], 1.0, 0.003)
check_true("K2 Pu > φPn,max flagged", not capacity_at(S1, 2600e3, 10e6, 0)["ok"])

# ---------------------------------------------------------------- K3 slenderness rules
check("K3 M1=M2=0 → limit 22", slenderness(S1, "x", 500e3, 0, 0, 4500)["limit"], 22.0)
r_dbl = curvature(90e6, 60e6, given="double")[0]
check("K3 double curvature limit capped 40", min(34 + 12 * r_dbl, 40), 40.0)
s_min = slenderness(S1, "x", 1600e3, 5e6, 5e6, 6000, V=0, L=6000)
check("K3 M2,min = Pu(15+0.03h) (kN·m)", s_min["M2min"] / 1e6, 1600 * (15 + 12) / 1e3)
check("K3 Cm = 1.0 when M2,min governs", s_min["Cm"], 1.0, 0)
s_un = slenderness(S1, "x", 2400e3, 50e6, 50e6, 9000, V=0, L=9000)
check_true("K3 Pu ≥ 0.75Pc → unstable", s_un.get("unstable") is True)

# ---------------------------------------------------------------- N1 fyt cap 420 (new)
r50 = shear_dir(S1, "y", 100e3, 0, 150, 2, 490.3)
check("N1 fyt used = 420", r50["fyt_used"], 420.0, 0)
check("N1 Vs uses 420", r50["Vs"], 2 * bar_area(10) * 420 * 340 / 150)

# ---------------------------------------------------------------- N2 shear: tension Nu, Av,min, biaxial
rt = shear_dir(S1, "y", 50e3, -300e3, 150, 2, 420)
check("N2 Nu tension term (MPa)", rt["Nu_term"], -300e3 / (6 * 160000))
rlow = shear_dir(S1, "y", 200e3, 0, 400, 2, 420)
check_true("N2 need Av,min and s > d/2 fails", rlow["need_min"] and not rlow["checks"]["s_10.7.6.5.2"])
bx = {"Vu": 0.6, "phiVn": 1.0}
by = {"Vu": 0.95, "phiVn": 1.0}
check_true("N2 biaxial sum 1.55 > 1.5 fails", not biaxial_shear(bx, by)["ok"])

# ---------------------------------------------------------------- N3 detailing
S12 = Section(300, 300, 24, 420, 12, 2, 2, 40, 10)
d12 = detailing(S12, 200, 20)
check("N3 ρg 4-DB12 in 300×300", d12["rho_g"], 4 * bar_area(12) / 90000)
check_true("N3 ρg < 1% fails", not d12["rho_ok"])
check("N3 s_tie,max = 16db", d12["s_tie_max"], 16 * 12)
W = Section(600, 600, 28, 420, 25, 5, 5, 40, 10)
dw = detailing(W, 200, 20, 0, 0)
check_true("N3 600 col, 5/side, no crossties → fail", not dw["crossties_ok"])
dw2 = detailing(W, 200, 20, 1, 1)
check_true("N3 1 crosstie each way (clear ≤ 150, alternate) → pass", dw2["crossties_ok"])

# ---------------------------------------------------------------- N4 splices (new)
sp = splices(S1, 250, 2, 2)
check("N4 compression lap SD40 DB20", sp["lap_comp"], 0.071 * 420 * 20)
check_true("N4 0.83 factor applies (Ast_tie ≥ 0.0015hs)", sp["factor_083"])
check("N4 ℓd DB20 (ψg 1.0, 2.1)", sp["ld"], 420 / (2.1 * math.sqrt(28)) * 20)
check("N4 Class B = 1.3ℓd", sp["lap_B"], 1.3 * sp["ld"])
S50 = Section(400, 400, 28, 490.3, 25, 3, 3, 40, 10)
sp50 = splices(S50, 250, 2, 2)
check("N4 SD50 compression lap (0.13fy−24)db", sp50["lap_comp"], (0.13 * 490.3 - 24) * 25)
check("N4 SD50 ψg 1.15", sp50["psi_g"], 1.15, 0)

# ---------------------------------------------------------------- N5 end-to-end kgf-m = SI
inp = {"units": "kgf-m", "b": 0.40, "h": 0.40, "fc": 28 / KSC_TO_MPA,
       "fy": 420 / KSC_TO_MPA, "bar_db": 20, "nx": 3, "ny": 3, "cover": 40,
       "tie_db": 10, "tie_s": 250, "lu": 4.5, "L": 5.0,
       "story": {"sumPu": 24000e3 / G, "delta_o": 3.2, "Vus": 900e3 / G, "lc": 5.0},
       "combos": [{"Pu": 1600e3 / G, "Mx_top": 90e6 / (G * 1000), "Mx_bot": 60e6 / (G * 1000),
                   "Vuy": 6e3 / G, "My_top": 30e6 / (G * 1000), "My_bot": 20e6 / (G * 1000),
                   "Vux": 10e3 / G}]}
res = design_column(inp)
check("N5 kgf-m Q", res["Q"], 0.01707, 0.002)
check("N5 kgf-m ratio midheight", res["rows"][0]["ratio"], 0.750, 0.003)
check_true("N5 report renders", "สรุปสถานะ" in report(res))

# ---------------------------------------------------------------- N6 scope stops
sway = dict(inp, story={"sumPu": 24000e3 / G, "delta_o": 15, "Vus": 900e3 / G, "lc": 5.0})
check_true("N6 Q > 0.05 stops", design_column(sway).get("stopped") is True)
check_true("N6 SMF stops", design_column(dict(inp, system="SMF")).get("stopped") is True)

# ---------------------------------------------------------------- N7 §18.3.3 Mn without φ
mn = Mn_at_Pn(S1, "x", 1000e3)
check_true("N7 Mn(no φ) > φMn at same P", mn > capacity_at(S1, 1000e3, 1, 0)["phiMcap"])

# ---------------------------------------------------------------- output
fails = [x for x in RESULTS if not x[3]]
lines = ["| # | การทดสอบ | ได้ | คาดหมาย | ผล |", "|---|---|---|---|---|"]
for i, (n, g, e, ok) in enumerate(RESULTS, 1):
    fmt = (lambda v: f"{v:,.4g}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v))
    lines.append(f"| {i} | {n} | {fmt(g)} | {fmt(e)} | {'✅' if ok else '❌'} |")
print("\n".join(lines))
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed")
sys.exit(1 if fails else 0)
