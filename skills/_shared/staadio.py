"""STAAD.Pro → design input (beamkit / colkit).  Units: STAAD kN, m.

CANONICAL COPY: skills/_shared/staadio.py — tools/build_skills.py copies it into each
skill package.  Sign rules verified against STAAD.Pro 2025 output of CC.std
(skills/_shared/tests): see references/staad-sign-convention.md.

Two STAAD tables are accepted (pasted text, tab or space separated):
  * "Beam End Forces"  (columns: Beam L/C Node Fx Fy Fz Mx My Mz)
  * "Beam Section Forces" (columns: Beam L/C Section Fx Fy Fz Mx My Mz)
Both are turned into the SECTION convention, one continuous diagram per member:
  section(0) = end-force at start,  section(1) = −(end-force at end).
In the section convention (verified):
  Axial > 0 = compression; for a member whose local y points up, Mz > 0 = tension on
  the +y (top) face, i.e. M_design (sagging +) = −Mz; a moment that changes sign
  between the two ends = double curvature.
"""
from __future__ import annotations

import math
import re

# ---------------------------------------------------------------- .std model


def _ids(text):
    """'1 TO 6 8 10 TO 12' → [1..6, 8, 10..12]."""
    t = text.replace("TO", " TO ").split()
    out, i = [], 0
    while i < len(t):
        if i + 2 < len(t) and t[i + 1].upper() == "TO":
            out += list(range(int(t[i]), int(t[i + 2]) + 1))
            i += 3
        else:
            out.append(int(t[i]))
            i += 1
    return out


class Model:
    def __init__(self, std_text):
        lines = [ln.split("!")[0].rstrip() for ln in std_text.upper().splitlines()]
        self.joints, self.members, self.prop, self.beta = {}, {}, {}, {}
        sec = None
        for ln in lines:
            s = ln.strip()
            if not s:
                continue
            head = s.split()[0]
            if s.startswith("JOINT COORDINATES"):
                sec = "J"; continue
            if s.startswith("MEMBER INCIDENCES"):
                sec = "M"; continue
            if s.startswith("MEMBER PROPERTY"):
                sec = "P"; continue
            if s.startswith("CONSTANTS"):
                sec = "C"; continue
            if re.match(r"^[A-Z]", head) and not (sec == "C" and head in ("BETA", "MATERIAL")):
                sec = None
                continue
            if sec == "J":
                for p in s.split(";"):
                    v = p.split()
                    if len(v) == 4:
                        self.joints[int(v[0])] = tuple(float(x) for x in v[1:])
            elif sec == "M":
                for p in s.split(";"):
                    v = p.split()
                    if len(v) == 3:
                        self.members[int(v[0])] = (int(v[1]), int(v[2]))
            elif sec == "P" and "PRIS" in s:
                lst, rest = s.split("PRIS")
                yd = re.search(r"YD\s+([\d.Ee+-]+)", rest)
                zd = re.search(r"ZD\s+([\d.Ee+-]+)", rest)
                for m in _ids(lst):
                    self.prop[m] = (float(yd.group(1)), float(zd.group(1)) if zd else float(yd.group(1)))
            elif sec == "C" and head == "BETA":
                v = s.split()
                ang = float(v[1])
                lst = s.split("MEMB")[1] if "MEMB" in s else ""
                for m in _ids(lst.replace("ALL", "")) if lst.strip() not in ("", "ALL") else self.members:
                    self.beta[m] = ang

    # geometry -------------------------------------------------------
    def length(self, m):
        a, b = (self.joints[n] for n in self.members[m])
        return math.dist(a, b)

    def axes(self, m):
        """STAAD default local axes (BETA 0, Y up).  Verified for vertical members both ways."""
        a, b = (self.joints[n] for n in self.members[m])
        L = math.dist(a, b)
        x = tuple((q - p) / L for p, q in zip(a, b))
        if abs(x[1]) > 0.999:                         # vertical: local z = global +Z
            z = (0.0, 0.0, 1.0)
        else:                                         # z = x × Y, normalised
            z = (-x[2], 0.0, x[0])
            n = math.hypot(z[0], z[2])
            z = (z[0] / n, 0.0, z[2] / n)
        y = (z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0])
        return x, y, z

    def is_vertical(self, m):
        return abs(self.axes(m)[0][1]) > 0.999

    def check_supported(self, m):
        """Raise if this member uses a case the sign rules were not verified for."""
        if self.beta.get(m, 0.0):
            raise ValueError(f"member {m}: BETA {self.beta[m]:g} — ยังไม่ได้ตรวจกฎเครื่องหมายกับ BETA ≠ 0")
        if m not in self.prop:
            raise ValueError(f"member {m}: ไม่ใช่หน้าตัด PRIS YD/ZD")
        x, y, _ = self.axes(m)
        if not self.is_vertical(m) and abs(x[1]) > 1e-6:
            raise ValueError(f"member {m}: สมาชิกเอียง — นอกขอบเขต")


