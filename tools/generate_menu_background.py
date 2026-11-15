#!/usr/bin/env python3
"""Draw the selector dialogue's panels as `sovereignmc:menu` glyphs.

Each panel is one 120 x 153 px glyph (17 text lines) drawn from the top of the
dialogue's first body line: a `minecraft:container`-style window with a title
band and accent rule, the screenshot and caption in an inset field, and a status
band. The lobby (SovereignPicoLobby `server_state/dialog.rs`) writes the panel
name and player count over the bands as live text, and carries the click events
on spacing runs, so no other glyphs are needed.

The size keeps the whole dialogue inside a 384 x 240 GUI, the smallest screen
auto GUI scale produces at 16:9 and 16:10 (e.g. 1920x1200 at scale 5).

Writes (relative to --pack-dir):
    assets/sovereignmc/textures/font/menu_<panel>.png   120x153, paletted
    assets/sovereignmc/font/menu.json

    python3 tools/generate_menu_background.py --pack-dir . [--client-jar JAR]
"""
from __future__ import annotations

import argparse
import glob
import json
import os

from PIL import Image, ImageDraw

import render_text

WIDTH, HEIGHT = 120, 153
LINE = 9
FONT_ID = "sovereignmc:menu"

# `minecraft:textures/gui/container/inventory.png` and `.../container/slot.png`
# palette: 1 px black frame, 2 px light bevel, plate, 2 px shadow bevel.
FRAME = (0, 0, 0, 255)
LIGHT = (255, 255, 255, 255)
PLATE = (198, 198, 198, 255)
SHADOW = (85, 85, 85, 255)
FIELD = (139, 139, 139, 255)
FIELD_EDGE = (55, 55, 55, 255)
BAND = (0x2B, 0x2B, 0x2B, 255)

# Rows, in glyph pixels. Text line n starts at y = 9n: the title is line 1 and
# the status line 15, each with one band row above its caps.
WINDOW_BOTTOM = 147          # frame row; the 5 rows below stay clear of the total line
TITLE_BAND = (8, 16)
RULE = 17
FIELD_BOX = (4, 18, WIDTH - 5, 133)
STATUS_BAND = (134, 143)
ART_LEFT, ART_TOP, ART_RIGHT, ART_BOTTOM = 5, 19, WIDTH - 6, 132
ART_WIDTH = ART_RIGHT - ART_LEFT + 1
CAPTION_PADDING = 3
CAPTION_COLOR = "#E8E8E8"
DISCORD_BLURPLE = "#5865F2"

# (name, glyph, accent rule colour, caption component)
PANELS = (
    ("events", "", (0xE0, 0x7B, 0x24), [
        {"text": "We regularly host PvP, War,\nMovecraft Events.\nCheck the "},
        {"text": "Discord Server", "color": DISCORD_BLURPLE},
        {"text": "\nfor updates."},
    ]),
    ("nations", "", (0xC9, 0xA2, 0x27),
     "1:750 Earth Map Geopol Towny\nPlanes, Ships, PvP,\nWars and Industry"),
    ("practice", "", (0x2F, 0x86, 0xB8),
     "Practice your PvP skills or Design cutting-edge ships in Plots, "
     "the sky's the limit"),
)


def window(accent: tuple[int, int, int]) -> Image.Image:
    """Frame, bevel, title and status bands, accent rule and the inset field."""
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    right, bottom = WIDTH - 1, WINDOW_BOTTOM
    draw.rectangle([0, 0, right, bottom], fill=FRAME)
    draw.rectangle([1, 1, right - 1, bottom - 1], fill=SHADOW)
    draw.rectangle([1, 1, right - 3, bottom - 3], fill=LIGHT)
    draw.rectangle([3, 3, right - 3, bottom - 3], fill=PLATE)
    for x, y in ((0, 0), (1, 0), (0, 1)):  # the 2 px corners vanilla rounds off
        for px, py in ((x, y), (right - x, y), (x, bottom - y), (right - x, bottom - y)):
            image.putpixel((px, py), (0, 0, 0, 0))
    left, top, field_right, field_bottom = FIELD_BOX
    draw.rectangle([left, TITLE_BAND[0], field_right, TITLE_BAND[1]], fill=BAND)
    draw.line([(left, RULE), (field_right, RULE)], fill=accent + (255,))
    draw.rectangle([left, STATUS_BAND[0], field_right, STATUS_BAND[1]], fill=BAND)
    draw.rectangle(FIELD_BOX, fill=FIELD)
    draw.line([(left, top), (field_right, top)], fill=FIELD_EDGE)
    draw.line([(left, top), (left, field_bottom)], fill=FIELD_EDGE)
    draw.line([(left, field_bottom), (field_right, field_bottom)], fill=LIGHT)
    draw.line([(field_right, top), (field_right, field_bottom)], fill=LIGHT)
    return image


