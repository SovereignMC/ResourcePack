"""Bullet projectile item models. Run: python3 tools/generate/guns/projectile_models.py

WeaponMechanics shows a projectile as a packet-only invisible ARMOR_STAND wearing the item on its
HEAD; the stand's yaw/pitch follow the flight, so the model's NORTH (-Z) side is the direction of
flight (like a carved pumpkin's face). Bullets are built around the model centre (8, 8, 8) with the
nose toward -Z, tracer tail toward +Z.

Writes (weapons namespace): items/projectile/{rifle,smg,pistol}.json,
models/projectile/{rifle,smg,pistol}.json, textures/projectile/bullet.png.
WM config: Projectile_Item_Or_Block: {Type: FEATHER, Item_Model: "weapons:projectile/rifle"}.
"""

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "assets" / "weapons"

# 16x16 texture, 1 px swatches in row 0 (cubes map every face to one swatch)
SWATCH = {
    "copper": (0xC9, 0x8A, 0x4B), "copper_dark": (0x9A, 0x5F, 0x2E), "brass": (0xE6, 0xBE, 0x50),
    "brass_dark": (0xB8, 0x8F, 0x2E), "lead": (0xB4, 0xB7, 0xBD), "tracer_white": (0xFF, 0xF6, 0xB8),
    "tracer_yellow": (0xFF, 0xD2, 0x4A), "tracer_orange": (0xFF, 0x8A, 0x1E), "tracer_red": (0xFF, 0x4A, 0x14),
    "base": (0x6B, 0x55, 0x2F),
}
ORDER = list(SWATCH)

# name -> [(swatch, half width (px), z0, z1)]  (centred on x=y=8, nose at the smallest z)
BULLETS = {
    # 7.62 x 39: stepped pointed ogive, copper jacket, brass base, short bright tracer tail
    "rifle": [("lead", 0.5, 4.0, 5.0), ("copper_dark", 0.75, 5.0, 6.0), ("copper", 1.0, 6.0, 9.2),
              ("brass", 1.0, 9.2, 10.0), ("tracer_white", 0.7, 10.0, 10.8),
              ("tracer_yellow", 0.55, 10.8, 11.7), ("tracer_orange", 0.4, 11.7, 12.5),
              ("tracer_red", 0.25, 12.5, 13.2)],
    # 9 x 25 / 7.62 x 25: shorter, rounder
    "smg": [("copper_dark", 0.75, 5.0, 5.8), ("copper", 1.0, 5.8, 8.6), ("brass", 1.0, 8.6, 9.6),
            ("tracer_yellow", 0.5, 9.6, 10.3), ("tracer_orange", 0.3, 10.3, 11.0)],
    # 9 x 19: stubby round nose
    "pistol": [("brass_dark", 0.8, 5.6, 6.2), ("brass", 1.1, 6.2, 8.2), ("copper_dark", 1.1, 8.2, 9.0),
               ("tracer_orange", 0.4, 9.0, 9.7)],
}
# the head slot is drawn at 0.625 scale; scale up so the bullet reads at speed
DISPLAY_SCALE = {"rifle": 1.2, "smg": 1.2, "pistol": 1.2}


def model(name):
    elements = []
    parts = BULLETS[name]
    shift = 8.0 - (parts[0][2] + parts[-1][3]) / 2   # centre the whole bullet on the model centre
    for i, (sw, hw, z0, z1) in enumerate(parts):
        z0, z1 = round(z0 + shift, 3), round(z1 + shift, 3)
        u = ORDER.index(sw)
        uv = [u, 0, u + 1, 1]
        elements.append({
            "name": f"{name}_{i}", "from": [8 - hw, 8 - hw, z0], "to": [8 + hw, 8 + hw, z1],
            "faces": {f: {"uv": uv, "texture": "#0"} for f in ("north", "south", "east", "west", "up", "down")},
        })
    s = DISPLAY_SCALE[name]
    return {
        "credit": "SovereignMC tools/generate/guns/projectile_models.py",
        "texture_size": [16, 16],
        "textures": {"0": "weapons:projectile/bullet", "particle": "weapons:projectile/bullet"},
        "elements": elements,
        "display": {"head": {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [s, s, s]}},
    }


def main():
    tex = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for i, k in enumerate(ORDER):
        tex.putpixel((i, 0), SWATCH[k] + (255,))
    tp = ASSETS / "textures" / "projectile" / "bullet.png"
    tp.parent.mkdir(parents=True, exist_ok=True)
    tex.save(tp, optimize=True)
    for name in BULLETS:
        mp = ASSETS / "models" / "projectile" / f"{name}.json"
        ip = ASSETS / "items" / "projectile" / f"{name}.json"
        mp.parent.mkdir(parents=True, exist_ok=True)
        ip.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(json.dumps(model(name), indent=2) + "\n")
        ip.write_text(json.dumps({"model": {"type": "minecraft:model", "model": f"weapons:projectile/{name}"}}, indent=2) + "\n")
        print(f"wrote {ip.relative_to(ROOT)} -> {mp.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
