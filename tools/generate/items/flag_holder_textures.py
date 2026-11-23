#!/usr/bin/env python3
"""Generate the flag holder's worn dark iron and shaded brass tiles.

Writes (relative to --pack-dir):
    assets/argentum/textures/item/holder_iron.png    16x16
    assets/argentum/textures/item/holder_brass.png   16x16

Both tiles are opaque and used with per-face UVs (1 texel per model pixel) by
models/item/flag_holder.json (see flag_holder_model.py). Deterministic: no RNG.

Example:
    python3 tools/generate/items/flag_holder_textures.py --pack-dir .
"""
from __future__ import annotations

import argparse
import os

from PIL import Image


def _hash(x: int, y: int, salt: int) -> float:
    n = (x * 374761393 + y * 668265263 + salt * 2246822519) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def _noise(x: int, y: int, salt: int) -> float:
    return (
        0.5 * _hash(x, y, salt)
        + 0.3 * _hash(x // 2, y // 2, salt + 7)
        + 0.2 * _hash(x // 4, y // 4, salt + 13)
    )


def _mix(base, delta):
    return tuple(max(0, min(255, round(c + delta))) for c in base)


def iron() -> Image.Image:
    img = Image.new("RGBA", (16, 16))
    px = img.load()
    base = (50, 49, 52)
    for y in range(16):
        for x in range(16):
            v = _noise(x, y, 1) - 0.5
            d = v * 13
            # faint brushed grain along x, sparse scratches and rust flecks
            d += (_hash(0, y, 5) - 0.5) * 3
            c = _mix(base, d)
            if _hash(x, y, 9) > 0.99:
                c = _mix((66, 52, 42), v * 10)  # rust fleck
            elif _hash(x, y, 11) > 0.99:
                c = _mix(base, 14)  # scratch highlight
            # soft edge shading so tiles read as bevelled plates
            edge = min(x, y, 15 - x, 15 - y)
            if edge == 0:
                c = _mix(c, 9 if (x + y) < 15 else -12)
            px[x, y] = (*c, 255)
    return img


def brass() -> Image.Image:
    img = Image.new("RGBA", (16, 16))
    px = img.load()
    base = (150, 116, 54)
    for y in range(16):
        for x in range(16):
            v = _noise(x, y, 2) - 0.5
            grad = (7.5 - y) * 3.2  # lit from above, darker toward the bottom
            d = grad + v * 26
            c = _mix(base, d)
            if _hash(x, y, 4) > 0.95:
                c = _mix((96, 84, 44), v * 16)  # verdigris tarnish
            if y == 1 and 1 <= x <= 14:
                c = _mix(c, 24)  # specular line
            px[x, y] = (*c, 255)
    return img


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", default=".")
    args = parser.parse_args()
    out_dir = os.path.join(args.pack_dir, "assets/argentum/textures/item")
    os.makedirs(out_dir, exist_ok=True)
    for name, img in (("holder_iron", iron()), ("holder_brass", brass())):
        path = os.path.join(out_dir, name + ".png")
        img.save(path)
        print(path)


if __name__ == "__main__":
    main()
