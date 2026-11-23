"""Bake a GunModel into the first-person "sgvm" viewmodel (objmc-style core shader model).

The gun is drawn as the held item in the first-person right hand. The item model is a list of
dummy quads (one per real face); the core shader
``assets/minecraft/shaders/core/rendertype_item_entity_translucent_cull.vsh`` moves every vertex
to its real camera-space position, read from the model's data texture. That keeps the viewmodel
locked to the camera by the client itself (no entities, no culling, no server lag).

Derived from objmc by Godlander (MIT, see LICENSE-OBJMC): face header pixels pointing at a
top-left marker, the first-person hand detection and the camera-space offset. The data layout is
a skeletal variant so long animations stay small: static per-vertex rest positions plus one 3x4
matrix per bone per tick (20 fps), interpolated linearly by the shader.

Texture layout (width W, all pixels opaque unless noted):

  row 0                 header. x0 marker (83,71,86,77); x1 (W, texture height);
                        x2 (vertex count 24 bit, bone count); x3 (texture row, vertex row);
                        x4 (frame row, animation count); x8+i animation i = (start frame 16 bit,
                        frame count, flags: bit0 loop). Frame count 0 = missing (-> standing).
  rows 1..              one pixel per face: (x, y) offset of the pixel from the top-left, so the
                        shader finds the marker from any face (works inside the item atlas).
  texture rows          the gun texture (128x128), W x TEX_H.
  vertex rows           per vertex (face*4 + corner) 5 pixels: x, y, z (24-bit fixed, blocks,
                        camera space at rest), (bone, u 16 bit), (0, v 16 bit).
  frame rows            per global frame, per bone 12 pixels: 3x3 matrix (row major) then the
                        translation, 24-bit fixed: value = (rgb - 2^23) / 65536.

Vertex row 5th pixel: (arm flag, v 16 bit). Arm vertices (flag 1) belong to the skinned-arm quads.

Item tints (custom_model_data colors[k]) are 24-bit values V = 0xRRGGBB:
  C = V >> 13 (11 bit): animation = C / 160, start game tick = C % 160 (160 divides 24000).
  P = V & 0x1FFF: colour R4 = P >> 9, G5 = (P >> 4) & 31, B4 = P & 15; P == 0x0010 = transparent.
colors[0] is the gun tint (tintindex 0, only C matters). Arm quads (right forearm, left upper arm,
left forearm; base + sleeve layer) are subdivided into skin texels; every texel quad has
tintindex k = its arm slot (1..N, see ``arm_slots()`` and objmc_arm_slots.json) and takes its colour
from colors[k] (the plugin fills them from the player's skin) with the same C as colors[0], so gun and
arms play the same animation in lockstep and interpolate smoothly at any frame rate. The .vsh does
the playback (``dt = mod(GameTime*24000 - start, 160)``, loop: mod frames, one-shot: clamp) and the
colour decode; the .fsh shades arm quads flat.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image

# Order is a contract with SovereignGuns core/ObjmcTime.ANIMATIONS.
ANIMATIONS = ("equip", "unequip", "standing", "sprint", "aiming", "shoot", "aiming_shoot",
              "reload", "reload_fail", "inspect", "firearm", "scoped")
# control C = anim * 160 + start must stay < 2048 (11 bits), so 12 slots is the maximum
assert len(ANIMATIONS) <= 12, "too many animation slots for the 11-bit tint control"

# The server plays ONE reload animation for every reload, retimed to the weapon's reload time.
# Reload duration in ticks per gun model id. MUST match plugins/WeaponMechanics/weapons/*.yml
# Reload_Duration; the "reload" slot is resampled to exactly ticks + 1 frames.
RELOAD_TICKS = {
    "ak47": 57, "g3": 50, "m14": 65, "ppsh41": 104, "uzi": 25, "m3": 31,
    "dragunov": 70, "ssg69": 50, "remington700": 40,
}
STANDING = ANIMATIONS.index("standing")
MARKER = (83, 71, 86, 77)
WIDTH = 256
TPS = 20

# Vanilla first-person right-hand item origin (ItemInHandRenderer.applyItemArmTransform) in
# blocks; the display translation cancels it so the shader's anchor is the eye.
ARM_ORIGIN = (0.56, -0.52, -0.72)
ANCHOR_SCALE = 0.001


def _fixed(v):
    i = int(round(v * 65536)) + 8388608
    if not 0 <= i < 1 << 24:
        raise ValueError(f"value {v} out of the +-128 fixed range")
    return ((i >> 16) & 255, (i >> 8) & 255, i & 255, 255)


def _u16(v):
    i = max(0, min(65535, int(round(v * 65535))))
    return (i >> 8) & 255, i & 255


def _inv(xf):
    """Inverse of a rigid Xf (rotation part orthonormal)."""
    from gunlib import Xf, m_t, m_vec
    rt = m_t(xf.r)
    t = m_vec(rt, xf.t)
    return Xf(rt, (-t[0], -t[1], -t[2]))


# corners() index = x*4 + y*2 + z; counter-clockwise seen from outside the cube
CCW = {
    "north": (0, 2, 6, 4), "south": (1, 5, 7, 3), "east": (4, 6, 7, 5),
    "west": (0, 1, 3, 2), "up": (2, 3, 7, 6), "down": (0, 4, 5, 1),
}


def _face_uv01(face, p, lo, hi):
    """Vanilla face UV orientation, (0,0) = top-left of the face's UV rect."""
    s = [max(1e-9, hi[i] - lo[i]) for i in range(3)]
    x, y, z = ((p[i] - lo[i]) / s[i] for i in range(3))
    return {
        "north": (1 - x, 1 - y), "south": (x, 1 - y), "east": (1 - z, 1 - y),
        "west": (z, 1 - y), "up": (x, z), "down": (x, 1 - z),
    }[face]


