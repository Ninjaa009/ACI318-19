#!/usr/bin/env python3
"""Independent tests for slabkit — expected values from the source tables and hand calcs."""
import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from slabkit import coeffs                                           # noqa: E402
from slabkit.strip import (as_required, flexure, choose, shear, h_min_two_way,  # noqa: E402
                           h_min_one_way, crack_smax)
from slabkit.engine import run, to_si, panels, t_beam_I, panel_name  # noqa: E402
from slabkit.report import build                                     # noqa: E402
from slabkit.rcsi import G, KSC, lambda_s                            # noqa: E402

PASS = FAIL = 0


def check(name, got, exp, tol=0.005):
    global PASS, FAIL
    good = got == exp if isinstance(exp, (bool, str, tuple)) or exp is None else abs(got - exp) <= tol * max(1.0, abs(exp))
    PASS += good
    FAIL += not good
    print(f"{'PASS' if good else 'FAIL'}  {name}: got {got!r} expected {exp!r}")


print("== Method 2 coefficients ==")
c = coeffs.two_way(1, 1.0)
check("case 1, m = 1: short = long (0.033 / 0.025)", (c["short"][0], c["short"][2]), (0.033, 0.025))
check("case 1, m = 0.95 interpolates (0.033+0.040)/2", coeffs.two_way(1, 0.95)["short"][0], 0.0365, 1e-9)
check("case 4, m = 0.75: positive (0.056+0.062)/2", coeffs.two_way(4, 0.75)["short"][2], 0.059, 1e-9)
check("m < 0.5 clamps to the 0.5 column", coeffs.two_way(2, 0.3)["short"][0], 0.085, 1e-9)
check("long span constant with m", coeffs.two_way(3, 0.6)["long"], (0.049, 0.025, 0.037))
bad = 0
for case, (nc, nd, pos) in coeffs.SHORT.items():
    for k in range(6):
        if nc is not None and abs(pos[k] - 0.75 * nc[k]) > 0.0025:
            bad += 1
        if nd is not None and abs(nd[k] - 2 / 3 * pos[k]) > 0.0025:
            bad += 1
check("table self-consistency: pos ≈ 0.75 neg-cont, neg-disc ≈ 2/3 pos (all cells)", bad, 0, 0)
check("m = 1 → both beams wS/3", coeffs.beam_load_factors(1.0), (1 / 3, 1 / 3))
check("m = 0.5 → long beam wS/3·(3 − 0.25)/2", coeffs.beam_load_factors(0.5)[1], 2.75 / 6, 1e-12)

print("== Table 6.5.2 (one-way) ==")
check("interior span 1/11, 1/11, 1/16", coeffs.one_way(True, True, 3, 4000), (1 / 11, 1 / 11, 1 / 16))
check("end span, two spans: first interior 1/9", coeffs.one_way(True, False, 2, 4000), (1 / 9, 1 / 24, 1 / 14))
check("end span, > two spans: first interior 1/10", coeffs.one_way(False, True, 3, 4000), (1 / 24, 1 / 10, 1 / 14))
check("span ≤ 3.05 m: 1/12 at all supports", coeffs.one_way(True, False, 2, 2500), (1 / 12, 1 / 12, 1 / 14))
check("single span: wℓ²/8", coeffs.one_way(False, False, 1, 4000)[2], 1 / 8, 1e-12)

