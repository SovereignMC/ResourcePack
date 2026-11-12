#!/usr/bin/env python3
"""Generate the Argentum component and cordite item icons.

Writes (relative to --pack-dir):
    assets/argentum/textures/item/components/advanced_magnet.png        16x16
    assets/argentum/textures/item/components/aluminium_casing.png       16x16
    assets/argentum/textures/item/components/reinforced_gear.png        16x16
    assets/argentum/textures/item/components/pure_copper_electrode.png  16x16
    assets/argentum/textures/item/consumables/cordite_charge.png        16x16
    assets/argentum/items/advanced_magnet.json
    assets/argentum/items/aluminium_casing.json
    assets/argentum/items/reinforced_gear.json
    assets/argentum/items/pure_copper_electrode.json
    assets/argentum/items/cordite_charge.json
    assets/argentum/models/item/advanced_magnet.json
    assets/argentum/models/item/aluminium_casing.json
    assets/argentum/models/item/reinforced_gear.json
    assets/argentum/models/item/pure_copper_electrode.json
    assets/argentum/models/item/cordite_charge.json

All tiles are 16x16 RGBA: transparent background, 1px black outline, light
from the top-left, 3-4 flat tones per material. Deterministic: no RNG, no
time, no network. Rerunning writes byte-identical files.

Example:
    python3 tools/generate_argentum_component_art.py --pack-dir .
"""
from __future__ import annotations

import argparse
import json
import math
import os

from PIL import Image

OUTLINE = (0x00, 0x00, 0x00, 255)
CLEAR = (0, 0, 0, 0)

STEEL = {
    "dark": (0x3A, 0x3A, 0x3A, 255),
    "mid": (0x57, 0x57, 0x57, 255),
    "light": (0x9A, 0x9A, 0x99, 255),
    "highlight": (0xC8, 0xC8, 0xC7, 255),
}
GOLD = {
    "dark": (0x7A, 0x55, 0x10, 255),
    "mid": (0xC8, 0x90, 0x2A, 255),
    "light": (0xFF, 0xE1, 0x7A, 255),
    "highlight": (0xFF, 0xF3, 0xC4, 255),
}
COPPER = {
    "dark": (0x7A, 0x3D, 0x1C, 255),
    "mid": (0xC4, 0x6A, 0x2E, 255),
    "light": (0xF2, 0xA4, 0x5C, 255),
    "highlight": (0xFF, 0xD7, 0xA8, 255),
}
ALUMINIUM = {
    "dark": (0x7D, 0x84, 0x89, 255),
    "mid": (0xB9, 0xC0, 0xC5, 255),
    "light": (0xEE, 0xF2, 0xF4, 255),
    "highlight": (0xFF, 0xFF, 0xFF, 255),
}
CARBON = {
    "dark": (0x0B, 0x0B, 0x0B, 255),
    "mid": (0x1F, 0x1F, 0x1F, 255),
    "light": (0x3A, 0x3A, 0x3A, 255),
    "highlight": (0x5C, 0x5C, 0x5C, 255),
}
RED = {
    "dark": (0x7A, 0x1C, 0x1C, 255),
    "mid": (0xC8, 0x38, 0x2F, 255),
    "light": (0xFF, 0x6A, 0x5A, 255),
    "highlight": (0xFF, 0xB0, 0xA6, 255),
}
YELLOW = {
    "dark": (0x8A, 0x6A, 0x10, 255),
    "mid": (0xE8, 0xC2, 0x3A, 255),
    "light": (0xFF, 0xEE, 0x9A, 255),
    "highlight": (0xFF, 0xFB, 0xD6, 255),
}

NEIGHBOURS_8 = [
    (dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)
]
NEIGHBOURS_4 = [(-1, 0), (0, -1), (1, 0), (0, 1)]


def canvas() -> tuple[Image.Image, "Image.PixelAccess"]:
    img = Image.new("RGBA", (16, 16), CLEAR)
    return img, img.load()


def outline_ring(mask: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """Silhouette edge: any masked pixel with a transparent 8-neighbour."""
    ring: set[tuple[int, int]] = set()
    for x, y in mask:
        for dx, dy in NEIGHBOURS_8:
            if (x + dx, y + dy) not in mask:
                ring.add((x, y))
                break
    return ring


def outline_around(px, mask: set[tuple[int, int]]) -> None:
    """Paint a 1px black ring on transparent pixels touching the mask."""
    for x, y in mask:
        for dx, dy in NEIGHBOURS_8:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < 16 and 0 <= ny < 16):
                continue
            if (nx, ny) not in mask and px[nx, ny][3] == 0:
                px[nx, ny] = OUTLINE


