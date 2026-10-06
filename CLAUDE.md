# CLAUDE.md — บริบทโครงการ ACI318-19 (อ่านก่อนเริ่มทุกครั้ง)

ผู้ใช้: วิศวกรโครงสร้างชาวไทย ใช้ STAAD.Pro เป็นหลัก ไม่ถนัด command line — **ตอบภาษาไทย** อธิบายเป็นขั้นตอนง่าย ๆ และรันคำสั่งให้เองเมื่อทำได้

## โครงการนี้คืออะไร

1. **Knowledge base ACI 318-19 ภาษาไทย** — `chapters/chapter-01.md` … `chapter-27.md` (สรุปรายบท, หน่วย inch-pound ตามต้นฉบับ) ดัชนีใน `README.md`
   - ทุกบทเทียบกับต้นฉบับแล้ว (Mistral OCR + ภาพหน้ากระดาษ)
   - ค่าคงที่ SI ของ Ch.6, 9, 10, 19, 20, 22, 24, 25 เทียบเล่ม ACI 318M-19 แล้ว → `audits/si-constants-check.md`
   - ยังไม่ได้เทียบ 318M: Ch.15, 18 (200/150/450/600 mm เป็นค่าแปลงหน่วย) · Ch.8 ไม่มี DDM (ค่าสัมประสิทธิ์ DDM มาจาก 318-14)
2. **สกิลออกแบบ** (อัปโหลดเป็น zip ที่ claude.ai → Settings → Capabilities → Skills)
   - `skills/rc-column-aci318m19/` — แพ็กเกจ `scripts/colkit` (เสาปลอกเดี่ยว, 3D interaction, ชะลูด, OMF/IMF, design/check)
   - `skills/rc-beam-aci318m19/` — แพ็กเกจ `scripts/beamkit` (คานทั้งช่วง ซ้าย/กลาง/ขวา ทุก combo, OMF/IMF, design/check)
   - ทั้งสองมี `kb/` (สำเนาบทที่เกี่ยวข้อง), `references/`, `examples/`, และรายงานอ้าง `kb/…` ทุกหัวข้อ
3. **โมดูลร่วม** `skills/_shared/` — แก้ที่นี่เท่านั้น แล้วรัน build
   - `rcsi.py` หน่วย/ค่าคงที่ SI/ℓd/ทาบ/รูปแบบรายงาน
   - `staadio.py` + `from_staad.py` แปลงผล STAAD → อินพุตสกิล · `staad-sign-convention.md`
   - `tests/test_staadio.py` + `tests/fixtures/CC.std` (ผล STAAD.Pro 2025 จริงของผู้ใช้)

## คำสั่งที่ใช้บ่อย

```
python3 tools/build_skills.py          # ซิงก์ _shared → ทั้งสองสกิล, รันทุก test, สร้าง dist/*.zip
python3 tools/build_skills.py --check  # ตรวจว่าไฟล์ร่วมตรงกัน
python3 skills/rc-column-aci318m19/scripts/column.py <input.json>
python3 skills/rc-beam-aci318m19/scripts/beam.py <input.json>
python3 skills/<skill>/scripts/from_staad.py model.std forces.txt --kind column|beam --member N --lc 101 102 --fc .. --fy .. -o in.json
```
Test ปัจจุบัน: staadio 38, เสา 75, คาน 55 — ต้องผ่านทั้งหมดก่อน commit · Python 3.11 ล้วน ไม่มี numpy

## ข้อเท็จจริงที่ยืนยันแล้ว (ห้ามเปลี่ยนโดยไม่มีหลักฐาน)

- หน่วย: ksc × 0.0980665 = MPa · **SD40 = 392.3 MPa (ไม่ใช่ 420)** · kgf × 9.80665 = N
- ℓd: "No.19 และเล็กกว่า" = db ≤ 19.5 mm → **DB20 ใช้ตัวหาร 1.7** · ψc ใช้เมื่อ f′c < 42 MPa (318M-19)
- ขาปลอกลดทาบ 0.83: legs_x·At ≥ 0.0015·h·s และ legs_y·At ≥ 0.0015·b·s
- ปลอกขั้นต่ำ DB10 (No.10 = 9.5 mm) — RB9 ไม่ผ่าน; โหมด design ปรับเป็น DB10 พร้อมคำเตือน
- **STAAD sign convention** (ยืนยันกับผลจริง, รายละเอียดใน `skills/_shared/staad-sign-convention.md`):
  - h = YD, b = ZD; Mz ใช้ความลึก YD · เสากลับด้าน (start บน) แกน local y = +X
  - ตาราง Section: แรงอัด + ทุกตำแหน่ง, M_design = −Mz, เครื่องหมายต่างกันสองปลาย = โค้งสองทาง
  - ตาราง End Forces: ค่าที่ end node กลับเครื่องหมายเทียบตาราง Section (กับดัก!)
  - คานต้องใช้ตาราง Section Forces · STAAD FCU = กำลังลูกบาศก์ ต้องถาม f′c ทรงกระบอก
  - ยังไม่ได้ทดสอบ: BETA ≠ 0 (สคริปต์หยุดถาม)

## กติกา

- พัฒนาและ push เฉพาะ branch `claude/pensive-ramanujan-qrseyq`; ไม่เปิด PR เว้นแต่ผู้ใช้ขอ
- ห้ามคัดลอกข้อความ ACI แบบคำต่อคำ, ห้าม commit PDF/OCR ของมาตรฐาน, ห้ามใช้สำเนาละเมิดลิขสิทธิ์
- ห้ามคำนวณในหัวแทนสคริปต์ · ห้ามเดาอินพุตที่มีผล (f′c, fy, ℓu, ระบบ, ตำแหน่งคาน) — ถาม
- รายงานต้องย้ำรายการ "ยังไม่ตรวจ" เสมอ

## งานค้าง / ทางเลือกต่อ

- ใช้ diagram จริงจากตาราง Section ในการคำนวณจุดตัดเหล็กคาน (ตอนนี้ใช้พาราโบลา 3 จุด)
- ทดสอบ BETA ≠ 0 และเสาไม่สมมาตรที่กลับด้าน (ขอผล STAAD จากผู้ใช้)
- ผู้ใช้ยังไม่ได้ให้ f′c ทรงกระบอกและเกรดเหล็กจริงของโมเดล CC.std
- เทียบ Ch.15/18 กับเล่ม 318M-19 เมื่อผู้ใช้ส่งมา
