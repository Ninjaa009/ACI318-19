# ผลทดสอบ beam.py

รันด้วย `python3 scripts/test_beam.py` — วันที่ 2026-10-04

| # | การทดสอบ | ได้ | คาดหมาย | ผล |
|---|---|---|---|---|
| 1 | T1 As,req singly (mm²) | 1,327 | 1,327 | ✅ |
| 2 | T1 bars | 3 | 3 | ✅ |
| 3 | T1 φMn (N·mm) | 2.751e+08 | 2.751e+08 | ✅ |
| 4 | T1 εt | 0.01282 | 0.01282 | ✅ |
| 5 | T2 doubly found | True | True | ✅ |
| 6 | T2 φMn ≥ Mu | True | True | ✅ |
| 7 | T2 strain ok | True | True | ✅ |
| 8 | T2 φMn regression (kN·m) | 346.9 | 346.9 | ✅ |
| 9 | T3 c (mm) | 178.6 | 178.6 | ✅ |
| 10 | T3 εt | 0.006031 | 0.00603 | ✅ |
| 11 | T3 φMn (kN·m) | 497.8 | 497.8 | ✅ |
| 12 | T3 d ≠ dt | True | True | ✅ |
| 13 | E2 strain limit fails | True | True | ✅ |
| 14 | E5 Vc eq.(a) (N) | 1.451e+05 | 1.451e+05 | ✅ |
| 15 | E5 s (mm) | 250 | 250 | ✅ |
| 16 | E5 φVn (N) | 2.152e+05 | 2.152e+05 | ✅ |
| 17 | E5 s=700 → eq.(c) | 1.182e+05 | 1.182e+05 | ✅ |
| 18 | E5 s=700 Av<Av,min flagged | True | True | ✅ |
| 19 | N1 fyt used = 420 | 420 | 420 | ✅ |
| 20 | N1 Vs uses 420 | 1.773e+05 | 1.773e+05 | ✅ |
| 21 | N2 leg spacing (mm) | 710 | 710 | ✅ |
| 22 | N2 2 legs fail across 800 mm | True | True | ✅ |
| 23 | N2 4 legs pass | True | True | ✅ |
| 24 | N3 h ≤ 250 exempt, no stirrups | True | True | ✅ |
| 25 | N4 ℓd DB25 SD40 bottom | 1,167 | 1,167 | ✅ |
| 26 | N4 ℓd DB25 SD50 ψg=1.15 | 1,567 | 1,567 | ✅ |
| 27 | N4 ℓd DB16 top other | 1,179 | 1,179 | ✅ |
| 28 | N4 ℓdh DB25 | 747.7 | 747.7 | ✅ |
| 29 | N4 compression lap DB25 SD40 | 745.5 | 745.5 | ✅ |
| 30 | N5 min depth simple 6 m SD40 | 375 | 375 | ✅ |
| 31 | N5 min depth SD50 | 412.7 | 412.7 | ✅ |
| 32 | N5 crack s,max cc=50 | 255 | 255 | ✅ |
| 33 | N6 kgf-m φMn = SI φMn | 2.751e+08 | 2.751e+08 | ✅ |
| 34 | N6 kgf-m stirrup s | 250 | 250 | ✅ |
| 35 | N6 report renders | True | True | ✅ |
| 36 | N7 deep beam stops | True | True | ✅ |
| 37 | N8 Mu<0 → tension top | True | True | ✅ |
| 38 | N8 top bar ψt = 1.3 | 1.3 | 1.3 | ✅ |

38/38 passed
