#!/usr/bin/env python3
"""Independent tests for beamkit.  Expected values are hand calculations or come from a
strip model written here (not from beamkit).  Run: python3 test_beam.py"""
import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from beamkit.section import Beam, split                         # noqa: E402
from beamkit.flexure import check_face, as_min                  # noqa: E402
from beamkit.shear import zone, vc                              # noqa: E402
from beamkit.detailing import crack_smax, min_depth, neg_extent, imf_hoop_smax  # noqa: E402
from beamkit.engine import run, nominal                         # noqa: E402
from beamkit.rcsi import ld_tension, lap_compression, ldh, area  # noqa: E402

PASS = FAIL = 0


def check(name, got, exp, tol=0.005):
    global PASS, FAIL
    if isinstance(exp, (bool, str, list)) or exp is None:
        good = got == exp
    else:
        good = abs(got - exp) <= tol * max(1.0, abs(exp))
    PASS += good
    FAIL += not good
    print(f"{'PASS' if good else 'FAIL'}  {name}: got {got!r} expected {exp!r}")


def strips(b, h, fc, fy, bars, n=3000):
    """Independent strip model: bars = [(area, depth from compression face)] → (Mn, c)."""
    b1 = 0.85 if fc <= 28 else max(0.65, 0.85 - 0.05 * (fc - 28) / 7)

    def resultant(c):
        a = b1 * c
        P = M = 0.0
        for i in range(n):
            y = (i + 0.5) * h / n
            if y <= a:
                F = 0.85 * fc * b * h / n
                P += F
                M += F * (h / 2 - y)
        for A, y in bars:
            eps = 0.003 * (c - y) / c
            fs = max(-fy, min(fy, 200000 * eps)) - (0.85 * fc if y <= a and eps > 0 else 0)
            P += A * fs
            M += A * fs * (h / 2 - y)
        return P, M
    lo, hi = 1.0, h
    for _ in range(60):
        c = 0.5 * (lo + hi)
        if resultant(c)[0] > 0:
            hi = c
        else:
            lo = c
    return resultant(c)[1], c


print("== flexure: hand calc (singly) ==")
bm = Beam(300, 600, 28, 420)
r = check_face(bm, [[4, 20]], [], 200e6)
As_ = 4 * area(20)
d = 600 - 40 - 10 - 10
a = As_ * 420 / (0.85 * 28 * 300)
check("d", r["d"], d, 1e-9)
check("φMn = 0.9As·fy(d − a/2)", r["phiMn"], 0.9 * As_ * 420 * (d - a / 2), 0.002)
check("c = a/β1", r["c"], a / 0.85, 0.002)
check("As,min = max(0.25√fc,1.4)bd/fy", r["As_min"], max(0.25 * math.sqrt(28), 1.4) / 420 * 300 * d, 1e-9)
check("As,min fy capped 550", as_min(Beam(300, 600, 28, 600), 500), max(0.25 * math.sqrt(28), 1.4) / 550 * 300 * 500, 1e-9)

print("== flexure: strip model (doubly, two layers) ==")
for (top, bot, fc) in [([[4, 25], [2, 25]], [[3, 25]], 28), ([[3, 16]], [[5, 20], [2, 20]], 35),
                       ([[2, 12]], [[6, 25], [3, 25]], 24)]:
    bm = Beam(300, 600, fc, 420)
    r = check_face(bm, top, bot, 1.0)
    lay = [(A, y) for A, y, *_ in bm.layers(bot)] + [(A, 600 - y) for A, y, *_ in bm.layers(top)]
    Mn, c = strips(300, 600, fc, 420, lay)
    check(f"Mn {top} vs {bot} f′c{fc}", r["Mn"], Mn, 0.005)
    check(f"c  {top} vs {bot} f′c{fc}", r["c"], c, 0.01)
over = check_face(Beam(300, 500, 21, 420), [[5, 25], [5, 25]], [], 100e6)
check("over-reinforced → εt < εty + 0.003 → fail", over["tension_ok"], False)
check("no demand → ok regardless", check_face(Beam(300, 500, 21, 420), [[5, 25], [5, 25]], [], 0)["ok"], True)

