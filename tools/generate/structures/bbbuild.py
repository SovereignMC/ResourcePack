"""Builder: construct industrial-style structure models from scratch (see README.md, section bblib).

    from bblib import Builder, industrial_plinth, industrial_status_mast
    b = Builder("industrial_smelter")
    industrial_plinth(b)
    b.cylinder("shell", 0, 0, 3.4, 26, 9, "steel_plate", sides=8, group="frame")
    ...
    b.spin("fan", "y", period=2)
    b.save("bbmodels/structure_industrial_smelter.bbmodel")   # also runs states.py

Coordinates: model pixels, +X east, +Y up, +Z south (north = -Z), 16 px = 1 block, structure centre = (0, 0).
"""
import base64
import copy
import io
import json
import math
import os
import sys
import uuid as _uuid
import zlib

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bbmaterials  # noqa: E402
import render  # noqa: E402
import states  # noqa: E402
from bblib import FACES, Model, UUID_NS, _strip_private  # noqa: E402

ATLAS = 256
FOOT = 17.0
MAX_Y = 48.0
LAMP_BLOCK = (252, 252)  # 4x4 reserved atlas block for the status lamp colours (as states.py would pick)


class AtlasFull(Exception):
    pass


def _f(v):
    return states.fmt(v)


def _seed(s):
    return zlib.crc32(str(s).encode("utf-8")) & 0xFFFFFFFF


