"""Markdown report; every section ends with the KB location it relies on."""
from __future__ import annotations

from .rcsi import G, KSC, Fmt, ld_tension, ok, ref
from .coeffs import CASE_NAME
from .engine import edge_name


def build(res):
    si = res["si"]
    kgf = si["_units"] == "kgf-m"
    f_ = Fmt(si["_units"])

    def Mm(nmm):            # N·mm per metre strip → kN·m/m
        return f"{nmm / 1e6:,.2f}" + (f" ({nmm / G / 1e6:,.3f})" if kgf else "")

    def q(mpa):             # N/mm² → kPa
        return f"{mpa * 1e3:,.2f} kPa" + (f" ({mpa * 1e6 / G:,.0f} kg/m²)" if kgf else "")

    def wl(npmm):           # N/mm → kN/m
        return f"{npmm:,.2f}" + (f" ({npmm / G:,.3f})" if kgf else "")

    mu = "kN·m/m" + (" [tf·m/m]" if kgf else "")
    wu_unit = "kN/m" + (" [t/m]" if kgf else "")
    L = ["# รายการคำนวณพื้นบนคาน (ทางเดียว / สองทาง) — ACI 318M-19", "",
         f"โหมด: **{'ออกแบบ (design)' if res['mode'] == 'design' else 'ตรวจสอบ (check)'}** · หน่วยอินพุต: {si['_units']} · ภายใน N, mm, MPa", ""]
    for lvl, cl, msg in res["messages"]:
        L.append(f"> {dict(FAIL='❌', WARN='⚠️', INFO='ℹ️')[lvl]} " + (f"§{cl} " if cl else "") + msg)
    if res.get("stopped"):
        return "\n".join(L + ["", "**หยุดการคำนวณ** — แก้ตามข้อความข้างบนแล้วรันใหม่"])
    m, h, P = si["materials"], res["h"], res["panels"]
    cover = si.get("cover", 20.0)

    # 0 scope
    L += ["", "## 0. ขอบเขต", "",
          "- พื้นตันหล่อในที่ ไม่อัดแรง รองรับด้วยคานทุกด้าน น้ำหนักแผ่สม่ำเสมอ ผังเป็นตาราง (grid) · คิดต่อแถบกว้าง 1 m",
          "- แผงที่ m = S/L ≥ 0.5 → **พื้นสองทาง** โมเมนต์จากตารางสัมประสิทธิ์ Method 2 (M = C·wu·S²) "
          "· m < 0.5 → **พื้นทางเดียว** สัมประสิทธิ์ Table 6.5.2 (M = C·wu·ℓn²)",
          "- S = ช่วงสั้น = ค่าน้อยกว่าของ (ระยะศูนย์กลางคาน) และ (ช่วงว่าง + 2h) · ชื่อแผง เช่น AB-12 = ระหว่างแนว A–B และ 1–2",
          ref("kb/chapter-08.md §8.2.1, §8.3.1.2", "kb/chapter-07.md §7.3.1", "kb/chapter-06.md §6.5",
              "references/method2-coefficients.md")]

    # 1 materials & loads
    Dsw = si["gamma_c"] * h
    fac = si.get("factors")
    wu_txt = (f"{fac['D']}D + {fac['L']}L (ผู้ใช้กำหนด)" if fac else "max(1.4D, 1.2D + 1.6L)")
    L += ["## 1. วัสดุและน้ำหนัก", "",
          f"- f′c = {f_.S(m['fc'])} · fy = {f_.S(m['fy'])} · ระยะหุ้ม {cover:.0f} mm · คานกว้าง {si['beam_width']:.0f} mm",
          f"- **h = {h:.0f} mm** · น้ำหนักพื้น = {q(Dsw)} · SDL = {q(si['loads'].get('sdl', 0.0))} · LL = {q(res['L'])}",
          f"- D = {q(res['D'])} · L = {q(res['L'])} · wu = {wu_txt} = **{q(res['wu'])}** · ใช้งาน w = {q(res['D'] + res['L'])}",
          ref("kb/chapter-05.md §5.3.1", "kb/chapter-19.md", "kb/chapter-20.md §20.5.1.3", "references/si-formulas.md")]

    # 2 panels
    L += ["## 2. ผังแผงและความหนาขั้นต่ำ", "",
          "| แผง | Lx × Ly (m) | ชนิด | กรณี | ขอบต่อเนื่อง (W E S N) | S (m) | m | h ขั้นต่ำ | เกณฑ์ | h ใช้ |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for k, p in sorted(P.items(), key=lambda t: (t[0][1], t[0][0])):
        c = "".join("●" if p["cont"][e] else "○" for e in "WESN")
        case = f"{p['case']} — {CASE_NAME[p['case']]}" if p["case"] else f"{p['n_spans']} ช่วงต่อกัน"
        L.append(f"| {p['name']} | {p['Lx'] / 1e3:.2f} × {p['Ly'] / 1e3:.2f} | {'สองทาง' if p['kind'] == 'two-way' else 'ทางเดียว (' + p['short'] + ')'} "
                 f"| {case} | {c} | {p['S'] / 1e3:.2f} | {p['m']:.3f} | {p['h_min']:.0f} | {p['h_rule']} | {h:.0f} {ok(p['h_ok'])} |")
    L += ["", "- ● = ต่อเนื่อง (มีแผงข้างเคียง) ○ = ไม่ต่อเนื่อง · กรณี Method 2 = 1 + จำนวนขอบไม่ต่อเนื่อง",
          "- พื้นสองทาง: Table 8.3.1.2 ใช้ ℓn ด้านยาว และ β = ℓn ยาว/สั้น · พื้นทางเดียว: Table 7.3.1.1 ใช้ ℓ × (0.4 + fy/700)",
          ref("kb/chapter-08.md §8.3.1.2", "kb/chapter-07.md §7.3.1.1", "kb/chapter-24.md §24.2")]
    if res.get("alphas"):
        hb = si["beam_depth"]
        L += [f"**αf ของคาน** (คาน {si['beam_width']:.0f} × {hb:.0f} mm รวมพื้น, ปีกข้างละ min(hb − h, 4h) = "
              f"{min(hb - h, 4 * h):.0f} mm, Is ใช้ความกว้างพื้นถึงกึ่งกลางแผงข้างเคียง, Ec เท่ากัน)", "",
              "| แผง | αf W | αf E | αf S | αf N | αfm | คานขอบ αf ≥ 0.8 |", "|---|---|---|---|---|---|---|"]
        for k, p in sorted(P.items(), key=lambda t: (t[0][1], t[0][0])):
            a = p["alpha"]
            disc = [e for e in "WESN" if not p["cont"][e]]
            L.append(f"| {p['name']} | " + " | ".join(f"{a[e]:.2f}" for e in "WESN") + f" | {p['alpha_fm']:.2f} | "
                     + (ok(all(a[e] >= 0.8 for e in disc)) if disc else "— (แผงใน)") + " |")
        L.append(ref("kb/chapter-08.md §8.4.1 (นิยามคาน), §8.3.1.2, §8.7.3"))

    # 3 positive
    L += ["## 3. โมเมนต์บวกกลางช่วงและเหล็กล่าง", "",
          f"| แผง | ทิศเหล็ก | C | Mu ({mu}) | d (mm) | As ต้องการ | As,min | เหล็ก | As ให้ | φMn ({mu}) | ผล |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, p in sorted(P.items(), key=lambda t: (t[0][1], t[0][0])):
        for d in ("x", "y"):
            r = p["bot"][d]
            C = p["M"]["coef"][d]["pos"]
            Mu = p["M"]["pos"][d]
            if not r:
                L.append(f"| {p['name']} | {d} | {C:.4f} | {Mm(Mu)} | — | หนาไม่พอ | — | — | — | — | ❌ |")
                continue
            dd = h - cover - (r["db"] / 2 if d == p["short"] else 1.5 * r["db"])
            req = "—" if r["As_req"] is None else f"{r['As_req']:,.0f}"
            phiMn = r.get("phiMn")
            if phiMn is None:
                from .strip import flexure
                fl = flexure(Mu, dd, h, m["fc"], m["fy"], r["db"], r["s"])
                phiMn, okv = fl["phiMn"], fl["ok"]
            else:
                okv = r["ok"]
            role = r.get("role", "รับแรงดัด")
            L.append(f"| {p['name']} | {d}{' (สั้น)' if d == p['short'] else ''} | {C:.4f} | {Mm(Mu)} | {dd:.0f} | {req} | "
                     f"{0.0018 * 1000 * h:,.0f} | DB{r['db']:g} @ {r['s']:.0f}{'' if role == 'รับแรงดัด' else ' ' + role} | "
                     f"{r['As']:,.0f} | {Mm(phiMn)} | {ok(okv)} |")
    L += ["", "- As มีหน่วย mm²/m · เหล็กทิศสั้นวางชั้นล่างสุด d = h − หุ้ม − db/2 · ทิศยาววางชั้นบน d = h − หุ้ม − 1.5db",
          f"- ระยะห่างสูงสุด: สองทาง min(2h, 450) = {min(2 * h, 450):.0f} · ทางเดียว min(3h, 450) = {min(3 * h, 450):.0f} · "
          f"เหล็กกันร้าว min(5h, 450) = {min(5 * h, 450):.0f} mm · As,min = 0.0018bh",
          "- Method 2: แถบเสา (column strip) ใช้ 2/3 ของค่านี้ได้ — รายงานนี้ใช้เหล็กเท่ากันทั้งแผง (ปลอดภัย)",
          ref("kb/chapter-08.md §8.6.1, §8.7.2", "kb/chapter-07.md §7.6.1, §7.7.2", "kb/chapter-24.md §24.4.3",
              "kb/chapter-22.md §22.2–22.3", "kb/chapter-21.md §21.2")]

    # 4 negative
    L += ["## 4. โมเมนต์ลบที่ขอบแผงและเหล็กบน", "",
          f"| ขอบ | ต่อเนื่อง | Mu ด้านซ้าย/ล่าง · ขวา/บน ({mu}) | Mu ออกแบบ | เหล็กบน | As ให้ | ผล |",
          "|---|---|---|---|---|---|---|"]
    unb = []
    for k, E in sorted(res["edges"].items()):
        sides = " · ".join(f"{P[s[0]]['name']}: {Mm(s[2])}" for s in E["sides"])
        if E["top"] is None:
            L.append(f"| {edge_name(k)} | {'ใช่' if E['cont'] else 'ไม่'} | {sides} | 0 | เหล็กกันร้าว/เหล็กเสริมบนขั้นต่ำ (แนะนำ) | — | — |")
            continue
        t = E["top"]
        okv = t.get("ok", True)
        L.append(f"| {edge_name(k)} | {'ใช่' if E['cont'] else 'ไม่'} | {sides} | {Mm(E['Mu'])} | DB{t['db']:g} @ {t['s']:.0f} | "
                 f"{t['As']:,.0f} | {ok(okv)} |")
        if E.get("unbalanced"):
            unb.append(edge_name(k))
    L += ["", "- ขอบที่ต่อเนื่อง: ใช้ค่ามากกว่าของสองแผง (ปลอดภัย) — Method 2 ยอมให้กระจาย 2/3 ของผลต่างตาม stiffness ถ้าต่างกันเกิน 20%"]
    if unb:
        L.append(f"- ⚠️ ผลต่างเกิน 20% ที่: {', '.join(unb)} — ใช้ค่ามากกว่าแล้ว แต่โมเมนต์ที่ไม่สมดุลถ่ายเป็นแรงบิดในคาน (ยังไม่ตรวจ)")
    L += ["- ขอบไม่ต่อเนื่อง: Method 2 ใช้สัมประสิทธิ์ขอบไม่ต่อเนื่อง (≈ 2/3 ของโมเมนต์บวก) · ทางเดียวใช้ 1/24 (หล่อเป็นเนื้อเดียวกับคานขอบ)",
          ref("references/method2-coefficients.md", "kb/chapter-06.md Table 6.5.2", "kb/chapter-08.md §8.7.2")]

    # 5 shear
    L += ["## 5. แรงเฉือน (ทิศช่วงสั้น ที่ระยะ d จากผิวคาน)", "",
          "| แผง | ขอบ | ตัวคูณ | Vu (kN/m) | d | ρw | φVc (kN/m) | ผล |", "|---|---|---|---|---|---|---|---|"]
    for k, p in sorted(P.items(), key=lambda t: (t[0][1], t[0][0])):
        for r in p["shear"]:
            L.append(f"| {p['name']} | {r['edge']} | {r['factor']:.2f} | {r['Vu'] / 1e3:,.1f} | {r['d']:.0f} | {r['rho']:.4f} | "
                     f"{r['phiVc'] / 1e3:,.1f} | {ok(r['ok'])} |")
    L += ["", "- Vu = (ตัวคูณ)·wu·ℓn/2 − wu·d · ตัวคูณ 1.15 ที่ผิวนอกของจุดรองรับในตัวแรกของพื้นทางเดียว (Table 6.5.4)",
          "- Vc = 0.66λsλ(ρw)^⅓√f′c·bd ≤ 0.42λ√f′c·bd (ไม่มีเหล็กเฉือน), λs = √(2/(1+0.004d)) ≤ 1, φ = 0.75",
          ref("kb/chapter-22.md §22.5.5.1", "kb/chapter-06.md Table 6.5.4", "kb/chapter-21.md §21.2")]

    # 6 crack & corner
    L += ["## 6. คุมรอยร้าว (พื้นทางเดียว) และเหล็กมุม", ""]
    ow = [p for p in P.values() if p["kind"] == "one-way"]
    if ow:
        sm = ow[0]["crack"]["s_max"]
        L.append(f"- Table 24.3.2 ด้วย fs = (2/3)fy, cc = {cover:.0f} mm → s ≤ {sm:.0f} mm: "
                 + ", ".join(f"{p['name']} {ok(p['crack']['ok'])}" for p in ow))
    else:
        L.append("- ไม่มีพื้นทางเดียว (พื้นสองทางคุมด้วยระยะ 2h ตาม §8.7.2.2)")
    if res["corners"]:
        L += ["", "| แผง | มุม | Mu = Mu บวกสูงสุดของแผง | ยาวจากมุมแต่ละทิศ ≥ ℓยาว/5 | เหล็ก (บนและล่าง) |", "|---|---|---|---|---|"]
        for c in res["corners"]:
            b = c["bars"]
            L.append(f"| {P[c['panel']]['name']} | {c['corner']} | {Mm(c['Mu'])} | {c['extent'] / 1e3:.2f} m | "
                     + (f"DB{b['db']:g} @ {b['s']:.0f} ทั้งสองชั้น สองทิศ ขนานขอบ" if b else "❌") + " |")
        L.append("\n- วางเป็นสองชั้นขนานขอบพื้นทั้งบนและล่าง (นับเหล็กหลักเดิมรวมได้) · ใช้เมื่อคานขอบ αf > 1.0")
    L.append(ref("kb/chapter-24.md §24.3.2", "kb/chapter-08.md §8.7.3"))

    # 7 beam loads
    L += ["## 7. น้ำหนักที่ถ่ายลงคาน (ใช้กับสกิลคาน)", "",
          f"| คาน | ยาว (m) | w ใช้งาน ({wu_unit}) | wu ประลัย ({wu_unit}) | ที่มา |", "|---|---|---|---|---|"]
    for k, b in sorted(res["beams"].items()):
        frm = "; ".join(f"{P[x[0]]['name']} {x[1]}" for x in b["from"])
        L.append(f"| {edge_name(k)} | {b['len'] / 1e3:.2f} | {wl(b['ws'])} | {wl(b['wu'])} | {frm} |")
    L += ["", "- เป็นน้ำหนักแผ่สม่ำเสมอเทียบเท่า (Method 2: คานด้านสั้น wS/3, คานด้านยาว wS/3·(3−m²)/2) ยังไม่รวมน้ำหนักคานและผนัง",
          "- พื้นทางเดียว: คานด้านยาว wS/2 · คานด้านสั้นใส่ wS/3 เผื่อไว้ (ปลอดภัย)",
          ref("references/method2-coefficients.md")]

    # 8 detailing
    t_db = max([E["top"]["db"] for E in res["edges"].values() if E["top"]] or [10])
    ld = ld_tension(t_db, m["fy"], m["fc"], top=False, epoxy=False, lam=1.0, good=True)["ld"]
    L += ["## 8. รายละเอียดเหล็ก (แนะนำ)", "",
          "- เหล็กล่าง: ยื่นถึงขอบพื้น ฝังเข้าคานขอบ ≥ 150 mm · เหล็กบนขอบไม่ต่อเนื่อง: งอขอยึดเข้าคานขอบ พัฒนา fy ที่ผิวคาน",
          f"- เหล็กบนที่ขอบต่อเนื่อง: ยื่นจากผิวคาน ≥ ค่ามากกว่าของ 0.30ℓn (ช่วงที่ยาวกว่า) และ ℓd = {ld:.0f} mm (DB{t_db:g}) — ตามแนวปฏิบัติ "
          "(ACI 318-19 ไม่ได้กำหนดความยาวเหล็กพื้นบนคานโดยตรง)",
          "- ระยะห่างเหล็กแถบเสา ≤ 1.5 เท่าของแถบกลาง ถ้าลดเหล็กแถบเสาเป็น 2/3",
          ref("kb/chapter-08.md §8.7.4.1", "kb/chapter-25.md §25.4.2")]

    # 9 summary & not checked
    st = res["status"]
    L += ["## 9. สรุป", "",
          f"- ความหนา h = {h:.0f} mm: ความหนาขั้นต่ำ {ok(st['thickness'])} · แรงดัด/แรงเฉือน/ระยะห่าง {ok(st['flexure_shear'])}",
          f"- คอนกรีตพื้น ≈ {sum(p['Lx'] * p['Ly'] for p in P.values()) * h / 1e9:,.2f} m³ (คิดเต็มแผงศูนย์กลางคาน)", "",
          "### ยังไม่ตรวจ (ต้องพิจารณาเอง)", "",
          "- การโก่งตัวที่คำนวณ (§24.2) — ไม่ต้องถ้าผ่านความหนาขั้นต่ำ และไม่มีผนังที่เสียหายง่าย",
          ("- αf คำนวณจากความลึกคานเดียวกันทุกเส้น — ถ้าคานแต่ละเส้นลึกไม่เท่ากันให้ตรวจแยก" if res.get("alphas") else
           "- αfm จริงของคาน (ไม่ได้ให้ beam_depth จึงสมมติคานแข็ง) และคานขอบ αf ≥ 0.8 / αf > 1.0 สำหรับเหล็กมุม"),
          "- น้ำหนักจุด/น้ำหนักผนังบนพื้น ช่องเปิด พื้นยื่น (cantilever) และพื้นต่างระดับ",
          "- แรงบิดในคานจากโมเมนต์ไม่สมดุล และการออกแบบคาน (ใช้สกิลคาน)",
          "- พื้นเป็นไดอะแฟรม/แรงแผ่นดินไหว (§12, §18.12) · การป้องกันไฟ (ความหนา/ระยะหุ้มตามกฎหมายไฟ)",
          "- ความยาวต่อทาบและจุดตัดเหล็กที่ละเอียด (ใช้ค่าแนะนำในหัวข้อ 8)"]
    return "\n".join(L)