def _frames(anim):
    """Sample times (seconds) of an animation: one per tick."""
    if anim.loop == "loop":
        n = max(1, int(round(anim.length * TPS)))
        return [i * anim.length / n for i in range(n)], True
    n = int(math.ceil(anim.length * TPS - 1e-6)) + 1
    return [min(anim.length, i / TPS) for i in range(n)], False


def slot_plan(model):
    """Per animation slot: (source Animation or None, sample times, loop, hidden).

    "reload" is the gun's full sequence (script "reload_empty" if present, else "reload")
    resampled to RELOAD_TICKS frames (ticks + 1, t_i = min(L, i * L / ticks), one-shot);
    "scoped" is synthetic: one looping frame with every bone hidden (sniper scope overlay)."""
    plan = {}
    for name in ANIMATIONS:
        if name == "reload":
            src = model.anims.get("reload_empty") or model.anims.get("reload")
            if src is None:
                plan[name] = (None, [], False, False)
                continue
            ticks = RELOAD_TICKS[model.id]
            plan[name] = (src, [min(src.length, i * src.length / ticks) for i in range(ticks + 1)],
                          False, False)
        elif name == "scoped":
            plan[name] = (None, [0.0], True, True)
        else:
            a = model.anims.get(name)
            if a is None:
                plan[name] = (None, [], False, False)
            else:
                times, loop = _frames(a)
                plan[name] = (a, times, loop, False)
    return plan


