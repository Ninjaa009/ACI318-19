"""Workflow driver for a floor of slab panels on beams (rectangular grid)."""
from __future__ import annotations

import copy
import math

from .rcsi import G, KSC, area
from . import coeffs
from .strip import B, as_required, choose, flexure, shear, h_min_two_way, h_min_one_way, crack_smax

DIRS = ("x", "y")


# ---------------------------------------------------------------- units

def to_si(inp):
    """kgf-m: spans m, loads kg/m², γ kg/m³, f′c/fy ksc.  SI: spans m, loads kPa, γ kN/m³, MPa.
    Internal: mm, N/mm² (MPa), N."""
    s = copy.deepcopy(inp)
    u = inp.get("units", "kgf-m")
    if u == "kgf-m":
        fq, fg = G * 1e-6, G * 1e-9
        s["materials"] = {k: v * KSC for k, v in inp["materials"].items() if v is not None}
        gc = inp.get("gamma_c", 2400.0)
    elif u == "SI":
        fq, fg = 1e-3, 1e-6
        gc = inp.get("gamma_c", 23.6)
    else:
        raise ValueError("units ต้องเป็น 'kgf-m' หรือ 'SI'")
    s["grid"] = {k: [v * 1000.0 for v in inp["grid"][k]] for k in DIRS}
    s["loads"] = {k: v * fq for k, v in inp["loads"].items()}
    s["gamma_c"] = gc * fg
    s["beam_width"] = inp.get("beam_width", 0.25) * 1000.0
    if inp.get("beam_depth") is not None:
        s["beam_depth"] = inp["beam_depth"] * 1000.0          # overall depth incl. slab, m → mm
    if inp.get("h") is not None:
        s["h"] = inp["h"] * (1000.0 if u == "kgf-m" and inp["h"] < 5 else 1.0)
    s["_units"] = u
    return s


# ---------------------------------------------------------------- geometry

LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"


def panel_name(i, j):
    return f"{LETTERS[j]}{LETTERS[j + 1]}-{i + 1}{i + 2}" if j + 1 < len(LETTERS) else f"({i},{j})"


def edge_name(k):
    d, i, j = k
    return f"แนว {i + 1} ช่วง {LETTERS[j]}–{LETTERS[j + 1]}" if d == "x" else f"แนว {LETTERS[j]} ช่วง {i + 1}–{i + 2}"


def _missing(si):
    out = set()
    nx, ny = len(si["grid"]["x"]), len(si["grid"]["y"])
    names = {panel_name(i, j): (i, j) for i in range(nx) for j in range(ny)}
    for m in si.get("missing", []):
        if isinstance(m, str):
            if m not in names:
                raise ValueError(f"missing: ไม่รู้จักแผง '{m}' (ใช้ชื่อแบบ AB-12)")
            out.add(names[m])
        else:
            out.add(tuple(m))
    return out


def panels(si):
    nx, ny = len(si["grid"]["x"]), len(si["grid"]["y"])
    missing = _missing(si)
    out = {}
    for i in range(nx):
        for j in range(ny):
            if (i, j) in missing:
                continue
            out[(i, j)] = {"i": i, "j": j, "name": panel_name(i, j), "Lx": si["grid"]["x"][i], "Ly": si["grid"]["y"][j]}
    for (i, j), p in out.items():
        p["cont"] = {"W": (i - 1, j) in out, "E": (i + 1, j) in out,
                     "S": (i, j - 1) in out, "N": (i, j + 1) in out}
    return out


def edge_key(i, j, side):
    """Shared key for the edge between two panels (gridline segment)."""
    return {"W": ("x", i, j), "E": ("x", i + 1, j), "S": ("y", i, j), "N": ("y", i, j + 1)}[side]


EDGES_OF = {"x": ("W", "E"), "y": ("S", "N")}      # edges crossed by bars running in that direction


# ---------------------------------------------------------------- moments

