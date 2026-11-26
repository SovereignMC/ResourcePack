#!/usr/bin/env python3
"""State-animation injector for structure bbmodels (see README.md and the structure styles plan).

    states.py MODEL.bbmodel            # dry run: report what would change
    states.py MODEL.bbmodel --write    # rewrite the file in place
    states.py MODEL.bbmodel -o OUT     # write the result to another file

Ensures the `status` group with the six lamp bones exists, then (re)generates the eight state
animations running / idle / paused / needs_input / output_full / no_power / no_fuel / inactive.
Idempotent: running it again yields the identical file. The motion source is the existing
`running` animation, or the model's `idle` animation on the first run (it is copied to `running`).
"""
import argparse
import base64
import copy
import io
import json
import math
import os
import sys
import uuid

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OVERRIDES_DIR = os.path.join(HERE, "state_overrides")

STATES = ["running", "idle", "paused", "needs_input", "output_full", "no_power", "no_fuel", "inactive"]
LAMPS = ["lamp_green", "lamp_amber", "lamp_red", "lamp_blue", "lamp_orange", "lamp_off"]
LAMP_RGB = {
    "lamp_green": (62, 214, 88), "lamp_amber": (255, 176, 32), "lamp_red": (232, 48, 48),
    "lamp_blue": (60, 140, 255), "lamp_orange": (255, 106, 0), "lamp_off": (40, 36, 38),
}
HOUSING_RGB = {"housing": (62, 64, 70), "rim": (34, 36, 40)}
# block layout (row-major in a 4x4 texel block)
PIXEL_SLOTS = ["housing", "rim"] + LAMPS
HIDE_WORDS = ("smoke", "fire", "flame", "spark", "pour", "molten")
INPUT_WORDS = ("hopper", "input", "intake", "feed", "chute")
OUTPUT_WORDS = ("output", "crate", "pile", "outbox")
UUID_NS = uuid.UUID("5b0f8a3e-2c8f-4a53-9d2e-71c4a6f0d001")

SPIN_THRESHOLD = 1e-6


def warn(msg):
    print("states.py: warning: " + msg, file=sys.stderr)


# ----------------------------------------------------------------------------- helpers

def uid(*parts):
    return str(uuid.uuid5(UUID_NS, "|".join(str(p) for p in parts)))


def fmt(v):
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def is_hidden_name(name):
    n = name.lower()
    return any(w in n for w in HIDE_WORDS)


def load_overrides(model_path, name):
    for cand in (os.path.join(OVERRIDES_DIR, name + ".json"),
                 os.path.join(OVERRIDES_DIR, os.path.basename(model_path).replace(".bbmodel", "") + ".json")):
        if os.path.isfile(cand):
            with open(cand, "r", encoding="utf-8") as f:
                return json.load(f), cand
    return {}, None


# ----------------------------------------------------------------------------- keyframes

def kf_make(channel, x, y, z, t, interp, bone, anim, idx, uniform=None):
    d = {"channel": channel, "data_points": [{"x": x, "y": y, "z": z}],
         "uuid": uid(anim, bone, channel, idx), "time": t, "color": -1}
    if channel == "scale":
        d["uniform"] = bool(uniform) if uniform is not None else (x == y == z)
    d["interpolation"] = interp
    return d


def scale_kf(value, t, interp, bone, anim, idx):
    v = fmt(value)
    return kf_make("scale", v, v, v, t, interp, bone, anim, idx, uniform=True)


