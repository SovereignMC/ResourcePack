#!/usr/bin/env python3
"""Generate the Argentum reinforced/quantum consumable item art.

Every tile is 16x16 RGBA with a transparent background, a 1px #000000 outline,
top-left lighting and 3-4 flat tones per material, matching the pack's existing
item/components icons.

Writes (relative to --pack-dir):
    assets/argentum/textures/item/components/reinforced_grindstone.png      16x16
    assets/argentum/textures/item/components/quantum_grindstone.png         16x16
    assets/argentum/textures/item/components/reinforced_mixing_blade.png    16x16
    assets/argentum/textures/item/components/quantum_mixing_blade.png       16x16
    assets/argentum/textures/item/components/reinforced_sawmill_blade.png   16x16
    assets/argentum/textures/item/components/quantum_sawmill_blade.png      16x16
    assets/argentum/textures/item/components/quantum_welding_rod.png        16x16
    assets/argentum/textures/item/components/quantum_industrial_bucket.png  16x16
    assets/argentum/items/reinforced_grindstone.json                        item model
    assets/argentum/items/quantum_grindstone.json                           item model
    assets/argentum/items/reinforced_mixing_blade.json                      item model
    assets/argentum/items/quantum_mixing_blade.json                         item model
    assets/argentum/items/reinforced_sawmill_blade.json                     item model
    assets/argentum/items/quantum_sawmill_blade.json                        item model
    assets/argentum/items/quantum_welding_rod.json                          item model
    assets/argentum/items/quantum_industrial_bucket.json                    item model
    assets/argentum/models/item/reinforced_grindstone.json                  item model
    assets/argentum/models/item/quantum_grindstone.json                     item model
    assets/argentum/models/item/reinforced_mixing_blade.json                item model
    assets/argentum/models/item/quantum_mixing_blade.json                   item model
    assets/argentum/models/item/reinforced_sawmill_blade.json               item model
    assets/argentum/models/item/quantum_sawmill_blade.json                  item model
    assets/argentum/models/item/quantum_welding_rod.json                    item model
    assets/argentum/models/item/quantum_industrial_bucket.json              item model

Deterministic: every silhouette and shade is a literal table below; no RNG, no
time, no network. A rerun rewrites byte-identical files.

Example:
    python3 tools/generate_argentum_consumable_art.py --pack-dir .
"""
from __future__ import annotations

import argparse
import json
import os

from PIL import Image

Colour = tuple[int, int, int, int]

BLACK: Colour = (0, 0, 0, 255)

STEEL = ("#3a3a3a", "#575757", "#9a9a99", "#c8c8c7")
GOLD = ("#7a5510", "#c8902a", "#ffe17a", "#fff3c4")
QUANTUM = ("#3b2456", "#7b52b8", "#cba9ff", "#efe6ff")

# Silhouettes. "#" is opaque, "." is transparent. Each is copied from the
# existing sibling icon so the upgrade chain shares one mask.
MASKS = {
    # grindstone_core with its 2x2 centre hole filled by the hub.
    "grindstone": (
        ".......###......",
        ".....#######....",
        "...##########...",
        "..#############.",
        ".###############",
        ".###############",
        "###############.",
        "###############.",
        "###############.",
        "###############.",
        ".#############..",
        ".#############..",
        "..###########...",
        "...#########....",
        ".....#####......",
        "................",
    ),
    # mixing_blade.
    "mixing_blade": (
        "................",
        "................",
        "................",
        "............###.",
        "..........#####.",
        "........#######.",
        ".......#######..",
        ".......#######..",
        "........#####...",
        ".......######...",
        "....#####.##....",
        "...###..........",
        "..###...........",
        ".###............",
        ".##.............",
        "................",
    ),
    # sawmill_blade.
    "sawmill_blade": (
        "................",
        "..........##....",
        ".........####...",
        "........######..",
        ".......########.",
        "......########..",
        ".....########...",
        "....########....",
        "...########.....",
        ".#########......",
        ".###.####.......",
        "..###.##........",
        "...#####........",
        "....###.........",
        ".....#..........",
        "................",
    ),
    # reinforced_welding_rod.
    "welding_rod": (
        ".............##.",
        "............####",
        "...........#####",
        "..........#####.",
        ".........#####..",
        "........#####...",
        ".......#####....",
        "......#####.....",
        ".....#####......",
        "....#####.......",
        "...#####........",
        "..#####.........",
        ".#####..........",
        "#####...........",
        "####............",
        ".##.............",
    ),
    # reinforced_industrial_bucket.
    "industrial_bucket": (
        ".....######.....",
        "...##########...",
        "..############..",
        ".##############.",
        ".##############.",
        ".##############.",
        ".##############.",
        "###############.",
        "###############.",
        "###############.",
        ".##############.",
        ".##############.",
        ".##############.",
        "..############..",
        "...##########...",
        ".....######.....",
    ),
}