def panel_moments(si, p, h):
    """Factored moments per metre (N·mm) at the panel's edges and mid-span, per direction."""
    bw = si["beam_width"]
    w = p["wu"]
    short = "x" if p["Lx"] <= p["Ly"] else "y"
    long_ = "y" if short == "x" else "x"
    Lc = {"x": p["Lx"], "y": p["Ly"]}
    ln = {d: Lc[d] - bw for d in DIRS}
    S_eff = min(Lc[short], ln[short] + 2 * h)
    L_eff = min(Lc[long_], ln[long_] + 2 * h)
    m = S_eff / L_eff
    p.update(short=short, long=long_, m=m, ln=ln, S=S_eff)
    res = {"pos": {}, "neg": {}, "coef": {}}
    if m >= 0.5:
        n_disc = sum(not c for c in p["cont"].values())
        case = 1 + n_disc
        C = coeffs.two_way(case, m)
        p.update(kind="two-way", case=case)
        for d in DIRS:
            nc, nd, pos = C["short"] if d == short else C["long"]
            res["pos"][d] = pos * w * S_eff ** 2 * B
            res["coef"][d] = {"pos": pos}
            for e in EDGES_OF[d]:
                c = nc if p["cont"][e] else nd
                res["neg"][e] = c * w * S_eff ** 2 * B
                res["coef"][d][e] = c
    else:
        a, b = EDGES_OF[short]
        lnS = ln[short]
        na, nb, pos = coeffs.one_way(p["cont"][a], p["cont"][b], p.get("n_spans", 3), lnS)
        p.update(kind="one-way", case=None)
        res["pos"][short] = pos * w * lnS ** 2 * B
        res["pos"][long_] = 0.0
        res["neg"][a] = na * w * lnS ** 2 * B
        res["neg"][b] = nb * w * lnS ** 2 * B
        for e in EDGES_OF[long_]:
            res["neg"][e] = 0.0
        res["coef"][short] = {"pos": pos, a: na, b: nb}
        res["coef"][long_] = {"pos": 0.0}
    return res


def t_beam_I(bw, hb, hf, n_sides):
    """I of the slab-beam (kb ch08 §8.4.1 definition): slab each side = min(hb − hf, 4hf)."""
    ov = min(max(hb - hf, 0.0), 4 * hf) * n_sides
    parts = [(bw, hb, hb / 2), (ov, hf, hf / 2)]                      # (b, depth, centroid from top)
    A = sum(b * t for b, t, _ in parts)
    yc = sum(b * t * y for b, t, y in parts) / A
    return sum(b * t ** 3 / 12 + b * t * (y - yc) ** 2 for b, t, y in parts)


def alpha_edges(si, P, h):
    """αf = Ib/Is per edge (same Ec); Is uses the slab width between adjacent panel centrelines."""
    hb, bw = si.get("beam_depth"), si["beam_width"]
    if hb is None:
        return None
    out = {}
    for (i, j), p in P.items():
        for d in DIRS:
            for e in EDGES_OF[d]:
                k = edge_key(i, j, e)
                E = out.setdefault(k, {"width": 0.0, "n": 0})
                E["width"] += (p["Lx"] if d == "x" else p["Ly"]) / 2.0
                E["n"] += 1
    for k, E in out.items():
        if E["n"] == 1:
            E["width"] += bw / 2.0                                    # slab to outer face of edge beam
        Ib = t_beam_I(bw, hb, h, E["n"])
        E["alpha"] = Ib / (E["width"] * h ** 3 / 12.0)
    return out


def thickness_min(si, p):
    fy = si["materials"]["fy"]
    if p["kind"] == "two-way":
        lnl, lns = p["ln"][p["long"]], p["ln"][p["short"]]
        afm = p.get("alpha_fm", si.get("alpha_fm"))
        h, rule = h_min_two_way(lnl, lns, fy, afm)
        if afm is not None and "alpha_fm" in p:
            rule = f"αfm = {afm:.2f} → " + rule
        return h, f"T8.3.1.2: {rule}"
    a, b = EDGES_OF[p["short"]]
    n = p["cont"][a] + p["cont"][b]
    span = {"x": p["Lx"], "y": p["Ly"]}[p["short"]]
    return h_min_one_way(span, n, fy), f"T7.3.1.1: ต่อเนื่อง {n} ปลาย"


# ---------------------------------------------------------------- evaluation

