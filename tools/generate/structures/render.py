#!/usr/bin/env python3
"""Software renderer for Blockbench "free" format (5.0) .bbmodel files.

Pure Python (numpy + Pillow). Orthographic, z-buffered, nearest-neighbour textured,
Minecraft-style per-face shading, transparent background. See README.md in this folder.

Coordinate system (Minecraft / BetterModel): +X east, +Y up, +Z south, so north is -Z.
Units are model pixels (16 px = 1 block).

Library use::

    import render
    m = render.Model.load("bbmodels/structure_smelter.bbmodel")
    img = render.render(m, "iso_ne", 256)                    # PIL RGBA
    img = render.render(m, "iso_ne", 256, anim="running", time=0.5)
"""
import argparse
import base64
import io
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PACK_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

VIEWS = ["iso_ne", "iso_nw", "iso_se", "iso_sw", "north", "east", "south", "west", "top"]
ISO_ELEVATION = 30.0  # degrees above the horizon (Minecraft GUI item look)

_warned = set()


def warn(msg):
    if msg not in _warned:
        _warned.add(msg)
        print("render.py: warning: " + msg, file=sys.stderr)


# ----------------------------------------------------------------------------- math

def _num(v, what=""):
    """Plain numbers only. Molang or anything unparseable counts as 0 (warned)."""
    if isinstance(v, (int, float)):
        return float(v)
    if v is None:
        return 0.0
    s = str(v).strip()
    if s == "":
        return 0.0
    try:
        return float(s)
    except ValueError:
        warn("non-numeric (Molang) keyframe value %r treated as 0%s" % (s, what))
        return 0.0


def translate(v):
    m = np.eye(4)
    m[:3, 3] = v
    return m


def scale_m(s):
    m = np.eye(4)
    m[0, 0], m[1, 1], m[2, 2] = s
    return m


def euler_zyx(rot_deg):
    """Blockbench/three.js Euler order 'ZYX': R = Rz @ Ry @ Rx (x applied first)."""
    x, y, z = (math.radians(a) for a in rot_deg)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    m = np.eye(4)
    m[:3, :3] = rz @ ry @ rx
    return m


def pivot_transform(origin, rot, pos=(0, 0, 0), scl=(1, 1, 1)):
    o = np.asarray(origin, float)
    return translate(pos) @ translate(o) @ euler_zyx(rot) @ scale_m(scl) @ translate(-o)


# ----------------------------------------------------------------------------- model

class Group:
    def __init__(self, d, parent):
        self.uuid = d["uuid"]
        self.name = d.get("name", "")
        self.origin = d.get("origin", [0, 0, 0])
        self.rotation = d.get("rotation", [0, 0, 0])
        self.visible = d.get("visibility", True)
        self.parent = parent
        self.children = []   # Group
        self.elements = []   # element dicts