# Shade classes: each letter is one tone of the anchor icon, re-mapped to the
# target material below. "." is transparent.
MIXING_BLADE_CLASSES = (
    "................",
    "................",
    "................",
    "............AAA.",
    "..........BBCDA.",
    "........BBCCDCA.",
    ".......BCCEDCA..",
    ".......BDEDECA..",
    "........BDECA...",
    ".......ADADCA...",
    "....FGFFA.AA....",
    "...FHA..........",
    "..FGA...........",
    ".FHA............",
    ".AA.............",
    "................",
)

# A is the anchor's near-black edge, B/C/J/K the tooth rim, D..I the disc face.
SAWMILL_BLADE_CLASSES = (
    "................",
    "..........BA....",
    ".........BCAD...",
    "........BCAEFD..",
    ".......BCAGHIFD.",
    "......BJAGHIFD..",
    ".....BCAGHIFD...",
    "....BJAGHIFD....",
    "...BJAGHIFD.....",
    ".ABJKAHIFD......",
    ".ACK.KAFD.......",
    "..ACK.KA........",
    "...AJKJA........",
    "....ACA.........",
    ".....A..........",
    "................",
)

# reinforced_industrial_bucket quantised to four steel tones (0 darkest); the
# anchor's black shadow/outline lines stay black.
BUCKET_CLASSES = (
    ".....111111.....",
    "...1112222211...",
    "..111111111321..",
    ".1100111111112K.",
    ".1100111111112K.",
    ".0322111111222K.",
    ".0233223222221K.",
    "K0222333333111K.",
    "K0222232223311K.",
    "K0222232222K11K.",
    ".K222222221K01K.",
    ".0K2223222K111K.",
    ".02KK222KK2111K.",
    "..K22KKK22211K..",
    "...KK232222KK...",
    ".....KKKKKK.....",
)

# Anchor class -> material tone index.
MIXING_BLADE_TONES = {
    "steel": {"A": 0, "B": 1, "C": 3, "D": 2, "E": 3, "F": 1, "G": 2, "H": 2},
    "quantum": {"A": 0, "B": 1, "C": 2, "D": 1, "E": 2, "F": 1, "G": 2, "H": 2},
}
# Gold-band classes of the saw (the tooth rim).
SAWMILL_RIM_CLASSES = "BCJK"


def rgba(value: str) -> Colour:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255)


def palette(tokens: tuple[str, ...]) -> tuple[Colour, ...]:
    return tuple(rgba(token) for token in tokens)


def mask_of(rows: tuple[str, ...]) -> set[tuple[int, int]]:
    pixels: set[tuple[int, int]] = set()
    for y, row in enumerate(rows):
        assert len(row) == 16, (y, row)
        for x, char in enumerate(row):
            if char != ".":
                pixels.add((x, y))
    return pixels


def is_edge(pixel: tuple[int, int], pixels: set[tuple[int, int]]) -> bool:
    x, y = pixel
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if (x + dx, y + dy) not in pixels:
            return True
    return False


def depth_of(pixels: set[tuple[int, int]]) -> dict[tuple[int, int], int]:
    depth = {pixel: 0 for pixel in pixels if is_edge(pixel, pixels)}
    frontier = list(depth)
    while frontier:
        following: list[tuple[int, int]] = []
        for x, y in frontier:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                near = (x + dx, y + dy)
                if near in pixels and near not in depth:
                    depth[near] = depth[(x, y)] + 1
                    following.append(near)
        frontier = following
    return depth


def row_runs(pixels: set[tuple[int, int]], y: int) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for x in range(17):
        inside = (x, y) in pixels
        if inside and start is None:
            start = x
        elif not inside and start is not None:
            runs.append((start, x - 1))
            start = None
    return runs


