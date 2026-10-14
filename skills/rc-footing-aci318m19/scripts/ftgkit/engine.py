"""Workflow driver — steps 0–10 for one isolated spread footing (see SKILL.md)."""
from __future__ import annotations

import copy
import math

from .rcsi import G, KSC, area
from .pressure import solve
from .checks import (Footing, face_moment, one_way_vu, flexure_required, flexure_check,
                     one_way_check, punching, bearing, development, dowel_embedment, column_tension)


# ---------------------------------------------------------------- units

def to_si(inp):
    """→ N, mm, MPa.  kgf-m: dimensions m, ksc, kgf, kgf·m, qa t/m², γ t/m³.
    SI: dimensions mm, MPa, kN, kN·m, qa kPa, γ kN/m³.  Df in m for both; bars/cover in mm."""
    s = copy.deepcopy(inp)
    u = inp.get("units", "kgf-m")
    if u == "kgf-m":
        fL, fF, fM, fq, fg = 1000.0, G, G * 1000.0, G * 1e-3, G * 1e-6
        s["materials"] = {k: v * KSC for k, v in inp["materials"].items() if v is not None}
    elif u == "SI":
        fL, fF, fM, fq, fg = 1.0, 1e3, 1e6, 1e-3, 1e-6
    else:
        raise ValueError("units ต้องเป็น 'kgf-m' หรือ 'SI'")
    s["column"] = {k: (v * fL if k in ("cx", "cy") else v) for k, v in inp["column"].items()}
    if inp.get("footing"):
        s["footing"] = {k: v * fL for k, v in inp["footing"].items()}
    so = s.setdefault("soil", {})
    so["qa"] = inp["soil"]["qa"] * fq                               # MPa
    so["gamma"] = inp["soil"].get("gamma", 1.8 if u == "kgf-m" else 18.0) * fg   # N/mm³
    so["Df"] = inp["soil"].get("Df", 0.0) * 1000.0
    s["gamma_c"] = inp.get("gamma_c", 2.4 if u == "kgf-m" else 23.6) * fg
    for k in ("service", "ultimate"):
        for cb in s.get(k, []):
            for f in ("P", "Pu", "Hx", "Hy", "Hux", "Huy"):
                if cb.get(f) is not None:
                    cb[f] = cb[f] * fF
            for f in ("Mx", "My", "Mux", "Muy"):
                if cb.get(f) is not None:
                    cb[f] = abs(cb[f]) * fM
    if s.get("design", {}).get("B") is not None:
        s["design"]["B"] *= fL
    if s.get("design", {}).get("L") is not None:
        s["design"]["L"] *= fL
    s["_units"] = u
    return s


# ---------------------------------------------------------------- service (soil)

def service_checks(si, f):
    so = si["soil"]
    W_f = si["gamma_c"] * f.B * f.L * f.h
    W_s = so["gamma"] * (f.B * f.L - f.cx * f.cy) * max(so["Df"] - f.h, 0.0)
    rows = []
    for i, cb in enumerate(si["service"]):
        P = cb["P"] + W_f + W_s
        Hx, Hy = abs(cb.get("Hx") or 0), abs(cb.get("Hy") or 0)
        Mx = (cb.get("Mx") or 0) + Hy * f.h
        My = (cb.get("My") or 0) + Hx * f.h
        sol = solve(P, Mx, My, f.B, f.L)
        r = {"name": cb.get("name", f"S{i + 1}"), "P": cb["P"], "W": W_f + W_s, "Ptot": P,
             "Mx": Mx, "My": My, "sol": sol}
        if not sol["stable"]:
            r.update(ok=False, q_ok=False)
            rows.append(r)
            continue
        q = sol["qmax"] - (so["gamma"] * so["Df"] if so.get("qa_type") == "net" else 0.0)
        FSx = P * f.B / 2 / My if My > 0 else math.inf
        FSy = P * f.L / 2 / Mx if Mx > 0 else math.inf
        H = math.hypot(Hx, Hy)
        FSs = (so["mu"] * P / H) if (H > 0 and so.get("mu")) else None
        need = si.get("FS_overturning", 1.5), si.get("FS_sliding", 1.5)
        full_req = si.get("require_full_contact", False)
        r.update(q=q, q_ok=q <= so["qa"] * (1 + 1e-9), FSx=FSx, FSy=FSy, FS_ot_ok=min(FSx, FSy) >= need[0],
                 FSs=FSs, FS_sl_ok=(FSs is None) or FSs >= need[1], contact_ok=sol["full"] or not full_req)
        r["ok"] = r["q_ok"] and r["FS_ot_ok"] and r["FS_sl_ok"] and r["contact_ok"]
        rows.append(r)
    return rows


