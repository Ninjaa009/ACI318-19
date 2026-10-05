---
name: rc-column-aci318m19
description: ออกแบบ (เลือกเหล็กยืน ปลอก crosstie ให้อัตโนมัติ) และตรวจสอบเสา คสล. หน้าตัดสี่เหลี่ยมปลอกเดี่ยว ตาม ACI 318M-19 โดยใช้ knowledge base ของโครงการใน kb/ เป็นแหล่งอ้างอิงหลัก ครอบคลุม OMF/IMF, Q (sway), ความชะลูดและการขยายโมเมนต์, 3D interaction สองแกนแบบ strain compatibility, แรงเฉือนสองทิศพร้อม Nu และ Ve แผ่นดินไหว, ρg/ระยะว่าง/ปลอก/crosstie/so/ℓo, ระยะทาบ, §15.5 และ dowel อินพุต kgf-m (ksc, tf) หรือ SI รายงานทุกหัวข้ออ้างไฟล์และข้อใน KB ใช้เมื่อผู้ใช้พูดถึง "ออกแบบเสา", "ตรวจเสา", "เลือกเหล็กเสา", "column", "biaxial", "interaction", "เสาชะลูด", "ปลอกเสา", "ทาบเหล็กเสา", "เสา STAAD", "IMF", "OMF" หรือถามข้อกำหนดเสาใน ACI 318 ไม่ใช่สำหรับคาน (rc-beam-aci318m19), เสากลม/ปลอกเกลียว, โครง sway หรือ SMF
---

# เสา คสล. ACI 318M-19 — colkit

ผลลัพธ์ใช้ประกอบรายการคำนวณ วิศวกรผู้รับผิดชอบต้องตรวจและลงนามเอง

## กฎ

1. **KB มาก่อน** — คำถามข้อกำหนดให้เปิด `kb/INDEX.md` แล้วอ่านไฟล์บทที่เกี่ยวข้อง ตอบพร้อม § และชื่อไฟล์ ถ้า KB ไม่มีให้บอกว่าไม่มี ห้ามเติมจากความจำโดยไม่บอก
2. **ค่า SI** — ใช้ `references/si-formulas.md` และ `references/si-constants-318m.md` (KB เป็นหน่วย inch-pound)
3. **ตัวเลขทุกตัวมาจาก `scripts/column.py`** — ห้ามคำนวณเองในหัว ห้ามใช้ Bresler/สูตรประมาณแทน
4. **ห้ามเดาอินพุต** ที่มีผลต่อผล: f′c, fy, ขนาดหน้าตัด, ℓu, ระบบ (null/OMF/IMF), แรงทุก combo พร้อมโมเมนต์ปลายบน-ล่าง และทิศแกน → ถาม ค่าที่มี default ใช้ได้แต่ต้องแจ้งผู้ใช้
5. **หน่วยไทย:** ksc × 0.0980665 = MPa — SD40 = 392.3 MPa (ไม่ใช่ 420), SD50 = 490.3 MPa
6. ห้ามสรุป "ผ่านทั้งหมด" ถ้ารายงานยังมีหัวข้อ "ยังไม่ตรวจ" — ต้องย้ำรายการนั้นทุกครั้ง
7. รัน `python3 scripts/test_column.py` ครั้งแรกในเซสชัน ต้องผ่านทั้งหมด

## Workflow

| ขั้น | งาน | KB |
|---|---|---|
| 0 | ระบบ: null / OMF / IMF — **SMF หยุด** | chapter-18 |
| 1 | หน้าตัด วัสดุ (design: เลือกเหล็กเอง) | chapter-10, 20, 22 |
| 2 | แรงจาก STAAD ทุก combo: Pu, Mx/My ปลายบน+ล่าง, Vux/Vuy | — |
| 3 | Q ≤ 0.05 → non-sway; **sway หยุด** | chapter-06 §6.6.4.3 |
| 4 | kℓu/r, M1/M2 (จาก V·L หรือ `curv_x/curv_y`), δ, M2,min, Mc ≤ 1.4M | chapter-06 §6.2.5, 6.6.4 |
| 5 | φPn,max; 3D interaction ที่ปลายบน, ปลายล่าง, กลางเสา (ขยาย) | chapter-22 §22.4, chapter-21 |
| 6 | เฉือนสองทิศ + Nu + สองแกน; Ve ของ OMF/IMF | chapter-22 §22.5, chapter-18 |
| 7 | ρg, ระยะว่าง, ปลอก, crosstie, so/ℓo | chapter-10, 25, 18 |
| 8 | ทาบรับแรงอัด/ดึง | chapter-10 §10.7.5, chapter-25 |
| 9 | ปลอกในจุดต่อ, §15.5, dowel | chapter-15, 16, 18 |
| 10 | สรุป + รายการยังไม่ตรวจ | — |

ขั้นตอน:
1. รวบรวมอินพุต → เขียน JSON (แบบใน `examples/`)
2. `python3 scripts/column.py input.json` (เพิ่ม `--json` ถ้าต้องการผลดิบ) — exit 0 = ผ่าน, 1 = มีข้อไม่ผ่านหรือหยุด
3. ไม่ผ่าน: δ สูง/ไม่เสถียร → ขยายหน้าตัดก่อน; กำลังไม่พอ → `mode: "design"` หรือเพิ่มเหล็ก; เฉือน → ลดระยะปลอก/เพิ่มขา แล้วรันใหม่
4. ส่งรายงานทั้งฉบับ (ทุกหัวข้อมีบรรทัด "อ้างอิง: kb/…") และสรุปสั้น ๆ เป็นภาษาไทย

