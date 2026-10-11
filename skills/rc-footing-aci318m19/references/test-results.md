# ผลทดสอบ ftgkit

```
== soil pressure ==
PASS  inside kern: q = P/A(1 + 6e/B): got 325.0 expected 325.0
PASS  outside kern: q = 2P/(3L(B/2 − e)): got 666.6969037251893 expected 666.6666666666666
PASS  outside kern: contact = 3(B/2 − e)/B: got 0.7500000000000089 expected 0.75
PASS  e = 0.3 < B/6 stays in kern: got True expected True
PASS  biaxial in kern: P/A + My/Sy + Mx/Sx: got 243.33333333333331 expected 243.33333333333331
PASS  biaxial partial contact: ΣqA = P: got 1000.0003430489742 expected 1000
PASS  biaxial partial contact: Σq·x·A = My: got 250.00610658286132 expected 250
PASS  resultant outside footing → unstable: got False expected False
== strength (uniform pressure, hand calc) ==
PASS  Mu face = q·L·c²/2: got 160000000.00000077 expected 160000000.0
PASS  one-way Vu = q·L·(c − d): got 191500.0 expected 191500.0
PASS  punching Vu = Pu − q(c+d)²: got 836379.75 expected 836379.75
PASS  punching vc = 0.33√f′c (β = 1): got 1.6500000000000001 expected 1.6500000000000001
PASS  β = 2 → vc = 0.17(1 + 2/2)√f′c = 0.34 → 0.33 governs: got 1.6500000000000001 expected 1.6500000000000001
PASS  β = 3 → 0.17(1 + 2/3)√f′c: got 1.4166666666666665 expected 1.4166666666666665
PASS  γv square = 1 − 1/(1 + 2/3) = 0.4: got 0.3999999999999999 expected 0.4
PASS  moment term γv·M·c/Jc: got 0.05267090447692986 expected 0.05267090447692987
PASS  Vc (c) = 0.66ρ^⅓√f′c·bd (λs = 1): got 421694.9419560612 expected 421694.9419560612
PASS  As_req gives φMn = Mu: got 300000000.0 expected 300000000.0
PASS  As,min = 0.0018bh: got 1800.0 expected 1800.0
PASS  As provided: n·Ab (s = 150): got 2613.805087786708 expected 2613.805087786708
PASS  √(A2/A1) limited by footing size = 800/400 = 2: got 2.0 expected 2.0
PASS  √(A2/A1) = 600/400: got 1.5 expected 1.5
PASS  φBn column = 0.65·0.85·30·A1: got 2652000.0 expected 2652000.0
PASS  Pu > φBn → extra dowels: got True expected True
PASS  band factor β = 2 → 4/3: got 1.3333333333333333 expected 1.3333333333333333
PASS  long direction no band: got 1.0 expected 1.0
PASS  ℓd DB16 (clear ≥ 2db) = fy/(2.1√f′c)·db: got 597.7904761904762 expected 597.7904761904762
== engine ==
PASS  F1 design passes: got True expected True
PASS  service total load = P + footing + soil above: got 1069704.478675 expected 1069704.478675
PASS  F1 qmax (hand, in kern): got 0.14376989580486302 expected 0.14376989580486302
PASS  design is minimal: 50 mm smaller fails soil: got False expected False
PASS  check mode h = 0.30 → shear fails: got False expected False
PASS  SI input gives the same footing: got (2850.0, 2850.0, 500.0, 200.0) expected (2850.0, 2850.0, 500.0, 200.0)
PASS  large moment → partial contact handled: got True expected True
PASS  large moment design still passes: got True expected True
PASS  SDC D stops: got True expected True
PASS  missing service combos stops: got True expected True

37 passed, 0 failed
```
