#!/usr/bin/env python3
"""
Stylize the 16 vanilla-path explosion particle frames (TNT, creeper, PlaneChase bombs).

Takes an existing set of 32x32 `explosion_0..15.png` frames and gives them a cleaner,
cel-shaded look while keeping every frame's silhouette and timing:

* fire is posterized into five hard heat bands (deep red -> white-yellow) and the band
  map is mode-filtered so the speckle noise becomes chunky flame shapes;
* the flash frames get a cream core with a warm amber rim;
* smoke is reduced to three greys, lit from the upper left (light on edges facing
  up-left, dark on edges facing down-right);
* fire gets a 1 px dark ember outline wherever it touches transparency, so the
  fireball reads clearly against the sky.

Outputs (relative to --pack-dir):
    assets/minecraft/textures/particle/explosion_<n>.png   n = 0..15

Example:
    python3 tools/generate_explosion_textures.py --src "<pack>/assets/minecraft/textures/particle" --pack-dir . --preview sheet.png
"""

from __future__ import annotations

import argparse
import colorsys
import os

from PIL import Image, ImageFilter

FRAMES = 16

FIRE_BANDS = [
    (176, 34, 22),
    (236, 84, 18),
    (255, 140, 22),
    (255, 198, 40),
    (255, 240, 150),
]
FLASH_CORE = (255, 249, 226)
FLASH_RIM = (255, 196, 92)
SPARK = (255, 214, 96)
SMOKE_DARK = (74, 68, 66)
SMOKE_MID = (112, 106, 100)
SMOKE_LIGHT = (152, 146, 138)
EMBER_OUTLINE = (84, 26, 20)

TRANSPARENT, FLASH, FIRE, SMOKE = 0, 1, 2, 3


def classify(rgba):
    r, g, b, a = rgba
    if a < 16:
        return TRANSPARENT
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if l > 0.8 and b > 150:
        return FLASH
    if s > 0.45 and r > 150:
        return FIRE
    return SMOKE


def fire_band(rgba):
    r, g, b, _ = rgba
    heat = (0.45 * r + 0.45 * g + 0.10 * b) / 255
    thresholds = [0.55, 0.68, 0.74, 0.80]
    return sum(heat > t for t in thresholds)


def stylize(src: Image.Image) -> Image.Image:
    im = src.convert("RGBA")
    w, h = im.size
    px = im.load()
    kind = [[classify(px[x, y]) for x in range(w)] for y in range(h)]

    def kind_at(x, y):
        return kind[y][x] if 0 <= x < w and 0 <= y < h else TRANSPARENT

    band_img = Image.new("L", (w, h), 0)
    bp = band_img.load()
    for y in range(h):
        for x in range(w):
            if kind[y][x] == FIRE:
                bp[x, y] = 10 + fire_band(px[x, y]) * 10
    smoothed = band_img.filter(ImageFilter.ModeFilter(3)).load()

    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    op = out.load()
    for y in range(h):
        for x in range(w):
            k = kind[y][x]
            if k == TRANSPARENT:
                continue
            neighbours = [kind_at(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            isolated = all(n == TRANSPARENT for n in neighbours)
            if k == FLASH:
                if isolated:
                    colour = SPARK
                elif TRANSPARENT in neighbours:
                    colour = FLASH_RIM
                else:
                    colour = FLASH_CORE
            elif k == FIRE:
                if isolated:
                    colour = SPARK
                else:
                    value = smoothed[x, y] or bp[x, y]
                    colour = FIRE_BANDS[max(0, min(4, value // 10 - 1))]
            else:
                lit = kind_at(x - 1, y) == TRANSPARENT or kind_at(x, y - 1) == TRANSPARENT
                shaded = kind_at(x + 1, y) == TRANSPARENT or kind_at(x, y + 1) == TRANSPARENT
                if lit and not shaded:
                    colour = SMOKE_LIGHT
                elif shaded and not lit:
                    colour = SMOKE_DARK
                else:
                    colour = SMOKE_MID
            op[x, y] = colour + (255,)

    for y in range(h):
        for x in range(w):
            if kind[y][x] != TRANSPARENT:
                continue
            touches_fire = False
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if kind_at(nx, ny) == FIRE:
                    ring = [kind_at(nx + ex, ny + ey) for ex, ey in ((1, 0), (-1, 0), (0, 1), (0, -1))]
                    if any(n == FIRE for n in ring):
                        touches_fire = True
            if touches_fire:
                op[x, y] = EMBER_OUTLINE + (255,)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--src", required=True, help="folder holding explosion_0..15.png")
    parser.add_argument("--pack-dir", default=".", help="resource pack root")
    parser.add_argument("--preview", help="optional path for a 6x upscaled contact sheet")
    args = parser.parse_args()

    out_dir = os.path.join(args.pack_dir, "assets", "minecraft", "textures", "particle")
    os.makedirs(out_dir, exist_ok=True)
    frames = []
    for i in range(FRAMES):
        frame = stylize(Image.open(os.path.join(args.src, f"explosion_{i}.png")))
        frame.save(os.path.join(out_dir, f"explosion_{i}.png"), optimize=True)
        frames.append(frame)

    if args.preview:
        scale = 6
        fw, fh = frames[0].size
        sheet = Image.new("RGBA", (8 * fw * scale, 2 * fh * scale), (40, 44, 64, 255))
        for i, frame in enumerate(frames):
            big = frame.resize((fw * scale, fh * scale), Image.NEAREST)
            sheet.alpha_composite(big, ((i % 8) * fw * scale, (i // 8) * fh * scale))
        sheet.save(args.preview)


if __name__ == "__main__":
    main()
