#!/usr/bin/env python3
"""Sync the shared module into each skill, run each skill's tests, and build dist/*.zip.

    python3 tools/build_skills.py           # sync + test + zip
    python3 tools/build_skills.py --check   # only verify the copies match skills/_shared
"""
import filecmp
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED = os.path.join(ROOT, "skills", "_shared", "rcsi.py")
SKILLS = {
    "rc-column-aci318m19": ("scripts/colkit/rcsi.py", "scripts/test_column.py"),
    "rc-beam-aci318m19": ("scripts/beamkit/rcsi.py", "scripts/test_beam.py"),
}


def main(argv):
    check_only = "--check" in argv
    bad = 0
    for name, (copy_rel, test_rel) in SKILLS.items():
        sk = os.path.join(ROOT, "skills", name)
        dst = os.path.join(sk, copy_rel)
        if check_only:
            same = os.path.exists(dst) and filecmp.cmp(SHARED, dst, shallow=False)
            print(f"{name}: rcsi.py {'matches' if same else 'DIFFERS from'} skills/_shared")
            bad += not same
            continue
        shutil.copyfile(SHARED, dst)
        r = subprocess.run([sys.executable, os.path.join(sk, test_rel)], capture_output=True, text=True)
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr
        print(f"{name}: {last}")
        if r.returncode:
            bad += 1
            continue
        for d, _, files in os.walk(sk):
            if os.path.basename(d) == "__pycache__":
                shutil.rmtree(d)
        out = os.path.join(ROOT, "dist", name + ".zip")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for d, dirs, files in os.walk(sk):
                dirs[:] = sorted(x for x in dirs if x != "__pycache__")
                for f in sorted(files):
                    p = os.path.join(d, f)
                    z.write(p, os.path.relpath(p, os.path.join(ROOT, "skills")))
        print(f"  → dist/{name}.zip")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
