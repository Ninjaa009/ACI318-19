"""Workflow driver — steps 0–10 (see SKILL.md and kb/INDEX.md)."""
from __future__ import annotations

import copy
import math

from .section import Column
from .pmm import capacity
from .stability import stability_index, slenderness
from .shear import shear_direction, biaxial, seismic_shear_demand
from .detailing import (longitudinal_limits, tie_limits, imf_end_zone, splices,
                        floor_concrete, footing_dowels)

G = 9.80665
KSC = 0.0980665


# ---------------------------------------------------------------- units

def to_si(inp):
    """Return a deep copy in N, mm, MPa.  kgf-m input: section in m, stresses in
    ksc, forces kgf, moments kgf·m.  SI input: section in mm, MPa, kN, kN·m.
    Member/story lengths are in m for both."""
    s = copy.deepcopy(inp)
    units = inp.get("units", "kgf-m")
    if units == "kgf-m":
        s["section"] = {k: v * 1000 for k, v in inp["section"].items()}
        s["materials"] = {k: v * KSC for k, v in inp["materials"].items() if v is not None}
        if inp.get("joint", {}).get("fc_floor") is not None:
            s["joint"]["fc_floor"] = inp["joint"]["fc_floor"] * KSC
        fF, fM = G, G * 1000.0
    elif units == "SI":
        fF, fM = 1e3, 1e6
    else:
        raise ValueError("units ต้องเป็น 'kgf-m' หรือ 'SI'")
    ln = s.get("length", {})
    for k in ("lu", "lux", "luy", "L"):
        if ln.get(k) is not None:
            ln[k] = ln[k] * 1000.0
    for cb in s.get("combos", []):
        for k in ("Pu", "Vux", "Vuy", "Vux_omega", "Vuy_omega"):
            if cb.get(k) is not None:
                cb[k] = cb[k] * fF
        for k in ("Mx_top", "Mx_bot", "My_top", "My_bot"):
            if cb.get(k) is not None:
                cb[k] = cb[k] * fM
    st = s.get("story")
    if st:
        st["sum_Pu"] *= fF
        st["Vus"] *= fF
        st["lc"] *= 1000.0
    s["_units"] = units
    return s


# ---------------------------------------------------------------- evaluation

def _lengths(si):
    ln = si.get("length", {})
    lux = ln.get("lux", ln.get("lu"))
    luy = ln.get("luy", ln.get("lu"))
    return lux, luy, ln.get("L"), ln.get("k", 1.0), ln.get("beta_dns", 0.6), ln.get("ei", "a"), ln.get("r", "sqrt")


def strength(col, si):
    """Steps 4–5 for every combination.  Returns rows and the governing ratio."""
    lux, luy, L, k, bdns, ei, rr = _lengths(si)
    rows, worst = [], (0.0, None, None)
    for i, cb in enumerate(si["combos"]):
        name = cb.get("name", f"LC{i + 1}")
        Pu = cb["Pu"]
        sx = slenderness(col, "x", Pu, cb.get("Mx_top", 0), cb.get("Mx_bot", 0), lux, k, bdns,
                         cb.get("Vuy"), L, cb.get("curv_x"), ei, rr, cb.get("transverse_load", False)) if lux else None
        sy = slenderness(col, "y", Pu, cb.get("My_top", 0), cb.get("My_bot", 0), luy, k, bdns,
                         cb.get("Vux"), L, cb.get("curv_y"), ei, rr, cb.get("transverse_load", False)) if luy else None
        pts = [("ปลายบน", cb.get("Mx_top", 0), cb.get("My_top", 0)),
               ("ปลายล่าง", cb.get("Mx_bot", 0), cb.get("My_bot", 0))]
        if (sx and sx["slender"]) or (sy and sy["slender"]):
            mx = sx["Mc"] if sx and sx["slender"] else max(abs(cb.get("Mx_top", 0)), abs(cb.get("Mx_bot", 0)))
            my = sy["Mc"] if sy and sy["slender"] else max(abs(cb.get("My_top", 0)), abs(cb.get("My_bot", 0)))
            pts.append(("กลางเสา (ขยาย)", mx, my))
        checks = []
        for at, mx, my in pts:
            if math.isinf(mx) or math.isinf(my):
                r = {"ok": False, "ratio": math.inf, "reason": "ไม่เสถียร: Pu ≥ 0.75Pc (§6.6.4.5.2)"}
            else:
                r = capacity(col, Pu, mx, my)
            r.update(at=at, Mux=mx, Muy=my)
            checks.append(r)
            if r["ratio"] > worst[0]:
                worst = (r["ratio"], name, at)
        rows.append({"name": name, "Pu": Pu, "sx": sx, "sy": sy, "checks": checks})
    return rows, worst


