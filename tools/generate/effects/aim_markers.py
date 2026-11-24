#!/usr/bin/env python3
"""
Generate the Cannons aim markers (item models under `sovereignmc:effect/`).

Writes textures, item definitions and models for:

  muzzle_pointer      Chevron strip drawn along the aim line (same 4-plane cross
                      as aim_beam).  One 32x32 tile covers ~2 blocks of beam and
                      shows 2 amber chevrons pointing away from the muzzle.
  landing_marker_1..3 A flagpole with a numbered pennant, placed at predicted
                      impact points as a vertical-billboard ItemDisplay.

--- Muzzle pointer: which texture axis is "forward" ---------------------------
The plugin rotates the display so local +Z points along the shot.  The model is
the aim_beam cross (z 0..16).  Working through vanilla's face vertex/UV
mapping (FaceBakery), texture +u (to the right) maps to world/model +Z on:
  west  face, uv [0,0,16,16]            : u -> +Z
  east  face, uv [16,0,0,16] (mirrored)  : u -> +Z
  up    face, rotation 90                : u -> +Z
  down  face, rotation 90                : u -> -Z  (BACKWARDS, so the model uses
                                            rotation 270 for "down": u -> +Z)
So the chevrons point toward +u (the tile's right) and every face, both sides of
every plane, shows them pointing forward.  A single texture is used.  The tile
is vertically symmetric, so v direction does not matter.  Each chevron sits
inside its own 16 px cell with a 2 px margin, so tiles chain without seams.

--- Landing marker: geometry and translation ------------------------------------
Model: one plane [0,0,8] -> [16,32,8] (16 wide, 32 tall), faces north and south
(both uv [0,0,16,16], unmirrored, so the digit reads correctly from either side).
Texture 32x64: pole at the bottom centre, pennant near the top, ground ring at
the base.  An ItemDisplay with transform NONE renders the model with its
[8,8,8] centre at the entity position, so the pole base (model y=0) is 0.5 block
BELOW the entity.  The plugin must translate the display by (0, +0.5, 0) blocks
at scale 1 (0.5 * scale for other scales) so the pole base rests on the impact
point.  (The ring is drawn ~1 model unit above the bottom edge, ~0.06 block.)
The pole (texture x=15..16) and ground ring (x=5..26) are centred on the plane's
centre line by construction, and the pennant extends right of the pole only, so
billboard VERTICAL (rotation about Y through the entity) keeps the pole base fixed;
no horizontal offset is needed.

Outputs (relative to --pack-dir):
    assets/sovereignmc/textures/item/effect/muzzle_pointer.png
    assets/sovereignmc/textures/item/effect/landing_marker_{1,2,3}.png

(The JSON items/models are static files committed in the tree.)

Example:
    python3 tools/generate/effects/aim_markers.py --pack-dir . \\
        --preview 8 --preview-dir /tmp/aim_preview
"""

from __future__ import annotations

import argparse
import os

from PIL import Image, ImageDraw, ImageFilter

AMBER_CORE = (255, 151, 72)     # #FF9748
AMBER_EDGE = (222, 104, 36)
OUTLINE = (58, 24, 8, 190)      # dark, semi-opaque
DIGIT = (46, 20, 8, 255)
POLE = (214, 218, 222, 255)
POLE_SHADE = (150, 156, 164, 255)
RING = (205, 190, 170, 200)

# 5x7 pixel font for the marker digits.
FONT = {
    1: ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    2: [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    3: ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
}


def _mask_from_polygon(size, points) -> Image.Image:
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).polygon(points, fill=255)
    return m


def _shade(img: Image.Image, mask: Image.Image, core, edge, outline) -> None:
    """Paint mask: outline ring (1px outside), edge colour (outer 1px), core inside."""
    grown = mask.filter(ImageFilter.MaxFilter(3))
    inner = mask.filter(ImageFilter.MinFilter(3))
    px, g, m, i = img.load(), grown.load(), mask.load(), inner.load()
    for y in range(img.height):
        for x in range(img.width):
            if i[x, y]:
                px[x, y] = core + (255,)
            elif m[x, y]:
                px[x, y] = edge + (255,)
            elif g[x, y]:
                px[x, y] = outline


