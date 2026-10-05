#!/usr/bin/env python3
"""STAAD.Pro → skill input JSON.  CANONICAL COPY in skills/_shared (synced by tools/build_skills.py).

  python3 scripts/from_staad.py MODEL.std FORCES.txt --kind column --member 30 --lc 101 102 \
          --fc 20 --fy 392.3 [--fyt 235.4] [--mode design|check] [--system OMF|IMF] \
          [--bars 20,3,3] [--ties 10,150] [--position interior|perimeter] [--support both_ends] -o input.json

FORCES.txt = STAAD table pasted as text: "Beam Section Forces" (needed for beams) or
"Beam End Forces" (columns only).  Units in STAAD must be kN and m.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
for pkg in ("colkit", "beamkit"):
    if os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), pkg)):
        staadio = __import__(f"{pkg}.staadio", fromlist=["staadio"])
        break


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("std")
    ap.add_argument("forces")
    ap.add_argument("--kind", choices=["column", "beam"], required=True)
    ap.add_argument("--member", type=int, required=True)
    ap.add_argument("--lc", nargs="+", required=True)
    ap.add_argument("--fc", type=float, required=True, help="f′c ทรงกระบอก MPa")
    ap.add_argument("--fy", type=float, required=True, help="MPa (SD40 = 392.3)")
    ap.add_argument("--fyt", type=float)
    ap.add_argument("--mode", default="design", choices=["design", "check"])
    ap.add_argument("--system", choices=["OMF", "IMF"])
    ap.add_argument("--bars", help="column check: db,nx,ny")
    ap.add_argument("--ties", help="db,s (column) or db,legs (beam)")
    ap.add_argument("--position", choices=["interior", "perimeter"])
    ap.add_argument("--support", choices=["simple", "one_end", "both_ends", "cantilever"])
    ap.add_argument("-o", "--out")
    a = ap.parse_args(argv)
    model = staadio.Model(open(a.std, encoding="utf-8", errors="replace").read())
    forces = staadio.read_forces(open(a.forces, encoding="utf-8", errors="replace").read(), model)
    mats = {"fc": a.fc, "fy": a.fy, "fyt": a.fyt or a.fy}
    if a.kind == "column":
        p = staadio.column(model, forces, a.member, a.lc)
        inp = {"mode": a.mode, "units": "SI", "system": a.system, "section": p["section"],
               "materials": mats, "length": dict(p["length"], k=1.0), "combos": p["combos"]}
        if a.bars:
            db, nx, ny = (float(v) for v in a.bars.split(","))
            inp["bars"] = {"db": db, "nx": int(nx), "ny": int(ny)}
        if a.ties:
            db, s = (float(v) for v in a.ties.split(","))
            inp["ties"] = {"db": db, "s": s}
    else:
        p = staadio.beam(model, forces, a.member, a.lc)
        span = dict(p["span"])
        if a.position:
            span["position"] = a.position
        if a.support:
            span["support"] = a.support
        inp = {"mode": a.mode, "units": "SI", "system": a.system, "section": p["section"],
               "materials": mats, "span": span, "combos": p["combos"]}
        if a.ties:
            db, legs = a.ties.split(",")
            inp["stirrups"] = {"db": float(db), "legs": int(legs)}
    inp["_trace_md"] = staadio.trace_md(a.kind, p)
    txt = json.dumps(inp, ensure_ascii=False, indent=1)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(txt)
    print(inp["_trace_md"])
    if not a.out:
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
