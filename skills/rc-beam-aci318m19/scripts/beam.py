#!/usr/bin/env python3
"""RC rectangular beam span — ACI 318M-19.  Usage: beam.py input.json [--json]"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from beamkit.engine import run       # noqa: E402
from beamkit.report import build     # noqa: E402


def _plain(o):
    if isinstance(o, dict):
        return {str(k): _plain(v) for k, v in o.items() if k not in ("beam", "input", "si")}
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
    print(json.dumps(_plain(res), ensure_ascii=False, indent=1) if "--json" in argv else build(res))
    if res.get("stopped"):
        return 1
    return 0 if all(res["status"].values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