print("== strip (b = 1 m) ==")
fc, fy = 24.0, 392.3
Mu, d = 10e6, 80.0
As = as_required(Mu, d, fc, fy)
a = As * fy / (0.85 * fc * 1000)
check("As_req reproduces Mu at φ = 0.9", 0.9 * As * fy * (d - a / 2), Mu, 1e-9)
check("too thin → None", as_required(80e6, 60, fc, fy), None)
r = flexure(Mu, d, 100, fc, fy, 10, 200)
check("As = 78.54·1000/200", r["As"], math.pi * 25 * 1000 / 200, 1e-9)
check("As,min = 0.0018·1000·100", r["As_min"], 180.0, 1e-12)
ch = choose(Mu, lambda db: 100 - 20 - db / 2, 100, fc, fy, [10, 12], 200)
check("choose: spacing is a multiple of 25 and ≤ 2h", (ch["s"] % 25 == 0, ch["s"] <= 200), (True, True))
check("choose: As ≥ As_req", ch["As"] >= ch["As_req"], True)
sh = shear(30e3, 75, 393, fc)
exp = 0.75 * min(0.66 * lambda_s(75) * (393 / 75000) ** (1 / 3) * math.sqrt(fc) * 75000, 0.42 * math.sqrt(fc) * 75000)
check("φVc = 0.75·0.66λs ρ^⅓ √f′c bd", sh["phiVc"], exp, 1e-9)
check("λs = 1 for d = 75 mm", lambda_s(75), 1.0, 1e-12)
h, _ = h_min_two_way(4250, 3750, fy)
check("T8.3.1.2 αfm > 2: ℓn(0.8 + fy/1400)/(36 + 9β)", h, 4250 * (0.8 + fy / 1400) / (36 + 9 * 4250 / 3750), 1e-9)
check("T8.3.1.2 αfm > 2: ≥ 90 mm", h_min_two_way(2000, 2000, fy)[0], 90.0, 1e-12)
h, _ = h_min_two_way(4250, 3750, fy, 1.0)
check("T8.3.1.2 0.2 < αfm ≤ 2: ≥ 125 mm", h, max(4250 * (0.8 + fy / 1400) / (36 + 5 * 4250 / 3750 * 0.8), 125.0), 1e-9)
check("T8.3.1.2 αfm ≤ 0.2 → out of scope", h_min_two_way(4250, 3750, fy, 0.1)[0], None)
check("T7.3.1.1 one end continuous: ℓ/24·(0.4 + fy/700)", h_min_one_way(4000, 1, fy), 4000 / 24 * (0.4 + fy / 700), 1e-9)
check("T7.3.1.1 fy = 420 → no modifier", h_min_one_way(4000, 2, 420.0), 4000 / 28, 1e-12)
check("T24.3.2 fs = 2/3 fy, cc = 20", crack_smax(fy, 20), min(380 * 280 / (2 * fy / 3) - 50, 300 * 280 / (2 * fy / 3)), 1e-9)
I = t_beam_I(250, 500, 100, 0)
check("T-beam I with no flange = bh³/12", I, 250 * 500 ** 3 / 12, 1e-9)
check("flange overhang capped at 4h", t_beam_I(250, 1000, 100, 1) < t_beam_I(250, 1000, 100, 2), True)

print("== floor example (kgf-m) ==")
with open(os.path.join(HERE, "..", "examples", "S1_floor_kgfm.json"), encoding="utf-8") as fh:
    inp = json.load(fh)
res = run(inp)
P = res["panels"]
check("S1 design passes", all(res["status"].values()), True)
check("S1 h = 100 mm", res["h"], 100.0, 1e-12)
check("panel names", (P[(0, 0)]["name"], P[(2, 1)]["name"]), ("AB-12", "BC-34"))
check("corner panel AB-12: case 3", P[(0, 0)]["case"], 3)
check("edge panel AB-23: case 2", P[(1, 0)]["case"], 2)
check("corridor BC-12: one-way (m < 0.5)", P[(0, 1)]["kind"], "one-way")
si = res["si"]
D = 2400 * G * 1e-9 * 100 + 150 * G * 1e-6
L_ = 300 * G * 1e-6
check("wu = max(1.4D, 1.2D + 1.6L)", res["wu"], max(1.4 * D, 1.2 * D + 1.6 * L_), 1e-9)
p = P[(0, 0)]
S = min(4000, 3750 + 200)
Cpos = coeffs.two_way(3, S / min(4500, 4250 + 200))["short"][2]
check("AB-12 short positive Mu = C·wu·S²·1 m", p["M"]["pos"]["y"], Cpos * res["wu"] * S ** 2 * 1000, 1e-9)
e = res["edges"][("x", 1, 0)]
check("shared edge uses the larger of the two panels", e["Mu"], max(s_[2] for s_ in e["sides"]), 1e-12)
b = res["beams"][("y", 0, 0)]
m = p["m"]
check("edge beam A (long) w = wS/3·(3 − m²)/2", b["wu"], res["wu"] * S / 3 * (3 - m * m) / 2, 1e-9)
check("corridor long beam C: wS/2 (c/c)", res["beams"][("y", 0, 2)]["wu"], res["wu"] * 2000 / 2, 1e-9)
check("BC-12 first-interior shear factor 1.15", P[(0, 1)]["shear"][0]["factor"], 1.15, 1e-12)
check("two exterior corners of two-way panels", len(res["corners"]), 2)
check("S&T steel spacing ≤ min(5h, 450)", P[(0, 1)]["bot"]["x"]["s"] <= 450, True)

