#!/usr/bin/env python3
"""Draw the menu banner panels and print the /dialog command that labels them.

Each panel is a stack of 96x20 slices exposed as bitmap glyphs in
sovereignmc:menu (ascent 13 / height 20, the metrics tinsel:hud_background
uses). One slice per text line, so the panels are three glyph columns repeated
down the dialog; the headers carry the labels as ordinary text components
placed with tinsel:spacing, and the body slices are empty inset rows waiting
for images and copy to be dropped in later.

Writes (relative to --pack-dir):
    assets/sovereignmc/textures/font/menu_body.png              96x20 RGBA
    assets/sovereignmc/textures/font/menu_header_<panel>.png    96x20 RGBA
    assets/sovereignmc/textures/font/menu_footer_<panel>.png    96x20 RGBA
    assets/sovereignmc/font/menu.json

Example:
    python3 tools/generate_menu_background.py --pack-dir .
"""
from __future__ import annotations

import argparse
import json
import os

from PIL import Image, ImageDraw

WIDTH, HEIGHT = 96, 9
GAP = 4
BODY_ROWS = 12
# The client lays text out on a fixed 9 px line pitch (see gio/gjy in the 1.21.11
# jar): a taller glyph does not push the next line down, it gets overdrawn. So the
# slices are exactly one line tall and ascent 7 puts a slice on rows 0..8.
ASCENT, GLYPH_HEIGHT = 7, 9

PANELS = (
    ("events", "\uE004", "\uE005", (0xE0, 0x7B, 0x24), "#FFC24D", "EVENTS"),
    ("nations", "\uE006", "\uE007", (0xC9, 0xA2, 0x27), "#FFE08A", "NATIONS"),
    ("practice", "\uE008", "\uE009", (0x2F, 0x86, 0xB8), "#8FE3FF", "PRACTICE"),
)
TITLE_GLYPH = "\uE00A"
BODY_GLYPH = "\uE00B"
FONT_ID = "sovereignmc:menu"
TEXT_FONT = "minecraft:default"

PLATE = (0, 0, 0, 165)
INSET = (0, 0, 0, 60)
BEVEL_DARK = (0, 0, 0, 235)
DIVIDER = (0, 0, 0, 190)


def _layer() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (WIDTH, HEIGHT))
    return image, ImageDraw.Draw(image)


def _plate() -> Image.Image:
    image, draw = _layer()
    draw.rectangle([0, 0, WIDTH - 1, HEIGHT - 1], fill=PLATE)
    return image


def _frame(accent: tuple[int, int, int] | None, divider: bool) -> Image.Image:
    """Dark side borders, optional accent rule on the last row. No light bevels."""
    image, draw = _layer()
    draw.line([(0, 0), (0, HEIGHT - 1)], fill=BEVEL_DARK)
    draw.line([(WIDTH - 1, 0), (WIDTH - 1, HEIGHT - 1)], fill=BEVEL_DARK)
    if accent is not None:
        draw.line([(1, HEIGHT - 1), (WIDTH - 2, HEIGHT - 1)], fill=accent + (255,))
    if divider:
        draw.line([(1, HEIGHT - 1), (WIDTH - 2, HEIGHT - 1)], fill=DIVIDER)
    return image


def build_bar(accent: tuple[int, int, int]) -> Image.Image:
    """Accent band that caps each panel; the label goes on the row below it."""
    image = _plate()
    band, draw = _layer()
    draw.rectangle([0, 0, WIDTH - 1, HEIGHT - 1], fill=accent + (255,))
    draw.line([(0, HEIGHT - 1), (WIDTH - 1, HEIGHT - 1)], fill=BEVEL_DARK)
    image.alpha_composite(band)
    return image


def build_title() -> Image.Image:
    """Plain plate row: the label text sits on this one."""
    image = _plate()
    frame, draw = _layer()
    draw.line([(0, 0), (0, HEIGHT - 1)], fill=BEVEL_DARK)
    draw.line([(WIDTH - 1, 0), (WIDTH - 1, HEIGHT - 1)], fill=BEVEL_DARK)
    image.alpha_composite(frame)
    return image


def build_body() -> Image.Image:
    """Flat inset row: no bevel lines, so the panel reads as one dark surface."""
    image = _plate()
    inset, draw = _layer()
    draw.rectangle([3, 1, WIDTH - 4, HEIGHT - 2], fill=INSET)
    image.alpha_composite(inset)
    image.alpha_composite(_frame(None, divider=True))
    return image


def build_footer(accent: tuple[int, int, int]) -> Image.Image:
    image = _plate()
    stripe, draw = _layer()
    draw.rectangle([1, HEIGHT - 2, WIDTH - 2, HEIGHT - 1], fill=accent + (230,))
    image.alpha_composite(stripe)
    image.alpha_composite(_frame(None, divider=False))
    return image


def font_definition() -> dict:
    providers = []
    for name, bar, footer, _accent, _colour, _title in PANELS:
        for kind, glyph in (("bar", bar), ("footer", footer)):
            providers.append({
                "type": "bitmap",
                "file": f"sovereignmc:font/menu_{kind}_{name}.png",
                "chars": [glyph], "ascent": ASCENT, "height": GLYPH_HEIGHT,
            })
    for kind, glyph in (("title", TITLE_GLYPH), ("body", BODY_GLYPH)):
        providers.append({
            "type": "bitmap",
            "file": f"sovereignmc:font/menu_{kind}.png",
            "chars": [glyph], "ascent": ASCENT, "height": GLYPH_HEIGHT,
        })
    return {"providers": providers}