def bake(model, pack_dir: Path, item_name: str):
    from gunlib import Xf

    gun_tex = model.texture.convert("RGBA")
    gsz = gun_tex.size[0]
    tex_h = max(gsz, 32)
    tex = Image.new("RGBA", (WIDTH, tex_h), (0, 0, 0, 0))
    tex.paste(gun_tex, (0, 0))

    # ---- faces -------------------------------------------------------------------------
    bones = []
    bone_index = {}
    quads = []   # (bone, [(rest_xyz_blocks, (u, v))] * 4, tintindex (0 gun, k arm slot), arm flag)
    for c in model.cubes:
        if c.material == "skin":
            continue   # arm skin cubes become texel quads below
        g = c.group
        if g.name not in bone_index:
            bone_index[g.name] = len(bones)
            bones.append(g)
        full = model.bone_xf(g, None, 0.0).then(Xf.pivot(c.origin, c.rotation))
        corners = c.corners()
        lo, hi = corners[0], corners[7]
        for f, idx in CCW.items():
            if f in c.faces_off:
                continue
            rect = c.uv.get(f)
            if rect is None:
                continue
            x1, y1, x2, y2 = rect
            verts = []
            for i in idx:
                p = full.apply(corners[i])
                u, v = _face_uv01(f, corners[i], lo, hi)
                verts.append((tuple(q / 16.0 for q in p),
                              ((x1 + u * (x2 - x1)) / WIDTH, (y1 + v * (y2 - y1)) / tex_h)))
            quads.append((bone_index[g.name], verts, 0, 0))

    # arm texel quads (tintindex = slot of the skin pixel)
    slots = arm_slots()
    slot_of = {px_: k + 1 for k, px_ in enumerate(slots["slots"])}
    arm_quads = _arm_quads(model)
    got = sorted({q["pixel"] for q in arm_quads}, key=lambda p: (p[1], p[0]))
    if got != slots["slots"]:
        raise ValueError(f"{model.id}: arm slot list differs from the canonical one")
    for q in arm_quads:
        g = q["group"]
        if g.name not in bone_index:
            bone_index[g.name] = len(bones)
            bones.append(g)
        full = model.bone_xf(g, None, 0.0).then(Xf.pivot(q["origin"], (0.0, 0.0, 0.0)))
        verts = [(tuple(c / 16.0 for c in full.apply(p)), (0.0, 0.0)) for p in q["corners"]]
        quads.append((bone_index[g.name], verts, slot_of[q["pixel"]], 1))
    n_arm = len(arm_quads)
    if len(bones) > 255:
        raise ValueError(f"{model.id}: too many bones ({len(bones)})")

    # ---- animation frames --------------------------------------------------------------
    rest_inv = [_inv(model.bone_xf(g, None, 0.0)) for g in bones]
    table = []
    frames = []   # per global frame: list of 12-tuples per bone
    for name, (a, times, loop, hidden) in slot_plan(model).items():
        if not times:
            table.append((0, 0, 0))
            continue
        if len(times) > 140:   # dt in [150, 160) is read as "not started yet" by the shader
            raise ValueError(f"{model.id}/{name}: {len(times)} frames > 140 (shader time window)")
        table.append((len(frames), len(times), 1 if loop else 0))
        for t in times:
            mats = []
            for g, inv in zip(bones, rest_inv):
                if hidden or model.bone_scale(g, a, t) < 0.01:
                    mats.append((0.0,) * 12)
                    continue
                m = model.bone_xf(g, a, t).then(inv)
                r = m.r
                mats.append((r[0][0], r[0][1], r[0][2], r[1][0], r[1][1], r[1][2],
                             r[2][0], r[2][1], r[2][2], m.t[0] / 16.0, m.t[1] / 16.0, m.t[2] / 16.0))
            frames.append(mats)
    if len(frames) >= 65536:
        raise ValueError(f"{model.id}: too many frames")

    # ---- layout ------------------------------------------------------------------------
    nfaces = len(quads)
    nverts = nfaces * 4
    nb = len(bones)
    face_rows = math.ceil(nfaces / WIDTH)
    row_tex = 1 + face_rows
    row_vert = row_tex + tex_h
    vert_rows = math.ceil(nverts * 5 / WIDTH)
    row_frame = row_vert + vert_rows
    frame_rows = math.ceil(len(frames) * nb * 12 / WIDTH)
    height = row_frame + frame_rows
    height = (height + 15) // 16 * 16   # keep the item atlas at full mip level
    if max(row_frame, row_vert, row_tex) >= 65536 or height > 16384:
        raise ValueError(f"{model.id}: data texture too tall ({height})")

    out = Image.new("RGBA", (WIDTH, height), (0, 0, 0, 255))
    px = out.load()
    px[0, 0] = MARKER
    px[1, 0] = (WIDTH >> 8, WIDTH & 255, tex_h >> 8, tex_h & 255)
    px[2, 0] = ((nverts >> 16) & 255, (nverts >> 8) & 255, nverts & 255, nb)
    px[3, 0] = (row_tex >> 8, row_tex & 255, row_vert >> 8, row_vert & 255)
    px[4, 0] = (row_frame >> 8, row_frame & 255, len(ANIMATIONS), 255)
    for i, (start, n, loop) in enumerate(table):
        px[8 + i, 0] = (start >> 8, start & 255, n, 254 | loop)   # alpha >= 254 keeps it opaque-ish

    out.paste(tex, (0, row_tex))

    def put(row, i, c):
        px[i % WIDTH, row + i // WIDTH] = c

    elements = []
    for fi, (bone, verts, tint, arm) in enumerate(quads):
        hx, hy = fi % WIDTH, 1 + fi // WIDTH
        px[hx, hy] = (hx >> 8, hx & 255, hy >> 8, hy & 255)
        elements.append({
            # Tiny dummy: the shader adds the real offset to each corner's own anchor, so the
            # corner spread (x the 0.001 display scale) must be negligible or neighbouring quads
            # crack apart (a 16 px element left ~1 mm seams between arm texels).
            "from": [15.99, 7.99, 8], "to": [16.01, 8.01, 8],
            "faces": {"north": {
                "uv": [round((hx + 0.1) * 16 / WIDTH, 6), round((hy + 0.1) * 16 / height, 6),
                       round((hx + 0.9) * 16 / WIDTH, 6), round((hy + 0.9) * 16 / height, 6)],
                "texture": "#0", "tintindex": tint}},
        })
        for k, (p, (u, v)) in enumerate(verts):
            base = (fi * 4 + k) * 5
            put(row_vert, base, _fixed(p[0]))
            put(row_vert, base + 1, _fixed(p[1]))
            put(row_vert, base + 2, _fixed(p[2]))
            uh, ul = _u16(u)
            vh, vl = _u16(v)
            put(row_vert, base + 3, (bone, uh, ul, 255))
            put(row_vert, base + 4, (arm, vh, vl, 255))

    i = 0
    for mats in frames:
        for m in mats:
            for val in m:
                put(row_frame, i, _fixed(val))
                i += 1

    tex_id = f"weapons:item/objmc/{model.id}"
    model_json = {
        "credit": "SovereignMC tools/generate/guns/viewmodel_bake.py (objmc-derived, MIT)",
        "textures": {"0": tex_id, "particle": f"weapons:item/gun/{model.id}"},
        "elements": elements,
        "display": {
            "firstperson_righthand": {
                "rotation": [0, 0, 0],
                "translation": [round(-ARM_ORIGIN[i] * 16, 4) for i in range(3)],
                "scale": [ANCHOR_SCALE] * 3,
            },
        },
    }
    tex_path = pack_dir / "assets" / "weapons" / "textures" / "item" / "objmc" / f"{model.id}.png"
    tex_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(tex_path, optimize=True)
    mdl_path = pack_dir / "assets" / "weapons" / "models" / "item" / "objmc" / f"{model.id}.json"
    mdl_path.parent.mkdir(parents=True, exist_ok=True)
    mdl_path.write_text(json.dumps(model_json, separators=(",", ":")) + "\n")
    _write_anim_table(model, pack_dir)
    _write_arm_slots(slots, pack_dir)
    _patch_feather(pack_dir, item_name, f"weapons:item/objmc/{model.id}", len(slots["slots"]))
    checks = _selftest_uv(model)
    print(f"[{model.id}] viewmodel: {nfaces} quads ({nfaces - n_arm} gun + {n_arm} arm), {nb} bones, "
          f"{len(frames)} frames, texture {WIDTH}x{height} -> {tex_path.relative_to(pack_dir)}; "
          f"arm uv selftest {checks} quads ok")
    return {"faces": nfaces, "bones": nb, "frames": len(frames), "height": height,
            "table": table, "quads": quads, "image": out, "rows": (row_tex, row_vert, row_frame)}


# --------------------------------------------------------------------------------------
# Skinned arms: every visible skin texel is a quad whose colour is a per-texel item tint.
# --------------------------------------------------------------------------------------

ARM_SEGMENTS = {   # bone group -> (side, forearm?)
    "prfa_right_forearm": ("right", True),
    "pla_left_arm": ("left", False),
    "plfa_left_forearm": ("left", True),
}
SLEEVE_INFLATE = 0.234375   # 0.25 skin texel (1 texel = 0.9375 model px)
# skin origin of the arm box net (base, sleeve) per side (classic 4 wide arm)
SKIN_NET = {"right": ((40, 16), (40, 32)), "left": ((32, 48), (48, 48))}


def _face_cells(face, lo, hi):
    """Texel sub-quads of one cube face: (corners CCW from outside, cell centre)."""
    corners = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    c = [corners[i] for i in CCW[face]]
    d1 = [c[1][i] - c[0][i] for i in range(3)]
    d3 = [c[3][i] - c[0][i] for i in range(3)]
    n1 = 6 if abs(d1[1]) > 0 else 4
    n3 = 6 if abs(d3[1]) > 0 else 4

    def pt(s, t):
        return tuple(c[0][i] + d1[i] * s / n1 + d3[i] * t / n3 for i in range(3))
    out = []
    for b in range(n3):
        for a in range(n1):
            quad = [pt(a, b), pt(a + 1, b), pt(a + 1, b + 1), pt(a, b + 1)]
            ctr = tuple((pt(a, b)[i] + pt(a + 1, b + 1)[i]) / 2 for i in range(3))
            out.append((quad, ctr))
    return out


def _skin_pixel(side, sleeve, fore, face, fr):
    """Skin pixel of the point with cube fractions fr=(fx, fy, fz) (bone space, 0 = -axis)
    on `face`. See AGENTS.md; this is vanilla's arm UV net with x/y negated."""
    cx = min(3, int(fr[0] * 4))
    cy = min(5, int((1 - fr[1]) * 6))
    cz = min(3, int(fr[2] * 4))
    row = (26 if fore else 20) + cy
    x, y = {
        "up": (44 + 3 - cx, 16 + 3 - cz),
        "down": (48 + 3 - cx, 16 + 3 - cz),
        "east": (40 + 3 - cz, row),
        "north": (44 + 3 - cx, row),
        "west": (48 + cz, row),
        "south": (52 + cx, row),
    }[face]
    # the net above is the right arm base at (40, 16)
    bx, by = SKIN_NET[side][1 if sleeve else 0]
    return x - 40 + bx, y - 16 + by


def _segment_quads(seg, lo, hi, sleeve):
    side, fore = ARM_SEGMENTS[seg]
    if sleeve:
        lo = tuple(v - SLEEVE_INFLATE for v in lo)
        hi = tuple(v + SLEEVE_INFLATE for v in hi)
    out = []
    for face in CCW:
        for quad, ctr in _face_cells(face, lo, hi):
            fr = tuple((ctr[i] - lo[i]) / (hi[i] - lo[i]) for i in range(3))
            out.append({"seg": seg, "sleeve": sleeve, "face": face, "corners": quad, "centre": ctr,
                        "frac": fr, "pixel": _skin_pixel(side, sleeve, fore, face, fr)})
    return out


def arm_slots():
    """Canonical slot list (same for every gun): the union of skin pixels of all texel quads,
    sorted by (y, x); slot k = index + 1."""
    pix = {}
    for seg in ARM_SEGMENTS:
        for sleeve in (False, True):
            for q in _segment_quads(seg, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0), sleeve):
                pix[q["pixel"]] = sleeve
    slots = sorted(pix, key=lambda p: (p[1], p[0]))
    return {"slots": slots, "sleeve": [pix[p] for p in slots]}


