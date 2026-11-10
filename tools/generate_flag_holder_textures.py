#!/usr/bin/env python3
"""Generate the flag holder's weathered iron and aged brass tiles.

Writes (relative to --pack-dir):
    assets/argentum/textures/item/holder_iron.png    16x16
    assets/argentum/textures/item/holder_brass.png   16x16

Both tiles are opaque, mottled metal used with full-face UVs ([0,0,16,16])
by models/item/flag_holder.json. Deterministic: no RNG, no seed arguments.

Example:
    python3 tools/generate_flag_holder_textures.py --pack-dir .
"""
from __future__ import annotations

import argparse
import os

from PIL import Image

# Thresholds -> colour. Mottled cast iron: near-black shadows up to warm worn edges.
IRON = [
    (0.30, (41, 38, 34)),
    (0.60, (52, 48, 42)),
    (0.82, (63, 57, 49)),
    (0.93, (78, 70, 58)),
    (1.01, (96, 80, 54)),
]
# Aged brass: dark tarnish through warm highlights.
BRASS = [
    (0.30, (82, 62, 33)),
    (0.60, (105, 82, 44)),
    (0.82, (128, 101, 56)),
    (0.93, (156, 126, 72)),
    (1.01, (184, 152, 92)),
]


def _hash(x: int, y: int, salt: int) -> float:
    n = (x * 374761393 + y * 668265263 + salt * 2246822519) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def tile(palette, salt: int) -> Image.Image:
    img = Image.new("RGBA", (16, 16))
    px = img.load()
    for y in range(16):
        for x in range(16):
            v = (
                0.55 * _hash(x, y, salt)
                + 0.30 * _hash(x // 2, y // 2, salt + 7)
                + 0.15 * _hash(x // 4, y // 4, salt + 13)
            )
            for limit, colour in palette:
                if v <= limit:
                    px[x, y] = (*colour, 255)
                    break
    return img


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", default=".")
    args = parser.parse_args()
    out_dir = os.path.join(args.pack_dir, "assets/argentum/textures/item")
    os.makedirs(out_dir, exist_ok=True)
    for name, palette, salt in (("holder_iron", IRON, 1), ("holder_brass", BRASS, 2)):
        path = os.path.join(out_dir, name + ".png")
        tile(palette, salt).save(path)
        print(path)


if __name__ == "__main__":
    main()
