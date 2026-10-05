#!/usr/bin/env python3
"""Independent tests for colkit.  Expected values come from hand calculation or from a
fiber model written here (not from colkit).  Run: python3 test_column.py"""
import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from colkit.section import Column, beta1                     # noqa: E402
from colkit.pmm import capacity, section_forces, nominal_moment, phi_tied  # noqa: E402
from colkit.stability import slenderness, stability_index, end_moment_ratio  # noqa: E402
from colkit.shear import shear_direction, seismic_shear_demand, lambda_s  # noqa: E402
from colkit.detailing import (splices, imf_end_zone, floor_concrete, footing_dowels,  # noqa: E402
                              tie_limits, longitudinal_limits)
from colkit.engine import run, to_si                          # noqa: E402

PASS = FAIL = 0


def check(name, got, exp, tol=0.005):
    global PASS, FAIL
    if isinstance(exp, (bool, str)) or exp is None:
        good = got == exp
    else:
        good = abs(got - exp) <= tol * max(1.0, abs(exp))
    PASS += good
    FAIL += not good
    print(f"{'PASS' if good else 'FAIL'}  {name}: got {got!r} expected {exp!r}")


# ---------------------------------------------------------------- independent fiber model

def fiber(b, h, fc, fy, bars, Ab, theta, c, n=120):
    """Grid of n×n concrete fibres with Whitney block + elastic-plastic bars."""
    nx, ny = math.sin(theta), math.cos(theta)
    b1 = beta1(fc)
    top = max(x * nx + y * ny for x in (-b / 2, b / 2) for y in (-h / 2, h / 2))
    a = b1 * c
    P = Mx = My = 0.0
    dA = (b / n) * (h / n)
    for i in range(n):
        x = -b / 2 + (i + 0.5) * b / n
        for j in range(n):
            y = -h / 2 + (j + 0.5) * h / n
            if top - (x * nx + y * ny) <= a:
                F = 0.85 * fc * dA
                P += F; Mx += F * y; My += F * x
    et = 0.0
    for x, y in bars:
        dep = top - (x * nx + y * ny)
        eps = 0.003 * (c - dep) / c
        fs = max(-fy, min(fy, 200000 * eps))
        if dep <= a:
            fs -= 0.85 * fc
        F = fs * Ab
        P += F; Mx += F * y; My += F * x
        et = max(et, -eps)
    return P, Mx, My, et


def fiber_at_P(col, theta, Pu):
    lo, hi = 1.0, 5 * max(col.b, col.h)
    for _ in range(50):
        c = 0.5 * (lo + hi)
        P, Mx, My, et = fiber(col.b, col.h, col.fc, col.fy, col.bars, col.Ab, theta, c, 80)
        phi = phi_tied(et, col.fy / 200000)
        if phi * P > Pu:
            hi = c
        else:
            lo = c
    return phi * Mx, phi * My


# ---------------------------------------------------------------- S1 hand calculation
print("== S1 400×400 8-DB20, f′c 28, fy 420 (hand calc) ==")
col = Column(400, 400, 28, 420, 20, 3, 3)
check("Ast", col.Ast, 8 * math.pi * 100, 1e-9)
check("φPn,max = 0.52Po", col.phiPn_max / 1e3, 2498.0, 0.001)
check("β1(28)", beta1(28), 0.85, 1e-9)
check("β1(35)", beta1(35), 0.80, 1e-9)
check("β1(56)", beta1(56), 0.65, 1e-9)
check("Q", stability_index(24000e3, 3.2, 900e3, 5000), 0.017067, 0.001)
check("M1/M2 single (V·L = 30 ≈ |90−60|)", end_moment_ratio(90, 60, 6, 5)[0], -2 / 3, 1e-6)
check("M1/M2 double (V·L = 50 ≈ 30+20)", end_moment_ratio(30, 20, 10, 5)[0], 2 / 3, 1e-6)
check("M1 = M2 = 0 → −1", end_moment_ratio(0, 0)[0], -1.0, 1e-9)
sx = slenderness(col, "x", 1600e3, 90e6, 60e6, 4500, V=6e3, L=5000)
check("kℓu/r = 4500/(0.2887·400)", sx["klr"], 38.97, 0.001)
check("limit 34+12(−2/3) = 26", sx["limit"], 26.0, 1e-6)
check("Pc", sx["Pc"] / 1e3, 6464.7, 0.001)
check("Cm = 0.6+0.4·2/3", sx["Cm"], 0.86667, 0.0005)
check("δ", sx["delta"], 1.2935, 0.001)
check("Mc", sx["Mc"] / 1e6, 116.42, 0.001)
sy = slenderness(col, "y", 1600e3, 30e6, 20e6, 4500, V=10e3, L=5000)
check("y not slender (limit 40)", sy["slender"], False)
r = capacity(col, 1600e3, 90e6, 30e6)
check("ratio top", r["ratio"], 0.600, 0.005)
r = capacity(col, 1600e3, 116.42e6, 30e6)
check("ratio mid", r["ratio"], 0.750, 0.005)
r = capacity(col, 1600e3, 169.5e6, 0)
check("uniaxial φMnx at 1600 kN ≈ 169.5", r["ratio"], 1.0, 0.005)
check("c at that point ≈ 267.2", r["c"], 267.2, 0.01)

