"""Step 9 — Markdown report; every section ends with the KB location it relies on."""
from __future__ import annotations

from .rcsi import Fmt, ok, ref
from .section import As, label

NAME = {"left": "ปลายซ้าย", "mid": "กลางช่วง", "right": "ปลายขวา"}
FACE = {"top": "บน (โมเมนต์ลบ)", "bot": "ล่าง (โมเมนต์บวก)"}


def build(res):
    si = res["si"]
    f = Fmt(si["_units"])
    L = ["# รายการคำนวณคาน คสล. — ACI 318M-19", ""]
    L.append(f"โหมด: **{'ออกแบบ (design)' if res['mode'] == 'design' else 'ตรวจสอบ (check)'}** · "
             f"หน่วยอินพุต: {si['_units']} · ภายใน N, mm, MPa")
    L.append("")
    for lvl, cl, msg in res["messages"]:
        tag = {"FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️"}[lvl]
        L.append(f"> {tag} " + (f"§{cl} " if cl else "") + msg)
    if res.get("stopped"):
        L += ["", "**หยุดการคำนวณ** — แก้ตามข้อความข้างบนแล้วรันใหม่"]
        return "\n".join(L)
    bm, bars, env = res["beam"], res["bars"], res["env"]
    sp = si["span"]
    sysname = {None: "ไม่อยู่ในระบบต้านแผ่นดินไหว", "OMF": "OMF (SDC B)", "IMF": "IMF (SDC C)"}[si.get("system")]

    # 0
    L += ["", "## 0. ขอบเขตและระบบ", "",
          f"- {sysname} · คานสี่เหลี่ยม ไม่อัดแรง · ℓn = {sp['ln']:.0f} mm > 4h = {4 * bm.h:.0f} mm (ไม่ใช่ deep beam) ✅",
          "- ไม่มีแรงบิด/แรงตามแกนที่ต้องคิด (ตามอินพุต)",
          ref("kb/chapter-09.md §9.2, §9.5, §9.9", "kb/chapter-18.md §18.3.2, §18.4.2")]

    # 1
    L += ["## 1. หน้าตัดและวัสดุ", "",
          f"- b × h = {bm.b:.0f} × {bm.h:.0f} mm · ระยะหุ้มถึงปลอก {bm.cover:.0f} mm · ปลอก DB{bm.ds:g} · dagg {bm.dagg:.0f} mm",
          f"- f′c = {f.S(bm.fc)} · β1 = {bm.b1:.3f} · fy = {f.S(bm.fy_spec)} · fyt = {f.S(bm.fyt)}"
          + (f" (ใช้ {min(bm.fyt, 420):.0f} MPa ในแรงเฉือน)" if bm.fyt > 420 else ""),
          ref("kb/chapter-20.md §20.2, §20.5", "kb/chapter-22.md §22.2.2", "references/si-constants-318m.md")]

    # 2
    L += ["## 2. แรงออกแบบ (envelope)", "",
          "| combo | M ปลายซ้าย | M กลางช่วง | M ปลายขวา | V ซ้าย | V ขวา |", "|---|---|---|---|---|---|"]
    for cb in si["combos"]:
        L.append(f"| {cb.get('name', '')} | {f.M(cb['M_left'])} | {f.M(cb['M_mid'])} | {f.M(cb['M_right'])} | "
                 f"{f.F(cb.get('V_left') or 0)} | {f.F(cb.get('V_right') or 0)} |")
    L += ["", "M ลบ = ดึงบน · Mu, Vu ที่ผิวจุดรองรับ / หน้าตัดวิกฤต (§9.4.2–9.4.3)",
          ref("kb/chapter-09.md §9.4")]

    if si.get("_trace_md"):
        L += ["", si["_trace_md"], ref("references/staad-sign-convention.md")]
    # 3
    L += ["## 3. แรงดัด", "", "| หน้าตัด | ผิวรับแรงดึง | Mu | เหล็ก | d | εt | φ | φMn | Mu/φMn | As ≥ As,min | ผล |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in ("left", "mid", "right"):
        for face in ("top", "bot"):
            r = res["flex"][k][face]
            b_ = bars[k][face]
            if r.get("none"):
                continue
            mu = env[k][face]
            L.append(f"| {NAME[k]} | {FACE[face]} | {f.M(mu) if mu else '—'} | {label(b_)} ({As(b_):,.0f} mm²) | "
                     f"{r['d']:.0f} | {r['eps_t']:.4f} | {r['phi']:.3f} | {f.M(r['phiMn'])} | "
                     f"{format(r['ratio'], '.3f') if mu else '—'} | "
                     f"{('✅' if r['As_min_ok'] else '❌') if mu else '—'} | {ok(r['ok']) if mu else 'ไม่มีแรง'} |")
    L += ["", "- strain compatibility (εcu = 0.003, Whitney 0.85f′c, a = β1c) นับเหล็กผิวตรงข้ามเป็นเหล็กอัด · "
          "คานต้อง tension-controlled: εt ≥ εty + 0.003 (§9.3.3.1) · As,min = max(0.25√f′c, 1.4)bwd/fy (§9.6.1.2)",
          ref("kb/chapter-22.md §22.2–22.3", "kb/chapter-21.md Table 21.2.2", "kb/chapter-09.md §9.3.3, §9.6.1")]

    # 4
    sh = res["shear"]
    L += ["## 4. แรงเฉือนและปลอก", "",
          f"- โซนปลาย = {sh['end_zone']:.0f} mm จากผิวจุดรองรับแต่ละข้าง · โซนกลางใช้ Vu ที่ขอบโซนปลาย "
          f"({'เส้นแรงเฉือนตรงผ่านศูนย์ (น้ำหนักแผ่)' if sp.get('V_shape', 'gravity') == 'gravity' else 'แรงเฉือนคงที่'})"
          + (f" · ยกเว้น Av,min ตาม Table 9.6.3.1: {sh['exempt']}" if sh["exempt"] else ""),
          "", "| โซน | Vu | d | ปลอก | Vc (สมการ) | Vs | φVn | s,max ตามยาว | ระยะขา ≤ | ผล |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for k in ("left", "mid", "right"):
        z = sh["zones"][k]
        L.append(f"| {NAME[k]} | {f.F(z['Vu'])} | {z['d']:.0f} | DB{z['ds']:g} {z['legs']} ขา @ {z['s']:.0f} | "
                 f"{f.F(z['Vc'])} {z['eq']}{' (ถึงเพดาน)' if z['capped'] else ''} | {f.F(z['Vs'])} | {f.F(z['phiVn'])} | "
                 f"{z['s_long']:.0f} | {z['leg_sp']:.0f} ≤ {z['s_trans']:.0f} | {ok(z['ok'])} |")
    bad = [(NAME[k], c) for k in ("left", "mid", "right") for c, v in sh["zones"][k]["checks"].items() if not v]
    for nm, c in bad:
        L.append(f"- ❌ {nm}: {c}")
    z0 = sh["zones"]["left"]
    L += ["", f"- Av,min/s = max(0.062√f′c, 0.35)bw/fyt = {z0['Av_min_s']:.3f} mm²/mm · ต้องมีเมื่อ Vu > φ0.083λ√f′c·bw·d "
          f"= {f.F(z0['trigger'])} (§9.6.3.1) · ใช้ปลอกปิดตลอดช่วงเพราะนับเหล็กอัดในกำลัง (§9.7.6.4)",
          ref("kb/chapter-22.md §22.5", "kb/chapter-09.md §9.6.3, §9.7.6.2, §9.7.6.4", "kb/chapter-21.md (φ = 0.75)")]

    # 5
    s = sh.get("seismic")
    if s:
        L += [f"## 5. ข้อกำหนดแผ่นดินไหว ({s['system']})", "",
              f"- เหล็กต่อเนื่องบน {s['cont_top']} / ล่าง {s['cont_bot']} เส้น ≥ 2 {ok(s['two_bars_ok'])} · "
              f"เหล็กล่างต่อเนื่อง ≥ ¼ ของมากสุด {ok(s['bot_quarter_ok'])}"]
        if s["system"] == "IMF":
            Mn = s["Mn"]
            L.append(f"- Mn⁺ ที่ผิวจุดต่อ ≥ Mn⁻/3: ซ้าย {f.M(Mn['left']['pos'])} vs {f.M(Mn['left']['neg'] / 3)}, "
                     f"ขวา {f.M(Mn['right']['pos'])} vs {f.M(Mn['right']['neg'] / 3)} {ok(s['third_ok'])}")
            L.append(f"- Mn ทุกหน้าตัด ≥ ⅕ ของ Mn สูงสุดที่ผิวจุดต่อ {ok(s['fifth_ok'])}")
            L.append(f"- Ve = (Mnl + Mnr)/ℓn" + (" + wuℓn/2" if s["wu_given"] else " (ไม่ได้ให้ wu → **ยังไม่รวมแรงเฉือนจากน้ำหนักแนวดิ่ง**)")
                     + f" = {f.F(s['V_mn'])}" + (f"; จาก 2E = {f.F(s['V_2E'])}" if s["V_2E"] else "")
                     + f" → **Ve = {f.F(s['Ve'])}** (ใช้เป็น Vu ขั้นต่ำทุกโซน)")
            L.append(f"- hoop ปลายคานยาว ≥ 2h = {2 * bm.h:.0f} mm, วงแรก ≤ 50 mm จากผิว, s ≤ min(d/4, 8db, 24dt, 300); นอกช่วง s ≤ d/2")
        L.append(ref("kb/chapter-18.md §18.3.2, §18.4.2"))

    # 6
    D = res["det"]
    L += ["## 6. รายละเอียดเหล็กและการใช้งาน", ""]
    for (k, face), v in D["layers"].items():
        L.append(f"- {NAME[k]} {FACE[face].split()[0]}: ≤ {v['per_layer']} เส้น/ชั้น {ok(v['fits'])} · ระยะว่าง {v['clear']:.0f} ≥ {v['clear_min']:.0f} mm {ok(v['clear'] >= v['clear_min'] - 1e-9)}")
    for (k, face), v in D["crack"].items():
        L.append(f"- คุมรอยร้าว {NAME[k]} {FACE[face].split()[0]}: s = {v['s']:.0f} ≤ {v['s_max']:.0f} mm {ok(v['ok'])}")
    if "min_depth" in D:
        md = D["min_depth"]
        L.append(f"- ความลึกขั้นต่ำ Table 9.3.1.1 ({sp['support']}): h,min = {md['h_min']:.0f} mm → "
                 + ("✅ ไม่ต้องคำนวณการแอ่นตัว" if md["ok"] else "⚠️ **ต้องคำนวณการแอ่นตัว §24.2 (ยังไม่ตรวจ)**"))
    else:
        L.append("- การแอ่นตัว: ไม่ได้ระบุ `support` — **ยังไม่ตรวจ**")
    if D["skin"]:
        L.append("- ⚠️ h > 900 mm → ต้องมีเหล็กผิวข้างในช่วง h/2 จากผิวรับแรงดึง (§9.7.2.3)")
    if D["Ktr"]:
        L.append("- ⚠️ fy ≥ 550 MPa → ช่วงฝังยึด/ทาบต้องมี Ktr ≥ 0.5db (§9.7.1.4)")
    L.append(ref("kb/chapter-25.md §25.2", "kb/chapter-24.md §24.3", "kb/chapter-09.md §9.3.1, §9.7.2"))

    # 7
    dv = res["dev"]
    L += ["## 7. การตัดเหล็ก ระยะฝังยึด และต่อทาบ", "",
          "| ข้อมูล | ปลายซ้าย | ปลายขวา |", "|---|---|---|"]
    c = res["cut"]
    L.append(f"| เหล็กบนเสริมพิเศษ (นอกจากเหล็กต่อเนื่อง) | {c['left']['extra']} เส้น | {c['right']['extra']} เส้น |")
    L.append(f"| จุดดัดกลับ (จากผิวจุดรองรับ) | {c['left']['x_ip']:.0f} mm | {c['right']['x_ip']:.0f} mm |")
    L.append(f"| เหล็กต่อเนื่องรับได้เองเมื่อห่างผิว | {c['left']['x_cont']:.0f} mm | {c['right']['x_cont']:.0f} mm |")
    L.append(f"| **ความยาวเหล็กพิเศษจากผิวจุดรองรับ** | **{c['left']['L']:.0f} mm** | **{c['right']['L']:.0f} mm** |")
    L.append(f"| เหล็กต่อเนื่อง ≥ ⅓ ของเหล็กบนที่จุดรองรับ | {ok(c['left']['third_ok'])} | {ok(c['right']['third_ok'])} |")
    L += ["", "- ความยาว = max(จุดที่เหล็กต่อเนื่องพอ + max(d, 12db), ℓd) และถ้าเหล็กต่อเนื่อง < ⅓ ต้องเลยจุดดัดกลับ max(d, 12db, ℓn/16) — "
          "โมเมนต์ระหว่างจุดใช้พาราโบลาผ่าน 3 จุด (รูปน้ำหนักแผ่) **ถ้ามีแรงจุดให้เทียบกับ diagram จาก STAAD**"]
    if any(c[k]["half_span"] for k in ("left", "right")):
        L.append("- ⚠️ ความยาวเกินครึ่งช่วง → ใช้เหล็กบนต่อเนื่องตลอดช่วงแทน")
    t, b_ = dv["top"], dv["bot"]
    L += ["", "| เหล็ก | ℓd | ℓdh (ขอ) | ทาบ Class A | ทาบ Class B | ทาบรับแรงอัด |", "|---|---|---|---|---|---|",
          f"| บน (ψt = {t['psi_t']}) | {t['ld']:.0f} | {t['ldh']:.0f} | {t['lap_A']:.0f} | **{t['lap_B']:.0f}** | {t['lap_c']:.0f} |" if t['lap_c'] else "",
          f"| ล่าง | {b_['ld']:.0f} | {b_['ldh']:.0f} | {b_['lap_A']:.0f} | **{b_['lap_B']:.0f}** | {b_['lap_c']:.0f} |" if b_['lap_c'] else "",
          "", f"- ℓd ตาม Table 25.4.2.3 — เหล็กบน: {'แถวแรก (ระยะว่าง ≥ db, หุ้ม ≥ db, ปลอก ≥ ขั้นต่ำ)' if t['good'] else '**แถวกรณีอื่น** (ระยะว่างหรือระยะหุ้ม < db)'}"
          f" · เหล็กล่าง: {'แถวแรก' if b_['good'] else '**กรณีอื่น**'} · ℓdh ใช้ ψr = 1.6, ψo = 1.25 (อนุรักษ์) — "
          "ใช้ขอที่ปลายคานริมที่ยึดเข้าเสา · ต่อทาบเหล็กบนช่วงกลางคาน เหล็กล่างใกล้จุดรองรับ ใช้ Class B (§9.7.7.5)",
          ref("kb/chapter-09.md §9.7.3", "kb/chapter-25.md §25.4, §25.5")]

    # 8
    ig = res["integrity"]
    L += ["## 8. Structural integrity", ""]
    L.append(f"- ตำแหน่งคาน: {'คานริม' if ig['position'] == 'perimeter' else 'คานภายใน' if ig['position'] == 'interior' else '**ไม่ระบุ — ตรวจแบบคานภายใน**'}")
    L.append(f"- เหล็กล่างต่อเนื่อง ≥ max(¼ ของมากสุด, 2 เส้น) {ok(ig['bot_ok'])}")
    if "top_ok" in ig:
        L.append(f"- คานริม: เหล็กบนต่อเนื่อง ≥ max(⅙ ของเหล็กบนที่จุดรองรับ, 2 เส้น) {ok(ig['top_ok'])} · ต้องอยู่ในปลอกปิดตลอดช่วง")
    L.append("- เหล็ก integrity ผ่านภายในเหล็กยืนของเสา; จุดรองรับไม่ต่อเนื่องยึดให้ได้ fy ที่ผิว")
    L.append(ref("kb/chapter-09.md §9.7.7"))

    # 9
    st = res["status"]
    names = {"flexure": "แรงดัด (ข้อ 3)", "shear": "แรงเฉือน (ข้อ 4)", "seismic": "แผ่นดินไหว (ข้อ 5)",
             "detailing": "รายละเอียด (ข้อ 6)", "integrity": "integrity (ข้อ 8)"}
    L += ["## 9. สรุป", "", "| หน้าตัด | เหล็กบน | เหล็กล่าง | ปลอก |", "|---|---|---|---|"]
    for k in ("left", "mid", "right"):
        z = sh["zones"][k]
        L.append(f"| {NAME[k]} | {label(bars[k]['top'])} | {label(bars[k]['bot'])} | DB{z['ds']:g} {z['legs']} ขา @ {z['s']:.0f} mm |")
    L.append("")
    for k, v in st.items():
        L.append(f"- {names[k]}: {ok(v)}")
    L.append(f"- **ผลรวม: {'ผ่านทุกรายการที่ตรวจ' if all(st.values()) else 'ไม่ผ่าน — ดูรายการ ❌'}**")
    pend = ["การแอ่นตัวจริง (ถ้าไม่ผ่าน Table 9.3.1.1)" if not D.get("min_depth", {}).get("ok", False) else None,
            "แรงบิด", "จุดตัดเหล็กเมื่อมีแรงจุด (เทียบ diagram STAAD)",
            "§9.7.3.5 การตัดเหล็กในโซนแรงดึง", "เหล็กแขวน (hanger) ที่คานซอยมาฝาก"]
    L += ["", "**ยังไม่ตรวจ:** " + ", ".join(p for p in pend if p),
          "", "_ผลลัพธ์ใช้ประกอบรายการคำนวณ วิศวกรผู้รับผิดชอบต้องตรวจและลงนาม_"]
    return "\n".join(x for x in L if x is not None)
