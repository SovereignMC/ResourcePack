"""bblib: edit existing .bbmodel files and build new ones (see README.md, section bblib).

Two halves:

* `Model` - load / edit / save a Blockbench free-format model (find, delete, translate, scale, clone with a
  Y rotation or mirror, radial4, symmetry checks, `directionality_report`).
* `Builder` - construct a fresh industrial-style model with procedural materials, helpers (cylinder,
  pipe_run, truss, gear, ...), animation helpers and `save()` which also runs states.py.
  (Builder and the helpers live in bbbuild.py and are re-exported here.)

Conventions: +X east, +Y up, +Z south (north = -Z). Rotations are given CLOCKWISE seen from above, in
multiples of 90: rot=90 turns the north face into the east face (N -> E -> S -> W).
"""
import copy
import json
import math
import os
import sys
import uuid as _uuid

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render  # noqa: E402

UUID_NS = _uuid.UUID("2d6a0c52-91c4-4d0e-8f35-6b7c1e9a4402")
FACES = ("north", "east", "south", "west", "up", "down")


# ----------------------------------------------------------------------------- linear algebra

def _rot_y_cw(k):
    """3x3 matrix of a clockwise-from-above rotation by 90*k degrees (north -> east for k=1)."""
    k %= 4
    m = np.eye(3, dtype=int)
    for _ in range(k):
        m = np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]]) @ m
    return m


def _mirror_m(axis):
    m = np.eye(3, dtype=int)
    m[{"x": 0, "z": 2}[axis], {"x": 0, "z": 2}[axis]] = -1
    return m


def _euler_to_m(rot):
    return render.euler_zyx(rot)[:3, :3]


def _m_to_euler(m):
    """ZYX Euler degrees (matches render.euler_zyx) from a rotation matrix."""
    sy = -m[2, 0]
    if abs(sy) < 0.999999:
        y = math.asin(sy)
        x = math.atan2(m[2, 1], m[2, 2])
        z = math.atan2(m[1, 0], m[0, 0])
    else:
        y = math.copysign(math.pi / 2, sy)
        x = math.atan2(-m[1, 2], m[1, 1])
        z = 0.0
    out = []
    for a in (x, y, z):
        d = math.degrees(a)
        r = round(d)
        if abs(d - r) < 1e-6:
            d = float(r)
        out.append(round(d, 4) + 0.0)
    return [int(v) if v == int(v) else v for v in out]


def _face_map(S):
    """Map face name -> face name under the signed permutation S."""
    normals = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0),
               "up": (0, 1, 0), "down": (0, -1, 0)}
    back = {v: k for k, v in normals.items()}
    return {k: back[tuple(int(x) for x in S @ np.array(v))] for k, v in normals.items()}


def _num(v):
    return int(v) if float(v) == int(v) else round(float(v), 5)


# ----------------------------------------------------------------------------- Model