print("== units, options, modes ==")
si_inp = copy.deepcopy(inp)
si_inp.update(units="SI", materials={"fc": 240 * KSC, "fy": 4000 * KSC},
              loads={"sdl": 150 * G / 1000, "ll": 300 * G / 1000}, gamma_c=2400 * G / 1000)
rs = run(si_inp)
check("SI input gives the same h and wu", (rs["h"], round(rs["wu"], 9)), (res["h"], round(res["wu"], 9)))
big = run(dict(inp, grid={"x": [6.0, 6.0], "y": [6.0, 6.0]}))
hm = max(p_["h_min"] for p_ in big["panels"].values())
check("6 m bays: h = h_min rounded up to 10 mm", big["h"], math.ceil(hm / 10 - 1e-9) * 10, 1e-12)
weak = run(dict(inp, grid={"x": [6.0, 6.0], "y": [6.0, 6.0]}, edge_beams_stiff=False))
check("edge_beams_stiff false → +10 % h_min on edge panels",
      weak["panels"][(0, 0)]["h_min"] / big["panels"][(0, 0)]["h_min"], 1.10, 1e-9)
one = run(dict(inp, grid={"x": [4.0], "y": [4.0]}))
check("single panel: case 5, four corners", (one["panels"][(0, 0)]["case"], len(one["corners"])), (5, 4))
check("single square panel: each beam wS/3", one["beams"][("x", 0, 0)]["wu"], one["wu"] * one["panels"][(0, 0)]["S"] / 3, 1e-9)
miss = run(dict(inp, missing=["AB-23"]))
check("missing panel AB-23 → AB-12 loses continuity (case 4)", miss["panels"][(0, 0)]["case"], 4)
check("missing panel by index", run(dict(inp, missing=[[1, 0]]))["panels"][(0, 0)]["case"], 4)
deep = run(dict(inp, beam_depth=0.5))
check("beam_depth 0.5 m → αfm > 2 on every panel", all(p_["alpha_fm"] > 2 for p_ in deep["panels"].values()), True)
shallow = run(dict(inp, beam_depth=0.25))
check("shallow beams (αfm ≤ 2) → h ≥ 125 mm", shallow["h"] >= 125, True)
check("flat plate (αfm ≤ 0.2) stops", run(dict(inp, alpha_fm=0.1)).get("stopped"), True)
fac = run(dict(inp, factors={"D": 1.4, "L": 1.7}))
check("user factors 1.4D + 1.7L", fac["wu"], 1.4 * D + 1.7 * L_, 1e-9)
chk = run(dict(inp, mode="check", h=100, bars={"bottom": {"db": 10, "s": 200}, "top": {"db": 10, "s": 200}}))
check("check mode: DB10@200 / h 100 passes", all(chk["status"].values()), True)
chk2 = run(dict(inp, mode="check", h=100, bars={"bottom": {"db": 10, "s": 250}, "top": {"db": 10, "s": 200}}))
check("check mode: s = 250 > 2h fails", chk2["status"]["flexure_shear"], False)
check("check mode without bars stops", run(dict(inp, mode="check", h=100)).get("stopped"), True)
rep = build(res)
check("report lists 'ยังไม่ตรวจ'", "ยังไม่ตรวจ" in rep, True)
check("report notes Method 2 is not 318-19 text", "ไม่ใช่ข้อความของ 318-19" in rep, True)
kb = os.path.join(HERE, "..")
refs = sorted(set(x.split()[0] for x in rep.split("_อ้างอิง: ")[1:] for x in x.split("_")[0].split(" · ")))
missing = [r_ for r_ in refs if not os.path.exists(os.path.join(kb, r_))]
check("every cited kb/ and references/ file exists", ", ".join(missing), "")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
