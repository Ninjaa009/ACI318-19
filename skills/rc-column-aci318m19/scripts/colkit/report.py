"""Step 10 — Markdown report.  Every section ends with the KB location it relies on."""
from __future__ import annotations

import math

from .rcsi import Fmt, ok, ref  # noqa: E402


def build(res):
    f = Fmt(res["si"]["_units"])
    si = res["si"]
    L = ["# รายการคำนวณเสา คสล. — ACI 318M-19", ""]
    L.append(f"โหมด: **{'ออกแบบ (design)' if res['mode'] == 'design' else 'ตรวจสอบ (check)'}** · "
             f"หน่วยอินพุต: {si['_units']} · ภายใน N, mm, MPa")
    L.append("")
    for lvl, cl, msg in res["messages"]:
        L.append(f"> **{lvl}** (§{cl}) {msg}")
    if res.get("stopped"):
        L += ["", "**หยุดการคำนวณ** — แก้ตามข้อความข้างบนแล้วรันใหม่"]
        if res.get("tried"):
            L += ["", "| การจัดเหล็กที่ลอง | อัตราส่วนสูงสุด |", "|---|---|"]
            L += [f"| {a} | {r:.3f} |" for a, r in res["tried"][:15]]
        return "\n".join(L)
    col, ties = res["col"], res["ties"]

    # 0
    sysname = {None: "ไม่อยู่ในระบบต้านแผ่นดินไหว", "OMF": "OMF (โครงต้านแรงดัดธรรมดา)",
               "IMF": "IMF (โครงต้านแรงดัดปานกลาง)"}[res["system"]]
    L += ["## 0. ระบบโครงสร้าง", "", f"- {sysname}", ref("kb/chapter-18.md §18.2.1, §18.3, §18.4")]

    # 1
    L += ["## 1. หน้าตัดและวัสดุ", "",
          f"- b × h = {col.b:.0f} × {col.h:.0f} mm (b ขนานแกน x) · Ag = {col.Ag:,.0f} mm²",
          f"- f′c = {f.S(col.fc)} · β1 = {col.b1:.3f} · fy = {f.S(col.fy_spec)}"
          + (f" (ใช้ {col.fy:.0f} ในกำลัง)" if col.fy < col.fy_spec else "")
          + f" · fyt = {f.S(col.fyt)}",
          f"- เหล็กยืน **{col.label()}** · Ast = {col.Ast:,.0f} mm² · ρg = {col.Ast / col.Ag:.2%}",
          f"- ระยะหุ้มถึงปลอก {col.cover:.0f} mm · ปลอก DB{ties['db']:g} · ผิวถึงศูนย์เหล็ก {col.e:.1f} mm",
          ref("kb/chapter-10.md §10.3", "kb/chapter-20.md §20.2", "kb/chapter-22.md §22.2.2",
              "references/si-constants-318m.md")]
    if res["mode"] == "design" and res.get("tried"):
        L += ["**ผลการเลือกเหล็ก** (เรียงตาม Ast จากน้อยไปมาก หยุดที่ชุดแรกที่ผ่านกำลังทุก combo):", "",
              "| การจัดเหล็ก | อัตราส่วนสูงสุด |", "|---|---|"]
        L += [f"| {a} | {r:.3f} {'✅' if r <= 1 else '❌'} |" for a, r in res["tried"][-8:]]
        L.append("")

    # 2
    L += ["## 2. แรงออกแบบ", "", "| combo | Pu | Mx บน | Mx ล่าง | My บน | My ล่าง | Vux | Vuy |",
          "|---|---|---|---|---|---|---|---|"]
    for cb in si["combos"]:
        g = lambda k: cb.get(k) or 0
        L.append(f"| {cb.get('name', '')} | {f.F(cb['Pu'])} | {f.M(g('Mx_top'))} | {f.M(g('Mx_bot'))} | "
                 f"{f.M(g('My_top'))} | {f.M(g('My_bot'))} | {f.F(g('Vux'))} | {f.F(g('Vuy'))} |")
    L += ["", "Mx ดัดรอบแกน x (ความลึก h) คู่กับ Vuy · My ดัดรอบแกน y (ความลึก b) คู่กับ Vux"]

    # 3
    L += ["", "## 3. โครงเซ (sway) หรือไม่", ""]
    if "Q" in res:
        st = si["story"]
        L.append(f"- Q = ΣPu·Δo/(Vus·lc) = {st['sum_Pu'] / 1e3:,.0f} kN × {st['delta_o']:.1f} mm / "
                 f"({st['Vus'] / 1e3:,.0f} kN × {st['lc']:.0f} mm) = **{res['Q']:.4f}** ≤ 0.05 → non-sway ✅")
    else:
        L.append("- ไม่มีข้อมูลชั้น → **ถือว่า non-sway ตามที่ผู้ใช้ระบุ (ยังไม่ตรวจ Q)**")
    L.append(ref("kb/chapter-06.md §6.6.4.3, Eq. 6.6.4.4.1"))

    # 4
    L += ["## 4. ความชะลูดและการขยายโมเมนต์", "",
          "| combo | แกน | kℓu/r | M1/M2 | ขีดจำกัด | ชะลูด | Pc | Cm | δ | Mc |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    notes = set()
    for r in res["rows"]:
        for s in (r["sx"], r["sy"]):
            if not s:
                continue
            notes.add(f"แกน {s['axis']} ({r['name']}): {s['how']}")
            if s["slender"]:
                L.append(f"| {r['name']} | {s['axis']} | {s['klr']:.1f} | {s['m_ratio']:+.3f} | {s['limit']:.1f} | ใช่ | "
                         f"{f.F(s['Pc'])} | {s['Cm']:.3f} | {s['delta']:.3f} | {f.M(s['Mc'])} |")
            else:
                L.append(f"| {r['name']} | {s['axis']} | {s['klr']:.1f} | {s['m_ratio']:+.3f} | {s['limit']:.1f} | ไม่ | — | — | 1.000 | {f.M(s['Mc'])} |")
    L.append("")
    L += [f"- {n}" for n in sorted(notes)]
    ln = si.get("length", {})
    L.append(f"- k = {ln.get('k', 1.0)} · βdns = {ln.get('beta_dns', 0.6)} · EI วิธี ({ln.get('ei', 'a')}) "
             "· M2 ≥ M2,min = Pu(15 + 0.03h) · Mc ≤ 1.4M (§6.2.5.3)")
    for r in res["rows"]:
        for s in (r["sx"], r["sy"]):
            if s and s.get("unstable"):
                L.append(f"- ❌ {r['name']} แกน {s['axis']}: Pu ≥ 0.75Pc — ไม่เสถียร ต้องขยายหน้าตัด")
            elif s and s.get("slender") and not s["second_order_ok"]:
                L.append(f"- ❌ {r['name']} แกน {s['axis']}: Mc > 1.4M — ขยายหน้าตัด")
    L.append(ref("kb/chapter-06.md §6.2.5, §6.6.4.4, §6.6.4.5", "kb/chapter-19.md §19.2.2 (Ec)"))

    # 5
    L += ["## 5. กำลังรับแรงอัดและโมเมนต์สองแกน (3D interaction)", "",
          f"- Po = 0.85f′c(Ag − Ast) + fy·Ast = {f.F(col.Po)} · **φPn,max = 0.65 × 0.80 × Po = {f.F(col.phiPn_max)}**",
          "- วิธี: strain compatibility (εcu = 0.003, Whitney block 0.85f′c, a = β1c) ที่ Pu คงที่ "
          "หามุมแกนสะเทินให้ทิศโมเมนต์ต้านทานตรงทิศ (Mux, Muy) · φ ตาม εt",
          "", "| combo | ตำแหน่ง | Pu | Mux | Muy | φMn (ทิศเดียวกัน) | φ | εt | อัตราส่วน |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        for c in r["checks"]:
            if "reason" in c:
                L.append(f"| {r['name']} | {c['at']} | {f.F(r['Pu'])} | {f.M(c['Mux'])} | {f.M(c['Muy'])} | — | — | — | ❌ {c['reason']} |")
            else:
                L.append(f"| {r['name']} | {c['at']} | {f.F(r['Pu'])} | {f.M(c['Mux'])} | {f.M(c['Muy'])} | "
                         f"{f.M(c['phiMcap'])} | {c['phi']:.3f} | {c['eps_t']:.4f} | {c['ratio']:.3f} {ok(c['ok'])} |")
    w = res["worst"]
    L += ["", f"- อัตราส่วนสูงสุด **{w[0]:.3f}** ({w[1]}, {w[2]}) {ok(res['status']['strength'])}",
          ref("kb/chapter-22.md §22.2, §22.4", "kb/chapter-21.md Table 21.2.2", "kb/chapter-10.md §10.5")]

    # 6
    L += ["## 6. แรงเฉือน", "",
          f"- ปลอก DB{ties['db']:g} @ {ties['s']:.0f} mm · ขาขนาน x = {2 + ties['crossties_x']} · ขาขนาน y = {2 + ties['crossties_y']}",
          "", "| combo | ทิศ | Vu | bw × d | Vc (สมการ) | Vs | φVn | Av,min/s ต้องมี | s,max | ผล |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["shear"]:
        for d in (r["x"], r["y"]):
            L.append(f"| {r['name']} | {d['dir']} | {f.F(d['Vu'])} | {d['bw']:.0f} × {d['d']:.0f} | {f.F(d['Vc'])} {d['eq']}"
                     f"{' (ถึงเพดาน 0.42λ√f′c)' if d['capped'] else ''} | {f.F(d['Vs'])} | {f.F(d['phiVn'])} | "
                     f"{'ใช่' if d['needs_min'] else 'ไม่'} | {d['s_max']:.0f} | {ok(d['ok'])} |")
        if r["biaxial"]["required"]:
            L.append(f"| {r['name']} | สองทิศ | Σ Vu/φVn = {r['biaxial']['sum']:.3f} ≤ 1.5 | | | | | | | {ok(r['biaxial']['ok'])} |")
    if not res["shear"]:
        L.append("| — | — | ไม่มีแรงเฉือนในอินพุต | | | | | | | ⚠️ |")
    L.append("")
    for axis, d in res["seismic"].items():
        if not d["applies"]:
            L.append(f"- §18.3.3 แกน {axis}: ไม่บังคับ — {d['note']}")
            continue
        c = d["check"]
        L.append(f"- §{d['clause']} (ดัดรอบแกน {axis} → เฉือนทิศ {c['dir']}): Mn สูงสุดในช่วง Pu = {f.M(d['Mn'])} (ไม่คูณ φ) → "
                 f"2Mn/ℓu = {f.F(d['V_mn'])}" + (f"; แรงจาก Ω0E ≤ {f.F(d['Ve'])}" if d["with_omega"] else "")
                 + f" → **Ve = {f.F(d['Ve'])}** · φVn (Pu น้อยสุด, s = {d['s']:.0f}) = {f.F(c['phiVn'])} {ok(c['phiVn'] >= d['Ve'])}")
    L.append(ref("kb/chapter-22.md §22.5.1 (รวมแรงเฉือนสองแกน), §22.5.5", "kb/chapter-10.md §10.6.2, §10.7.6.5",
                 "kb/chapter-18.md §18.3.3, §18.4.3.1", "kb/chapter-21.md (φ = 0.75)"))

    # 7
    lo, ti = res["long"], res["tie"]
    L += ["## 7. รายละเอียดเหล็ก", "",
          f"- ρg = {lo['rho']:.2%} (1% – {lo['rho_max']:.0%}) {ok(lo['rho_ok'])} · จำนวน {lo['n']} ≥ 4 {ok(lo['n_ok'])}",
          f"- ระยะว่างเหล็ก {lo['clear']:.0f} mm ≥ max(40, 1.5db, 4/3dagg) = {lo['clear_min']:.0f} mm {ok(lo['clear_ok'])}",
          f"- ปลอก DB{ties['db']:g} ≥ DB{ti['tie_min']:g} {ok(ti['tie_ok'])} · s = {ties['s']:.0f} ≤ min(16db, 48dt, ด้านแคบ) = {ti['s_max']:.0f} mm {ok(ti['s_ok'])}",
          f"- crosstie (§25.7.2.3 เหล็กเว้นเส้น, ระยะว่าง ≤ 150 mm): ต้องการ วิ่งทิศ x {ti['crossties_x']} / ทิศ y {ti['crossties_y']} · "
          f"ใช้ {ties['crossties_x']} / {ties['crossties_y']} {ok(ti['crossties_ok'])}"]
    if res.get("imf"):
        im = res["imf"]
        L.append(f"- IMF: so = {im['so']:.0f} ≤ {im['so_max']:.0f} mm {ok(im['so_ok'])} · ℓo ≥ max(ℓu/6, ด้านใหญ่, 450) = **{im['lo']:.0f} mm** · "
                 f"ปลอกแรกห่างผิวรอยต่อ ≤ {im['first']:.0f} mm · นอก ℓo ใช้ s ตาม §10.7.6.5.2")
    L.append(ref("kb/chapter-10.md §10.6.1, §10.7.3, §10.7.6", "kb/chapter-25.md §25.2.3, §25.7.2",
                 "kb/chapter-18.md §18.4.3.3–18.4.3.5"))

    # 8
    sp = res["splice"]
    L += ["## 8. การต่อทาบเหล็กยืน", "",
          f"- ทาบรับแรงอัด ℓsc = {sp['lsc']:.0f} mm" + (f" → ลดเหลือ 0.83ℓsc = **{sp['lsc_red']:.0f} mm** (ขาปลอกพอตาม §10.7.5.2.1)" if sp["reduced"] else " (ไม่เข้าเงื่อนไขลด 0.83)"),
          f"- ทาบรับแรงดึง: ℓd = {sp['ld']:.0f} mm (ตัวหาร {sp['k']}, ψg = {sp['psi_g']}) · Class A = {sp['class_A']:.0f} mm · Class B = **{sp['class_B']:.0f} mm**",
          "- ใช้ Class B เมื่อเหล็กรับแรงดึงเกิน 0.5fy หรือทาบทุกเส้นในตำแหน่งเดียว (§10.7.5.2.2) — "
          "ตรวจจากหน่วยแรงในเหล็กของ combo ที่วิกฤต"]
    if sp["Ktr_rule"]:
        L.append("- fy ≥ 550: ต้องมี Ktr ≥ 0.5db (§10.7.1.3)")
    L.append(ref("kb/chapter-10.md §10.7.5", "kb/chapter-25.md §25.4.2, §25.5.2, §25.5.5"))

    # 9
    L += ["## 9. รอยต่อ พื้น และฐานราก", ""]
    fl = res["floor"]
    if fl:
        if fl["required"]:
            L.append(f"- §15.5: f′c พื้น {f.S(fl['fc_floor'])} < 0.7f′c เสา ❌ → เลือก (a) เทคอนกรีตเสาทะลุพื้นและเลยออก 600 mm, "
                     "(b) ออกแบบด้วยกำลังพื้น" + (f", หรือ (c) ใช้ f′c เทียบเท่า = {f.S(fl['fc_equiv'])}" if fl["fc_equiv"] else ""))
        else:
            L.append(f"- §15.5: f′c พื้น/เสา = {fl['ratio']:.2f} ≥ 0.7 ✅ ไม่ต้องดำเนินการเพิ่ม")
    else:
        L.append("- §15.5: ไม่มีข้อมูล f′c พื้น — **ยังไม่ตรวจ**")
    if res["system"] == "IMF":
        L.append(f"- ปลอกในรอยต่อคาน-เสา (IMF §18.4.4): ระยะ ≤ so = {res['imf']['so_max']:.0f} mm ตลอดความลึกคานที่ลึกที่สุด")
    else:
        L.append("- ปลอกในรอยต่อคาน-เสา: ≥ 2 ชั้น, ระยะ ≤ 200 mm ภายในความลึกคานที่ลึกที่สุด (§15.3.1.4) "
                 "เว้นแต่มีคานครบ 4 ด้านตาม §15.3.1.1")
    if res["dowels"]:
        dw = res["dowels"]
        L.append(f"- dowel ลงฐานราก ≥ 0.005Ag = {dw['As_req']:,.0f} mm² → ≥ {dw['n']}-DB{col.db:g}; ต่อเหล็กเสาครบทุกเส้น {ok(dw['all_bars_enough'])}")
    L.append("- แรงเฉือนในรอยต่อ (Ch.15) — **ยังไม่ตรวจ**")
    L.append(ref("kb/chapter-15.md §15.3.1, §15.5", "kb/chapter-16.md §16.3.4", "kb/chapter-18.md §18.4.4"))

    # 10
    st = res["status"]
    names = {"strength": "กำลัง (ข้อ 4–5)", "shear": "แรงเฉือน (ข้อ 6)", "detailing": "รายละเอียด (ข้อ 7)",
             "floor": "§15.5 (ข้อ 9)"}
    L += ["## 10. สรุป", ""]
    for k, v in st.items():
        L.append(f"- {names[k]}: {ok(v)}")
    L.append(f"- **ผลรวม: {'ผ่านทุกรายการที่ตรวจ' if all(st.values()) else 'ไม่ผ่าน — ดูรายการ ❌'}**")
    if res["mode"] == "design":
        L.append(f"- แบบที่เลือก: **{col.label()}**, ปลอก DB{ties['db']:g} @ {ties['s']:.0f} mm"
                 + (f" (ช่วง ℓo @ {ties['s_end']:.0f} mm)" if ties.get("s_end") else "")
                 + f", crosstie ทิศ x {ties['crossties_x']} / ทิศ y {ties['crossties_y']}")
    L += ["", "**ยังไม่ตรวจ:** แรงเฉือนในรอยต่อคาน-เสา, การเลือก Class A/B ตามหน่วยแรงจริง, "
          "การยึดฝังของ dowel ในฐานราก, การกระจายแรงอัดเฉพาะที่ (§22.8)"
          + ("" if "Q" in res else ", Q (ไม่มีข้อมูลชั้น)"),
          "", "_ผลลัพธ์ใช้ประกอบรายการคำนวณ วิศวกรผู้รับผิดชอบต้องตรวจและลงนาม_"]
    return "\n".join(L)