def class_image(
    rows: tuple[str, ...], colours: dict[str, Colour]
) -> tuple[Image.Image, set[tuple[int, int]]]:
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    pixels: set[tuple[int, int]] = set()
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char == ".":
                continue
            pixels.add((x, y))
            img.putpixel((x, y), colours[char])
    return img, pixels


def outline(img: Image.Image, pixels: set[tuple[int, int]], full_from: int) -> None:
    """Trace the silhouette in black; thin runs keep their material and only
    take the outline on their shadow (right) side so narrow arms stay readable."""
    for y in range(16):
        for first, last in row_runs(pixels, y):
            if last - first + 1 >= full_from:
                for x in range(first, last + 1):
                    if is_edge((x, y), pixels):
                        img.putpixel((x, y), BLACK)
            else:
                img.putpixel((last, y), BLACK)


def grindstone(tier: str) -> Image.Image:
    pixels = mask_of(MASKS["grindstone"])
    depth = depth_of(pixels)
    quantum = tier == "quantum"
    body = palette(QUANTUM if quantum else STEEL)
    trim = palette(QUANTUM if quantum else GOLD)
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))

    def light(x: int, y: int) -> float:
        return (x - 7.5) * -0.7071 + (7.0 - y) * 0.7071

    rim = [pixel for pixel in pixels if depth[pixel] == 1]
    rim.sort(key=lambda pixel: (-light(*pixel), pixel[1], pixel[0]))
    glow = set(rim[:4]) if quantum else set()

    for x, y in pixels:
        value = light(x, y)
        if depth[(x, y)] == 0:
            colour = BLACK
        elif depth[(x, y)] == 1:
            if quantum:
                if (x, y) in glow:
                    colour = trim[3]
                elif value < -1.5:
                    colour = trim[0]
                else:
                    colour = trim[2]
            elif value > 1.5:
                colour = trim[2]
            elif value < -1.5:
                colour = trim[0]
            else:
                colour = trim[1]
        elif value > 4.0 and not quantum:
            colour = body[3]
        elif value > 0.0:
            colour = body[2]
        elif value > -3.5:
            colour = body[1]
        else:
            colour = body[0]
        img.putpixel((x, y), colour)

    # Hub: bright 2x2 set in a 1px trim ring, filling the sibling's centre hole.
    hub = [(7, 7), (8, 7), (7, 8), (8, 8)]
    ring = [(x, y) for y in range(6, 10) for x in range(6, 10) if (x, y) not in hub]
    for pixel in hub:
        img.putpixel(pixel, trim[2])
    for pixel in ring:
        img.putpixel(pixel, trim[1] if not quantum else trim[0])
    return img


def mixing_blade(tier: str) -> Image.Image:
    quantum = tier == "quantum"
    body = palette(QUANTUM if quantum else STEEL)
    trim = palette(QUANTUM if quantum else GOLD)
    tones = MIXING_BLADE_TONES["quantum" if quantum else "steel"]
    img, pixels = class_image(
        MIXING_BLADE_CLASSES, {char: body[index] for char, index in tones.items()}
    )
    outline(img, pixels, full_from=4)
    # Last two pixels of each of the three arm tips, leading edge first.
    leading, trailing = (trim[3], trim[2]) if quantum else (trim[2], trim[1])
    for pixel, colour in (
        ((13, 3), leading),
        ((14, 3), trailing),
        ((1, 14), leading),
        ((2, 14), trailing),
        ((10, 10), leading),
        ((11, 10), trailing),
    ):
        img.putpixel(pixel, colour)
    return img


