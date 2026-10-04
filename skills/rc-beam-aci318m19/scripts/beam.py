#!/usr/bin/env python3
"""RC rectangular beam design/check per ACI 318M-19 (SI internal: N, mm, MPa).

Scope: nonprestressed rectangular beam, flexure (singly/doubly, multi-layer),
one-way shear with vertical stirrups, detailing, development/splice lengths,
minimum depth. No axial force (Pu < 0.10 f'c Ag), no torsion (Tu < phi*Tth),
not a deep beam, no special seismic (Ch.18) provisions.

Usage:
    python3 beam.py input.json            -> markdown report to stdout
    python3 beam.py input.json --json     -> raw results as JSON

Every check carries its ACI 318M-19 clause so the report can cite it.
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field, asdict

G = 9.80665                 # kgf -> N
KSC_TO_MPA = 0.0980665      # kgf/cm^2 -> MPa
ES = 200_000.0              # MPa, 20.2.2.2
ECU = 0.003                 # 22.2.2.1
PHI_V = 0.75                # Table 21.2.1(b)
SQRT_FC_MAX = 8.3           # MPa, 22.5.3.1 / 25.4.1.4
FYT_SHEAR_MAX = 420.0       # MPa, Table 20.2.2.4(a) stirrups (deformed bars)


def bar_area(db: float) -> float:
    return math.pi * db * db / 4.0


# ---------------------------------------------------------------------------
# Material helpers
# ---------------------------------------------------------------------------

def beta1(fc: float) -> float:
    """Table 22.2.2.4.3."""
    if fc <= 28.0:
        return 0.85
    if fc >= 55.0:
        return 0.65
    return 0.85 - 0.05 * (fc - 28.0) / 7.0


def eps_ty(fy: float, grade420_exception: bool = False) -> float:
    """21.2.2.1: eps_ty = fy/Es; Grade 420 may use 0.002."""
    if grade420_exception and abs(fy - 420.0) < 1e-6:
        return 0.002
    return fy / ES


def phi_flexure(eps_t: float, ety: float, spiral: bool = False) -> float:
    """Table 21.2.2."""
    lo, span = (0.75, 0.15) if spiral else (0.65, 0.25)
    if eps_t <= ety:
        return lo
    if eps_t >= ety + 0.003:
        return 0.90
    return lo + span * (eps_t - ety) / 0.003


# ---------------------------------------------------------------------------
# Flexure: strain-compatibility section analysis
# ---------------------------------------------------------------------------

@dataclass
class Layer:
    area: float     # mm^2
    y: float        # mm, depth from compression face


@dataclass
class FlexResult:
    c: float
    a: float
    Mn: float           # N*mm
    phi: float
    phiMn: float
    eps_t: float
    dt: float
    d: float            # centroid of tension steel
    tension_ok: bool    # eps_t >= eps_ty + 0.003  (9.3.3.1)
    eps_ty: float
    layer_stress: list = field(default_factory=list)


def analyze(b: float, h: float, fc: float, fy: float, layers: list[Layer],
            grade420_exception: bool = False) -> FlexResult:
    """Find neutral axis by bisection on force equilibrium (22.2.1)."""
    b1 = beta1(fc)
    ety = eps_ty(fy, grade420_exception)

    def forces(c):
        a = min(b1 * c, h)
        Cc = 0.85 * fc * b * a
        F = []
        for L in layers:
            es = ECU * (c - L.y) / c                    # + = compression
            fs = max(-fy, min(fy, ES * es))             # 20.2.2.1
            if es > 0 and L.y <= a:                     # displaced concrete
                fs -= 0.85 * fc
            F.append(L.area * fs)
        return Cc, a, F

    lo, hi = 1e-6, 5.0 * h
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        Cc, a, F = forces(mid)
        if Cc + sum(F) > 0:
            hi = mid
        else:
            lo = mid
    c = 0.5 * (lo + hi)
    Cc, a, F = forces(c)
    Mn = -Cc * a / 2.0 - sum(Fi * L.y for Fi, L in zip(F, layers))

    tens = [(L, Fi) for L, Fi in zip(layers, F) if Fi < 0]
    dt = max(L.y for L in layers)
    ten_area = sum(L.area for L, _ in tens) or 1.0
    d = sum(L.area * L.y for L, _ in tens) / ten_area if tens else dt
    eps_t = ECU * (dt - c) / c
    phi = phi_flexure(eps_t, ety)
    stresses = [{"y": round(L.y, 1), "area": round(L.area, 1),
                 "stress": round(Fi / L.area, 1)} for L, Fi in zip(layers, F)]
    return FlexResult(c, a, Mn, phi, phi * Mn, eps_t, dt, d,
                      eps_t >= ety + 0.003 - 1e-12, ety, stresses)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def clear_spacing_min(db: float, dagg: float) -> float:
    """25.2.1: max(25 mm, db, 4/3 dagg)."""
    return max(25.0, db, 4.0 / 3.0 * dagg)


def bars_per_layer(b: float, cover: float, ds: float, db: float, dagg: float) -> int:
    sc = clear_spacing_min(db, dagg)
    width = b - 2 * (cover + ds)
    return max(2, int((width + sc) // (db + sc)))


def tension_layers(h, cover, ds, db, n, nmax):
    """Up to 2 layers; layer clear gap max(25, db) per 25.2.2."""
    y1 = h - cover - ds - db / 2.0
    n1 = min(n, nmax)
    out = [Layer(n1 * bar_area(db), y1)]
    if n > nmax:
        gap = max(25.0, db)
        out.append(Layer((n - n1) * bar_area(db), y1 - db - gap))
    return out


def as_min(fc, fy, bw, d):
    """9.6.1.2 (fy <= 550 in formula)."""
    fyc = min(fy, 550.0)
    return max(0.25 * math.sqrt(fc) / fyc, 1.4 / fyc) * bw * d


# ---------------------------------------------------------------------------
# Flexural design
# ---------------------------------------------------------------------------

def design_flexure(b, h, fc, fy, Mu, cover, ds, db, dbc, dagg=20.0,
                   max_layers=2, grade420_exception=False):
    """Smallest tension (then compression) bar count that satisfies
    phiMn >= Mu, eps_t >= eps_ty + 0.003 and As >= As,min.
    Mu in N*mm (positive magnitude; the caller handles which face is tension).
    """
    Mu = abs(Mu)
    nmax = bars_per_layer(b, cover, ds, db, dagg)
    nmax_c = bars_per_layer(b, cover, ds, dbc, dagg)
    yc = cover + ds + dbc / 2.0
    ntmax = nmax * max_layers

    # closed-form singly estimate (for the report only)
    d1 = h - cover - ds - db / 2.0
    est = None
    disc = d1 * d1 - 2 * Mu / (0.9 * 0.85 * fc * b)
    if disc > 0:
        a = d1 - math.sqrt(disc)
        est = 0.85 * fc * b * a / fy

    for nc in [0] + list(range(2, nmax_c + 1)):
        for nt in range(2, ntmax + 1):
            layers = tension_layers(h, cover, ds, db, nt, nmax)
            if nc:
                layers = [Layer(nc * bar_area(dbc), yc)] + layers
            r = analyze(b, h, fc, fy, layers, grade420_exception)
            As = nt * bar_area(db)
            if (r.phiMn >= Mu and r.tension_ok
                    and As >= as_min(fc, fy, b, r.d)):
                return {"ok": True, "n_tension": nt, "n_comp": nc,
                        "n_per_layer": nmax, "layers": layers, "res": r,
                        "As": As, "Asc": nc * bar_area(dbc),
                        "As_min": as_min(fc, fy, b, r.d),
                        "As_est_singly": est}
    return {"ok": False, "reason": "ไม่พบการจัดเหล็กที่ผ่าน (เพิ่มหน้าตัด / ขนาดเหล็ก)",
            "As_est_singly": est}


# ---------------------------------------------------------------------------
# Shear (one-way, vertical stirrups)
# ---------------------------------------------------------------------------

def lambda_s(d):
    """22.5.5.1.3."""
    return min(1.0, math.sqrt(2.0 / (1.0 + d / 250.0)))


def vc_nonprestressed(fc, bw, d, As, Av_ok, lam=1.0, Nu=0.0, Ag=None,
                      eq="a"):
    """Table 22.5.5.1. Av_ok = (Av/s >= Av,min/s)."""
    rho_w = As / (bw * d)
    # 22.5.3.2: sqrt(fc) > 8.3 allowed only with min web reinforcement
    sfc = math.sqrt(fc) if Av_ok else min(math.sqrt(fc), SQRT_FC_MAX)
    ax = 0.0
    if Nu and Ag:
        ax = min(Nu / (6.0 * Ag), 0.05 * fc)
    va = (0.17 * lam * sfc + ax) * bw * d
    vb = (0.66 * lam * rho_w ** (1 / 3) * sfc + ax) * bw * d
    vcc = (0.66 * lambda_s(d) * lam * rho_w ** (1 / 3) * sfc + ax) * bw * d
    vmax = 0.42 * lam * sfc * bw * d                         # 22.5.5.1.1
    if Av_ok:
        val = {"a": va, "b": vb, "max": max(va, vb)}[eq]
        used = {"a": "(a)", "b": "(b)", "max": "(a)" if va >= vb else "(b)"}[eq]
    else:
        val, used = vcc, "(c)"
    return {"Vc": max(0.0, min(val, vmax)), "eq": used, "Vc_a": va,
            "Vc_b": vb, "Vc_c": vcc, "lambda_s": lambda_s(d),
            "rho_w": rho_w, "Vc_max": vmax}


def av_min_s(fc, bw, fyt):
    """Table 9.6.3.4 (nonprestressed)."""
    return max(0.062 * math.sqrt(fc) * bw / fyt, 0.35 * bw / fyt)


def exempt_9631(h, bw=None, tf=None, integral_slab=False):
    """Table 9.6.3.1 geometric exemptions (fiber-reinforced / joists not handled)."""
    if h <= 250.0:
        return True, "h ≤ 250 mm"
    if integral_slab and tf and h <= max(2.5 * tf, 0.5 * bw) and h <= 600.0:
        return True, "หล่อเป็นเนื้อเดียวกับพื้น h ≤ max(2.5tf, 0.5bw) และ ≤ 600 mm"
    return False, ""


def s_max_table(Vs, fc, bw, d):
    """Table 9.7.6.2.2 nonprestressed: (along length, across width)."""
    if Vs <= 0.33 * math.sqrt(fc) * bw * d:
        return min(d / 2, 600.0), min(d, 600.0)
    return min(d / 4, 300.0), min(d / 2, 300.0)


def leg_spacing(b, cover, ds, legs):
    if legs < 2:
        return float("inf")
    return (b - 2 * cover - ds) / (legs - 1)


def shear(fc, fyt, bw, h, d, As, Vu, ds, legs, cover, s=None, lam=1.0,
          vc_eq="a", integral_slab=False, tf=None, step=25.0):
    """Design (s=None) or check (s given) vertical stirrups."""
    fyt_d = min(fyt, FYT_SHEAR_MAX)
    Av = legs * bar_area(ds)
    avmin = av_min_s(fc, bw, fyt_d)
    trig = 0.083 * PHI_V * lam * math.sqrt(fc) * bw * d          # 9.6.3.1
    ex, ex_txt = exempt_9631(h, bw, tf, integral_slab)
    out = {"fyt_input": fyt, "fyt_used": fyt_d, "Av": Av, "Av_min_s": avmin,
           "Vu": Vu, "trigger_min": trig, "exempt_9631": ex_txt or None}

    vc0 = vc_nonprestressed(fc, bw, d, As, False, lam)          # no stirrups
    need_min = Vu > trig and not ex
    if s is None:
        if Vu <= PHI_V * vc0["Vc"] and not need_min:
            out.update(required=False, s=None, Vc=vc0, Vs=0.0,
                       phiVn=PHI_V * vc0["Vc"],
                       note="ไม่ต้องใช้ปลอกตามการคำนวณ (แนะนำปลอกขั้นต่ำตามหลักปฏิบัติ)")
            out["section_ok"] = True
            out["ok"] = True
            return out
        vc = vc_nonprestressed(fc, bw, d, As, True, lam, eq=vc_eq)
        vs_req = max(Vu / PHI_V - vc["Vc"], 0.0)
        s_str = Av * fyt_d * d / vs_req if vs_req > 0 else float("inf")
        s_min_req = Av / avmin
        s_cand = min(s_str, s_min_req)
        smax_l, _ = s_max_table(vs_req, fc, bw, d)
        s_try = min(s_cand, smax_l)
        s = math.floor(s_try / step) * step
        if s <= 0:
            s = s_try
        # re-check spacing limit with provided Vs
        vs_p = Av * fyt_d * d / s
        smax_l, _ = s_max_table(vs_p, fc, bw, d)
        if s > smax_l:
            s = math.floor(smax_l / step) * step
        out["s_strength"] = s_str
        out["s_from_Avmin"] = s_min_req
    av_ok = (Av / s) >= avmin - 1e-9
    vc = vc_nonprestressed(fc, bw, d, As, av_ok, lam, eq=vc_eq)
    vs = Av * fyt_d * d / s
    smax_l, smax_t = s_max_table(vs, fc, bw, d)
    lsp = leg_spacing(bw, cover, ds, legs)
    sec_lim = PHI_V * (vc["Vc"] + 0.66 * math.sqrt(fc) * bw * d)  # 22.5.1.2
    phiVn = PHI_V * (vc["Vc"] + vs)
    out.update(required=True, s=s, Vc=vc, Vs=vs, phiVn=phiVn,
               Av_ok=av_ok, need_min=need_min,
               smax_long=smax_l, smax_trans=smax_t, leg_spacing=lsp,
               section_limit=sec_lim)
    checks = {
        "strength": phiVn >= Vu,
        "section_22.5.1.2": Vu <= sec_lim,
        "Av_min_9.6.3": (not need_min) or av_ok,
        "s_long_9.7.6.2.2": s <= smax_l + 1e-9,
        "s_trans_9.7.6.2.2": lsp <= smax_t + 1e-9,
    }
    out["checks"] = checks
    out["section_ok"] = checks["section_22.5.1.2"]
    out["ok"] = all(checks.values())
    return out


# ---------------------------------------------------------------------------
# Detailing
# ---------------------------------------------------------------------------

def crack_spacing_max(fy, cc, fs=None):
    """Table 24.3.2; fs = 2/3 fy permitted (24.3.2.1)."""
    fs = fs or 2.0 * fy / 3.0
    return min(380.0 * 280.0 / fs - 2.5 * cc, 300.0 * 280.0 / fs)


def min_depth(ln, support, fy, wc=None):
    """Table 9.3.1.1 + 9.3.1.1.1/9.3.1.1.2. ln in mm."""
    div = {"simple": 16.0, "one_end": 18.5, "both_ends": 21.0,
           "cantilever": 8.0}[support]
    hmin = ln / div
    if abs(fy - 420.0) > 1e-6:
        hmin *= 0.4 + fy / 700.0
    if wc and 1440 <= wc <= 1840:
        hmin *= max(1.65 - 0.0003 * wc, 1.09)
    return hmin


def comp_tie_req(dbc, ds_avail, b, h):
    """9.7.6.4 / 25.7.2: tie size and max spacing for compression bars."""
    tie = 10.0 if dbc <= 32 else 12.0
    smax = min(16 * dbc, 48 * max(ds_avail, tie), min(b, h))
    return {"tie_db_min": tie, "s_max": smax,
            "ok_size": ds_avail >= tie}


# ---------------------------------------------------------------------------
# Development and splices (Chapter 25, SI form of ACI 318M-19)
# ---------------------------------------------------------------------------

def psi_g(fy):
    if fy <= 420.0 + 1e-6:
        return 1.0
    if fy <= 550.0 + 1e-6:
        return 1.15
    return 1.3


def ld_tension(db, fy, fc, top=False, epoxy=None, lam=1.0, good=True,
               cb=None, Ktr=0.0):
    """25.4.2. good=True -> first row of Table 25.4.2.3.
    If cb is given, use general Eq. 25.4.2.4a instead."""
    sfc = min(math.sqrt(fc), SQRT_FC_MAX)
    pt = 1.3 if top else 1.0
    pe = {"near": 1.5, "other": 1.2}.get(epoxy, 1.0)
    pt_pe = min(pt * pe, 1.7)
    pg = psi_g(fy)
    if cb is not None:
        ps = 0.8 if db <= 20 else 1.0
        conf = min((cb + Ktr) / db, 2.5)
        ld = fy / (1.1 * lam * sfc) * pt_pe * ps * pg / conf * db
        method = "Eq. 25.4.2.4a"
    else:
        small = db <= 20
        k = (2.1 if small else 1.7) if good else (1.4 if small else 1.1)
        ld = fy * pt_pe * pg / (k * lam * sfc) * db
        method = f"Table 25.4.2.3 (k = {k})"
    return {"ld": max(ld, 300.0), "ld_calc": ld, "psi_t": pt, "psi_e": pe,
            "psi_g": pg, "method": method}


def ldh(db, fy, fc, lam=1.0, epoxy=False, psi_r=1.6, psi_o=1.25):
    """25.4.3. Conservative defaults psi_r=1.6, psi_o=1.25 unless confirmed."""
    pc = fc / 105.0 + 0.6 if fc < 40.0 else 1.0
    pe = 1.2 if epoxy else 1.0
    sfc = min(math.sqrt(fc), SQRT_FC_MAX)
    val = fy * pe * psi_r * psi_o * pc / (23.0 * lam * sfc) * db ** 1.5
    return {"ldh": max(val, 8 * db, 150.0), "calc": val, "psi_c": pc,
            "psi_r": psi_r, "psi_o": psi_o, "psi_e": pe}


def ldc(db, fy, fc, lam=1.0, psi_r=1.0):
    """25.4.9."""
    sfc = min(math.sqrt(fc), SQRT_FC_MAX)
    v = max(0.24 * fy * psi_r / (lam * sfc), 0.043 * fy * psi_r) * db
    return max(v, 200.0)


def lap_tension(ld_val, cls="B"):
    """Table 25.5.2.1 (ld without As,req/As,prov reduction)."""
    return max((1.0 if cls == "A" else 1.3) * ld_val, 300.0)


def lap_compression(db, fy, fc):
    """25.5.5.1."""
    if fy <= 420.0 + 1e-6:
        v = 0.071 * fy * db
    elif fy <= 550.0 + 1e-6:
        v = (0.13 * fy - 24.0) * db
    else:
        v = None
    v = max(v, 300.0) if v else None
    if v and fc < 21.0:
        v *= 4.0 / 3.0
    return v


# ---------------------------------------------------------------------------
# Top-level: from user input (kgf-m or SI) to results
# ---------------------------------------------------------------------------

def to_si(inp: dict) -> dict:
    u = inp.get("units", "kgf-m")
    s = dict(inp)
    if u == "kgf-m":
        s["b"] = inp["b"] * 1000.0
        s["h"] = inp["h"] * 1000.0
        for k in ("fc", "fy", "fyt"):
            if k in inp:
                s[k] = inp[k] * KSC_TO_MPA
        s["Mu"] = inp.get("Mu", 0.0) * G * 1000.0          # kgf*m -> N*mm
        s["Vu"] = inp.get("Vu", 0.0) * G                   # kgf -> N
        if inp.get("ln") is not None:
            s["ln"] = inp["ln"] * 1000.0
        if inp.get("tf") is not None:
            s["tf"] = inp["tf"] * 1000.0
    elif u == "SI":                                         # kN, kN*m, mm, MPa
        s["Mu"] = inp.get("Mu", 0.0) * 1e6
        s["Vu"] = inp.get("Vu", 0.0) * 1e3
    else:
        raise ValueError("units must be 'kgf-m' or 'SI'")
    return s


def scope_checks(si):
    msgs = []
    ln, h = si.get("ln"), si["h"]
    if ln is not None and ln <= 4 * h:
        msgs.append(("FAIL", "9.9.1.1", f"ℓn = {ln:.0f} mm ≤ 4h = {4*h:.0f} mm → deep beam นอกขอบเขต (ใช้ STM Ch.23)"))
    if si.get("conc_load_within_2h"):
        msgs.append(("FAIL", "9.9.1.1", "มีแรงจุดภายใน 2h จากผิวจุดรองรับ → deep beam นอกขอบเขต"))
    Pu = si.get("Pu", 0.0) or 0.0
    if Pu and Pu >= 0.10 * si["fc"] * si["b"] * h:
        msgs.append(("FAIL", "9.5.2.2", "Pu ≥ 0.10f′cAg → ต้องออกแบบตาม §22.4 (นอกขอบเขต)"))
    if si.get("Tu"):
        msgs.append(("WARN", "9.5.4.1", "มีแรงบิด — ต้องยืนยัน Tu < φTth ก่อน มิฉะนั้นนอกขอบเขต"))
    if si.get("sdc") in ("D", "E", "F") and si.get("seismic_system"):
        msgs.append(("FAIL", "18", "คานในระบบต้านแผ่นดินไหว SDC D–F → ต้องใช้ Ch.18"))
    lu = si.get("lateral_brace")
    if lu is not None and lu > 50 * si["b"]:
        msgs.append(("FAIL", "9.2.3.1", f"ระยะค้ำยันด้านข้าง {lu:.0f} mm > 50b"))
    return msgs


def design_beam(inp: dict) -> dict:
    si = to_si(inp)
    b, h, fc, fy = si["b"], si["h"], si["fc"], si["fy"]
    fyt = si.get("fyt", fy)
    cover = si.get("cover", 40.0)
    ds = si.get("stirrup_db", 10.0)
    legs = si.get("stirrup_legs", 2)
    db = si.get("bar_db", 20.0)
    dbc = si.get("comp_db", db)
    dagg = si.get("dagg", 20.0)
    lam = si.get("lam", 1.0)
    g420 = si.get("grade420_exception", False)
    Mu = si.get("Mu", 0.0)
    Vu = abs(si.get("Vu", 0.0))
    tension_face = "ล่าง" if Mu >= 0 else "บน"

    res = {"input": inp, "si": {k: si[k] for k in ("b", "h", "fc", "fy")},
           "fyt": fyt, "tension_face": tension_face, "beta1": beta1(fc)}
    res["scope"] = scope_checks(si)
    if any(m[0] == "FAIL" for m in res["scope"]):
        res["stopped"] = True
        return res

    # ---- flexure
    if si.get("mode", "design") == "design":
        fl = design_flexure(b, h, fc, fy, Mu, cover, ds, db, dbc, dagg,
                            grade420_exception=g420)
        if not fl["ok"]:
            res["flexure"] = fl
            res["stopped"] = True
            return res
        r = fl["res"]
        As, Asc, nt, nc = fl["As"], fl["Asc"], fl["n_tension"], fl["n_comp"]
        nmax = fl["n_per_layer"]
        res["flexure"] = {"design": True, "n_tension": nt, "db": db,
                          "n_comp": nc, "dbc": dbc, "As": As, "Asc": Asc,
                          "As_est_singly": fl["As_est_singly"],
                          "As_min": fl["As_min"], "n_per_layer": nmax}
    else:
        layers = []
        nt = 0
        for n, d_b in si["tension_bars"]:           # [[n, db], ...] layer 1 first
            nt += n
        y = h - cover - ds
        As = 0.0
        prev_db = None
        for i, (n, d_b) in enumerate(si["tension_bars"]):
            if i == 0:
                y -= d_b / 2.0
            else:
                y -= prev_db / 2.0 + max(25.0, prev_db, d_b) + d_b / 2.0
            layers.append(Layer(n * bar_area(d_b), y))
            As += n * bar_area(d_b)
            prev_db = d_b
        Asc = 0.0
        nc = 0
        if si.get("comp_bars"):
            nc, dbc = si["comp_bars"]
            Asc = nc * bar_area(dbc)
            layers.insert(0, Layer(Asc, cover + ds + dbc / 2.0))
        db = si["tension_bars"][0][1]
        r = analyze(b, h, fc, fy, layers, g420)
        nmax = bars_per_layer(b, cover, ds, db, dagg)
        res["flexure"] = {"design": False, "As": As, "Asc": Asc,
                          "As_min": as_min(fc, fy, b, r.d),
                          "n_per_layer": nmax,
                          "layer1_fits": si["tension_bars"][0][0] <= nmax}
    asmin = as_min(fc, fy, b, r.d)
    res["flexure"].update({
        "c": r.c, "a": r.a, "d": r.d, "dt": r.dt, "eps_t": r.eps_t,
        "eps_ty": r.eps_ty, "phi": r.phi, "Mn": r.Mn, "phiMn": r.phiMn,
        "Mu": abs(Mu), "strength_ok": r.phiMn >= abs(Mu),
        "strain_ok": r.tension_ok, "As_min_ok": As >= asmin,
        "layers": r.layer_stress,
        "cmax": ECU * r.dt / (ECU + r.eps_ty + 0.003)})

    # ---- shear
    if Vu > 0 or si.get("stirrup_s"):
        sh = shear(fc, fyt, b, h, r.d, As, Vu, ds, legs, cover,
                   s=si.get("stirrup_s"), lam=lam,
                   vc_eq=si.get("vc_eq", "a"),
                   integral_slab=si.get("integral_slab", False),
                   tf=si.get("tf"))
        res["shear"] = sh

    # ---- detailing
    det = {}
    cc = cover + ds
    sp = crack_spacing_max(fy, cc)
    n1 = min(res["flexure"].get("n_tension", nt) or nt, nmax)
    width = b - 2 * (cover + ds) - db
    s_cc = width / (n1 - 1) if n1 > 1 else float("inf")
    det["crack"] = {"s_max": sp, "s_provided": s_cc, "ok": s_cc <= sp + 1e-9,
                    "cc": cc}
    det["clear_min"] = clear_spacing_min(db, dagg)
    if res["flexure"].get("n_comp") or Asc:
        det["comp_ties"] = comp_tie_req(dbc, ds, b, h)
    det["skin_required"] = h > 900.0
    det["Ktr_note"] = fy >= 550.0
    if si.get("ln") is not None and si.get("support"):
        hm = min_depth(si["ln"], si["support"], fy, si.get("wc"))
        det["min_depth"] = {"h_min": hm, "ok": h >= hm}
    res["detailing"] = det

    # ---- development
    top = tension_face == "บน" and (h - (cover + ds + db / 2.0)) > 300.0
    clear_bars = s_cc - db
    good = clear_bars >= db and cc >= db      # stirrups >= min assumed present
    ldt = ld_tension(db, fy, fc, top=top, epoxy=si.get("epoxy"), lam=lam,
                     good=good)
    res["development"] = {
        "ld": ldt, "ldh": ldh(db, fy, fc, lam, bool(si.get("epoxy"))),
        "ldc": ldc(db, fy, fc, lam),
        "lap_A": lap_tension(ldt["ld"], "A"),
        "lap_B": lap_tension(ldt["ld"], "B"),
        "lap_comp": lap_compression(db, fy, fc),
        "top_bar": top}
    res["integrity_position"] = si.get("position", "unknown")
    return res


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _st(ok):
    return "✅ ผ่าน" if ok else "❌ ไม่ผ่าน"


def report(res: dict) -> str:
    inp = res["input"]
    u = inp.get("units", "kgf-m")
    kgfm = u == "kgf-m"

    def M(nmm):
        return f"{nmm/1e6:,.1f} kN·m" + (f" ({nmm/(G*1000):,.0f} kgf·m)" if kgfm else "")

    def V(n):
        return f"{n/1e3:,.1f} kN" + (f" ({n/G:,.0f} kgf)" if kgfm else "")

    def A(mm2):
        return f"{mm2/100:,.2f} cm²"

    L = []
    si = res["si"]
    L.append("# ผลออกแบบ/ตรวจสอบคาน RC — ACI 318M-19\n")
    L.append(f"หน้าตัด {si['b']:.0f}×{si['h']:.0f} mm · f′c = {si['fc']:.2f} MPa · "
             f"fy = {si['fy']:.1f} MPa · fyt = {res['fyt']:.1f} MPa · β1 = {res['beta1']:.3f} · "
             f"ผิวรับแรงดึง: **{res['tension_face']}**\n")
    if res["scope"]:
        L.append("## ขอบเขต")
        for lvl, cl, msg in res["scope"]:
            L.append(f"- {'❌' if lvl == 'FAIL' else '⚠️'} §{cl}: {msg}")
        L.append("")
    if res.get("stopped"):
        if "flexure" in res and not res["flexure"].get("ok", True):
            L.append(f"❌ แรงดัด: {res['flexure']['reason']}")
        L.append("\n**หยุดการคำนวณ — อยู่นอกขอบเขตหรือหาการจัดเหล็กไม่ได้**")
        return "\n".join(L)

    f = res["flexure"]
    L.append("## 1. แรงดัด (§22.2, §22.3, §9.5.2, Table 21.2.2)")
    if f["design"]:
        if f["As_est_singly"]:
            L.append(f"- As ประมาณ (singly, φ = 0.9, สูตรปิด) = {A(f['As_est_singly'])}")
        L.append(f"- เลือกเหล็กดึง **{f['n_tension']}-DB{f['db']:.0f}** "
                 f"(As = {A(f['As'])}, ชั้นละไม่เกิน {f['n_per_layer']} เส้น)"
                 + (f" + เหล็กอัด **{f['n_comp']}-DB{f['dbc']:.0f}** (A′s = {A(f['Asc'])})"
                    if f['n_comp'] else " · singly"))
    else:
        L.append(f"- As = {A(f['As'])}, A′s = {A(f['Asc'])}"
                 + ("" if f.get("layer1_fits", True) else
                    f" · ⚠️ ชั้นแรกเกิน {f['n_per_layer']} เส้นต่อชั้น (§25.2.1)"))
    L.append(f"- d = {f['d']:.1f} mm, dt = {f['dt']:.1f} mm, c = {f['c']:.1f} mm, a = {f['a']:.1f} mm "
             f"(c,max = {f['cmax']:.1f} mm)")
    L.append(f"- εt = {f['eps_t']:.5f} (เกณฑ์ εty + 0.003 = {f['eps_ty']+0.003:.5f}) → φ = {f['phi']:.3f}")
    L.append(f"- Mn = {M(f['Mn'])}, **φMn = {M(f['phiMn'])}** เทียบ Mu = {M(f['Mu'])}")
    L.append(f"- As,min (§9.6.1.2) = {A(f['As_min'])}")
    L.append("")

    sh = res.get("shear")
    if sh:
        L.append("## 2. แรงเฉือน (§22.5, §9.6.3, Table 9.7.6.2.2)")
        if sh["fyt_used"] < sh["fyt_input"] - 1e-6:
            L.append(f"- fyt ที่ใช้ = **{sh['fyt_used']:.0f} MPa** (ลดจาก {sh['fyt_input']:.1f} MPa ตาม Table 20.2.2.4(a))")
        vc = sh["Vc"]
        L.append(f"- Vu = {V(sh['Vu'])}; เกณฑ์ต้องมีปลอกขั้นต่ำ 0.083φλ√f′c·bw·d = {V(sh['trigger_min'])}"
                 + (f" · ยกเว้นตาม Table 9.6.3.1: {sh['exempt_9631']}" if sh["exempt_9631"] else ""))
        L.append(f"- Vc ใช้สมการ {vc['eq']} = {V(vc['Vc'])} "
                 f"[(a) {V(vc['Vc_a'])}, (b) {V(vc['Vc_b'])}, (c) {V(vc['Vc_c'])}, λs = {vc['lambda_s']:.3f}, ρw = {vc['rho_w']:.4f}]")
        if sh["required"]:
            L.append(f"- Av = {sh['Av']:.1f} mm², Av,min/s = {sh['Av_min_s']:.3f} mm²/mm")
            L.append(f"- **ปลอก DB{inp.get('stirrup_db', 10):.0f} {inp.get('stirrup_legs', 2)} ขา @ {sh['s']:.0f} mm** "
                     f"→ Vs = {V(sh['Vs'])}, **φVn = {V(sh['phiVn'])}**")
            L.append(f"- s,max ตามยาว = {sh['smax_long']:.0f} mm, ระยะขาตามขวาง = {sh['leg_spacing']:.0f} mm "
                     f"(≤ {sh['smax_trans']:.0f} mm)")
            L.append(f"- ขนาดหน้าตัด §22.5.1.2: Vu ≤ φ(Vc + 0.66√f′c·bw·d) = {V(sh['section_limit'])}")
        else:
            L.append(f"- {sh['note']} · φVc = {V(sh['phiVn'])}")
        L.append("")

    det = res["detailing"]
    L.append("## 3. รายละเอียดเหล็ก")
    L.append(f"- ระยะว่างขั้นต่ำ §25.2.1 = {det['clear_min']:.0f} mm")
    cr = det["crack"]
    L.append(f"- คุมรอยร้าว Table 24.3.2 (fs = 2fy/3, cc = {cr['cc']:.0f} mm): s,max = {cr['s_max']:.0f} mm, "
             f"ระยะจริง = {cr['s_provided']:.0f} mm → {_st(cr['ok'])}")
    if "comp_ties" in det:
        ct = det["comp_ties"]
        L.append(f"- ปลอกยึดเหล็กอัด §9.7.6.4: ปลอกปิด ≥ DB{ct['tie_db_min']:.0f}, s ≤ {ct['s_max']:.0f} mm, "
                 "มุม ≤ 135°, เหล็กไม่ถูกยึดห่าง ≤ 150 mm"
                 + ("" if ct["ok_size"] else " → ❌ ขนาดปลอกไม่พอ"))
    if det["skin_required"]:
        L.append("- ⚠️ h > 900 mm → ต้องมีเหล็กผิวข้าง §9.7.2.3 ในช่วง h/2 จากผิวรับแรงดึง")
    if det["Ktr_note"]:
        L.append("- ⚠️ fy ≥ 550 MPa → ช่วงฝังยึด/ทาบต้องมี Ktr ≥ 0.5db (§9.7.1.4, §25.4.2.2)")
    if "min_depth" in det:
        md = det["min_depth"]
        L.append(f"- ความลึกขั้นต่ำ Table 9.3.1.1: h,min = {md['h_min']:.0f} mm → "
                 + ("✅ ไม่ต้องคำนวณการแอ่นตัว" if md["ok"] else "⚠️ ต้องคำนวณการแอ่นตัว §24.2"))
    L.append("")

    dv = res["development"]
    ld = dv["ld"]
    L.append("## 4. ระยะฝังยึดและต่อทาบ (Ch.25) — เหล็กหลัก")
    L.append(f"- ℓd = **{ld['ld']:.0f} mm** ({ld['method']}, ψt = {ld['psi_t']}, ψe = {ld['psi_e']}, ψg = {ld['psi_g']}"
             + (", เหล็กบน" if dv["top_bar"] else "") + ")")
    h_ = dv["ldh"]
    L.append(f"- ℓdh (ขอ 90°/180°) = **{h_['ldh']:.0f} mm** (ψr = {h_['psi_r']}, ψo = {h_['psi_o']} ค่าอนุรักษ์, ψc = {h_['psi_c']:.3f})")
    L.append(f"- ต่อทาบรับแรงดึง Class A = {dv['lap_A']:.0f} mm, **Class B = {dv['lap_B']:.0f} mm**")
    if dv["lap_comp"]:
        L.append(f"- ℓdc = {dv['ldc']:.0f} mm, ต่อทาบรับแรงอัด = {dv['lap_comp']:.0f} mm")
    L.append("")

    L.append("## 5. สรุปสถานะ")
    L.append("| รายการ | สถานะ |\n|---|---|")
    L.append(f"| กำลังดัด φMn ≥ Mu | {_st(f['strength_ok'])} |")
    L.append(f"| Strain limit εt ≥ εty + 0.003 (§9.3.3.1) | {_st(f['strain_ok'])} |")
    L.append(f"| As ≥ As,min (§9.6.1.2) | {_st(f['As'] >= f['As_min'])} |")
    if sh:
        ck = sh.get("checks", {})
        L.append(f"| กำลังเฉือน φVn ≥ Vu | {_st(sh['phiVn'] >= sh['Vu'])} |")
        if ck:
            L.append(f"| ขนาดหน้าตัด §22.5.1.2 | {_st(ck['section_22.5.1.2'])} |")
            L.append(f"| Av ≥ Av,min | {_st(ck['Av_min_9.6.3'])} |")
            L.append(f"| ระยะปลอกตามยาว / ระยะขาตามขวาง | {_st(ck['s_long_9.7.6.2.2'])} / {_st(ck['s_trans_9.7.6.2.2'])} |")
    L.append(f"| คุมรอยร้าว (Table 24.3.2) | {_st(det['crack']['ok'])} |")
    if "min_depth" in det:
        L.append(f"| การแอ่นตัว | {'✅ ผ่านตาม Table 9.3.1.1' if det['min_depth']['ok'] else '⚠️ ยังไม่ตรวจ — ต้องคำนวณ §24.2'} |")
    else:
        L.append("| การแอ่นตัว | ยังไม่ตรวจ (ไม่ได้ให้ ℓn และสภาพจุดรองรับ) |")
    L.append("| ระยะฝังยึด/ทาบ | คำนวณแล้ว — ต้องระบุในแบบ |")
    L.append("| การตัดเหล็ก + integrity (§9.7.3, §9.7.7) | ยังไม่ตรวจ — ใช้ checklist |")
    L.append("")
    L.append("**Checklist การตัดเหล็กและ integrity (ต้องระบุในแบบ)**")
    L.append("- [ ] เหล็กยื่นเลยจุดที่ไม่ต้องใช้ ≥ max(d, 12db); เหล็กต่อเนื่องฝัง ≥ ℓd เลยจุดตัด (§9.7.3.3–9.7.3.4)")
    L.append("- [ ] เหล็กบวก ≥ 1/3 (ช่วงเดียว) / ≥ 1/4 (ต่อเนื่อง) เข้าจุดรองรับ ≥ 150 mm (§9.7.3.8.2)")
    L.append("- [ ] เหล็กลบ ≥ 1/3 เลยจุดดัดกลับ ≥ max(d, 12db, ℓn/16) (§9.7.3.8.4)")
    pos = res.get("integrity_position")
    if pos == "perimeter":
        L.append("- [ ] คานริม: เหล็กบวกต่อเนื่อง ≥ max(1/4, 2 เส้น), เหล็กลบ ≥ max(1/6, 2 เส้น), อยู่ในปลอกปิดตลอดช่วงว่าง (§9.7.7.1)")
    else:
        L.append("- [ ] Integrity: คานริม → เหล็กบวก ≥ max(1/4, 2 เส้น) + เหล็กลบ ≥ max(1/6, 2 เส้น) ในปลอกปิด; คานอื่น → เหล็กบวก ≥ max(1/4, 2 เส้น) หรือปลอกปิด (§9.7.7)")
    L.append("- [ ] ต่อเหล็ก integrity: เหล็กบวกที่/ใกล้จุดรองรับ, เหล็กลบที่/ใกล้กลางช่วง, ทาบ Class B หรือต่อกล ≥ 1.25fy (§9.7.7.5)")
    L.append("")
    L.append("_สมมติฐาน: ACI 318M-19 · หน่วยภายใน N–mm–MPa · Es = 200,000 MPa · "
             + ("ใช้ข้อยกเว้น εty = 0.002 (Grade 420)" if res['input'].get('grade420_exception') else "εty = fy/Es")
             + " · ค่าคงที่ SI ใน Ch.25 ยังไม่ได้เทียบกับเล่ม 318M จริง · ผลนี้ใช้ประกอบรายการคำนวณ วิศวกรผู้รับผิดชอบต้องตรวจและลงนาม_")
    return "\n".join(L)


def _jsonable(o):
    if isinstance(o, (Layer, FlexResult)):
        return asdict(o)
    if isinstance(o, float) and math.isinf(o):
        return None
    raise TypeError(type(o))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    with open(argv[1], encoding="utf-8") as fh:
        inp = json.load(fh)
    res = design_beam(inp)
    if "--json" in argv:
        print(json.dumps(res, default=_jsonable, ensure_ascii=False, indent=2))
    else:
        print(report(res))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
