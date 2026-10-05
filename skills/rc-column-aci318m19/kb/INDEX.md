# KB index — เสา คสล. (ACI 318-19)

สรุปรายบทจาก repo ACI318-19 (ภาษาไทย หน่วย inch-pound ตามต้นฉบับ — ค่า SI ดู `../references/si-constants-318m.md` และ `../references/si-formulas.md`)
ทุกบทเทียบกับต้นฉบับ ACI 318-19 แล้ว · ค่าคงที่ SI ของ Ch.6, 10, 19, 20, 22, 25 เทียบกับเล่ม 318M-19 แล้ว · Ch.15, 18 ยังเป็นค่าแปลงหน่วย

| ขั้น | เรื่อง | ไฟล์ / ข้อ | โมดูล |
|---|---|---|---|
| 0 | ระบบต้านแผ่นดินไหว OMF / IMF / SMF | chapter-18.md §18.2, 18.3, 18.4 | engine.run |
| 1 | วัสดุ, β1, fy ≤ 550, fyt ≤ 420 | chapter-10.md §10.3; chapter-20.md §20.2; chapter-22.md §22.2 | section |
| 2 | ชุดผสมน้ำหนัก | (Ch.5 ไม่รวมในสกิล — ใช้ผลจาก STAAD) | — |
| 3 | Sway / non-sway (Q) | chapter-06.md §6.6.4.3 | stability |
| 4 | ความชะลูด, EIeff, δ, M2,min | chapter-06.md §6.2.5, 6.6.4.4–6.6.4.5; chapter-19.md §19.2.2 | stability |
| 5 | φPn,max, ดัดสองแกน, φ | chapter-22.md §22.2, 22.4; chapter-21.md Table 21.2.2 | pmm |
| 6 | แรงเฉือน, Nu, สองแกน, Ve แผ่นดินไหว | chapter-22.md §22.5; chapter-10.md §10.6.2, 10.7.6.5; chapter-18.md §18.3.3, 18.4.3 | shear |
| 7 | ρg, ระยะว่าง, ปลอก, crosstie, so/ℓo | chapter-10.md §10.6.1, 10.7; chapter-25.md §25.2, 25.7.2; chapter-18.md §18.4.3 | detailing |
| 8 | ต่อทาบ | chapter-10.md §10.7.5; chapter-25.md §25.4, 25.5 | detailing.splices |
| 9 | ปลอกในจุดต่อ, คอนกรีตพื้น, dowel | chapter-15.md §15.3.1, 15.5; chapter-16.md §16.3.4; chapter-18.md §18.4.4 | detailing |
