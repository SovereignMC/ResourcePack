"""Skinned first-person arms for the sgvm gun viewmodel.

The gun (``viewmodel_bake.py``) is drawn by an item shader that cannot read player skins, so the
arms are extra layers of the ``minecraft:player_head`` special item model (skin = the stack's
``minecraft:profile``). Every layer is ``{"type": "minecraft:special", "base": <model id>,
"model": {"type": "minecraft:player_head"}}``; the base model's ``firstperson_righthand`` display
transform places, rotates and scales the 8x8x8 head box so that it becomes ONE arm segment for ONE
animation frame, and the ``core/entity`` shader override (assets/minecraft/shaders/core/entity.*)
remaps the head/hat UVs onto the skin's right-arm / sleeve UVs.

Segments per gun (the right upper arm is never on screen):

  rfa  right forearm   (bone prfa_right_forearm)   normal
  lua  left upper arm  (bone pla_left_arm)          MIRRORED (negative z scale); the shader
                                                    treats back-facing = mirrored = upper half
  lfa  left forearm    (bone plfa_left_forearm)     normal

Each layer is a ``range_dispatch`` on custom_model_data floats[1] = animIndex * 1000 + frame
(``viewmodel_bake.ANIMATIONS`` order, ``_frames`` frame lists), one entry per distinct run.

Vanilla chain (hand pass, view space = eye origin, -Z forward, +X right, +Y up, 1 px = 1/16):

  view(v) = T0 + T(t) * Rx*Ry*Rz * S(s) * L(v)       T0 = (0.56, -0.52, -0.72) blocks
  L(v)    = (vx/16, -vy/16 - 0.5, -vz/16)            head model vertex v in px, box [-4,4]x[-8,0]x[-4,4]

so the head box is L in [-.25,.25] x [-.5,0] x [-.25,.25] (centre (0,-.25,0)), its "DOWN"-named
face (model y = -8) is the +Y (top) face and NORTH/SOUTH/WEST/EAST land on +Z/-Z/-X/+X.
The head is oriented like a vanilla player arm: top = shoulder end of the segment (+Y of the
bone), NORTH (front) = the arm front (-Z of the bone), WEST = the player's right side. Hence
L -> bone rest axes: right/forearm diag(-1,1,-1), mirrored left upper arm diag(1,1,-1).

Run this file to verify every gun: ``python3 viewmodel_arms.py`` (reads the generated files back
from disk, reimplements the vanilla chain and asserts the head box lands on the gunlib cube).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from gunlib import m_mul, m_vec, rot_x, rot_y, rot_z  # noqa: E402

HAND_ORIGIN = (0.56, -0.52, -0.72)       # ItemInHandRenderer.applyItemArmTransform, right hand
HEAD_EDGE_PX = 8.0
HEAD_CENTRE_L = (0.0, -0.25, 0.0)         # head box centre in L (blocks)
MAX_T_PX = 80.0
MAX_S = 4.0
ANIM_STRIDE = 1000

# name, bone group, mirrored, L -> bone-rest axis signs
SEGMENTS = (
    ("rfa", "prfa_right_forearm", False),
    ("lua", "pla_left_arm", True),
    ("lfa", "plfa_left_forearm", False),
)


def _cl(mirrored):
    return (1.0 if mirrored else -1.0, 1.0, -1.0)


def _skin_cube(model, group):
    cubes = [c for c in model.cubes if c.group is group and c.material == "skin" and c.name == "skin"]
    if len(cubes) != 1:
        raise ValueError(f"{model.id}: expected one skin cube in {group.name}, got {len(cubes)}")
    c = cubes[0]
    if any(abs(r) > 1e-9 for r in c.rotation) or c.inflate:
        raise ValueError(f"{model.id}: skin cube {group.name} is rotated/inflated")
    return c


def _euler_xyz(r):
    """Degrees (rx, ry, rz) with R = Rx*Ry*Rz (JOML Quaternionf.rotationXYZ)."""
    sy = max(-1.0, min(1.0, r[0][2]))
    ry = math.asin(sy)
    if abs(sy) < 0.999999:
        rx = math.atan2(-r[1][2], r[2][2])
        rz = math.atan2(-r[0][1], r[0][0])
    else:   # gimbal lock: fold everything into rx
        rz = 0.0
        rx = math.atan2(r[2][1], r[1][1])
    return tuple(math.degrees(a) for a in (rx, ry, rz))


def segment_transform(model, group, mirrored, anim, t):
    """Display transform (rotation deg, translation px, scale) of the segment at (anim, t), or
    None when the bone is hidden."""
    if model.bone_scale(group, anim, t) < 0.01:
        return None
    cube = _skin_cube(model, group)
    size = cube.size()
    centre = cube.center()
    b = model.bone_xf(group, anim, t)
    cc = b.apply(centre)                                   # cube centre, view space, px
    cl = _cl(mirrored)
    # W = Br * diag(cl) * diag(size/8): the linear map head-L (blocks) -> view (blocks)
    cols = []
    for i in range(3):
        col = [b.r[row][i] * cl[i] * size[i] / HEAD_EDGE_PX for row in range(3)]
        cols.append(col)
    s = [math.sqrt(sum(x * x for x in col)) for col in cols]
    rcols = [[x / s[i] for x in cols[i]] for i in range(3)]
    r = [[rcols[c][row] for c in range(3)] for row in range(3)]
    det = (r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1])
           - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0])
           + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0]))
    if det < 0:      # mirrored: keep R a rotation, push the reflection into one scale axis
        for row in range(3):
            r[row][2] = -r[row][2]
        s[2] = -s[2]
    rot = _euler_xyz(r)
    # t = C - T0 - W * Lc,  W = R*S (columns scaled)
    wl = [sum(r[row][i] * s[i] * HEAD_CENTRE_L[i] for i in range(3)) for row in range(3)]
    tr = [cc[i] / 16.0 - HAND_ORIGIN[i] - wl[i] for i in range(3)]
    trans = [x * 16.0 for x in tr]
    if max(abs(x) for x in trans) > MAX_T_PX:
        raise ValueError(f"{model.id}/{group.name}: translation {trans} exceeds {MAX_T_PX} px")
    if max(abs(x) for x in s) > MAX_S:
        raise ValueError(f"{model.id}/{group.name}: scale {s} exceeds {MAX_S}")
    return rot, tuple(trans), tuple(s)


# Quantization steps (applied before dedupe; the selftest tolerance follows from them).
Q_ROT, Q_TRANS, Q_SCALE = 0.5, 0.05, 0.001
SELFTEST_TOL_PX = 0.3
# 1-2 char gun codes for the shortened base model paths weapons:a/<code>/<base36 n>
GUN_CODES = {"ak47": "ak", "dragunov": "dr", "g3": "g3", "m14": "m1", "m3": "m3",
             "ppsh41": "pp", "remington700": "r7", "ssg69": "ss", "uzi": "uz"}


def _q(v, step, nd):
    return round(round(v / step) * step, nd) + 0.0


def _round(tf):
    rot, trans, scale = tf
    return (tuple(_q(v, Q_ROT, 1) for v in rot), tuple(_q(v, Q_TRANS, 2) for v in trans),
            tuple(_q(v, Q_SCALE, 3) for v in scale))


def _b36(n):
    d = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while True:
        n, r = divmod(n, 36)
        out = d[r] + out
        if not n:
            return out


def base_dir(pack_dir: Path, model_id):
    return pack_dir / "assets" / "weapons" / "models" / "a" / GUN_CODES[model_id]


def _special(base):
    return {"type": "minecraft:special", "base": base, "model": {"type": "minecraft:player_head"}}


EMPTY = {"type": "minecraft:empty"}


def build(model, pack_dir: Path, frames_fn, animations, standing):
    """Write the base models and return {segment: layer item-model JSON} plus statistics.

    frames_fn(anim) -> (times, loop); animations = ANIMATIONS tuple."""
    folder = base_dir(pack_dir, model.id)
    if folder.exists():
        for f in folder.glob("*.json"):
            f.unlink()
    folder.mkdir(parents=True, exist_ok=True)
    files: dict[tuple, int] = {}

    def base_for(tf):
        if tf not in files:
            files[tf] = len(files)
            rot, trans, scale = tf
            data = {"display": {"firstperson_righthand": {
                "rotation": list(rot), "translation": list(trans), "scale": list(scale)}}}
            (folder / f"{_b36(files[tf])}.json").write_text(json.dumps(data, separators=(",", ":")) + "\n")
        return f"weapons:a/{GUN_CODES[model.id]}/{_b36(files[tf])}"

    layers = {}
    entries_total = 0
    for name, gname, mirrored in SEGMENTS:
        group = model.groups[gname]

        def layer_model(anim, t):
            tf = segment_transform(model, group, mirrored, anim, t)
            return EMPTY if tf is None else _special(base_for(_round(tf)))

        fallback = layer_model(model.anims[animations[standing]], 0.0)
        entries = []
        for ai, an in enumerate(animations):
            a = model.anims.get(an)
            if a is None:
                items = [(0, fallback)]
            else:
                times, _ = frames_fn(a)
                items = [(f, layer_model(a, t)) for f, t in enumerate(times)]
            for f, m in items:
                if entries and entries[-1]["model"] == m:
                    continue
                entries.append({"threshold": ai * ANIM_STRIDE + f, "model": m})
        entries_total += len(entries)
        layers[name] = {"type": "minecraft:range_dispatch", "property": "minecraft:custom_model_data",
                        "index": 1, "entries": entries, "fallback": fallback}
    return layers, {"files": len(files), "entries": entries_total}


# --------------------------------------------------------------------------------------
# Self test: reimplement the vanilla chain and check against gunlib
# --------------------------------------------------------------------------------------

def _mat4(r=None, t=(0.0, 0.0, 0.0)):
    r = r or [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    return [list(r[0]) + [t[0]], list(r[1]) + [t[1]], list(r[2]) + [t[2]], [0, 0, 0, 1]]


def _mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _apply4(m, p):
    return tuple(sum(m[i][k] * (p[k] if k < 3 else 1.0) for k in range(4)) for i in range(3))


def vanilla_chain(rot_deg, trans_px, scale):
    """ItemTransform.apply + SkullBlockRenderer for the right hand, then the hand origin;
    returns a function head-model px -> view-space px."""
    t = _mat4(None, tuple(x / 16.0 for x in trans_px))
    rx, ry, rz = (rot_x(rot_deg[0]), rot_y(rot_deg[1]), rot_z(rot_deg[2]))
    r = _mat4(m_mul(rx, m_mul(ry, rz)))
    s = _mat4([[scale[0], 0, 0], [0, scale[1], 0], [0, 0, scale[2]]])
    m = _mm(t, _mm(r, s))
    m = _mm(m, _mat4(None, (-0.5, -0.5, -0.5)))          # ItemTransform tail
    m = _mm(m, _mat4(None, (0.5, 0.0, 0.5)))             # SkullBlockRenderer
    m = _mm(m, _mat4([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]))
    m = _mm(m, _mat4([[-1, 0, 0], [0, 1, 0], [0, 0, -1]]))   # head.yRot = 180 deg
    m = _mm(_mat4(None, HAND_ORIGIN), m)

    def apply(v):
        return tuple(c * 16.0 for c in _apply4(m, tuple(x / 16.0 for x in v)))
    return apply


# ModelPart cube (minX..maxX = -4..4, -8..0, -4..4) vertices and polygon vertex order
def _head_vertices(inflate=0.0):
    x0, x1, y0, y1, z0, z1 = -4 - inflate, 4 + inflate, -8 - inflate, 0 + inflate, -4 - inflate, 4 + inflate
    v = {19: (x0, y0, z0), 20: (x1, y0, z0), 21: (x1, y1, z0), 22: (x0, y1, z0),
         23: (x0, y0, z1), 24: (x1, y0, z1), 25: (x1, y1, z1), 26: (x0, y1, z1)}
    polys = {"down": (24, 23, 19, 20), "up": (21, 22, 26, 25), "west": (19, 23, 26, 22),
             "north": (20, 19, 22, 21), "east": (24, 20, 21, 25), "south": (23, 24, 25, 26)}
    return v, polys


def _expected_face(face, mirrored):
    """Cube face (axis, sign) in bone rest space on which the named head face must land."""
    west_sign = -1 if mirrored else 1
    return {"down": (1, 1), "up": (1, -1), "north": (2, -1), "south": (2, 1),
            "west": (0, west_sign), "east": (0, -west_sign)}[face]


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _inv_bone(b, p):
    """Rest-space point mapping to view-space p under bone transform b (rigid)."""
    q = _sub(p, b.t)
    return tuple(sum(b.r[row][i] * q[row] for row in range(3)) for i in range(3))


def selftest(model, pack_dir: Path, item_name: str, frames_fn, animations, standing, verbose=False):
    """Read feather.json + base models back from disk and check every (animation, frame, segment).
    Returns (max corner error px, checks)."""
    feather = json.loads((pack_dir / "assets" / "minecraft" / "items" / "feather.json").read_text())
    item_model = f"weapons:item/{item_name}"
    entry = next(e["model"] for e in feather["model"]["entries"]
                 if e["model"].get("type") == "minecraft:select"
                 and e["model"].get("fallback", {}).get("model") == item_model)
    case = next(c for c in entry["cases"] if c["when"] == "firstperson_righthand")["model"]
    assert case["type"] == "minecraft:composite" and len(case["models"]) == 4, "composite layout"
    assert entry["cases"][1]["when"] == "firstperson_lefthand" and entry["cases"][1]["model"] == EMPTY
    max_err = 0.0
    checks = 0

    def display(base_id):
        ns, path = base_id.split(":")
        assert ns == "weapons"
        d = json.loads((pack_dir / "assets" / "weapons" / "models" / f"{path}.json").read_text())
        disp = d["display"]["firstperson_righthand"]
        return disp["rotation"], disp["translation"], disp["scale"]

    def dispatch(layer, value):
        assert layer["property"] == "minecraft:custom_model_data" and layer["index"] == 1
        ths = [e["threshold"] for e in layer["entries"]]
        assert ths == sorted(ths) and len(set(ths)) == len(ths)
        pick = layer["fallback"]
        for e in layer["entries"]:
            if e["threshold"] <= value:
                pick = e["model"]
        return pick

    for (name, gname, mirrored), layer in zip(SEGMENTS, case["models"][1:]):
        group = model.groups[gname]
        cube = _skin_cube(model, group)
        lo, hi = cube.frm, cube.to
        crn = (lo, hi)
        for ai, an in enumerate(animations):
            a = model.anims.get(an)
            if a is None:
                frames = [(0, model.anims[animations[standing]], 0.0)]
                probes = [ai * ANIM_STRIDE, ai * ANIM_STRIDE + 17, ai * ANIM_STRIDE + 255]
            else:
                times, _ = frames_fn(a)
                frames = [(f, a, t) for f, t in enumerate(times)]
                probes = None
            for f, aa, t in frames:
                for value in (probes or [ai * ANIM_STRIDE + f]):
                    m = dispatch(layer, value)
                    hidden = model.bone_scale(group, aa, t) < 0.01
                    if hidden:
                        assert m == EMPTY, f"{model.id}/{name} {an}/{f}: hidden bone must be empty"
                        checks += 1
                        continue
                    assert m["type"] == "minecraft:special" and m["model"] == {"type": "minecraft:player_head"}, m
                    rot, trans, scale = display(m["base"])
                    assert max(abs(x) for x in trans) <= MAX_T_PX and max(abs(x) for x in scale) <= MAX_S
                    chain = vanilla_chain(rot, trans, scale)
                    b = model.bone_xf(group, aa, t)
                    for infl, hat in ((0.0, False),):
                        verts, polys = _head_vertices(infl)
                        centre = chain(tuple(sum(verts[k][i] for k in verts) / 8 for i in range(3)))
                        for face, idx in polys.items():
                            pts = [chain(verts[k]) for k in idx]
                            local = [_inv_bone(b, p) for p in pts]
                            axis, sign = _expected_face(face, mirrored)
                            # all four verts lie on the expected cube face
                            want = hi[axis] if sign > 0 else lo[axis]
                            for p in local:
                                err = abs(p[axis] - want)
                                max_err = max(max_err, err)
                                assert err < SELFTEST_TOL_PX, f"{model.id}/{name} {an}/{f} {face}: plane err {err}"
                            # and inside its rect (corner errors)
                            for p in local:
                                for i in range(3):
                                    if i == axis:
                                        continue
                                    e = min(abs(p[i] - lo[i]), abs(p[i] - hi[i]))
                                    max_err = max(max_err, e)
                                    assert e < SELFTEST_TOL_PX, f"{model.id}/{name} {an}/{f} {face}: corner err {e}"
                            # vertical UV direction: k0/k1 are the v1 edge (top for the side faces)
                            if face in ("north", "south", "west", "east"):
                                top = local[0][1]
                                bot = local[2][1]
                                assert top > bot + 1e-6, f"{model.id}/{name}: side face {face} upside down"
                            # winding: outward normal sign vs det (mirrored = reversed)
                            fc = tuple(sum(p[i] for p in pts) / 4 for i in range(3))
                            nrm = _cross(_sub(pts[1], pts[0]), _sub(pts[2], pts[1]))
                            outward = _sub(fc, centre)
                            wind = _dot(nrm, outward)
                            assert (wind < 0) == mirrored, f"{model.id}/{name} {an}/{f} {face}: winding {wind}"
                    # all 8 head corners vs cube corners (as a set)
                    verts, _ = _head_vertices(0.0)
                    got = [_inv_bone(b, chain(v)) for v in verts.values()]
                    want = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
                    for g_ in got:
                        e = min(max(abs(gi - wi) for gi, wi in zip(g_, w_)) for w_ in want)
                        max_err = max(max_err, e)
                        assert e < SELFTEST_TOL_PX, f"{model.id}/{name} {an}/{f}: corner {g_} is {e} px off the cube"
                    assert len({tuple(round(c, 2) for c in g_) for g_ in got}) == 8
                    checks += 1
    if verbose:
        print(f"[{model.id}] arm selftest ok: {checks} (segment, frame) checks, max error {max_err:.3f} px")
    return max_err, checks


def main():
    """Rebuild each gun model (without writing) and verify the committed pack files."""
    import runpy
    import gunlib
    import viewmodel_bake as vb

    root = gunlib.ROOT
    total_err, total = 0.0, 0
    for script in sorted(HERE.glob("*.py")):
        if script.name in ("gunlib.py", "viewmodel_bake.py", "viewmodel_arms.py"):
            continue
        captured = {}

        def fake_write(self, pack_dir=root, item_display=None, item_name=None, **kw):
            gunlib.deconflict(self)
            self.finish()
            captured["m"] = (self, item_name or self.id)

        orig = gunlib.GunModel.write
        gunlib.GunModel.write = fake_write
        try:
            runpy.run_path(str(script), run_name="__main__")
        finally:
            gunlib.GunModel.write = orig
        m, item_name = captured["m"]
        err, n = selftest(m, root, item_name, vb._frames, vb.ANIMATIONS, vb.STANDING, verbose=True)
        total_err, total = max(total_err, err), total + n
    print(f"all guns ok: {total} checks, max error {total_err:.3f} px")


if __name__ == "__main__":
    main()