# ---------------------------------------------------------------- force tables


def read_forces(text, model):
    """→ {(member, lc): [(pos, [Fx, Fy, Fz, Mx, My, Mz]), …]} in the SECTION convention."""
    kind = "section" if re.search(r"\bSection\b", text, re.I) else "end"
    out, beam, lc = {}, None, None
    for ln in text.splitlines():
        t = ln.split()
        if not t or not re.match(r"^-?\d", t[0]):
            continue
        if len(t) == 9:
            beam, lc, rest = int(t[0]), t[1], t[2:]
        elif len(t) == 8:
            lc, rest = t[0], t[1:]
        elif len(t) == 7:
            rest = t
        else:
            continue
        vals = [float(v) for v in rest[1:]]
        if kind == "section":
            pos = float(rest[0])
        else:
            node = int(rest[0])
            s, e = model.members[beam]
            if node == s:
                pos = 0.0
            elif node == e:
                pos, vals = 1.0, [-v for v in vals]
            else:
                raise ValueError(f"member {beam}: node {node} ไม่ใช่ปลายของสมาชิก")
        out.setdefault((beam, lc), []).append((pos, vals))
    for k in out:
        out[k].sort()
    return out


def at(rows, pos, i):
    """Linear interpolation of component i at relative position pos."""
    for (p0, v0), (p1, v1) in zip(rows, rows[1:]):
        if p0 - 1e-9 <= pos <= p1 + 1e-9:
            if p1 - p0 < 1e-12:
                return v0[i]
            return v0[i] + (v1[i] - v0[i]) * (pos - p0) / (p1 - p0)
    return rows[0][1][i] if pos <= rows[0][0] else rows[-1][1][i]


FX, FY, FZ, MX, MY, MZ = range(6)


# ---------------------------------------------------------------- columns


def _curv(a, b):
    """Section-convention end moments → 'double' if the sign changes along the member."""
    if abs(a) < 1e-9 or abs(b) < 1e-9:
        return "single"                                   # conservative
    return "double" if a * b < 0 else "single"


def column(model, forces, m, lcs):
    """colkit pieces for one vertical member: section (mm), length (m), combos (kN, kN·m)
    and a trace table.  b = ZD (along local z), h = YD (along local y); Mx = Mz, My = My."""
    model.check_supported(m)
    if not model.is_vertical(m):
        raise ValueError(f"member {m} ไม่ใช่เสาแนวดิ่ง")
    s, e = model.members[m]
    top_is_start = model.joints[s][1] > model.joints[e][1]
    pt, pb = (0.0, 1.0) if top_is_start else (1.0, 0.0)
    yd, zd = model.prop[m]
    combos, trace = [], []
    for lc in lcs:
        rows = forces.get((m, str(lc)))
        if not rows:
            raise ValueError(f"ไม่มีแรงของ member {m} LC {lc}")
        P_top, P_bot = at(rows, pt, FX), at(rows, pb, FX)
        Mz_t, Mz_b = at(rows, pt, MZ), at(rows, pb, MZ)
        My_t, My_b = at(rows, pt, MY), at(rows, pb, MY)
        Vy = max(abs(at(rows, p, FY)) for p, _ in rows)
        Vz = max(abs(at(rows, p, FZ)) for p, _ in rows)
        cb = {"name": f"LC{lc}", "Pu": max(P_top, P_bot),
              "Mx_top": abs(Mz_t), "Mx_bot": abs(Mz_b), "curv_x": _curv(Mz_t, Mz_b),
              "My_top": abs(My_t), "My_bot": abs(My_b), "curv_y": _curv(My_t, My_b),
              "Vux": Vz, "Vuy": Vy}
        combos.append(cb)
        trace.append({"lc": lc, "P_top": P_top, "P_bot": P_bot, "Mz_top": Mz_t, "Mz_bot": Mz_b,
                      "My_top": My_t, "My_bot": My_b, "Vy": Vy, "Vz": Vz,
                      "curv_x": cb["curv_x"], "curv_y": cb["curv_y"]})
    beams_top = [b for b, (i, j) in model.members.items()
                 if not model.is_vertical(b) and (model.joints[s if top_is_start else e] in
                                                  (model.joints[i], model.joints[j]))]
    hb = max((model.prop[b][0] for b in beams_top if b in model.prop), default=0.0)
    L = model.length(m)
    return {"section": {"b": zd * 1000.0, "h": yd * 1000.0},
            "length": {"L": L, "lu": L - hb},
            "combos": combos, "trace": trace,
            "info": {"member": m, "top_node": s if top_is_start else e,
                     "bottom_node": e if top_is_start else s, "flipped": top_is_start,
                     "beam_depth_top": hb}}


# ---------------------------------------------------------------- beams


def _support_offset(model, node, xdir):
    """Half the width of the column at `node`, measured along the beam direction (m)."""
    best = 0.0
    for c, (i, j) in model.members.items():
        if node in (i, j) and model.is_vertical(c) and c in model.prop:
            _, yc, zc = model.axes(c)
            yd, zd = model.prop[c]
            w = yd if abs(sum(p * q for p, q in zip(xdir, yc))) > 0.9 else zd
            best = max(best, w / 2.0)
    return best


