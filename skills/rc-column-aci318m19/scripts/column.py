#!/usr/bin/env python3
"""RC tied rectangular column — ACI 318M-19.  Usage: column.py input.json [--json]"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colkit.engine import run          # noqa: E402
from colkit.report import build        # noqa: E402


def _plain(o):
    if isinstance(o, dict):
        return {k: _plain(v) for k, v in o.items() if k not in ("col", "input", "si")}
    if isinstance(o, (list, tuple)):
        return [_plain(v) for v in o]
    if isinstance(o, float) and math.isinf(o):
        return "inf"
    return o


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        inp = json.load(fh)
    res = run(inp)
    if "--json" in argv:
        out = _plain(res)
        if "col" in res:
            c = res["col"]
            out["section"] = {"label": c.label(), "Ast": c.Ast, "rho": c.Ast / c.Ag, "phiPn_max": c.phiPn_max}
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(build(res))
    if res.get("stopped"):
        return 1
    return 0 if all(res["status"].values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
