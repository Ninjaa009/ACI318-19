"""Step 10 — Markdown report; every section ends with the KB location it relies on."""
from __future__ import annotations

import math

from .rcsi import G, Fmt, ok, ref


def build(res):
    si = res["si"]
    f_ = Fmt(si["_units"])
    kgf = si["_units"] == "kgf-m"

    def q(mpa):
        return f"{mpa * 1e3:,.1f} kPa" + (f" ({mpa * 1e3 / G:,.2f} t/m²)" if kgf else "")

    L = ["# รายการคำนวณฐานรากแผ่ (Isolated spread footing) — ACI 318M-19", "",
         f"โหมด: **{'ออกแบบ (design)' if res['mode'] == 'design' else 'ตรวจสอบ (check)'}** · หน่วยอินพุต: {si['_units']} · ภายใน N, mm, MPa", ""]
    for lvl, cl, msg in res["messages"]:
        L.append(f"> {dict(FAIL='❌', WARN='⚠️', INFO='ℹ️')[lvl]} " + (f"§{cl} " if cl else "") + msg)
    if res.get("stopped"):
        return "\n".join(L + ["", "**หยุดการคำนวณ** — แก้ตามข้อความข้างบนแล้วรันใหม่"])
    f, so, m = res["f"], si["soil"], si["materials"]

    # 0–1
    L += ["", "## 0. ขอบเขต", "",
          "- ฐานรากเดี่ยวสองทาง วางบนดิน เสาสี่เหลี่ยมอยู่กึ่งกลาง ไม่มีเหล็กเฉือน · ขนาดฐานจากน้ำหนักใช้งาน + qa (ยอมให้) · กำลังคอนกรีตจากน้ำหนักประลัย",
          ref("kb/chapter-13.md §13.1, §13.2.6, §13.3.3"),
          "## 1. วัสดุและขนาด", "",
          f"- f′c = {f_.S(m['fc'])} · fy = {f_.S(m['fy'])} · ระยะหุ้ม {f.cover:.0f} mm (เทชิดดิน) · γc = {si['gamma_c'] * 1e6:.1f} kN/m³",
          f"- เสา {f.cx:.0f} × {f.cy:.0f} mm · **ฐาน B × L × h = {f.B:,.0f} × {f.L:,.0f} × {f.h:,.0f} mm** (B ตามแกน x)",
          f"- dx = {f.dx:.0f} mm, dy = {f.dy:.0f} mm, d เฉลี่ย = {f.d:.0f} mm ≥ 150 mm {ok(res['d_ok'])} · เหล็กชั้นล่างสุด = เหล็ก{'แกน x' if f.x_bottom else 'แกน y'} (ทิศยาว)",
          f"- ดิน: qa = {q(so['qa'])} ({'net' if so.get('qa_type') == 'net' else 'gross'}) · Df = {so['Df']:.0f} mm · γดิน = {so['gamma'] * 1e6:.1f} kN/m³",
          ref("kb/chapter-20.md §20.5.1.3 (ระยะหุ้ม)", "kb/chapter-13.md §13.3.1", "references/si-formulas.md")]

    if si.get("_trace_md"):
        L += [si["_trace_md"], ref("references/staad-sign-convention.md")]

    # 2 service
    L += ["## 2. แรงแบกทานดิน (น้ำหนักใช้งาน)", "",
          "| combo | P | น้ำหนักฐาน+ดิน | Mx ที่ท้องฐาน | My ที่ท้องฐาน | qmax | สัมผัสดิน | FS พลิก | FS เลื่อน | ผล |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["service"]:
        s = r["sol"]
        if not s["stable"]:
            L.append(f"| {r['name']} | {f_.F(r['P'])} | {f_.F(r['W'])} | {f_.M(r['Mx'])} | {f_.M(r['My'])} | — | — | — | — | ❌ {s['reason']} |")
            continue
        L.append(f"| {r['name']} | {f_.F(r['P'])} | {f_.F(r['W'])} | {f_.M(r['Mx'])} | {f_.M(r['My'])} | {q(r['q'])} {ok(r['q_ok'])} | "
                 f"{s['contact']:.0%}{'' if s['full'] else ' ⚠️'} | {min(r['FSx'], r['FSy']):.2f} | "
                 f"{'—' if r['FSs'] is None else format(r['FSs'], '.2f')} | {ok(r['ok'])} |")
    L += ["", "- q = P/A ± M/S เมื่อแรงลัพธ์อยู่ใน kern; นอก kern คิดแรงดันเฉพาะส่วนที่สัมผัสดิน (ไม่มีแรงดึง) · โมเมนต์ที่ท้องฐานรวม H × h",
          f"- FS พลิกคว่ำ ≥ {si.get('FS_overturning', 1.5)}, FS เลื่อนไถล ≥ {si.get('FS_sliding', 1.5)} (μ = {so.get('mu', '—')}) ตาม building code",
          ref("kb/chapter-13.md §13.2.6.1, §13.3.1")]

    # 3 ultimate pressure
    L += ["## 3. แรงดันดินประลัย (net — ไม่รวมน้ำหนักฐาน)", "", "| combo | Pu | Mux | Muy | qu,max | สัมผัสดิน |", "|---|---|---|---|---|---|"]
    for r in res["ultimate"]:
        s = r["sol"]
        L.append(f"| {r['name']} | {f_.F(r['Pu'])} | {f_.M(r['Mux'])} | {f_.M(r['Muy'])} | "
                 + (f"{q(s['qmax'])} | {s['contact']:.0%} |" if s["stable"] else f"❌ {s['reason']} | — |"))
    L.append(ref("kb/chapter-13.md §13.2.6.3"))
    if not all(r["sol"]["stable"] for r in res["ultimate"]):
        return "\n".join(L + ["**หยุด: แรงประลัยทำให้ฐานพลิก**"])

    # 4 flexure
    L += ["## 4. แรงดัดที่หน้าเสา", "", "| เหล็ก | Mu (กว้างเต็มฐาน) | b × d | As ต้องการ | As,min (0.0018bh) | ใช้ | As ให้ | φMn | ผล |",
          "|---|---|---|---|---|---|---|---|---|"]
    for d, nm in (("x", "แกน x (ยาว B)"), ("y", "แกน y (ยาว L)")):
        fl = res["flex"][d]
        db, s = (f.dbx, f.sx) if d == "x" else (f.dby, f.sy)
        req = "หนาไม่พอ" if fl["As_req"] is None else f"{fl['As_req']:,.0f}"
        L.append(f"| {nm} | {f_.M(fl['Mu'])} | {fl['b']:,.0f} × {fl['d']:.0f} | {req} | {fl['As_min']:,.0f} | DB{db:g} @ {s:.0f} | "
                 f"{fl['As']:,.0f} mm² | {f_.M(fl['phiMn'])} (φ {fl['phi']:.2f}) | {ok(fl['ok'])} |")
    for d in ("x", "y"):
        fl = res["flex"][d]
        if fl["band"] > 1:
            L.append(f"- เหล็กทิศสั้น (แกน {d}): γs = 2/(β+1) ในแถบกลาง → ใช้ระยะเท่ากันโดยเพิ่ม As × 2β/(β+1) = {fl['band']:.3f} {ok(fl['band_ok'])}")
        L.append(f"- ระยะเหล็กแกน {d}: {fl['s']:.0f} ≤ min(2h, 450) = {fl['s_max']:.0f} mm {ok(fl['s_ok'])}")
    L.append(ref("kb/chapter-13.md §13.2.7.1, §13.3.3", "kb/chapter-08.md §8.6.1, §8.7.2", "kb/chapter-22.md §22.2–22.3", "kb/chapter-21.md"))

    # 5 one-way shear
    L += ["## 5. แรงเฉือนทางเดียว (ที่ระยะ d จากหน้าเสา)", "", "| ทิศ | Vu | b × d | ρw | φVc | ผล |", "|---|---|---|---|---|---|"]
    for d in ("x", "y"):
        s = res["shear1"][d]
        L.append(f"| {d} | {f_.F(s['Vu'])} | {s['b']:,.0f} × {s['d']:.0f} | {s['rho']:.4f} | {f_.F(s['phiVc'])} | {ok(s['ok'])} |")
    L += ["", "- ไม่มีเหล็กเฉือน → Vc ตาม Table 22.5.5.1(c) = 0.66ρw^⅓√f′c·bd (λs = 1 สำหรับฐานราก §13.2.6.2) — ค่านี้ต่ำกว่าสูตรเดิม 0.17√f′c·bd เมื่อ ρw น้อย",
          ref("kb/chapter-22.md §22.5.5", "kb/chapter-13.md §13.2.6.2, §13.2.7")]

    # 6 punching
    L += ["## 6. แรงเฉือนสองทาง (punching ที่ d/2 รอบเสา)", "", "| combo | Vu | bo | vu (แรงเฉือน + ถ่ายโมเมนต์) | φvc | ผล |", "|---|---|---|---|---|---|"]
    for r in res["ultimate"]:
        p = r["punch"]
        L.append(f"| {r['name']} | {f_.F(p['Vu'])} | {p['bo']:,.0f} | {p['vuv']:.3f} + {p['vM']:.3f} = **{p['vu']:.3f} MPa** | {p['phivc']:.3f} MPa | {ok(p['ok'])} |")
    p0 = res["ultimate"][0]["punch"]
    L += ["", f"- vc = min(0.33, 0.17(1 + 2/β), 0.083(2 + αs·d/bo))√f′c, β = {p0['beta']:.2f}, αs = {si.get('alpha_s', 40)}, λs = 1 · "
          f"γv = {p0['gv'][0]:.2f} / {p0['gv'][1]:.2f} (ถ่ายโมเมนต์เสาเต็มค่า — อนุรักษ์)",
          ref("kb/chapter-22.md §22.6", "kb/chapter-08.md §8.4.4", "kb/chapter-13.md §13.2.6.2")]

    # 7 bearing & dowels
    b = res["bearing"]
    L += ["## 7. แรงแบกทานใต้เสาและเหล็กเสียบ", "",
          f"- A1 = {b['A1']:,.0f} mm² · √(A2/A1) = {b['sqrtA2A1']:.2f} (≤ 2) · φBn ฐาน = {f_.F(b['phiBn_ftg'])}, φBn เสา = {f_.F(b['phiBn_col'])} (φ = 0.65)",
          f"- Pu สูงสุด {f_.F(max(r['Pu'] for r in res['ultimate']))} ≤ φBn = {f_.F(b['phiBn'])} {ok(b['ok'])}"
          + ("" if b["ok"] else f" → ต้องมีเหล็กเสียบรับส่วนเกิน {b['As_extra']:,.0f} mm²"),
          f"- เหล็กเสียบข้ามรอยต่อ ≥ 0.005Ag เสา = {b['As_min']:,.0f} mm² (ใช้เหล็กยืนเสาทุกเส้นยื่นลงฐาน)"]
    dw = res["dowel"]
    if dw:
        L.append(f"- ℓdc ของเหล็กเสา DB{si['column']['db']:g} = {dw['ldc']:.0f} mm ≤ ความลึกที่มี {dw['avail']:.0f} mm {ok(dw['ok'])} (ขอที่ปลายไม่นับในแรงอัด)")
    else:
        L.append("- ไม่ได้ระบุขนาดเหล็กเสา (`column.db`) — **ยังไม่ตรวจ ℓdc ของเหล็กเสียบ**")
    L.append(ref("kb/chapter-22.md §22.8", "kb/chapter-16.md §16.3", "kb/chapter-25.md §25.4.9"))

    # 8 development
    L += ["## 8. ระยะฝังยึดเหล็กล่าง", ""]
    for d in ("x", "y"):
        dv = res["dev"][d]
        how = "ตรงได้ ✅" if dv["straight_ok"] else ("**ต้องงอขอ 90°** ✅" if dv["hook_ok"] else "❌ ไม่พอแม้งอขอ")
        L.append(f"- แกน {d}: ระยะจากหน้าเสาถึงปลายเหล็ก {dv['avail']:.0f} mm · ℓd = {dv['ld']:.0f} mm (ตัวหาร {dv['k']}) · ℓdh = {dv['ldh']:.0f} mm → {how}")
    L.append(ref("kb/chapter-13.md §13.2.8", "kb/chapter-25.md §25.4.2, §25.4.3"))

    # 9 summary
    st = res["status"]
    names = {"soil": "ดิน (ข้อ 2)", "flexure": "แรงดัด (ข้อ 4)", "shear": "แรงเฉือน (ข้อ 5–6)",
             "detailing": "รายละเอียด (ข้อ 1, 7, 8)", "bearing": "แบกทานใต้เสา (ข้อ 7)"}
    L += ["## 9. สรุป", "",
          f"**ฐาน {f.B / 1000:.2f} × {f.L / 1000:.2f} × {f.h / 1000:.2f} m · เหล็กล่างแกน x DB{f.dbx:g} @ {f.sx:.0f} mm · แกน y DB{f.dby:g} @ {f.sy:.0f} mm**", ""]
    L += [f"- {names[k]}: {ok(v)}" for k, v in st.items()]
    L += [f"- **ผลรวม: {'ผ่านทุกรายการที่ตรวจ' if all(st.values()) else 'ไม่ผ่าน — ดูรายการ ❌'}**", "",
          "**ยังไม่ตรวจ:** การทรุดตัว, แรงยกจากน้ำใต้ดิน, ฐานรากใน SDC C–F (§18.13), คานยึดฐาน (tie beam), "
          "เหล็กบน (กรณีฐานยกบางส่วนหรือมีแรงดึง), เสาเยื้องศูนย์/ฐานร่วม",
          "", "_ผลลัพธ์ใช้ประกอบรายการคำนวณ วิศวกรผู้รับผิดชอบต้องตรวจและลงนาม_"]
    return "\n".join(L)
