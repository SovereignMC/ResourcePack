"""Shared builder for SovereignMC gun models.

Every gun is authored as a small Python script (``tools/generate/guns/<gun>.py``) that uses
this module to build ONE source of truth (a rig with player-skin arms ``pra_*``/``prfa_*``/
``pla_*``/``plfa_*`` and all animations) and write these outputs:

* ``assets/weapons/models/item/<id>.json`` + ``assets/weapons/textures/item/gun/<id>.png`` -
  vanilla item model built from the ``gun`` bone (GUI, ground, third person, frames).
* ``assets/weapons/{models,textures}/item/objmc/<id>`` + the gun's ``feather.json`` entry - first-person
  viewmodel baked for the sgvm core shader (see ``viewmodel_bake.py``).
* ``tools/generate/guns/preview/<id>_*.png`` - offline renders (side/top/front orthographic,
  first-person hip + ADS, animation contact sheet) so a script can be checked without
  Blockbench.

Coordinate system (Blockbench / BetterModel, 1 unit = 1 px = 1/16 block):

* Camera (the player's eye) sits at the origin looking down **-Z**. **+X is screen right**,
  **+Y is up**. Everything in the viewmodel is expressed in this camera space.
* Rotations are right-handed degrees, Euler order ZYX (three.js ``'ZYX'``: R = Rz*Ry*Rx), the
  same convention Blockbench uses for group rotations. ``+X`` rotation tilts the muzzle (-Z)
  **up**. All angles passed to this module are TRUE rotations; the conversion to
  Blockbench's animation keyframe sign convention happens on export.
* Guns are modelled muzzle toward -Z, bore along Z, the gun's own right side at +X.

Rig standard (created by ``GunModel``)::

    viewmodel                 root of everything visible; state animations move it
      gun                     pivot at the grip (rest yaw HIP_YAW); all gun geometry lives below
        magazine / bolt / ... moving parts (create with add_part)
        muzzle                empty locator at the muzzle
          glow_flash          muzzle flash, hidden (scale 0) except in shoot animations
      pra_right_arm > prfa_right_forearm > pri_right_item
      pla_left_arm  > plfa_left_forearm  > pli_left_item
    camera                    empty, reserved for a camera-roll shader

Bone names must not start with another BetterModel tag token followed by ``_``
(``b h hi p sp tag mtag ptag glow li ri pli pri ph pra prfa pla plfa phip pw pc prl prfl pll
plfl cape``) unless the tag is intended.
"""

from __future__ import annotations

import base64
import io
import json
import math
import random
import zlib
import uuid as uuidlib
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]  # ResourcePack/
PREVIEW_DIR = Path(__file__).resolve().parent / "preview"

DENSITY = 4          # texels per model px
ARM_UPPER = 5.5      # pra pivot -> prfa pivot (BetterModel steve rig)
ARM_LOWER = 5.625    # prfa pivot -> hand (pri item bone)
ALLOWED_ITEM_ANGLES = (-45.0, -22.5, 0.0, 22.5, 45.0)
HIP_GRIP = (3.2, -4.8, -8.5)   # where every gun's `grip` point sits at the hip
HIP_YAW = 6.0                  # gun rest yaw about +Y (muzzle toward screen centre), about the grip
TEX_SIZE = 128                 # every gun texture is exactly this size
DENSITIES = (4, 3.5, 3.0, 2.5, 2.0)   # texels per model px, tried in order until the faces fit
FOV_V = 70.0                   # vertical FOV of the offline preview / shoulder visibility check

# --------------------------------------------------------------------------------------
# Small vector / matrix helpers (pure python, 3x3 rotation + translation)
# --------------------------------------------------------------------------------------


def v_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v_mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def v_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def v_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def v_len(a):
    return math.sqrt(v_dot(a, a))


def v_norm(a):
    n = v_len(a)
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-9 else (0.0, 0.0, 0.0)


def m_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def m_vec(m, v):
    return (
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    )


def m_t(m):
    return [[m[j][i] for j in range(3)] for i in range(3)]