def beam(model, forces, m, lcs):
    """beamkit pieces for one horizontal member: moments at the column faces and the
    largest sagging moment, shear at the faces (kN, kN·m, skill sign: M < 0 = top tension)."""
    model.check_supported(m)
    x, y, _ = model.axes(m)
    if len(forces.get((m, str(lcs[0])), [])) < 3:
        raise ValueError("คานต้องใช้ตาราง Beam Section Forces (ตาราง End Forces ไม่มีโมเมนต์กลางช่วง)")
    if model.is_vertical(m) or y[1] < 0.999:
        raise ValueError(f"member {m}: แกน local y ไม่ชี้ขึ้น — ตรวจ start/end หรือ BETA")
    s, e = model.members[m]
    L = model.length(m)
    a0 = _support_offset(model, s, x) / L
    a1 = 1.0 - _support_offset(model, e, x) / L
    combos, trace = [], []
    for lc in lcs:
        rows = forces.get((m, str(lc)))
        if not rows:
            raise ValueError(f"ไม่มีแรงของ member {m} LC {lc}")
        ML, MR = -at(rows, a0, MZ), -at(rows, a1, MZ)
        inner = [(p, -v[MZ]) for p, v in rows if a0 <= p <= a1]
        Mmid = max([v for _, v in inner] + [-at(rows, 0.5, MZ)])
        VL, VR = abs(at(rows, a0, FY)), abs(at(rows, a1, FY))
        T = max(abs(v[MX]) for _, v in rows)
        combos.append({"name": f"LC{lc}", "M_left": ML, "M_mid": Mmid, "M_right": MR,
                       "V_left": VL, "V_right": VR})
        trace.append({"lc": lc, "M_left": ML, "M_mid": Mmid, "M_right": MR, "V_left": VL,
                      "V_right": VR, "T": T, "Mz_node_s": at(rows, 0.0, MZ), "Mz_node_e": at(rows, 1.0, MZ)})
    yd, zd = model.prop[m]
    return {"section": {"b": zd * 1000.0, "h": yd * 1000.0},
            "span": {"ln": L * (a1 - a0)}, "combos": combos, "trace": trace,
            "info": {"member": m, "left_node": s, "right_node": e, "L": L,
                     "face_left": a0 * L, "face_right": (1 - a1) * L}}


# ---------------------------------------------------------------- report helper


def trace_md(kind, piece):
    """Markdown table: where each design value came from."""
    i = piece["info"]
    if kind == "column":
        L = [f"**ที่มาของแรง: STAAD member {i['member']}** · บน = node {i['top_node']}, ล่าง = node {i['bottom_node']}"
             + (" (start อยู่บน — สมาชิกกลับด้าน)" if i["flipped"] else ""),
             f"h = YD, b = ZD · Mx = Mz, My = My · ℓu = L − ความลึกคานที่หัวเสา ({i['beam_depth_top']:.2f} m)", "",
             "| LC | Pu บน / ล่าง | Mz บน / ล่าง (section) | ทิศดัด x | My บน / ล่าง | ทิศดัด y | Vy / Vz |",
             "|---|---|---|---|---|---|---|"]
        for t in piece["trace"]:
            L.append(f"| {t['lc']} | {t['P_top']:.1f} / {t['P_bot']:.1f} | {t['Mz_top']:+.2f} / {t['Mz_bot']:+.2f} | {t['curv_x']} | "
                     f"{t['My_top']:+.2f} / {t['My_bot']:+.2f} | {t['curv_y']} | {t['Vy']:.2f} / {t['Vz']:.2f} |")
        L.append("\nPu ใช้ค่ามากสุดตามความยาว (ปลายล่าง) · เครื่องหมาย section ต่างกันที่สองปลาย = โค้งสองทาง")
    else:
        L = [f"**ที่มาของแรง: STAAD member {i['member']}** · ซ้าย = node {i['left_node']} (start), ขวา = node {i['right_node']}",
             f"M, V ที่ผิวเสา: ห่าง node {i['face_left']:.3f} / {i['face_right']:.3f} m · M_design = −Mz(section)", "",
             "| LC | Mz node ซ้าย / ขวา (section) | M ซ้าย | M บวกมากสุด | M ขวา | V ซ้าย / ขวา | แรงบิดสูงสุด |",
             "|---|---|---|---|---|---|---|"]
        for t in piece["trace"]:
            L.append(f"| {t['lc']} | {t['Mz_node_s']:+.2f} / {t['Mz_node_e']:+.2f} | {t['M_left']:+.2f} | {t['M_mid']:+.2f} | "
                     f"{t['M_right']:+.2f} | {t['V_left']:.2f} / {t['V_right']:.2f} | {t['T']:.2f} |")
    return "\n".join(L)
