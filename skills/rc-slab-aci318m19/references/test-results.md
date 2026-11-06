# ผลทดสอบ slabkit

```
== Method 2 coefficients ==
PASS  case 1, m = 1: short = long (0.033 / 0.025): got (0.033, 0.025) expected (0.033, 0.025)
PASS  case 1, m = 0.95 interpolates (0.033+0.040)/2: got 0.036500000000000005 expected 0.0365
PASS  case 4, m = 0.75: positive (0.056+0.062)/2: got 0.059 expected 0.059
PASS  m < 0.5 clamps to the 0.5 column: got 0.085 expected 0.085
PASS  long span constant with m: got (0.049, 0.025, 0.037) expected (0.049, 0.025, 0.037)
PASS  table self-consistency: pos ≈ 0.75 neg-cont, neg-disc ≈ 2/3 pos (all cells): got 0 expected 0
PASS  m = 1 → both beams wS/3: got (0.3333333333333333, 0.3333333333333333) expected (0.3333333333333333, 0.3333333333333333)
PASS  m = 0.5 → long beam wS/3·(3 − 0.25)/2: got 0.4583333333333333 expected 0.4583333333333333
== Table 6.5.2 (one-way) ==
PASS  interior span 1/11, 1/11, 1/16: got (0.09090909090909091, 0.09090909090909091, 0.0625) expected (0.09090909090909091, 0.09090909090909091, 0.0625)
PASS  end span, two spans: first interior 1/9: got (0.1111111111111111, 0.041666666666666664, 0.07142857142857142) expected (0.1111111111111111, 0.041666666666666664, 0.07142857142857142)
PASS  end span, > two spans: first interior 1/10: got (0.041666666666666664, 0.1, 0.07142857142857142) expected (0.041666666666666664, 0.1, 0.07142857142857142)
PASS  span ≤ 3.05 m: 1/12 at all supports: got (0.08333333333333333, 0.08333333333333333, 0.07142857142857142) expected (0.08333333333333333, 0.08333333333333333, 0.07142857142857142)
PASS  single span: wℓ²/8: got 0.125 expected 0.125
== strip (b = 1 m) ==
PASS  As_req reproduces Mu at φ = 0.9: got 10000000.000000002 expected 10000000.0
PASS  too thin → None: got None expected None
PASS  As = 78.54·1000/200: got 392.69908169872417 expected 392.69908169872417
PASS  As,min = 0.0018·1000·100: got 180.0 expected 180.0
PASS  choose: spacing is a multiple of 25 and ≤ 2h: got (True, True) expected (True, True)
PASS  choose: As ≥ As_req: got True expected True
PASS  φVc = 0.75·0.66λs ρ^⅓ √f′c bd: got 31589.96748126381 expected 31589.96748126381
PASS  λs = 1 for d = 75 mm: got 1.0 expected 1.0
PASS  T8.3.1.2 αfm > 2: ℓn(0.8 + fy/1400)/(36 + 9β): got 99.37036178107607 expected 99.37036178107607
PASS  T8.3.1.2 αfm > 2: ≥ 90 mm: got 90.0 expected 90.0
PASS  T8.3.1.2 0.2 < αfm ≤ 2: ≥ 125 mm: got 125.0 expected 125.0
PASS  T8.3.1.2 αfm ≤ 0.2 → out of scope: got None expected None
PASS  T7.3.1.1 one end continuous: ℓ/24·(0.4 + fy/700): got 160.07142857142858 expected 160.07142857142858
PASS  T7.3.1.1 fy = 420 → no modifier: got 142.85714285714286 expected 142.85714285714286
PASS  T24.3.2 fs = 2/3 fy, cc = 20: got 321.18276828957426 expected 321.18276828957426
PASS  T-beam I with no flange = bh³/12: got 2604166666.6666665 expected 2604166666.6666665
PASS  flange overhang capped at 4h: got True expected True
== floor example (kgf-m) ==
PASS  S1 design passes: got True expected True
PASS  S1 h = 100 mm: got 100.0 expected 100.0
PASS  panel names: got ('AB-12', 'BC-34') expected ('AB-12', 'BC-34')
PASS  corner panel AB-12: case 3: got 3 expected 3
PASS  edge panel AB-23: case 2: got 2 expected 2
PASS  corridor BC-12: one-way (m < 0.5): got 'one-way' expected 'one-way'
PASS  wu = max(1.4D, 1.2D + 1.6L): got 0.009296704199999999 expected 0.009296704199999999
PASS  AB-12 short positive Mu = C·wu·S²·1 m: got 6326867.342729223 expected 6326867.342729223
PASS  shared edge uses the larger of the two panels: got 7107539.536744499 expected 7107539.536744499
PASS  edge beam A (long) w = wS/3·(3 − m²)/2: got 13.538748504397173 expected 13.538748504397171
PASS  corridor long beam C: wS/2 (c/c): got 9.296704199999999 expected 9.296704199999999
PASS  BC-12 first-interior shear factor 1.15: got 1.15 expected 1.15
PASS  two exterior corners of two-way panels: got 2 expected 2
PASS  S&T steel spacing ≤ min(5h, 450): got True expected True
== units, options, modes ==
PASS  SI input gives the same h and wu: got (100.0, 0.009296704) expected (100.0, 0.009296704)
PASS  6 m bays: h = h_min rounded up to 10 mm: got 140.0 expected 140
PASS  edge_beams_stiff false → +10 % h_min on edge panels: got 1.1 expected 1.1
PASS  single panel: case 5, four corners: got (5, 4) expected (5, 4)
PASS  single square panel: each beam wS/3: got 12.240660529999998 expected 12.240660529999998
PASS  missing panel AB-23 → AB-12 loses continuity (case 4): got 4 expected 4
PASS  missing panel by index: got 4 expected 4
PASS  beam_depth 0.5 m → αfm > 2 on every panel: got True expected True
PASS  shallow beams (αfm ≤ 2) → h ≥ 125 mm: got True expected True
PASS  flat plate (αfm ≤ 0.2) stops: got True expected True
PASS  user factors 1.4D + 1.7L: got 0.010355822399999999 expected 0.010355822399999999
PASS  check mode: DB10@200 / h 100 passes: got True expected True
PASS  check mode: s = 250 > 2h fails: got False expected False
PASS  check mode without bars stops: got True expected True
PASS  report lists 'ยังไม่ตรวจ': got True expected True
PASS  report notes Method 2 is not 318-19 text: got True expected True
PASS  every cited kb/ and references/ file exists: got '' expected ''

61 passed, 0 failed
```
