#!/usr/bin/env python3
"""Generate the Argentum custom-machine block tiles and their item/model JSON.

Writes (relative to --pack-dir), all block tiles 16x16 full-face opaque:
    assets/argentum/textures/block/machines/electric_motor_advanced.png    16x16
    assets/argentum/textures/block/machines/graphene_conductor.png         16x16
    assets/argentum/textures/block/machines/quantum_core.png               16x16
    assets/argentum/textures/block/machines/reinforced_fluid_pump.png      16x16
    assets/argentum/textures/block/machines/reinforced_water_tank_side.png 16x16
    assets/argentum/textures/block/machines/reinforced_water_tank_top.png  16x16
    assets/argentum/textures/block/machines/reinforced_water_tank_bottom.png 16x16
    assets/argentum/textures/block/machines/titanium_furnace.png           16x16
    assets/argentum/items/<id>.json                                         (6)
    assets/argentum/models/block/<id>.json                                  (6)

The 1.21.4+ pack renders these through item definitions that point straight at
argentum:block/<id>; five blocks use minecraft:block/cube_all and the water
tank uses a six-face block/cube model. Housing surfaces carry the pack's
deterministic worn-metal mottle: the flag-holder hash mix sampled on a 2x2 cell
grid, split 25/55/20 dark/mid/light. Housing directly around crisp accents is
held at the mid tone, then the rightmost and bottommost housing cells are
shifted one tone darker. No RNG, no timestamps.

Example:
    python3 tools/generate_argentum_machine_art.py --pack-dir .
"""
from __future__ import annotations

import argparse
import json
import os

from PIL import Image

HOUSING = 1
ACCENT = 2
STRUCTURE = 3

# Shared material tones (exact pack palette), ordered dark -> mid -> light.
STEEL_TONES = ((0x3A, 0x3A, 0x3A), (0x57, 0x57, 0x57), (0x9A, 0x9A, 0x99))
# The motor face is a light steel panel, so it mottles across the upper three tones.
STEEL_PANEL_TONES = ((0x57, 0x57, 0x57), (0x9A, 0x9A, 0x99), (0xC8, 0xC8, 0xC7))
CARBON_TONES = ((0x0B, 0x0B, 0x0B), (0x1F, 0x1F, 0x1F), (0x3A, 0x3A, 0x3A))
TITANIUM_TONES = ((0x46, 0x56, 0x5F), (0x8F, 0xA7, 0xB2), (0xDF, 0xF2, 0xF8))
TERRACOTTA_TONES = ((0xB1, 0x53, 0x48), (0xC0, 0x6F, 0x4D), (0xE8, 0x8D, 0x70))

STEEL_DARK = STEEL_TONES[0]
STEEL_MID = STEEL_TONES[1]
STEEL_LIGHT = STEEL_TONES[2]
STEEL_HIGHLIGHT = (0xC8, 0xC8, 0xC7)
CARBON_MID = CARBON_TONES[1]
GOLD_MID = (0xC8, 0x90, 0x2A)
GOLD_LIGHT = (0xFF, 0xE1, 0x7A)
COPPER_MID = (0xC4, 0x6A, 0x2E)
GRAPHENE_MID = (0x40, 0xAC, 0x73)
GRAPHENE_LIGHT = (0x58, 0xEC, 0x9E)
GRAPHENE_GLOW = (0xB8, 0xFF, 0xD9)
QUANTUM_DARK = (0x3B, 0x24, 0x56)
QUANTUM_MID = (0x7B, 0x52, 0xB8)
QUANTUM_LIGHT = (0xCB, 0xA9, 0xFF)
QUANTUM_GLOW = (0xEF, 0xE6, 0xFF)
TITANIUM_DARK = TITANIUM_TONES[0]
TITANIUM_MID = TITANIUM_TONES[1]
TITANIUM_LIGHT = TITANIUM_TONES[2]
FIRE_BODY = (0xFF, 0xB3, 0x47)
FIRE_LIGHT = (0xFF, 0xE9, 0xB0)

TEXTURE_DIR = "assets/argentum/textures/block/machines"
ITEMS_DIR = "assets/argentum/items"
MODELS_DIR = "assets/argentum/models/block"

