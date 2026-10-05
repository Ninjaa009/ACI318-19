"""Workflow driver for one beam span: sections L (left face), M (midspan), R (right face)."""
from __future__ import annotations

import copy
import math

from .rcsi import G, KSC, area
from .section import Beam, As, split
from .flexure import check_face, analyze
from .shear import zone, design_zone, exempt_9631
from .detailing import (crack_smax, min_depth, comp_tie_smax, imf_hoop_smax, neg_extent,
                        development)

SECTIONS = ("left", "mid", "right")


# ---------------------------------------------------------------- units

def to_si(inp):
    s = copy.deepcopy(inp)
    units = inp.get("units", "kgf-m")
    if units == "kgf-m":
        s["section"] = {k: v * 1000.0 for k, v in inp["section"].items()}
        s["materials"] = {k: v * KSC for k, v in inp["materials"].items() if v is not None}
        fF, fM, fw = G, G * 1000.0, G / 1000.0          # kgf, kgf·m, kgf/m → N, N·mm, N/mm
    elif units == "SI":
        fF, fM, fw = 1e3, 1e6, 1.0                       # kN, kN·m, kN/m
    else:
        raise ValueError("units ต้องเป็น 'kgf-m' หรือ 'SI'")
    sp = s.setdefault("span", {})
    for k in ("ln", "end_zone", "tf", "lateral_brace"):
        if sp.get(k) is not None:
            sp[k] = sp[k] * 1000.0
    if sp.get("wu") is not None:
        sp["wu"] *= fw
    for cb in s["combos"]:
        for k in ("M_left", "M_mid", "M_right"):
            cb[k] = (cb.get(k) or 0.0) * fM
        for k in ("V_left", "V_right", "V_2E"):
            if cb.get(k) is not None:
                cb[k] = abs(cb[k]) * fF
    sc = s.get("scope", {})
    if sc.get("Pu") is not None:
        sc["Pu"] *= fF
    s["_units"] = units
    return s


# ---------------------------------------------------------------- demand envelope

def envelope(si):
    """Hogging (top) and sagging (bottom) moment demand at each section, plus shear."""
    env = {k: {"top": 0.0, "bot": 0.0, "top_by": "—", "bot_by": "—"} for k in SECTIONS}
    for cb in si["combos"]:
        for k in SECTIONS:
            m = cb[f"M_{k}"]
            face = "top" if m < 0 else "bot"
            if abs(m) > env[k][face]:
                env[k][face], env[k][face + "_by"] = abs(m), cb.get("name", "")
    return env


def zone_shear(si, ze):
    """Shear demand: end zones use V at the critical section; the middle zone uses V at the
    end-zone boundary from a straight shear line (+VL at left, −VR at right) unless
    span.V_shape == 'constant' (then the end values)."""
    ln = si["span"]["ln"]
    shape = si["span"].get("V_shape", "gravity")
    VL = max((cb.get("V_left") or 0) for cb in si["combos"])
    VR = max((cb.get("V_right") or 0) for cb in si["combos"])
    vm = 0.0
    for cb in si["combos"]:
        a, b = cb.get("V_left") or 0, cb.get("V_right") or 0
        if shape == "constant":
            vm = max(vm, a, b)
        else:
            f = lambda x: a - (a + b) * x / ln
            vm = max(vm, abs(f(ze)), abs(f(ln - ze)))
    return {"left": VL, "mid": vm, "right": VR}


# ---------------------------------------------------------------- evaluation of a full layout

def flexure_all(beam, bars, env):
    out = {}
    for k in SECTIONS:
        t, bo = bars[k]["top"], bars[k]["bot"]
        out[k] = {"top": check_face(beam, t, bo, env[k]["top"]),
                  "bot": check_face(beam, bo, t, env[k]["bot"])}
    return out


def nominal(beam, tension, comp):
    if not tension:
        return 0.0
    return analyze(beam, beam.layers(tension), beam.layers(comp) if comp else [])["Mn"]