def _arm_quads(model):
    """All arm texel quads of a gun model, with corners in the skin cube's bone space."""
    out = []
    for seg in ARM_SEGMENTS:
        cubes = [c for c in model.cubes if c.group.name == seg and c.material == "skin" and c.name == "skin"]
        assert len(cubes) == 1, f"{model.id}: {seg} needs exactly one base skin cube, has {len(cubes)}"
        c = cubes[0]
        assert c.rotation == (0.0, 0.0, 0.0) and c.inflate == 0.0, f"{model.id}: {seg} skin cube is rotated/inflated"
        sz = c.size()
        assert all(abs(sz[i] - e) < 1e-6 for i, e in enumerate((3.75, 5.625, 3.75))), f"{model.id}: {seg} size {sz}"
        corners = c.corners()
        lo, hi = corners[0], corners[7]
        for sleeve in (False, True):
            for q in _segment_quads(seg, lo, hi, sleeve):
                q["group"] = c.group
                q["origin"] = c.origin
                out.append(q)
    return out


def _vanilla_pixel(side, sleeve, fore, face, fr):
    """Independent derivation through vanilla ModelPart.Cube's polygons (box 4x12x4, x/y
    negated into bone space, a segment is half the arm)."""
    tx, ty = SKIN_NET[side][1 if sleeve else 0]
    w, h, d = 4, 12, 4
    u0, u1, u2, u3, u4, u5 = tx, tx + d, tx + d + w, tx + d + 2 * w, tx + 2 * d + w, tx + 2 * d + 2 * w
    v0, v1, v2 = ty, ty + d, ty + d + h
    mn, mx = (0.0, 0.0, 0.0), (float(w), float(h), float(d))
    v = [None] * 8
    for i in range(8):
        v[i] = (mx[0] if i in (1, 2, 5, 6) else mn[0], mx[1] if i in (2, 3, 6, 7) else mn[1],
                mx[2] if i in (4, 5, 6, 7) else mn[2])
    polys = {   # name: (vertex ids, (x1, y1, x2, y2)) with vertex UVs (x2,y1),(x1,y1),(x1,y2),(x2,y2)
        "down": ((5, 4, 0, 1), (u1, v0, u2, v1)), "up": ((2, 3, 7, 6), (u2, v1, u3, v0)),
        "west": ((0, 4, 7, 3), (u0, v1, u1, v2)), "north": ((1, 0, 3, 2), (u1, v1, u2, v2)),
        "east": ((5, 1, 2, 6), (u2, v1, u4, v2)), "south": ((4, 5, 6, 7), (u4, v1, u5, v2)),
    }
    # vanilla space point: x_v = -x_bone, y_v = -y_bone (down is +), z_v = z_bone; arm = 12 tall
    xv = w * (1 - fr[0])
    yv = (6 if fore else 0) + 6 * (1 - fr[1])
    zv = d * fr[2]
    # bone face -> vanilla face (x and y flip)
    vface = {"east": "west", "west": "east", "up": "down", "down": "up", "north": "north", "south": "south"}[face]
    ids, (x1, y1, x2, y2) = polys[vface]
    p = (xv, yv, zv)
    if vface in ("west", "east"):
        p = (mn[0] if vface == "west" else mx[0], yv, zv)
    elif vface in ("up", "down"):
        p = (xv, mn[1] if vface == "down" else mx[1], zv)   # vanilla DOWN = minY = shoulder cap
    else:
        p = (xv, yv, mn[2] if vface == "north" else mx[2])
    uvs = [(x2, y1), (x1, y1), (x1, y2), (x2, y2)]
    a, b, c_, d_ = (v[i] for i in ids)
    e1 = [b[i] - a[i] for i in range(3)]
    e3 = [d_[i] - a[i] for i in range(3)]
    rel = [p[i] - a[i] for i in range(3)]
    s = sum(rel[i] * e1[i] for i in range(3)) / sum(q * q for q in e1)
    t = sum(rel[i] * e3[i] for i in range(3)) / sum(q * q for q in e3)
    u = uvs[0][0] + s * (uvs[1][0] - uvs[0][0]) + t * (uvs[3][0] - uvs[0][0])
    vv = uvs[0][1] + s * (uvs[1][1] - uvs[0][1]) + t * (uvs[3][1] - uvs[0][1])
    return int(math.floor(u + 1e-9)), int(math.floor(vv + 1e-9))