print("== fiber-model cross-check ==")
for (b, h, db, nx, ny, Pu, th) in [(400, 400, 20, 3, 3, 1600e3, 0.0), (400, 600, 25, 3, 4, 800e3, 0.5),
                                   (500, 500, 25, 4, 4, 300e3, 0.785), (300, 600, 20, 2, 5, 2000e3, 1.2)]:
    cc = Column(b, h, 28, 420, db, nx, ny)
    fx, fy_ = fiber_at_P(cc, th, Pu)
    r = capacity(cc, Pu, fx, fy_)
    check(f"{b}×{h} θ={th}: fiber point lies on colkit surface", r["ratio"], 1.0, 0.015)

print("== symmetry / surface ==")
c2 = Column(500, 500, 30, 420, 25, 4, 4)
a = capacity(c2, 1000e3, 150e6, 60e6)
b = capacity(c2, 1000e3, 60e6, 150e6)
check("square: swap Mx/My same ratio", a["ratio"], b["ratio"], 0.002)
check("sign of moments ignored", capacity(c2, 1000e3, -150e6, 60e6)["ratio"], a["ratio"], 1e-6)
p = capacity(c2, 1000e3, 150e6 / a["ratio"], 60e6 / a["ratio"])
check("scaled load on surface → 1.0", p["ratio"], 1.0, 0.002)
check("Pu > φPn,max → fail", capacity(c2, c2.phiPn_max * 1.01, 0, 0)["ok"], False)
check("φ tension-controlled", phi_tied(0.01, 0.0021), 0.90, 1e-9)
check("φ transition", phi_tied(0.0021 + 0.0015, 0.0021), 0.775, 1e-9)

print("== shear ==")
d = shear_direction(col, "y", 6e3, 1600e3, 250, 2)
check("Vc capped 0.42√28·400·340", d["Vc"] / 1e3, 0.42 * math.sqrt(28) * 400 * 340 / 1e3, 1e-6)
check("φVn S1", d["phiVn"] / 1e3, 294.0, 0.002)
check("λs(d=1000)", lambda_s(1000), math.sqrt(2 / 5), 1e-9)
c3 = Column(400, 400, 28, 500, 20, 3, 3, fyt=500)
check("fyt capped at 420 for shear", shear_direction(c3, "y", 0, 0, 200, 2)["fyt"], 420.0, 1e-9)
d0 = shear_direction(col, "y", 100e3, 0, 600, 2)
Av_min = max(0.062 * math.sqrt(28), 0.35) * 400 / 420
check("Av,min/s", d0["Av_min_s"], Av_min, 1e-9)
check("s=600 → Av < Av,min → eq (c)", d0["eq"], "(c)")

print("== seismic shear / IMF ==")
cI = Column(400, 500, 27.46, 392.3, 16, 3, 4)
Mn_list = [nominal_moment(cI, "x", p) for p in (80e3 * 9.80665, 165e3 * 9.80665, 210e3 * 9.80665)]
dm = seismic_shear_demand(cI, "x", [80e3 * 9.80665, 165e3 * 9.80665, 210e3 * 9.80665], 3000, "IMF")
check("Ve uses largest Mn over Pu", dm["Mn"], max(Mn_list), 1e-9)
check("Ve = 2Mn/ℓu", dm["Ve"], 2 * max(Mn_list) / 3000, 1e-9)
check("Ve limited by Ω0 shear", seismic_shear_demand(cI, "x", [1e6], 3000, "IMF", 50e3)["Ve"], 50e3, 1e-9)
check("OMF ℓu > 5c1 → not applicable", seismic_shear_demand(cI, "x", [1e6], 3000, "OMF")["applies"], False)
check("OMF ℓu ≤ 5c1 → applies", seismic_shear_demand(cI, "x", [1e6], 2400, "OMF")["applies"], True)
z = imf_end_zone(cI, 3000, 125)
check("so = min(8·16, 200, 200)", z["so_max"], 128.0, 1e-9)
check("ℓo = max(500, 500, 450)", z["lo"], 500.0, 1e-9)
c5 = Column(600, 600, 35, 550, 25, 4, 4)
check("Grade 550: so = min(6·25,150,300)", imf_end_zone(c5, 3000, 100)["so_max"], 150.0, 1e-9)
check("ℓo = ℓu/6 when governing", imf_end_zone(c5, 4800, 100)["lo"], 800.0, 1e-9)