def seismic_beam(si, beam, bars):
    """§18.3.2 (OMF) and §18.4.2 (IMF) longitudinal rules + IMF design shear."""
    system = si.get("system")
    if system not in ("OMF", "IMF"):
        return None
    cont_top = min(sum(n for n, _ in bars[k]["top"]) for k in SECTIONS)
    cont_bot = min(sum(n for n, _ in bars[k]["bot"]) for k in SECTIONS)
    As_bot = [As(bars[k]["bot"]) for k in SECTIONS]
    r = {"system": system, "cont_top": cont_top, "cont_bot": cont_bot,
         "two_bars_ok": cont_top >= 2 and cont_bot >= 2,
         "bot_quarter_ok": min(As_bot) >= 0.25 * max(As_bot) - 1e-9}
    if system == "IMF":
        Mn = {k: {"neg": nominal(beam, bars[k]["top"], bars[k]["bot"]),
                  "pos": nominal(beam, bars[k]["bot"], bars[k]["top"])} for k in SECTIONS}
        face_max = max(Mn[k][f] for k in ("left", "right") for f in ("neg", "pos"))
        r["Mn"] = Mn
        r["third_ok"] = all(Mn[k]["pos"] >= Mn[k]["neg"] / 3.0 - 1e-6 for k in ("left", "right"))
        r["fifth_ok"] = all(Mn[k][f] >= face_max / 5.0 - 1e-6 for k in SECTIONS for f in ("neg", "pos"))
        ln = si["span"]["ln"]
        wu = si["span"].get("wu")
        Vmn = max(Mn["left"]["neg"] + Mn["right"]["pos"], Mn["left"]["pos"] + Mn["right"]["neg"]) / ln
        r["V_mn"] = Vmn + (wu * ln / 2.0 if wu else 0.0)
        r["wu_given"] = wu is not None
        v2e = [cb["V_2E"] for cb in si["combos"] if cb.get("V_2E") is not None]
        r["V_2E"] = max(v2e) if v2e else None
        r["Ve"] = min(r["V_mn"], r["V_2E"]) if r["V_2E"] else r["V_mn"]
    return r


def section_d(beam, bars, k):
    """Effective depth for shear at a section: the smaller of top/bottom tension d."""
    ds = []
    for face in ("top", "bot"):
        L = beam.layers(bars[k][face]) if bars[k][face] else []
        if L:
            ds.append(beam.h - sum(A * y for A, y, *_ in L) / sum(A for A, *_ in L))
    return min(ds), min(As(bars[k]["top"]), As(bars[k]["bot"]))


def shear_all(si, beam, bars, st, design=False):
    """Stirrups by zone.  st = {db, legs, s_end, s_mid, end_zone}."""
    sp = si["span"]
    ln = sp["ln"]
    system = si.get("system")
    ze = st.get("end_zone") or max(2 * beam.h, ln / 4.0)
    if system == "IMF":
        ze = max(ze, 2 * beam.h)                                         # 18.4.2.4
    Vz = zone_shear(si, ze)
    seis = seismic_beam(si, beam, bars)
    ex = exempt_9631(beam, sp.get("integral_slab"), sp.get("tf"))
    db_comp = min(db for k in SECTIONS for f in ("top", "bot") for _, db in bars[k][f])
    ct = comp_tie_smax(beam, db_comp)
    out = {"end_zone": ze, "zones": {}, "exempt": ex}
    for k in SECTIONS:
        d, Ast = section_d(beam, bars, k)
        Vu = Vz[k]
        extra = _extra_for(si, beam, bars, k, st, seis, ct, db_comp, d)
        if seis and system == "IMF":
            Vu = max(Vu, seis["Ve"])                                     # 18.4.2.3
        if design:
            z = design_zone(beam, Vu, d, Ast, st["db"], st.get("legs", 2), si.get("vc_eq", "a"),
                            si.get("lam", 1.0), ex, extra)
        else:
            s = st["s_mid"] if k == "mid" else st["s_end"]
            z = zone(beam, Vu, d, Ast, st["db"], st.get("legs", 2), s, si.get("vc_eq", "a"),
                     si.get("lam", 1.0), ex, extra)
        out["zones"][k] = z
    if design:                                     # one spacing for both end zones
        ends = [out["zones"]["left"], out["zones"]["right"]]
        gov = min(ends, key=lambda z: (z["s"] / z["legs"]))
        for k in ("left", "right"):
            d, Ast = section_d(beam, bars, k)
            out["zones"][k] = zone(beam, out["zones"][k]["Vu"], d, Ast, st["db"], gov["legs"], gov["s"],
                                   si.get("vc_eq", "a"), si.get("lam", 1.0), ex,
                                   _extra_for(si, beam, bars, k, st, seis, ct, db_comp, d))
    out["seismic"] = seis
    out["ok"] = all(z["ok"] for z in out["zones"].values())
    return out