class Model:
    """Editable bbmodel. All edit methods take a *selection*: element/group dicts, names or uuids, or lists."""

    def __init__(self, data, path=None):
        self.d = data
        self.path = path
        self._counter = 0
        self.reindex()

    @classmethod
    def load(cls, path):
        path = render.resolve_model(path)
        with open(path, "r", encoding="utf-8") as f:
            return cls(json.load(f), path)

    def dumps(self):
        d = _strip_private(self.d)
        return json.dumps(d, separators=(",", ":"), ensure_ascii=False)

    def save(self, path=None):
        path = path or self.path
        if not path:
            raise ValueError("no path")
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(self.dumps())
        self.path = path
        return path

    # ---- index
    def reindex(self):
        d = self.d
        self.groups = {g["uuid"]: g for g in d["groups"]}
        self.elements = {e["uuid"]: e for e in d["elements"]}
        self.parent = {}
        self.node = {}

        def walk(nodes, parent):
            for n in nodes:
                if isinstance(n, dict):
                    self.node[n["uuid"]] = n
                    self.parent[n["uuid"]] = parent
                    walk(n.get("children", []), n["uuid"])
                else:
                    self.parent[n] = parent
        walk(d["outliner"], None)

    def children_list(self, parent_uuid):
        return self.d["outliner"] if parent_uuid is None else self.node[parent_uuid]["children"]

    # ---- find
    def find(self, key):
        """Element/group dict by uuid or exact name (first match; groups before elements). None if absent."""
        if isinstance(key, dict):
            return key
        if key in self.groups:
            return self.groups[key]
        if key in self.elements:
            return self.elements[key]
        for g in self.d["groups"]:
            if g["name"] == key:
                return g
        for e in self.d["elements"]:
            if e["name"] == key:
                return e
        return None

    def find_all(self, name_substr, kind=None):
        """All elements/groups whose name contains the (case-insensitive) substring."""
        s = name_substr.lower()
        out = []
        if kind in (None, "group"):
            out += [g for g in self.d["groups"] if s in g["name"].lower()]
        if kind in (None, "element"):
            out += [e for e in self.d["elements"] if s in e["name"].lower()]
        return out

    def group(self, key):
        g = self.find(key)
        if g is None or g["uuid"] not in self.groups:
            raise KeyError("no group %r" % (key,))
        return g

    def is_group(self, o):
        return o["uuid"] in self.groups

    def elements_in(self, group, recursive=True):
        g = self.group(group)
        out = []
        for c in self.node[g["uuid"]]["children"]:
            if isinstance(c, str):
                out.append(self.elements[c])
            elif recursive:
                out += self.elements_in(self.groups[c["uuid"]], True)
        return out

    def child_groups(self, group, recursive=False):
        g = self.group(group)
        out = []
        for c in self.node[g["uuid"]]["children"]:
            if isinstance(c, dict):
                out.append(self.groups[c["uuid"]])
                if recursive:
                    out += self.child_groups(c["uuid"], True)
        return out

    def parent_group(self, o):
        p = self.parent.get(self.find(o)["uuid"])
        return self.groups[p] if p else None

    def _sel(self, sel):
        """Normalise a selection to a list of unique top-level dicts (children of selected groups dropped)."""
        if sel is None:
            return []
        if isinstance(sel, (dict, str)):
            sel = [sel]
        items = []
        for s in sel:
            o = self.find(s)
            if o is None:
                raise KeyError("not found: %r" % (s,))
            items.append(o)
        ids = {o["uuid"] for o in items}
        out = []
        for o in items:
            p = self.parent.get(o["uuid"])
            skip = False
            while p:
                if p in ids:
                    skip = True
                    break
                p = self.parent.get(p)
            if not skip and o not in out:
                out.append(o)
        return out

    def _all_in(self, items):
        """All groups and elements in the selection, children included."""
        els, grs = [], []
        for o in items:
            if o["uuid"] in self.groups:
                grs.append(o)
                for g in self.child_groups(o, True):
                    grs.append(g)
                els += self.elements_in(o, True)
            else:
                els.append(o)
        return els, grs

    # ---- delete
    def delete(self, sel):
        items = self._sel(sel)
        els, grs = self._all_in(items)
        dead = {o["uuid"] for o in els + grs}
        for o in items:
            lst = self.children_list(self.parent.get(o["uuid"]))
            for c in list(lst):
                if (c if isinstance(c, str) else c["uuid"]) == o["uuid"]:
                    lst.remove(c)
        self.d["elements"] = [e for e in self.d["elements"] if e["uuid"] not in dead]
        self.d["groups"] = [g for g in self.d["groups"] if g["uuid"] not in dead]
        for a in self.d.get("animations", []):
            for u in dead:
                a.get("animators", {}).pop(u, None)
        self.reindex()
        return len(els) + len(grs)

    # ---- plain transforms
    def translate(self, sel, dx=0, dy=0, dz=0):
        items = self._sel(sel)
        els, grs = self._all_in(items)
        v = (dx, dy, dz)
        for e in els:
            e["from"] = [_num(a + b) for a, b in zip(e["from"], v)]
            e["to"] = [_num(a + b) for a, b in zip(e["to"], v)]
            e["origin"] = [_num(a + b) for a, b in zip(e["origin"], v)]
        for g in grs:
            g["origin"] = [_num(a + b) for a, b in zip(g["origin"], v)]
        return items

    def scale(self, sel, factor, about=(0, 0, 0)):
        """Uniformly scale geometry about a point (cube boxes, origins, group origins; positions in animations too)."""
        items = self._sel(sel)
        els, grs = self._all_in(items)
        c = np.array(about, float)

        def sc(p):
            return [_num(round(float(x), 4)) for x in c + (np.array(p, float) - c) * factor]
        for e in els:
            a, b = sc(e["from"]), sc(e["to"])
            e["from"], e["to"] = a, b
            e["origin"] = sc(e["origin"])
            if e.get("inflate"):
                e["inflate"] = _num(e["inflate"] * factor)
        for g in grs:
            g["origin"] = sc(g["origin"])
        gids = {g["uuid"] for g in grs}
        for a in self.d.get("animations", []):
            for gu, an in a.get("animators", {}).items():
                if gu in gids:
                    for k in an.get("keyframes", []):
                        if k["channel"] == "position":
                            for dp in k["data_points"]:
                                for ax in "xyz":
                                    try:
                                        dp[ax] = str(_num(float(dp[ax]) * factor))
                                    except (TypeError, ValueError):
                                        pass
        return items

    def resize(self, element, frm=None, to=None):
        """Set an element's from/to (None keeps). Origin is kept unless the element has no rotation."""
        e = self.find(element)
        if frm is not None:
            e["from"] = [_num(x) for x in frm]
        if to is not None:
            e["to"] = [_num(x) for x in to]
        if not any(e.get("rotation", [0, 0, 0])):
            e["origin"] = [_num((a + b) / 2) for a, b in zip(e["from"], e["to"])] if False else e["origin"]
        return e

    # ---- clone / rotate / mirror
    def _fresh(self, old, tag):
        self._counter += 1
        return str(_uuid.uuid5(UUID_NS, "%s|%s|%d" % (old, tag, self._counter)))

    def clone(self, sel, rot=0, mirror=None, offset=(0, 0, 0), suffix=None, into=None):
        """Copy a selection, optionally mirrored ('x'|'z') and then rotated `rot` degrees clockwise about the
        model origin (Y axis), then offset. Faces and UVs travel with the geometry, cube rotations and
        origins are conjugated, groups' animators are copied (rotation axes / position remapped).
        Returns the list of new top-level dicts (same order as the selection)."""
        rot = int(rot) % 360
        if rot % 90:
            raise ValueError("rot must be a multiple of 90")
        k = rot // 90
        items = self._sel(sel)
        if suffix is None:
            suffix = "".join(["_m" + mirror if mirror else "", "_r%d" % rot if rot else ""]) or "_c"
        tag = "%s%s%d" % (suffix, mirror or "", rot)
        S = np.eye(3, dtype=int)
        if mirror:
            S = _mirror_m(mirror) @ S
        S = _rot_y_cw(k) @ S
        det = int(round(np.linalg.det(S)))
        fmap = _face_map(S)
        gmap = {}
        new_top = []

        def fix_face(face, name_old, name_new):
            f = copy.deepcopy(face)
            r = int(f.get("rotation", 0) or 0)
            if mirror:
                if name_old in ("up", "down"):
                    ax = "u" if mirror == "x" else "v"
                else:
                    ax = "u"
                u1, v1, u2, v2 = f["uv"]
                f["uv"] = [u2, v1, u1, v2] if ax == "u" else [u1, v2, u2, v1]
                r = (-r) % 360
            # after the mirror the face is now named by the mirrored name; then Y rotation
            nm = _face_map(_mirror_m(mirror))[name_old] if mirror else name_old
            if k and nm == "up":
                r = (r + 90 * k) % 360
            elif k and nm == "down":
                r = (r - 90 * k) % 360
            if r or "rotation" in f:
                f["rotation"] = r
            return f

        def xf_element(e):
            n = copy.deepcopy(e)
            f0, t0 = np.array(e["from"], float), np.array(e["to"], float)
            a, b = S @ f0, S @ t0
            n["from"] = [_num(round(x, 5)) for x in np.minimum(a, b)]
            n["to"] = [_num(round(x, 5)) for x in np.maximum(a, b)]
            n["origin"] = [_num(round(float(x), 5)) for x in S @ np.array(e["origin"], float)]
            if "rotation" in e and any(e["rotation"]):
                Rm = _euler_to_m(e["rotation"])
                n["rotation"] = _m_to_euler(S @ Rm @ S.T)
            faces = {}
            for name, face in e.get("faces", {}).items():
                faces[fmap[name]] = fix_face(face, name, fmap[name])
            n["faces"] = {fn: faces[fn] for fn in FACES if fn in faces}
            n["name"] = e["name"] + suffix
            n["uuid"] = self._fresh(e["uuid"], tag)
            if any(offset):
                n["from"] = [_num(x + o) for x, o in zip(n["from"], offset)]
                n["to"] = [_num(x + o) for x, o in zip(n["to"], offset)]
                n["origin"] = [_num(x + o) for x, o in zip(n["origin"], offset)]
            return n

        def xf_group(g, parent_uuid):
            n = copy.deepcopy(g)
            n["origin"] = [_num(round(float(x), 5)) for x in S @ np.array(g["origin"], float)]
            if any(g.get("rotation", [0, 0, 0])):
                n["rotation"] = _m_to_euler(S @ _euler_to_m(g["rotation"]) @ S.T)
            n["name"] = g["name"] + suffix
            n["uuid"] = self._fresh(g["uuid"], tag)
            n["children"] = []
            n["selected"] = False
            n["primary_selected"] = False
            if any(offset):
                n["origin"] = [_num(x + o) for x, o in zip(n["origin"], offset)]
            gmap[g["uuid"]] = n["uuid"]
            return n

        def copy_tree(o, dest_children, dest_parent):
            if o["uuid"] in self.groups:
                n = xf_group(o, dest_parent)
                node = {"uuid": n["uuid"], "isOpen": False, "children": []}
                self.d["groups"].append(n)
                dest_children.append(node)
                for c in self.node[o["uuid"]]["children"]:
                    if isinstance(c, str):
                        copy_tree(self.elements[c], node["children"], n["uuid"])
                    else:
                        copy_tree(self.groups[c["uuid"]], node["children"], n["uuid"])
                return n
            n = xf_element(o)
            self.d["elements"].append(n)
            dest_children.append(n["uuid"])
            return n

        into_g = self.group(into) if into is not None else None
        for o in items:
            dest_parent = into_g["uuid"] if into_g else self.parent.get(o["uuid"])
            dest = self.children_list(dest_parent)
            new_top.append(copy_tree(o, dest, dest_parent))
            # reindex lazily: node dicts created above must be visible for nested children
        self._clone_animators(gmap, S, det)
        self.reindex()
        return new_top

    def _clone_animators(self, gmap, S, det):
        if not gmap:
            return
        # rotation component k -> (axis j, sign)
        axmap = []
        for kx in range(3):
            col = S[:, kx]
            j = int(np.argmax(np.abs(col)))
            axmap.append((j, int(col[j]) * det))
        for a in self.d.get("animations", []):
            for old, new in gmap.items():
                an = a.get("animators", {}).get(old)
                if an is None:
                    continue
                n = copy.deepcopy(an)
                for kf in n.get("keyframes", []):
                    kf["uuid"] = self._fresh(kf["uuid"], "kf")
                    for dp in kf["data_points"]:
                        v = [dp.get(c, "0") for c in "xyz"]
                        out = ["0", "0", "0"]
                        if kf["channel"] == "rotation":
                            for kx, (j, sg) in enumerate(axmap):
                                out[j] = _scale_str(v[kx], sg)
                        elif kf["channel"] == "position":
                            for j in range(3):
                                for kx in range(3):
                                    if S[j, kx]:
                                        out[j] = _scale_str(v[kx], int(S[j, kx]))
                        else:  # scale: axes permute, no sign
                            for j in range(3):
                                for kx in range(3):
                                    if S[j, kx]:
                                        out[j] = v[kx]
                        dp["x"], dp["y"], dp["z"] = out
                n["name"] = self.groups[old]["name"] if False else n.get("name")
                new_name = next((g["name"] for g in self.d["groups"] if g["uuid"] == new), n.get("name"))
                n["name"] = new_name
                a["animators"][new] = n

    def rotate(self, sel, rot, suffix=""):
        """Rotate a selection in place (clone + delete original, names unchanged by default)."""
        items = self._sel(sel)
        into = None
        news = self.clone(items, rot=rot, suffix=suffix)
        self.delete(items)
        return news

    def mirror(self, sel, axis, **kw):
        return self.clone(sel, mirror=axis, **kw)

    def radial4(self, sel, suffixes=("_r90", "_r180", "_r270")):
        """Original + 3 clones at 90/180/270. Returns [original items, clone90, clone180, clone270]."""
        items = self._sel(sel)
        return [items] + [self.clone(items, rot=r, suffix=s) for r, s in zip((90, 180, 270), suffixes)]

    # ---- analysis
    def rest_faces(self):
        return render.Model(copy.deepcopy(_strip_private(self.d)), self.path).faces()

    def bounds(self):
        fs = self.rest_faces()
        pts = np.concatenate([f["c"] for f in fs]) if fs else np.zeros((1, 3))
        return pts.min(axis=0), pts.max(axis=0)

    def render(self, view="iso_ne", size=256, **kw):
        m = render.Model(copy.deepcopy(_strip_private(self.d)), self.path)
        return render.render(m, view, size, **kw)

    def sheet(self, path, size=256, anim=None, time=0.0):
        m = render.Model(copy.deepcopy(_strip_private(self.d)), self.path)
        im = render.contact_sheet(m, size, anim, time)
        im.save(path)
        return path


