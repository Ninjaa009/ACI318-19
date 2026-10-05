# ผลทดสอบ column.py

รันด้วย `python3 scripts/test_column.py` — วันที่ 2026-10-05

C8 = ตัวอย่างมือเสาชะลูด S1 (400×400, 8-DB20, Pu 1,600 kN) · K = สูตรปิดอิสระ · N = เคสใหม่ (fyt ≤ 420, ทาบ, crosstie, kgf-m, หยุดนอกขอบเขต)

| # | การทดสอบ | ได้ | คาดหมาย | ผล |
|---|---|---|---|---|
| 1 | C8 Ast (mm²) | 2,513 | 2,513 | ✅ |
| 2 | C8 Q | 0.01707 | 0.01707 | ✅ |
| 3 | C8 φPn,max (kN) | 2,498 | 2,498 | ✅ |
| 4 | C8 M1/M2 x (single, from V·L) | -0.6667 | -0.6667 | ✅ |
| 5 | C8 M1/M2 y (double, from V·L) | 0.6667 | 0.6667 | ✅ |
| 6 | C8 klu/r | 38.97 | 38.97 | ✅ |
| 7 | C8 x slender, y not | True | True | ✅ |
| 8 | C8 Pc (kN) | 6,465 | 6,465 | ✅ |
| 9 | C8 δ | 1.294 | 1.294 | ✅ |
| 10 | C8 Mcx (kN·m) | 116.4 | 116.4 | ✅ |
| 11 | C8 φMnx uniaxial at Pu (kN·m) | 169.5 | 169.5 | ✅ |
| 12 | C8 c at Pu (mm) | 267.2 | 267.2 | ✅ |
| 13 | C8 ratio top end | 0.6003 | 0.6 | ✅ |
| 14 | C8 ratio midheight | 0.7501 | 0.75 | ✅ |
| 15 | C8 ratio x only | 0.6869 | 0.687 | ✅ |
| 16 | C8 Vc limited to Vc,max (kN) | 302.3 | 302.3 | ✅ |
| 17 | C8 Vc capped flag | True | True | ✅ |
| 18 | C8 φVn (kN) | 294 | 294 | ✅ |
| 19 | C8 detailing all pass | True | True | ✅ |
| 20 | K1 hand φPn = Pu (kN) | 1,600 | 1,600 | ✅ |
| 21 | K1 hand φMn (kN·m) | 169.5 | 169.5 | ✅ |
| 22 | K2 Pn at c→∞ = Po (kN) | 4,804 | 4,804 | ✅ |
| 23 | K2 symmetric φMcap(α) = φMcap(90°−α) | 1.64e+08 | 1.64e+08 | ✅ |
| 24 | K2 capacity direction = load direction (°) | 26.57 | 26.57 | ✅ |
| 25 | K2 point on surface ratio = 1 | 1 | 1 | ✅ |
| 26 | K2 Pu > φPn,max flagged | True | True | ✅ |
| 27 | K3 M1=M2=0 → limit 22 | 22 | 22 | ✅ |
| 28 | K3 double curvature limit capped 40 | 40 | 40 | ✅ |
| 29 | K3 M2,min = Pu(15+0.03h) (kN·m) | 43.2 | 43.2 | ✅ |
| 30 | K3 Cm = 1.0 when M2,min governs | 1 | 1 | ✅ |
| 31 | K3 Pu ≥ 0.75Pc → unstable | True | True | ✅ |
| 32 | N1 fyt used = 420 | 420 | 420 | ✅ |
| 33 | N1 Vs uses 420 | 1.495e+05 | 1.495e+05 | ✅ |
| 34 | N2 Nu tension term (MPa) | -0.3125 | -0.3125 | ✅ |
| 35 | N2 need Av,min and s > d/2 fails | True | True | ✅ |
| 36 | N2 biaxial sum 1.55 > 1.5 fails | True | True | ✅ |
| 37 | N3 ρg 4-DB12 in 300×300 | 0.005027 | 0.005027 | ✅ |
| 38 | N3 ρg < 1% fails | True | True | ✅ |
| 39 | N3 s_tie,max = 16db | 192 | 192 | ✅ |
| 40 | N3 600 col, 5/side, no crossties → fail | True | True | ✅ |
| 41 | N3 1 crosstie each way (clear ≤ 150, alternate) → pass | True | True | ✅ |
| 42 | N4 compression lap SD40 DB20 | 596.4 | 596.4 | ✅ |
| 43 | N4 0.83 factor applies (Ast_tie ≥ 0.0015hs) | True | True | ✅ |
| 44 | N4 ℓd DB20 (ψg 1.0, 2.1) | 755.9 | 755.9 | ✅ |
| 45 | N4 Class B = 1.3ℓd | 982.7 | 982.7 | ✅ |
| 46 | N4 SD50 compression lap (0.13fy−24)db | 993.5 | 993.5 | ✅ |
| 47 | N4 SD50 ψg 1.15 | 1.15 | 1.15 | ✅ |
| 48 | N5 kgf-m Q | 0.01707 | 0.01707 | ✅ |
| 49 | N5 kgf-m ratio midheight | 0.7501 | 0.75 | ✅ |
| 50 | N5 report renders | True | True | ✅ |
| 51 | N6 Q > 0.05 stops | True | True | ✅ |
| 52 | N6 SMF stops | True | True | ✅ |
| 53 | N7 Mn(no φ) > φMn at same P | True | True | ✅ |

53/53 passed