def _extra_for(si, beam, bars, k, st, seis, ct, db_comp, d):
    if seis and si.get("system") == "IMF":
        if k != "mid":
            lim = imf_hoop_smax(d, db_comp, st["db"])
            return (min(ct, lim), "§18.4.2.4 hoop ปลายคาน") if lim < ct else (ct, "§9.7.6.4 ยึดเหล็กอัด")
        return (min(ct, d / 2.0), "§18.4.2.5 ≤ d/2")
    return (ct, "§9.7.6.4 ยึดเหล็กอัด")


def detailing_all(si, beam, bars, env):
    out = {"layers": {}, "crack": {}}
    for k in SECTIONS:
        for f in ("top", "bot"):
            b_ = bars[k][f]
            if not b_:
                continue
            n1, db = b_[0]
            fits = all(n <= beam.per_layer(d_) for n, d_ in b_) and len(b_) <= 2
            cc_sp, clear = beam.spacing_outer(b_)
            out["layers"][(k, f)] = {"fits": fits, "clear": clear, "clear_min": beam.clear_min(db),
                                     "per_layer": beam.per_layer(db)}
            if env[k][f] > 0:
                smax = crack_smax(beam, beam.cover + beam.ds)
                out["crack"][(k, f)] = {"s": cc_sp, "s_max": smax, "ok": cc_sp <= smax + 1e-9}
    sp = si["span"]
    if sp.get("support"):
        hm = min_depth(sp["ln"], sp["support"], beam.fy_spec)
        out["min_depth"] = {"h_min": hm, "ok": beam.h >= hm - 1e-9}
    out["skin"] = beam.h > 900.0
    out["Ktr"] = beam.fy_spec >= 550.0
    return out


def cutoffs(si, beam, bars, ld_top):
    """Top bars at each support: continuous bars run through; the extra bars stop at
    max(x where continuous bars suffice + max(d, 12db), ℓd from the face), and if the
    continuous bars are < 1/3 of the support steel, beyond the inflection point by
    max(d, 12db, ℓn/16) (§9.7.3.3, §9.7.3.4, §9.7.3.8.4)."""
    ln = si["span"]["ln"]
    Ms = [(cb["M_left"], cb["M_mid"], cb["M_right"]) for cb in si["combos"]]
    mid_top = bars["mid"]["top"]
    out = {}
    for k in ("left", "right"):
        top = bars[k]["top"]
        n_sup = sum(n for n, _ in top)
        n_cont = sum(n for n, _ in mid_top)
        db = max(d for _, d in top)
        r = analyze(beam, beam.layers(top), beam.layers(bars[k]["bot"]))
        d = r["d"]
        x_ip = neg_extent(Ms, ln, k, 0.0)
        cap_cont = check_face(beam, mid_top, bars[k]["bot"], 0.0)["phiMn"] if mid_top else 0.0
        x_cont = neg_extent(Ms, ln, k, cap_cont)
        ext = max(d, 12 * db)
        L = max(x_cont + ext, ld_top) if n_sup > n_cont else 0.0
        third = n_cont >= n_sup / 3.0 - 1e-9
        if n_sup > n_cont and not third:
            L = max(L, x_ip + max(d, 12 * db, ln / 16.0))
        out[k] = {"x_ip": x_ip, "x_cont": x_cont, "extra": n_sup - n_cont, "L": L,
                  "third_ok": third, "ld": ld_top, "half_span": L > ln / 2}
    return out