def _selftest_uv(model):
    """Every texel quad's centre must hit the same skin pixel through the vanilla polygon net."""
    n = 0
    for q in _arm_quads(model):
        side, fore = ARM_SEGMENTS[q["seg"]]
        want = _vanilla_pixel(side, q["sleeve"], fore, q["face"], q["frac"])
        assert want == q["pixel"], f"{model.id}: {q['seg']} {q['face']} sleeve={q['sleeve']} {q['frac']}: {q['pixel']} != vanilla {want}"
        n += 1
    return n


def _write_arm_slots(slots, pack_dir: Path):
    """objmc_arm_slots.json: {"version": 1, "slots": [[x, y]], "sleeve": [bool]} (contract with SovereignGuns)."""
    data = {"version": 1, "slots": [list(p) for p in slots["slots"]], "sleeve": slots["sleeve"]}
    targets = [Path(__file__).resolve().parent / "objmc_arm_slots.json"]
    plugin_res = pack_dir.parent / "SovereignGuns" / "src" / "main" / "resources"
    if plugin_res.is_dir():
        targets.append(plugin_res / "objmc_arm_slots.json")
    for path in targets:
        path.write_text(json.dumps(data, separators=(",", ":")) + "\n")


def _write_anim_table(model, pack_dir: Path):
    """Merge this gun's animations into objmc_animations.json (contract with SovereignGuns).

    {"<model id>": {"<anim>": {"frames": n, "loop": bool, "length": seconds}}}; written next to
    the generators and, when the sibling plugin checkout exists, into its resources."""
    entry = {}
    for name, (a, times, loop, hidden) in slot_plan(model).items():
        if not times:
            continue
        if name == "reload":
            length = RELOAD_TICKS[model.id] / TPS
        else:
            length = float(a.length) if a is not None else 1.0 / TPS
        entry[name] = {"frames": len(times), "loop": loop, "length": length}
    targets = [Path(__file__).resolve().parent / "objmc_animations.json"]
    plugin_res = pack_dir.parent / "SovereignGuns" / "src" / "main" / "resources"
    if plugin_res.is_dir():
        targets.append(plugin_res / "objmc_animations.json")
    for path in targets:
        try:
            table = json.loads(path.read_text())
        except (OSError, ValueError):
            table = {}
        table[model.id] = entry
        path.write_text(json.dumps(table, indent=2, sort_keys=True) + "\n")