# Machine ids that share the single-tile cube_all shape.
CUBE_ALL_IDS = (
    "electric_motor_advanced",
    "graphene_conductor",
    "quantum_core",
    "reinforced_fluid_pump",
    "titanium_furnace",
)
# The water tank is the only six-face machine block.
TANK_ID = "reinforced_water_tank"


def _hash(x: int, y: int, salt: int) -> float:
    """Deterministic 0..1 value, same integer mix as generate_flag_holder_textures.py."""
    n = (x * 374761393 + y * 668265263 + salt * 2246822519) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


class Canvas:
    """16x16 opaque pixel buffer with a per-pixel layer tag and region mid tone."""

    def __init__(self) -> None:
        self.pixels: list[list[tuple[int, int, int] | None]] = [
            [None] * 16 for _ in range(16)
        ]
        self.kinds: list[list[int]] = [[0] * 16 for _ in range(16)]
        self.mids: list[list[tuple[int, int, int] | None]] = [[None] * 16 for _ in range(16)]

    def put(
        self,
        x: int,
        y: int,
        colour: tuple[int, int, int],
        kind: int | None = None,
    ) -> None:
        self.pixels[y][x] = colour
        if kind is not None:
            self.kinds[y][x] = kind

    def fill(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        colour: tuple[int, int, int],
        kind: int | None = None,
    ) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, colour, kind)

    def image(self) -> Image.Image:
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        px = img.load()
        for y in range(16):
            for x in range(16):
                colour = self.pixels[y][x]
                if colour is None:
                    raise ValueError(f"unpainted pixel at {x},{y}")
                px[x, y] = (*colour, 255)
        return img


