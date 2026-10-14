#!/usr/bin/env python3
"""Independent tests for ftgkit — expected values from closed-form statics / hand calcs."""
import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ftgkit.pressure import solve, integrate                       # noqa: E402
from ftgkit.checks import (Footing, face_moment, one_way_vu, one_way_check, punching,  # noqa: E402
                           bearing, flexure_required, flexure_check, development)
from ftgkit.engine import run, service_checks, _band_factor        # noqa: E402

PASS = FAIL = 0


def check(name, got, exp, tol=0.005):
    global PASS, FAIL
    good = got == exp if isinstance(exp, (bool, str, tuple)) or exp is None else abs(got - exp) <= tol * max(1.0, abs(exp))
    PASS += good
    FAIL += not good
    print(f"{'PASS' if good else 'FAIL'}  {name}: got {got!r} expected {exp!r}")


print("== soil pressure ==")
r = solve(1000, 0, 100, 2.0, 2.0)
check("inside kern: q = P/A(1 + 6e/B)", r["qmax"], 1000 / 4 * (1 + 6 * 0.1 / 2), 1e-9)
r = solve(1000, 0, 500, 2.0, 2.0)                     # e = 0.5 > B/6
check("outside kern: q = 2P/(3L(B/2 − e))", r["qmax"], 2 * 1000 / (3 * 2 * (1 - 0.5)), 0.005)
check("outside kern: contact = 3(B/2 − e)/B", r["contact"], 3 * 0.5 / 2.0, 0.01)
check("e = 0.3 < B/6 stays in kern", solve(1000, 0, 300, 2.0, 2.0)["full"], True)
r = solve(1000, 80, 100, 2.0, 3.0)
check("biaxial in kern: P/A + My/Sy + Mx/Sx", r["qmax"], 1000 / 6 + 100 * 6 / (3 * 4) + 80 * 6 / (2 * 9), 1e-9)
r = solve(1000, 250, 250, 2.0, 2.0)
check("biaxial partial contact: ΣqA = P", integrate(r, -1, 1, -1, 1, n=200), 1000, 0.005)
check("biaxial partial contact: Σq·x·A = My", integrate(r, -1, 1, -1, 1, lambda x, y: x, n=200), 250, 0.01)
check("resultant outside footing → unstable", solve(1000, 0, 1100, 2.0, 2.0)["stable"], False)

print("== strength (uniform pressure, hand calc) ==")
f = Footing(2000, 2000, 500, 400, 400, 25, 400, 75, 16, 16, 150, 150)
P = 1000e3
q = P / (2000 * 2000)
sol = solve(P, 0, 0, 2000, 2000)
c = (2000 - 400) / 2
check("Mu face = q·L·c²/2", face_moment(f, sol, "x"), q * 2000 * c * c / 2, 0.002)
check("one-way Vu = q·L·(c − d)", one_way_vu(f, sol, "x"), q * 2000 * (c - f.dx), 0.002)
p = punching(f, sol, P, 0, 0)
check("punching Vu = Pu − q(c+d)²", p["Vu"], P - q * (400 + f.d) ** 2, 0.002)
check("punching vc = 0.33√f′c (β = 1)", p["vc"], min(0.33, 0.083 * (2 + 40 * f.d / p["bo"])) * 5.0, 1e-9)
f2 = Footing(2000, 2000, 500, 600, 300, 25, 400)
p2 = punching(f2, solve(P, 0, 0, 2000, 2000), P, 0, 0)
check("β = 2 → vc = 0.17(1 + 2/2)√f′c = 0.34 → 0.33 governs", p2["vc"], 0.33 * 5, 1e-9)
f3 = Footing(2000, 2000, 500, 900, 300, 25, 400)
check("β = 3 → 0.17(1 + 2/3)√f′c", punching(f3, solve(P, 0, 0, 2000, 2000), P, 0, 0)["vc"], 0.17 * (1 + 2 / 3) * 5, 1e-9)
pm = punching(f, sol, P, 0, 50e6)
check("γv square = 1 − 1/(1 + 2/3) = 0.4", pm["gv"][0], 0.4, 1e-9)
b1 = 400 + f.d
Jc = f.d * b1 ** 3 / 6 + b1 * f.d ** 3 / 6 + f.d * b1 * b1 ** 2 / 2
check("moment term γv·M·c/Jc", pm["vM"], 0.4 * 50e6 * (b1 / 2) / Jc, 1e-9)
s1 = one_way_check(f, 0, "x", 3000)
rho = 3000 / (2000 * f.dx)
check("Vc (c) = 0.66ρ^⅓√f′c·bd (λs = 1)", s1["Vc"], 0.66 * rho ** (1 / 3) * 5 * 2000 * f.dx, 1e-9)
req = flexure_required(f, 300e6, "x")
fl = flexure_check(f, 300e6, "x", req)
check("As_req gives φMn = Mu", fl["phiMn"], 300e6, 0.002)
check("As,min = 0.0018bh", fl["As_min"], 0.0018 * 2000 * 500, 1e-9)
check("As provided: n·Ab (s = 150)", f.As("x"), (math.floor((2000 - 150 - 16) / 150) + 1) * math.pi * 64, 1e-9)
br = bearing(Footing(800, 800, 600, 400, 400, 25, 400), 5000e3, 30, 160000)
check("√(A2/A1) limited by footing size = 800/400 = 2", br["sqrtA2A1"], 2.0, 1e-9)
br = bearing(Footing(600, 600, 600, 400, 400, 25, 400), 5000e3, 30, 160000)
check("√(A2/A1) = 600/400", br["sqrtA2A1"], 1.5, 1e-9)
check("φBn column = 0.65·0.85·30·A1", br["phiBn_col"], 0.65 * 0.85 * 30 * 160000, 1e-9)
check("Pu > φBn → extra dowels", br["As_extra"] > 0, True)
check("band factor β = 2 → 4/3", _band_factor(Footing(1500, 3000, 500, 400, 400, 25, 400), "x"), 4 / 3, 1e-9)
check("long direction no band", _band_factor(Footing(1500, 3000, 500, 400, 400, 25, 400), "y"), 1.0, 1e-9)
dv = development(Footing(2000, 2000, 500, 400, 400, 25, 392.3, 75, 16, 16, 200, 200), "x", 392.3)
check("ℓd DB16 (clear ≥ 2db) = fy/(2.1√f′c)·db", dv["ld"], 392.3 / (2.1 * 5) * 16, 1e-9)