def evaluate(si, h, bars=None):
    """bars None → design each location; else {'bottom': {db, s}, 'top': {db, s}} checked everywhere."""
    mats = si["materials"]
    fc, fy = mats["fc"], mats["fy"]
    cover = si.get("cover", 20.0)
    D_ = si["gamma_c"] * h + si["loads"].get("sdl", 0.0)
    L_ = si["loads"].get("ll", 0.0)
    f = si.get("factors")
    wu = (f["D"] * D_ + f["L"] * L_) if f else max(1.4 * D_, 1.2 * D_ + 1.6 * L_)     # 5.3.1
    opts = si.get("design", {}).get("db_options", [10, 12])
    P = panels(si)
    for (i, j), p in P.items():
        p["wu"], p["ws"] = wu, D_ + L_
        # spans in the line of the short direction (for Table 6.5.2 "two spans" vs "more")
        short = "x" if p["Lx"] <= p["Ly"] else "y"
        step = (1, 0) if short == "x" else (0, 1)
        n = 1
        for sg in (1, -1):
            k = 1
            while (i + sg * k * step[0], j + sg * k * step[1]) in P:
                n += 1
                k += 1
        p["n_spans"] = n
    alphas = alpha_edges(si, P, h)
    for (i, j), p in P.items():
        p["M"] = panel_moments(si, p, h)
        weak_edge = si.get("edge_beams_stiff") is False
        if alphas is not None:
            a = {e: alphas[edge_key(i, j, e)]["alpha"] for e in "WESN"}
            p["alpha"] = a
            p["alpha_fm"] = sum(a.values()) / 4.0
            weak_edge = any(a[e] < 0.8 for e in "WESN" if not p["cont"][e])
        p["h_min"], p["h_rule"] = thickness_min(si, p)
        if p["h_min"] is None:
            continue
        if p["kind"] == "two-way" and weak_edge and not all(p["cont"].values()):
            p["h_min"] *= 1.10
            p["h_rule"] += " ×1.10 (ขอบไม่ต่อเนื่อง คานขอบ αf < 0.8)"

    def d_of(outer):
        return (lambda db: h - cover - db / 2) if outer else (lambda db: h - cover - 1.5 * db)

    def s_max(kind):
        return {"two-way": min(2 * h, 450.0), "one-way": min(3 * h, 450.0),
                "st": min(5 * h, 450.0)}[kind]                    # 8.7.2.2 / 7.7.2.3 / 24.4.3.3

    def pick(Mu, outer, kind, which):
        if bars is None:
            return choose(Mu, d_of(outer), h, fc, fy, opts, s_max(kind))
        b = bars[which]
        d = d_of(outer)(b["db"])
        r = flexure(Mu, d, h, fc, fy, b["db"], b["s"])
        r.update(db=b["db"], s=b["s"], As_req=as_required(Mu, d, fc, fy), s_ok=b["s"] <= s_max(kind) + 1e-9)
        r["ok"] = r["ok"] and r["s_ok"]
        return r

    ok = True
    # bottom (positive) steel per panel
    for p in P.values():
        p["bot"] = {}
        for d in DIRS:
            kind = "st" if (p["kind"] == "one-way" and d == p["long"]) else p["kind"]
            r = pick(p["M"]["pos"][d], d == p["short"], kind, "bottom")
            if r:
                r["role"] = "กันร้าว (S&T)" if kind == "st" else "รับแรงดัด"
            p["bot"][d] = r
            ok &= bool(r) and r.get("ok", True)
    # top steel per edge (max of the two sides)
    edges = {}
    for (i, j), p in P.items():
        for d in DIRS:
            for e in EDGES_OF[d]:
                k = edge_key(i, j, e)
                E = edges.setdefault(k, {"dir": d, "Mu": 0.0, "sides": [], "short_both": True, "kind": "one-way"})
                E["Mu"] = max(E["Mu"], p["M"]["neg"][e])
                E["sides"].append(((i, j), e, p["M"]["neg"][e]))
                E["short_both"] &= (d == p["short"])
                if p["kind"] == "two-way":
                    E["kind"] = "two-way"
    for k, E in edges.items():
        E["cont"] = len(E["sides"]) == 2
        if E["Mu"] <= 0:
            E["top"] = None
            continue
        r = pick(E["Mu"], E["short_both"], E["kind"], "top")
        E["top"] = r
        ok &= bool(r) and r.get("ok", True)
        if E["cont"]:
            a, b = (s[2] for s in E["sides"])
            E["unbalanced"] = min(a, b) < 0.8 * max(a, b)
    # shear per panel (short direction edges)
    for (i, j), p in P.items():
        d = p["short"]
        lnS = p["ln"][d]
        p["shear"] = []
        for e in EDGES_OF[d]:
            E = edges[edge_key(i, j, e)]
            if p["kind"] == "one-way":
                other = [x for x in EDGES_OF[d] if x != e][0]
                fac = 1.15 if (p["cont"][e] and not p["cont"][other]) else 1.0      # T6.5.4
            else:
                fac = 1.0
            top = E["top"]
            dd = d_of(E["short_both"])(top["db"] if top else opts[0])
            Vu = (fac * p["wu"] * lnS / 2 - p["wu"] * dd) * B
            As_t = top["As"] if top else 0.0018 * B * h
            r = shear(Vu, dd, As_t, fc)
            r.update(edge=e, factor=fac, d=dd)
            p["shear"].append(r)
            ok &= r["ok"]
        p["h_ok"] = p["h_min"] is not None and h >= p["h_min"] - 1e-9
        # crack control, one-way slabs (T24.3.2)
        if p["kind"] == "one-way":
            sm = crack_smax(fy, cover)
            p["crack"] = {"s_max": sm, "ok": all(x["s"] <= sm + 1e-9 for x in
                                                [p["bot"][p["short"]]] if x)}
    # corner reinforcement at exterior corners of two-way panels (§8.7.3)
    corners = []
    for (i, j), p in P.items():
        if p["kind"] != "two-way":
            continue
        for e1, e2 in (("W", "S"), ("W", "N"), ("E", "S"), ("E", "N")):
            if not p["cont"][e1] and not p["cont"][e2]:
                if "alpha" in p and max(p["alpha"][e1], p["alpha"][e2]) <= 1.0:
                    continue                                          # §8.7.3: only if an edge beam αf > 1.0
                Mu = max(p["M"]["pos"].values())
                r = choose(Mu, d_of(False), h, fc, fy, opts, min(2 * h, 450.0))
                corners.append({"panel": (i, j), "corner": e1 + e2, "Mu": Mu,
                                "extent": max(p["Lx"], p["Ly"]) / 5.0, "bars": r})
    # loads on supporting beams, per gridline segment (uniform equivalent, per metre of beam)
    beams = {}
    for (i, j), p in P.items():
        Scc = {"x": p["Lx"], "y": p["Ly"]}[p["short"]]
        for d in DIRS:
            for e in EDGES_OF[d]:
                k = edge_key(i, j, e)
                if p["kind"] == "two-way":
                    k_short, k_long = coeffs.beam_load_factors(p["m"])
                    # edges crossed by short-direction bars are the long beams
                    kf, how = (k_long, "Method 2: wS/3·(3−m²)/2") if d == p["short"] else (k_short, "Method 2: wS/3")
                    S_ = p["S"]
                elif d == p["short"]:
                    kf, how, S_ = 0.5, "ทางเดียว: wS/2", Scc
                else:
                    kf, how, S_ = 1.0 / 3.0, "ทางเดียว คานด้านสั้น: wS/3 (เผื่อ)", Scc
                bm = beams.setdefault(k, {"len": p["Ly"] if k[0] == "x" else p["Lx"], "ws": 0.0, "wu": 0.0, "from": []})
                bm["ws"] += kf * p["ws"] * S_
                bm["wu"] += kf * p["wu"] * S_
                bm["from"].append(((i, j), how))
    return {"h": h, "wu": wu, "alphas": alphas, "D": D_, "L": L_, "panels": P, "edges": edges, "corners": corners,
            "beams": beams, "ok": ok and all(p["h_ok"] for p in P.values()),
            "flex_shear_ok": ok}


