#!/usr/bin/env python3
"""Offline mirror of tools/verify-pack.ps1 (which needs pwsh) plus the
argentum asset checks this repo's CI cannot run on Linux.

Rules mirrored from verify-pack.ps1:
  * every "parent": "argentum:..." resolves to models/<path>.json
  * every texture ref (textures.* values) resolves to textures/<path>.png
  * every items/*.json "model" ref resolves to models/<path>.json OR is allowlisted
  * argentum texture refs must live in a known category subfolder
  * assets/** paths must be valid lowercase resource locations
  * warns on PNGs no JSON references
  * pack.mcmeta must be valid JSON

Extra checks:
  * the item ids the live StructuresRevamped plugin resolves must have an
    items/<id>.json (TARGET_IDS below)
  * every new item tile is 16x16 RGBA with both transparent and opaque pixels;
    every new block tile is 16x16 RGBA and fully opaque
  * every new PNG is referenced by some JSON

Usage: python3 tools/verify_argentum_refs.py
Exit 0 = clean (warnings allowed), 1 = hard failure. Writes nothing.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ARGENTUM = ASSETS / "argentum"

# items defs whose model ref has no models/*.json today. Keep in sync with the pack
# (mirrors $MODEL_REF_WARNLIST in verify-pack.ps1).
MODEL_REF_WARNLIST = {
    "item/alternator",
    "item/big_capacitor",
    "item/brewer",
    "item/carbonado_capacitor",
    "item/connector",
    "item/electric_motor",
    "item/elevator_block",
    "item/energized_capacitor",
    "item/fluid_pump",
    "item/heater",
    "item/large_capacitor",
    "item/medium_capacitor",
    "item/small_capacitor",
    "item/steam_turbine",
    "item/transformer",
    "item/water_tank",
}

# Texture category subfolders (keep in sync with README.md).
TEXTURE_CATEGORIES = {
    "item": {"sigils", "metallurgy", "dust", "components", "consumables", "ui", "tools"},
    "block": {"machines", "basic_machines", "capacitors", "crates", "supply"},
}

# Ids the deployed StructuresRevamped resolves to ItemStacks and the pack must cover.
# (argentum:engine is intentionally absent: EngineBlock overrides no getModel(), so it
# renders as the vanilla infested chiseled stone bricks item.)
TARGET_IDS = [
    "advanced_magnet",
    "aluminium_casing",
    "carbon_fiber",
    "cordite_charge",
    "electric_motor_advanced",
    "graphene_conductor",
    "pure_copper_electrode",
    "quantum_alloy",
    "quantum_core",
    "quantum_grindstone",
    "quantum_industrial_bucket",
    "quantum_mixing_blade",
    "quantum_sawmill_blade",
    "quantum_welding_rod",
    "reinforced_fluid_pump",
    "reinforced_gear",
    "reinforced_grindstone",
    "reinforced_mixing_blade",
    "reinforced_sawmill_blade",
    "reinforced_water_tank",
    "titanium_furnace",
    "titanium_ingot",
]

# Textures added for TARGET_IDS; item tiles must carry transparency, block tiles are opaque.
NEW_ITEM_TEXTURES = [
    "textures/item/metallurgy/titanium_ingot.png",
    "textures/item/metallurgy/quantum_alloy.png",
    "textures/item/metallurgy/carbon_fiber.png",
    "textures/item/components/advanced_magnet.png",
    "textures/item/components/aluminium_casing.png",
    "textures/item/components/reinforced_gear.png",
    "textures/item/components/pure_copper_electrode.png",
    "textures/item/consumables/cordite_charge.png",
    "textures/item/components/reinforced_grindstone.png",
    "textures/item/components/quantum_grindstone.png",
    "textures/item/components/reinforced_mixing_blade.png",
    "textures/item/components/quantum_mixing_blade.png",
    "textures/item/components/reinforced_sawmill_blade.png",
    "textures/item/components/quantum_sawmill_blade.png",
    "textures/item/components/quantum_welding_rod.png",
    "textures/item/components/quantum_industrial_bucket.png",
]
NEW_BLOCK_TEXTURES = [
    "textures/block/machines/electric_motor_advanced.png",
    "textures/block/machines/graphene_conductor.png",
    "textures/block/machines/quantum_core.png",
    "textures/block/machines/reinforced_fluid_pump.png",
    "textures/block/machines/reinforced_water_tank_side.png",
    "textures/block/machines/reinforced_water_tank_top.png",
    "textures/block/machines/reinforced_water_tank_bottom.png",
    "textures/block/machines/titanium_furnace.png",
]
# The block ids among TARGET_IDS get models/block/<id>.json instead of models/item/<id>.json.
BLOCK_IDS = {
    "electric_motor_advanced",
    "graphene_conductor",
    "quantum_core",
    "reinforced_fluid_pump",
    "reinforced_water_tank",
    "titanium_furnace",
}
NEW_JSONS = [f"items/{i}.json" for i in TARGET_IDS] + [
    f"{'models/block' if i in BLOCK_IDS else 'models/item'}/{i}.json" for i in TARGET_IDS
]

RESOURCE_LOCATION = re.compile(r"[a-z0-9_.\-/]+")

warns: list[str] = []
fails: list[str] = []
referenced: set[Path] = set()


def rel(p: Path, base: Path = ROOT) -> str:
    return p.relative_to(base).as_posix()


def test_model_ref(ref: str, whence: str) -> None:
    if not (ARGENTUM / "models" / f"{ref}.json").is_file():
        if ref in MODEL_REF_WARNLIST:
            warns.append(f"model ref not found (allowlisted): {ref} in {whence}")
        else:
            fails.append(f"model ref not found: {ref} in {whence}")


def test_texture_ref(ref: str, whence: str) -> None:
    tex = ARGENTUM / "textures" / f"{ref}.png"
    m = re.match(r"(item|block)/([^/]+)/", ref)
    if re.fullmatch(r"(item|block)/[^/]+", ref):
        warns.append(f"texture ref not in a category subfolder: argentum:{ref} in {whence}")
    elif m and m.group(2) not in TEXTURE_CATEGORIES[m.group(1)]:
        fails.append(
            f"texture ref uses unknown category '{m.group(2)}': argentum:{ref} in {whence}"
        )
    if tex.is_file():
        referenced.add(tex.resolve())
    else:
        fails.append(f"texture ref not found: argentum:{ref} in {whence}")


def walk(node, whence: str) -> None:
    if isinstance(node, dict):
        parent = node.get("parent")
        if isinstance(parent, str) and parent.startswith("argentum:"):
            test_model_ref(parent.split(":", 1)[1], whence)
        textures = node.get("textures")
        if isinstance(textures, dict):
            for value in textures.values():
                if isinstance(value, str) and value.startswith("argentum:"):
                    test_texture_ref(value.split(":", 1)[1], whence)
        model = node.get("model")
        if isinstance(model, dict):
            ref = model.get("model")
            if isinstance(ref, str) and ref.startswith("argentum:"):
                test_model_ref(ref.split(":", 1)[1], whence)
        for key, value in node.items():
            if key not in {"parent", "textures", "model"}:
                walk(value, whence)
    elif isinstance(node, list):
        for entry in node:
            walk(entry, whence)


def check_tile(path: Path, must_be_transparent: bool) -> None:
    try:
        with Image.open(path) as im:
            if im.size != (16, 16):
                fails.append(f"texture is {im.size[0]}x{im.size[1]}, expected 16x16: {rel(path)}")
            if im.mode != "RGBA":
                fails.append(f"texture mode is {im.mode}, expected RGBA: {rel(path)}")
                return
            alphas = im.getchannel("A").getextrema()
    except OSError as exc:  # unreadable/corrupt
        fails.append(f"unreadable texture {rel(path)}: {exc}")
        return
    if must_be_transparent:
        if alphas[0] != 0:
            fails.append(f"item texture has no transparent pixel: {rel(path)}")
        if alphas[1] == 0:
            fails.append(f"item texture has no opaque pixel: {rel(path)}")
        if 0 < alphas[0] < 255:
            fails.append(f"item texture has semi-transparent pixels: {rel(path)}")
    elif alphas[0] != 255:
        fails.append(f"block texture has transparent pixels: {rel(path)}")


def main() -> int:
    if not ARGENTUM.is_dir():
        print(f"argentum assets not found at {ARGENTUM}", file=sys.stderr)
        return 1

    for path in sorted(ASSETS.rglob("*")):
        if not path.is_file():
            continue
        if not RESOURCE_LOCATION.fullmatch(rel(path, ASSETS)):
            fails.append(
                "invalid resource location (allowed: a-z 0-9 _ . - /): "
                f"assets/{rel(path, ASSETS)}"
            )

    json_count = 0
    for path in sorted(ARGENTUM.rglob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            fails.append(f"unparseable JSON: {rel(path)} ({exc})")
            continue
        json_count += 1
        walk(doc, rel(path))

    all_textures = sorted(ARGENTUM.rglob("*.png"))
    for tex in all_textures:
        if tex.resolve() not in referenced:
            warns.append(f"texture not referenced by any JSON: {rel(tex)}")

    missing_ids = [i for i in TARGET_IDS if not (ARGENTUM / "items" / f"{i}.json").is_file()]
    for i in missing_ids:
        fails.append(f"items/{i}.json missing (plugin resolves argentum:{i})")

    for entry in NEW_ITEM_TEXTURES:
        path = ARGENTUM / entry
        if not path.is_file():
            fails.append(f"missing new item texture: {rel(path)}")
        else:
            check_tile(path, must_be_transparent=True)
    for entry in NEW_BLOCK_TEXTURES:
        path = ARGENTUM / entry
        if not path.is_file():
            fails.append(f"missing new block texture: {rel(path)}")
        else:
            check_tile(path, must_be_transparent=False)

    mcmeta = ROOT / "pack.mcmeta"
    if mcmeta.is_file():
        try:
            json.loads(mcmeta.read_text(encoding="utf-8"))
        except ValueError:
            fails.append("pack.mcmeta is not valid JSON")
    else:
        fails.append("pack.mcmeta missing")

    print(
        f"scanned {json_count} argentum JSON file(s), {len(all_textures)} texture PNG(s); "
        f"{len(NEW_ITEM_TEXTURES) + len(NEW_BLOCK_TEXTURES)} new tile(s), {len(NEW_JSONS)} new JSON file(s)"
    )

    if warns:
        print(f"\nWARNINGS: {len(warns)}")
        for w in warns:
            print(f"  [warn] {w}")
    if fails:
        print(f"\nFAILURES: {len(fails)}")
        for f in fails:
            print(f"  [fail] {f}")
        return 1
    print("verify: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