def evaluate(si, beam, bars, st, design=False):
    env = envelope(si)
    res = {"beam": beam, "bars": bars, "env": env}
    res["flex"] = flexure_all(beam, bars, env)
    res["shear"] = shear_all(si, beam, bars, st, design)
    res["det"] = detailing_all(si, beam, bars, env)
    res["dev"] = {}
    for face in ("top", "bot"):
        db = max(d for k in SECTIONS for _, d in bars[k][face])
        clear = min(beam.spacing_outer(bars[k][face])[1] for k in SECTIONS if bars[k][face])
        good = clear >= db - 1e-9 and beam.cover + beam.ds >= db - 1e-9   # Table 25.4.2.3 row 1
        top = face == "top" and (beam.h - beam.cover - beam.ds - db / 2) > 300.0   # ψt (25.4.2.5)
        res["dev"][face] = development(beam, db, top, si.get("epoxy"), si.get("lam", 1.0), good)
        res["dev"][face]["good"] = good
    res["cut"] = cutoffs(si, beam, bars, res["dev"]["top"]["ld"])
    pos = si["span"].get("position", "unknown")
    cont_bot = min(sum(n for n, _ in bars[k]["bot"]) for k in SECTIONS)
    cont_top = min(sum(n for n, _ in bars[k]["top"]) for k in SECTIONS)
    max_bot = max(sum(n for n, _ in bars[k]["bot"]) for k in SECTIONS)
    max_top = max(sum(n for n, _ in bars[k]["top"]) for k in ("left", "right"))
    integ = {"position": pos,
             "bot_ok": cont_bot >= max(2, math.ceil(max_bot / 4.0))}
    if pos == "perimeter":
        integ["top_ok"] = cont_top >= max(2, math.ceil(max_top / 6.0))
    res["integrity"] = integ
    seis = res["shear"]["seismic"]
    F = res["flex"]
    D = res["det"]
    res["status"] = {
        "flexure": all(F[k][f]["ok"] for k in SECTIONS for f in ("top", "bot")),
        "shear": res["shear"]["ok"],
        "detailing": all(v["fits"] and v["clear"] >= v["clear_min"] - 1e-9 for v in D["layers"].values())
                     and all(v["ok"] for v in D["crack"].values()),
        "integrity": all(v for k, v in integ.items() if k.endswith("_ok")),
    }
    if seis:
        res["status"]["seismic"] = seis["two_bars_ok"] and seis["bot_quarter_ok"] and \
            (seis.get("third_ok", True) and seis.get("fifth_ok", True))
    return res


# ---------------------------------------------------------------- design

def _min_bars(beam, db_opts, max_layers, test, start=2):
    """Smallest As (over sizes/counts) that passes test(bars) → bars or None."""
    cands = []
    for db in db_opts:
        for n in range(start, beam.per_layer(db) * max_layers + 1):
            b = split(n, db, beam, max_layers)
            if b:
                cands.append((n * area(db), n, db, b))
    cands.sort(key=lambda c: (c[0], c[1]))
    for _, _, _, b in cands:
        if test(b):
            return b
    return None