def build_pointer() -> Image.Image:
    """32x32 tile: two forward (+u) chevrons, one per 16 px cell."""
    mask = Image.new("L", (32, 32), 0)
    for cell in (0, 16):
        x0 = cell + 3
        pts = [(x0, 4), (x0 + 5, 4), (x0 + 10, 15), (x0 + 10, 16),
               (x0 + 5, 27), (x0, 27), (x0 + 5, 16), (x0 + 5, 15)]
        mask.paste(_mask_from_polygon((32, 32), pts), mask=_mask_from_polygon((32, 32), pts))
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    _shade(img, mask, AMBER_CORE, AMBER_EDGE, OUTLINE)
    return img


def build_marker(n: int) -> Image.Image:
    img = Image.new("RGBA", (32, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Ground ring / puff at the base.
    d.ellipse([5, 59, 26, 63], fill=(RING[0], RING[1], RING[2], 110), outline=RING)
    # Pole (2px wide, centred) with a darker right column.
    d.rectangle([15, 2, 15, 61], fill=POLE)
    d.rectangle([16, 2, 16, 61], fill=POLE_SHADE)
    d.rectangle([14, 1, 17, 1], fill=OUTLINE)
    d.rectangle([14, 2, 14, 61], fill=OUTLINE)
    d.rectangle([17, 27, 17, 61], fill=OUTLINE)
    # Pennant with swallowtail notch on its free edge.
    x0, x1, y0, y1 = 18, 30, 3, 26
    mask = Image.new("L", (32, 64), 0)
    ImageDraw.Draw(mask).polygon(
        [(x0, y0), (x1, y0), (x1 - 3, (y0 + y1) // 2 - 1), (x1 - 3, (y0 + y1) // 2 + 1),
         (x1, y1), (x0, y1)], fill=255)
    _shade(img, mask, AMBER_CORE, AMBER_EDGE, OUTLINE)
    # Pole pixels at column 17 next to the flag stay pole-coloured/outlined.
    # Digit: 5x7 font at 2x -> 10x14, centred on the pennant body.
    scale = 2
    dx = x0 + 1 + (x1 - 3 - x0 - 1 - 5 * scale) // 2 + 1
    dy = y0 + (y1 - y0 + 1 - 7 * scale) // 2
    for r, row in enumerate(FONT[n]):
        for c, ch in enumerate(row):
            if ch == "#":
                d.rectangle([dx + c * scale, dy + r * scale,
                             dx + c * scale + scale - 1, dy + r * scale + scale - 1], fill=DIGIT)
    return img


def _up(img: Image.Image, size: int) -> Image.Image:
    if size == img.width:
        return img
    k = size / img.width
    return img.resize((size, round(img.height * k)), Image.NEAREST)


def _save_preview(images, per_px, path, bg=(26, 40, 66, 255)) -> None:
    pad = 4
    w = sum(i.width for i in images) + pad * (len(images) + 1)
    h = max(i.height for i in images) + 2 * pad
    sheet = Image.new("RGBA", (w, h), bg)
    x = pad
    for i in images:
        sheet.alpha_composite(i, (x, pad))
        x += i.width + pad
    sheet.resize((w * per_px, h * per_px), Image.NEAREST).save(path)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pack-dir", default=".", help="resource pack root")
    p.add_argument("--size", type=int, default=32,
                   help="pointer tile / marker width in pixels (nearest-neighbour upscaled from 32)")
    p.add_argument("--preview", type=int, default=0,
                   help="also write previews at this pixel magnification (0 = off)")
    p.add_argument("--preview-dir", default=None,
                   help="where previews go (default: next to this script)")
    a = p.parse_args()

    tex_dir = os.path.join(a.pack_dir, "assets", "sovereignmc", "textures", "item", "effect")
    os.makedirs(tex_dir, exist_ok=True)

    pointer = _up(build_pointer(), a.size)
    pointer.save(os.path.join(tex_dir, "muzzle_pointer.png"))
    markers = [_up(build_marker(n), a.size) for n in (1, 2, 3)]
    for n, m in enumerate(markers, 1):
        m.save(os.path.join(tex_dir, f"landing_marker_{n}.png"))

    if a.preview:
        out = a.preview_dir or os.path.dirname(os.path.abspath(__file__))
        os.makedirs(out, exist_ok=True)
        _save_preview([pointer] * 4, a.preview, os.path.join(out, "muzzle_pointer_preview.png"))
        _save_preview(markers, a.preview, os.path.join(out, "landing_markers_preview.png"))
    print("wrote", tex_dir)


if __name__ == "__main__":
    main()