print("== shear ==")
bm = Beam(300, 600, 28, 420)
z = zone(bm, 220e3, 521, 2945, 10, 2, 150)
check("Vc (a) = 0.17√fc·b·d", z["Vc"], 0.17 * math.sqrt(28) * 300 * 521, 1e-9)
check("Vs = Av·fyt·d/s", z["Vs"], 2 * area(10) * 420 * 521 / 150, 1e-9)
check("s,max = d/2", z["s_long"], 521 / 2, 1e-9)
check("trigger = φ0.083√fc·bw·d", z["trigger"], 0.75 * 0.083 * math.sqrt(28) * 300 * 521, 1e-9)
z2 = zone(bm, 50e3, 540, 1473, 10, 2, 1000)   # Av/s = 0.157 < 0.25
check("Av < Av,min → Vc (c) with λs", z2["eq"], "(c)")
check("Vc (c) value", z2["Vc"], 0.66 * math.sqrt(2 / (1 + 0.004 * 540)) * (1473 / (300 * 540)) ** (1 / 3) * math.sqrt(28) * 300 * 540, 1e-6)
z3 = zone(Beam(300, 600, 28, 500, fyt=500), 0, 540, 1473, 10, 2, 200)
check("fyt capped at 420", z3["fyt"], 420.0, 1e-9)
z4 = zone(bm, 500e3, 540, 2945, 12, 4, 75)
check("Vs > 0.33√fc·bw·d → s,max = min(d/4, 300)", z4["s_long"], 135.0, 1e-9)
check("§22.5.1.2 limit", z4["section_limit"], 0.75 * (z4["Vc"] + 0.66 * math.sqrt(28) * 300 * 540), 1e-9)
wide = zone(Beam(700, 600, 28, 420), 100e3, 540, 3000, 10, 2, 200)
check("leg spacing 610 > d → fails transverse limit", wide["checks"]["ระยะขาตามขวาง (T9.7.6.2.2)"], False)

print("== detailing / development ==")
b4 = Beam(300, 600, 27.46, 392.3)
check("crack s,max (fs = 2fy/3, cc 50)", crack_smax(b4, 50), min(380 * 280 / (2 / 3 * 392.3) - 125, 300 * 280 / (2 / 3 * 392.3)), 1e-9)
check("h,min both ends fy 420 = ℓn/21", min_depth(6000, "both_ends", 420), 6000 / 21, 1e-9)
check("h,min × (0.4 + fy/700)", min_depth(6000, "both_ends", 392.3), 6000 / 21 * (0.4 + 392.3 / 700), 1e-9)
check("ℓd DB16 (2.1)", ld_tension(16, 392.3, 27.46)["ld"], 392.3 / (2.1 * math.sqrt(27.46)) * 16, 1e-9)
check("ℓd DB20 (1.7, larger bar)", ld_tension(20, 420, 28)["k"], 1.7)
check("ℓd top bar ψt 1.3", ld_tension(25, 420, 28, top=True)["ld"], 420 * 1.3 / (1.7 * math.sqrt(28)) * 25, 1e-9)
check("ℓd poor spacing → 1.1", ld_tension(25, 420, 28, good=False)["k"], 1.1)
check("ψc f′c < 42", ldh(20, 420, 28)["psi_c"], 28 / 105 + 0.6, 1e-9)
check("lap compression fy 420", lap_compression(25, 420, 28), 0.071 * 420 * 25, 1e-9)
check("IMF hoop s = min(d/4, 8db, 24dt, 300)", imf_hoop_smax(535, 16, 10), 128.0, 1e-9)
check("bars per layer DB25 b300", Beam(300, 600, 28, 420).per_layer(25), 4)
check("split 6-DB25 → 4 + 2", split(6, 25, Beam(300, 600, 28, 420)), [[4, 25], [2, 25]])
# symmetric UDL: M = −wl²/12 at ends, +wl²/24 at mid → inflection at 0.2113 ℓn
w, ln = 30.0, 6000.0
check("inflection point UDL fixed-fixed", neg_extent([(-w * ln ** 2 / 12, w * ln ** 2 / 24, -w * ln ** 2 / 12)], ln, "left"),
      0.21132 * ln, 0.003)

print("== engine ==")
ex = lambda n: json.load(open(os.path.join(HERE, "..", "examples", n)))
b1 = ex("B1_design_kgfm.json")
r1 = run(b1)
check("B1 design passes", all(r1["status"].values()), True)
# minimality of bottom bars: one bar fewer (or next smaller set) must fail midspan
bot = r1["bars"]["mid"]["bot"]
n = sum(k for k, _ in bot)
fewer = split(n - 1, bot[0][1], r1["beam"]) if n > 2 else None
if fewer:
    m = r1["env"]["mid"]["bot"]
    check("B1 bottom is minimal (n−1 fails)", check_face(r1["beam"], fewer, [[2, 16]], m)["ok"], False)
