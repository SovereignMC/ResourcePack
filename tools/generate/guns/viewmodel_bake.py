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

Item tint (custom_model_data colors[0]) controls playback; see the .vsh and the plugin's
ObjmcTime: r = paused bit (0x80) | animation index (ANIMATIONS order), gb = tick value.

The gun is drawn WITHOUT arms. The player's skinned arms are extra composite layers of the
feather.json entry (``minecraft:player_head`` special models squeezed into arm segments by their
base model display transforms, see ``viewmodel_arms.py`` and the ``core/entity`` override). They
follow the same frame as the gun through custom_model_data floats[1] = animIndex*1000 + frame.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image

# Order is a contract with SovereignGuns core/ObjmcTime.ANIMATIONS.
ANIMATIONS = ("equip", "unequip", "standing", "sprint", "aiming", "shoot", "aiming_shoot",
              "reload", "reload_empty", "inspect", "firearm")
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
    quads = []   # (bone, [(rest_xyz_blocks, (u, v))] * 4)
    for c in model.cubes:
        if c.material == "skin":
            continue   # arms are skinned head layers (viewmodel_arms.py), not part of the gun
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
            quads.append((bone_index[g.name], verts))
    if len(bones) > 255:
        raise ValueError(f"{model.id}: too many bones ({len(bones)})")

    # ---- animation frames --------------------------------------------------------------
    rest_inv = [_inv(model.bone_xf(g, None, 0.0)) for g in bones]
    table = []
    frames = []   # per global frame: list of 12-tuples per bone
    for name in ANIMATIONS:
        a = model.anims.get(name)
        if a is None:
            table.append((0, 0, 0))
            continue
        times, loop = _frames(a)
        if len(times) > 255:
            raise ValueError(f"{model.id}/{name}: {len(times)} frames > 255")
        table.append((len(frames), len(times), 1 if loop else 0))
        for t in times:
            mats = []
            for g, inv in zip(bones, rest_inv):
                if model.bone_scale(g, a, t) < 0.01:
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
    for fi, (bone, verts) in enumerate(quads):
        hx, hy = fi % WIDTH, 1 + fi // WIDTH
        px[hx, hy] = (hx >> 8, hx & 255, hy >> 8, hy & 255)
        elements.append({
            "from": [8, 0, 8], "to": [24, 16, 8],
            "faces": {"north": {
                "uv": [round((hx + 0.1) * 16 / WIDTH, 6), round((hy + 0.1) * 16 / height, 6),
                       round((hx + 0.9) * 16 / WIDTH, 6), round((hy + 0.9) * 16 / height, 6)],
                "texture": "#0", "tintindex": 0}},
        })
        for k, (p, (u, v)) in enumerate(verts):
            base = (fi * 4 + k) * 5
            put(row_vert, base, _fixed(p[0]))
            put(row_vert, base + 1, _fixed(p[1]))
            put(row_vert, base + 2, _fixed(p[2]))
            uh, ul = _u16(u)
            vh, vl = _u16(v)
            put(row_vert, base + 3, (bone, uh, ul, 255))
            put(row_vert, base + 4, (0, vh, vl, 255))

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
    import viewmodel_arms
    layers, arm_stats = viewmodel_arms.build(model, pack_dir, _frames, ANIMATIONS, STANDING)
    _write_anim_table(model, pack_dir)
    _patch_feather(pack_dir, item_name, f"weapons:item/objmc/{model.id}", layers)
    arm_err, arm_checks = viewmodel_arms.selftest(model, pack_dir, item_name, _frames, ANIMATIONS, STANDING)
    print(f"[{model.id}] viewmodel: {nfaces} faces, {nb} bones, {len(frames)} frames, "
          f"texture {WIDTH}x{height} -> {tex_path.relative_to(pack_dir)}")
    print(f"[{model.id}] arms: {arm_stats['files']} base models, {arm_stats['entries']} dispatch entries; "
          f"selftest {arm_checks} checks, max error {arm_err:.3f} px")
    return {"faces": nfaces, "bones": nb, "frames": len(frames), "height": height,
            "table": table, "quads": quads, "image": out, "rows": (row_tex, row_vert, row_frame)}


def _write_anim_table(model, pack_dir: Path):
    """Merge this gun's animations into objmc_animations.json (contract with SovereignGuns).

    {"<model id>": {"<anim>": {"frames": n, "loop": bool, "length": seconds}}}; written next to
    the generators and, when the sibling plugin checkout exists, into its resources."""
    entry = {}
    for name in ANIMATIONS:
        a = model.anims.get(name)
        if a is None:
            continue
        times, loop = _frames(a)
        entry[name] = {"frames": len(times), "loop": loop, "length": float(a.length)}
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


def feather_entry(item_model: str, viewmodel: str, layers: dict):
    gun = {"type": "minecraft:model", "model": viewmodel,
           "tints": [{"type": "minecraft:custom_model_data", "index": 0, "default": STANDING << 16}]}
    return {
        "type": "minecraft:select",
        "property": "minecraft:display_context",
        "cases": [
            {"when": "firstperson_righthand", "model": {
                "type": "minecraft:composite",
                "models": [gun, layers["rfa"], layers["lua"], layers["lfa"]]}},
            {"when": "firstperson_lefthand", "model": {"type": "minecraft:empty"}},
        ],
        "fallback": {"type": "minecraft:model", "model": item_model},
    }


def _patch_feather(pack_dir: Path, item_name: str, viewmodel: str, layers: dict):
    """Point the gun's feather.json entry (found by its fallback item model) at the viewmodel."""
    path = pack_dir / "assets" / "minecraft" / "items" / "feather.json"
    data = json.loads(path.read_text())
    item_model = f"weapons:item/{item_name}"
    hit = False
    for e in data["model"]["entries"]:
        m = e["model"]
        if m.get("type") == "minecraft:select" and m.get("fallback", {}).get("model") == item_model:
            e["model"] = feather_entry(item_model, viewmodel, layers)
            hit = True
    if not hit:
        raise ValueError(f"feather.json has no entry for {item_model}")
    # no re-equip bob when the plugin rewrites the held gun's tint
    data["hand_animation_on_swap"] = False
    path.write_text(json.dumps(data, indent=4) + "\n")
