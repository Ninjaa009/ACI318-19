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
SHARED_DIR = os.path.join(ROOT, "skills", "_shared")
SHARED_TEST = os.path.join(SHARED_DIR, "tests", "test_staadio.py")
SKILLS = {   # skill: (package dir, test)
    "rc-column-aci318m19": ("scripts/colkit", "scripts/test_column.py"),
    "rc-beam-aci318m19": ("scripts/beamkit", "scripts/test_beam.py"),
}
# shared file → destination relative to the package dir
SYNC = {"rcsi.py": "rcsi.py", "staadio.py": "staadio.py", "from_staad.py": "../from_staad.py",
        "staad-sign-convention.md": "../../references/staad-sign-convention.md"}


def main(argv):
    check_only = "--check" in argv
    bad = 0
    if not check_only:
        r = subprocess.run([sys.executable, SHARED_TEST], capture_output=True, text=True)
        print("_shared/staadio:", (r.stdout.strip().splitlines() or [r.stderr])[-1])
        if r.returncode:
            return 1
    for name, (pkg_rel, test_rel) in SKILLS.items():
        sk = os.path.join(ROOT, "skills", name)
        pkg = os.path.join(sk, pkg_rel)
        diffs = []
        for src, rel in SYNC.items():
            s_, d_ = os.path.join(SHARED_DIR, src), os.path.normpath(os.path.join(pkg, rel))
            if check_only:
                if not (os.path.exists(d_) and filecmp.cmp(s_, d_, shallow=False)):
                    diffs.append(src)
            else:
                shutil.copyfile(s_, d_)
        if check_only:
            print(f"{name}: " + ("shared files match" if not diffs else "DIFFERS: " + ", ".join(diffs)))
            bad += bool(diffs)
            continue
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
