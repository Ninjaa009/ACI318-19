# ผลทดสอบ colkit

รัน `python3 scripts/test_column.py` (Python 3.11, ไม่ใช้ไลบรารีภายนอก)

```
== S1 400×400 8-DB20, f′c 28, fy 420 (hand calc) ==
PASS  Ast: got 2513.2741228718346 expected 2513.2741228718346
PASS  φPn,max = 0.52Po: got 2497.954787890547 expected 2498.0
PASS  β1(28): got 0.85 expected 0.85
PASS  β1(35): got 0.7999999999999999 expected 0.8
PASS  β1(56): got 0.65 expected 0.65
PASS  Q: got 0.017066666666666667 expected 0.017067
PASS  M1/M2 single (V·L = 30 ≈ |90−60|): got -0.6666666666666666 expected -0.6666666666666666
PASS  M1/M2 double (V·L = 50 ≈ 30+20): got 0.6666666666666666 expected 0.6666666666666666
PASS  M1 = M2 = 0 → −1: got -1.0 expected -1.0
PASS  kℓu/r = 4500/(0.2887·400): got 38.97114317029974 expected 38.97
PASS  limit 34+12(−2/3) = 26: got 26.0 expected 26.0
PASS  Pc: got 6464.728930196217 expected 6464.7
PASS  Cm = 0.6+0.4·2/3: got 0.8666666666666667 expected 0.86667
PASS  δ: got 1.293524211202195 expected 1.2935
PASS  Mc: got 116.41717900819755 expected 116.42
PASS  y not slender (limit 40): got False expected False
PASS  ratio top: got 0.6002882756147649 expected 0.6
PASS  ratio mid: got 0.7501000572598583 expected 0.75
PASS  uniaxial φMnx at 1600 kN ≈ 169.5: got 1.0001189703494586 expected 1.0
PASS  c at that point ≈ 267.2: got 267.21333739647105 expected 267.2
== fiber-model cross-check ==
PASS  400×400 θ=0.0: fiber point lies on colkit surface: got 0.9963819784684164 expected 1.0
PASS  400×600 θ=0.5: fiber point lies on colkit surface: got 0.9999805700108401 expected 1.0
PASS  500×500 θ=0.785: fiber point lies on colkit surface: got 1.0025323237981858 expected 1.0
PASS  300×600 θ=1.2: fiber point lies on colkit surface: got 0.9998528952778895 expected 1.0
== symmetry / surface ==
PASS  square: swap Mx/My same ratio: got 0.3712645166558804 expected 0.3712645166558805
PASS  sign of moments ignored: got 0.3712645166558804 expected 0.3712645166558804
PASS  scaled load on surface → 1.0: got 1.0 expected 1.0
PASS  Pu > φPn,max → fail: got False expected False
PASS  φ tension-controlled: got 0.9 expected 0.9
PASS  φ transition: got 0.775 expected 0.775
== shear ==
PASS  Vc capped 0.42√28·400·340: got 302.2506297760188 expected 302.2506297760188
PASS  φVn S1: got 293.98088697190747 expected 294.0
PASS  λs(d=1000): got 0.6324555320336759 expected 0.6324555320336759
PASS  fyt capped at 420 for shear: got 420.0 expected 420.0
PASS  Av,min/s: got 0.3333333333333333 expected 0.3333333333333333
PASS  s=600 → Av < Av,min → eq (c): got '(c)' expected '(c)'
== seismic shear / IMF ==
PASS  Ve uses largest Mn over Pu: got 383020274.4757906 expected 383020274.4757906
PASS  Ve = 2Mn/ℓu: got 255346.8496505271 expected 255346.8496505271
PASS  Ve limited by Ω0 shear: got 50000.0 expected 50000.0
PASS  OMF ℓu > 5c1 → not applicable: got False expected False
PASS  OMF ℓu ≤ 5c1 → applies: got True expected True
PASS  so = min(8·16, 200, 200): got 128.0 expected 128.0
PASS  ℓo = max(500, 500, 450): got 500.0 expected 500.0
PASS  Grade 550: so = min(6·25,150,300): got 150.0 expected 150.0
PASS  ℓo = ℓu/6 when governing: got 800.0 expected 800.0
== detailing / splices ==
PASS  DB20 uses 1.7 (bigger-bar row): got 1.7 expected 1.7
PASS  ℓd DB20: got 933.7945803757378 expected 933.7945803757378
PASS  ℓsc = 0.071·420·20: got 596.4 expected 596.4
PASS  0.83 applies: 2·78.5 ≥ 0.0015·400·250: got True expected True
PASS  DB16 uses 2.1: got 2.1 expected 2.1
PASS  0.83 not applied (legs along x short for h=800): got False expected False
PASS  0.83 applied with 4 legs along x: got True expected True
PASS  Grade 550 ℓsc = (0.13fy−24)db: got 1187.5 expected 1187.5
PASS  f′c < 21 → ×4/3: got 795.1999999999999 expected 795.1999999999999
PASS  6 bars/face clear < 150 → 2 crossties each way: got True expected True
PASS  tie s,max = min(16db,48dt,b): got 320.0 expected 320.0
PASS  ρ < 1% fails: got False expected False
PASS  §15.5 0.6 ratio → required: got True expected True
PASS  §15.5 (c) 0.75·min(40,60)+0.35·24: got 38.4 expected 38.4
PASS  dowels 0.005Ag: got 800.0 expected 800.0
== engine ==
PASS  S1 worst ratio: got 0.7500839692633338 expected 0.75
PASS  S1 all pass: got True expected True
PASS  kgf-m gives same ratio: got 0.7500839692633338 expected 0.7500839692633338
PASS  kgf-m fc_floor converted: got 0.8571428571428571 expected 0.8571428571428571
PASS  kgf-m Q: got 0.017066666666666667 expected 0.017066666666666667
PASS  SMF stops: got True expected True
PASS  Q > 0.05 stops: got True expected True
PASS  design passes: got True expected True
PASS  design: all lighter tried layouts fail: got True expected True
PASS  design: chosen = last tried: got '8-DB16 (3×3)' expected '8-DB16 (3×3)'
PASS  design: impossible → stop: got True expected True
PASS  design: RB9 request bumped to DB10: got 10.0 expected 10.0
PASS  design: bump reported: got True expected True
PASS  IMF design passes: got True expected True
PASS  IMF s_end ≤ so,max: got True expected True

75 passed, 0 failed
```