def lit_tone(
    x: int,
    y: int,
    ring: set[tuple[int, int]],
    material: dict[str, tuple[int, int, int, int]],
) -> tuple[int, int, int, int]:
    """Top-left lit flat face: light on upper/left edges, dark lower/right."""
    if (x, y - 1) in ring or (x - 1, y) in ring:
        return material["light"]
    if (x, y + 1) in ring or (x + 1, y) in ring:
        return material["dark"]
    return material["mid"]


def advanced_magnet() -> Image.Image:
    """Horseshoe magnet, opening downwards, 2px gap between the poles."""
    img, px = canvas()
    mask: set[tuple[int, int]] = set()
    for y, x0, x1 in ((2, 4, 11), (3, 3, 12), (4, 2, 13), (5, 2, 13), (6, 2, 13)):
        mask.update((x, y) for x in range(x0, x1 + 1))
    for y in range(7, 15):
        mask.update((x, y) for x in range(1, 7))
        mask.update((x, y) for x in range(9, 15))
    ring = outline_ring(mask)
    for x, y in mask:
        if (x, y) in ring:
            px[x, y] = OUTLINE
        else:
            px[x, y] = lit_tone(x, y, ring, RED if y <= 10 else STEEL)
    # 1px top-left highlight along the arch.
    for point in ((4, 4), (5, 4), (4, 5)):
        if point in mask and point not in ring:
            px[point] = RED["highlight"]
    # Steel pole tips: their upper edge is lit even though it meets the red body.
    for x0, x1 in ((2, 5), (10, 13)):
        for x in range(x0, x1 + 1):
            for y, material in ((11, "light"), (12, "mid")):
                if (x, y) in mask and (x, y) not in ring:
                    px[x, y] = STEEL[material]
    px[2, 11] = STEEL["highlight"]
    return img


def aluminium_casing() -> Image.Image:
    """12x14 rounded aluminium box with rivets, a seam and vent slits."""
    img, px = canvas()
    mask: set[tuple[int, int]] = set()
    mask.update((x, 1) for x in range(3, 13))
    for y in range(2, 14):
        mask.update((x, y) for x in range(2, 14))
    mask.update((x, 14) for x in range(3, 13))
    ring = outline_ring(mask)
    for x, y in mask:
        if (x, y) in ring:
            px[x, y] = OUTLINE
        elif y == 2 or x == 3:
            px[x, y] = ALUMINIUM["light"]
        elif y == 13 or x == 12:
            px[x, y] = ALUMINIUM["dark"]
        else:
            px[x, y] = ALUMINIUM["mid"]
    # Label plate centred between the top rivets and the middle seam.
    for x in range(5, 11):
        px[x, 5] = ALUMINIUM["light"]
        px[x, 6] = ALUMINIUM["dark"]
    # 1px seam across the middle.
    for x in range(4, 12):
        px[x, 7] = ALUMINIUM["dark"]
    # Two 4x1 vent slits in the lower half, two pixels apart.
    for y in (9, 12):
        for x in range(6, 10):
            px[x, y] = STEEL["dark"]
    # Four white rivets seated 1px inside the corners, each with a
    # dark pixel under-right so they read as bumps.
    for x, y in ((4, 3), (11, 3), (4, 12), (11, 12)):
        px[x, y] = ALUMINIUM["highlight"]
        if (x + 1, y + 1) not in ring:
            px[x + 1, y + 1] = ALUMINIUM["dark"]
    return img


def gear_mask() -> set[tuple[int, int]]:
    """8-tooth gear: round body plus a stub at every compass and diagonal step."""
    mask: set[tuple[int, int]] = {
        (x, y)
        for y in range(16)
        for x in range(16)
        if math.hypot(x - 7.5, y - 7.5) <= 5.0
    }
    for x0, x1, y0, y1 in (
        (6, 9, 2, 4),
        (6, 9, 11, 13),
        (2, 4, 6, 9),
        (11, 13, 6, 9),
        (3, 4, 3, 4),
        (11, 12, 3, 4),
        (3, 4, 11, 12),
        (11, 12, 11, 12),
    ):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                mask.add((x, y))
    return mask


