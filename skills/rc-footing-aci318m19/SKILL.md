---
name: rc-footing-aci318m19
description: ออกแบบ (เลือกขนาดฐาน ความหนา และเหล็กล่างให้อัตโนมัติ) และตรวจสอบฐานรากแผ่เดี่ยว (isolated spread footing) วางบนดิน ตาม ACI 318M-19 โดยใช้ knowledge base ของโครงการใน kb/ เป็นแหล่งอ้างอิงหลัก ขนาดฐานจากน้ำหนักใช้งาน + กำลังรับน้ำหนักดินที่ยอมให้ (qa) พร้อมโมเมนต์สองแกน แรงดันดินกรณีฐานยกบางส่วน พลิกคว่ำ เลื่อนไถล แล้วตรวจกำลังด้วยน้ำหนักประลัย: โมเมนต์ที่หน้าเสา, As,min, แถบกลาง γs, แรงเฉือนทางเดียว (Vc ตาม 318-19), punching พร้อมถ่ายโมเมนต์, แรงแบกทานใต้เสา, เหล็กเสียบ 0.005Ag, ℓdc และระยะฝังยึดเหล็กล่าง อินพุต kgf-m (ksc, t/m²) หรือ SI และรับผล STAAD ได้โดยตรง ใช้เมื่อผู้ใช้พูดถึง "ออกแบบฐานราก", "ตรวจฐานราก", "footing", "ฐานแผ่", "spread footing", "แรงแบกทานดิน", "qa", "punching ฐานราก", "เหล็กฐานราก", "ฐานราก STAAD" ไม่ใช่สำหรับฐานรากบนเสาเข็ม (pile cap), ฐานรากร่วม, mat หรือฐานรากใน SDC D–F
---

# ฐานรากแผ่ ACI 318M-19 — ftgkit

ผลลัพธ์ใช้ประกอบรายการคำนวณ วิศวกรผู้รับผิดชอบต้องตรวจและลงนามเอง

## กฎ

1. **KB มาก่อน** — คำถามข้อกำหนดให้เปิด `kb/INDEX.md` แล้วอ่านไฟล์บทที่เกี่ยวข้อง ตอบพร้อม § และชื่อไฟล์ ถ้า KB ไม่มีให้บอกว่าไม่มี
2. **ค่า SI** — `references/si-formulas.md`, `references/si-constants-318m.md`
3. **ตัวเลขทุกตัวมาจาก `scripts/footing.py`** — ห้ามคำนวณเองในหัว
4. **ห้ามเดาอินพุต** ที่มีผล: qa และชนิด (gross/net), Df, f′c ทรงกระบอก, fy, ขนาดเสา, **แรงใช้งาน (service) และแรงประลัย (ultimate) แยกกัน** → ถาม ค่าที่มี default ใช้ได้แต่ต้องแจ้งผู้ใช้
5. **หน่วยไทย:** ksc × 0.0980665 = MPa — SD40 = 392.3 MPa · qa ใน kgf-m ใส่เป็น **t/m²** · γ ใส่เป็น t/m³
6. ห้ามสรุป "ผ่านทั้งหมด" ถ้ารายงานยังมีหัวข้อ "ยังไม่ตรวจ"
7. รัน `python3 scripts/test_footing.py` ครั้งแรกในเซสชัน ต้องผ่านทั้งหมด

## Workflow

| ขั้น | งาน | KB |
|---|---|---|
| 0 | ขอบเขต: SDC D–F → **หยุด**, SDC C → เตือน §18.13 | chapter-13 §13.2.3 |
| 1 | วัสดุ ระยะหุ้ม 75 mm, d ≥ 150 mm | chapter-20, chapter-13 |
| 2 | ขนาดฐาน: แรงใช้งาน + น้ำหนักฐานและดินถม, qmax ≤ qa, พลิกคว่ำ, เลื่อนไถล | chapter-13 §13.2.6.1 |
| 3 | แรงดันดินประลัย (net) | chapter-13 §13.2.6.3 |
| 4 | โมเมนต์ที่หน้าเสา → เหล็กล่างสองทิศ, As,min, ระยะ, แถบกลาง | chapter-13, 08, 22 |
| 5 | แรงเฉือนทางเดียวที่ d | chapter-22 §22.5 |
| 6 | Punching ที่ d/2 + ถ่ายโมเมนต์ | chapter-22 §22.6, chapter-08 §8.4.4 |
| 7 | แบกทานใต้เสา, เหล็กเสียบ, ℓdc | chapter-22 §22.8, chapter-16, 25 |
| 8 | ระยะฝังยึดเหล็กล่าง (ตรง หรือ ขอ) | chapter-13 §13.2.8, chapter-25 |
| 9 | สรุป + รายการยังไม่ตรวจ | — |

ขั้นตอน: รวบรวมอินพุต → เขียน JSON (แบบใน `examples/`) → `python3 scripts/footing.py input.json` (exit 0 = ผ่าน) → ส่งรายงานทั้งฉบับและสรุปสั้น ๆ

## อินพุตจาก STAAD.Pro (แนะนำ)

ใช้แรงที่**โคนเสา**ที่ตั้งบนฐาน (ตาราง Beam End Forces หรือ Section Forces ของเสาต้นนั้น, หน่วย kN–m) — **ห้ามแปลงเครื่องหมายเอง**:

```
python3 scripts/from_staad.py model.std forces.txt --kind footing --member <เลขเสา> \
        --lc <combo ประลัย ...> --lc-service <combo ใช้งาน ...> \
        --fc <f′c ทรงกระบอก> --fy <MPa> --qa <kPa> --Df <m> [--qa-type net] [--mu 0.4] [--col-db 20] -o input.json
python3 scripts/footing.py input.json
```

- แกนผัง x = X, y = Z ของ STAAD · cx = YD, cy = ZD ของเสา · ใช้ค่าที่ปลายล่างของเสาแม้ start อยู่บน
- **ต้องมี combo ใช้งาน** (เช่น D+L) สำหรับขนาดฐาน — ถ้าโมเดลไม่มี ให้ผู้ใช้เพิ่มใน STAAD
- qa ใน STAAD flow ใส่เป็น kPa (1 t/m² = 9.81 kPa) · f′c ต้องถาม (STAAD เก็บ FCU กำลังลูกบาศก์)
- สคริปต์หยุดเมื่อเจอ BETA ≠ 0 หรือเสาไม่ใช่ PRIS

## โหมด

- `"mode": "design"` — ขนาดฐานเพิ่มทีละ 50 mm (สี่เหลี่ยมจัตุรัส หรือ `design.ratio` = L/B, หรือกำหนด `design.B`/`design.L`), ความหนาเริ่มที่ `design.h_min` เพิ่มทีละ 50 mm จนผ่านเฉือนทางเดียว punching และ ℓdc, เลือกเหล็กจาก `design.db_options` ให้ As น้อยสุด ระยะ 100 mm – min(2h, 450) ปัดลงทีละ 25 mm
- `"mode": "check"` — ตรวจตาม `footing` และ `bars`

## อินพุต JSON

| key | ความหมาย | kgf-m | SI | default |
|---|---|---|---|---|
| `mode`, `units` | `design`/`check`, `kgf-m`/`SI` | | | design, kgf-m |
| `column` | `{cx, cy, db}` — cx ตามแกน x (ด้าน B), db = เหล็กยืนเสา (ตรวจ ℓdc) | m | mm | **cx, cy ต้องให้** |
| `materials` | `{fc, fy, fc_column}` | ksc | MPa | fc_column = fc |
| `soil` | `{qa, qa_type, Df, gamma, mu}` — Df = ความลึกท้องฐานจากผิวดิน | t/m², m, t/m³ | kPa, m, kN/m³ | qa_type gross, γ 1.8 / 18, ไม่มี μ = ไม่ตรวจเลื่อน |
| `service[]` | `{name, P, Mx, My, Hx, Hy}` — แรงใช้งานที่โคนเสา | kgf, kgf·m | kN, kN·m | **ต้องให้** |
| `ultimate[]` | `{name, Pu, Mux, Muy, Hux, Huy}` | kgf, kgf·m | kN, kN·m | **ต้องให้** |
| `footing` (check) | `{B, L, h}` | m | mm | |
| `bars` (check) | `{x: {db, s}, y: {db, s}}` — เหล็ก x วางขนานด้าน B | mm | mm | |
| `design` | `{ratio, B, L, h_min, db_options}` | m | mm | 1.0, –, –, 300 mm, [12,16,20,25] |
| `cover`, `gamma_c` | ระยะหุ้ม, หน่วยน้ำหนักคอนกรีต | mm, t/m³ | mm, kN/m³ | 75, 2.4 / 23.6 |
| `FS_overturning`, `FS_sliding`, `require_full_contact`, `alpha_s`, `sdc` | | | | 1.5, 1.5, false, 40, – |

แกน: **My** = โมเมนต์รอบแกน y → แรงดันแปรตามแนว x (ด้าน B) · **Mx** → แปรตามแนว y (ด้าน L) · ใส่ค่าโมเมนต์ได้ทั้งบวก/ลบ (ใช้ค่าสัมบูรณ์ เพราะฐานสมมาตร)

## นอกขอบเขต (บอกผู้ใช้)

ฐานรากบนเสาเข็ม (pile cap), ฐานรากร่วม/ฐานแถบ/mat, เสาเยื้องศูนย์, ฐานลาดหรือขั้นบันได, เหล็กเฉือนในฐาน, เหล็กบน, การทรุดตัว, แรงยกจากน้ำใต้ดิน, ฐานรากใน SDC C–F (§18.13), คานยึดฐาน

## ไฟล์

- `scripts/ftgkit/` — `pressure` (แรงดันดิน ไม่มีแรงดึง), `checks` (กำลัง), `engine` (check/design), `report`, `rcsi` + `staadio` (โมดูลร่วม)
- `scripts/footing.py` — CLI · `scripts/from_staad.py` — แปลงผล STAAD · `scripts/test_footing.py` — เทียบสูตรปิดและค่ามือ
- `kb/` — สรุป ACI 318-19 บท 7, 8, 13, 16, 20, 21, 22, 25 + `INDEX.md`
- `references/si-formulas.md`, `references/si-constants-318m.md`, `references/staad-sign-convention.md`, `references/test-results.md`
- `examples/` — `F1_design_kgfm` (ออกแบบ kgf-m), `F2_staad_col1` (จากผล STAAD โมเดล CC เสา 1) พร้อมรายงาน

## ความถูกต้อง

KB ทุกบทเทียบต้นฉบับแล้ว · ค่าคงที่ SI ของ Ch.20, 22, 25 เทียบเล่ม 318M-19 แล้ว · d ≥ 150 mm (Ch.13) เป็นค่าแปลงหน่วย
