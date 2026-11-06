# KB index — พื้นบนคาน ทางเดียว / สองทาง (ACI 318-19)

สรุปรายบทจาก repo ACI318-19 (ภาษาไทย หน่วย inch-pound ตามต้นฉบับ — ค่า SI ดู `../references/si-formulas.md` และ `../references/si-constants-318m.md`)
ทุกบทเทียบต้นฉบับแล้ว · ค่าคงที่ SI ของ Ch.6, 19, 20, 22, 24, 25 เทียบเล่ม 318M-19 แล้ว
ตารางสัมประสิทธิ์ Method 2 **ไม่ได้อยู่ใน ACI 318-19** → `../references/method2-coefficients.md`

| ขั้น | เรื่อง | ไฟล์ / ข้อ | โมดูล |
|---|---|---|---|
| 0 | ขอบเขต, วิธีวิเคราะห์ที่ยอมให้ | chapter-08.md §8.2.1; chapter-06.md §6.5 | engine.run |
| 1 | ชุดผสมน้ำหนัก, วัสดุ, ระยะหุ้ม 20 mm | chapter-05.md §5.3.1; chapter-19.md; chapter-20.md §20.5.1.3 | engine.to_si |
| 2 | แบ่งแผง ต่อเนื่อง/ไม่ต่อเนื่อง, m = S/L, ทางเดียว/สองทาง | chapter-08.md §8.4.1 (นิยามแผง) | engine.panels, panel_moments |
| 3 | ความหนาขั้นต่ำ, αf ของคาน, คานขอบ +10% | chapter-08.md §8.3.1.2, §8.4.1 (นิยามคาน); chapter-07.md §7.3.1.1 | strip.h_min_*, engine.alpha_edges |
| 4 | โมเมนต์: สองทาง Method 2 · ทางเดียว Table 6.5.2 | ../references/method2-coefficients.md; chapter-06.md §6.5 | coeffs |
| 5 | แรงดัดต่อเมตร, As,min 0.0018bh, ระยะเหล็ก 2h/3h/5h | chapter-22.md §22.2–22.3; chapter-21.md §21.2; chapter-08.md §8.6.1, §8.7.2; chapter-07.md §7.6.1, §7.7.2; chapter-24.md §24.4.3 | strip.flexure, choose |
| 6 | แรงเฉือน (λs ใช้กับพื้น), 1.15 ที่จุดรองรับในตัวแรก | chapter-22.md §22.5.5.1; chapter-06.md Table 6.5.4 | strip.shear |
| 7 | คุมรอยร้าวพื้นทางเดียว | chapter-24.md §24.3.2 | strip.crack_smax |
| 8 | เหล็กมุม (αf > 1.0) | chapter-08.md §8.7.3 | engine.evaluate |
| 9 | ระยะฝัง/ยื่นเหล็ก | chapter-08.md §8.7.4.1; chapter-25.md §25.4.2 | report |