def rot_x(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def rot_y(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def rot_z(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def euler_zyx(r):
    """Rotation matrix for Blockbench Euler degrees (x, y, z), order ZYX: R = Rz*Ry*Rx."""
    return m_mul(rot_z(r[2]), m_mul(rot_y(r[1]), rot_x(r[0])))


class Xf:
    """Affine transform: p -> R*p + t."""

    __slots__ = ("r", "t")

    def __init__(self, r=None, t=(0.0, 0.0, 0.0)):
        self.r = r or [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        self.t = t

    def apply(self, p):
        return v_add(m_vec(self.r, p), self.t)

    def then(self, inner: "Xf") -> "Xf":
        """self * inner (apply inner first)."""
        return Xf(m_mul(self.r, inner.r), v_add(m_vec(self.r, inner.t), self.t))

    @staticmethod
    def pivot(origin, rot_deg, offset=(0.0, 0.0, 0.0)) -> "Xf":
        """T(origin + offset) * R * T(-origin)."""
        r = euler_zyx(rot_deg)
        t = v_add(v_sub(origin, m_vec(r, origin)), offset)
        return Xf(r, t)


def _uid():
    return str(uuidlib.uuid4())


# --------------------------------------------------------------------------------------
# Materials and procedural texture painting
# --------------------------------------------------------------------------------------

def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


@dataclass
class Material:
    base: str
    kind: str = "metal"         # metal | wood | polymer | rubber | glass | brass | emissive | skin | cloth
    noise: float = 0.05         # per-texel brightness jitter
    edge: float = -0.18         # 1-texel border brightness change (bevel); 0 disables
    wear: float = 0.0           # 0..1 chance-scale of bright worn texels on metal edges


MATERIALS: dict[str, Material] = {
    "steel": Material("#474a52", "metal", 0.06, -0.22, 0.35),
    "steel_dark": Material("#2c2e33", "metal", 0.05, -0.25, 0.25),
    "parkerized": Material("#555858", "metal", 0.08, -0.2, 0.2),
    "gunmetal": Material("#666a72", "metal", 0.06, -0.2, 0.3),
    "aluminium": Material("#969ba2", "metal", 0.05, -0.15, 0.2),
    "olive": Material("#697046", "polymer", 0.05, -0.18, 0.0),
    "wood": Material("#7c472d", "wood", 0.04, -0.2, 0.0),
    "wood_light": Material("#9d603f", "wood", 0.04, -0.2, 0.0),
    "wood_dark": Material("#5a3422", "wood", 0.04, -0.2, 0.0),
    "walnut": Material("#684732", "wood", 0.04, -0.2, 0.0),
    "birch": Material("#b68c5f", "wood", 0.04, -0.18, 0.0),
    "bakelite": Material("#75341f", "polymer", 0.04, -0.2, 0.0),
    "polymer": Material("#3a3b3f", "polymer", 0.04, -0.18, 0.0),
    "polymer_green": Material("#576143", "polymer", 0.04, -0.18, 0.0),
    "rubber": Material("#2a2a2a", "rubber", 0.06, -0.1, 0.0),
    "brass": Material("#c29842", "brass", 0.05, -0.2, 0.0),
    "copper": Material("#a96339", "brass", 0.05, -0.2, 0.0),
    "glass": Material("#1d3550", "glass", 0.0, 0.0, 0.0),
    "flash": Material("#ffd27a", "emissive", 0.0, 0.0, 0.0),
    "leather": Material("#6a482d", "cloth", 0.06, -0.15, 0.0),
    "canvas": Material("#706c4a", "cloth", 0.07, -0.12, 0.0),
    "skin": Material("#c99a7a", "skin", 0.03, 0.0, 0.0),
}


NOISE_SCALE = 0.4   # per-texel noise multiplier (smooth, not speckled)
EDGE_SCALE = 0.5    # bevel strength multiplier


def _shade(rgb, f):
    if f >= 0:
        return tuple(min(255, int(c + (255 - c) * f)) for c in rgb)
    return tuple(max(0, int(c * (1 + f))) for c in rgb)


def _paint_face(img: Image.Image, rect, mat: Material, grain_along_u: bool, rng: random.Random,
                face_dir: str):
    x1, y1, x2, y2 = rect
    w, h = x2 - x1, y2 - y1
    base = _hex(mat.base)
    px = img.load()
    if mat.kind == "emissive":
        cx, cy = (w - 1) / 2, (h - 1) / 2
        for j in range(h):
            for i in range(w):
                d = math.hypot((i - cx) / max(cx, 0.5), (j - cy) / max(cy, 0.5))
                a = max(0.0, 1.0 - d)
                col = _shade(base, 0.6 * a)
                px[x1 + i, y1 + j] = (*col, int(255 * min(1.0, 0.25 + a)))
        return
    # directional pre-light (very soft; the game shades faces too)
    light = {"up": 0.06, "down": -0.08, "north": 0.0, "south": 0.0, "east": 0.02, "west": -0.02}[face_dir]
    phase = rng.random() * 10
    for j in range(h):
        for i in range(w):
            f = light + rng.uniform(-mat.noise, mat.noise) * NOISE_SCALE
            if mat.kind == "wood":
                t = (j if grain_along_u else i) + 0.35 * math.sin(((i if grain_along_u else j) + phase) * 0.7)
                f += 0.09 * math.sin(t * 2.1 + phase) + 0.015 * math.sin(t * 5.3)
            elif mat.kind == "metal":
                f += 0.04 * (0.5 - j / max(h - 1, 1))
            elif mat.kind == "brass":
                f += 0.12 * (0.5 - j / max(h - 1, 1))
            elif mat.kind == "glass":
                d = (i / max(w - 1, 1)) + (j / max(h - 1, 1))
                f += 0.45 if 0.35 < d < 0.6 else 0.0
            elif mat.kind == "rubber":
                f += 0.03 if (i + j) % 2 == 0 else -0.02
            edge = i == 0 or j == 0 or i == w - 1 or j == h - 1
            if edge and w >= 3 and h >= 3 and mat.edge:
                f += mat.edge * EDGE_SCALE
            px[x1 + i, y1 + j] = (*_shade(base, f), 255)


# --------------------------------------------------------------------------------------
# Model elements
# --------------------------------------------------------------------------------------

FACE_AXES = {  # face -> (u axis, v axis) in model axes, used for UV size + grain direction
    "north": (0, 1), "south": (0, 1), "east": (2, 1), "west": (2, 1), "up": (0, 2), "down": (0, 2),
}


@dataclass
class Cube:
    name: str
    frm: tuple
    to: tuple
    group: "Group"
    material: str
    origin: tuple | None = None
    rotation: tuple = (0.0, 0.0, 0.0)
    inflate: float = 0.0
    item_model: bool = True     # include in the vanilla item model (gun subtree only)
    faces_off: tuple = ()       # faces to skip (never visible)
    uuid: str = field(default_factory=_uid)
    uv: dict = field(default_factory=dict)

    def size(self):
        return tuple(self.to[i] - self.frm[i] for i in range(3))

    def center(self):
        return tuple((self.frm[i] + self.to[i]) / 2 for i in range(3))

    def corners(self):
        f, t = self.frm, self.to
        inf = self.inflate
        f = (f[0] - inf, f[1] - inf, f[2] - inf)
        t = (t[0] + inf, t[1] + inf, t[2] + inf)
        return [(x, y, z) for x in (f[0], t[0]) for y in (f[1], t[1]) for z in (f[2], t[2])]


@dataclass
class Group:
    name: str
    origin: tuple
    parent: "Group | None" = None
    rotation: tuple = (0.0, 0.0, 0.0)   # TRUE rest rotation (degrees)
    hidden: bool = False                # scale 0 in every animation that does not key its scale
    uuid: str = field(default_factory=_uid)
    children: list = field(default_factory=list)   # Groups and Cubes, in outliner order

    def path(self):
        g, out = self, []
        while g:
            out.append(g)
            g = g.parent
        return list(reversed(out))

    def is_under(self, other: "Group"):
        g = self
        while g:
            if g is other:
                return True
            g = g.parent
        return False


# --------------------------------------------------------------------------------------
# Animation
# --------------------------------------------------------------------------------------


def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


EASES = {
    "linear": lambda x: x,
    "smooth": smoothstep,
    "in": lambda x: x * x,
    "out": lambda x: 1 - (1 - x) * (1 - x),
    "back": lambda x: 1 + 2.70158 * (x - 1) ** 3 + 1.70158 * (x - 1) ** 2,  # overshoot
}


@dataclass
class Channel:
    """Keyframes for one bone channel. Values are TRUE offsets from the rest pose:
    rotation = degrees added to the rest Euler angles, position = px translation,
    scale = multiplier (1 = rest)."""

    keys: list = field(default_factory=list)   # (time, (x,y,z))

    def add(self, t, v):
        self.keys = [k for k in self.keys if abs(k[0] - t) > 1e-6]
        self.keys.append((round(t, 4), tuple(float(c) for c in v)))
        self.keys.sort(key=lambda k: k[0])

    def sample(self, t, default):
        if not self.keys:
            return default
        if t <= self.keys[0][0]:
            return self.keys[0][1]
        for (t0, a), (t1, b) in zip(self.keys, self.keys[1:]):
            if t0 <= t <= t1:
                x = 0 if t1 == t0 else (t - t0) / (t1 - t0)
                return tuple(a[i] + (b[i] - a[i]) * x for i in range(3))
        return self.keys[-1][1]


class Animation:
    """One BetterModel animation. Author with ``key`` / ``ease`` on bones; arms are solved by
    IK with ``hands`` (call ``GunModel.solve_arms`` - ``GunModel.finish`` does it)."""

    def __init__(self, model: "GunModel", name, length, loop="once"):
        self.model = model
        self.name = name
        self.length = float(length)
        self.loop = loop          # once | loop | hold
        self.channels: dict[tuple[str, str], Channel] = {}
        # hand targets: side -> list of (time, target) ; target = ("grip", None) |
        #   ("point", (x,y,z) viewmodel space) | ("bone", bone_name, (x,y,z) rest-space point)
        self.hand_keys: dict[str, list] = {"right": [], "left": []}
        self.hand_pole: dict[str, tuple] = {}

    # -- authoring -------------------------------------------------------------------
    def ch(self, bone, channel) -> Channel:
        if bone not in self.model.groups:
            raise KeyError(f"{self.name}: unknown bone {bone!r}")
        return self.channels.setdefault((bone, channel), Channel())

    def key(self, bone, t, rot=None, pos=None, scale=None):
        """Set an absolute (relative-to-rest) pose at time t for the given channels."""
        if rot is not None:
            self.ch(bone, "rotation").add(t, rot)
        if pos is not None:
            self.ch(bone, "position").add(t, pos)
        if scale is not None:
            s = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
            self.ch(bone, "scale").add(t, s)
        return self

    def ease(self, bone, t0, t1, rot0=None, rot1=None, pos0=None, pos1=None, curve="smooth", steps=None):
        """Eased motion between two poses, expanded into dense linear keys (BetterModel and the
        preview evaluate linear keys identically)."""
        steps = steps or max(2, int(round((t1 - t0) / 0.05)))
        fn = EASES[curve]
        for i in range(steps + 1):
            x = i / steps
            e = fn(x)
            t = t0 + (t1 - t0) * x
            if rot0 is not None:
                self.ch(bone, "rotation").add(t, tuple(rot0[k] + (rot1[k] - rot0[k]) * e for k in range(3)))
            if pos0 is not None:
                self.ch(bone, "position").add(t, tuple(pos0[k] + (pos1[k] - pos0[k]) * e for k in range(3)))
        return self

    def hand(self, side, t, target):
        """Hand target at time t. target:
        'grip' / 'support'      -> the gun's grip / support point (follows the gun bone)
        ('bone', name, point)   -> a rest-space point carried by that bone (e.g. the magazine)
        (x, y, z)               -> a fixed viewmodel-space point (e.g. off-screen at a pouch)
        Targets are interpolated between keys (positions are blended in viewmodel space)."""
        self.hand_keys[side] = [k for k in self.hand_keys[side] if abs(k[0] - t) > 1e-6]
        self.hand_keys[side].append((round(t, 4), target))
        self.hand_keys[side].sort(key=lambda k: k[0])
        return self

    def pole(self, side, direction):
        self.hand_pole[side] = direction
        return self

    # -- evaluation ------------------------------------------------------------------
    def offsets(self, bone, t):
        rot = (0.0, 0.0, 0.0)
        pos = (0.0, 0.0, 0.0)
        scl = (1.0, 1.0, 1.0)
        if (bone, "rotation") in self.channels:
            rot = self.channels[(bone, "rotation")].sample(t, rot)
        if (bone, "position") in self.channels:
            pos = self.channels[(bone, "position")].sample(t, pos)
        if (bone, "scale") in self.channels:
            scl = self.channels[(bone, "scale")].sample(t, scl)
        return rot, pos, scl


# --------------------------------------------------------------------------------------
# The model
# --------------------------------------------------------------------------------------


class GunModel:
    def __init__(self, gun_id: str, display_name: str, texture_size: int | None = None):
        self.id = gun_id
        self.display_name = display_name
        self.texture_size = texture_size
        self.density = DENSITY
        self.groups: dict[str, Group] = {}
        self.cubes: list[Cube] = []
        self.anims: dict[str, Animation] = {}
        self.points: dict[str, tuple] = {}     # named rest-space points (grip, support, sights...)
        self.flags: dict[str, object] = {}
        self.root_order: list = []

        self.viewmodel = self.group("viewmodel", (0, 0, 0), None)
        self.gun = self.group("gun", (0, 0, 0), self.viewmodel)
        self.camera = self.group("camera", (0, 0, 0), None)

    # -- building --------------------------------------------------------------------
    def group(self, name, origin, parent: Group | str | None = "gun", rotation=(0, 0, 0),
              hidden=False) -> Group:
        if name in self.groups:
            raise ValueError(f"duplicate group {name}")
        if isinstance(parent, str):
            parent = self.groups[parent]
        g = Group(name, tuple(float(c) for c in origin), parent, tuple(float(c) for c in rotation), hidden)
        self.groups[name] = g
        (parent.children if parent else self.root_order).append(g)
        return g

    def part(self, name, origin, parent="gun", hidden=False):
        """A moving part bone (magazine, bolt, trigger, cover, ...) under the gun. hidden=True:
        invisible (scale 0) in every animation that does not key its scale."""
        return self.group(name, origin, parent, hidden=hidden)

    def box(self, name, frm, to, material, group="gun", rotation=None, origin=None,
            inflate=0.0, item_model=True, faces_off=()) -> Cube:
        if material not in MATERIALS:
            raise KeyError(f"unknown material {material}")
        g = self.groups[group] if isinstance(group, str) else group
        frm = tuple(float(c) for c in frm)
        to = tuple(float(c) for c in to)
        frm, to = tuple(min(a, b) for a, b in zip(frm, to)), tuple(max(a, b) for a, b in zip(frm, to))
        c = Cube(name, frm, to, g, material,
                 tuple(float(v) for v in origin) if origin else None,
                 tuple(float(v) for v in rotation) if rotation else (0.0, 0.0, 0.0),
                 inflate, item_model, tuple(faces_off))
        if c.origin is None:
            c.origin = c.center()
        self.cubes.append(c)
        g.children.append(c)
        return c

    def cbox(self, name, center, size, material, **kw) -> Cube:
        """Box from centre + size."""
        f = tuple(center[i] - size[i] / 2 for i in range(3))
        t = tuple(center[i] + size[i] / 2 for i in range(3))
        return self.box(name, f, t, material, **kw)

    def octa(self, name, cx, cy, a, z0, z1, mat, group="gun", item_model=True):
        """True octagonal bar along Z with apothem a (4 cubes, end faces staggered)."""
        z0, z1 = min(z0, z1), max(z0, z1)
        s = a * math.tan(math.radians(22.5))
        zm = (z0 + z1) / 2
        kw = dict(group=group, item_model=item_model)
        return [
            self.box(f"{name}", (cx - a, cy - s, z0), (cx + a, cy + s, z1), mat, **kw),
            self.box(f"{name}_b", (cx - s, cy - a, z0 + 0.012), (cx + s, cy + a, z1 - 0.012), mat, **kw),
            self.box(f"{name}_c", (cx - a, cy - s, z0 + 0.024), (cx + a, cy + s, z1 - 0.024), mat,
                     rotation=(0, 0, 45), origin=(cx, cy, zm), **kw),
            self.box(f"{name}_d", (cx - s, cy - a, z0 + 0.036), (cx + s, cy + a, z1 - 0.036), mat,
                     rotation=(0, 0, 45), origin=(cx, cy, zm), **kw),
        ]

    def rod(self, name, R, z0, z1, mat, ch=None, cx=0.0, cy=0.0, group="gun", item_model=True):
        """Chamfered square bar along Z: two crossing boxes (corners stepped by ch, default 0.3 R)."""
        ch = 0.3 * R if ch is None else ch
        z0, z1 = min(z0, z1), max(z0, z1)
        kw = dict(group=group, item_model=item_model)
        return [
            self.box(name, (cx - R, cy - (R - ch), z0), (cx + R, cy + (R - ch), z1), mat, **kw),
            self.box(name + "_x", (cx - (R - ch), cy - R, z0 + 0.02), (cx + (R - ch), cy + R, z1 - 0.02), mat, **kw),
        ]

    def ring_x(self, name, cy, cz, R, x0, x1, mat, group="gun", k=0):
        """Round disc (axis X) from four crossing bars; k offsets the faces to avoid z-fighting."""
        w = R * 0.416
        d = 0.012 * k
        xa, xb = (x0 + d, x1 - d) if x0 < x1 else (x0 - d, x1 + d)
        B = self.box
        return [
            B(f"{name}_0", (xa, cy - R, cz - w), (xb, cy + R, cz + w), mat, group=group),
            B(f"{name}_1", (xa, cy - w, cz - R), (xb, cy + w, cz + R), mat, group=group),
            B(f"{name}_2", (xa, cy - R, cz - w), (xb, cy + R, cz + w), mat, group=group, rotation=(45, 0, 0),
              origin=(0, cy, cz)),
            B(f"{name}_3", (xa, cy - w, cz - R), (xb, cy + w, cz + R), mat, group=group, rotation=(45, 0, 0),
              origin=(0, cy, cz)),
        ]

    def cylinder_z(self, name, center, radius, z0, z1, material, group="gun", item_model=True):
        """Round bar along Z. radius >= 0.4: real octagon (apothem = radius, 4 cubes). Smaller:
        2-cube chamfered bar (ch = 0.3 r). 45deg cube rotations are legal in the item model."""
        cx, cy = center
        if radius >= 0.4:
            return self.octa(name, cx, cy, radius, z0, z1, material, group=group, item_model=item_model)
        return self.rod(name, radius, z0, z1, material, cx=cx, cy=cy, group=group, item_model=item_model)

    def point(self, name, xyz):
        """Name a rest-space point. Required: 'grip' (right hand), 'support' (left hand),
        'sight_rear' and 'sight_front' (line of sight; for scopes: eyepiece centre and
        objective centre), 'muzzle'."""
        self.points[name] = tuple(float(c) for c in xyz)

    def place_gun(self, offset):
        """Translate every gun-subtree cube, group origin and named point by offset (use to put
        the gun built around (0,0,0) into its hip position in camera space). Pivots the `gun` bone
        at the (placed) `grip` point and gives it the hip rest yaw HIP_YAW. Returns offset and
        records it in flags["place_offset"] (local point + offset = viewmodel point)."""
        offset = tuple(float(c) for c in offset)
        self.flags["old_gun_origin"] = self.gun.origin    # pre-placement pivot (local space)
        self.flags["grip_local"] = self.points.get("grip")
        for c in self.cubes:
            if c.group.is_under(self.gun):
                c.frm = v_add(c.frm, offset)
                c.to = v_add(c.to, offset)
                c.origin = v_add(c.origin, offset)
        for g in self.groups.values():
            if g.is_under(self.gun):
                g.origin = v_add(g.origin, offset)
        for k in list(self.points):
            self.points[k] = v_add(self.points[k], offset)
        if "grip" in self.points:
            self.gun.origin = self.points["grip"]
        self.gun.rotation = (0.0, HIP_YAW, 0.0)
        self.flags["place_offset"] = offset
        return offset

    def place_gun_at_hip(self, nudge=(0.0, 0.0, 0.0)):
        """place_gun so that `grip` lands at HIP_GRIP + nudge (the standard hip pose). Returns the
        offset. Keep nudges small and justify them in the gun script."""
        if "grip" not in self.points:
            raise ValueError(f"{self.id}: define the 'grip' point before place_gun_at_hip()")
        target = v_add(HIP_GRIP, nudge)
        return self.place_gun(v_sub(target, self.points["grip"]))

    def repivot_gun_keys(self, old_pivot=None):
        """Re-express the `gun` rotation/position keys authored for a gun bone pivoting at
        old_pivot (local build space, default: the gun origin before place_gun, usually (0,0,0))
        so the motion is unchanged with the pivot now at the grip: a rotation R about p with
        translation t equals R about p' with t' = t + (I-R)(p-p'). The rest-pose part of that
        term is removed so zero offsets still mean the hip pose. Call after authoring all
        animations, before finish()."""
        if self.flags.get("repivoted"):
            return
        self.flags["repivoted"] = True
        off = self.flags["place_offset"]
        old = v_add(old_pivot if old_pivot is not None else self.flags["old_gun_origin"], off)
        d = v_sub(old, self.gun.origin)
        rest = self.gun.rotation
        i3 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

        def term(r):
            m = euler_zyx(r)
            return m_vec([[i3[a][b] - m[a][b] for b in range(3)] for a in range(3)], d)

        rest_term = term(rest)
        for a in self.anims.values():
            if a.name in ("aiming", "aiming_shoot"):
                continue   # standard ADS keys already cancel the yaw about the new pivot
            rc, pc = a.channels.get(("gun", "rotation")), a.channels.get(("gun", "position"))
            if not rc and not pc:
                continue
            times = {k[0] for ch in (rc, pc) if ch for k in ch.keys}
            lo, hi = min(times), max(times)
            times |= {round(lo + i * 0.05, 4) for i in range(1, int((hi - lo) / 0.05 + 1e-9) + 1) if lo + i * 0.05 < hi}
            times = sorted(times)
            new = []
            for t in times:
                rot = rc.sample(t, (0.0, 0.0, 0.0)) if rc else (0.0, 0.0, 0.0)
                pos = pc.sample(t, (0.0, 0.0, 0.0)) if pc else (0.0, 0.0, 0.0)
                tt = term(tuple(rest[i] + rot[i] for i in range(3)))
                new.append((t, tuple(pos[i] + tt[i] - rest_term[i] for i in range(3))))
            for t, v in new:
                a.ch("gun", "position").add(t, v)

    # -- arms ------------------------------------------------------------------------
    @staticmethod
    def on_screen(p, fov=FOV_V, aspect=16 / 9):
        """True if camera-space point p is inside the view frustum (and in front of the camera)."""
        if p[2] >= 0:
            return False
        k = math.tan(math.radians(fov / 2))
        return p[1] >= p[2] * k and abs(p[0]) <= -p[2] * k * aspect

    def _offscreen(self, p):
        """Clamp y down until p is off-screen (below the view)."""
        if self.on_screen(p):
            p = (p[0], p[2] * math.tan(math.radians(FOV_V / 2)) - 0.5, p[2])
        return p

    def build_arms(self, right_shoulder=None, left_shoulder=None):
        """Create the BetterModel skin-arm bones. Shoulders are in camera space (below and
        behind the eye), both off-screen. Defaults: right (5.5,-9.5,-3.0); left = the support point
        at rest (incl. the gun's rest yaw) + 9.5 * norm((-0.55,-0.60,0.58)). Pass either to
        override. Rest pose = hip: right hand on 'grip', left hand on 'support'."""
        if right_shoulder is None:
            right_shoulder = self._offscreen((5.5, -9.5, -3.0))
        if left_shoulder is None:
            sup = self.bone_xf(self.gun, None, 0.0, self.viewmodel).apply(self.points["support"])
            left_shoulder = self._offscreen(v_add(sup, v_mul(v_norm((-0.55, -0.60, 0.58)), 9.5)))
        self.flags["shoulders"] = {"right": right_shoulder, "left": left_shoulder}
        for side, s in (("right", right_shoulder), ("left", left_shoulder)):
            p, sx = ("pr", 1) if side == "right" else ("pl", -1)
            upper = self.group(f"{p}a_{side}_arm", s, self.viewmodel)
            elbow_rest = (s[0], s[1] - ARM_UPPER, s[2])
            fore = self.group(f"{p}fa_{side}_forearm", elbow_rest, upper)
            hand_rest = (s[0] + 0.625 * sx, s[1] - ARM_UPPER - ARM_LOWER, s[2])
            self.group(f"{p}i_{side}_item", hand_rest, fore, rotation=(-90, 0, 0))
            # skin cubes, same proportions as BetterModel's steve.bbmodel (skin + hat layer)
            ux = (s[0] - 1.25, s[0] + 2.5) if side == "right" else (s[0] - 2.5, s[0] + 1.25)
            for layer, inf in (("skin", 0.0), ("hat", -0.016)):
                self.box(layer, (ux[0], s[1] - 5.125, s[2] - 1.875), (ux[1], s[1] + 0.5, s[2] + 1.875),
                         "skin", group=upper, inflate=inf, item_model=False)
                self.box(layer, (ux[0], elbow_rest[1] - 5.25, s[2] - 1.875), (ux[1], elbow_rest[1] + 0.375, s[2] + 1.875),
                         "skin", group=fore, inflate=inf, item_model=False)

    def _arm_groups(self, side):
        p = "pr" if side == "right" else "pl"
        return self.groups[f"{p}a_{side}_arm"], self.groups[f"{p}fa_{side}_forearm"]

    def _solve_arm(self, side, hand, pole=None):
        """TRUE Euler rotations (upper, fore) putting the hand at `hand` (viewmodel space)."""
        s = self.flags["shoulders"][side]
        d = v_sub(hand, s)
        dist = max(0.5, min(v_len(d), ARM_UPPER + ARM_LOWER - 0.05))
        u = v_norm(d)
        pole = pole or ((1.0 if side == "right" else -1.0) * 0.6, -1.0, 0.25)
        n = v_sub(pole, v_mul(u, v_dot(pole, u)))
        n = v_norm(n) if v_len(n) > 1e-6 else (0.0, -1.0, 0.0)
        a = (ARM_UPPER ** 2 - ARM_LOWER ** 2 + dist ** 2) / (2 * dist)
        h = math.sqrt(max(0.0, ARM_UPPER ** 2 - a * a))
        elbow = v_add(v_add(s, v_mul(u, a)), v_mul(n, h))
        hand_pt = v_add(s, v_mul(u, dist))

        def aim(direction):  # rotation (x, 0, z) mapping (0,-1,0) to direction
            dx, dy, dz = v_norm(direction)
            rx = math.degrees(math.asin(max(-1.0, min(1.0, -dz))))
            rz = math.degrees(math.atan2(dx, -dy))
            return (rx, 0.0, rz)

        up_rot = aim(v_sub(elbow, s))
        r_up = euler_zyx(up_rot)
        local = m_vec(m_t(r_up), v_sub(hand_pt, elbow))
        fo_rot = aim(local)
        return up_rot, fo_rot

    # -- pose evaluation ---------------------------------------------------------------
    def bone_xf(self, g: Group, anim: Animation | None, t: float, root: Group | None = None,
                gun_local: bool = False) -> Xf:
        """World transform of bone g (rest + animation). With root, stop below that bone
        (e.g. root=viewmodel gives viewmodel-local space). gun_local drops the gun bone's rest
        rotation (the hip yaw), i.e. shows the gun unrotated, as in the item model."""
        xf = Xf()
        for b in g.path():
            if root is not None and b is root:
                xf = Xf()
                continue
            rot, pos, _ = anim.offsets(b.name, t) if anim else ((0, 0, 0), (0, 0, 0), (1, 1, 1))
            base = (0.0, 0.0, 0.0) if (gun_local and b is self.gun) else b.rotation
            total = tuple(base[i] + rot[i] for i in range(3))
            xf = xf.then(Xf.pivot(b.origin, total, pos))
        return xf

    def bone_scale(self, g: Group, anim, t):
        s = 1.0
        for b in g.path():
            if anim:
                sc = anim.offsets(b.name, t)[2]
                s *= sc[0]
        return s

    def _hand_target(self, anim, side, t):
        keys = anim.hand_keys[side]
        if not keys:
            keys = [(0.0, "grip" if side == "right" else "support")]

        def resolve(target):
            if target == "grip":
                return self.bone_xf(self.gun, anim, t, self.viewmodel).apply(self.points["grip"])
            if target == "support":
                return self.bone_xf(self.gun, anim, t, self.viewmodel).apply(self.points["support"])
            if isinstance(target, tuple) and target and target[0] == "bone":
                _, bone, pt = target
                return self.bone_xf(self.groups[bone], anim, t, self.viewmodel).apply(pt)
            return tuple(target)

        if t <= keys[0][0]:
            return resolve(keys[0][1])
        for (t0, a), (t1, b) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                x = smoothstep(0 if t1 == t0 else (t - t0) / (t1 - t0))
                pa, pb = resolve(a), resolve(b)
                return tuple(pa[i] + (pb[i] - pa[i]) * x for i in range(3))
        return resolve(keys[-1][1])

    # -- animations ------------------------------------------------------------------
    def anim(self, name, length, loop="once") -> Animation:
        a = Animation(self, name, length, loop)
        self.anims[name] = a
        return a

    def reload_fail(self, cant_rot=(8.0, -6.0, -14.0), cant_pos=(0.2, 1.0, 1.4), length=1.2):
        """The "reload_fail" animation (reload pressed with no magazine item): the left hand drops
        off screen to a pouch point below the view, pats twice, returns EMPTY to the support point
        while the gun cants toward the camera ("check the mag") and comes back; a small magazine
        nudge if the gun has a `magazine` bone. Starts and ends on the exact rest pose.
        cant_rot / cant_pos: gun bone offsets at the cant (per-gun, same feel)."""
        Z3 = (0.0, 0.0, 0.0)
        sh = self.flags["shoulders"]["left"]
        reach = ARM_UPPER + ARM_LOWER - 1.2
        d = v_norm((-0.25, -1.0, 0.12))
        pouch = self._offscreen(v_add(sh, v_mul(d, reach)))
        up = (0.0, 1.6, -0.5)
        a = self.anim("reload_fail", length, "once")
        a.key("gun", 0.0, rot=Z3, pos=Z3)
        a.ease("gun", 0.0, 0.4, rot0=Z3, rot1=cant_rot, pos0=Z3, pos1=cant_pos)
        a.key("gun", 0.85, rot=cant_rot, pos=cant_pos)
        a.ease("gun", 0.85, length - 0.05, rot0=cant_rot, rot1=Z3, pos0=cant_pos, pos1=Z3)
        a.key("gun", length, rot=Z3, pos=Z3)
        a.hand("left", 0.0, "support")
        a.hand("left", 0.1, "support")
        a.hand("left", 0.38, pouch)
        for k, t in enumerate((0.5, 0.66)):          # two pats
            a.hand("left", t, v_add(pouch, up))
            a.hand("left", t + 0.08, pouch)
        a.hand("left", 0.84, pouch)
        a.hand("left", length - 0.05, "support")
        a.hand("left", length, "support")
        if "magazine" in self.groups:                # release nudge
            for t, y in ((0.0, 0.0), (0.2, 0.0), (0.26, -0.45), (0.38, 0.0), (length, 0.0)):
                a.key("magazine", t, pos=(0.0, y, 0.0))
        return a

    def solve_arms(self, step=0.05):
        """Bake hand targets of every animation into arm rotation keyframes (IK)."""
        rest = {}
        for side in ("right", "left"):
            up, fo = self._arm_groups(side)
            hand = self._hand_target(Animation(self, "_rest", 0), side, 0.0)
            up_rot, fo_rot = self._solve_arm(side, hand)
            up.rotation, fo.rotation = up_rot, fo_rot
            rest[side] = (up_rot, fo_rot)
        for a in self.anims.values():
            n = max(1, int(round(a.length / step)))
            for side in ("right", "left"):
                up, fo = self._arm_groups(side)
                for i in range(n + 1):
                    t = min(a.length, i * step)
                    hand = self._hand_target(a, side, t)
                    up_rot, fo_rot = self._solve_arm(side, hand, a.hand_pole.get(side))
                    a.ch(up.name, "rotation").add(t, tuple(up_rot[k] - rest[side][0][k] for k in range(3)))
                    a.ch(fo.name, "rotation").add(t, tuple(fo_rot[k] - rest[side][1][k] for k in range(3)))

    def ads_offset(self, eye_relief=None):
        """Viewmodel translation that puts the line of sight on the camera axis."""
        rear, front = self.points["sight_rear"], self.points["sight_front"]
        drop = front[1] - rear[1]
        if abs(drop) > 0.02 or abs(front[0] - rear[0]) > 0.02:
            print(f"[{self.id}] WARNING sight line not parallel to -Z: rear={rear} front={front}")
        relief = eye_relief if eye_relief is not None else self.flags.get("eye_relief", 4.5)
        return (-rear[0], -rear[1], -relief - rear[2])

    def casing(self, port_point, direction=(1.0, 0.55, 0.25), length=0.55, radius=0.12):
        """Hidden `casing` bone holding one small brass case (case + darker rim, two cubes, not in
        the item model) at the ejection port. Call it BEFORE standard_animations(casing=True), in
        local build space before place_gun_at_hip() or in viewmodel space after it. `direction` is
        the fly-out direction in gun space (+X right, +Y up, +Z toward the camera)."""
        p = tuple(float(c) for c in port_point)
        self.part("casing", p, hidden=True)
        r, h = radius, length / 2
        self.box("casing_case", (p[0] - r, p[1] - r, p[2] - h), (p[0] + r, p[1] + r, p[2] + h * 0.8),
                 "brass", group="casing", item_model=False)
        self.box("casing_rim", (p[0] - r * 1.15, p[1] - r * 1.15, p[2] + h * 0.8),
                 (p[0] + r * 1.15, p[1] + r * 1.15, p[2] + h), "copper", group="casing", item_model=False)
        self.flags["casing"] = {"direction": tuple(direction)}

    def casing_keys(self, a, t0, t1, dist=3.5, arc=1.2, direction=None, scale=1.0, size=1.0):
        """Fly the `casing` bone out of the port during t0..t1 (visible from t0, scale 0 from t1):
        straight line along direction * dist * scale with an upward arc, spinning in 90 degree steps
        per 0.05 s frame (`size` scales the case itself, e.g. smaller in ADS). Keys sit on the 0.05 s grid."""
        d = v_norm(direction or self.flags["casing"]["direction"])
        steps = max(2, int(round((t1 - t0) / 0.05)))
        Z3 = (0.0, 0.0, 0.0)
        if t0 > 0:
            a.key("casing", 0.0, scale=0.0, pos=Z3, rot=Z3)
            a.key("casing", t0 - 0.001, scale=0.0, pos=Z3, rot=Z3)
        for i in range(steps + 1):
            u = i / steps
            t = t0 + (t1 - t0) * u
            e = 1 - (1 - u) ** 2
            pos = (d[0] * dist * scale * e, d[1] * dist * scale * e + arc * scale * 4 * u * (1 - u),
                   d[2] * dist * scale * e)
            a.key("casing", t, pos=pos, rot=(90.0 * i, 0.0, 180.0 * i))
            a.key("casing", t, scale=size if u <= 0.6 else max(0.0, size * (1.0 - (u - 0.6) / 0.4)))
        a.key("casing", t1, scale=0.0)
        a.key("casing", max(a.length, t1), scale=0.0)

    def standard_animations(self, *, fire_interval=0.2, kick=0.45, climb=2.5, bolt=None,
                            bolt_travel=1.2, eye_relief=4.5, ads_kick_scale=0.5,
                            sprint_style="rifle", roll=0.8, casing=None):
        """Create the channels every gun shares: equip, unequip, standing, sprint, aiming,
        shoot, aiming_shoot. Gun-specific ones (reload, reload_empty, inspect, firearm) are
        authored by the gun script. `bolt` = name of the bone that cycles when firing."""
        self.flags["eye_relief"] = eye_relief
        ads = self.ads_offset(eye_relief)
        self.flags["ads"] = ads
        vm = "viewmodel"
        unyaw = (0.0, -self.gun.rotation[1], 0.0)

        a = self.anim("equip", 0.5, "once")
        a.ease(vm, 0.0, 0.5, rot0=(-55, 10, -20), rot1=(0, 0, 0), pos0=(1.5, -9, 2), pos1=(0, 0, 0), curve="out")

        a = self.anim("unequip", 0.4, "once")
        a.ease(vm, 0.0, 0.4, rot0=(0, 0, 0), rot1=(-55, 10, -20), pos0=(0, 0, 0), pos1=(1.5, -9, 2), curve="in")

        a = self.anim("standing", 3.0, "loop")
        for i in range(13):
            t = i * 0.25
            ph = 2 * math.pi * t / 3.0
            a.key(vm, t, rot=(0.6 * math.sin(ph), 0.4 * math.sin(ph * 0.5 + 1), 0.3 * math.sin(ph)),
                  pos=(0.06 * math.sin(ph * 0.5), 0.12 * math.sin(ph), 0))

        a = self.anim("sprint", 0.7, "loop")
        base_rot = (-10, 22, 16) if sprint_style == "rifle" else (-8, 15, 20)
        base_pos = (-0.8, -1.4, 0.6)
        for i in range(15):
            t = i * 0.05
            ph = 2 * math.pi * t / 0.7
            a.key(vm, t, rot=(base_rot[0] + 3 * math.sin(2 * ph), base_rot[1] + 2.5 * math.sin(ph), base_rot[2]),
                  pos=(base_pos[0] + 0.6 * math.sin(ph), base_pos[1] + 0.35 * abs(math.sin(ph)), base_pos[2]))

        a = self.anim("aiming", 2.0, "loop")
        for i in range(9):
            t = i * 0.25
            ph = 2 * math.pi * t / 2.0
            a.key(vm, t, pos=(ads[0] + 0.02 * math.sin(ph), ads[1] + 0.03 * math.sin(2 * ph), ads[2]),
                  rot=(0.15 * math.sin(ph), 0.1 * math.sin(2 * ph), 0))
            a.key("gun", t, rot=unyaw)   # cancel the hip yaw about the grip: sights on the camera axis

        def shoot(name, base_pos, scale, aim=False):
            L = max(0.1, fire_interval)
            R = min(L, 0.35)                 # the recoil finishes by R, then rest until L
            s = self.anim(name, L, "once")
            bx, by, bz = base_pos
            sc = scale

            def pose(rx, ry, rz, px, py, pz):
                """Pose as fractions of the peak (pos peak = (0.1, 0.15, 1) * kick, rot = climb, 0.3 climb, -roll)."""
                # ADS: the rear sight is only a few px from the eye, so the rearward kick is halved again
                kz = 0.5 if aim else 1.0
                return ((bx + px * 0.1 * kick * sc, by + py * 0.15 * kick * sc, bz + pz * kick * sc * kz),
                        (rx * climb * sc, ry * 0.3 * climb * sc, rz * -roll * sc))

            pk = pose(1, 1, 1, 1, 1, 1)
            rest = (base_pos, (0.0, 0.0, 0.0))
            frame0 = pose(0.6, 0.6, 0.6, 0.6, 0.6, 0.6)
            s.key(vm, 0.0, pos=frame0[0], rot=frame0[1])   # frame 0 shows on the shot tick
            s.key(vm, 0.05, pos=pk[0], rot=pk[1])

            def seg(t0, t1, p0, p1, curve):
                s.ease(vm, t0, t1, rot0=p0[1], rot1=p1[1], pos0=p0[0], pos1=p1[0], curve=curve)

            if R >= 0.2:
                mid = pose(1.15, 1.15, 0.8, 0.5, 0.5, 0.5)   # muzzle still rising, translation half back
                ov = pose(-0.1, -0.1, 0.0, 0.0, 0.0, -0.08)  # slight overshoot
                seg(0.05, 0.1, pk, mid, "out")
                seg(0.1, 0.8 * R, mid, ov, "smooth")
                seg(0.8 * R, R, ov, rest, "smooth")
            else:
                seg(0.05, L, pk, rest, "out")
            if R < L:
                s.key(vm, L, pos=base_pos, rot=(0, 0, 0))
            if bolt:
                s.key(bolt, 0.0, pos=(0, 0, 0))
                s.key(bolt, min(0.04, L * 0.3), pos=(0, 0, bolt_travel))
                s.ease(bolt, min(0.04, L * 0.3), min(L, 0.1), pos0=(0, 0, bolt_travel), pos1=(0, 0, 0), curve="in")
            if aim:   # aiming_shoot: keep the hip yaw cancelled
                s.key("gun", 0.0, rot=unyaw)
                s.key("gun", L, rot=unyaw)
            if casing:
                if "casing" not in self.groups:
                    raise ValueError(f"{self.id}: call m.casing(...) before standard_animations(casing=True)")
                self.casing_keys(s, 0.0, min(L, 0.25), scale=0.7 if aim else 1.0, size=0.6 if aim else 1.0)
            s.key("glow_flash", 0.0, scale=1.0)
            s.key("glow_flash", 0.05, scale=1.0)
            s.key("glow_flash", 0.051, scale=0.0)
            s.key("glow_flash", L, scale=0.0)
            return s

        shoot("shoot", (0, 0, 0), 1.0)
        shoot("aiming_shoot", ads, ads_kick_scale, aim=True)

    # -- muzzle flash ------------------------------------------------------------------
    def muzzle_flash(self, size=2.2):
        m = self.points["muzzle"]
        mz = self.group("muzzle", m, "gun")
        fl = self.group("glow_flash", m, mz, hidden=True)
        L = size
        self.box("flash_core_h", (m[0] - L / 2, m[1] - 0.001, m[2] - L * 1.3), (m[0] + L / 2, m[1] + 0.001, m[2]),
                 "flash", group=fl, item_model=False)
        self.box("flash_core_v", (m[0] - 0.001, m[1] - L / 2, m[2] - L * 1.3), (m[0] + 0.001, m[1] + L / 2, m[2]),
                 "flash", group=fl, item_model=False)
        self.box("flash_core_f", (m[0] - L * 0.35, m[1] - L * 0.35, m[2] - 0.05), (m[0] + L * 0.35, m[1] + L * 0.35, m[2] - 0.04),
                 "flash", group=fl, item_model=False)

    # -- texture / UV --------------------------------------------------------------------
    def _faces(self, c: Cube):
        sz = c.size()
        out = []
        for f, (ua, va) in FACE_AXES.items():
            if f in c.faces_off:
                continue
            w = max(1, int(round(sz[ua] * self.density)))
            h = max(1, int(round(sz[va] * self.density)))
            if c.material == "flash":
                if (sz[ua] < 0.05 or sz[va] < 0.05):
                    continue
            out.append((f, w, h))
        return out

    def _pack(self):
        """Shelf-pack every face into a TEX_SIZE (or texture_size) square. The whole gun retries at
        a lower texel density until it fits. Sets self.density."""
        size = self.texture_size or TEX_SIZE
        for density in DENSITIES:
            self.density = density
            rects = []
            for c in self.cubes:
                if c.material == "skin":
                    continue
                for f, w, h in self._faces(c):
                    rects.append((c, f, w, h))
            rects.append((None, "skin", 2, 2))
            rects.sort(key=lambda r: (-r[3], -r[2]))
            x = y = row = 0
            placed = {}
            ok = True
            for c, f, w, h in rects:
                if x + w > size:
                    x, y, row = 0, y + row, 0
                if y + h > size or w > size:
                    ok = False
                    break
                placed[(id(c), f) if c is not None else "skin"] = (x, y, x + w, y + h)
                x += w
                row = max(row, h)
            if ok:
                for c in self.cubes:
                    if c.material == "skin":
                        c.uv = {f: placed["skin"] for f in FACE_AXES}
                    else:
                        c.uv = {f: placed[(id(c), f)] for f, _, _ in self._faces(c)}
                return size
        raise RuntimeError(f"{self.id}: faces do not fit a {size}x{size} texture even at density {DENSITIES[-1]}")

    def _paint(self, size):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        rng = random.Random(zlib.crc32(self.id.encode()) & 0xFFFF)  # hash() is salted per process
        for c in self.cubes:
            if c.material == "skin":
                x1, y1, x2, y2 = c.uv["north"]
                for j in range(y1, y2):
                    for i in range(x1, x2):
                        img.putpixel((i, j), (*_hex(MATERIALS["skin"].base), 255))
                continue
            sz = c.size()
            longest = max(range(3), key=lambda i: sz[i])
            for f, rect in c.uv.items():
                ua, va = FACE_AXES[f]
                _paint_face(img, rect, MATERIALS[c.material], grain_along_u=(longest == ua), rng=rng, face_dir=f)
        return img

    # -- acceptance numbers ----------------------------------------------------------------
    def reach_report(self, step=0.05):
        """{(anim, side): max shoulder->hand-target distance} sampled every `step` seconds."""
        out = {}
        for a in self.anims.values():
            for side in ("right", "left"):
                s = self.flags["shoulders"][side]
                n = max(1, int(round(a.length / step)))
                out[(a.name, side)] = max(
                    v_len(v_sub(self._hand_target(a, side, min(a.length, i * step)), s)) for i in range(n + 1))
        return out

    def hip_metrics(self):
        """Rest-pose numbers: hand distances, stock rear (max world z of gun cubes), grip."""
        sh = self.flags["shoulders"]
        gx = self.bone_xf(self.gun, None, 0.0, self.viewmodel)
        zmax = -1e9
        for c in self.cubes:
            if c.group.is_under(self.gun) and c.material != "flash" and not any(g.hidden for g in c.group.path()):
                full = self.bone_xf(c.group, None, 0.0).then(Xf.pivot(c.origin, c.rotation))
                zmax = max(zmax, max(full.apply(p)[2] for p in c.corners()))
        return {
            "dL": v_len(v_sub(gx.apply(self.points["support"]), sh["left"])),
            "dR": v_len(v_sub(gx.apply(self.points["grip"]), sh["right"])),
            "stock": zmax, "grip": gx.apply(self.points["grip"]),
            "left_shoulder": sh["left"], "right_shoulder": sh["right"],
        }

    # -- export ------------------------------------------------------------------------
    def finish(self):
        """Solve arms, pack UVs, paint. Call after all geometry + animations exist."""
        if "grip" not in self.points:
            raise ValueError(f"{self.id}: no 'grip' point defined (the gun bone pivots at the grip)")
        if "place_offset" not in self.flags:
            raise ValueError(f"{self.id}: place_gun()/place_gun_at_hip() was never called")
        self.gun.origin = self.points["grip"]
        for g in self.groups.values():
            if g.hidden:
                for a in self.anims.values():
                    if (g.name, "scale") not in a.channels:
                        a.key(g.name, 0.0, scale=0.0)
                        a.key(g.name, a.length, scale=0.0)   # also hold 0 on the last frame
        if "shoulders" in self.flags:
            self.solve_arms()
        self.tex_size = self._pack()
        self.texture = self._paint(self.tex_size)

    def _bb_group(self, g: Group):
        return {
            "name": g.name, "origin": list(g.origin), "color": 0,
            "rotation": list(bb_rest_rotation(g.rotation)), "uuid": g.uuid, "export": True,
            "mirror_uv": False, "isOpen": False, "locked": False, "visibility": True, "autouv": 0,
            "selected": False, "primary_selected": False,
        }

    def _bb_cube(self, c: Cube):
        faces = {}
        for f in FACE_AXES:
            if f in c.uv:
                x1, y1, x2, y2 = c.uv[f]
                faces[f] = {"uv": [x1, y1, x2, y2], "texture": 0}
            else:
                faces[f] = {"uv": [0, 0, 0, 0], "texture": None}
        d = {
            "name": c.name, "box_uv": False, "rescale": False, "locked": False, "light_emission": 0,
            "render_order": "default", "allow_mirror_modeling": True,
            "from": list(c.frm), "to": list(c.to), "autouv": 0, "color": 0,
            "origin": list(c.origin), "inflate": c.inflate, "faces": faces, "type": "cube", "uuid": c.uuid,
        }
        if any(abs(r) > 1e-9 for r in c.rotation):
            d["rotation"] = list(bb_rest_rotation(c.rotation))
        return d

    def _outliner(self, items):
        out = []
        for it in items:
            if isinstance(it, Group):
                out.append({"uuid": it.uuid, "isOpen": False, "children": self._outliner(it.children)})
            else:
                out.append(it.uuid)
        return out

    def _bb_anim(self, a: Animation):
        animators = {}
        for (bone, chan), ch in sorted(a.channels.items()):
            g = self.groups[bone]
            ent = animators.setdefault(g.uuid, {"name": g.name, "type": "bone", "keyframes": []})
            for t, v in ch.keys:
                if chan == "rotation":
                    val = bb_anim_rotation(v)
                elif chan == "position":
                    val = bb_anim_position(v)
                else:
                    val = v
                ent["keyframes"].append({
                    "channel": chan, "data_points": [{"x": round(val[0], 4), "y": round(val[1], 4), "z": round(val[2], 4)}],
                    "uuid": _uid(), "time": t, "color": -1, "interpolation": "linear",
                })
        return {
            "uuid": _uid(), "name": a.name, "loop": a.loop, "override": False, "length": a.length,
            "snapping": 20, "selected": False, "anim_time_update": "", "blend_weight": "",
            "start_delay": "", "loop_delay": "", "animators": animators,
        }

    def to_bbmodel(self) -> dict:
        buf = io.BytesIO()
        self.texture.save(buf, "PNG")
        src = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        return {
            "meta": {"format_version": "5.0", "model_format": "free", "box_uv": False},
            "name": f"gun_{self.id}", "model_identifier": "", "visible_box": [1, 1, 0],
            "variable_placeholders": "", "variable_placeholder_buttons": [], "timeline_setups": [],
            "unhandled_root_fields": {},
            "resolution": {"width": self.tex_size, "height": self.tex_size},
            "elements": [self._bb_cube(c) for c in self.cubes],
            "groups": [self._bb_group(g) for g in self.groups.values()],
            "outliner": self._outliner(self.root_order),
            "textures": [{
                "path": "", "name": f"gun_{self.id}.png", "folder": "", "namespace": "", "id": "0",
                "group": "", "width": self.tex_size, "height": self.tex_size,
                "uv_width": self.tex_size, "uv_height": self.tex_size, "particle": False,
                "use_as_default": False, "layers_enabled": False, "sync_to_project": "",
                "render_mode": "default", "render_sides": "auto", "pbr_channel": "color",
                "frame_time": 1, "frame_order_type": "loop", "frame_order": "", "frame_interpolate": False,
                "visible": True, "internal": True, "saved": False, "uuid": _uid(), "source": src,
            }],
            "animations": [self._bb_anim(a) for a in self.anims.values()],
        }

    def item_model(self, display=None) -> dict:
        """Vanilla item model of the gun subtree at rest, recentred into the 16^3 box. Built in
        gun-local space: the rest rotation (hip yaw) of `gun` is ignored; bones below it must not
        have rest rotations."""
        cubes = [c for c in self.cubes if c.item_model and c.group.is_under(self.gun) and c.material != "flash"
                 and not any(g.hidden for g in c.group.path())]
        lo = [min(min(p[i] for p in c.corners()) for c in cubes) for i in range(3)]
        hi = [max(max(p[i] for p in c.corners()) for c in cubes) for i in range(3)]
        center = [(lo[i] + hi[i]) / 2 for i in range(3)]
        shift = [8 - center[i] for i in range(3)]
        elements = []
        warned = False
        for c in cubes:
            below = c.group.path()[c.group.path().index(self.gun) + 1:]
            if any(abs(r) > 1e-9 for g in below for r in g.rotation):
                raise ValueError(f"{self.id}: bones below gun must not have rest rotations ({c.group.name})")
            el = {
                "name": c.name,
                "from": [round(c.frm[i] - c.inflate + shift[i], 4) for i in range(3)],
                "to": [round(c.to[i] + c.inflate + shift[i], 4) for i in range(3)],
                "faces": {},
            }
            nz = [(i, r) for i, r in enumerate(c.rotation) if abs(r) > 1e-9]
            if nz:
                axis_i, ang = nz[0]
                snapped = min(ALLOWED_ITEM_ANGLES, key=lambda a: abs(a - ang))
                if len(nz) > 1 or abs(snapped - ang) > 1e-6:
                    if not warned:
                        print(f"[{self.id}] item model: snapping non-vanilla rotations (e.g. {c.name} {c.rotation})")
                        warned = True
                el["rotation"] = {"angle": snapped, "axis": "xyz"[axis_i],
                                  "origin": [round(c.origin[i] + shift[i], 4) for i in range(3)]}
            for f, (x1, y1, x2, y2) in c.uv.items():
                k = 16 / self.tex_size
                el["faces"][f] = {"uv": [round(x1 * k, 4), round(y1 * k, 4), round(x2 * k, 4), round(y2 * k, 4)],
                                  "texture": "#0"}
            for p in el["from"] + el["to"]:
                if p < -16 or p > 32:
                    raise ValueError(f"{self.id}: item model element {c.name} outside -16..32")
            elements.append(el)
        length = hi[2] - lo[2]
        grip_off = self.points["grip"][2] - center[2]     # px behind the bbox centre (+Z = toward the stock)
        disp = display or default_display(length, grip_off)
        return {
            "credit": "SovereignMC tools/generate/guns",
            "texture_size": [self.tex_size, self.tex_size],
            "textures": {"0": f"weapons:item/gun/{self.id}", "particle": f"weapons:item/gun/{self.id}"},
            "elements": elements,
            "gui_light": "front",
            "display": disp,
        }

    def write(self, pack_dir: Path = ROOT, item_display=None, item_name=None, previews=True, viewmodel=True):
        left = deconflict(self)
        if left:
            print(f"[{self.id}] WARNING {left} coplanar face pairs left after deconflict")
        self.finish()
        tex = pack_dir / "assets" / "weapons" / "textures" / "item" / "gun" / f"{self.id}.png"
        tex.parent.mkdir(parents=True, exist_ok=True)
        self.texture.save(tex)
        item = pack_dir / "assets" / "weapons" / "models" / "item" / f"{item_name or self.id}.json"
        item.parent.mkdir(parents=True, exist_ok=True)
        item.write_text(json.dumps(self.item_model(item_display), indent=1) + "\n")
        print(f"[{self.id}] {len(self.cubes)} cubes ({sum(1 for c in self.cubes if c.group.is_under(self.gun))} gun), "
              f"texture {self.tex_size}px, animations: {', '.join(self.anims)}")
        print(f"[{self.id}] texture density {self.density} texels/px")
        for (an, side), d in self.reach_report().items():
            if d > 11.0:
                print(f"[{self.id}] WARNING arm reach {an}/{side} max hand distance {d:.2f} > 11.0")
        print(f"[{self.id}] wrote {item.relative_to(pack_dir)}, {tex.relative_to(pack_dir)}")
        if viewmodel:
            import viewmodel_bake
            viewmodel_bake.bake(self, pack_dir, item_name or self.id)
        if previews:
            paths = render_previews(self)
            print(f"[{self.id}] previews: " + ", ".join(str(p) for p in paths))


# --------------------------------------------------------------------------------------
# Coplanar-face cleanup (z-fighting). write() runs deconflict() before finish().
# Axis-aligned, unrotated, non-inflated cubes of the same bone whose faces share a plane and
# overlap: the cube with the smaller face is pushed DECONFLICT_STEP proud. Rotated cubes and
# penetrating overlaps are not touched.
# --------------------------------------------------------------------------------------

import itertools  # noqa: E402

DECONFLICT_STEP = 0.02
DECONFLICT_TOL = 0.005


def _cubes(m):
    return [c for c in m.cubes if c.group.is_under(m.gun) and c.material != "flash"
            and c.inflate == 0 and all(abs(r) < 1e-9 for r in c.rotation)]


def coplanar_pairs(m):
    """[(cube_a, cube_b, axis, side)] of same-bone coplanar overlapping same-direction faces."""
    out = []
    for a, b in itertools.combinations(_cubes(m), 2):
        if a.group is not b.group:
            continue
        for ax in range(3):
            o = [i for i in range(3) if i != ax]
            if not all(min(a.to[i], b.to[i]) - max(a.frm[i], b.frm[i]) > DECONFLICT_TOL for i in o):
                continue
            for side, va, vb in (("lo", a.frm[ax], b.frm[ax]), ("hi", a.to[ax], b.to[ax])):
                if abs(va - vb) <= DECONFLICT_TOL:
                    out.append((a, b, ax, side))
    return out


def buried(m):
    """Cubes (same bone) completely inside another cube."""
    out = []
    cs = _cubes(m)
    for a in cs:
        for b in cs:
            if a is not b and a.group is b.group and all(
                    b.frm[i] - DECONFLICT_TOL <= a.frm[i] and a.to[i] <= b.to[i] + DECONFLICT_TOL for i in range(3)):
                out.append((a.name, b.name))
    return out


def deconflict(m, max_passes=6):
    for _ in range(max_passes):
        pairs = coplanar_pairs(m)
        if not pairs:
            break
        moved = set()
        for a, b, ax, side in pairs:
            o = [i for i in range(3) if i != ax]
            area = lambda c: (c.to[o[0]] - c.frm[o[0]]) * (c.to[o[1]] - c.frm[o[1]])  # noqa: E731
            small = a if (area(a), a.name) <= (area(b), b.name) else b
            if (id(small), ax, side) in moved:
                continue
            moved.add((id(small), ax, side))
            f, t = list(small.frm), list(small.to)
            if side == "lo":
                f[ax] -= DECONFLICT_STEP
            else:
                t[ax] += DECONFLICT_STEP
            small.frm, small.to = tuple(f), tuple(t)
    return len(coplanar_pairs(m))


# --------------------------------------------------------------------------------------
# Blockbench sign conventions (verified in Blockbench 5.2.2 Generic format)
# --------------------------------------------------------------------------------------

def bb_rest_rotation(r):
    """TRUE rest rotation -> value stored in .bbmodel group/cube 'rotation'."""
    return (r[0], r[1], r[2])


def bb_anim_rotation(r):
    """TRUE rotation offset -> Blockbench rotation keyframe value (Generic/free format adds
    keyframe values to the rest Euler angles unchanged; verified in Blockbench 5.2.2)."""
    return (r[0], r[1], r[2])


def bb_anim_position(p):
    """TRUE translation -> Blockbench position keyframe value (unchanged in Generic format)."""
    return (p[0], p[1], p[2])


def default_display(length, grip_off=None):
    """Item display transforms for a gun of `length` px laid along Z, muzzle -Z, centred on the
    bbox. grip_off = px from the bbox centre to the grip along Z (+ toward the stock). Tuned in
    Blockbench on the AK-47 (2026-11-22). Item display Euler order is XYZ (Z applied first, about
    the barrel), so the GUI diagonal is X=90, Z=90, Y=-(90-roll) with roll 40."""
    L = max(length, 1.0)
    g = 0.1 * L if grip_off is None else grip_off
    s_gui = 18.5 / L                 # AK 16.2 -> 1.14, ~15 of the 16 px slot
    s_fix = 22.0 / L                 # fills an item frame
    s_head = min(1.0, 14.0 / L)      # head slot is scaled 0.625 by the game
    r = lambda v: round(v, 3)

    def held():
        return {"rotation": [90, 0, 0], "translation": [0, r(g), -0.2], "scale": [1, 1, 1]}

    return {
        "thirdperson_righthand": held(),
        "thirdperson_lefthand": held(),
        # first person renders minecraft:empty (feather.json display_context); the viewmodel replaces it
        "firstperson_righthand": {"rotation": [0, 180, 0], "translation": [2, 2, 0], "scale": [0.9, 0.9, 0.9]},
        "firstperson_lefthand": {"rotation": [0, 180, 0], "translation": [2, 2, 0], "scale": [0.9, 0.9, 0.9]},
        "ground": {"rotation": [0, 0, 90], "translation": [0, 2, 0], "scale": [0.65, 0.65, 0.65]},
        "gui": {"rotation": [90, -50, 90], "translation": [r(0.071 * L * s_gui), r(-0.046 * L * s_gui), 0],
                "scale": [r(s_gui)] * 3},
        "fixed": {"rotation": [0, 90, 0], "translation": [0, 0, 0], "scale": [r(s_fix)] * 3},
        "head": {"rotation": [0, 0, 0], "translation": [0, 9.5, 0], "scale": [r(s_head)] * 3},
        "on_shelf": {"rotation": [0, 90, 0], "translation": [0, 0, 0], "scale": [r(16.0 / L)] * 3},
    }


# --------------------------------------------------------------------------------------
# Preview renderer (offline, Pillow): orthographic views + first-person perspective
# --------------------------------------------------------------------------------------

FACE_NORMALS = {"north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0), "west": (-1, 0, 0),
                "up": (0, 1, 0), "down": (0, -1, 0)}
FACE_CORNERS = {  # indices into Cube.corners() (x,y,z bits: x*4 + y*2 + z)
    "north": (0, 4, 6, 2), "south": (1, 3, 7, 5), "east": (4, 5, 7, 6),
    "west": (0, 2, 3, 1), "up": (2, 6, 7, 3), "down": (0, 1, 5, 4),
}
LIGHT = v_norm((0.4, 0.8, 0.45))


def _face_color(model: GunModel, c: Cube, f):
    if c.uv and f in c.uv:
        x1, y1, x2, y2 = c.uv[f]
        crop = model.texture.crop((x1, y1, x2, y2)).convert("RGB").resize((1, 1), Image.BOX)
        return crop.getpixel((0, 0))
    return _hex(MATERIALS[c.material].base)


def _collect_polys(model: GunModel, anim, t, only_gun=False, include_arms=True, gun_local=False):
    polys = []
    for c in model.cubes:
        if only_gun and not c.group.is_under(model.gun):
            continue
        if not include_arms and c.material == "skin":
            continue
        if c.material == "skin" and c.name == "hat":
            continue
        if model.bone_scale(c.group, anim, t) < 0.01:
            continue
        if anim is None and (c.material == "flash" or any(g.hidden for g in c.group.path())):
            continue
        gx = model.bone_xf(c.group, anim, t, gun_local=gun_local)
        cx = Xf.pivot(c.origin, c.rotation)
        full = gx.then(cx)
        corners = [full.apply(p) for p in c.corners()]
        for f, idx in FACE_CORNERS.items():
            if f in c.faces_off:
                continue
            n = m_vec(full.r, FACE_NORMALS[f])
            pts = [corners[i] for i in idx]
            col = _face_color(model, c, f)
            if c.material == "skin":
                col = (199, 154, 122) if "forearm" in c.group.name else (70, 92, 60)  # sleeve upper arm
            polys.append((pts, n, col, c.material == "flash"))
    return polys


def _draw(polys, proj, size, bg=(46, 50, 58), cull_back=True, view_dir=None):
    img = Image.new("RGB", size, bg)
    dr = ImageDraw.Draw(img)
    items = []
    for pts, n, col, emissive in polys:
        pp = [proj(p) for p in pts]
        if any(q is None for q in pp):
            continue
        if cull_back and view_dir is not None and v_dot(n, view_dir(pts)) >= 0:
            continue
        depth = sum(q[2] for q in pp) / len(pp)
        lum = 1.0 if emissive else 0.55 + 0.45 * max(0.0, v_dot(n, LIGHT))
        items.append((depth, [(q[0], q[1]) for q in pp], tuple(min(255, int(ch * lum)) for ch in col)))
    items.sort(key=lambda it: -it[0])
    for _, pp, col in items:
        dr.polygon(pp, fill=col, outline=tuple(max(0, ch - 25) for ch in col))
    return img


def render_ortho(model: GunModel, view="side", px=40, anim=None, t=0.0, only_gun=True):
    polys = _collect_polys(model, anim, t, only_gun=only_gun, gun_local=True)
    pts = [p for poly in polys for p in poly[0]]
    axes = {"side": (2, 1, 0, -1), "side_left": (2, 1, 0, 1), "top": (2, 0, 1, 1), "front": (0, 1, 2, -1)}
    # (horizontal axis, vertical axis, depth axis, sign); side = viewed from +X (gun's right)
    ha, va, da, sgn = axes[view]
    hs = -1 if view in ("side",) else 1
    xs = [p[ha] * hs for p in pts]
    ys = [p[va] for p in pts]
    w = int((max(xs) - min(xs)) * px) + 40
    h = int((max(ys) - min(ys)) * px) + 40
    x0, y1 = min(xs), max(ys)

    def proj(p):
        return ((p[ha] * hs - x0) * px + 20, (y1 - p[va]) * px + 20, -p[da] * sgn if view != "front" else p[2])

    vd = {"side": (-1, 0, 0), "side_left": (1, 0, 0), "top": (0, -1, 0), "front": (0, 0, 1)}[view]
    if view == "top":
        def proj(p):  # noqa: F811 - top: x right, -z up
            return ((p[2] * -1 - (-max(q[2] for q in pts))) * px + 20, (p[0] - min(q[0] for q in pts)) * px + 20, -p[1])
        w = int((max(q[2] for q in pts) - min(q[2] for q in pts)) * px) + 40
        h = int((max(q[0] for q in pts) - min(q[0] for q in pts)) * px) + 40
    if view == "front":
        def proj(p):  # noqa: F811 - looking from the muzzle (-Z) toward +Z
            return ((max(q[0] for q in pts) - p[0]) * px + 20, (y1 - p[1]) * px + 20, p[2])
        w = int((max(q[0] for q in pts) - min(q[0] for q in pts)) * px) + 40
    return _draw(polys, proj, (max(w, 60), max(h, 60)), cull_back=True, view_dir=lambda _pts: v_mul(vd, -1))


def _clip_near(pts, near):
    """Sutherland-Hodgman clip of a polygon against the plane z = -near (keep z <= -near)."""
    out = []
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        ina, inb = a[2] <= -near, b[2] <= -near
        if ina:
            out.append(a)
        if ina != inb:
            k = (-near - a[2]) / (b[2] - a[2])
            out.append(tuple(a[j] + (b[j] - a[j]) * k for j in range(3)))
    return out


def render_fp(model: GunModel, anim=None, t=0.0, size=(640, 360), fov=70.0, near=0.8):
    """First-person render: camera at origin looking -Z, vertical FOV `fov`.
    near=0.8 px = 0.05 block, the Minecraft near plane."""
    polys = []
    for pts, n, col, em in _collect_polys(model, anim, t):
        if v_dot(n, v_mul(pts[0], -1)) <= 0:
            continue  # back face (test before clipping)
        cp = _clip_near(pts, near)
        if len(cp) >= 3:
            polys.append((cp, n, col, em))
    f = (size[1] / 2) / math.tan(math.radians(fov / 2))

    def proj(p):
        return (size[0] / 2 + f * p[0] / -p[2], size[1] / 2 - f * p[1] / -p[2], -p[2])

    img = _draw(polys, proj, size, bg=(120, 160, 200), cull_back=False)
    dr = ImageDraw.Draw(img)
    dr.line((size[0] / 2 - 6, size[1] / 2, size[0] / 2 + 6, size[1] / 2), fill=(255, 255, 255))
    dr.line((size[0] / 2, size[1] / 2 - 6, size[0] / 2, size[1] / 2 + 6), fill=(255, 255, 255))
    return img


def _fp_view_dir(pts):
    return v_norm(v_mul(pts[0], -1))


def render_previews(model: GunModel):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    side = render_ortho(model, "side")
    p = PREVIEW_DIR / f"{model.id}_side.png"
    side.save(p)
    out.append(p)
    top = render_ortho(model, "top", px=30)
    front = render_ortho(model, "front", px=30)
    sheet = Image.new("RGB", (top.width + front.width + 10, max(top.height, front.height)), (46, 50, 58))
    sheet.paste(top, (0, 0))
    sheet.paste(front, (top.width + 10, 0))
    p = PREVIEW_DIR / f"{model.id}_top_front.png"
    sheet.save(p)
    out.append(p)
    hip = render_fp(model)
    ads = render_fp(model, model.anims.get("aiming"), 0.0) if "aiming" in model.anims else hip
    fp = Image.new("RGB", (hip.width * 2 + 10, hip.height), (0, 0, 0))
    fp.paste(hip, (0, 0))
    fp.paste(ads, (hip.width + 10, 0))
    p = PREVIEW_DIR / f"{model.id}_fp_hip_ads.png"
    fp.save(p)
    out.append(p)
    # animation contact sheets: 6 frames per animation, small
    for a in model.anims.values():
        frames = [render_fp(model, a, a.length * i / 5, size=(256, 144)) for i in range(6)]
        sh = Image.new("RGB", (256 * 6 + 25, 144), (0, 0, 0))
        for i, fr in enumerate(frames):
            sh.paste(fr, (i * 261, 0))
        p = PREVIEW_DIR / f"{model.id}_anim_{a.name}.png"
        sh.save(p)
        out.append(p)
    return out
