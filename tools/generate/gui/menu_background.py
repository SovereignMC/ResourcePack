#!/usr/bin/env python3
"""Draw the selector dialogue's panels as `sovereignmc:menu` glyphs, in two sizes.

Each panel is one glyph drawn from the top of the dialogue's first body line: a
`minecraft:container`-style window with a title band and accent rule, the
screenshot and caption in an inset field, and a status band. The lobby
(SovereignPicoLobby `server_state/dialog.rs`) writes the panel name and player
count over the bands as live text, and carries the click events on spacing runs,
so no other glyphs are needed.

Sizes (width x rows of 9 px text lines):
    large    192 x 216 (24 rows), U+E00D..E00F, menu_<panel>.png: the old 600 px dialogue
    compact  152 x 180 (20 rows), U+E011..E013, menu_<panel>_s.png: fits a 480 x 270
             GUI, i.e. 1920x1080 at GUI scale 4
The lobby picks one per player via a footer toggle. U+E010 stays unused.

Writes (relative to --pack-dir):
    assets/sovereignmc/textures/font/menu_<panel>[_s].png   paletted
    assets/sovereignmc/font/menu.json

    python3 tools/generate/gui/menu_background.py --pack-dir . [--client-jar JAR]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import NamedTuple

from PIL import Image, ImageDraw

# render_text lives in tools/render; keep the generator runnable directly.
_TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_TOOLS, "render"))
import render_text



class Layout(NamedTuple):
    width: int
    rows: int
    suffix: str
    glyphs: tuple[str, str, str]  # events, nations, practice

    @property
    def height(self) -> int:
        return self.rows * LINE

    @property
    def status_row(self) -> int:
        return self.rows - 2

    @property
    def window_bottom(self) -> int:  # frame row; the 5 rows below stay clear of the total line
        return self.height - 6

    @property
    def field_box(self) -> tuple[int, int, int, int]:
        return (4, 18, self.width - 5, LINE * self.status_row - 2)

    @property
    def status_band(self) -> tuple[int, int]:
        return (LINE * self.status_row - 1, LINE * self.status_row + 8)

    @property
    def art_bottom(self) -> int:
        return LINE * self.status_row - 3

    @property
    def art_right(self) -> int:
        return self.width - 6

    @property
    def art_width(self) -> int:
        return self.art_right - ART_LEFT + 1


LAYOUTS = (
    Layout(192, 24, "", ("\uE00D", "\uE00E", "\uE00F")),
    Layout(152, 20, "_s", ("\uE011", "\uE012", "\uE013")),
)
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
# the status line is `rows - 2`, each with one band row above its caps.
TITLE_BAND = (8, 16)
RULE = 17
ART_LEFT, ART_TOP = 5, 19
CAPTION_PADDING = 3
CAPTION_COLOR = "#E8E8E8"
DISCORD_BLURPLE = "#5865F2"

# (name, accent rule colour, caption component)
PANELS = (
    ("events", (0xE0, 0x7B, 0x24), [
        {"text": "We regularly host PvP, War,\nMovecraft Events.\nCheck the "},
        {"text": "Discord Server", "color": DISCORD_BLURPLE},
        {"text": "\nfor updates."},
    ]),
    ("nations", (0xC9, 0xA2, 0x27),
     "1:750 Earth Map Geopol Towny\nPlanes, Ships, PvP,\nWars and Industry"),
    ("practice", (0x2F, 0x86, 0xB8),
     "Practice your PvP skills or Design cutting-edge ships in Plots, "
     "the sky's the limit"),
)


def window(layout: Layout, accent: tuple[int, int, int]) -> Image.Image:
    """Frame, bevel, title and status bands, accent rule and the inset field."""
    image = Image.new("RGBA", (layout.width, layout.height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    right, bottom = layout.width - 1, layout.window_bottom
    draw.rectangle([0, 0, right, bottom], fill=FRAME)
    draw.rectangle([1, 1, right - 1, bottom - 1], fill=SHADOW)
    draw.rectangle([1, 1, right - 3, bottom - 3], fill=LIGHT)
    draw.rectangle([3, 3, right - 3, bottom - 3], fill=PLATE)
    for x, y in ((0, 0), (1, 0), (0, 1)):  # the 2 px corners vanilla rounds off
        for px, py in ((x, y), (right - x, y), (x, bottom - y), (right - x, bottom - y)):
            image.putpixel((px, py), (0, 0, 0, 0))
    left, top, field_right, field_bottom = layout.field_box
    draw.rectangle([left, TITLE_BAND[0], field_right, TITLE_BAND[1]], fill=BAND)
    draw.line([(left, RULE), (field_right, RULE)], fill=accent + (255,))
    draw.rectangle([left, layout.status_band[0], field_right, layout.status_band[1]], fill=BAND)
    draw.rectangle(layout.field_box, fill=FIELD)
    draw.line([(left, top), (field_right, top)], fill=FIELD_EDGE)
    draw.line([(left, top), (left, field_bottom)], fill=FIELD_EDGE)
    draw.line([(left, field_bottom), (field_right, field_bottom)], fill=LIGHT)
    draw.line([(field_right, top), (field_right, field_bottom)], fill=LIGHT)
    return image


def caption_lines(layout: Layout, renderer, caption, reflow=False) -> list[Image.Image]:
    """The caption in `minecraft:default`, wrapped to the field, one image per line.

    When the field is too narrow for an authored line, the authored breaks are
    dropped and the whole caption wraps freely, so no word is left alone.
    """
    if isinstance(caption, str):
        caption = [{"text": caption}]
    if reflow:
        caption = [{**part, "text": part["text"].replace("\n", " ")} for part in caption]
    rendered = renderer.render({"color": CAPTION_COLOR, "extra": caption},
                               width=layout.art_width - 2 * CAPTION_PADDING, zoom=1,
                               background=(0, 0, 0, 0))
    pad = render_text.BODY_PADDING
    band = rendered.crop((pad, pad, rendered.width - pad, rendered.height - pad))
    lines = []
    for top in range(0, band.height, LINE):
        strip = band.crop((0, top, band.width, top + LINE))
        if (ink := strip.getbbox()) is not None:
            lines.append(strip.crop((ink[0], 0, ink[2], LINE)))
    authored = 1 + sum(part["text"].count("\n") for part in caption)
    if not reflow and len(lines) > authored:
        return caption_lines(layout, renderer, caption, reflow=True)
    return lines


def panel(layout: Layout, name: str, accent, lines: list[Image.Image], caption_rows: int) -> Image.Image:
    image = window(layout, accent)
    art_width, art_right, art_bottom = layout.art_width, layout.art_right, layout.art_bottom
    caption_top = art_bottom + 1 - (caption_rows * LINE + 4)
    shot_height = caption_top - 1 - ART_TOP
    source = Image.open(os.path.join(_TOOLS, "art", "menu", f"{name}.png")).convert("RGB")
    crop = min(source.width, round(source.height * art_width / shot_height))
    left = (source.width - crop) // 2
    shot = source.crop((left, 0, left + crop, source.height))
    image.paste(shot.resize((art_width, shot_height), Image.Resampling.LANCZOS),
                (ART_LEFT, ART_TOP))
    ImageDraw.Draw(image).rectangle([ART_LEFT, caption_top, art_right, art_bottom],
                                    fill=BAND)
    top = caption_top + 2 + (caption_rows - len(lines)) * LINE // 2
    for index, line in enumerate(lines):
        image.alpha_composite(line, (ART_LEFT + (art_width - line.width) // 2,
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
    texture_dir = os.path.join(args.pack_dir, "assets/sovereignmc/textures/font")
    for stale in glob.glob(os.path.join(texture_dir, "menu_*.png")):
        os.remove(stale)
    providers = []
    for layout in LAYOUTS:
        captions = [caption_lines(layout, renderer, caption) for *_, caption in PANELS]
        rows = max(map(len, captions))
        for (name, accent, _), glyph, lines in zip(PANELS, layout.glyphs, captions):
            file = f"menu_{name}{layout.suffix}.png"
            path = os.path.join(texture_dir, file)
            panel(layout, name, accent, lines, rows).save(path, optimize=True)
            print(path, os.path.getsize(path), "bytes")
            providers.append({"type": "bitmap", "file": f"{FONT_ID.split(':')[0]}:font/{file}",
                              "chars": [glyph], "ascent": 7, "height": layout.height})

    font_path = os.path.join(args.pack_dir, "assets/sovereignmc/font/menu.json")
    with open(font_path, "w", encoding="utf-8") as handle:
        json.dump({"providers": providers}, handle, separators=(",", ":"))
    print(font_path)


if __name__ == "__main__":
    main()
