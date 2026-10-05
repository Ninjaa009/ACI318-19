#!/usr/bin/env python3
"""staadio vs real STAAD.Pro 2025 output of CC.std (fixtures/).  Expected numbers are read
straight from the STAAD tables (or from statics), not from staadio."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import staadio  # noqa: E402

F = lambda n: open(os.path.join(HERE, "fixtures", n), encoding="utf-8").read()
PASS = FAIL = 0


def check(name, got, exp, tol=0.002):
    global PASS, FAIL
    good = got == exp if isinstance(exp, (str, bool, tuple)) else abs(got - exp) <= tol * max(1.0, abs(exp))
    PASS += good
    FAIL += not good
    print(f"{'PASS' if good else 'FAIL'}  {name}: got {got!r} expected {exp!r}")


model = staadio.Model(F("CC.std"))
end = staadio.read_forces(F("CC_end_forces.txt"), model)
sec = staadio.read_forces(F("CC_section_forces.txt"), model)

print("== model / local axes ==")
check("29 members", len(model.members), 29)
check("col 1 local y = −X", tuple(round(v) for v in model.axes(1)[1]), (-1, 0, 0))
check("col 30 (start on top) local y = +X", tuple(round(v) for v in model.axes(30)[1]), (1, 0, 0))
check("beam 22 (along Z) local z = −X", tuple(round(v) for v in model.axes(22)[2]), (-1, 0, 0))
check("PRIS 0.5×0.4", model.prop[1], (0.5, 0.4))

print("== end-force table → section convention ==")
check("end table: section(1) = −end force (col 1 LC102 Mz)", staadio.at(end[(1, "102")], 1.0, staadio.MZ), 20.909)
check("same as section table at 1.0", staadio.at(sec[(1, "102")], 1.0, staadio.MZ), 20.909)
check("axial at end node → compression +", staadio.at(end[(30, "102")], 1.0, staadio.FX), 94.477)

print("== columns ==")
c30 = staadio.column(model, sec, 30, ["102"])
cb = c30["combos"][0]
check("col 30 Pu = bottom (node 25) 94.477, not start 58.852", cb["Pu"], 94.477)
check("col 30 top = node 21", c30["info"]["top_node"], 21)
check("col 30 Mx top 25.764", cb["Mx_top"], 25.764)
check("col 30 Mx bottom 9.289", cb["Mx_bot"], 9.289)
check("col 30 double curvature about x", cb["curv_x"], "double")
check("col 30 My top / bot", (round(cb["My_top"], 3), round(cb["My_bot"], 3)), (24.641, 6.855))
check("col 30 Vuy = |Shear-Y|", cb["Vuy"], 10.015)
check("col 30 Vux = |Shear-Z|", cb["Vux"], 8.999)
check("section 600×600", (c30["section"]["b"], c30["section"]["h"]), (600.0, 600.0))
check("ℓu = 3.5 − 0.5 (beam depth)", c30["length"]["lu"], 3.0)
c1s = staadio.column(model, sec, 1, ["102"])["combos"][0]
c1e = staadio.column(model, end, 1, ["102"])["combos"][0]
check("col 1 end-table = section-table (Pu)", c1e["Pu"], c1s["Pu"])
check("col 1 end-table = section-table (Mx top)", c1e["Mx_top"], c1s["Mx_top"])
check("col 1 end-table curvature", c1e["curv_x"], c1s["curv_x"])
check("col 1 b = ZD 400, h = YD 500", (staadio.column(model, sec, 1, ["102"])["section"]["b"],), (400.0,))
check("col 1 |V|·L = |Mt| + |Mb| (double curvature check)", 8.700 * 3.5, cb_sum := c1s["Mx_top"] + c1s["Mx_bot"], 0.002)
c31 = staadio.column(model, end, 31, ["102"])["combos"][0]
check("col 31 (flipped) Pu bottom 262.549", c31["Pu"], 262.549)

print("== beams ==")
b13 = staadio.beam(model, sec, 13, ["2", "102"])
lc2, lc102 = b13["combos"]
check("beam 13 LC2 max sagging = statics 6.658 (section −6.651 at 0.5)", lc2["M_mid"], 6.658, 0.003)
check("face offset left = col 1 YD/2 = 0.25 m", b13["info"]["face_left"], 0.25)
check("face offset right = col 2 YD/2 = 0.25 m", b13["info"]["face_right"], 0.25)
ml = -(20.191 + (8.708 - 20.191) * (0.05 / 0.083))
check("beam 13 LC102 M at left face (interpolated)", lc102["M_left"], ml, 0.003)
mr = -(34.117 + (20.312 - 34.117) * (0.05 / 0.083))
check("beam 13 LC102 M at right face", lc102["M_right"], mr, 0.003)
check("beam 13 LC102 hogging at both faces", lc102["M_left"] < 0 and lc102["M_right"] < 0, True)
check("beam 13 LC102 sagging mid 20.690", lc102["M_mid"], 20.690)
check("ln = 5 − 0.25 − 0.25", b13["span"]["ln"], 4.5)
b22 = staadio.beam(model, sec, 22, ["102"])
check("beam 22 (along Z) face offset = col 1 ZD/2 = 0.2", b22["info"]["face_left"], 0.2)
check("beam 22 sagging mid 21.384", b22["combos"][0]["M_mid"], 21.384)
check("beam 22 width 300 depth 500", (b22["section"]["b"], b22["section"]["h"]), (300.0, 500.0))

print("== guards ==")
try:
    staadio.beam(model, end, 13, ["102"])
    check("beam needs section table", False, True)
except ValueError:
    check("beam needs section table", True, True)
m2 = staadio.Model(F("CC.std").replace("CONSTANTS", "CONSTANTS\nBETA 90 MEMB 4"))
try:
    m2.check_supported(4)
    check("BETA ≠ 0 stops", False, True)
except ValueError:
    check("BETA ≠ 0 stops", True, True)
check("BETA list parsed", m2.beta.get(4), 90.0)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