## โหมด

- `"mode": "check"` — ตรวจตามเหล็กที่ให้ใน `bars` และ `ties`
- `"mode": "design"` — ไม่ต้องให้ `bars`: ไล่ทุกขนาดใน `design.db_options` และจำนวนต่อด้าน ที่ผ่าน ρ ≤ `design.rho_max` และระยะว่าง เรียงตาม Ast น้อยไปมาก เลือกชุดแรกที่ผ่านกำลังทุก combo แล้วเลือกปลอก (ขนาดตาม §25.7.2.2, crosstie ตาม §25.7.2.3, ระยะปัดลงทีละ 25 mm ให้ผ่านเฉือนและ s,max; IMF เลือก so ในช่วง ℓo) รายงานแสดงชุดที่ลองและอัตราส่วน

## อินพุต JSON

| key | ความหมาย | kgf-m | SI | default |
|---|---|---|---|---|
| `mode` | `check` / `design` | | | check |
| `units` | `kgf-m` / `SI` | | | kgf-m |
| `system` | `null` / `OMF` / `IMF` (`SMF` หยุด) | | | null |
| `section` | `{b, h}` — b ขนานแกน x | m | mm | **ต้องให้** |
| `materials` | `{fc, fy, fyt}` | ksc | MPa | fyt = fy |
| `bars` | `{db, nx, ny}` — nx เส้นต่อด้านขนาน x (รวมมุม), ny ต่อด้านขนาน y | mm | mm | check: ต้องให้ |
| `ties` | `{db, s, s_end, crossties_x, crossties_y}` — crosstie_x = เส้นที่วิ่งขนาน x | mm | mm | 10, 150, –, 0, 0 |
| `cover` | ระยะหุ้มถึงผิวปลอก | mm | mm | 40 |
| `length` | `{lu หรือ lux/luy, L, k, beta_dns, ei: "a"/"b", r: "sqrt"/"0.3h"}` | m | m | k 1.0, βdns 0.6, a |
| `story` | `{sum_Pu, delta_o (mm), Vus, lc (m)}` | kgf | kN | ไม่มี → แจ้งว่ายังไม่ตรวจ Q |
| `combos[]` | `{name, Pu, Mx_top, Mx_bot, My_top, My_bot, Vux, Vuy, Vux_omega?, Vuy_omega?, curv_x?, curv_y?, transverse_load?}` | kgf, kgf·m | kN, kN·m | |
| `joint` | `{fc_floor, beams_4_sides}` | ksc | MPa | — |
| `base_on_footing` | ตรวจ dowel 0.005Ag | | | false |
| `design` | `{db_options, rho_max}` | mm | mm | [16,20,25,28,32], 0.04 |
| `dagg` | ขนาดมวลรวมโตสุด | mm | mm | 20 |

แกนและเครื่องหมาย: `Mx` ดัดรอบแกน x (ใช้ความลึก h) คู่กับ `Vuy`; `My` ดัดรอบแกน y (ความลึก b) คู่กับ `Vux` · ใส่โมเมนต์ปลายตามเครื่องหมายจาก STAAD ได้ สคริปต์หา M1/M2 จาก |V|·L เทียบ |Mt|±|Mb| หรือระบุ `curv_x: "single"/"double"` · แรงอัด Pu เป็นบวก · `Vux_omega/Vuy_omega` = แรงเฉือนจาก combo ที่ใช้ Ω0E (ถ้ามี จะใช้ค่าน้อยกว่าตาม §18.4.3.1)

## นอกขอบเขต (บอกผู้ใช้)

SMF (§18.7), โครง sway, เสากลม/ปลอกเกลียว, หน้าตัด L/T, เหล็กต่างขนาดในหน้าตัดเดียว, คอนกรีตมวลเบา, อัดแรง, แรงบิด, แรงเฉือนในจุดต่อคาน-เสา, เสารองรับชิ้นส่วนแข็งที่ไม่ต่อเนื่อง (§18.4.3.6), การเลือก Class A/B ตามหน่วยแรงจริง (รายงานให้ทั้งสองค่า)

## ไฟล์

- `scripts/colkit/` — `section` (หน้าตัด), `pmm` (interaction แบบตัด polygon แม่นตรง), `stability`, `shear`, `detailing`, `engine` (check/design), `report`, `rcsi` (โมดูลร่วมกับสกิลคาน)
- `scripts/column.py` — CLI · `scripts/test_column.py` — เทียบค่ามือ + fiber model ที่เขียนแยก
- `kb/` — สรุป ACI 318-19 บท 6, 10, 15, 16, 18, 19, 20, 21, 22, 25 + `INDEX.md`
- `references/si-formulas.md`, `references/si-constants-318m.md`, `references/test-results.md`
- `examples/` — `S1_check_SI` (ตรวจ, SI), `IMF_design_kgfm` (ออกแบบ, IMF, kgf-m) และ `C1_design_kgfm` (ออกแบบ, ไม่ใช่ระบบแผ่นดินไหว, kgf-m) พร้อมรายงาน

## ความถูกต้อง

KB ทุกบทเทียบต้นฉบับ ACI 318-19 แล้ว · ค่าคงที่ SI ของ Ch.6, 10, 19, 20, 22, 25 เทียบเล่ม 318M-19 แล้ว · ค่า SI ใน Ch.15, 18 (200/150/450/600 mm) แปลงจาก inch-pound ยังไม่ได้เทียบเล่ม 318M