class Model:
    def __init__(self, data, path=None):
        self.data = data
        self.path = path
        self.name = data.get("name", "")
        res = data.get("resolution", {"width": 16, "height": 16})
        self.res = (res.get("width", 16), res.get("height", 16))
        self.groups = {}
        self.root_elements = []
        self.elements = {e["uuid"]: e for e in data.get("elements", [])}
        defs = {g["uuid"]: g for g in data.get("groups", []) if isinstance(g, dict)}
        self._walk(data.get("outliner", []), None, defs)
        self.textures = []
        for t in data.get("textures", []):
            self.textures.append(_decode_texture(t, self.res))
        self.animations = {a["name"]: a for a in data.get("animations", [])}
        self.unsupported = set()
        for e in self.elements.values():
            if e.get("type", "cube") != "cube":
                self.unsupported.add("element type %s" % e.get("type"))
        for s in sorted(self.unsupported):
            warn("%s: unsupported feature (%s); those elements are skipped" % (self.name, s))

    @classmethod
    def load(cls, path):
        path = resolve_model(path)
        with open(path, "r", encoding="utf-8") as f:
            return cls(json.load(f), path)

    def _walk(self, nodes, parent, defs):
        for n in nodes:
            if isinstance(n, str):
                el = self.elements.get(n)
                if el is None:
                    continue
                (parent.elements if parent else self.root_elements).append(el)
            else:
                d = dict(defs.get(n.get("uuid"), {}))
                d.update({k: v for k, v in n.items() if k not in ("children",)})
                g = Group(d, parent)
                self.groups[g.uuid] = g
                if parent:
                    parent.children.append(g)
                self._walk(n.get("children", []), g, defs)

    def group_by_name(self, name):
        for g in self.groups.values():
            if g.name == name:
                return g
        return None

    # ---- animation
    def anim_length(self, name):
        a = self.animations.get(name)
        return float(a.get("length", 0)) if a else 0.0

    def group_pose(self, anim=None, time=0.0):
        """Return {group uuid: 4x4 world matrix of the group's local space} for the animation at `time`."""
        a = self.animations.get(anim) if anim else None
        if anim and a is None:
            raise SystemExit("animation %r not found (have: %s)" % (anim, ", ".join(self.animations) or "none"))
        t = 0.0
        loop = "loop"
        if a is not None:
            loop = a.get("loop", "loop")
            length = float(a.get("length", 0))
            t = float(time)
            if loop == "loop" and length > 0:
                t = t % length
            elif length > 0:
                t = min(t, length)
        mats = {}

        def visit(g, parent_m, parent_vis):
            rot = list(map(float, g.rotation))
            pos = [0.0, 0.0, 0.0]
            scl = [1.0, 1.0, 1.0]
            if a is not None:
                an = a.get("animators", {}).get(g.uuid)
                if an:
                    kfs = an.get("keyframes", [])
                    for ch, dst, default in (("rotation", rot, None), ("position", pos, None), ("scale", scl, None)):
                        v = _sample_channel(kfs, ch, t, a, g.name)
                        if v is not None:
                            if ch == "rotation":
                                rot = [rot[i] + v[i] for i in range(3)]
                            elif ch == "position":
                                pos = v
                            else:
                                scl = v
            m = parent_m @ pivot_transform(g.origin, rot, pos, scl)
            mats[g.uuid] = (m, parent_vis and g.visible)
            for c in g.children:
                visit(c, m, parent_vis and g.visible)

        top = [g for g in self.groups.values() if g.parent is None]
        for g in top:
            visit(g, np.eye(4), True)
        return mats

    # ---- geometry
    def faces(self, anim=None, time=0.0):
        """List of face dicts: corners (4,3) TL,TR,BR,BL world px, uv (4,2) texture px, tex, name, normal."""
        mats = self.group_pose(anim, time)
        out = []

        def emit(el, gm, gname=""):
            if el.get("type", "cube") != "cube" or el.get("visibility", True) is False:
                return
            f0 = np.array(el["from"], float) - el.get("inflate", 0)
            t0 = np.array(el["to"], float) + el.get("inflate", 0)
            rot = el.get("rotation", [0, 0, 0])
            origin = el.get("origin", [0, 0, 0])
            m = gm @ pivot_transform(origin, rot)
            x0, y0, z0 = f0
            x1, y1, z1 = t0
            corners = {
                "north": [(x1, y1, z0), (x0, y1, z0), (x0, y0, z0), (x1, y0, z0)],
                "south": [(x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1)],
                "east": [(x1, y1, z1), (x1, y1, z0), (x1, y0, z0), (x1, y0, z1)],
                "west": [(x0, y1, z0), (x0, y1, z1), (x0, y0, z1), (x0, y0, z0)],
                "up": [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
                "down": [(x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0)],
            }
            canon = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0),
                     "up": (0, 1, 0), "down": (0, -1, 0)}
            for fname, face in el.get("faces", {}).items():
                tex = face.get("texture")
                if tex is None or fname not in corners:
                    continue
                if not (0 <= tex < len(self.textures)):
                    continue
                c = np.array(corners[fname], float)
                c = (m[:3, :3] @ c.T).T + m[:3, 3]
                u1, v1, u2, v2 = face.get("uv", [0, 0, 0, 0])
                uvs = [(u1, v1), (u2, v1), (u2, v2), (u1, v2)]
                rot_f = int(face.get("rotation", 0) or 0) % 360
                for _ in range(rot_f // 90):  # texture rotated clockwise: TL's uv moves to TR
                    uvs = [uvs[3], uvs[0], uvs[1], uvs[2]]
                tw = self.textures[tex]
                sx, sy = tw["w"] / tw["uv_w"], tw["h"] / tw["uv_h"]
                uv = np.array([(u * sx, v * sy) for u, v in uvs], float)
                n = np.cross(c[1] - c[0], c[0] - c[3])
                ln = np.linalg.norm(n)
                if ln < 1e-9:
                    n = m[:3, :3] @ np.array(canon[fname], float)
                    ln = np.linalg.norm(n)
                n = n / ln if ln > 1e-9 else np.array(canon[fname], float)
                out.append({"c": c, "uv": uv, "tex": tex, "name": fname, "n": n, "group": gname,
                            "element": el.get("name", "")})

        def visit(g):
            gm, vis = mats[g.uuid]
            if vis:
                for el in g.elements:
                    emit(el, gm, g.name)
            for ch in g.children:
                visit(ch)

        for el in self.root_elements:
            emit(el, np.eye(4))
        for g in self.groups.values():
            if g.parent is None:
                visit(g)
        return out

    def points(self, anim=None, time=0.0, faces=None):
        fs = faces if faces is not None else self.faces(anim, time)
        if not fs:
            return np.zeros((1, 3))
        return np.concatenate([f["c"] for f in fs])


def resolve_model(path):
    """Accept a path, a bbmodels file name, or a bare family name such as `smelter`."""
    cands = [path, os.path.join(PACK_ROOT, path), os.path.join(PACK_ROOT, "bbmodels", path),
             os.path.join(PACK_ROOT, "bbmodels", path + ".bbmodel"),
             os.path.join(PACK_ROOT, "bbmodels", "structure_" + path + ".bbmodel")]
    for c in cands:
        if os.path.isfile(c):
            return c
    raise SystemExit("model not found: %s" % path)


def _decode_texture(t, res):
    src = t.get("source", "")
    if not src.startswith("data:"):
        raise SystemExit("texture %r is not embedded (no data: source)" % t.get("name"))
    img = Image.open(io.BytesIO(base64.b64decode(src.split(",", 1)[1]))).convert("RGBA")
    arr = np.array(img)
    return {"arr": arr, "w": arr.shape[1], "h": arr.shape[0],
            "uv_w": t.get("uv_width") or res[0], "uv_h": t.get("uv_height") or res[1]}


# ----------------------------------------------------------------------------- animation sampling

def _vec(kf, idx=-1):
    dp = kf["data_points"][idx]
    return [_num(dp.get(k), " (axis %s)" % k) for k in "xyz"]


def _sample_channel(kfs, ch, t, anim, bone):
    ks = sorted((k for k in kfs if k["channel"] == ch), key=lambda k: k["time"])
    if not ks:
        return None
    if t <= ks[0]["time"]:
        return _vec(ks[0], 0)
    if t >= ks[-1]["time"]:
        return _vec(ks[-1], -1)
    i = 0
    while ks[i + 1]["time"] <= t:
        i += 1
    a, b = ks[i], ks[i + 1]
    span = b["time"] - a["time"]
    al = (t - a["time"]) / span if span > 0 else 1.0
    va, vb = _vec(a, -1), _vec(b, 0)
    # Blockbench uses the interpolation of the keyframe the segment ends at for catmullrom/bezier
    mode = b.get("interpolation", "linear")
    if mode == "step" or a.get("interpolation") == "step":
        return va
    if mode == "catmullrom" or a.get("interpolation") == "catmullrom":
        loop = anim.get("loop", "loop") == "loop"
        p0 = _vec(ks[i - 1], -1) if i > 0 else (_vec(ks[-1], -1) if loop and len(ks) > 2 else va)
        p3 = _vec(ks[i + 2], 0) if i + 2 < len(ks) else (_vec(ks[0], 0) if loop and len(ks) > 2 else vb)
        out = []
        for k in range(3):
            out.append(0.5 * ((2 * va[k]) + (-p0[k] + vb[k]) * al +
                              (2 * p0[k] - 5 * va[k] + 4 * vb[k] - p3[k]) * al * al +
                              (-p0[k] + 3 * va[k] - 3 * vb[k] + p3[k]) * al ** 3))
        return out
    if mode == "bezier":
        warn("bezier interpolation rendered as linear")
    return [va[k] + (vb[k] - va[k]) * al for k in range(3)]


# ----------------------------------------------------------------------------- camera

def camera(view):
    """Return (right, up, forward) unit vectors; forward points from the camera into the scene."""
    if view.startswith("iso_"):
        # iso_<ns><ew>: camera sits on that corner, above.
        ns, ew = view[4], view[5]
        dz = -1.0 if ns == "n" else 1.0
        dx = 1.0 if ew == "e" else -1.0
        el = math.radians(ISO_ELEVATION)
        to_cam = np.array([dx * math.cos(el) / math.sqrt(2), math.sin(el), dz * math.cos(el) / math.sqrt(2)])
        hint = np.array([0, 1.0, 0])
    elif view == "top":
        to_cam = np.array([0, 1.0, 0])
        hint = np.array([0, 0, -1.0])  # north at the top of the image
    else:
        to_cam = {"north": (0, 0, -1.0), "south": (0, 0, 1.0), "east": (1.0, 0, 0), "west": (-1.0, 0, 0)}.get(view)
        if to_cam is None:
            raise SystemExit("unknown view %r (use one of %s)" % (view, ", ".join(VIEWS)))
        to_cam = np.array(to_cam)
        hint = np.array([0, 1.0, 0])
    f = -to_cam / np.linalg.norm(to_cam)
    r = np.cross(f, hint)
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return r, u, f


def view_extent(points, view):
    r, u, f = camera(view)
    x = points @ r
    y = points @ u
    return (x.min(), x.max(), y.min(), y.max())


def fit(points_list, views, size, margin=0.06):
    """Common scale (px per model px) so every view of every point set fits, plus per-view centres."""
    if isinstance(points_list, np.ndarray):
        points_list = [points_list]
    allp = np.concatenate(points_list)
    scale = None
    centres = {}
    for v in views:
        x0, x1, y0, y1 = view_extent(allp, v)
        w, h = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
        s = size * (1 - 2 * margin) / max(w, h)
        scale = s if scale is None else min(scale, s)
        centres[v] = ((x0 + x1) / 2, (y0 + y1) / 2)
    return scale, centres


# ----------------------------------------------------------------------------- rasteriser

def _shade(n, view_f):
    n = np.asarray(n, float)
    if float(n @ view_f) > 0:  # back-facing (thin planes): shade by the visible side
        n = -n
    nx2, ny2, nz2 = n[0] ** 2, n[1] ** 2, n[2] ** 2
    top = 1.0 if n[1] > 0 else 0.5
    return 0.8 * nz2 + 0.6 * nx2 + top * ny2


def render(model, view="iso_ne", size=256, anim=None, time=0.0, scale=None, centre=None,
           ssaa=1, faces=None, shading=True):
    """Render to a PIL RGBA image of size x size (transparent background).

    scale/centre: px per model unit and the (x, y) view-plane point in the image centre; both
    default to a fit of this model/pose. `ssaa` > 1 renders larger and box-filters down.
    """
    fs = faces if faces is not None else model.faces(anim, time)
    if scale is None or centre is None:
        pts = model.points(faces=fs)
        s, cs = fit(pts, [view], size)
        scale = scale or s
        centre = centre or cs[view]
    k = max(1, int(ssaa))
    W = size * k
    r, u, f = camera(view)
    zbuf = np.full((W, W), -1e18)
    img = np.zeros((W, W, 4), np.uint8)
    sc = scale * k
    for face in fs:
        c = face["c"]
        sx = (c @ r - centre[0]) * sc + W / 2
        sy = W / 2 - (c @ u - centre[1]) * sc
        z = -(c @ f)
        ex, ey = (sx[1] - sx[0], sy[1] - sy[0])
        fx, fy = (sx[3] - sx[0], sy[3] - sy[0])
        det = ex * fy - ey * fx
        if abs(det) < 1e-9:
            continue
        x0 = int(max(0, math.floor(sx.min())))
        x1 = int(min(W, math.ceil(sx.max())))
        y0 = int(max(0, math.floor(sy.min())))
        y1 = int(min(W, math.ceil(sy.max())))
        if x1 <= x0 or y1 <= y0:
            continue
        px = np.arange(x0, x1) + 0.5 - sx[0]
        py = np.arange(y0, y1) + 0.5 - sy[0]
        PX, PY = np.meshgrid(px, py)
        s_ = (PX * fy - PY * fx) / det
        t_ = (-PX * ey + PY * ex) / det
        inside = (s_ >= 0) & (s_ < 1) & (t_ >= 0) & (t_ < 1)
        if not inside.any():
            continue
        zz = z[0] + s_ * (z[1] - z[0]) + t_ * (z[3] - z[0])
        uv = face["uv"]
        uu = uv[0, 0] + s_ * (uv[1, 0] - uv[0, 0]) + t_ * (uv[3, 0] - uv[0, 0])
        vv = uv[0, 1] + s_ * (uv[1, 1] - uv[0, 1]) + t_ * (uv[3, 1] - uv[0, 1])
        tex = model.textures[face["tex"]]
        ix = np.clip(np.floor(np.where(inside, uu, 0)).astype(int), 0, tex["w"] - 1)
        iy = np.clip(np.floor(np.where(inside, vv, 0)).astype(int), 0, tex["h"] - 1)
        col = tex["arr"][iy, ix]
        zb = zbuf[y0:y1, x0:x1]
        ok = inside & (col[..., 3] >= 8) & (zz >= zb - 1e-4)
        if not ok.any():
            continue
        sh = _shade(face["n"], f) if shading else 1.0
        rgb = (col[..., :3].astype(float) * sh).clip(0, 255).astype(np.uint8)
        out = img[y0:y1, x0:x1]
        out[ok, :3] = rgb[ok]
        out[ok, 3] = 255
        zb[ok] = zz[ok]
    im = Image.fromarray(img, "RGBA")
    if k > 1:
        a = np.asarray(im).astype(np.float64)
        a = a.reshape(size, k, size, k, 4)
        al = a[..., 3]
        wsum = al.sum(axis=(1, 3))
        rgb = (a[..., :3] * al[..., None]).sum(axis=(1, 3)) / np.maximum(wsum, 1)[..., None]
        alpha = wsum / (k * k)
        res = np.concatenate([rgb, alpha[..., None]], axis=2)
        im = Image.fromarray(np.rint(res).astype(np.uint8), "RGBA")
    return im


# ----------------------------------------------------------------------------- composites

def _font(size=14):
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def _paste_label(canvas, text, xy, fill=(235, 235, 235, 255)):
    ImageDraw.Draw(canvas).text(xy, text, fill=fill, font=_font(14))


def parse_bg(s):
    if s in (None, "", "transparent", "none"):
        return None
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def contact_sheet(model, size=256, anim=None, time=0.0, bg=(58, 62, 70, 255), ssaa=1, cols=3):
    fs = model.faces(anim, time)
    pts = model.points(faces=fs)
    order = ["iso_ne", "iso_nw", "iso_se", "iso_sw", "top", "north", "east", "south", "west"]
    scale, centres = fit(pts, order, size)
    label_h = 20
    rows = math.ceil(len(order) / cols)
    sheet = Image.new("RGBA", (cols * size, rows * (size + label_h)), bg or (0, 0, 0, 0))
    nice = {"north": "N (looking at the north face)", "east": "E (looking at the east face)",
            "south": "S (looking at the south face)", "west": "W (looking at the west face)",
            "top": "top (north up)", "iso_ne": "iso NE", "iso_nw": "iso NW", "iso_se": "iso SE", "iso_sw": "iso SW"}
    for i, v in enumerate(order):
        im = render(model, v, size, scale=scale, centre=centres[v], ssaa=ssaa, faces=fs)
        x, y = (i % cols) * size, (i // cols) * (size + label_h)
        sheet.alpha_composite(im, (x, y + label_h))
        _paste_label(sheet, nice[v], (x + 6, y + 2))
    return sheet


def anim_strip(model, anim, frames, view="iso_ne", size=192, bg=(58, 62, 70, 255), ssaa=1):
    length = model.anim_length(anim) or 1.0
    times = [length * i / frames for i in range(frames)]
    faces = [model.faces(anim, t) for t in times]
    scale, centres = fit([model.points(faces=f) for f in faces], [view], size)
    label_h = 20
    strip = Image.new("RGBA", (frames * size, size + label_h), bg or (0, 0, 0, 0))
    for i, (t, fs) in enumerate(zip(times, faces)):
        im = render(model, view, size, scale=scale, centre=centres[view], ssaa=ssaa, faces=fs)
        strip.alpha_composite(im, (i * size, label_h))
        _paste_label(strip, "%s t=%.3g" % (anim, t), (i * size + 6, 2))
    return strip


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a .bbmodel (Blockbench free format) to PNG.")
    ap.add_argument("model", help="path, bbmodels file name, or family name (e.g. smelter)")
    ap.add_argument("--view", default="iso_ne", help="one of: " + ", ".join(VIEWS))
    ap.add_argument("--size", type=int, default=256, help="cell size in px (default 256)")
    ap.add_argument("--sheet", action="store_true", help="contact sheet: 4 iso corners, top, N/E/S/W")
    ap.add_argument("--anim", help="animation name to pose the model with")
    ap.add_argument("--time", type=float, default=0.0, help="animation time in seconds (default 0)")
    ap.add_argument("--frames", type=int, help="with --anim: horizontal strip of N frames over the loop")
    ap.add_argument("--ssaa", type=int, default=1, help="supersampling factor (default 1 = pure nearest)")
    ap.add_argument("--bg", default=None, help="background colour #rrggbb or transparent (default: sheet/strip grey, single transparent)")
    ap.add_argument("-o", "--output", required=True)
    a = ap.parse_args(argv)
    model = Model.load(a.model)
    if a.sheet or a.frames:
        bg = (58, 62, 70, 255) if a.bg is None else parse_bg(a.bg)
    else:
        bg = parse_bg(a.bg)
    if a.frames:
        if not a.anim:
            raise SystemExit("--frames needs --anim")
        out = anim_strip(model, a.anim, a.frames, a.view, a.size, bg, a.ssaa)
    elif a.sheet:
        out = contact_sheet(model, a.size, a.anim, a.time, bg, a.ssaa)
    else:
        out = render(model, a.view, a.size, a.anim, a.time, ssaa=a.ssaa)
        if bg:
            base = Image.new("RGBA", out.size, bg)
            base.alpha_composite(out)
            out = base
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    out.save(a.output)
    print("wrote %s (%dx%d)" % (a.output, out.width, out.height))


if __name__ == "__main__":
    main()
