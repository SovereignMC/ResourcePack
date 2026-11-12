#!/usr/bin/env python3
"""Generate the Argentum metallurgy item icons.

Writes (relative to --pack-dir):
    assets/argentum/textures/item/metallurgy/titanium_ingot.png   16x16
    assets/argentum/textures/item/metallurgy/quantum_alloy.png    16x16
    assets/argentum/textures/item/metallurgy/carbon_fiber.png     16x16
    assets/argentum/items/titanium_ingot.json
    assets/argentum/items/quantum_alloy.json
    assets/argentum/items/carbon_fiber.json
    assets/argentum/models/item/titanium_ingot.json
    assets/argentum/models/item/quantum_alloy.json
    assets/argentum/models/item/carbon_fiber.json

All tiles are 16x16 RGBA: transparent background, every opaque pixel at alpha
255, 1px black outline, light from the top-left, 3-4 flat tones per material.
The two ingots reuse the exact trapezoid and facet layout of
textures/item/metallurgy/chromium_ingot.png, re-toned per material.
Deterministic: no RNG, no time, no network, so reruns are byte-identical.

Example:
    python3 tools/generate_argentum_metallurgy_art.py --pack-dir .
"""
from __future__ import annotations

import argparse
import json
import os

from PIL import Image

CLEAR = (0, 0, 0, 0)
OUTLINE = (0x00, 0x00, 0x00, 255)

TITANIUM = {
    "dark": (0x46, 0x56, 0x5F, 255),
    "mid": (0x8F, 0xA7, 0xB2, 255),
    "light": (0xDF, 0xF2, 0xF8, 255),
    "highlight": (0xF6, 0xFD, 0xFF, 255),
}
QUANTUM = {
    "dark": (0x3B, 0x24, 0x56, 255),
    "mid": (0x7B, 0x52, 0xB8, 255),
    "light": (0xCB, 0xA9, 0xFF, 255),
    "spark": (0xEF, 0xE6, 0xFF, 255),
}
CARBON = {
    "dark": (0x0B, 0x0B, 0x0B, 255),
    "mid": (0x1F, 0x1F, 0x1F, 255),
    "light": (0x3A, 0x3A, 0x3A, 255),
    "sheen": (0x5C, 0x5C, 0x5C, 255),
}

# Ingot layout, one char per pixel, lifted from chromium_ingot.png with its
# tones folded into tiers: K = outline/shadow rim, D = dark, M = mid,
# L = light body, H = top-face highlight, '.' = transparent.
INGOT_LAYOUT = (
    "................",
    "................",
    "..........KK....",
    ".......KKKLLK...",
    "....KKKLHLLLLK..",
    ".KKKLHHLLLLLLLK.",
    "KMHHHLLLLLLMMMMK",
    "KHMLLLLLMMMLLLLK",
    "KHLMLMMMLLLLLDDK",
    "KLLLMLLLLLDDDDDK",
    "KLLLMLLLDDDDKKK.",
    ".KLLMDDDDKKK....",
    "..KLMDKKK.......",
    "...KKK..........",
    "................",
    "................",
)

# Per-material mapping of layout tiers to palette tones.
INGOT_TONES = {
    "titanium": {
        "K": OUTLINE,
        "D": TITANIUM["dark"],
        "M": TITANIUM["mid"],
        "L": TITANIUM["light"],
        "H": TITANIUM["highlight"],
    },
    "quantum": {
        "K": OUTLINE,
        "D": QUANTUM["dark"],
        "M": QUANTUM["dark"],
        "L": QUANTUM["mid"],
        "H": QUANTUM["light"],
    },
}

# Two detail pixels per ingot: studs low-right, sparks on the upper face.
INGOT_DETAILS = {
    "titanium": ([(11, 7), (11, 8)], TITANIUM["dark"]),
    "quantum": ([(8, 4), (5, 5)], QUANTUM["spark"]),
}


def ingot(variant: str) -> Image.Image:
    img = Image.new("RGBA", (16, 16), CLEAR)
    px = img.load()
    tones = INGOT_TONES[variant]
    for y, row in enumerate(INGOT_LAYOUT):
        for x, tier in enumerate(row):
            if tier != ".":
                px[x, y] = tones[tier]
    (points, colour) = INGOT_DETAILS[variant]
    for x, y in points:
        px[x, y] = colour
    return img


def carbon_fiber() -> Image.Image:
    img = Image.new("RGBA", (16, 16), CLEAR)
    px = img.load()
    # 14x14 sheet inside the outer 1px margin: black outline, then a 1px
    # CARBON dark border, then a 10x10 2px-checker twill field.
    for y in range(1, 15):
        for x in range(1, 15):
            if x in (1, 14) or y in (1, 14):
                px[x, y] = OUTLINE
            elif x in (2, 13) or y in (2, 13):
                px[x, y] = CARBON["dark"]
            else:
                weave = ((x - 3) // 2 + (y - 3) // 2) % 2
                px[x, y] = CARBON["light"] if weave == 0 else CARBON["mid"]
    # Single sheen pixel pair on the top-left diagonal.
    px[4, 4] = CARBON["sheen"]
    px[5, 5] = CARBON["sheen"]
    return img


def write_png(path: str, image: Image.Image) -> None:
    image.save(path)
    print(f"{path} (16x16)")


def write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    print(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", default=".")
    args = parser.parse_args()
    root = args.pack_dir
    tex_dir = os.path.join(root, "assets/argentum/textures/item/metallurgy")
    item_dir = os.path.join(root, "assets/argentum/items")
    model_dir = os.path.join(root, "assets/argentum/models/item")
    for directory in (tex_dir, item_dir, model_dir):
        os.makedirs(directory, exist_ok=True)

    tiles = {
        "titanium_ingot": ingot("titanium"),
        "quantum_alloy": ingot("quantum"),
        "carbon_fiber": carbon_fiber(),
    }
    for name, image in tiles.items():
        write_png(os.path.join(tex_dir, name + ".png"), image)

    for name in tiles:
        write_json(
            os.path.join(item_dir, name + ".json"),
            {"model": {"type": "minecraft:model", "model": f"argentum:item/{name}"}},
        )
        write_json(
            os.path.join(model_dir, name + ".json"),
            {
                "parent": "item/generated",
                "textures": {"layer0": f"argentum:item/metallurgy/{name}"},
            },
        )


if __name__ == "__main__":
    main()