top = r1["bars"]["left"]["top"]
nt = sum(k for k, _ in top)
fewer_t = split(nt - 1, top[0][1], r1["beam"])
check("B1 left top is minimal (n−1 fails)", check_face(r1["beam"], fewer_t, bot, r1["env"]["left"]["top"])["ok"], False)
# kgf-m vs SI equivalence
si = copy.deepcopy(b1)
si["units"] = "SI"
si["section"] = {"b": 300, "h": 600}
si["materials"] = {k: v * 0.0980665 for k, v in b1["materials"].items()}
for cb in si["combos"]:
    for k in ("M_left", "M_mid", "M_right"):
        cb[k] = cb[k] * 9.80665 / 1000
    for k in ("V_left", "V_right"):
        cb[k] = cb[k] * 9.80665 / 1000
r1s = run(si)
check("kgf-m and SI give same bars", r1s["bars"] == r1["bars"], True)
check("kgf-m and SI same φMn", r1s["flex"]["left"]["top"]["phiMn"], r1["flex"]["left"]["top"]["phiMn"], 1e-9)
b2 = run(ex("B2_check_SI.json"))
check("B2 check passes", all(b2["status"].values()), True)
check("B2 left top φMn", b2["flex"]["left"]["top"]["phiMn"] / 1e6, 514.7, 0.002)
deep = copy.deepcopy(b1)
deep["span"]["ln"] = 2.0
check("deep beam stops", run(deep).get("stopped"), True)
smf = dict(b1, system="SMF")
check("SMF stops", run(smf).get("stopped"), True)
rb9 = copy.deepcopy(ex("B2_check_SI.json"))
rb9["stirrups"]["db"] = 9
check("check mode: RB9 flagged (§9.7.6.4)", run(rb9)["status"]["detailing"], False)
d9 = copy.deepcopy(b1)
d9["stirrups"]["db"] = 9
check("design mode: RB9 bumped to DB10", run(d9)["beam"].ds, 10.0, 1e-9)
weak = copy.deepcopy(b1)
for cb in weak["combos"]:
    for k in ("M_left", "M_mid", "M_right"):
        cb[k] *= 4
check("impossible design stops", run(weak).get("stopped"), True)

print("== IMF ==")
r3 = run(ex("B3_IMF_design_kgfm.json"))
check("IMF design passes", all(r3["status"].values()), True)
s3 = r3["shear"]["seismic"]
bm3, bars3 = r3["beam"], r3["bars"]
Mn_l_neg = nominal(bm3, bars3["left"]["top"], bars3["left"]["bot"])
Mn_l_pos = nominal(bm3, bars3["left"]["bot"], bars3["left"]["top"])
Mn_r_neg = nominal(bm3, bars3["right"]["top"], bars3["right"]["bot"])
Mn_r_pos = nominal(bm3, bars3["right"]["bot"], bars3["right"]["top"])
wu = 4500 * 9.80665 / 1000
Ve = max(Mn_l_neg + Mn_r_pos, Mn_l_pos + Mn_r_neg) / 6000 + wu * 6000 / 2
check("IMF Ve = (Mnl + Mnr)/ℓn + wuℓn/2", s3["Ve"], Ve, 1e-9)
check("IMF Mn+ ≥ Mn−/3 at faces", Mn_l_pos >= Mn_l_neg / 3 and Mn_r_pos >= Mn_r_neg / 3, True)
check("IMF end hoops ≤ 8db", r3["shear"]["zones"]["left"]["s"] <= 8 * 16, True)
check("IMF end zone ≥ 2h", r3["shear"]["end_zone"] >= 1200, True)
lowpos = copy.deepcopy(ex("B3_IMF_design_kgfm.json"))
for cb in lowpos["combos"]:
    cb["M_mid"] = 500
    cb["M_left"] = -30000
rl = run(lowpos)
if not rl.get("stopped"):
    bl = rl["bars"]
    check("IMF raises bottom bars for Mn+ ≥ Mn−/3",
          nominal(rl["beam"], bl["left"]["bot"], bl["left"]["top"]) >= nominal(rl["beam"], bl["left"]["top"], bl["left"]["bot"]) / 3 - 1, True)
per = copy.deepcopy(b1)
per["span"]["position"] = "perimeter"
rp = run(per)
nt = max(sum(k for k, _ in rp["bars"][s]["top"]) for s in ("left", "right"))
check("perimeter: continuous top ≥ max(2, ⅙)", sum(k for k, _ in rp["bars"]["mid"]["top"]) >= max(2, math.ceil(nt / 6)), True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