def caption_lines(renderer, caption) -> list[Image.Image]:
    """The caption in `minecraft:default`, wrapped to the field, one image per line."""
    if isinstance(caption, str):
        caption = [{"text": caption}]
    rendered = renderer.render({"color": CAPTION_COLOR, "extra": caption},
                               width=ART_WIDTH - 2 * CAPTION_PADDING, zoom=1,
                               background=(0, 0, 0, 0))
    pad = render_text.BODY_PADDING
    band = rendered.crop((pad, pad, rendered.width - pad, rendered.height - pad))
    lines = []
    for top in range(0, band.height, LINE):
        strip = band.crop((0, top, band.width, top + LINE))
        if (ink := strip.getbbox()) is not None:
            lines.append(strip.crop((ink[0], 0, ink[2], LINE)))
    return lines


def panel(name: str, accent, lines: list[Image.Image], caption_rows: int) -> Image.Image:
    image = window(accent)
    caption_top = ART_BOTTOM + 1 - (caption_rows * LINE + 4)
    shot_height = caption_top - 1 - ART_TOP
    source = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "art", f"{name}.png")).convert("RGB")
    crop = min(source.width, round(source.height * ART_WIDTH / shot_height))
    left = (source.width - crop) // 2
    shot = source.crop((left, 0, left + crop, source.height))
    image.paste(shot.resize((ART_WIDTH, shot_height), Image.Resampling.LANCZOS),
                (ART_LEFT, ART_TOP))
    ImageDraw.Draw(image).rectangle([ART_LEFT, caption_top, ART_RIGHT, ART_BOTTOM],
                                    fill=BAND)
    top = caption_top + 2 + (caption_rows - len(lines)) * LINE // 2
    for index, line in enumerate(lines):
        image.alpha_composite(line, (ART_LEFT + (ART_WIDTH - line.width) // 2,
                                     top + index * LINE))
    # 256 colours carry the screenshot; the frame and bands are exact palette
    # entries, and transparency survives as a palette alpha.
    return image.quantize(256, method=Image.Quantize.LIBIMAGEQUANT,
                          dither=Image.Dither.NONE)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", default=".")
    parser.add_argument("--client-jar",
                        help="Minecraft client jar, for the captions' minecraft:default")
    args = parser.parse_args()

    jar = render_text.find_client_jar(args.client_jar)
    if jar is None:
        raise SystemExit("no client jar: the captions need minecraft:default")
    renderer = render_text.Renderer(render_text.AssetSource(args.pack_dir, jar, None))
    captions = [caption_lines(renderer, caption) for *_, caption in PANELS]
    rows = max(map(len, captions))

    texture_dir = os.path.join(args.pack_dir, "assets/sovereignmc/textures/font")
    for stale in glob.glob(os.path.join(texture_dir, "menu_*.png")):
        os.remove(stale)
    providers = []
    for (name, glyph, accent, _), lines in zip(PANELS, captions):
        path = os.path.join(texture_dir, f"menu_{name}.png")
        panel(name, accent, lines, rows).save(path, optimize=True)
        print(path, os.path.getsize(path), "bytes")
        providers.append({"type": "bitmap", "file": f"{FONT_ID.split(':')[0]}:font/menu_{name}.png",
                          "chars": [glyph], "ascent": 7, "height": HEIGHT})

    font_path = os.path.join(args.pack_dir, "assets/sovereignmc/font/menu.json")
    with open(font_path, "w", encoding="utf-8") as handle:
        json.dump({"providers": providers}, handle, separators=(",", ":"))
    print(font_path)


if __name__ == "__main__":
    main()