def shear_all(col, si, s, legs_x, legs_y, s_end=None):
    """Step 6.  Returns per-combo results and seismic demand checks."""
    out = []
    ok = True
    for i, cb in enumerate(si["combos"]):
        if cb.get("Vux") is None and cb.get("Vuy") is None:
            continue
        rx = shear_direction(col, "x", abs(cb.get("Vux") or 0), cb["Pu"], s, legs_x)
        ry = shear_direction(col, "y", abs(cb.get("Vuy") or 0), cb["Pu"], s, legs_y)
        bi = biaxial(rx, ry)
        ok &= rx["ok"] and ry["ok"] and bi["ok"]
        out.append({"name": cb.get("name", f"LC{i + 1}"), "x": rx, "y": ry, "biaxial": bi})
    seismic = {}
    system = si.get("system")
    lux, luy, *_ = _lengths(si)
    if system in ("OMF", "IMF"):
        Pus = [cb["Pu"] for cb in si["combos"]]
        for axis, lu in (("x", lux), ("y", luy)):
            if not lu:
                continue
            key = "Vuy_omega" if axis == "x" else "Vux_omega"
            vo = max((cb.get(key) or 0 for cb in si["combos"]), default=0) or None
            d = seismic_shear_demand(col, axis, Pus, lu, system, vo)
            if d["applies"]:
                direc = "y" if axis == "x" else "x"
                legs = legs_y if direc == "y" else legs_x
                s_use = s_end if (system == "IMF" and s_end) else s
                d["check"] = shear_direction(col, direc, d["Ve"], min(Pus), s_use, legs)
                d["s"] = s_use
                ok &= d["check"]["phiVn"] >= d["Ve"] and d["check"]["checks"]["§22.5.1.2"]
            seismic[axis] = d
    return out, seismic, ok


def evaluate(si, col, ties):
    """All steps for one fully defined column."""
    res = {"col": col, "ties": ties, "system": si.get("system")}
    res["rows"], res["worst"] = strength(col, si)
    legs_x = 2 + ties["crossties_x"]
    legs_y = 2 + ties["crossties_y"]
    res["shear"], res["seismic"], res["shear_ok"] = shear_all(col, si, ties["s"], legs_x, legs_y, ties.get("s_end"))
    res["long"] = longitudinal_limits(col, si.get("dagg", 20.0), si.get("rho_max", 0.08))
    res["tie"] = tie_limits(col, ties["s"])
    res["tie"]["crossties_ok"] = (ties["crossties_x"] >= res["tie"]["crossties_x"]
                                  and ties["crossties_y"] >= res["tie"]["crossties_y"])
    lux, luy, *_ = _lengths(si)
    if si.get("system") == "IMF" and (lux or luy):
        res["imf"] = imf_end_zone(col, min(v for v in (lux, luy) if v), ties.get("s_end") or ties["s"])
    res["splice"] = splices(col, ties["s"], legs_x, legs_y)
    jt = si.get("joint", {})
    res["floor"] = floor_concrete(col.fc, jt.get("fc_floor"), jt.get("beams_4_sides", False))
    res["dowels"] = footing_dowels(col) if si.get("base_on_footing") else None
    stable = all(not (r[k] and r[k].get("unstable")) for r in res["rows"] for k in ("sx", "sy"))
    second = all(not (r[k] and r[k].get("slender") and not r[k].get("unstable") and not r[k]["second_order_ok"])
                 for r in res["rows"] for k in ("sx", "sy"))
    L_, T_ = res["long"], res["tie"]
    res["status"] = {
        "strength": res["worst"][0] <= 1.0 and stable and second,
        "shear": res["shear_ok"],
        "detailing": L_["rho_ok"] and L_["n_ok"] and L_["clear_ok"] and T_["tie_ok"] and T_["s_ok"]
                     and T_["crossties_ok"] and (res["imf"]["so_ok"] if res.get("imf") else True),
        "floor": not (res["floor"] and res["floor"]["required"]),
    }
    return res


# ---------------------------------------------------------------- design helpers

def _floor25(x):
    return max(50.0, math.floor(x / 25.0) * 25.0)


def design_ties(si, col, tie_db=None):
    """Choose tie size, crossties and spacing (general s and IMF s_end)."""
    col.tie_db = tie_db or (10.0 if col.db <= 32 else 12.0)              # 25.7.2.2
    col.e = col.cover + col.tie_db + col.db / 2.0
    col.bars = col._layout()
    t = tie_limits(col, 0)
    cx, cy = t["crossties_x"], t["crossties_y"]
    s_top = _floor25(t["s_max"])
    for extra in range(0, 4):
        for s in [s_top - 25 * i for i in range(int((s_top - 50) / 25) + 1)]:
            ties = {"db": col.tie_db, "s": s, "crossties_x": cx + extra, "crossties_y": cy + extra}
            if si.get("system") == "IMF":
                lux, luy, *_ = _lengths(si)
                lu = min(v for v in (lux, luy) if v)
                so_max = imf_end_zone(col, lu, 0)["so_max"]
                ties["s_end"] = min(s, _floor25(so_max))
            _, _, ok = shear_all(col, si, s, 2 + ties["crossties_x"], 2 + ties["crossties_y"], ties.get("s_end"))
            if ok:
                return ties
    return {"db": col.tie_db, "s": 50.0, "crossties_x": cx + 3, "crossties_y": cy + 3,
            "s_end": 50.0 if si.get("system") == "IMF" else None, "failed": True}


