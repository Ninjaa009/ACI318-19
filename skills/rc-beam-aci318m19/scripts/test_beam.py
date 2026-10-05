#!/usr/bin/env python3
"""Regression + independent closed-form tests for beam.py.

Run: python3 test_beam.py      (exit code 0 = all pass)
Expected values are computed here with separate closed-form arithmetic,
not by calling the solver internals, except where noted.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from beam import (Layer, analyze, bar_area, design_flexure, shear, ld_tension,
                  ldh, lap_compression, min_depth, crack_spacing_max,
                  design_beam, report, KSC_TO_MPA, G)

RESULTS = []


def check(name, got, exp, tol=0.005):
    ok = abs(got - exp) <= tol * max(1.0, abs(exp))
    RESULTS.append((name, got, exp, ok))


def check_true(name, cond):
    RESULTS.append((name, cond, True, bool(cond)))


# ---------------------------------------------------------------- T1 singly
b, h, fc, fy = 300, 600, 28, 420
d = 600 - 40 - 10 - 12.5
Mu = 250e6
a_req = d - math.sqrt(d * d - 2 * Mu / (0.9 * 0.85 * fc * b))
As_req = 0.85 * fc * b * a_req / fy
r = design_flexure(b, h, fc, fy, Mu, 40, 10, 25, 20)
check("T1 As,req singly (mm²)", r["As_est_singly"], As_req)
check("T1 bars", r["n_tension"], 3, 0)
As = 3 * bar_area(25)
a = As * fy / (0.85 * fc * b)
phiMn = 0.9 * As * fy * (d - a / 2)
check("T1 φMn (N·mm)", r["res"].phiMn, phiMn)
check("T1 εt", r["res"].eps_t, 0.003 * (d - a / 0.85) / (a / 0.85))

# ---------------------------------------------------------------- T2 doubly
r2 = design_flexure(300, 450, 28, 420, 330e6, 40, 10, 25, 20)
check_true("T2 doubly found", r2["ok"] and r2["n_comp"] > 0)
check_true("T2 φMn ≥ Mu", r2["res"].phiMn >= 330e6)
check_true("T2 strain ok", r2["res"].tension_ok)
check("T2 φMn regression (kN·m)", r2["res"].phiMn / 1e6, 346.9, 0.002)

# ---------------------------------------------------------------- T3 check, 2 layers
L = [Layer(2 * bar_area(16), 58), Layer(4 * bar_area(25), 537.5),
     Layer(2 * bar_area(25), 487.5)]
t3 = analyze(300, 600, 28, 420, L)
check("T3 c (mm)", t3.c, 178.6, 0.002)
check("T3 εt", t3.eps_t, 0.00603, 0.005)
check("T3 φMn (kN·m)", t3.phiMn / 1e6, 497.8, 0.002)
check_true("T3 d ≠ dt", abs(t3.d - t3.dt) > 1)

# ---------------------------------------------------------------- E2 strain fail
e2 = analyze(300, 600, 28, 420, [Layer(4 * bar_area(25), 537.5),
                                  Layer(4 * bar_area(25), 487.5)])
check_true("E2 strain limit fails", not e2.tension_ok)

# ---------------------------------------------------------------- E5 shear
bw, dd = 300, 537.5
Vc_a = 0.17 * math.sqrt(28) * bw * dd
Av = 2 * bar_area(10)
s_lim = min(Av * 420 * dd / (150e3 / 0.75 - Vc_a), Av / 0.25, dd / 2)
s_exp = math.floor(s_lim / 25) * 25
sh = shear(28, 420, 300, 600, dd, 6 * bar_area(25), 150e3, 10, 2, 40)
check("E5 Vc eq.(a) (N)", sh["Vc"]["Vc"], Vc_a)
check("E5 s (mm)", sh["s"], s_exp, 0)
check("E5 φVn (N)", sh["phiVn"], 0.75 * (Vc_a + Av * 420 * dd / s_exp))
sh700 = shear(28, 420, 300, 600, dd, 6 * bar_area(25), 150e3, 10, 2, 40, s=700)
lam_s = math.sqrt(2 / (1 + dd / 250))
rho = 6 * bar_area(25) / (bw * dd)
check("E5 s=700 → eq.(c)", sh700["Vc"]["Vc"],
      0.66 * lam_s * rho ** (1 / 3) * math.sqrt(28) * bw * dd)
check_true("E5 s=700 Av<Av,min flagged", not sh700["checks"]["Av_min_9.6.3"])

# ---------------------------------------------------------------- N1 fyt cap (new)
sh_sd50 = shear(28, 490.3, 300, 600, dd, 6 * bar_area(25), 150e3, 10, 2, 40, s=200)
check("N1 fyt used = 420", sh_sd50["fyt_used"], 420.0, 0)
check("N1 Vs uses 420", sh_sd50["Vs"], Av * 420 * dd / 200)

# ---------------------------------------------------------------- N2 transverse legs (new)
wide = shear(28, 420, 800, 700, 630, 8 * bar_area(25), 400e3, 10, 2, 40, s=150)
lsp = (800 - 2 * 40 - 10) / 1
check("N2 leg spacing (mm)", wide["leg_spacing"], lsp)
check_true("N2 2 legs fail across 800 mm", not wide["checks"]["s_trans_9.7.6.2.2"])
wide4 = shear(28, 420, 800, 700, 630, 8 * bar_area(25), 400e3, 10, 4, 40, s=150)
check_true("N2 4 legs pass", wide4["checks"]["s_trans_9.7.6.2.2"])

# ---------------------------------------------------------------- N3 Table 9.6.3.1 exemption (new)
shallow = shear(28, 420, 300, 250, 200, 3 * bar_area(16), 30e3, 10, 2, 25)
check_true("N3 h ≤ 250 exempt, no stirrups", shallow["required"] is False)

# ---------------------------------------------------------------- N4 development (new)
sfc = math.sqrt(28)
check("N4 ℓd DB25 SD40 bottom", ld_tension(25, 420, 28)["ld"], 420 / (1.7 * sfc) * 25)
check("N4 ℓd DB25 SD50 ψg=1.15", ld_tension(25, 490.3, 28)["ld"],
      490.3 * 1.15 / (1.7 * sfc) * 25)
check("N4 ℓd DB16 top other", ld_tension(16, 420, 28, top=True, good=False)["ld"],
      420 * 1.3 / (1.4 * sfc) * 16)
check("N4 ℓd DB20 bottom → larger-bar row (1.7)", ld_tension(20, 420, 28)["ld"], 420 / (1.7 * sfc) * 20)
chk_db19 = ld_tension(19, 420, 28)["ld"]
check("N4 ℓd DB19 bottom → 2.1 row", chk_db19, max(420 / (2.1 * sfc) * 19, 300))
pc = 28 / 105 + 0.6
check("N4 ℓdh DB25", ldh(25, 420, 28)["ldh"],
      max(420 * 1.6 * 1.25 * pc / (23 * sfc) * 25 ** 1.5, 200, 150))
check("N4 compression lap DB25 SD40", lap_compression(25, 420, 28), 0.071 * 420 * 25)

# ---------------------------------------------------------------- N5 misc (new)
check("N5 min depth simple 6 m SD40", min_depth(6000, "simple", 420), 6000 / 16)
check("N5 min depth SD50", min_depth(6000, "simple", 490.3), 6000 / 16 * (0.4 + 490.3 / 700))
check("N5 crack s,max cc=50", crack_spacing_max(420, 50), min(380 * 280 / 280 - 125, 300))

# ---------------------------------------------------------------- N6 end-to-end kgf-m (new)
inp = {"units": "kgf-m", "b": 0.30, "h": 0.60, "fc": 28 / KSC_TO_MPA,
       "fy": 420 / KSC_TO_MPA, "fyt": 420 / KSC_TO_MPA, "cover": 40,
       "stirrup_db": 10, "stirrup_legs": 2, "bar_db": 25, "comp_db": 20,
       "Mu": 250e6 / (G * 1000), "Vu": 150e3 / G, "ln": 6.0, "support": "both_ends"}
res = design_beam(inp)
check("N6 kgf-m φMn = SI φMn", res["flexure"]["phiMn"], r["res"].phiMn)
check("N6 kgf-m stirrup s", res["shear"]["s"], s_exp, 0)
rep = report(res)
check_true("N6 report renders", "สรุปสถานะ" in rep)

# ---------------------------------------------------------------- N7 deep beam stop (new)
deep = design_beam({"units": "SI", "b": 300, "h": 1200, "fc": 28, "fy": 420,
                    "Mu": 300, "Vu": 200, "ln": 4000})
check_true("N7 deep beam stops", deep.get("stopped") is True)

# ---------------------------------------------------------------- N8 negative moment → top bar ψt
neg = design_beam({"units": "SI", "b": 300, "h": 600, "fc": 28, "fy": 420,
                   "Mu": -250, "Vu": 0, "bar_db": 25})
check_true("N8 Mu<0 → tension top", neg["tension_face"] == "บน")
check("N8 top bar ψt = 1.3", neg["development"]["ld"]["psi_t"], 1.3, 0)

# ---------------------------------------------------------------- output
fails = [x for x in RESULTS if not x[3]]
lines = ["| # | การทดสอบ | ได้ | คาดหมาย | ผล |", "|---|---|---|---|---|"]
for i, (n, g, e, ok) in enumerate(RESULTS, 1):
    fmt = (lambda v: f"{v:,.4g}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v))
    lines.append(f"| {i} | {n} | {fmt(g)} | {fmt(e)} | {'✅' if ok else '❌'} |")
print("\n".join(lines))
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed")
sys.exit(1 if fails else 0)