def sawmill_blade(tier: str) -> Image.Image:
    quantum = tier == "quantum"
    body = palette(QUANTUM if quantum else STEEL)
    trim = palette(QUANTUM if quantum else GOLD)
    # Class A is the anchor's shaded inner edge of the tooth band: keep it in
    # the trim metal; the outline pass supplies the black silhouette.
    colours: dict[str, Colour] = {"A": trim[0]}
    if quantum:
        face = (body[0], body[1], body[1], body[2], body[2])
    else:
        face = (body[1], body[2], body[2], body[3], body[3])
    colours.update(
        {
            "B": trim[0],
            "C": trim[2],
            "J": trim[1],
            "K": trim[0],
            "D": face[0],
            "E": face[1],
            "F": face[2],
            "G": face[3],
            "H": face[4],
            "I": face[4],
        }
    )
    img, pixels = class_image(SAWMILL_BLADE_CLASSES, colours)
    outline(img, pixels, full_from=3)
    if quantum:
        def light(x: int, y: int) -> float:
            return (x - 7.0) * -0.7071 + (7.5 - y) * 0.7071

        rim = [
            (x, y)
            for y, row in enumerate(SAWMILL_BLADE_CLASSES)
            for x, char in enumerate(row)
            if char in SAWMILL_RIM_CLASSES
            and img.getpixel((x, y)) != BLACK
            and light(x, y) > 1.5
        ]
        rim.sort(key=lambda pixel: (-light(*pixel), pixel[1], pixel[0]))
        for pixel in rim:
            img.putpixel(pixel, trim[3])

    # The sibling's two transparent pixels stay the arbor hole; the hub is the
    # shaded metal already surrounding them in the class grid.
    return img


def welding_rod() -> Image.Image:
    pixels = mask_of(MASKS["welding_rod"])
    tones = palette(QUANTUM)
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y in range(16):
        for first, last in row_runs(pixels, y):
            points = [(x, y) for x in range(first, last + 1)]
            if len(points) >= 3:
                img.putpixel(points[0], BLACK)
                img.putpixel(points[-1], BLACK)
                for pixel, colour in zip(points[1:-1], (tones[2], tones[1], tones[0])):
                    img.putpixel(pixel, colour)
            else:
                for pixel, colour in zip(points, (tones[2], tones[0])):
                    img.putpixel(pixel, colour)
    # Two hot pixels on the top-right point; the butt is closed with outline.
    for pixel in ((13, 0), (14, 0)):
        img.putpixel(pixel, tones[3])
    for pixel in ((1, 15), (2, 15)):
        img.putpixel(pixel, BLACK)
    return img


def industrial_bucket() -> Image.Image:
    tones = palette(STEEL)
    img, pixels = class_image(
        BUCKET_CLASSES,
        {str(index): tones[index] for index in range(4)} | {"K": BLACK},
    )
    outline(img, pixels, full_from=1)
    band = palette(QUANTUM)
    for y, colour in ((7, band[2]), (8, band[1]), (9, band[1])):
        for x in range(16):
            if (x, y) in pixels and img.getpixel((x, y)) != BLACK:
                img.putpixel((x, y), colour)
    return img


def item_model(identifier: str) -> dict:
    return {"model": {"type": "minecraft:model", "model": f"argentum:item/{identifier}"}}


def flat_model(identifier: str) -> dict:
    return {
        "parent": "item/generated",
        "textures": {"layer0": f"argentum:item/components/{identifier}"},
    }


def write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", default=".")
    args = parser.parse_args()

    texture_dir = os.path.join(args.pack_dir, "assets/argentum/textures/item/components")
    item_dir = os.path.join(args.pack_dir, "assets/argentum/items")
    model_dir = os.path.join(args.pack_dir, "assets/argentum/models/item")
    for directory in (texture_dir, item_dir, model_dir):
        os.makedirs(directory, exist_ok=True)

    images = {
        "reinforced_grindstone": grindstone("reinforced"),
        "quantum_grindstone": grindstone("quantum"),
        "reinforced_mixing_blade": mixing_blade("reinforced"),
        "quantum_mixing_blade": mixing_blade("quantum"),
        "reinforced_sawmill_blade": sawmill_blade("reinforced"),
        "quantum_sawmill_blade": sawmill_blade("quantum"),
        "quantum_welding_rod": welding_rod(),
        "quantum_industrial_bucket": industrial_bucket(),
    }

    for identifier, image in images.items():
        path = os.path.join(texture_dir, identifier + ".png")
        image.save(path)
        print(f"{path} (16x16)")

    for identifier in images:
        item_path = os.path.join(item_dir, identifier + ".json")
        write_json(item_path, item_model(identifier))
        print(f"{item_path} (json)")
        model_path = os.path.join(model_dir, identifier + ".json")
        write_json(model_path, flat_model(identifier))
        print(f"{model_path} (json)")


if __name__ == "__main__":
    main()