print("== detailing / splices ==")
sp = splices(col, 250, 2, 2)
check("DB20 uses 1.7 (bigger-bar row)", sp["k"], 1.7)
check("ℓd DB20", sp["ld"], 420 / (1.7 * math.sqrt(28)) * 20, 1e-9)
check("ℓsc = 0.071·420·20", sp["lsc"], 0.071 * 420 * 20, 1e-9)
check("0.83 applies: 2·78.5 ≥ 0.0015·400·250", sp["reduced"], True)
check("DB16 uses 2.1", splices(Column(400, 400, 28, 420, 16, 3, 3), 200, 2, 2)["k"], 2.1)
cw = Column(300, 800, 28, 420, 20, 2, 6)
spw = splices(cw, 200, 2, 3)        # h side needs 0.0015·800·200 = 240 mm² → 2 legs (157) fail
check("0.83 not applied (legs along x short for h=800)", spw["reduced"], False)
spw2 = splices(cw, 200, 4, 2)       # 4·78.5 = 314 ≥ 240; 2·78.5 ≥ 0.0015·300·200 = 90
check("0.83 applied with 4 legs along x", spw2["reduced"], True)
check("Grade 550 ℓsc = (0.13fy−24)db", splices(c5, 100, 4, 4)["lsc"], (0.13 * 550 - 24) * 25, 1e-9)
check("f′c < 21 → ×4/3", splices(Column(400, 400, 18, 420, 20, 3, 3), 150, 2, 2)["lsc"], 0.071 * 420 * 20 * 4 / 3, 1e-9)
t = tie_limits(Column(600, 600, 28, 420, 20, 6, 6), 200)
check("6 bars/face clear < 150 → 2 crossties each way", (t["crossties_x"], t["crossties_y"]) == (2, 2), True)
check("tie s,max = min(16db,48dt,b)", tie_limits(col, 0)["s_max"], 320.0, 1e-9)
lg = longitudinal_limits(Column(300, 300, 28, 420, 12, 2, 2))
check("ρ < 1% fails", lg["rho_ok"], False)
check("§15.5 0.6 ratio → required", floor_concrete(40, 24, True)["required"], True)
check("§15.5 (c) 0.75·min(40,60)+0.35·24", floor_concrete(40, 24, True)["fc_equiv"], 38.4, 1e-9)
check("dowels 0.005Ag", footing_dowels(col)["As_req"], 800.0, 1e-9)

print("== engine ==")
ex = json.load(open(os.path.join(HERE, "..", "examples", "S1_check_SI.json")))
res = run(ex)
check("S1 worst ratio", res["worst"][0], 0.750, 0.005)
check("S1 all pass", all(res["status"].values()), True)
# kgf-m equivalence: same column expressed in kgf-m
kg = copy.deepcopy(ex)
kg["units"] = "kgf-m"
kg["section"] = {"b": 0.4, "h": 0.4}
kg["materials"] = {k: v / 0.0980665 for k, v in ex["materials"].items()}
kg["joint"] = {"fc_floor": 24 / 0.0980665}
for cb in kg["combos"]:
    for k in ("Pu", "Vux", "Vuy"):
        cb[k] = cb[k] * 1e3 / 9.80665
    for k in ("Mx_top", "Mx_bot", "My_top", "My_bot"):
        cb[k] = cb[k] * 1e3 / 9.80665
kg["story"] = {"sum_Pu": 24000e3 / 9.80665, "delta_o": 3.2, "Vus": 900e3 / 9.80665, "lc": 5.0}
rk = run(kg)
check("kgf-m gives same ratio", rk["worst"][0], res["worst"][0], 1e-6)
check("kgf-m fc_floor converted", rk["floor"]["ratio"], res["floor"]["ratio"], 1e-6)
check("kgf-m Q", rk["Q"], res["Q"], 1e-6)
smf = dict(ex, system="SMF")
check("SMF stops", run(smf).get("stopped"), True)
sw = copy.deepcopy(ex)
sw["story"]["delta_o"] = 12
check("Q > 0.05 stops", run(sw).get("stopped"), True)
dz = copy.deepcopy(ex)
dz["mode"] = "design"
dz.pop("bars")
rd = run(dz)
check("design passes", all(rd["status"].values()), True)
# minimality: every lighter candidate that was tried must have failed
check("design: all lighter tried layouts fail", all(r > 1.0 for _, r in rd["tried"][:-1]), True)
check("design: chosen = last tried", rd["tried"][-1][0], rd["col"].label())
big = copy.deepcopy(dz)
big["combos"][0]["Pu"] = 3500
check("design: impossible → stop", run(big).get("stopped"), True)
imf = json.load(open(os.path.join(HERE, "..", "examples", "IMF_design_kgfm.json")))
ri = run(imf)
check("IMF design passes", all(ri["status"].values()), True)
check("IMF s_end ≤ so,max", ri["ties"]["s_end"] <= ri["imf"]["so_max"], True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