class Builder:
    def __init__(self, name, seed=None, variants=3, run_length=4.0, lamps_at=(0.0, 0.0)):
        """name: the bbmodel `name` (also the key of state_overrides/<name>.json), e.g. "industrial_smelter".
        variants: how many different noise variants of the same material/size are painted (atlas economy).
        run_length: length in seconds of the `running` loop; animation periods must divide it.
        lamps_at: (x, z) of the status mast if industrial_status_mast() is not called."""
        self.name = name
        self.seed = _seed(seed if seed is not None else name)
        self.variants = max(1, variants)
        self.run_length = float(run_length)
        self.lamps_at = tuple(lamps_at)
        self._n = 0
        self._terms = {}
        self._inputs, self._outputs, self._full_amp = [], [], []
        self._lamp_site = None
        d = {
            "meta": {"format_version": "5.0", "model_format": "free", "box_uv": False},
            "name": name, "model_identifier": name, "visible_box": [1, 1, 0], "variable_placeholders": "",
            "multi_file_ruleset": "", "variable_placeholder_buttons": [], "timeline_setups": [],
            "unhandled_root_fields": {}, "resolution": {"width": ATLAS, "height": ATLAS},
            "elements": [], "groups": [], "outliner": [],
            "textures": [{
                "name": name, "path": "", "folder": "", "namespace": "", "id": "0", "group": "", "scope": 0,
                "width": ATLAS, "height": ATLAS, "uv_width": ATLAS, "uv_height": ATLAS, "particle": False,
                "use_as_default": False, "layers_enabled": False, "sync_to_project": "", "file_format": "png",
                "render_mode": "default", "render_sides": "auto", "wrap_mode": "limited", "pbr_channel": "color",
                "fps": 7, "force_translucent": False, "frame_time": 1, "frame_order_type": "loop",
                "frame_order": "", "frame_interpolate": False, "visible": True, "internal": True, "saved": False,
                "uuid": str(_uuid.uuid5(UUID_NS, name + "|texture")), "source": ""}],
            "animations": [],
        }
        self.m = Model(d)
        self.group("root", parent=None)
        self.group("frame", parent="root")
        self.default_group = "frame"

    # ------------------------------------------------------------------ ids / groups
    def _uid(self, kind, name):
        self._n += 1
        return str(_uuid.uuid5(UUID_NS, "%s|%s|%s|%d" % (self.name, kind, name, self._n)))

    def group(self, name, parent="frame", origin=(0, 0, 0), rotation=(0, 0, 0)):
        """Create a group (bone) with pivot `origin` and static `rotation`; returns its name. Names must be unique."""
        if self.m.find(name) is not None and name in {g["name"] for g in self.m.d["groups"]}:
            return name
        u = self._uid("group", name)
        g = {"name": name, "uuid": u, "export": True, "locked": False, "scope": 0, "selected": False,
             "visibility": True, "_static": {"properties": {}, "temp_data": {}},
             "origin": [_f(x) for x in origin], "rotation": [_f(x) for x in rotation], "color": 0,
             "children": [], "reset": False, "shade": True, "mirror_uv": False, "autouv": 0, "isOpen": False,
             "primary_selected": False}
        g["origin"] = [float(x) if float(x) != int(float(x)) else int(float(x)) for x in g["origin"]]
        g["rotation"] = [float(x) if float(x) != int(float(x)) else int(float(x)) for x in g["rotation"]]
        self.m.d["groups"].append(g)
        node = {"uuid": u, "isOpen": False, "children": []}
        if parent is None:
            self.m.d["outliner"].append(node)
        else:
            self.m.node[self.m.group(parent)["uuid"]]["children"].append(node)
        self.m.groups[u] = g
        self.m.node[u] = node
        self.m.parent[u] = self.m.group(parent)["uuid"] if parent else None
        return name

    # ------------------------------------------------------------------ cubes
    def cube(self, name, frm, to, mat="steel_plate", group=None, rotation=None, origin=None, hide=(),
             faces=None, inflate=0):
        """Add a cube. mat: material name, or {"up": "...", "side": "...", "down": "...", "north": ..., "*": default}.
        hide: face names that get no texture (not drawn). faces: if given, only these faces are drawn.
        rotation: [x, y, z] degrees (Blockbench ZYX order) about `origin` (default box centre)."""
        group = group or self.default_group
        f0 = [float(x) for x in frm]
        t0 = [float(x) for x in to]
        f0, t0 = [min(a, b) for a, b in zip(f0, t0)], [max(a, b) for a, b in zip(f0, t0)]
        dx, dy, dz = (t0[i] - f0[i] for i in range(3))
        centre = [(a + b) / 2 for a, b in zip(f0, t0)]
        origin = list(origin) if origin is not None else centre
        u = self._uid("element", name)
        variant = (_seed("%d|%s" % (self.seed, name)) % self.variants)
        hide = set(hide)
        if f0[1] <= 0.01:
            hide.add("down")
        dims = {"north": (dx, dy), "south": (dx, dy), "east": (dz, dy), "west": (dz, dy), "up": (dx, dz), "down": (dx, dz)}
        fd = {}
        for fn in FACES:
            if fn in hide or (faces is not None and fn not in faces):
                fd[fn] = {"uv": [0, 0, 0, 0], "texture": None}
                continue
            mname = self._pick_mat(mat, fn)
            w, h = dims[fn]
            w, h = max(1, int(round(w))), max(1, int(round(h)))
            kind = "top" if fn == "up" else "bottom" if fn == "down" else "side"
            fd[fn] = {"uv": [0, 0, 0, 0], "texture": 0,
                      "_tile": {"mat": mname, "w": w, "h": h, "kind": kind, "variant": variant}}
        e = {"name": name, "box_uv": False, "render_order": "default", "locked": False, "export": True, "scope": 0,
             "allow_mirror_modeling": True, "from": [_nn(x) for x in f0], "to": [_nn(x) for x in t0],
             "autouv": 0, "color": 0}
        if inflate:
            e["inflate"] = inflate
        if rotation is not None and any(rotation):
            e["rotation"] = [_nn(x) for x in rotation]
        e["origin"] = [_nn(x) for x in origin]
        e["faces"] = fd
        e["type"] = "cube"
        e["uuid"] = u
        self.m.d["elements"].append(e)
        self.m.elements[u] = e
        gu = self.m.group(group)["uuid"]
        self.m.node[gu]["children"].append(u)
        self.m.parent[u] = gu
        return e

    @staticmethod
    def _pick_mat(mat, face):
        if isinstance(mat, str):
            return mat
        kind = "up" if face == "up" else "down" if face == "down" else "side"
        for k in (face, kind, "*"):
            if k in mat:
                return mat[k]
        raise KeyError("no material for face %s in %r" % (face, mat))

    # ------------------------------------------------------------------ editing shortcuts (new geometry)
    def radial4(self, sel, suffixes=("_r90", "_r180", "_r270")):
        """Original + clones at 90/180/270 about the model centre. Returns [orig, c90, c180, c270] (lists)."""
        return self.m.radial4(sel, suffixes)

    def mirror(self, sel, axis, **kw):
        return self.m.mirror(sel, axis, **kw)

    # ------------------------------------------------------------------ geometry helpers
    def cylinder(self, name, cx, cz, y0, y1, r, mat="steel_plate", sides=8, group=None, cap_mat=None,
                 hide=(), _origin_y=None):
        """Vertical n-gon prism (circumradius r) from n/2 rotated cubes; returns the list of elements.
        mat may be a dict (see cube); cap_mat overrides 'up'/'down'. sides must be 4 or even."""
        group = group or self.default_group
        n = sides
        if n == 4:
            return [self.cube(name, (cx - r, y0, cz - r), (cx + r, y1, cz + r), self._capped(mat, cap_mat), group, hide=hide)]
        if n % 2:
            raise ValueError("sides must be even")
        rho = r * math.cos(math.pi / n)
        s = 2 * rho * math.tan(math.pi / n) + 0.02
        els = []
        for k in range(n // 2):
            phi = k * 360.0 / n
            d = 0.02 * k
            els.append(self.cube("%s_%d" % (name, k), (cx - rho, y0, cz - s / 2), (cx + rho, y1 - d, cz + s / 2),
                                 self._capped(mat, cap_mat), group, rotation=(0, phi, 0) if phi else None,
                                 origin=(cx, (y0 + y1) / 2, cz), hide=set(hide) | {"north", "south"}))
        return els

    @staticmethod
    def _capped(mat, cap_mat):
        if cap_mat is None:
            return mat
        base = mat if isinstance(mat, dict) else {"*": mat}
        return dict(base, up=cap_mat, down=cap_mat)

    def pipe(self, name, centre, length, r, axis="x", mat="galvanized", sides=8, group=None, cap_mat=None):
        """Horizontal cylinder along `axis` ('x' or 'z') centred at `centre` (x, y, z). Builds a sub-group
        `<name>_t` (rotated) inside `group`; returns the sub-group name."""
        group = group or self.default_group
        cx, cy, cz = centre
        rot = {"x": (0, 0, 90), "z": (90, 0, 0)}[axis]
        gname = self.group(name + "_t", parent=group, origin=(cx, cy, cz), rotation=rot)
        self.cylinder(name, cx, cz, cy - length / 2, cy + length / 2, r, mat, sides, gname, cap_mat)
        return gname

    def ring(self, name, cx, cz, y0, y1, r_out, r_in, mat="steel_plate", sides=8, group=None, hide=()):
        """Hollow n-gon ring (r_out/r_in circumradii) made of slabs."""
        group = group or self.default_group
        n = sides
        ro, ri = r_out * math.cos(math.pi / n), r_in * math.cos(math.pi / n)
        L = 2 * ro * math.tan(math.pi / n) + 0.1
        els = []
        for i in range(n):
            phi = i * 360.0 / n
            els.append(self.cube("%s_%d" % (name, i), (cx + ri, y0, cz - L / 2), (cx + ro, y1, cz + L / 2), mat, group,
                                 rotation=(0, phi, 0) if phi else None, origin=(cx, (y0 + y1) / 2, cz),
                                 hide=set(hide) | {"north", "south"}))
        return els

    def taper(self, name, cx, cz, y0, y1, r0, r1, mat="steel_plate", steps=4, sides=8, group=None, cap_mat=None):
        """Stepped cone frustum (r0 at y0 -> r1 at y1) made of stacked prisms."""
        els = []
        for i in range(steps):
            a, b = y0 + (y1 - y0) * i / steps, y0 + (y1 - y0) * (i + 1) / steps
            r = r0 + (r1 - r0) * (i + 0.5) / steps
            els += self.cylinder("%s_%d" % (name, i), cx, cz, a, b, r, mat, sides, group, cap_mat if i == steps - 1 else None)
        return els

    def chimney(self, name, cx, cz, y0, y1, r_bottom, r_top, mat="steel_plate", rim_mat="dark_steel", sides=8, group=None):
        """Tapered stack with a rim collar and a lip."""
        els = self.taper(name, cx, cz, y0, y1 - 1.5, r_bottom, r_top, mat, 3, sides, group)
        els += self.cylinder(name + "_collar", cx, cz, y1 - 1.5, y1, r_top + 0.8, rim_mat, sides, group, cap_mat="dark_steel")
        els += self.ring(name + "_inner", cx, cz, y1 - 0.3, y1 + 0.2, r_top + 0.8, r_top - 0.5, "rusted_steel", sides, group)
        return els

    def hopper(self, name, cx, cz, y0, y1, r_top, r_bottom, mat="galvanized", rim_mat="dark_steel", sides=8, group=None):
        """Funnel: wide at the top, narrow outlet at the bottom, with a rim."""
        els = self.taper(name, cx, cz, y0, y1 - 1, r_bottom, r_top, mat, 4, sides, group)
        els += self.cylinder(name + "_rim", cx, cz, y1 - 1, y1, r_top + 0.6, rim_mat, sides, group)
        return els

    def tank(self, name, cx, cz, y0, y1, r, mat="galvanized", band_mat="dark_steel", sides=12, bands=2, group=None):
        """Vertical tank: body, domed top/bottom (two shrinking discs) and `bands` hoops."""
        els = self.cylinder(name, cx, cz, y0, y1, r, mat, sides, group)
        for i, f in enumerate((0.88, 0.62)):
            els += self.cylinder("%s_dome%d" % (name, i), cx, cz, y1 + i * 1.0, y1 + (i + 1) * 1.0, r * f, mat, sides, group)
        for i in range(bands):
            y = y0 + (y1 - y0) * (i + 1) / (bands + 1)
            els += self.cylinder("%s_band%d" % (name, i), cx, cz, y - 0.6, y + 0.6, r + 0.5, band_mat, sides, group)
        return els

    def beam(self, name, a, b, w=2.0, h=2.0, mat="steel_plate", profile="box", group=None):
        """Axis-aligned beam from point a to b (the longest axis), cross-section w x h centred on the line.
        profile 'I' builds web + flanges (cross-section h tall flanges)."""
        group = group or self.default_group
        a, b = [float(x) for x in a], [float(x) for x in b]
        ax = int(np.argmax([abs(b[i] - a[i]) for i in range(3)]))
        lo = [min(a[i], b[i]) for i in range(3)]
        hi = [max(a[i], b[i]) for i in range(3)]
        others = [i for i in range(3) if i != ax]
        # cross-section extents: w along the first non-long axis (prefer x/z), h along y when y is not the long axis
        ya = 1
        if ax == 1:
            wi, hi_ = 0, 2
        else:
            wi, hi_ = (0 if ax == 2 else 2), 1
        def box(wv, hv, off_h=0.0, wc=0.0):
            f, t = list(lo), list(hi)
            f[wi], t[wi] = a[wi] - wv / 2 + wc, a[wi] + wv / 2 + wc
            f[hi_], t[hi_] = a[hi_] - hv / 2 + off_h, a[hi_] + hv / 2 + off_h
            return f, t
        if profile == "I":
            ft = max(0.6, h * 0.25)
            els = []
            f, t = box(w, ft, h / 2 - ft / 2)
            els.append(self.cube(name + "_fl1", f, t, mat, group))
            f, t = box(w, ft, -h / 2 + ft / 2)
            els.append(self.cube(name + "_fl2", f, t, mat, group))
            f, t = box(max(0.6, w * 0.25), h - 2 * ft)
            els.append(self.cube(name + "_web", f, t, mat, group))
            return els
        f, t = box(w, h)
        return [self.cube(name, f, t, mat, group)]

    def strut(self, name, p0, p1, thick=1.0, depth=1.0, mat="steel_plate", group=None):
        """Diagonal brace between two points lying in an X-Y or Z-Y plane (rotated cube)."""
        group = group or self.default_group
        (x0, y0, z0), (x1, y1, z1) = p0, p1
        if abs(z1 - z0) < 1e-6:  # x-y plane: rotate about Z
            L = math.hypot(x1 - x0, y1 - y0)
            ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
            c = ((x0 + x1) / 2, (y0 + y1) / 2, z0)
            return self.cube(name, (c[0] - L / 2, c[1] - thick / 2, c[2] - depth / 2),
                             (c[0] + L / 2, c[1] + thick / 2, c[2] + depth / 2), mat, group,
                             rotation=(0, 0, ang), origin=c)
        if abs(x1 - x0) < 1e-6:  # z-y plane: rotate about X (positive x rotation lifts +z side down)
            L = math.hypot(z1 - z0, y1 - y0)
            ang = -math.degrees(math.atan2(y1 - y0, z1 - z0))
            c = (x0, (y0 + y1) / 2, (z0 + z1) / 2)
            return self.cube(name, (c[0] - depth / 2, c[1] - thick / 2, c[2] - L / 2),
                             (c[0] + depth / 2, c[1] + thick / 2, c[2] + L / 2), mat, group,
                             rotation=(ang, 0, 0), origin=c)
        raise ValueError("strut must lie in an X-Y or Z-Y plane")

    def truss(self, name, x0, z0, x1, z1, y0, y1, mat="steel_plate", post=1.2, brace=True, group=None, rail_mat=None):
        """Rectangular lattice tower/frame: 4 corner posts, rails at both ends and X braces on all four faces."""
        group = group or self.default_group
        rail_mat = rail_mat or mat
        p = post
        els = []
        for i, (x, z) in enumerate(((x0, z0), (x1 - p, z0), (x1 - p, z1 - p), (x0, z1 - p))):
            els.append(self.cube("%s_post%d" % (name, i), (x, y0, z), (x + p, y1, z + p), mat, group))
        for j, y in enumerate((y0, y1 - p)):
            els.append(self.cube("%s_railx%d" % (name, j), (x0, y, z0), (x1, y + p, z0 + p), rail_mat, group))
            els.append(self.cube("%s_railx%db" % (name, j), (x0, y, z1 - p), (x1, y + p, z1), rail_mat, group))
            els.append(self.cube("%s_railz%d" % (name, j), (x0, y, z0 + p), (x0 + p, y + p, z1 - p), rail_mat, group))
            els.append(self.cube("%s_railz%db" % (name, j), (x1 - p, y, z0 + p), (x1, y + p, z1 - p), rail_mat, group))
        if brace:
            t = 0.7
            ya, yb = y0 + p, y1 - p
            xa, xb = x0 + p, x1 - p
            za, zb = z0 + p, z1 - p
            els.append(self.strut(name + "_bn1", (xa, ya, z0 + p / 2), (xb, yb, z0 + p / 2), t, t, mat, group))
            els.append(self.strut(name + "_bn2", (xa, yb, z0 + p / 2), (xb, ya, z0 + p / 2), t, t, mat, group))
            els.append(self.strut(name + "_bs1", (xa, ya, z1 - p / 2), (xb, yb, z1 - p / 2), t, t, mat, group))
            els.append(self.strut(name + "_bs2", (xa, yb, z1 - p / 2), (xb, ya, z1 - p / 2), t, t, mat, group))
            els.append(self.strut(name + "_be1", (x1 - p / 2, ya, za), (x1 - p / 2, yb, zb), t, t, mat, group))
            els.append(self.strut(name + "_be2", (x1 - p / 2, yb, za), (x1 - p / 2, ya, zb), t, t, mat, group))
            els.append(self.strut(name + "_bw1", (x0 + p / 2, ya, za), (x0 + p / 2, yb, zb), t, t, mat, group))
            els.append(self.strut(name + "_bw2", (x0 + p / 2, yb, za), (x0 + p / 2, ya, zb), t, t, mat, group))
        return els

    # wall-relative placement: (u along the wall, v up, w outward) -> world box
    @staticmethod
    def _wall(facing, base):
        bx, by, bz = base

        def box(u0, u1, v0, v1, w0, w1):
            if facing == "north":
                f, t = (bx + u0, by + v0, bz - w1), (bx + u1, by + v1, bz - w0)
            elif facing == "south":
                f, t = (bx - u1, by + v0, bz + w0), (bx - u0, by + v1, bz + w1)
            elif facing == "east":
                f, t = (bx + w0, by + v0, bz + u0), (bx + w1, by + v1, bz + u1)
            else:
                f, t = (bx - w1, by + v0, bz - u1), (bx - w0, by + v1, bz - u0)
            return f, t
        return box

    def rivet_strip(self, name, base, facing="north", length=10, spacing=3, v=0, mat="steel_plate", group=None):
        """Row of round-ish bolt heads on a wall; base = point on the wall (centre of the strip start)."""
        box = self._wall(facing, base)
        els = []
        for i in range(max(1, int(length // spacing) + 1)):
            u = i * spacing
            f, t = box(u - 0.5, u + 0.5, v - 0.5, v + 0.5, 0, 0.6)
            els.append(self.cube("%s_%d" % (name, i), f, t, mat, group, hide={"down"}))
        return els

    def panel(self, name, base, width, height, facing="north", mat="steel_plate", frame_mat="dark_steel",
              inset=1.0, depth=0.6, group=None):
        """Framed recessed panel on a wall: base = bottom-left (u=0) point on the wall, `width` along u."""
        box = self._wall(facing, base)
        els = []
        i = inset
        for nm, (u0, u1, v0, v1) in (("b", (0, width, 0, i)), ("t", (0, width, height - i, height)),
                                    ("l", (0, i, i, height - i)), ("r", (width - i, width, i, height - i))):
            f, t = box(u0, u1, v0, v1, 0, depth)
            els.append(self.cube("%s_f%s" % (name, nm), f, t, frame_mat, group))
        f, t = box(i, width - i, i, height - i, 0, depth * 0.4)
        els.append(self.cube(name + "_in", f, t, mat, group))
        return els

    def ladder(self, name, base, height, facing="north", width=3.0, mat="galvanized", group=None):
        """Ladder against a wall; base = wall point at the foot, centred on u=0."""
        box = self._wall(facing, base)
        els = []
        for sgn, nm in ((-1, "l"), (1, "r")):
            u0 = sgn * width / 2 - 0.4
            f, t = box(u0, u0 + 0.8, 0, height, 0.8, 1.6)
            els.append(self.cube("%s_rail%s" % (name, nm), f, t, mat, group))
        for i in range(int(height // 2.5)):
            v = 1.0 + i * 2.5
            f, t = box(-width / 2, width / 2, v, v + 0.7, 1.0, 1.4)
            els.append(self.cube("%s_rung%d" % (name, i), f, t, mat, group))
        return els

    def railing(self, name, p0, p1, height=5.0, post=0.8, spacing=5.0, mat="warning_paint_yellow", group=None):
        """Handrail from p0 to p1 (x or z aligned) with posts, top rail and mid rail; p0.y is the walkway."""
        group = group or self.default_group
        x0, y0, z0 = p0
        x1, _, z1 = p1
        ax = 0 if abs(x1 - x0) >= abs(z1 - z0) else 2
        length = abs((x1 - x0) if ax == 0 else (z1 - z0))
        n = max(1, int(round(length / spacing)))
        els = []
        sgn = 1 if ((x1 - x0) if ax == 0 else (z1 - z0)) >= 0 else -1
        for i in range(n + 1):
            t = i * length / n * sgn
            x = x0 + (t if ax == 0 else 0)
            z = z0 + (t if ax == 2 else 0)
            els.append(self.cube("%s_p%d" % (name, i), (x - post / 2, y0, z - post / 2), (x + post / 2, y0 + height, z + post / 2), mat, group, hide={"down"}))
        lo_x, hi_x = sorted((x0, x1))
        lo_z, hi_z = sorted((z0, z1))
        pp = post / 2
        for j, yy in enumerate((height - 0.8, height * 0.5)):
            f = (lo_x - (pp if ax == 0 else 0.3), y0 + yy - 0.3, lo_z - (pp if ax == 2 else 0.3))
            t = (hi_x + (pp if ax == 0 else 0.3), y0 + yy + 0.3, hi_z + (pp if ax == 2 else 0.3))
            els.append(self.cube("%s_r%d" % (name, j), f, t, mat, group))
        return els

    def gear(self, name, centre, r, thickness=2.0, teeth=8, axis="z", mat="dark_steel", tooth_mat="steel_plate",
             hub_mat="brass", group=None):
        """Gear = disc + radial teeth + hub. Returns the OUTER group name (axis-aligned, pivot at `centre`):
        spin it with spin(outer, axis, period)."""
        group = group or self.default_group
        cx, cy, cz = centre
        outer = self.group(name, parent=group, origin=centre)
        rot = {"x": (0, 0, 90), "z": (90, 0, 0), "y": (0, 0, 0)}[axis]
        inner = self.group(name + "_t", parent=outer, origin=centre, rotation=rot)
        h2 = thickness / 2
        self.cylinder(name + "_disc", cx, cz, cy - h2, cy + h2, r, mat, 12 if r >= 5 else 8, inner)
        self.cylinder(name + "_hub", cx, cz, cy - h2 - 0.4, cy + h2 + 0.4, max(1.0, r * 0.3), hub_mat, 8, inner)
        tw = max(1.0, 2 * math.pi * r / teeth * 0.45)
        for i in range(teeth):
            phi = i * 360.0 / teeth
            self.cube("%s_tooth%d" % (name, i), (cx + r - 0.6, cy - h2, cz - tw / 2), (cx + r + 1.2, cy + h2, cz + tw / 2),
                      tooth_mat, inner, rotation=(0, phi, 0), origin=(cx, cy, cz), hide={"north", "south"})
        return outer

    def fan(self, name, centre, r, blades=4, axis="z", mat="galvanized", hub_mat="dark_steel", group=None, pitch=25):
        """Fan: hub + pitched blades. Returns the OUTER group (spin this)."""
        group = group or self.default_group
        cx, cy, cz = centre
        outer = self.group(name, parent=group, origin=centre)
        rot = {"x": (0, 0, 90), "z": (90, 0, 0), "y": (0, 0, 0)}[axis]
        inner = self.group(name + "_t", parent=outer, origin=centre, rotation=rot)
        self.cylinder(name + "_hub", cx, cz, cy - 1, cy + 1, max(1.2, r * 0.2), hub_mat, 8, inner)
        for i in range(blades):
            phi = i * 360.0 / blades
            self.cube("%s_blade%d" % (name, i), (cx + r * 0.2, cy - 0.25, cz - r * 0.22), (cx + r, cy + 0.25, cz + r * 0.22),
                      mat, inner, rotation=(pitch, phi, 0), origin=(cx, cy, cz))
        return outer

    def conveyor(self, name, x0, z0, x1, z1, y, width=5.0, belt_mat="rubber", frame_mat="steel_plate", group=None, rollers=True):
        """Belt conveyor between two points on a common x or z line at belt height y. Returns the belt
        group name `<name>_belt` (animate its position to scroll)."""
        group = group or self.default_group
        along_x = abs(x1 - x0) >= abs(z1 - z0)
        belt = self.group(name + "_belt", parent=group)
        lo_x, hi_x, lo_z, hi_z = min(x0, x1), max(x0, x1), min(z0, z1), max(z0, z1)
        hw = width / 2
        if along_x:
            zc = (z0 + z1) / 2
            self.cube(name + "_deck", (lo_x, y - 1.2, zc - hw), (hi_x, y - 0.2, zc + hw), frame_mat, group)
            self.cube(name + "_surface", (lo_x, y - 0.2, zc - hw + 0.6), (hi_x, y + 0.4, zc + hw - 0.6),
                      {"up": belt_mat, "*": belt_mat}, belt)
            for sgn, nm in ((-1, "a"), (1, "b")):
                zz = zc + sgn * hw
                self.cube("%s_side%s" % (name, nm), (lo_x, y - 1.2, zz - (0.6 if sgn > 0 else 0)),
                          (hi_x, y + 1.0, zz + (0 if sgn > 0 else 0.6)), frame_mat, group)
            if rollers:
                for i, x in enumerate((lo_x + 1.2, hi_x - 1.2)):
                    self.pipe("%s_roller%d" % (name, i), (x, y - 0.2, zc), width - 1.2, 1.2, "z", "dark_steel", 8, group)
            for i, x in enumerate(np.linspace(lo_x + 1, hi_x - 1, max(2, int((hi_x - lo_x) // 8) + 1))):
                self.cube("%s_leg%d" % (name, i), (x - 0.6, 0, zc - hw), (x + 0.6, y - 1.2, zc - hw + 1.0), frame_mat, group, hide={"down"})
                self.cube("%s_leg%db" % (name, i), (x - 0.6, 0, zc + hw - 1.0), (x + 0.6, y - 1.2, zc + hw), frame_mat, group, hide={"down"})
        else:
            xc = (x0 + x1) / 2
            self.cube(name + "_deck", (xc - hw, y - 1.2, lo_z), (xc + hw, y - 0.2, hi_z), frame_mat, group)
            self.cube(name + "_surface", (xc - hw + 0.6, y - 0.2, lo_z), (xc + hw - 0.6, y + 0.4, hi_z),
                      {"up": belt_mat, "*": belt_mat}, belt)
            for sgn, nm in ((-1, "a"), (1, "b")):
                xx = xc + sgn * hw
                self.cube("%s_side%s" % (name, nm), (xx - (0.6 if sgn > 0 else 0), y - 1.2, lo_z),
                          (xx + (0 if sgn > 0 else 0.6), y + 1.0, hi_z), frame_mat, group)
            if rollers:
                for i, z in enumerate((lo_z + 1.2, hi_z - 1.2)):
                    self.pipe("%s_roller%d" % (name, i), (xc, y - 0.2, z), width - 1.2, 1.2, "x", "dark_steel", 8, group)
            for i, z in enumerate(np.linspace(lo_z + 1, hi_z - 1, max(2, int((hi_z - lo_z) // 8) + 1))):
                self.cube("%s_leg%d" % (name, i), (xc - hw, 0, z - 0.6), (xc - hw + 1.0, y - 1.2, z + 0.6), frame_mat, group, hide={"down"})
                self.cube("%s_leg%db" % (name, i), (xc + hw - 1.0, 0, z - 0.6), (xc + hw, y - 1.2, z + 0.6), frame_mat, group, hide={"down"})
        return belt

    def pipe_run(self, name, points, r=1.0, mat="galvanized", joint_mat="dark_steel", sides=8, group=None, flange=True):
        """Pipe through a list of (x, y, z) points; each leg must be axis-aligned. Elbows are joint blocks
        slightly larger than the pipe; flanges are added at both ends."""
        group = group or self.default_group
        els = []
        pts = [tuple(float(c) for c in p) for p in points]
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            d = [b[k] - a[k] for k in range(3)]
            ax = [k for k in range(3) if abs(d[k]) > 1e-6]
            if len(ax) != 1:
                raise ValueError("pipe_run legs must be axis-aligned: %r -> %r" % (a, b))
            ax = ax[0]
            L = abs(d[ax])
            c = [(a[k] + b[k]) / 2 for k in range(3)]
            if ax == 1:
                els += self.cylinder("%s_%d" % (name, i), c[0], c[2], min(a[1], b[1]), max(a[1], b[1]), r, mat, sides, group)
            else:
                g = self.pipe("%s_%d" % (name, i), c, L, r, "x" if ax == 0 else "z", mat, sides, group)
        for i in range(1, len(pts) - 1):
            x, y, z = pts[i]
            els.append(self.cube("%s_elbow%d" % (name, i), (x - r * 1.15, y - r * 1.15, z - r * 1.15), (x + r * 1.15, y + r * 1.15, z + r * 1.15), joint_mat, group))
        if flange:
            for i, idx in enumerate((0, len(pts) - 1)):
                x, y, z = pts[idx]
                nxt = pts[1] if idx == 0 else pts[-2]
                ax = [k for k in range(3) if abs(nxt[k] - pts[idx][k]) > 1e-6][0]
                s = 1.5 * r
                f = [x - s, y - s, z - s]
                t = [x + s, y + s, z + s]
                th = 0.6
                f[ax], t[ax] = (pts[idx][ax] - th / 2, pts[idx][ax] + th / 2)
                els.append(self.cube("%s_flange%d" % (name, i), f, t, joint_mat, group))
        return els

    # ------------------------------------------------------------------ animation helpers (write `running`)
    def _check_period(self, period):
        n = self.run_length / period
        if abs(n - round(n)) > 1e-6 or round(n) < 1:
            raise ValueError("period %s must divide run_length %s" % (period, self.run_length))

    def _add(self, bone, channel, axis, kind, fn, period):
        self.m.group(bone)
        self._terms.setdefault((bone, channel), []).append({"axis": "xyz".index(axis), "kind": kind, "fn": fn, "period": period})

    def spin(self, bone, axis="y", period=2.0, direction=1):
        """Continuous rotation of `bone` about world axis `axis`, one turn per `period` seconds."""
        self._check_period(period)
        self._add(bone, "rotation", axis, "spin", lambda t, p=period, d=direction: 360.0 * d * t / p, period)

    def oscillate(self, bone, channel, axis, amplitude, period, phase=0.0):
        """Sine oscillation: rotation (deg) / position (px) around 0, scale around 1."""
        self._check_period(period)
        base = 1.0 if channel == "scale" else 0.0
        self._add(bone, channel, axis, "osc",
                  lambda t, a=amplitude, p=period, ph=phase, b=base: b + a * math.sin(2 * math.pi * (t / p + ph)), period)

    def bob(self, bone, amplitude, period, phase=0.0):
        """Vertical bobbing (position y)."""
        self.oscillate(bone, "position", "y", amplitude, period, phase)

    def piston(self, bone, axis, stroke, period, phase=0.0):
        """Reciprocating stroke 0..stroke along `axis` (smooth, never negative)."""
        self._check_period(period)
        self._add(bone, "position", axis, "osc",
                  lambda t, s=stroke, p=period, ph=phase: s * (1 - math.cos(2 * math.pi * (t / p + ph))) / 2, period)

    def pulse_scale(self, bone, lo, hi, period, phase=0.0):
        """Uniform scale pulse between lo and hi."""
        self._check_period(period)
        for ax in "xyz":
            self._add(bone, "scale", ax, "osc",
                      lambda t, l=lo, h=hi, p=period, ph=phase: l + (h - l) * (1 - math.cos(2 * math.pi * (t / p + ph))) / 2, period)

    def rise(self, bone, height, period, phase=0.0, scale_from=0.6, scale_to=1.4):
        """Looping 'smoke puff': position y 0 -> height while scaling scale_from -> scale_to, then restart."""
        self._check_period(period)
        self._add(bone, "position", "y", "saw", lambda f, h=height: h * f, period)
        for ax in "xyz":
            self._add(bone, "scale", ax, "saw", lambda f, a=scale_from, b=scale_to: a + (b - a) * f, period)
        self._terms[(bone, "position")][-1]["phase"] = phase
        for t in self._terms[(bone, "scale")][-3:]:
            t["phase"] = phase

    def smoke(self, name, x, y, z, puffs=3, rise=9.0, period=None, size=2.5, group=None, mat="galvanized"):
        """`puffs` smoke bones named smoke_<name>_<i> (hidden by states.py outside `running`)."""
        group = group or self.default_group
        period = period or self.run_length
        names = []
        for i in range(puffs):
            g = self.group("smoke_%s_%d" % (name, i), parent=group, origin=(x, y, z))
            s = size * (0.8 + 0.15 * i)
            self.cube("smoke_%s_puff%d" % (name, i), (x - s / 2, y, z - s / 2), (x + s / 2, y + s, z + s / 2),
                      {"*": mat}, g, hide={"down"})
            self.rise(g, rise, period, phase=i / puffs)
            names.append(g)
        return names

    def input_bones(self, names):
        """Declare the bones that wobble in the NEEDS INPUT state (written to state_overrides)."""
        self._inputs = list(names)

    def full_amplitude(self, names):
        """Bones whose motion keeps its full amplitude in idle/no_power (only slowed), e.g. show/hide scale toggles."""
        self._full_amp = list(names)

    def output_bones(self, names):
        """Declare the bones that pulse in the OUTPUT FULL state (written to state_overrides)."""
        self._outputs = list(names)

    # ------------------------------------------------------------------ status lamps
    def status_lamps(self, x, z, top):
        """Create the `status` group + six lamp bones with lens plates on all four sides of a 6x6 housing whose
        base sits at `top` (housing y = top+3 .. top+7, see industrial_status_mast). Idempotent."""
        if "status" in {g["name"] for g in self.m.d["groups"]}:
            return
        self._lamp_site = (x, z, top)
        self.group("status", parent="root", origin=(x, top, z))
        boxes = states.lens_boxes(x, z, top)
        for i, name in enumerate(states.LAMPS):
            px = (LAMP_BLOCK[0] + (i + 2) % 4, LAMP_BLOCK[1] + (i + 2) // 4)
            self.group(name, parent="status", origin=(x, top + 5, z))
            for side, (f, t) in boxes.items():
                e = self.cube("%s_%s" % (name, side), f, t, "steel_plate", name, hide=set(FACES))
                e["faces"] = states.faces_with_uv(px[0], px[1], 0)
                for fc in e["faces"].values():
                    fc["texture"] = 0

    # ------------------------------------------------------------------ finalize / save
    def _tiles(self):
        tiles = {}
        for e in self.m.d["elements"]:
            for fn, f in e["faces"].items():
                t = f.get("_tile")
                if t:
                    tiles.setdefault((t["mat"], t["kind"], t["w"], t["h"], t["variant"]), None)
        return tiles

    def finalize(self):
        """Pack and paint all face tiles into the atlas, set uv/texture; returns the model data dict."""
        keys = sorted(self._tiles(), key=lambda k: (-k[3], -k[2], k))
        occ = np.zeros((ATLAS, ATLAS), bool)
        occ[LAMP_BLOCK[1] - 1:, LAMP_BLOCK[0] - 1:] = True
        shelves = []  # [y, height, x_cursor]
        pos = {}
        y_next = 0
        for k in keys:
            w, h = k[2], k[3]
            placed = None
            for s in shelves:
                if h <= s[1] and s[2] + w + 1 <= ATLAS:
                    x = s[2]
                    while x + w + 1 <= ATLAS and occ[s[0]:s[0] + h + 1, x:x + w + 1].any():
                        x += 1
                    if x + w + 1 <= ATLAS:
                        placed = (x, s[0])
                        s[2] = x + w + 1
                        break
            if placed is None:
                if y_next + h + 1 > ATLAS:
                    raise AtlasFull("atlas full: %d tiles, area %d of %d texels; reduce variants/detail" % (
                        len(keys), int(sum(k2[2] * k2[3] for k2 in keys)), ATLAS * ATLAS))
                shelves.append([y_next, h, w + 1])
                placed = (0, y_next)
                y_next += h + 1
            pos[k] = placed
            occ[placed[1]:placed[1] + h + 1, placed[0]:placed[0] + w + 1] = True
        arr = np.zeros((ATLAS, ATLAS, 4), np.uint8)
        for k, (x, y) in pos.items():
            mat, kind, w, h, variant = k
            rng = np.random.default_rng(_seed("%d|%s|%s|%d|%d|%d" % (self.seed, mat, kind, w, h, variant)))
            tile = bbmaterials.paint(mat, w, h, rng, kind)
            arr[y:y + h, x:x + w] = tile
            if x + w < ATLAS:
                arr[y:y + h, x + w] = tile[:, -1]
            if y + h < ATLAS:
                arr[y + h, x:x + w] = tile[-1, :]
        # lamp block colours (states.py repaints identical values)
        for i, name in enumerate(states.LAMPS):
            px = (LAMP_BLOCK[0] + (i + 2) % 4, LAMP_BLOCK[1] + (i + 2) // 4)
            arr[px[1], px[0]] = list(states.LAMP_RGB[name]) + [255]
        for e in self.m.d["elements"]:
            for fn, f in e["faces"].items():
                t = f.get("_tile")
                if t:
                    x, y = pos[(t["mat"], t["kind"], t["w"], t["h"], t["variant"])]
                    f["uv"] = [x, y, x + t["w"], y + t["h"]]
                    f["texture"] = 0
        self.m.d["textures"][0]["source"] = states.encode_tex(arr)
        self._atlas = arr
        self._build_running()
        self.stats = {"tiles": len(keys), "tile_area": int(sum(k[2] * k[3] for k in keys)),
                      "cubes": len(self.m.d["elements"]), "groups": len(self.m.d["groups"])}
        return _strip_private(self.m.d)

    def _build_running(self):
        d = self.m.d
        L = self.run_length
        names = {g["uuid"]: g["name"] for g in d["groups"]}
        by_name = {g["name"]: g["uuid"] for g in d["groups"]}
        anim = {"uuid": str(_uuid.uuid5(UUID_NS, self.name + "|running")), "name": "running", "loop": "loop",
                "override": False, "length": L, "snapping": 24, "selected": True, "group_name": "", "scope": 0,
                "anim_time_update": "", "blend_weight": "", "start_delay": "", "loop_delay": "", "animators": {}}
        kfs_by = {}
        for (bone, channel), terms in self._terms.items():
            gu = by_name[bone]
            default = 1.0 if channel == "scale" else 0.0
            kinds = {t["kind"] for t in terms}
            times = None
            if "saw" in kinds:
                ts = [t for t in terms if t["kind"] == "saw"]
                per = ts[0]["period"]
                cyc = int(round(L / per))
                eps = 1.0 / 48
                ph = ts[0].get("phase", 0.0)
                # fraction f(t) = (t/per + ph) mod 1 ; emit keys at t = 0, each wrap (just before/at), and L
                def frac(t):
                    return ((t / per + ph) % 1.0)
                wraps = [((1 - ph) % 1.0) * per + c * per for c in range(cyc + 1)]
                wraps = sorted(w for w in wraps if 0 < w < L - 1e-9)
                times = sorted(set([0.0, L] + [w - eps for w in wraps] + wraps))
                times = [t for t in times if -1e-9 <= t <= L + 1e-9]
                def val(axis_terms, t):
                    out = []
                    for ax in range(3):
                        tt = [x for x in terms if x["axis"] == ax]
                        if not tt:
                            out.append(default)
                            continue
                        f = frac(t)
                        if t in wraps:
                            f = 0.0
                        out.append(sum(x["fn"](f) for x in tt))
                    return out
                keys = [(t, val(terms, t)) for t in times]
            elif kinds == {"spin"} and len(terms) == 1:
                t0 = terms[0]
                keys = [(0.0, [default] * 3), (L, [default] * 3)]
                keys[0][1][t0["axis"]] = t0["fn"](0.0)
                keys[1][1][t0["axis"]] = t0["fn"](L)
            else:
                dt = min(t["period"] for t in terms) / 16.0
                n = int(round(L / dt))
                keys = []
                for i in range(n + 1):
                    t = i * L / n
                    v = [default] * 3
                    for ax in range(3):
                        tt = [x for x in terms if x["axis"] == ax]
                        if tt:
                            v[ax] = sum(x["fn"](t) for x in tt) - (len(tt) - 1) * default
                    keys.append((t, v))
            lst = []
            for i, (t, v) in enumerate(keys):
                x, y, z = (_f(c) for c in v)
                lst.append(states.kf_make(channel, x, y, z, round(t, 6), "linear", bone, "running", i,
                                          uniform=(x == y == z) if channel == "scale" else None))
            kfs_by[gu] = kfs_by.get(gu, []) + lst
        for g in d["groups"]:
            an = {"name": g["name"], "type": "bone", "rotation_global": False, "quaternion_interpolation": False}
            if g["uuid"] in kfs_by:
                an["keyframes"] = kfs_by[g["uuid"]]
            anim["animators"][g["uuid"]] = an
        d["animations"] = [anim]

    def check_footprint(self, verbose=True):
        data = self.finalize()
        rm = render.Model(copy.deepcopy(data))
        fs = rm.faces()
        fs = [f for f in fs if not f["group"].startswith(("smoke", "status", "lamp_"))
              and not f["element"].startswith("mast_")] or fs
        pts = np.concatenate([f["c"] for f in fs])
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        warns = []
        if lo[0] < -FOOT or hi[0] > FOOT or lo[2] < -FOOT or hi[2] > FOOT:
            warns.append("footprint X %.1f..%.1f Z %.1f..%.1f exceeds +-%g px" % (lo[0], hi[0], lo[2], hi[2], FOOT))
        if hi[1] > MAX_Y:
            warns.append("height %.1f exceeds %g px" % (hi[1], MAX_Y))
        if lo[1] < -0.5:
            warns.append("geometry below y=0 (%.1f)" % lo[1])
        if verbose:
            for w in warns:
                print("bblib: WARNING: " + w, file=sys.stderr)
        return warns, (lo, hi)

    def sheet(self, path, size=256, anim=None, time=0.0):
        data = self.finalize()
        rm = render.Model(copy.deepcopy(data))
        render.contact_sheet(rm, size, anim, time).save(path)
        return path

    def render(self, view="iso_ne", size=256, **kw):
        data = self.finalize()
        return render.render(render.Model(copy.deepcopy(data)), view, size, **kw)

    def save(self, path, run_states=True):
        """Write the bbmodel, write state_overrides/<name>.json if bones were declared, run states.py on it."""
        if "status" not in {g["name"] for g in self.m.d["groups"]}:
            warns, (lo, hi) = self.check_footprint(False)
            industrial_status_mast(self, self.lamps_at[0], self.lamps_at[1], float(hi[1]))
        self.check_footprint(True)
        data = self.finalize()
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(json.dumps(data, separators=(",", ":"), ensure_ascii=False))
        if self._inputs or self._outputs or self._full_amp:
            os.makedirs(states.OVERRIDES_DIR, exist_ok=True)
            ov = {}
            if self._inputs:
                ov["input_bones"] = self._inputs
            if self._outputs:
                ov["output_bones"] = self._outputs
            if self._full_amp:
                ov["full_amplitude"] = self._full_amp
            with open(os.path.join(states.OVERRIDES_DIR, self.name + ".json"), "w", encoding="utf-8", newline="\n") as f:
                json.dump(ov, f, indent=2)
                f.write("\n")
        if run_states:
            states.main([path, "--write"])
        print("bblib: saved %s (%s)" % (path, self.stats))
        return path


def _nn(v):
    v = round(float(v), 5)
    return int(v) if v == int(v) else v


# ----------------------------------------------------------------------------- shared industrial kit

def industrial_plinth(b, group="frame"):
    """32x32 concrete pad (3.4 px tall) with a pinwheel hazard-striped edge and bolted corner plates;
    identical from all four sides (4-fold). Machine geometry should start at y = 3.4."""
    b.group("plinth", parent=group)
    b.cube("pad", (-16, 0, -16), (16, 2.4, 16), {"up": "concrete", "*": "concrete"}, "plinth")
    b.cube("pad_top", (-15, 2.4, -15), (15, 3.0, 15), {"up": "concrete", "*": "dark_steel"}, "plinth")
    s = b.cube("hazard_edge", (-16, 2.4, -16), (14, 3.4, -14), {"up": "hazard_stripe", "*": "dark_steel"}, "plinth")
    bolt_base = b.cube("corner_plate", (-16, 2.4, -16), (-12, 3.8, -12), {"up": "steel_plate", "*": "steel_plate"}, "plinth")
    bolts = []
    for i, (x, z) in enumerate(((-15, -15), (-13, -15), (-15, -13), (-13, -13))):
        bolts.append(b.cube("corner_bolt%d" % i, (x - 0.5, 3.8, z - 0.5), (x + 0.5, 4.3, z + 0.5), "galvanized", "plinth", hide={"down"}))
    b.radial4([s, bolt_base] + bolts)
    return "plinth"


def industrial_status_mast(b, x=0.0, z=0.0, base=None, group="status"):
    """Short steel mast carrying the status lamps (replaces states.py's auto housing). base = y of the mast
    foot (default: the highest geometry so far at the centre). Housing is 6x4x6 at base+3..base+7 with a
    lens plate on each side and a hood above each lens; the six lamp bones are created by status_lamps()."""
    if base is None:
        warns, (lo, hi) = b.check_footprint(False)
        base = float(hi[1])
    b.status_lamps(x, z, base)
    g = group
    b.cube("mast_base", (x - 2, base, z - 2), (x + 2, base + 0.8, z + 2), "dark_steel", g, hide={"down"})
    b.cube("mast_post", (x - 1, base + 0.8, z - 1), (x + 1, base + 3, z + 1), "steel_plate", g)
    b.cube("mast_housing", (x - 3, base + 3, z - 3), (x + 3, base + 7, z + 3), "dark_steel", g)
    b.cube("mast_roof", (x - 3.5, base + 7, z - 3.5), (x + 3.5, base + 7.8, z + 3.5), "steel_plate", g)
    b.cube("mast_cap", (x - 1, base + 7.8, z - 1), (x + 1, base + 9, z + 1), "galvanized", g, hide={"down"})
    hood = b.cube("mast_hood", (x - 2, base + 6.3, z - 3.7), (x + 2, base + 6.9, z - 3), "warning_paint_yellow", g)
    b.radial4([hood], ("_90", "_180", "_270"))
    return base