def design(si):
    D = si.get("design", {})
    hmin_user = D.get("h_min", 100.0)
    probe = evaluate(si, max(hmin_user, 100.0))
    if any(p["h_min"] is None for p in probe["panels"].values()):
        return "flat"
    h = max(hmin_user, max(p["h_min"] for p in probe["panels"].values()))
    h = math.ceil(h / 10.0 - 1e-9) * 10.0
    for _ in range(40):
        r = evaluate(si, h)
        if r["flex_shear_ok"] and all(p["h_ok"] for p in r["panels"].values()):
            return r
        h += 10.0
    return None


def run(inp):
    si = to_si(inp)
    res = {"input": inp, "si": si, "mode": inp.get("mode", "design"), "messages": []}
    if si.get("sdc") in ("D", "E", "F"):
        res["messages"].append(("WARN", "18.2", "SDC D–F: พื้นที่เป็นไดอะแฟรมต้องตรวจ §18.12 เพิ่ม — ยังไม่ตรวจ"))
    afm = si.get("alpha_fm")
    if afm is not None and afm <= 0.2:
        res["messages"].append(("FAIL", "8.3.1.2", "αfm ≤ 0.2 = พื้นไร้คาน (flat plate) — นอกขอบเขตสกิลนี้"))
        res["stopped"] = True
        return res
    if res["mode"] == "check" and (si.get("h") is None or not si.get("bars")):
        res["messages"].append(("FAIL", "", "โหมด check ต้องให้ h (mm) และ bars {bottom: {db, s}, top: {db, s}}"))
        res["stopped"] = True
        return res
    if res["mode"] == "design":
        r = design(si)
        if r == "flat":
            res["messages"].append(("FAIL", "8.3.1.2", "คานเล็กจน αfm ≤ 0.2 ในบางแผง = พื้นไร้คาน — นอกขอบเขตสกิลนี้"))
            res["stopped"] = True
            return res
        if r is None:
            res["messages"].append(("FAIL", "8.3", "หาความหนาที่ผ่านไม่ได้ภายใน 400 mm — ตรวจช่วงและน้ำหนัก"))
            res["stopped"] = True
            return res
    else:
        r = evaluate(si, si["h"], si["bars"])
    res.update(r)
    msgs = res["messages"]
    msgs.append(("INFO", "8.2.1", "โมเมนต์พื้นสองทางใช้ตารางสัมประสิทธิ์ Method 2 (ACI 318-63 ภาคผนวก A) "
                 "เป็นวิธีวิเคราะห์ที่ §8.2.1 ยอมให้ — ไม่ใช่ข้อความของ 318-19"))
    if si.get("alpha_fm") is None and si.get("beam_depth") is None:
        msgs.append(("WARN", "8.3.1.2", "ไม่ได้ให้ความลึกคาน (beam_depth) หรือ αfm → สมมติคานแข็ง αfm > 2, "
                     "คานขอบ αf ≥ 0.8 และมีเหล็กมุม — ใส่ beam_depth เพื่อคำนวณ αf จริง"))
    for k, p in sorted(r["panels"].items()):
        if p["kind"] != "one-way":
            continue
        if r["L"] > 3 * r["D"]:
            msgs.append(("WARN", "6.5.1", f"แผง {p['name']}: L > 3D — สัมประสิทธิ์ Table 6.5.2 ใช้ไม่ได้ ต้องวิเคราะห์โครงสร้าง"))
        if p["n_spans"] < 2:
            msgs.append(("INFO", "6.5.1", f"แผง {p['name']}: ช่วงเดียว → ใช้สถิตศาสตร์ wℓn²/8 (Table 6.5.2 ต้อง ≥ 2 ช่วง) "
                         "เหล็กบนขอบใช้ 1/24 เป็นอย่างน้อย"))
        st = (1, 0) if p["short"] == "x" else (0, 1)
        for sg in (1, -1):
            q = r["panels"].get((k[0] + sg * st[0], k[1] + sg * st[1]))
            if q is not None and q["kind"] == "one-way":
                a, b = p["ln"][p["short"]], q["ln"][p["short"]]
                if max(a, b) > 1.2 * min(a, b):
                    msgs.append(("WARN", "6.5.1", f"แผง {p['name']}–{q['name']}: ช่วงข้างเคียงยาวต่างกัน > 20% — Table 6.5.2 ใช้ไม่ได้โดยตรง"))
    res["status"] = {"thickness": all(p["h_ok"] for p in r["panels"].values()),
                     "flexure_shear": r["flex_shear_ok"]}
    return res