ANIM_SHIFT = 13
SLOT_TRANSPARENT = 0x0010
SKIN_DEFAULT = (0xB4, 0x84, 0x6C)


def quantize(r, g, b):
    """24-bit rgb -> P (R4 G5 B4), the tint colour payload."""
    return (round(r / 255 * 15) << 9) | (round(g / 255 * 31) << 4) | round(b / 255 * 15)


def feather_entry(item_model: str, viewmodel: str, sleeve):
    ctrl = (STANDING * 160) << ANIM_SHIFT
    skin_p = quantize(*SKIN_DEFAULT)
    assert skin_p != SLOT_TRANSPARENT
    tints = [{"type": "minecraft:custom_model_data", "index": 0, "default": ctrl}]
    for k, sl in enumerate(sleeve):
        tints.append({"type": "minecraft:custom_model_data", "index": k + 1,
                      "default": ctrl | (SLOT_TRANSPARENT if sl else skin_p)})
    return {
        "type": "minecraft:select",
        "property": "minecraft:display_context",
        "cases": [
            {"when": "firstperson_righthand", "model": {
                "type": "minecraft:model", "model": viewmodel, "tints": tints}},
            {"when": "firstperson_lefthand", "model": {"type": "minecraft:empty"}},
        ],
        "fallback": {"type": "minecraft:model", "model": item_model},
    }


def _patch_feather(pack_dir: Path, item_name: str, viewmodel: str, n_slots: int):
    """Point the gun's feather.json entry (found by its fallback item model) at the viewmodel."""
    path = pack_dir / "assets" / "minecraft" / "items" / "feather.json"
    data = json.loads(path.read_text())
    item_model = f"weapons:item/{item_name}"
    hit = False
    for e in data["model"]["entries"]:
        m = e["model"]
        if m.get("type") == "minecraft:select" and m.get("fallback", {}).get("model") == item_model:
            e["model"] = feather_entry(item_model, viewmodel, arm_slots()["sleeve"])
            hit = True
    if not hit:
        raise ValueError(f"feather.json has no entry for {item_model}")
    # no re-equip bob when the plugin rewrites the held gun's tint
    data["hand_animation_on_swap"] = False
    path.write_text(json.dumps(data, indent=4) + "\n")