def _region(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    return [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]


def _cells(coords: list[tuple[int, int]]) -> dict[tuple[int, int], list[tuple[int, int]]]:
    cells: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for x, y in coords:
        cells.setdefault((x // 2, y // 2), []).append((x, y))
    return cells


def _mottle(
    c: Canvas,
    coords: list[tuple[int, int]],
    tones: tuple[tuple[int, int, int], ...],
    salt: int,
) -> None:
    """Worn-metal mottle on a 2x2 cell grid: 25% dark, 55% mid, 20% light.

    The flag-holder hash mix is sampled once per cell, so every 2x2 block gets
    one tone; the quantile split keeps each housing region at the same overall
    value instead of letting a salt's clump distribution drift dark or light.
    """
    dark, mid, light = tones
    cells = _cells(coords)
    ranked = sorted(
        (
            0.55 * _hash(cx, cy, salt)
            + 0.30 * _hash(cx // 2, cy // 2, salt + 7)
            + 0.15 * _hash(cx // 4, cy // 4, salt + 13),
            cx,
            cy,
        )
        for cx, cy in cells
    )
    dark_end = round(len(ranked) * 0.25)
    mid_end = round(len(ranked) * 0.80)
    for index, (_, cx, cy) in enumerate(ranked):
        tone = dark if index < dark_end else mid if index < mid_end else light
        for x, y in cells[(cx, cy)]:
            c.put(x, y, tone, HOUSING)
            c.mids[y][x] = mid


def _halo(c: Canvas) -> None:
    """Hold housing touching a crisp accent at the region's mid tone.

    Only the pixels orthogonally adjacent to an accent change, so the halo is a
    clean 1px transition and leaves the surrounding 2x2 mottle cells intact.
    """
    accents = {
        (x, y) for y in range(16) for x in range(16) if c.kinds[y][x] == ACCENT
    }
    neighbour_offsets = ((1, 0), (-1, 0), (0, 1), (0, -1))
    for y in range(16):
        for x in range(16):
            if c.kinds[y][x] != HOUSING:
                continue
            if any((x + dx, y + dy) in accents for dx, dy in neighbour_offsets):
                c.put(x, y, c.mids[y][x], HOUSING)


def _shade_edges(
    c: Canvas,
    coords: list[tuple[int, int]],
    tones: tuple[tuple[int, int, int], ...],
) -> None:
    """Shift the rightmost housing column and bottommost housing row one tone darker."""
    housing = [(x, y) for x, y in coords if c.kinds[y][x] == HOUSING]
    if not housing:
        return
    max_x = max(x for x, _ in housing)
    max_y = max(y for _, y in housing)
    for x, y in housing:
        if x == max_x or y == max_y:
            colour = c.pixels[y][x]
            if colour in tones:
                c.put(x, y, tones[max(0, tones.index(colour) - 1)], HOUSING)


def _edge_ring(c: Canvas, colour: tuple[int, int, int] = STEEL_DARK) -> None:
    """1px dark STEEL ring around the whole full-face tile (never mottled)."""
    for i in range(16):
        c.put(i, 0, colour, ACCENT)
        c.put(i, 15, colour, ACCENT)
        c.put(0, i, colour, ACCENT)
        c.put(15, i, colour, ACCENT)


def _rivet(c: Canvas, x: int, y: int) -> None:
    """2x2 steel rivet lit from the top-left (never mottled)."""
    c.put(x, y, STEEL_HIGHLIGHT, ACCENT)
    c.put(x + 1, y, STEEL_LIGHT, ACCENT)
    c.put(x, y + 1, STEEL_LIGHT, ACCENT)
    c.put(x + 1, y + 1, STEEL_MID, ACCENT)


def electric_motor_advanced() -> Canvas:
    """Electric motor face: mottled steel panel, gold end caps, copper winding bar."""
    c = Canvas()
    _edge_ring(c)
    panel = _region(3, 1, 12, 14)
    _mottle(c, panel, STEEL_PANEL_TONES, 11)
    # Structural details: vent louvers, square rotor rim with a dark hub.
    for x in (5, 7, 9, 11):
        c.put(x, 3, STEEL_DARK, STRUCTURE)
    for y in range(5, 13):
        for x in range(4, 12):
            if x in (4, 11) or y in (5, 12):
                c.put(x, y, STEEL_DARK, STRUCTURE)
    for y in (9, 10):
        for x in (7, 8):
            c.put(x, y, STEEL_DARK, STRUCTURE)
    # Gold 2px end caps down both edges: mid body, light inner edge.
    for y in range(1, 15):
        c.put(1, y, GOLD_MID, ACCENT)
        c.put(2, y, GOLD_LIGHT, ACCENT)
        c.put(13, y, GOLD_LIGHT, ACCENT)
        c.put(14, y, GOLD_MID, ACCENT)
    # 3 horizontal copper winding pixels across the centre.
    for x in (6, 7, 8):
        c.put(x, 8, COPPER_MID, ACCENT)
    _halo(c)
    _shade_edges(c, panel, STEEL_PANEL_TONES)
    return c


def graphene_conductor() -> Canvas:
    """Mottled carbon housing with four graphene traces and a glowing crossing."""
    c = Canvas()
    c.fill(0, 0, 15, 15, CARBON_MID)
    _edge_ring(c)
    housing = _region(1, 1, 14, 14)
    _mottle(c, housing, CARBON_TONES, 23)
    for x in range(1, 15):
        c.put(x, 7, GRAPHENE_LIGHT, ACCENT)
        c.put(x, 8, GRAPHENE_MID, ACCENT)
    for y in range(1, 15):
        c.put(7, y, GRAPHENE_LIGHT, ACCENT)
        c.put(8, y, GRAPHENE_MID, ACCENT)
    for y in (7, 8):
        for x in (7, 8):
            c.put(x, y, GRAPHENE_LIGHT, ACCENT)
    c.put(7, 7, GRAPHENE_GLOW, ACCENT)
    for x, y in ((2, 2), (12, 2), (2, 12), (12, 12)):
        _rivet(c, x, y)
    _halo(c)
    _shade_edges(c, housing, CARBON_TONES)
    return c


def quantum_core() -> Canvas:
    """Mottled carbon housing, concentric steel ring, crisp 6x6 quantum lens."""
    c = Canvas()
    c.fill(0, 0, 15, 15, CARBON_MID)
    _edge_ring(c)
    housing = _region(1, 1, 14, 14)
    _mottle(c, housing, CARBON_TONES, 37)
    for x, y in ((1, 1), (13, 1), (1, 13), (13, 13)):
        _rivet(c, x, y)
    # Structural steel ring around the lens.
    for y in range(3, 13):
        for x in range(3, 13):
            if x in (3, 12) or y in (3, 12):
                c.put(x, y, STEEL_DARK, STRUCTURE)
            elif x in (4, 11) or y in (4, 11):
                c.put(x, y, STEEL_MID, STRUCTURE)
    # 6x6 lens at x5..10, y5..10.
    for y in range(5, 11):
        for x in range(5, 11):
            c.put(x, y, QUANTUM_MID, ACCENT)
            if x in (5, 10) or y in (5, 10):
                c.put(x, y, QUANTUM_DARK, ACCENT)
    for x in range(6, 10):
        c.put(x, 6, QUANTUM_LIGHT, ACCENT)
    for y in range(6, 10):
        c.put(6, y, QUANTUM_LIGHT, ACCENT)
    for y in (7, 8):
        for x in (7, 8):
            c.put(x, y, QUANTUM_GLOW, ACCENT)
    _halo(c)
    _shade_edges(c, housing, CARBON_TONES)
    return c


def reinforced_fluid_pump() -> Canvas:
    """Mottled steel pump face: bolted flange, ribbed body, gold belt and nozzle."""
    c = Canvas()
    c.fill(0, 0, 15, 15, STEEL_MID)
    _edge_ring(c)
    housing = _region(1, 1, 14, 14)
    _mottle(c, housing, STEEL_TONES, 41)
    # Structural flange seam and rib pairs.
    for x in range(1, 15):
        c.put(x, 4, STEEL_DARK, STRUCTURE)
    for y in range(5, 14):
        c.put(5, y, STEEL_HIGHLIGHT, STRUCTURE)
        c.put(6, y, STEEL_DARK, STRUCTURE)
        c.put(10, y, STEEL_HIGHLIGHT, STRUCTURE)
        c.put(11, y, STEEL_DARK, STRUCTURE)
    # Accents: four bolt heads, the gold belt, the gold nozzle.
    for x in (3, 6, 9, 12):
        c.put(x, 2, STEEL_HIGHLIGHT, ACCENT)
    for x in range(1, 15):
        c.put(x, 8, GOLD_LIGHT if x < 4 else GOLD_MID, ACCENT)
    for x in (7, 8):
        c.put(x, 13, GOLD_LIGHT, ACCENT)
        c.put(x, 14, GOLD_MID, ACCENT)
    _halo(c)
    _shade_edges(c, housing, STEEL_TONES)
    return c


def _terracotta_body(c: Canvas, salt: int) -> list[tuple[int, int]]:
    housing = _region(1, 1, 14, 14)
    _mottle(c, housing, TERRACOTTA_TONES, salt)
    return housing


def reinforced_water_tank_side() -> Canvas:
    """Mottled terracotta side crossed by two crisp gold bands."""
    c = Canvas()
    _edge_ring(c)
    housing = _terracotta_body(c, 53)
    for top in (4, 10):
        for x in range(1, 15):
            c.put(x, top, GOLD_LIGHT, ACCENT)
            c.put(x, top + 1, GOLD_MID, ACCENT)
            c.put(x, top + 2, GOLD_MID, ACCENT)
    _halo(c)
    _shade_edges(c, housing, TERRACOTTA_TONES)
    return c


def reinforced_water_tank_top() -> Canvas:
    """Mottled terracotta lid with a crisp gold cross-strap through the centre."""
    c = Canvas()
    _edge_ring(c)
    housing = _terracotta_body(c, 59)
    for x in range(1, 15):
        c.put(x, 7, GOLD_LIGHT, ACCENT)
        c.put(x, 8, GOLD_MID, ACCENT)
    for y in range(1, 15):
        c.put(7, y, GOLD_LIGHT, ACCENT)
        c.put(8, y, GOLD_MID, ACCENT)
    _halo(c)
    _shade_edges(c, housing, TERRACOTTA_TONES)
    return c


def reinforced_water_tank_bottom() -> Canvas:
    """Mottled terracotta bottom, plain apart from four stiff steel rivets."""
    c = Canvas()
    _edge_ring(c)
    housing = _terracotta_body(c, 61)
    for x, y in ((2, 2), (12, 2), (2, 12), (12, 12)):
        _rivet(c, x, y)
    _halo(c)
    _shade_edges(c, housing, TERRACOTTA_TONES)
    return c


def titanium_furnace() -> Canvas:
    """Mottled titanium frame and face, crisp grate and fire slots."""
    c = Canvas()
    c.fill(0, 0, 15, 15, TITANIUM_MID)
    # 1px titanium frame is housing and gets the mottle; the inner ring is the
    # crisp bevel/shadow line, so the tile reads lit from the top-left.
    frame = [(x, y) for y in range(16) for x in range(16) if x in (0, 15) or y in (0, 15)]
    _mottle(c, frame, TITANIUM_TONES, 67)
    face = _region(2, 2, 13, 13)
    _mottle(c, face, TITANIUM_TONES, 71)
    for i in range(1, 15):
        c.put(i, 1, TITANIUM_LIGHT, STRUCTURE)
        c.put(i, 14, TITANIUM_DARK, STRUCTURE)
        c.put(1, i, TITANIUM_LIGHT, STRUCTURE)
        c.put(14, i, TITANIUM_DARK, STRUCTURE)
    c.put(1, 1, TITANIUM_LIGHT, STRUCTURE)
    c.put(14, 1, TITANIUM_DARK, STRUCTURE)
    c.put(1, 14, TITANIUM_DARK, STRUCTURE)
    c.put(14, 14, TITANIUM_DARK, STRUCTURE)
    # 8x6 grate at x4..11, y3..8 with 1px bars.
    c.fill(4, 3, 11, 8, CARBON_MID, ACCENT)
    for x in (5, 7, 9, 11):
        c.fill(x, 3, x, 8, STEEL_DARK, ACCENT)
    # Two 3x2 fire slots side by side in the lower half.
    for x0 in (4, 9):
        for x in range(x0, x0 + 3):
            c.put(x, 10, FIRE_LIGHT, ACCENT)
            c.put(x, 11, FIRE_BODY, ACCENT)
    _halo(c)
    _shade_edges(c, frame, TITANIUM_TONES)
    _shade_edges(c, face, TITANIUM_TONES)
    return c


BUILDERS = {
    "electric_motor_advanced": electric_motor_advanced,
    "graphene_conductor": graphene_conductor,
    "quantum_core": quantum_core,
    "reinforced_fluid_pump": reinforced_fluid_pump,
    "reinforced_water_tank_side": reinforced_water_tank_side,
    "reinforced_water_tank_top": reinforced_water_tank_top,
    "reinforced_water_tank_bottom": reinforced_water_tank_bottom,
    "titanium_furnace": titanium_furnace,
}


def _write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _cube_all_model(model_id: str) -> dict:
    return {
        "parent": "minecraft:block/cube_all",
        "textures": {"all": f"argentum:block/machines/{model_id}"},
    }


def _cube_model(model_id: str) -> dict:
    side = f"argentum:block/machines/{model_id}_side"
    return {
        "parent": "block/cube",
        "textures": {
            "particle": side,
            "down": f"argentum:block/machines/{model_id}_bottom",
            "up": f"argentum:block/machines/{model_id}_top",
            "north": side,
            "south": side,
            "west": side,
            "east": side,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", default=".")
    args = parser.parse_args()

    texture_dir = os.path.join(args.pack_dir, TEXTURE_DIR)
    items_dir = os.path.join(args.pack_dir, ITEMS_DIR)
    models_dir = os.path.join(args.pack_dir, MODELS_DIR)
    for directory in (texture_dir, items_dir, models_dir):
        os.makedirs(directory, exist_ok=True)

    for name, builder in BUILDERS.items():
        path = os.path.join(texture_dir, name + ".png")
        builder().image().save(path, format="PNG")
        print(f"{path} (16x16)")

    for model_id in CUBE_ALL_IDS:
        path = os.path.join(items_dir, model_id + ".json")
        _write_json(path, {"model": {"type": "minecraft:model", "model": f"argentum:block/{model_id}"}})
        print(f"{path} (json)")
        path = os.path.join(models_dir, model_id + ".json")
        _write_json(path, _cube_all_model(model_id))
        print(f"{path} (json)")

    path = os.path.join(items_dir, TANK_ID + ".json")
    _write_json(path, {"model": {"type": "minecraft:model", "model": f"argentum:block/{TANK_ID}"}})
    print(f"{path} (json)")
    path = os.path.join(models_dir, TANK_ID + ".json")
    _write_json(path, _cube_model(TANK_ID))
    print(f"{path} (json)")


if __name__ == "__main__":
    main()