def design(si, beam):
    env = envelope(si)
    D = si.get("design", {})
    opts = D.get("db_options", [16, 20, 25])
    ml = D.get("max_layers", 2)
    system = si.get("system")
    hanger = [[2, min(opts)]]
    msgs = []

    # 1) bottom bars: continuous, sized for the largest sagging moment (top = 2 hangers as comp.)
    def bot_ok(b):
        return all(check_face(beam, b, hanger, env[k]["bot"])["ok"] for k in SECTIONS
                   if env[k]["bot"] > 0) and check_face(beam, b, hanger, 0)["tension_ok"]
    bot = _min_bars(beam, opts, ml, bot_ok)
    if bot is None:
        return None, ["ไม่มีเหล็กล่างที่ผ่าน — ขยายหน้าตัด"]

    # 2) continuous top bars: ≥ 2, carry any hogging at midspan
    def top_mid_ok(b):
        return env["mid"]["top"] <= 0 or check_face(beam, b, bot, env["mid"]["top"])["ok"]
    top_c = _min_bars(beam, opts, 1, top_mid_ok) or [[2, min(opts)]]
    db_t = top_c[0][1]

    # 3) top bars at supports: continuous + extra bars of the same size
    tops = {}
    for k in ("left", "right"):
        nc = sum(n for n, _ in top_c)
        found = None
        for n in range(nc, beam.per_layer(db_t) * ml + 1):
            b = split(n, db_t, beam, ml)
            if b and (env[k]["top"] <= 0 or check_face(beam, b, bot, env[k]["top"])["ok"]):
                found = b
                break
        if found is None:                       # try a bigger size for the whole top set
            for dbx in [x for x in opts if x > db_t]:
                for n in range(2, beam.per_layer(dbx) * ml + 1):
                    b = split(n, dbx, beam, ml)
                    if b and check_face(beam, b, bot, env[k]["top"])["ok"]:
                        found = b
                        break
                if found:
                    break
        if found is None:
            return None, [f"ไม่มีเหล็กบนที่ผ่านที่จุดรองรับ{'ซ้าย' if k == 'left' else 'ขวา'} — ขยายหน้าตัด"]
        tops[k] = found
    # keep one bar size on top: if a support needed a bigger size, re-run continuous with it
    db_t = max(tops["left"][0][1], tops["right"][0][1], db_t)
    if top_c[0][1] != db_t:
        top_c = [[max(2, sum(n for n, _ in top_c)), db_t]]
    bars = {"left": {"top": tops["left"], "bot": bot}, "mid": {"top": top_c, "bot": bot},
            "right": {"top": tops["right"], "bot": bot}}

    # 4) perimeter integrity (top continuous ≥ 1/6 of support steel) and IMF Mn rules
    for _ in range(20):
        max_top = max(sum(n for n, _ in bars[k]["top"]) for k in ("left", "right"))
        need_c = max(2, math.ceil(max_top / 6.0)) if si["span"].get("position") == "perimeter" else 2
        if sum(n for n, _ in bars["mid"]["top"]) < need_c:
            bars["mid"]["top"] = split(need_c, db_t, beam, 1) or bars["mid"]["top"]
            msgs.append(f"เพิ่มเหล็กบนต่อเนื่องเป็น {need_c} เส้น (§9.7.7.1(b))")
            continue
        if system == "IMF":
            s = seismic_beam(si, beam, bars)
            if not (s["third_ok"] and s["fifth_ok"]):
                nb = sum(n for n, _ in bot) + 1
                nbars = split(nb, bot[0][1], beam, ml)
                if nbars is None:
                    return None, ["IMF: เพิ่มเหล็กล่างให้ Mn⁺ ≥ Mn⁻/3 ไม่ได้ — ขยายหน้าตัด"]
                bot = nbars
                for k in SECTIONS:
                    bars[k]["bot"] = bot
                msgs.append(f"IMF: เพิ่มเหล็กล่างเป็น {nb} เส้นให้ Mn⁺ ≥ Mn⁻/3 และ ≥ Mn,max/5 (§18.4.2.2)")
                continue
            if sum(n for n, _ in bars["mid"]["top"]) < 2:
                bars["mid"]["top"] = [[2, db_t]]
                continue
        break
    return bars, msgs


# ---------------------------------------------------------------- entry point