def design_bars(si, mats, sec):
    """Smallest steel area (then fewest bars) that passes strength and spacing."""
    opts = si.get("design", {}).get("db_options", [16, 20, 25, 28, 32])
    rho_max = si.get("design", {}).get("rho_max", 0.04)
    cover = si.get("cover", 40.0)
    cands = []
    for db in opts:
        for nx in range(2, 15):
            for ny in range(2, 15):
                col = Column(sec["b"], sec["h"], mats["fc"], mats["fy"], db, nx, ny, cover,
                             10.0 if db <= 32 else 12.0, mats.get("fyt"))
                L_ = longitudinal_limits(col, si.get("dagg", 20.0), rho_max)
                if not (L_["rho_ok"] and L_["clear_ok"]):
                    continue
                if abs((nx - 1) / max(col.b - 2 * col.e, 1) - (ny - 1) / max(col.h - 2 * col.e, 1)) * 1000 > 6:
                    continue          # keep bar spacing similar on both faces
                cands.append((col.Ast, len(col.bars), db, nx, ny))
    cands.sort()
    tried = []
    for Ast, n, db, nx, ny in cands:
        col = Column(sec["b"], sec["h"], mats["fc"], mats["fy"], db, nx, ny, cover,
                     10.0 if db <= 32 else 12.0, mats.get("fyt"))
        _, worst = strength(col, si)
        tried.append((col.label(), worst[0]))
        if worst[0] <= 1.0:
            return col, tried
    return None, tried


# ---------------------------------------------------------------- entry point

def run(inp):
    si = to_si(inp)
    res_head = {"input": inp, "si": si, "messages": [], "mode": inp.get("mode", "check")}
    system = si.get("system")
    # Step 0
    if system == "SMF":
        res_head["messages"].append(("FAIL", "18.7", "เสา SMF ต้องใช้ §18.7 ครบชุด — นอกขอบเขตสกิล"))
        res_head["stopped"] = True
        return res_head
    if system not in (None, "OMF", "IMF"):
        res_head["messages"].append(("FAIL", "18.2", f"ไม่รู้จักระบบ '{system}' (ใช้ null, OMF, IMF)"))
        res_head["stopped"] = True
        return res_head
    # Step 3
    st = si.get("story")
    if st:
        Q = stability_index(st["sum_Pu"], st["delta_o"], st["Vus"], st["lc"])
        res_head["Q"] = Q
        if Q > 0.05:
            res_head["messages"].append(("FAIL", "6.6.4.3", f"Q = {Q:.4f} > 0.05 → sway (นอกขอบเขตสกิล: ใช้ §6.6.4.6 หรือ P-Δ)"))
            res_head["stopped"] = True
            return res_head
    if si.get("length", {}).get("k", 1.0) > 1.0:
        res_head["messages"].append(("WARN", "6.6.4.4.3", "non-sway ควรใช้ k ≤ 1.0"))
    sec, mats = si["section"], si["materials"]
    cover = si.get("cover", 40.0)
    if res_head["mode"] == "design":
        col, tried = design_bars(si, mats, sec)
        res_head["tried"] = tried
        if col is None:
            res_head["messages"].append(("FAIL", "22.4", f"ไม่มีการจัดเหล็กที่ผ่านใน ρ ≤ {si.get('design', {}).get('rho_max', 0.04):.0%} — ขยายหน้าตัด"))
            res_head["stopped"] = True
            return res_head
        ties = design_ties(si, col, si.get("ties", {}).get("db"))
    else:
        bars, tz = si["bars"], si.get("ties", {})
        col = Column(sec["b"], sec["h"], mats["fc"], mats["fy"], bars["db"], bars["nx"], bars["ny"],
                     cover, tz.get("db", 10.0), mats.get("fyt"), si.get("eps_ty_420", False))
        ties = {"db": col.tie_db, "s": tz.get("s", 150.0), "s_end": tz.get("s_end"),
                "crossties_x": tz.get("crossties_x", 0), "crossties_y": tz.get("crossties_y", 0)}
    res = evaluate(si, col, ties)
    res.update(res_head)
    return res