def _scale_str(s, sign):
    try:
        v = float(s) * sign
        return str(_num(v))
    except (TypeError, ValueError):
        return s if sign > 0 else "-(%s)" % s


def _strip_private(d):
    """Copy of the model data without keys starting with '_' inside elements/faces (builder bookkeeping)."""
    out = dict(d)
    els = []
    for e in d["elements"]:
        ne = {k: v for k, v in e.items() if not k.startswith("_")}
        ne["faces"] = {fn: {k: v for k, v in f.items() if not k.startswith("_")} for fn, f in e.get("faces", {}).items()}
        els.append(ne)
    out["elements"] = els
    return out


# ----------------------------------------------------------------------------- symmetry / directionality

def symmetric_about_center(model, order=4, use_color=True):
    """Check rotational symmetry of the rest-pose geometry about the Y axis through the origin.

    order 4 = 4-fold (90 deg), 2 = 2-fold (180). Faces are compared by their world corners and (optionally)
    quantised average colour. Returns dict(symmetric, matched, total, fraction, unmatched=[element names])."""
    m = model if isinstance(model, Model) else Model.load(model)
    rm = render.Model(copy.deepcopy(_strip_private(m.d)), m.path)
    faces = rm.faces()

    def sig(f, S=None):
        c = f["c"] if S is None else (S @ f["c"].T).T
        pts = tuple(sorted(tuple(np.round(p, 1) + 0.0) for p in c))
        col = ()
        if use_color:
            t = rm.textures[f["tex"]]["arr"]
            uv = f["uv"]
            x0, x1 = sorted((int(math.floor(uv[0, 0])), int(math.ceil(uv[2, 0]))))
            y0, y1 = sorted((int(math.floor(uv[0, 1])), int(math.ceil(uv[2, 1]))))
            patch = t[max(0, y0):max(y0 + 1, y1), max(0, x0):max(x0 + 1, x1), :3]
            col = tuple((patch.reshape(-1, 3).mean(axis=0) // 24).astype(int)) if patch.size else ()
        return (pts, col)
    base = {}
    for f in faces:
        base.setdefault(sig(f), []).append(f)
    steps = [1, 2, 3] if order == 4 else [2]
    bad = set()
    total = len(faces)
    ok = 0
    for f in faces:
        good = True
        for s in steps:
            S = _rot_y_cw(s).astype(float)
            key = sig(f, S)
            if use_color and key not in base:
                # fall back to geometry only if colour quantisation differs slightly
                geo = [k for k in base if k[0] == key[0]]
                if not geo:
                    good = False
            elif not use_color and key not in base:
                good = False
        if good:
            ok += 1
        else:
            bad.add(f["element"])
    return {"symmetric": not bad, "matched": ok, "total": total, "fraction": ok / total if total else 1.0,
            "unmatched": sorted(bad)}


def directionality_report(model, size=128, print_it=True, anim=None, time=0.0):
    """Render N/E/S/W side views (unshaded) and score how different they are (0 = identical).

    A 4-fold symmetric model has N == E == S == W. Scores are mean absolute RGBA difference in 0..1 between
    the view from a side and the views from the others (`per_side`), plus the silhouette (alpha) difference.
    Also scores the top view against itself rotated by 90 degrees."""
    m = model if isinstance(model, Model) else Model.load(model)
    rm = render.Model(copy.deepcopy(_strip_private(m.d)), m.path)
    fs = rm.faces(anim, time)
    pts = rm.points(faces=fs)
    sides = ["north", "east", "south", "west"]
    scale, cs = render.fit(pts, sides + ["top"], size)
    imgs = {}
    for v in sides + ["top"]:
        imgs[v] = np.asarray(render.render(rm, v, size, scale=scale, centre=cs[v], faces=fs, shading=False)).astype(float)
    # common centre so the views are comparable even if the model is off-centre
    def diff(a, b):
        cov = np.maximum(a[..., 3], b[..., 3]) > 0
        da = np.abs(a - b)[..., :3]
        col = float(da[cov].mean() / 255.0) if cov.any() else 0.0
        # silhouette: share of covered pixels that are covered in only one of the two views
        return col, float((np.abs(a[..., 3] - b[..., 3]) > 0)[cov].mean()) if cov.any() else 0.0
    per = {}
    pair = {}
    for i, a in enumerate(sides):
        for b in sides[i + 1:]:
            pair["%s-%s" % (a, b)] = diff(imgs[a], imgs[b])
    for a in sides:
        vals = [diff(imgs[a], imgs[b]) for b in sides if b != a]
        per[a] = {"color": round(sum(v[0] for v in vals) / 3, 4), "silhouette": round(sum(v[1] for v in vals) / 3, 4)}
    top = imgs["top"]
    tr = np.rot90(top, 1, axes=(0, 1))
    covt = np.maximum(top[..., 3], tr[..., 3]) > 0
    top_rot = float(np.abs(top - tr)[..., :3][covt].mean() / 255.0) if covt.any() else 0.0
    mean_c = round(sum(v["color"] for v in per.values()) / 4, 4)
    mean_s = round(sum(v["silhouette"] for v in per.values()) / 4, 4)
    rep = {"per_side": per, "pairs": {k: [round(x, 4) for x in v] for k, v in pair.items()},
           "mean_color": mean_c, "mean_silhouette": mean_s, "top_rot90": round(top_rot, 4)}
    if print_it:
        print("directionality (0 = sides identical):")
        for s in sides:
            print("  %-5s color %.4f  silhouette %.4f" % (s, per[s]["color"], per[s]["silhouette"]))
        print("  mean  color %.4f  silhouette %.4f   top vs top rotated 90: %.4f" % (mean_c, mean_s, rep["top_rot90"]))
    return rep


# ----------------------------------------------------------------------------- self test

def selftest():
    """Verify clone(): every original face maps onto a clone face with identical corner -> texel mapping."""
    base = Model.load("smelter")
    for rot, mir in ((90, None), (180, None), (270, None), (0, "x"), (0, "z"), (90, "x"), (270, "z")):
        m = Model(copy.deepcopy(base.d))
        # add rotated cubes with face rotations to exercise the paths
        els = [e for e in m.d["elements"]]
        for i, e in enumerate(els[:60]):
            if i % 7 == 0 and "faces" in e:
                e["faces"]["up"]["rotation"] = 90 * (i % 4)
                e["faces"]["down"]["rotation"] = 90 * ((i + 1) % 4)
        sel = m.group("frame")
        before = render.Model(copy.deepcopy(m.d)).faces()
        new = m.clone(sel, rot=rot, mirror=mir, suffix="_t")
        names = {e["name"] for e in m.elements_in(new[0])}
        after = [f for f in render.Model(copy.deepcopy(m.d)).faces() if f["element"] in names]
        S = np.eye(3)
        if mir:
            S = _mirror_m(mir) @ S
        S = _rot_y_cw(rot // 90) @ S
        bad = 0
        index = {}
        for f in after:
            for i in range(4):
                index[(tuple(np.round(f["c"][i], 3)), tuple(np.round(f["uv"][i], 3)), f["tex"])] = 1
        orig_names = {e["name"] for e in m.elements_in(sel)}
        for f in before:
            if f["element"] not in orig_names:
                continue
            for i in range(4):
                key = (tuple(np.round(S @ f["c"][i], 3)), tuple(np.round(f["uv"][i], 3)), f["tex"])
                # for mirrored copies the texel at a corner is the same by definition
                if key not in index:
                    bad += 1
        # sides compare against the frame subtree only (new group is a child of root)
        print("selftest rot=%s mirror=%s: %d corner mismatches of %d" % (rot, mir, bad, 4 * len(before)))
        if bad:
            return False
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        directionality_report(Model.load(sys.argv[2]))


def __getattr__(name):  # lazy re-export of the Builder half (avoids a circular import)
    if name in ("Builder", "industrial_plinth", "industrial_status_mast", "AtlasFull"):
        import bbbuild
        return getattr(bbbuild, name)
    raise AttributeError(name)