# ---------------------------------------------------------------- strength

def strength_checks(si, f):
    rows = []
    for i, cb in enumerate(si["ultimate"]):
        Pu = cb["Pu"]
        Hx, Hy = abs(cb.get("Hux") or 0), abs(cb.get("Huy") or 0)
        Mux, Muy = cb.get("Mux") or 0, cb.get("Muy") or 0
        sol = solve(Pu, Mux + Hy * f.h, Muy + Hx * f.h, f.B, f.L)
        r = {"name": cb.get("name", f"U{i + 1}"), "Pu": Pu, "Mux": Mux, "Muy": Muy, "sol": sol}
        if not sol["stable"]:
            r["ok"] = False
            rows.append(r)
            continue
        r["Mu"] = {d: face_moment(f, sol, d) for d in ("x", "y")}
        r["Vu1"] = {d: one_way_vu(f, sol, d) for d in ("x", "y")}
        r["punch"] = punching(f, sol, Pu, Mux, Muy, si.get("alpha_s", 40))
        rows.append(r)
    return rows


def _band_factor(f, direction):
    """Short-direction bars of a rectangular footing: 2β/(β+1) (§13.3.3.3, commentary)."""
    long_, short = max(f.B, f.L), min(f.B, f.L)
    beta = long_ / short
    is_short = (direction == "x" and f.B < f.L) or (direction == "y" and f.L < f.B)
    return (2 * beta / (beta + 1)) if is_short else 1.0


def dowel_check(si, f, brg):
    """Column bars (or separate dowels) into the footing.  §25.4.10 reduction is applied when
    the code allows it: not SDC D–F, no tension in the column at its base, bars not hooked
    for compression, and the provided area is known."""
    col, mats = si["column"], si["materials"]
    db = col.get("dowel_db") or col.get("db")
    if not db:
        return None
    n = col.get("dowel_n") or col.get("n")
    As_prov = n * area(db) if n else None
    As_req = max(brg["As_min"], brg["As_extra"])
    why = None
    tension = column_tension(col, si["ultimate"])
    allowed = si.get("ldc_reduction", True)
    if not allowed:
        why = "ผู้ใช้ปิด (ldc_reduction: false)"
    elif si.get("sdc") in ("D", "E", "F"):
        why = "SDC D–F (§25.4.10.2(e))"
    elif tension:
        why = "เสามีแรงดึงที่โคน (P/A − M/S < 0) — เหล็กเสียบต้องพัฒนาแรงดึงด้วย"
    elif not As_prov:
        why = "ไม่ได้ระบุจำนวนเหล็ก (column.n)"
    return dowel_embedment(f, db, mats["fy"], As_req, As_prov, why is None, why, tension) | \
        {"As_req": As_req, "As_prov": As_prov}


def evaluate(si, f):
    mats, col = si["materials"], si["column"]
    res = {"f": f}
    res["service"] = service_checks(si, f)
    res["ultimate"] = strength_checks(si, f)
    stable = all(r["sol"]["stable"] for r in res["ultimate"])
    res["flex"], res["shear1"] = {}, {}
    for d in ("x", "y"):
        As = f.As(d)
        if stable:
            Mu = max(r["Mu"][d] for r in res["ultimate"])
            Vu = max(r["Vu1"][d] for r in res["ultimate"])
            req = flexure_required(f, Mu, d)
            fl = flexure_check(f, Mu, d, As)
            fl["As_req"] = req
            fl["band"] = _band_factor(f, d)
            need = max(req or math.inf, fl["As_min"])
            fl["band_ok"] = As >= need * fl["band"] * (1 - 1e-9) if fl["band"] > 1 else True
            fl["s"] = f.sx if d == "x" else f.sy
            fl["s_max"] = min(2 * f.h, 450.0)                                  # 8.7.2.2
            fl["s_ok"] = fl["s"] <= fl["s_max"] + 1e-9
            res["flex"][d] = fl
            res["shear1"][d] = one_way_check(f, Vu, d, As)
        res.setdefault("dev", {})[d] = development(f, d, mats["fy"])
    Pu_max = max(cb["Pu"] for cb in si["ultimate"])
    Ag_col = f.cx * f.cy
    res["bearing"] = bearing(f, Pu_max, mats.get("fc_column", mats["fc"]), Ag_col)
    res["dowel"] = dowel_check(si, f, res["bearing"])
    res["d_ok"] = min(f.dx, f.dy) >= 150.0                                   # 13.3.1.2
    sv = res["service"]
    res["status"] = {
        "soil": all(r.get("ok", False) for r in sv),
        "flexure": stable and all(res["flex"][d]["ok"] and res["flex"][d]["band_ok"] and res["flex"][d]["s_ok"]
                                  for d in ("x", "y")),
        "shear": stable and all(res["shear1"][d]["ok"] for d in ("x", "y"))
                 and all(r["punch"]["ok"] for r in res["ultimate"]),
        "detailing": res["d_ok"] and all(res["dev"][d]["straight_ok"] or res["dev"][d]["hook_ok"] for d in ("x", "y"))
                     and (res["dowel"]["ok"] if res["dowel"] else True),
        "bearing": res["bearing"]["ok"],
    }
    return res


