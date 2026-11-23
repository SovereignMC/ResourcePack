#!/usr/bin/env python3
"""Generate the flag holder block model and its Blockbench source.

Writes (relative to --pack-dir):
    assets/argentum/models/item/flag_holder.json
    tools/art/items/flag_holder.bbmodel   (Java Block/Item, textures embedded)

Layout (block model px, axis at x=8, z=8):
    y 0..1       iron base plate, chamfered corners; it is also the socket floor
    y 1..2.5     iron step plate (ring around the socket)
    y 2.5..23    iron tube, outer 3..13, socket opening 5..11 (6x6) with brass bands
    y 23..25.5   thin brass collar and flared rim, opening widens to 4.5..11.5 at the top
    plus buttress brackets on all four sides, rivets, and 45 degree corner bolts.
The pole (4 px) stands on the floor at y=1 inside the opening.

Run flag_holder_textures.py first (the bbmodel embeds the PNGs).
    python3 tools/generate/items/flag_holder_model.py --pack-dir .
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import uuid

IRON, BRASS = "0", "1"
FACES = ("north", "east", "south", "west", "up", "down")

DISPLAY = {
    "thirdperson_righthand": {"rotation": [75, 45, 0], "translation": [0.5, 0.5, 0], "scale": [0.375, 0.375, 0.375]},
    "thirdperson_lefthand": {"rotation": [75, 45, 0], "translation": [-4, 2.5, 0], "scale": [0.375, 0.375, 0.375]},
    "firstperson_righthand": {"rotation": [0, 45, 0], "translation": [-4, 0, 0], "scale": [0.4, 0.4, 0.4]},
    "firstperson_lefthand": {"rotation": [0, -135, 0], "translation": [-4, 0, 0], "scale": [0.4, 0.4, 0.4]},
    "ground": {"translation": [0, 3, 0], "scale": [0.25, 0.25, 0.25]},
    "gui": {"rotation": [30, -135, 0], "translation": [0, -1.75, 0], "scale": [0.5, 0.5, 0.5]},
    "fixed": {"translation": [0, -1.5, 0], "scale": [0.5, 0.5, 0.5]},
}

elements: list[dict] = []


def _span(a: float, b: float) -> tuple[float, float]:
    """Map a coordinate span onto the 0..16 tile, keeping its length."""
    lo, hi = min(a, b), max(a, b)
    lo_m = lo % 16
    if lo_m + (hi - lo) > 16:
        lo_m = 16 - (hi - lo)
    return lo_m, lo_m + (hi - lo)


def box(name, frm, to, tex, skip=(), rot=None):
    x0, y0, z0 = frm
    x1, y1, z1 = to
    xs, ys, zs = _span(x0, x1), _span(y0, y1), _span(z0, z1)
    # (u span, v span) per face; v runs top to bottom so y is flipped
    def vy():
        return (16 - ys[1], 16 - ys[0]) if False else ys
    uv = {
        "north": (xs, ys), "south": (xs, ys),
        "east": (zs, ys), "west": (zs, ys),
        "up": (xs, zs), "down": (xs, zs),
    }
    faces = {}
    for f in FACES:
        if f in skip:
            continue
        (u0, u1), (v0, v1) = uv[f]
        if f in ("north", "south", "east", "west"):
            v0, v1 = 16 - v1, 16 - v0
        r = lambda n: round(n, 3)
        faces[f] = {"uv": [r(u0), r(v0), r(u1), r(v1)], "texture": "#" + tex}
    e = {"name": name, "from": [round(c, 3) for c in frm], "to": [round(c, 3) for c in to], "faces": faces}
    if rot:
        e["rotation"] = rot
    elements.append(e)


def ring(name, x0, z0, x1, z1, y0, y1, ix0, iz0, ix1, iz1, tex, skip=()):
    box(name + "_n", (x0, y0, z0), (x1, y1, iz0), tex, skip)
    box(name + "_s", (x0, y0, iz1), (x1, y1, z1), tex, skip)
    box(name + "_w", (x0, y0, iz0), (ix0, y1, iz1), tex, skip)
    box(name + "_e", (ix1, y0, iz0), (x1, y1, iz1), tex, skip)


def build():
    # base plate: three strips -> chamfered corners, no overlap
    box("plate_mid", (2, 0, 0), (14, 1, 16), IRON)
    box("plate_w", (0, 0, 2), (2, 1, 14), IRON)
    box("plate_e", (14, 0, 2), (16, 1, 14), IRON)
    # step plate ring around the socket (floor at y=1 stays open)
    ring("step", 2, 2, 14, 14, 1, 2.5, 5, 5, 11, 11, IRON, skip=("down",))
    # tube sections between brass bands; the iron tube runs up to y=23
    for i, (a, b) in enumerate(((2.5, 6), (8, 13), (15, 23))):
        ring(f"tube{i}", 3, 3, 13, 13, a, b, 5, 5, 11, 11, IRON, skip=("down",) if i == 0 else ())
    # brass bands and a thin collar (inner wall flush with the tube)
    ring("band0", 2.5, 2.5, 13.5, 13.5, 6, 8, 5, 5, 11, 11, BRASS)
    ring("band1", 2.5, 2.5, 13.5, 13.5, 13, 15, 5, 5, 11, 11, BRASS)
    ring("collar", 2.5, 2.5, 13.5, 13.5, 23, 24, 5, 5, 11, 11, BRASS)
    # flared rim: wide short lower lip, then a stepped-in upper lip; opening widens to 4.5..11.5
    ring("rim_lo", 1.5, 1.5, 14.5, 14.5, 24, 24.8, 4.5, 4.5, 11.5, 11.5, BRASS, skip=("down",))
    ring("rim_hi", 2.2, 2.2, 13.8, 13.8, 24.8, 25.5, 4.5, 4.5, 11.5, 11.5, BRASS, skip=("down",))
    # buttress brackets, 3 steps (foot, mid, riser against the tube) + brass rivet.
    # Built for the north side (small z = outside) then mapped to the other sides.
    side_map = {
        "n": lambda x, z: (x, z),
        "s": lambda x, z: (16 - x, 16 - z),
        "w": lambda x, z: (z, x),
        "e": lambda x, z: (16 - z, x),
    }
    parts = (
        ("foot", (6, 1, 0.5), (10, 3, 1.2), ("down",), IRON),
        ("mid", (6.2, 1, 1.2), (9.8, 5.5, 2), ("down",), IRON),
        ("riser", (6.5, 2.5, 2), (9.5, 9, 3), ("down",), IRON),
        ("rivet", (7.6, 6.5, 1.6), (8.4, 7.3, 2), (), BRASS),
    )
    for sd, m in side_map.items():
        for nm, f, t, sk, tex in parts:
            (xa, za), (xb, zb) = m(f[0], f[2]), m(t[0], t[2])
            box(f"brace_{sd}_{nm}", (min(xa, xb), f[1], min(za, zb)), (max(xa, xb), t[1], max(za, zb)), tex, sk)
    # rivets on the step plate corners
    for i, (x, z) in enumerate(((2.2, 2.2), (13, 2.2), (2.2, 13), (13, 13))):
        box(f"rivet{i}", (x, 2.5, z), (x + 0.8, 3.1, z + 0.8), BRASS, skip=("down",))
    # 45 degree bolts on the base plate side strips, footprint fully inside the plate
    for i, (cx, cz) in enumerate(((1, 3), (15, 3), (1, 13), (15, 13))):
        rot = {"angle": 45, "axis": "y", "origin": [cx, 0.5, cz]}
        box(f"bolt{i}", (cx - 0.5, 0.5, cz - 0.5), (cx + 0.5, 2, cz + 0.5), IRON, skip=("down",), rot=rot)
        box(f"bolt_cap{i}", (cx - 0.6, 2, cz - 0.6), (cx + 0.6, 2.6, cz + 0.6), BRASS, skip=("down",), rot=rot)


def model_json():
    return {
        "format_version": "1.21.6",
        "credit": "Made with Blockbench",
        "textures": {"0": "argentum:item/holder_iron", "1": "argentum:item/holder_brass"},
        "elements": elements,
        "display": DISPLAY,
    }


def bbmodel(png_iron: bytes, png_brass: bytes):
    def uid():
        return str(uuid.uuid5(uuid.NAMESPACE_URL, "flag_holder/" + str(len(seen))))
    seen: list = []
    els = []
    for e in elements:
        seen.append(1)
        faces = {}
        for f in FACES:
            if f in e["faces"]:
                d = e["faces"][f]
                faces[f] = {"uv": d["uv"], "texture": int(d["texture"][1:])}
            else:
                faces[f] = {"uv": [0, 0, 0, 0], "texture": None}
        be = {
            "name": e["name"], "box_uv": False, "render_order": "default", "locked": False,
            "shade": True, "light_emission": 0, "export": True, "allow_mirror_modeling": True,
            "from": e["from"], "to": e["to"], "autouv": 0, "color": 0,
            "origin": e.get("rotation", {}).get("origin", [0, 0, 0]),
            "faces": faces, "type": "cube", "uuid": uid(),
        }
        if "rotation" in e:
            r = e["rotation"]
            be["rotation"] = [r["angle"] if r["axis"] == a else 0 for a in "xyz"]
        els.append(be)
    textures = []
    for i, (n, png) in enumerate((("holder_iron.png", png_iron), ("holder_brass.png", png_brass))):
        textures.append({
            "name": n, "path": "", "folder": "item", "namespace": "argentum", "id": str(i),
            "width": 16, "height": 16, "uv_width": 16, "uv_height": 16, "particle": False,
            "use_as_default": False, "layers_enabled": False, "sync_to_project": "",
            "render_mode": "default", "render_sides": "auto", "frame_time": 1,
            "frame_order_type": "loop", "frame_order": "", "frame_interpolate": False,
            "visible": True, "internal": True, "saved": True,
            "uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, "flag_holder_tex/" + n)),
            "source": "data:image/png;base64," + base64.b64encode(png).decode(),
        })
    return {
        "meta": {"format_version": "5.0", "model_format": "java_block", "box_uv": False},
        "name": "flag_holder", "parent": "", "java_block_version": "1.21.11",
        "ambientocclusion": True, "front_gui_light": False, "visible_box": [1, 1, 0],
        "resolution": {"width": 16, "height": 16},
        "elements": els, "groups": [], "outliner": [x["uuid"] for x in els],
        "textures": textures, "display": DISPLAY,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--pack-dir", default=".")
    a = p.parse_args()
    build()
    out = os.path.join(a.pack_dir, "assets/argentum/models/item/flag_holder.json")
    with open(out, "w") as f:
        json.dump(model_json(), f, indent=2)
        f.write("\n")
    print(out, len(elements), "elements")
    tex = os.path.join(a.pack_dir, "assets/argentum/textures/item")
    pngs = [open(os.path.join(tex, n), "rb").read() for n in ("holder_iron.png", "holder_brass.png")]
    bb = os.path.join(a.pack_dir, "tools/art/items/flag_holder.bbmodel")
    os.makedirs(os.path.dirname(bb), exist_ok=True)
    with open(bb, "w") as f:
        json.dump(bbmodel(*pngs), f, indent=1)
        f.write("\n")
    print(bb)


if __name__ == "__main__":
    main()