# tinsel:spacing is a power-of-two space font; U+E000.. climbs +1..+1024,
# U+F8FF.. climbs -1..-1024.
ADVANCES = (
    (1024, 0xE00A, 0xF8F5), (512, 0xE009, 0xF8F6), (256, 0xE008, 0xF8F7),
    (128, 0xE007, 0xF8F8), (64, 0xE006, 0xF8F9), (32, 0xE005, 0xF8FA),
    (16, 0xE004, 0xF8FB), (8, 0xE003, 0xF8FC), (4, 0xE002, 0xF8FD),
    (2, 0xE001, 0xF8FE), (1, 0xE000, 0xF8FF),
)


def advance(delta: int) -> dict:
    """One tinsel:spacing component whose advances sum to exactly `delta`."""
    remaining, text = abs(delta), ""
    for value, positive, negative in ADVANCES:
        while remaining >= value:
            text += chr(positive if delta > 0 else negative)
            remaining -= value
    assert remaining == 0, delta
    return {"text": text, "font": "tinsel:spacing"}


def text_width(text: str) -> int:
    """Bold vanilla text: 6 px per glyph (4 for 'I') plus 1 px of bold spread."""
    return sum(4 if c == "I" else 6 for c in text) + len(text)


def panel_left(index: int) -> int:
    return index * (WIDTH + 1 + GAP)


def glyph_row(glyphs) -> tuple[list[dict], int]:
    components: list[dict] = []
    pen = 0
    for index, glyph in enumerate(glyphs):
        left = panel_left(index)
        if left != pen:
            components.append(advance(left - pen))
        components.append({"text": glyph, "font": FONT_ID})
        pen = left + WIDTH + 1
    return components, pen


def contents() -> list[dict]:
    flat: list[dict] = []

    bars, pen = glyph_row([panel[1] for panel in PANELS])
    line_width = pen
    flat.extend(bars)

    flat.append({"text": "\n"})
    titles, pen = glyph_row([TITLE_GLYPH] * len(PANELS))
    flat.extend(titles)
    for index, panel in enumerate(PANELS):
        title = panel[5]
        left = panel_left(index) + (WIDTH - text_width(title)) // 2
        if left != pen:
            flat.append(advance(left - pen))
        flat.append({"text": title, "color": panel[4], "font": TEXT_FONT, "bold": True})
        pen = left + text_width(title)
    # Pad the label line back out to the glyph lines' width so every line of the
    # body measures the same, whatever alignment the dialog applies per line.
    if pen < line_width:
        flat.append(advance(line_width - pen))

    for _ in range(BODY_ROWS):
        flat.append({"text": "\n"})
        row, _ = glyph_row([BODY_GLYPH] * len(PANELS))
        flat.extend(row)

    flat.append({"text": "\n"})
    footers, _ = glyph_row([panel[2] for panel in PANELS])
    flat.extend(footers)
    return flat


def dialog() -> dict:
    return {
        "type": "minecraft:notice",
        "title": "SovereignMC",
        "body": {"type": "minecraft:plain_message", "width": 310, "contents": contents()},
        "action": {"label": "Close"},
    }


def escape(text: str) -> str:
    r"""\uXXXX-escape everything outside printable ASCII so commands stay readable."""
    out = []
    for ch in text:
        if 0x20 <= ord(ch) < 0x7F and ch not in '"\\':
            out.append(ch)
        else:
            out.append(f"\\u{ord(ch):04X}")
    return "".join(out)


def snbt(value, ascii_only: bool = False) -> str:
    if isinstance(value, bool):
        return "1b" if value else "0b"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        if ascii_only:
            return f'"{escape(value)}"'
        escaped = (value.replace("\\", "\\\\").replace('"', '\\"')
                   .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"))
        return f'"{escaped}"'
    if isinstance(value, list):
        return "[" + ",".join(snbt(v, ascii_only) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(f"{k}:{snbt(v, ascii_only)}" for k, v in value.items()) + "}"
    raise TypeError(type(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", default=".")
    parser.add_argument("--escape", action="store_true",
                        help="emit \\uXXXX escapes instead of raw auxiliary characters")
    args = parser.parse_args()

    texture_dir = os.path.join(args.pack_dir, "assets/sovereignmc/textures/font")
    font_dir = os.path.join(args.pack_dir, "assets/sovereignmc/font")
    os.makedirs(texture_dir, exist_ok=True)
    os.makedirs(font_dir, exist_ok=True)

    for name, _bar, _footer, accent, _colour, _title in PANELS:
        for kind, image in (("bar", build_bar(accent)),
                            ("footer", build_footer(accent))):
            path = os.path.join(texture_dir, f"menu_{kind}_{name}.png")
            image.save(path)
            print(path)
    for kind, image in (("title", build_title()), ("body", build_body())):
        path = os.path.join(texture_dir, f"menu_{kind}.png")
        image.save(path)
        print(path)

    font_path = os.path.join(font_dir, "menu.json")
    with open(font_path, "w", encoding="utf-8") as handle:
        json.dump(font_definition(), handle, indent=2)
        handle.write("\n")
    print(font_path)

    print("/dialog show @s " + snbt(dialog(), args.escape))


if __name__ == "__main__":
    main()