def reinforced_gear() -> Image.Image:
    """8-tooth steel gear with a gold tooth rim and a 4x4 dark centre bore."""
    img, px = canvas()
    mask = gear_mask()
    edge = outline_ring(mask)
    for x, y in mask:
        if (x, y) in edge:
            # Gold 1px rim on the protruding teeth only; the body rim is steel.
            if math.hypot(x - 7.5, y - 7.5) > 5.0:
                px[x, y] = GOLD["light"] if x + y <= 15 else GOLD["mid"]
            else:
                px[x, y] = STEEL["light"]
        else:
            px[x, y] = lit_tone(x, y, edge, STEEL)
    # 4x4 dark centre bore with a 1px black ring.
    for y in range(6, 10):
        for x in range(6, 10):
            px[x, y] = STEEL["dark"]
    for y in range(5, 11):
        for x in range(5, 11):
            if x in (5, 10) or y in (5, 10):
                px[x, y] = OUTLINE
    outline_around(px, mask)
    return img


def pure_copper_electrode() -> Image.Image:
    """4x12 vertical copper rod with a pale tip and a clean face."""
    img, px = canvas()
    mask = {(x, y) for y in range(2, 14) for x in range(6, 10)}
    for x, y in mask:
        if x == 6:
            px[x, y] = COPPER["light"]
        elif x == 9:
            px[x, y] = COPPER["dark"]
        else:
            px[x, y] = COPPER["mid"]
    for x in range(6, 10):
        px[x, 2] = COPPER["highlight"]
        px[x, 3] = COPPER["highlight"]
    px[6, 4] = (0xFF, 0xFF, 0xFF, 255)
    outline_around(px, mask)
    return img


def cordite_charge() -> Image.Image:
    """Stubby carbon cylinder with yellow bands and a red fuse cap."""
    img, px = canvas()
    mask: set[tuple[int, int]] = set()
    mask.update((x, y) for y in (2, 3) for x in range(6, 10))
    mask.update((x, y) for y in range(4, 13) for x in range(3, 13))
    for x, y in mask:
        if y <= 3:
            px[x, y] = RED["mid"]
        elif x == 3:
            px[x, y] = CARBON["light"]
        elif x == 4:
            px[x, y] = CARBON["light"]
        elif x >= 10:
            px[x, y] = CARBON["dark"]
        else:
            px[x, y] = CARBON["mid"]
    # Fuse cap: lit top row and one pale highlight pixel.
    for x in range(6, 10):
        px[x, 2] = RED["light"]
    px[9, 2] = RED["light"]
    px[9, 3] = RED["dark"]
    px[6, 2] = RED["highlight"]
    # Three yellow bands with a lit left end.
    for y in (6, 8, 10):
        for x in range(3, 13):
            px[x, y] = YELLOW["mid"]
        px[3, y] = YELLOW["light"]
        px[4, y] = YELLOW["light"]
    outline_around(px, mask)
    return img


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
    item_tex = os.path.join(root, "assets/argentum/textures/item/components")
    consumable_tex = os.path.join(root, "assets/argentum/textures/item/consumables")
    item_dir = os.path.join(root, "assets/argentum/items")
    model_dir = os.path.join(root, "assets/argentum/models/item")
    for directory in (item_tex, consumable_tex, item_dir, model_dir):
        os.makedirs(directory, exist_ok=True)

    tiles = {
        "advanced_magnet": ("components", advanced_magnet()),
        "aluminium_casing": ("components", aluminium_casing()),
        "reinforced_gear": ("components", reinforced_gear()),
        "pure_copper_electrode": ("components", pure_copper_electrode()),
        "cordite_charge": ("consumables", cordite_charge()),
    }
    for name, (category, image) in tiles.items():
        directory = consumable_tex if category == "consumables" else item_tex
        path = os.path.join(directory, name + ".png")
        image.save(path)
        print(f"{path} (16x16)")

    for name, (category, _) in tiles.items():
        write_json(
            os.path.join(item_dir, name + ".json"),
            {"model": {"type": "minecraft:model", "model": f"argentum:item/{name}"}},
        )
        write_json(
            os.path.join(model_dir, name + ".json"),
            {
                "parent": "item/generated",
                "textures": {"layer0": f"argentum:item/{category}/{name}"},
            },
        )


if __name__ == "__main__":
    main()
