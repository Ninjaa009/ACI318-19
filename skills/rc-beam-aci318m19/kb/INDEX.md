# KB index — คาน คสล. (ACI 318-19)

สรุปรายบทจาก repo ACI318-19 (ภาษาไทย หน่วย inch-pound ตามต้นฉบับ — ค่า SI ดู `../references/si-formulas.md` และ `../references/si-constants-318m.md`)
ทุกบทเทียบต้นฉบับ ACI 318-19 แล้ว · ค่าคงที่ SI ของ Ch.9, 20, 22, 24, 25 เทียบเล่ม 318M-19 แล้ว · Ch.18 ยังเป็นค่าแปลงหน่วย

| ขั้น | เรื่อง | ไฟล์ / ข้อ | โมดูล |
|---|---|---|---|
| 0 | ขอบเขต: deep beam, แรงตามแกน, แรงบิด, ค้ำยันด้านข้าง; ระบบ OMF/IMF | chapter-09.md §9.2, 9.5, 9.9; chapter-18.md §18.2 | engine.scope |
| 1 | วัสดุ, ระยะหุ้ม, β1 | chapter-20.md §20.2, 20.5; chapter-22.md §22.2 | section |
| 2 | แรงที่ผิวจุดรองรับ, หน้าตัดวิกฤตแรงเฉือน | chapter-09.md §9.4 | engine.envelope |
| 3 | แรงดัด, φ, tension-controlled, As,min | chapter-22.md §22.2–22.3; chapter-21.md T21.2.2; chapter-09.md §9.3.3, 9.6.1 | flexure |
| 4 | แรงเฉือน, Av,min, ระยะปลอก, ยึดเหล็กอัด | chapter-22.md §22.5; chapter-09.md §9.6.3, 9.7.6 | shear |
| 5 | คานในโครง OMF / IMF | chapter-18.md §18.3.2, 18.4.2 | engine.seismic_beam |
| 6 | ระยะว่าง, คุมรอยร้าว, ความลึกขั้นต่ำ, เหล็กผิวข้าง | chapter-25.md §25.2; chapter-24.md §24.3; chapter-09.md §9.3.1, 9.7.2 | detailing |
| 7 | การตัดเหล็ก, ℓd, ℓdh, ทาบ | chapter-09.md §9.7.3; chapter-25.md §25.4, 25.5 | detailing, rcsi |
| 8 | Structural integrity | chapter-09.md §9.7.7 | engine.evaluate |