# ---------------------------------------------------------------- design

def _floor25(x):
    return math.floor(x / 25.0) * 25.0


def _ceil50(x):
    return math.ceil(x / 50.0 - 1e-9) * 50.0


def _size_plan(si, h, cx, cy, fc, fy):
    """Smallest plan (50 mm steps) that passes the soil checks.  design.B / design.L fix a side;
    otherwise L = ratio·B."""
    D = si.get("design", {})
    ratio, Bf, Lf = D.get("ratio", 1.0), D.get("B"), D.get("L")
    B = Bf or _ceil50(max(cx, cy / ratio) + 2 * h)
    L = Lf or _ceil50(B * ratio)
    for _ in range(400):
        f = Footing(B, L, h, cx, cy, fc, fy, si.get("cover", 75.0))
        if all(r.get("ok", False) for r in service_checks(si, f)):
            return B, L
        if Bf and Lf:
            return None
        if Bf:
            L += 50.0
        elif Lf:
            B += 50.0
        else:
            B += 50.0
            L = _ceil50(B * ratio)
    return None


def _choose_bars(f, Mu, direction, opts, factor=1.0):
    """Lightest bar set for max(As,req, As,min) × band × factor (factor > 1 adds steel
    to raise ρw and therefore Vc of T22.5.5.1(c) instead of thickening the footing)."""
    w = f.L if direction == "x" else f.B
    req = flexure_required(f, Mu, direction)
    if req is None:
        return None
    As_min = 0.0018 * w * f.h
    need = max(req, As_min) * _band_factor(f, direction) * factor
    smax = min(2 * f.h, 450.0)
    best = None
    for db in opts:
        Ab = area(db)
        n = max(2, math.ceil(need / Ab))
        s = min(_floor25((w - 2 * f.cover - db) / (n - 1)), smax)
        if s < 100:
            continue
        nprov = math.floor((w - 2 * f.cover - db) / s) + 1
        cand = (nprov * Ab, -s, db, s)
        if best is None or cand < best:
            best = cand
    return best and (best[2], best[3])


def design(si):
    """Thinnest footing first: at each h (50 mm steps) try the lightest bars, then add bottom
    steel (up to ×2.5, s ≥ 100 mm) when only one-way shear fails — design.prefer = "thin"
    (default).  design.prefer = "steel" skips the extra-steel step (thicker, less steel)."""
    mats, col = si["materials"], si["column"]
    D = si.get("design", {})
    opts = D.get("db_options", [12, 16, 20, 25])
    factors = (1.0,) if D.get("prefer", "thin") == "steel" else (1.0, 1.15, 1.3, 1.5, 1.75, 2.0, 2.5)
    cx, cy = col["cx"], col["cy"]
    h = D.get("h_min", 300.0)
    notes = []
    mk = lambda B, L, h, bx, by: Footing(B, L, h, cx, cy, mats["fc"], mats["fy"], si.get("cover", 75.0),
                                         bx[0], by[0], bx[1], by[1])
    for _ in range(60):
        plan = _size_plan(si, h, cx, cy, mats["fc"], mats["fy"])
        if plan is None:
            return None, notes + ["หาขนาดฐานที่ผ่านแรงแบกทาน/พลิกคว่ำไม่ได้ — ตรวจ qa และแรง"]
        B, L = plan
        f0 = Footing(B, L, h, cx, cy, mats["fc"], mats["fy"], si.get("cover", 75.0), opts[1], opts[1])
        ult = strength_checks(si, f0)
        if not all(r["sol"]["stable"] for r in ult):
            return None, notes + ["แรงประลัยทำให้แรงลัพธ์ออกนอกฐาน"]
        for k in factors:
            bars = {}
            f = f0
            for _pass in range(2):                       # bar sizes change d: pick twice
                ult = strength_checks(si, f)
                for d in ("x", "y"):
                    bars[d] = _choose_bars(f, max(r["Mu"][d] for r in ult), d, opts, k) or bars.get(d)
                if not (bars.get("x") and bars.get("y")):
                    break
                f = mk(B, L, h, bars["x"], bars["y"])
            if not (bars.get("x") and bars.get("y")):
                break
            res = evaluate(si, f)
            st = res["status"]
            punch_ok = all(r["punch"]["ok"] for r in res["ultimate"])
            dowel_ok = res["dowel"]["ok"] if res["dowel"] else True
            if all(st[k_] for k_ in ("soil", "flexure", "shear")) and res["d_ok"] and dowel_ok:
                if k > 1:
                    notes.append(f"เพิ่มเหล็กล่าง ×{k:g} ของที่ต้องการรับดัด เพื่อให้ Vc (ขึ้นกับ ρw) พอ — ฐานบางลงแทนการเพิ่มความหนา")
                if not st["detailing"]:
                    notes.append("เหล็กล่างยื่นตรงไม่พอ ℓd — ต้องงอขอที่ปลาย (ดูข้อ 8)")
                return f, notes
            # extra steel only helps one-way shear; stop early if something else governs
            if not punch_ok or not dowel_ok or not res["d_ok"] or not st["flexure"]:
                break
        h += 50.0
    return None, notes + ["ความหนาเกิน 3 m แล้วยังไม่ผ่าน — ตรวจข้อมูล"]


