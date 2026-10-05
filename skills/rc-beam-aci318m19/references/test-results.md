# ผลทดสอบ beamkit

รัน `python3 scripts/test_beam.py` (Python 3.11, ไม่ใช้ไลบรารีภายนอก)

```
== flexure: hand calc (singly) ==
PASS  d: got 540.0 expected 540
PASS  φMn = 0.9As·fy(d − a/2): got 238948472.4456558 expected 238948472.4456558
PASS  c = a/β1: got 86.96450252151678 expected 86.96450252151675
PASS  As,min = max(0.25√fc,1.4)bd/fy: got 539.9999999999999 expected 539.9999999999999
PASS  As,min fy capped 550: got 381.81818181818176 expected 381.81818181818176
== flexure: strip model (doubly, two layers) ==
PASS  Mn [[4, 25], [2, 25]] vs [[3, 25]] f′c28: got 571898079.139177 expected 571702601.5821643
PASS  c  [[4, 25], [2, 25]] vs [[3, 25]] f′c28: got 132.6210156629557 expected 132.58823529411762
PASS  Mn [[3, 16]] vs [[5, 20], [2, 20]] f′c35: got 148951525.85749424 expected 148937777.51955238
PASS  c  [[3, 16]] vs [[5, 20], [2, 20]] f′c35: got 63.319011211622694 expected 63.339568024678144
PASS  Mn [[2, 12]] vs [[6, 25], [3, 25]] f′c24: got 82868843.5711689 expected 82907692.75401792
PASS  c  [[2, 12]] vs [[6, 25], [3, 25]] f′c24: got 71.65782182690918 expected 71.64705882352942
PASS  over-reinforced → εt < εty + 0.003 → fail: got False expected False
PASS  no demand → ok regardless: got True expected True
== shear ==
PASS  Vc (a) = 0.17√fc·b·d: got 140600.5161725945 expected 140600.5161725945
PASS  Vs = Av·fyt·d/s: got 229147.7681528395 expected 229147.7681528395
PASS  s,max = d/2: got 260.5 expected 260.5
PASS  trigger = φ0.083√fc·bw·d: got 51484.60077496475 expected 51484.60077496475
PASS  Av < Av,min → Vc (c) with λs: got '(c)' expected '(c)'
PASS  Vc (c) value: got 93944.63852627361 expected 93944.63852627361
PASS  fyt capped at 420: got 420.0 expected 420.0
PASS  Vs > 0.33√fc·bw·d → s,max = min(d/4, 300): got 135.0 expected 135.0
PASS  §22.5.1.2 limit: got 533621.5819286173 expected 533621.5819286173
PASS  leg spacing 610 > d → fails transverse limit: got False expected False
== detailing / development ==
PASS  crack s,max (fs = 2fy/3, cc 50): got 281.83150650012743 expected 281.8315065001275
PASS  h,min both ends fy 420 = ℓn/21: got 285.7142857142857 expected 285.7142857142857
PASS  h,min × (0.4 + fy/700): got 274.40816326530614 expected 274.40816326530614
PASS  ℓd DB16 (2.1): got 570.3858322704059 expected 570.3858322704059
PASS  ℓd DB20 (1.7, larger bar): got 1.7 expected 1.7
PASS  ℓd top bar ψt 1.3: got 1517.4161931105739 expected 1517.4161931105739
PASS  ℓd poor spacing → 1.1: got 1.1 expected 1.1
PASS  ψc f′c < 42: got 0.8666666666666667 expected 0.8666666666666667
PASS  lap compression fy 420: got 745.4999999999999 expected 745.4999999999999
PASS  IMF hoop s = min(d/4, 8db, 24dt, 300): got 128 expected 128.0
PASS  bars per layer DB25 b300: got 4 expected 4
PASS  split 6-DB25 → 4 + 2: got [[4, 25], [2, 25]] expected [[4, 25], [2, 25]]
PASS  inflection point UDL fixed-fixed: got 1267.9491924311035 expected 1267.92
== engine ==
PASS  B1 design passes: got True expected True
PASS  B1 bottom is minimal (n−1 fails): got False expected False
PASS  B1 left top is minimal (n−1 fails): got False expected False
PASS  kgf-m and SI give same bars: got True expected True
PASS  kgf-m and SI same φMn: got 182294280.5055256 expected 182294280.5055256
PASS  B2 check passes: got True expected True
PASS  B2 left top φMn: got 514.7082712252593 expected 514.7
PASS  deep beam stops: got True expected True
PASS  SMF stops: got True expected True
PASS  check mode: RB9 flagged (§9.7.6.4): got False expected False
PASS  design mode: RB9 bumped to DB10: got 10.0 expected 10.0
PASS  impossible design stops: got True expected True
== IMF ==
PASS  IMF design passes: got True expected True
PASS  IMF Ve = (Mnl + Mnr)/ℓn + wuℓn/2: got 192907.32288463297 expected 192907.32288463297
PASS  IMF Mn+ ≥ Mn−/3 at faces: got True expected True
PASS  IMF end hoops ≤ 8db: got True expected True
PASS  IMF end zone ≥ 2h: got True expected True
PASS  IMF raises bottom bars for Mn+ ≥ Mn−/3: got True expected True
PASS  perimeter: continuous top ≥ max(2, ⅙): got True expected True

55 passed, 0 failed
```
