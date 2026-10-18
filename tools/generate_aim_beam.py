#!/usr/bin/env python3
"""
Generate the Cannons aim-line beam texture (item model `sovereignmc:effect/aim_beam`).

The cannon aim line is drawn with stretched `ItemDisplay` entities that use the
item model `sovereignmc:effect/aim_beam` (see
assets/sovereignmc/items/effect/aim_beam.json).  The model is a cross of flat
planes, so this single tile is a *soft, translucent glow*: bright (and slightly
more opaque) along the beam's centre line, fading to fully transparent at the
plane edges.  That is what makes the flat planes read as a round beam.

The tile is a smooth, repeating unit - no chevrons/details - so it can be
"spammed and chained" along the beam without visible seams.

Outputs (relative to --pack-dir):
    assets/sovereignmc/textures/item/effect/aim_beam.png      the beam tile
    assets/sovereignmc/textures/item/effect/aim_beam_e.png    emissive (glow) tile

Example:
    python3 tools/generate_aim_beam.py --pack-dir . --size 64 --preview 128
"""

from __future__ import annotations

import argparse
import math
import os

from PIL import Image

# Warm orange glow (single colour family).
BEAM_EDGE = (255, 74, 22)     # deep orange at the outer edge
BEAM_CORE = (255, 196, 138)   # bright, near-white core


def _parse_color(value: str):
    v = value.strip().lstrip("#")
    if len(v) != 6:
        raise argparse.ArgumentTypeError("colour must be a 6-digit hex value, e.g. FF5A1E")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def _clamp255(v: float) -> int:
    return max(0, min(255, int(round(v))))


def _mix(a, b, t: float):
    return tuple(_clamp255(x + (y - x) * t) for x, y in zip(a, b))


def build_texture(size: int, edge, core, peak_alpha: float) -> Image.Image:
    """A smooth translucent glow: opaque-ish core fading to transparent rims."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()

    c = (size - 1) / 2.0
    sigma = size * 0.30
    edge_falloff = math.exp(-(c / sigma) ** 2)  # value of the gaussian at the rim

    for y in range(size):
        g = math.exp(-((y - c) / sigma) ** 2)
        fall = max(0.0, (g - edge_falloff) / (1.0 - edge_falloff))  # 1 centre -> 0 rim
        fall = fall ** 0.7  # flatter profile: more of the beam is solid, edge stays soft
        col = _mix(edge, core, fall)
        alpha = _clamp255(peak_alpha * fall * 255.0)
        for x in range(size):
            px[x, y] = (col[0], col[1], col[2], alpha)
    return img


def build_emissive(texture: Image.Image, size: int, core) -> Image.Image:
    """The bright core glows; keeps the same alpha as the beam."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    src = texture.load()
    dst = img.load()
    for y in range(size):
        for x in range(size):
            dst[x, y] = (core[0], core[1], core[2], src[x, y][3])
    return img


def _write_preview(texture: Image.Image, size: int, per_tile: int, path: str) -> None:
    """A 4-tile strip on a dark background (alpha is visible against it)."""
    strip = Image.new("RGBA", (size * 4, size), (18, 18, 22, 255))
    for i in range(4):
        strip.alpha_composite(texture, (i * size, 0))
    strip.resize((per_tile * 4, per_tile), Image.NEAREST).save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack-dir", default=".", help="resource pack root")
    parser.add_argument("--size", type=int, default=64, help="texture resolution in pixels")
    parser.add_argument("--edge", type=_parse_color, default=BEAM_EDGE, help="outer edge colour (RRGGBB)")
    parser.add_argument("--core", type=_parse_color, default=BEAM_CORE, help="centre colour (RRGGBB)")
    parser.add_argument("--peak-alpha", type=float, default=1.0, help="opacity of the beam centre (0-1)")
    parser.add_argument("--preview", type=int, default=0,
                        help="also write a 4-tile preview of this per-tile pixel size next to this script (0 = off)")
    args = parser.parse_args()

    texture = build_texture(args.size, args.edge, args.core, args.peak_alpha)
    emissive = build_emissive(texture, args.size, args.core)

    tex_dir = os.path.join(args.pack_dir, "assets", "sovereignmc", "textures", "item", "effect")
    os.makedirs(tex_dir, exist_ok=True)

    beam_path = os.path.join(tex_dir, "aim_beam.png")
    texture.save(beam_path)
    emissive.save(os.path.join(tex_dir, "aim_beam_e.png"))

    if args.preview:
        _write_preview(texture, args.size, args.preview,
                       os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview.png"))

    print("wrote", beam_path)


if __name__ == "__main__":
    main()