# ---------------------------------------------------------------- entry

def quantities(f):
    """Concrete (m³) and bottom steel (kg) — for comparing design alternatives."""
    nx = math.floor((f.L - 2 * f.cover - f.dbx) / f.sx) + 1
    ny = math.floor((f.B - 2 * f.cover - f.dby) / f.sy) + 1
    kg = 7850e-9 * (nx * area(f.dbx) * (f.B - 2 * f.cover) + ny * area(f.dby) * (f.L - 2 * f.cover))
    return f.B * f.L * f.h * 1e-9, kg


def run(inp):
    si = to_si(inp)
    res = {"input": inp, "si": si, "mode": inp.get("mode", "design"), "messages": []}
    if si.get("system") == "SMF" or si.get("sdc") in ("D", "E", "F"):
        res["messages"].append(("FAIL", "13.2.3 / 18.13", "ฐานรากใน SDC D–F ต้องใช้ §18.13 — นอกขอบเขต"))
        res["stopped"] = True
        return res
    if si.get("sdc") == "C" or si.get("system") == "IMF":
        res["messages"].append(("WARN", "18.13", "SDC C: ตรวจข้อกำหนด §18.13 (คานยึดฐาน ฯลฯ) เพิ่มเอง — ยังไม่ตรวจในสกิล"))
    if not si.get("service") or not si.get("ultimate"):
        res["messages"].append(("FAIL", "13.2.6", "ต้องมีทั้ง combo ใช้งาน (service) และ combo ประลัย (ultimate)"))
        res["stopped"] = True
        return res
    mats, col = si["materials"], si["column"]
    if res["mode"] == "design":
        f, notes = design(si)
        if f is not None and si.get("design", {}).get("prefer", "thin") == "thin" and any("เพิ่มเหล็กล่าง" in n for n in notes):
            alt, _ = design(dict(si, design=dict(si.get("design", {}), prefer="steel")))
            if alt is not None and alt.h > f.h:
                c1, s1 = quantities(f)
                c2, s2 = quantities(alt)
                notes.append(f"ทางเลือก (design.prefer = \"steel\"): h = {alt.h:.0f} mm, DB{alt.dbx:g}@{alt.sx:.0f}/DB{alt.dby:g}@{alt.sy:.0f} "
                             f"→ คอนกรีต {c2 - c1:+.2f} m³, เหล็กล่าง {s2 - s1:+.0f} kg เทียบแบบที่เลือก — ให้เทียบราคาวัสดุเอง")
        res["messages"] += [("INFO", "", n) for n in notes]
        if f is None:
            res["stopped"] = True
            return res
    else:
        ft, br = si["footing"], si["bars"]
        f = Footing(ft["B"], ft["L"], ft["h"], col["cx"], col["cy"], mats["fc"], mats["fy"],
                    si.get("cover", 75.0), br["x"]["db"], br["y"]["db"], br["x"]["s"], br["y"]["s"])
    res.update(evaluate(si, f))
    return res