def scope(si, beam):
    msgs = []
    sp, sc = si["span"], si.get("scope", {})
    if si.get("system") == "SMF":
        msgs.append(("FAIL", "18.6", "คาน SMF ต้องใช้ §18.6 ครบชุด — นอกขอบเขต"))
    if si.get("system") not in (None, "OMF", "IMF", "SMF"):
        msgs.append(("FAIL", "18.2", "system ต้องเป็น null / OMF / IMF"))
    if sp["ln"] <= 4 * beam.h:
        msgs.append(("FAIL", "9.9.1.1", f"ℓn = {sp['ln']:.0f} ≤ 4h = {4 * beam.h:.0f} mm → deep beam (Ch.23)"))
    if sc.get("conc_load_within_2h"):
        msgs.append(("FAIL", "9.9.1.1", "แรงจุดภายใน 2h จากผิวจุดรองรับ → deep beam"))
    if (sc.get("Pu") or 0) >= 0.10 * beam.fc * beam.Ag:
        msgs.append(("FAIL", "9.5.2.2", "Pu ≥ 0.10f′cAg → ออกแบบแบบเสา (§22.4)"))
    if sc.get("Tu"):
        msgs.append(("WARN", "9.5.4.1", "มีแรงบิด — ต้องยืนยัน Tu < φTth มิฉะนั้นนอกขอบเขต"))
    lb = sp.get("lateral_brace")
    if lb is not None and lb > 50 * beam.b:
        msgs.append(("FAIL", "9.2.3.1", f"ระยะค้ำยันด้านข้าง {lb:.0f} mm > 50b"))
    return msgs


def run(inp):
    si = to_si(inp)
    sec, mat = si["section"], si["materials"]
    st = dict({"db": 10.0, "legs": 2}, **si.get("stirrups", {}))
    if st.get("end_zone") is not None:
        st["end_zone"] *= 1000.0                                         # m → mm (both unit systems)
    beam = Beam(sec["b"], sec["h"], mat["fc"], mat["fy"], mat.get("fyt"), si.get("cover", 40.0),
                st["db"], si.get("dagg", 20.0), si.get("grade420_exception", False))
    res = {"input": inp, "si": si, "mode": inp.get("mode", "design"), "beam": beam, "messages": []}
    res["messages"] += scope(si, beam)
    if any(m[0] == "FAIL" for m in res["messages"]):
        res["stopped"] = True
        return res
    if beam.ds < 10.0 - 0.6:                                             # 9.7.6.4.2 / 25.7.2.2
        if res["mode"] == "design":
            res["messages"].append(("WARN", "9.7.6.4.2", f"ปลอก DB{beam.ds:g} เล็กกว่า DB10 ที่ต้องใช้ยึดเหล็กอัด → ใช้ DB10"))
            st["db"] = 10.0
            beam = Beam(sec["b"], sec["h"], mat["fc"], mat["fy"], mat.get("fyt"), si.get("cover", 40.0),
                        10.0, si.get("dagg", 20.0), si.get("grade420_exception", False))
            res["beam"] = beam
        else:
            res["messages"].append(("WARN", "9.7.6.4.2", f"ปลอก DB{beam.ds:g} < DB10 — ยึดเหล็กอัดไม่ได้ตาม §9.7.6.4 "
                                    "(กำลังดัดที่นับเหล็กผิวตรงข้ามเป็นเหล็กอัดจึงไม่ถูกต้อง)"))
            res["tie_small"] = True
    if res["mode"] == "design":
        bars, notes = design(si, beam)
        res["messages"] += [("INFO", "", n) for n in notes]
        if bars is None:
            res["messages"].append(("FAIL", "9.5", notes[-1] if notes else "ออกแบบไม่ได้"))
            res["stopped"] = True
            return res
        out = evaluate(si, beam, bars, st, design=True)
    else:
        bars = {k: {"top": si["bars"][k]["top"], "bot": si["bars"][k]["bot"]} for k in SECTIONS}
        out = evaluate(si, beam, bars, st)
    res.update(out)
    if res.get("tie_small"):
        res["status"]["detailing"] = False
    return res