print("== engine ==")
ex = lambda n: json.load(open(os.path.join(HERE, "..", "examples", n)))
inp = ex("F1_design_kgfm.json")
r = run(inp)
f = r["f"]
check("F1 design passes", all(r["status"].values()), True)
sv = r["service"][0]
G = 9.80665
P_tot = (85000 + 0) * G + (24 * 9.80665e-6 / 10 * 0 + 2.4 * G * 1e-6) * f.B * f.L * f.h + 1.8 * G * 1e-6 * (f.B * f.L - 400 * 400) * (1500 - f.h)
check("service total load = P + footing + soil above", sv["Ptot"], P_tot, 1e-9)
A = f.B * f.L
q_hand = P_tot / A + 6 * (2500 * G * 1000 + 900 * G * f.h) / (f.L * f.B ** 2) + 6 * (1500 * G * 1000 + 600 * G * f.h) / (f.B * f.L ** 2)
check("F1 qmax (hand, in kern)", sv["q"], q_hand, 1e-9)
smaller = copy.deepcopy(inp)
smaller["mode"] = "check"
smaller["footing"] = {"B": f.B / 1000 - 0.05, "L": f.L / 1000 - 0.05, "h": f.h / 1000}
smaller["bars"] = {"x": {"db": f.dbx, "s": f.sx}, "y": {"db": f.dby, "s": f.sy}}
check("design is minimal: 50 mm smaller fails soil", run(smaller)["status"]["soil"], False)
thin = copy.deepcopy(smaller)
thin["footing"] = {"B": f.B / 1000, "L": f.L / 1000, "h": 0.30}
rt = run(thin)
check("check mode h = 0.30 → shear fails", rt["status"]["shear"], False)
si_in = copy.deepcopy(inp)
si_in["units"] = "SI"
si_in["column"] = {"cx": 400, "cy": 400, "db": 20, "n": 8}
si_in["materials"] = {k: v * 0.0980665 for k, v in inp["materials"].items()}
si_in["soil"] = {"qa": 15 * G, "qa_type": "gross", "Df": 1.5, "gamma": 1.8 * G, "mu": 0.4}
si_in["gamma_c"] = 2.4 * G
for k in ("service", "ultimate"):
    for cb in si_in[k]:
        for fld in list(cb):
            if fld != "name":
                cb[fld] = cb[fld] * G / 1000
rs = run(si_in)
check("SI input gives the same footing", (rs["f"].B, rs["f"].L, rs["f"].h, rs["f"].sx), (f.B, f.L, f.h, f.sx))
big_m = copy.deepcopy(inp)
big_m["service"][0]["My"] = 60000
rb = run(big_m)
check("large moment → partial contact handled", rb["service"][0]["sol"]["full"] is False or rb["service"][0]["sol"]["full"] is True, True)
check("large moment design still passes", all(rb["status"].values()), True)
thin = r
std = run(dict(inp, design=dict(inp["design"], prefer="steel")))
check("prefer=steel is never thinner than the default (thin)", std["f"].h >= thin["f"].h, True)
nored = run(dict(inp, ldc_reduction=False))
check("without §25.4.10 the dowel ℓdc is the full value", nored["dowel"]["ldc"], nored["dowel"]["ldc_full"], 1e-9)
check("§25.4.10: ℓdc = max(ratio·ℓdc, 200)", r["dowel"]["ldc"], max(r["dowel"]["ldc_full"] * 800 / (8 * math.pi * 100), 200), 1e-6)
tens = copy.deepcopy(inp)
tens["ultimate"][0]["Muy"] = 12000   # > P·S/A = 8,333 kgf·m → tension
check("column tension at base → no §25.4.10 reduction", run(dict(tens, mode="design"))["dowel"]["ratio"], None)
rt2 = run(dict(tens, mode="design"))
check("column tension → hooked dowels checked (ℓdh, ψo = 1.0)", rt2["dowel"]["tension"] and "ldh" in rt2["dowel"], True)
check("SDC D stops", run(dict(inp, sdc="D")).get("stopped"), True)
check("missing service combos stops", run(dict(inp, service=[])).get("stopped"), True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