def _numeric(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def transform_keyframes(kfs, anim, bone, time_mul=1.0, amp=1.0, step=False):
    """Copy keyframes of one bone, grouped per channel, with new deterministic uuids.

    Channels whose last value differs from the first ("travelling", e.g. a spinning flywheel) keep their
    amplitude and are only stretched in time; closed oscillations also get their amplitude scaled by `amp`
    (rotation/position around 0, scale around 1).
    """
    out = []
    by_ch = {}
    for k in kfs:
        by_ch.setdefault(k["channel"], []).append(k)
    for ch in sorted(by_ch, key=["rotation", "position", "scale"].index):
        ks = sorted(by_ch[ch], key=lambda k: k["time"])

        def vals(k, which):
            dp = k["data_points"][which]
            return [_numeric(dp.get(a)) for a in "xyz"]

        first, last = vals(ks[0], 0), vals(ks[-1], -1)
        travelling = any(a is not None and b is not None and abs(a - b) > SPIN_THRESHOLD
                         for a, b in zip(first, last)) and len(ks) > 1
        factor = 1.0 if travelling else amp
        for i, k in enumerate(ks):
            nk = copy.deepcopy(k)
            nk["uuid"] = uid(anim, bone, ch, i)
            nk["time"] = round(k["time"] * time_mul, 6)
            if step:
                nk["interpolation"] = "step"
            for dp in nk["data_points"]:
                for a in "xyz":
                    v = _numeric(dp.get(a))
                    if v is None:
                        continue
                    if ch == "scale":
                        v = 1 + (v - 1) * factor
                    else:
                        v = v * factor
                    dp[a] = fmt(v)
            out.append(nk)
    return out


# ----------------------------------------------------------------------------- model wrapper

class Doc:
    def __init__(self, data):
        self.d = data
        self.groups = data["groups"]
        self.by_uuid = {g["uuid"]: g for g in self.groups}
        self.by_name = {}
        for g in self.groups:
            self.by_name.setdefault(g["name"], g)
        self.elements = data["elements"]
        self.parent = {}
        self.node = {}
        self._index(data["outliner"], None)

    def _index(self, nodes, parent):
        for n in nodes:
            if isinstance(n, dict):
                self.node[n["uuid"]] = n
                self.parent[n["uuid"]] = parent
                self._index(n.get("children", []), n["uuid"])
            else:
                self.parent[n] = parent

    def subtree_groups(self, root_uuid):
        res = []

        def walk(u):
            res.append(u)
            for c in self.node[u].get("children", []):
                if isinstance(c, dict):
                    walk(c["uuid"])
        walk(root_uuid)
        return res

    def group_elements(self, guuid):
        return [e for e in self.elements if self.parent.get(e["uuid"]) == guuid]


# ----------------------------------------------------------------------------- atlas

def decode_tex(t):
    return np.array(Image.open(io.BytesIO(base64.b64decode(t["source"].split(",", 1)[1]))).convert("RGBA"))


def encode_tex(arr):
    buf = io.BytesIO()
    Image.fromarray(arr, "RGBA").save(buf, "PNG", optimize=False)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def used_mask(doc, tex_index, w, h, uvw, uvh):
    m = np.zeros((h, w), bool)
    sx, sy = w / uvw, h / uvh
    for e in doc.elements:
        for f in e.get("faces", {}).values():
            if f.get("texture") != tex_index:
                continue
            u1, v1, u2, v2 = f["uv"]
            x0, x1 = sorted((u1 * sx, u2 * sx))
            y0, y1 = sorted((v1 * sy, v2 * sy))
            m[max(0, int(math.floor(y0))):min(h, int(math.ceil(y1))),
              max(0, int(math.floor(x0))):min(w, int(math.ceil(x1)))] = True
    return m


def find_free_block(mask, alpha, size=4):
    """Aligned size x size block, scanning from the bottom-right; prefers a 1 px free margin and alpha 0."""
    h, w = mask.shape
    dil = mask.copy()
    dil[1:, :] |= mask[:-1, :]
    dil[:-1, :] |= mask[1:, :]
    dil[:, 1:] |= mask[:, :-1]
    dil[:, :-1] |= mask[:, 1:]
    for use, need_alpha in ((dil, True), (dil, False), (mask, True), (mask, False)):
        for by in range((h // size) - 1, -1, -1):
            for bx in range((w // size) - 1, -1, -1):
                ys, xs = slice(by * size, by * size + size), slice(bx * size, bx * size + size)
                if use[ys, xs].any():
                    continue
                if need_alpha and (alpha[ys, xs] != 0).any():
                    continue
                return bx * size, by * size
    return None


# ----------------------------------------------------------------------------- lamp construction

def faces_with_uv(u, v, tex):
    fa = {"uv": [u, v, u + 1, v + 1], "texture": tex}
    return {k: copy.deepcopy(fa) for k in ("north", "east", "south", "west", "up", "down")}


def make_cube(template, name, frm, to, uvpix, tex, seed):
    e = {}
    for k in template:  # mirror key order of existing elements
        e[k] = copy.deepcopy(template[k])
    e["name"] = name
    e["from"] = [round(x, 4) for x in frm]
    e["to"] = [round(x, 4) for x in to]
    e["origin"] = [round((a + b) / 2, 4) for a, b in zip(frm, to)]
    e["faces"] = faces_with_uv(uvpix[0], uvpix[1], tex)
    e["uuid"] = uid("element", seed, name)
    e.pop("rotation", None)
    e.pop("inflate", None)
    return e


def lens_boxes(cx, cz, top):
    """Lens plates (center-based) on the housing sides: dict side -> (from, to)."""
    y0, y1 = top + 4.0, top + 6.0
    hw = 1.5
    r = 3.0
    t = 0.25
    return {
        "n": ([cx - hw, y0, cz - r - t], [cx + hw, y1, cz - r]),
        "e": ([cx + r, y0, cz - hw], [cx + r + t, y1, cz + hw]),
        "s": ([cx - hw, y0, cz + r], [cx + hw, y1, cz + r + t]),
        "w": ([cx - r - t, y0, cz - hw], [cx - r, y1, cz + hw]),
    }


def heightmap(model, exclude_groups):
    """Max up-facing height per 1 px column over [-48, 48]^2 (index [z+48, x+48]), -inf where empty."""
    half = 48
    hm = np.full((2 * half, 2 * half), -np.inf)
    for f in model.faces():
        if f["group"] in exclude_groups or f["n"][1] < 0.5:
            continue
        c = f["c"]
        e1, e2 = c[1] - c[0], c[3] - c[0]
        # solve in the XZ plane
        det = e1[0] * e2[2] - e1[2] * e2[0]
        if abs(det) < 1e-9:
            continue
        x0 = int(math.floor(min(c[:, 0]) + half))
        x1 = int(math.ceil(max(c[:, 0]) + half))
        z0 = int(math.floor(min(c[:, 2]) + half))
        z1 = int(math.ceil(max(c[:, 2]) + half))
        x0, z0 = max(x0, 0), max(z0, 0)
        x1, z1 = min(x1, 2 * half), min(z1, 2 * half)
        if x1 <= x0 or z1 <= z0:
            continue
        X, Z = np.meshgrid(np.arange(x0, x1) + 0.5 - half - c[0, 0], np.arange(z0, z1) + 0.5 - half - c[0, 2])
        s = (X * e2[2] - Z * e2[0]) / det
        t = (-X * e1[2] + Z * e1[0]) / det
        ins = (s >= 0) & (s < 1) & (t >= 0) & (t < 1)
        y = c[0, 1] + s * e1[1] + t * e2[1]
        sub = hm[z0:z1, x0:x1]
        sub[ins] = np.maximum(sub[ins], y[ins])
    return hm


def choose_site(model, exclude_groups, override=None):
    if override:
        return override
    hm = heightmap(model, exclude_groups)
    half = 48
    cells = []
    for z in range(-12, 13):
        for x in range(-12, 13):
            h = hm[z + half, x + half]
            if np.isfinite(h):
                cells.append((h, x, z))
    best = None
    if cells:
        hmax = max(c[0] for c in cells)
        # within 3 px of the highest point, take the cell nearest the centre
        h, x, z = min((c for c in cells if c[0] >= hmax - 3), key=lambda c: (c[1] ** 2 + c[2] ** 2, -c[0]))
        best = (None, x + 0.5, z + 0.5, h)
    if best is None:
        warn("no geometry found for the lamp site; using the centre at y=16")
        return [0.0, 0.0, 16.0]
    # snap to a pixel centre -> integer-aligned housing
    return [float(round(best[1] - 0.5)), float(round(best[2] - 0.5)), float(best[3])]


def ensure_status(doc, model, ov, report):
    """Create `status` + lamp bones when missing. Returns (status_group, {lamp name: group}, pixel map or None)."""
    d = doc.d
    status = doc.by_name.get("status")
    have = {n: doc.by_name.get(n) for n in LAMPS}
    if status is not None and all(have.values()):
        return status, have, False
    el_t = d["elements"][0]
    grp_t = copy.deepcopy(next(g for g in doc.groups if g["name"] != "root"))
    seed = d.get("name", "model")

    # texture / pixel allocation
    texes = d["textures"]
    if status is not None:
        site = None
    else:
        exclude = {"status"} | set(LAMPS)
        for g in doc.groups:
            if is_hidden_name(g["name"]):
                exclude.add(g["name"])
        site = choose_site(model, exclude, ov.get("lamp_at"))
        report.append("lamp site x=%.1f z=%.1f top=%.1f" % tuple(site))
    # pixel block
    t0 = texes[0]
    arr = decode_tex(t0)
    h, w = arr.shape[:2]
    mask = used_mask(doc, 0, w, h, t0.get("uv_width") or d["resolution"]["width"],
                     t0.get("uv_height") or d["resolution"]["height"])
    block = find_free_block(mask, arr[..., 3])
    tex_i = 0
    if block is None:
        tex_i = len(texes)
        nt = copy.deepcopy(t0)
        nt["name"] = "status"
        nt["id"] = str(tex_i)
        nt["uuid"] = uid("texture", seed, "status")
        nt["source"] = encode_tex(np.zeros((h, w, 4), np.uint8))
        texes.append(nt)
        block = (0, 0)
        report.append("no free atlas space: added second texture 'status' (index %d)" % tex_i)
    else:
        report.append("lamp pixels in atlas block x=%d y=%d" % block)
    pix = {n: (block[0] + i % 4, block[1] + i // 4) for i, n in enumerate(PIXEL_SLOTS)}

    if status is None:
        cx, cz, top = site
        gid = uid("group", seed, "status")
        status = copy.deepcopy(grp_t)
        status.update({"name": "status", "uuid": gid, "origin": [cx, top, cz], "rotation": [0, 0, 0],
                       "children": [], "isOpen": False})
        doc.groups.append(status)
        doc.by_name["status"] = status
        root_node = doc.node.get(next((g["uuid"] for g in doc.groups if g["name"] == "root"), None))
        node = {"uuid": gid, "isOpen": False, "children": []}
        if root_node is not None:
            root_node["children"].append(node)
            doc.parent[gid] = root_node["uuid"]
        else:
            d["outliner"].append(node)
            doc.parent[gid] = None
        doc.node[gid] = node
        # mast + housing + cap
        parts = [("status_mast", [cx - 1, top, cz - 1], [cx + 1, top + 3, cz + 1], "rim"),
                 ("status_housing", [cx - 3, top + 3, cz - 3], [cx + 3, top + 7, cz + 3], "housing"),
                 ("status_cap", [cx - 2, top + 7, cz - 2], [cx + 2, top + 8, cz + 2], "rim")]
        for name, f, t, slot in parts:
            e = make_cube(el_t, name, f, t, pix[slot], tex_i, seed)
            d["elements"].append(e)
            node["children"].append(e["uuid"])
            doc.parent[e["uuid"]] = gid
        lens_src = None
    else:
        lens_src = None
    cxz = (status["origin"][0], status["origin"][2])
    top = status["origin"][1]
    lens = lens_boxes(cxz[0], cxz[1], top)
    snode = doc.node[status["uuid"]]
    for n in LAMPS:
        if have[n] is not None:
            continue
        gid = uid("group", seed, n)
        g = copy.deepcopy(grp_t)
        g.update({"name": n, "uuid": gid, "origin": [cxz[0], top + 5, cxz[1]], "rotation": [0, 0, 0],
                  "children": [], "isOpen": False})
        doc.groups.append(g)
        doc.by_name[n] = g
        have[n] = g
        node = {"uuid": gid, "isOpen": False, "children": []}
        snode["children"].append(node)
        doc.node[gid] = node
        doc.parent[gid] = status["uuid"]
        for side, (f, t) in lens.items():
            e = make_cube(el_t, "%s_%s" % (n, side), f, t, pix[n], tex_i, seed)
            d["elements"].append(e)
            node["children"].append(e["uuid"])
            doc.parent[e["uuid"]] = gid
    return status, have, True


def paint_lamps(doc, ov, report):
    """Fill the uv texels of the lamp lens / housing faces with the lamp colours (idempotent)."""
    if ov.get("paint_lamps", True) is False:
        return
    d = doc.d
    status = doc.by_name["status"]
    sub = set(doc.subtree_groups(status["uuid"]))
    lens_color = {}
    for n in LAMPS:
        for e in doc.group_elements(doc.by_name[n]["uuid"]):
            lens_color[e["uuid"]] = LAMP_RGB[n]
    # housing: elements directly in status named status_*
    for e in doc.group_elements(status["uuid"]):
        slot = {"status_mast": "rim", "status_housing": "housing", "status_cap": "rim"}.get(e["name"])
        if slot:
            lens_color[e["uuid"]] = HOUSING_RGB[slot]
    ids = set(lens_color)
    arrs = {}
    foreign = {}
    for e in doc.elements:
        for f in e.get("faces", {}).values():
            ti = f.get("texture")
            if ti is None:
                continue
            t = d["textures"][ti]
            if ti not in arrs:
                arrs[ti] = decode_tex(t)
            a = arrs[ti]
            h, w = a.shape[:2]
            sx, sy = w / (t.get("uv_width") or d["resolution"]["width"]), h / (t.get("uv_height") or d["resolution"]["height"])
            u1, v1, u2, v2 = f["uv"]
            x0, x1 = sorted((u1 * sx, u2 * sx))
            y0, y1 = sorted((v1 * sy, v2 * sy))
            rect = (int(math.floor(x0)), int(math.floor(y0)), max(int(math.ceil(x1)), int(math.floor(x0)) + 1),
                    max(int(math.ceil(y1)), int(math.floor(y0)) + 1))
            if e["uuid"] not in ids:
                foreign.setdefault(ti, []).append(rect)
    changed = False
    for e in doc.elements:
        if e["uuid"] not in ids:
            continue
        rgb = lens_color[e["uuid"]]
        for f in e["faces"].values():
            ti = f["texture"]
            t = d["textures"][ti]
            a = arrs[ti]
            h, w = a.shape[:2]
            sx, sy = w / (t.get("uv_width") or d["resolution"]["width"]), h / (t.get("uv_height") or d["resolution"]["height"])
            u1, v1, u2, v2 = f["uv"]
            x0, x1 = sorted((u1 * sx, u2 * sx))
            y0, y1 = sorted((v1 * sy, v2 * sy))
            xa, ya = int(math.floor(x0)), int(math.floor(y0))
            xb, yb = max(int(math.ceil(x1)), xa + 1), max(int(math.ceil(y1)), ya + 1)
            clash = any(not (xb <= r[0] or r[2] <= xa or yb <= r[1] or r[3] <= ya) for r in foreign.get(ti, []))
            if clash:
                warn("lamp face %s overlaps uv of a non-lamp face; not repainting" % e["name"])
                continue
            region = a[ya:yb, xa:xb]
            new = np.array(list(rgb) + [255], np.uint8)
            if not (region == new).all():
                a[ya:yb, xa:xb] = new
                changed = True
                arrs[ti] = a
    if changed:
        for ti, a in arrs.items():
            new_src = encode_tex(a)
            if decode_tex(d["textures"][ti]).tobytes() != a.tobytes():
                d["textures"][ti]["source"] = new_src
        report.append("lamp texels (re)painted")


# ----------------------------------------------------------------------------- animations

def blank_animation(src_tpl, name, length, seed):
    a = {}
    for k in src_tpl:
        a[k] = copy.deepcopy(src_tpl[k])
    a["uuid"] = uid("animation", seed, name)
    a["name"] = name
    a["loop"] = "loop"
    a["override"] = False
    a["length"] = length
    a["selected"] = False
    a["animators"] = {}
    return a


def lamp_keyframes(state, lamp, anim, bone):
    """Scale keyframes (step) for one lamp bone in one state."""
    def steps(pairs):
        return [scale_kf(v, t, "step", bone, anim, i) for i, (t, v) in enumerate(pairs)]

    off = [(0, 0)]
    plans = {
        "running": {"lamp_green": [(0, 1)]},
        "idle": {"lamp_amber": [(0, 1)]},
        "paused": {"lamp_amber": [(0, 1), (1, 0)]},
        "needs_input": {"lamp_red": [(0, 1), (0.25, 0), (0.5, 1), (0.75, 0)]},
        "output_full": {"lamp_blue": [(0, 1), (0.5, 0)]},
        "no_power": {
            "lamp_off": [(0, 1), (2.0, 0), (2.125, 1), (2.25, 0), (2.375, 1)],
            "lamp_amber": [(0, 0), (2.0, 1), (2.125, 0), (2.25, 1), (2.375, 0)],
        },
        "no_fuel": {"lamp_orange": [(0, 1), (0.5, 0)]},
        "inactive": {"lamp_off": [(0, 1)]},
    }
    return steps(plans[state].get(lamp, off))


STATE_LENGTH = {"paused": 2, "needs_input": 1, "output_full": 1, "no_power": 4, "no_fuel": 1, "inactive": 1}


def wobble_keyframes(anim, bone):
    pts = [(0, 0), (0.25, 4), (0.5, 0), (0.75, -4), (1, 0)]
    return [kf_make("rotation", "0", "0", fmt(v), t, "linear", bone, anim, i) for i, (t, v) in enumerate(pts)]


def pulse_keyframes(anim, bone):
    pts = [(0, 1.0), (0.5, 1.15), (1, 1.0)]
    return [scale_kf(v, t, "linear", bone, anim, i) for i, (t, v) in enumerate(pts)]


def build(doc, ov, model_path, report):
    d = doc.d
    seed = d.get("name", "model")
    anims = d.setdefault("animations", [])
    byname = {a["name"]: a for a in anims}
    src = byname.get("running") or byname.get("idle")
    if src is None:
        src = {"uuid": "", "name": "running", "loop": "loop", "override": False, "length": 1, "snapping": 24,
               "selected": True, "group_name": "", "scope": 0, "anim_time_update": "", "blend_weight": "",
               "start_delay": "", "loop_delay": "", "animators": {}}
        report.append("no idle/running animation found: running has no motion")
    elif "running" not in byname:
        report.append("copied the original idle motion to 'running'")
    run_len = float(src.get("length", 1)) or 1.0
    status_ids = set(doc.subtree_groups(doc.by_name["status"]["uuid"]))
    name_by_uuid = {g["uuid"]: g["name"] for g in doc.groups}

    # motion: keyframes per non-status bone, from the source animation
    motion = {}
    for gu, an in src.get("animators", {}).items():
        if gu in status_ids or gu not in name_by_uuid:
            continue
        if an.get("keyframes"):
            motion[gu] = an["keyframes"]

    hide_extra = {n.lower() for n in ov.get("hide", [])}
    idle_visible = {n.lower() for n in ov.get("idle_visible", [])}
    full_amp = {n.lower() for n in ov.get("full_amplitude", [])}

    def hidden(gname):
        return is_hidden_name(gname) or gname.lower() in hide_extra

    # input / output bones
    def pick(key, words):
        if key in ov:
            names = {n.lower() for n in ov[key]}
            found = [g["uuid"] for g in doc.groups if g["name"].lower() in names]
            missing = names - {g["name"].lower() for g in doc.groups}
            if missing:
                warn("override %s: unknown bone(s) %s" % (key, sorted(missing)))
            return found
        return [g["uuid"] for g in doc.groups
                if g["uuid"] not in status_ids and any(w in g["name"].lower() for w in words)]

    inputs, outputs = pick("input_bones", INPUT_WORDS), pick("output_bones", OUTPUT_WORDS)
    report.append("input bones: %s; output bones: %s" % (
        [name_by_uuid[u] for u in inputs] or "none", [name_by_uuid[u] for u in outputs] or "none"))

    new = {}
    for state in STATES:
        length = float(STATE_LENGTH.get(state, run_len))
        mot_mul, amp, step = 1.0, 1.0, False
        use_motion = False
        if state == "running":
            length = run_len
        elif state == "idle":
            length, mot_mul, amp, use_motion = run_len * 4, 4.0, 0.25, True
        elif state == "no_power":
            length, mot_mul, amp, step, use_motion = max(run_len * 4, 4.0), 4.0, 0.5, True, True
            # winding-down stutter needs a common period for lamps (4 s) and motion
            length = math.lcm(int(round(run_len * 4 * 1000)), 4000) / 1000.0
        a = blank_animation(src, state, length, seed)
        if state == "running":
            # keep the uuid of whatever animation supplied the motion (old idle on the first run)
            a["uuid"] = src["uuid"] or uid("animation", seed, state)
            a["selected"] = bool(src.get("selected", False))
        for g in doc.groups:
            gu, gname = g["uuid"], g["name"]
            an = {"name": gname, "type": "bone", "rotation_global": False, "quaternion_interpolation": False}
            kfs = []
            if gu in status_ids and gname in LAMPS:
                kfs = lamp_keyframes(state, gname, state, gname)
            elif gu in status_ids:
                kfs = []
            elif state == "running":
                kfs = copy.deepcopy(src.get("animators", {}).get(gu, {}).get("keyframes", []))
            elif hidden(gname):
                visible_idle = state == "idle" and gname.lower() in idle_visible
                if not visible_idle:
                    kfs = [scale_kf(0, 0, "linear", gname, state, 0)]
                elif gu in motion:
                    kfs = transform_keyframes(motion[gu], state, gname, mot_mul, amp, step)
            else:
                if use_motion and gu in motion:
                    bone_amp = 1.0 if gname.lower() in full_amp else amp
                    kfs = transform_keyframes(motion[gu], state, gname, mot_mul, bone_amp, step)
                if state == "needs_input" and gu in inputs:
                    kfs = wobble_keyframes(state, gname)
                if state == "output_full" and gu in outputs:
                    kfs = pulse_keyframes(state, gname)
            if kfs:
                an["keyframes"] = kfs
            a["animators"][gu] = an
        # keep unknown animators of the running animation (e.g. effects) untouched
        if state == "running":
            for gu, an in src.get("animators", {}).items():
                if gu not in a["animators"]:
                    a["animators"][gu] = an
        new[state] = a
    others = [a for a in anims if a["name"] not in STATES]
    d["animations"] = [new[s] for s in STATES] + others


def process(data, model_path, report):
    model = render.Model(copy.deepcopy(data), model_path)
    doc = Doc(data)
    ov, ov_path = load_overrides(model_path, data.get("name", ""))
    if ov_path:
        report.append("overrides: " + ov_path)
    ensure_status(doc, model, ov, report)
    paint_lamps(doc, ov, report)
    build(doc, ov, model_path, report)
    return data


def dumps(data):
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model")
    ap.add_argument("--write", action="store_true", help="rewrite MODEL in place")
    ap.add_argument("-o", "--output", help="write the result to this path instead")
    a = ap.parse_args(argv)
    path = render.resolve_model(a.model)
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    data = json.loads(raw)
    report = []
    out = dumps(process(data, path, report))
    for line in report:
        print("  " + line)
    if a.output:
        with open(a.output, "w", encoding="utf-8", newline="") as f:
            f.write(out)
        print("wrote %s" % a.output)
    elif a.write:
        if out != raw:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(out)
            print("updated %s" % path)
        else:
            print("%s already up to date" % path)
    else:
        print("dry run: %s would %s" % (path, "change" if out != raw else "stay the same"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
