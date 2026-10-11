# KB index — ฐานรากแผ่ (ACI 318-19)

สรุปรายบทจาก repo ACI318-19 (ภาษาไทย หน่วย inch-pound ตามต้นฉบับ — ค่า SI ดู `../references/si-formulas.md` และ `../references/si-constants-318m.md`)
ทุกบทเทียบต้นฉบับแล้ว · ค่าคงที่ SI ของ Ch.20, 22, 25 เทียบเล่ม 318M-19 แล้ว · Ch.13, 16 ยังเป็นค่าแปลงหน่วย (150 mm, 0.005Ag ไม่ขึ้นกับหน่วย)

| ขั้น | เรื่อง | ไฟล์ / ข้อ | โมดูล |
|---|---|---|---|
| 0 | ขอบเขต, แผ่นดินไหว | chapter-13.md §13.1, 13.2.3 | engine.run |
| 1 | วัสดุ, ระยะหุ้ม 75 mm, d ≥ 150 mm | chapter-20.md §20.5.1.3; chapter-13.md §13.3.1 | checks.Footing |
| 2 | ขนาดฐานจากน้ำหนักใช้งาน + qa, พลิกคว่ำ, เลื่อนไถล | chapter-13.md §13.2.6.1, 13.3.1 | pressure, engine.service_checks |
| 3 | แรงดันดินประลัย | chapter-13.md §13.2.6.3 | pressure |
| 4 | โมเมนต์ที่หน้าเสา, As,min, ระยะเหล็ก, แถบกลาง γs | chapter-13.md §13.2.7, 13.3.3; chapter-08.md §8.6.1, 8.7.2; chapter-22.md §22.2–22.3 | checks.flexure_* |
| 5 | แรงเฉือนทางเดียว (λs = 1) | chapter-22.md §22.5.5; chapter-13.md §13.2.6.2 | checks.one_way_* |
| 6 | Punching + ถ่ายโมเมนต์ | chapter-22.md §22.6; chapter-08.md §8.4.4 | checks.punching |
| 7 | แบกทานใต้เสา, เหล็กเสียบ 0.005Ag, ℓdc | chapter-22.md §22.8; chapter-16.md §16.3; chapter-25.md §25.4.9 | checks.bearing, dowel_embedment |
| 8 | ระยะฝังยึดเหล็กล่าง | chapter-13.md §13.2.8; chapter-25.md §25.4 | checks.development |
| — | พื้นทางเดียว/สองทาง (ข้อกำหนดที่ Ch.13 อ้างถึง) | chapter-07.md, chapter-08.md | — |
