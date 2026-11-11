#!/usr/bin/env python3
"""Draw the selector dialogue's vanilla container panels and print the /dialog command.

Each panel is a 192 x 252 px `minecraft:container`-style window, cut into 9 px
rows so the client's fixed line pitch (see gio/gjy in the 1.21.11 jar) can draw
it: a 3 px bevel with the vanilla palette, a title row carrying a 1 px accent
rule, a 24 line inset field, a status row and the closing bevel. Every row is one
bitmap glyph in `sovereignmc:menu` (ascent 7 / height 9), repeated down the
dialogue by the Rust builder.

Writes (relative to --pack-dir):
    assets/sovereignmc/textures/font/menu_top.png            192x9 RGBA
    assets/sovereignmc/textures/font/menu_label_<panel>.png  192x9 RGBA
    assets/sovereignmc/textures/font/menu_body_top.png       192x9 RGBA
    assets/sovereignmc/textures/font/menu_body.png           192x9 RGBA
    assets/sovereignmc/textures/font/menu_body_bottom.png    192x9 RGBA
    assets/sovereignmc/textures/font/menu_status.png         192x9 RGBA
    assets/sovereignmc/textures/font/menu_bottom.png         192x9 RGBA
    assets/sovereignmc/font/menu.json

Example:
    python3 tools/generate_menu_background.py --pack-dir .
"""
from __future__ import annotations

import argparse
import json
import os

from PIL import Image, ImageDraw

WIDTH, HEIGHT = 192, 9
BODY_ROWS = 24
ASCENT, GLYPH_HEIGHT = 7, 9

# `minecraft:textures/gui/container/inventory.png` and `.../container/slot.png`
# palette: 1 px black frame, 2 px light bevel, plate, 2 px shadow bevel.
FRAME = (0, 0, 0, 255)
LIGHT = (255, 255, 255, 255)
PLATE = (198, 198, 198, 255)
SHADOW = (85, 85, 85, 255)
FIELD = (139, 139, 139, 255)
FIELD_EDGE = (55, 55, 55, 255)
# Title and status rows are dark bands, so the light palette's accent text keeps
# the contrast the plain #404040-on-plate container grey loses without a shadow.
BAND = (0x2B, 0x2B, 0x2B, 255)

# Inset field: 1 px of plate on each side of the window's bevel.
FIELD_LEFT, FIELD_TOP, FIELD_RIGHT = 4, 18, WIDTH - 5
# The field's rows are the pack's body rows; its white bottom bevel sits one row
# above the last line, which belongs to the status band.
FIELD_BOTTOM = FIELD_TOP + HEIGHT * BODY_ROWS - 2
RULE_ROW = FIELD_TOP - 1
STATUS_ROW = FIELD_BOTTOM + 1
PANEL_HEIGHT = STATUS_ROW + 19

TOP_GLYPH = "\uE004"
BODY_TOP_GLYPH = "\uE008"
BODY_GLYPH = "\uE009"
BODY_BOTTOM_GLYPH = "\uE00A"
STATUS_GLYPH = "\uE00B"
BOTTOM_GLYPH = "\uE00C"

PANELS = (
    ("events", "\uE005", (0xE0, 0x7B, 0x24), "#FFC24D", "EVENTS"),
    ("nations", "\uE006", (0xC9, 0xA2, 0x27), "#FFE08A", "NATIONS"),
    ("practice", "\uE007", (0x2F, 0x86, 0xB8), "#8FE3FF", "PRACTICE"),
)
FONT_ID = "sovereignmc:menu"
TEXT_FONT = "minecraft:default"


def window_pixels() -> Image.Image:
    """One panel window: rounded frame, vanilla bevel, inset field, accent rule."""
    image = Image.new("RGBA", (WIDTH, PANEL_HEIGHT), PLATE)
    px = image.load()
    # 2 px bevel: light on the top/left, shadow on the bottom/right.
    for y in range(1, PANEL_HEIGHT - 1):
        px[1, y], px[2, y] = LIGHT, LIGHT
        px[WIDTH - 2, y], px[WIDTH - 3, y] = SHADOW, SHADOW
    for x in range(1, WIDTH - 1):
        px[x, 1], px[x, 2] = LIGHT, LIGHT
        px[x, PANEL_HEIGHT - 2], px[x, PANEL_HEIGHT - 3] = SHADOW, SHADOW
    # 1 px black frame, then the 2 px corners the vanilla textures round off.
    for x in range(WIDTH):
        px[x, 0] = px[x, PANEL_HEIGHT - 1] = FRAME
    for y in range(PANEL_HEIGHT):
        px[0, y] = px[WIDTH - 1, y] = FRAME
    for x, y in ((0, 0), (1, 0), (0, 1),
                 (WIDTH - 1, 0), (WIDTH - 2, 0), (WIDTH - 1, 1),
                 (0, PANEL_HEIGHT - 1), (1, PANEL_HEIGHT - 1), (0, PANEL_HEIGHT - 2),
                 (WIDTH - 1, PANEL_HEIGHT - 1), (WIDTH - 2, PANEL_HEIGHT - 1),
                 (WIDTH - 1, PANEL_HEIGHT - 2)):
        px[x, y] = (0, 0, 0, 0)
    return image


def panel_slice(accent: tuple[int, int, int], kind: str) -> Image.Image:
    image = window_pixels()
    draw = ImageDraw.Draw(image)

    if kind == "top":
        # The band starts one row into the bevel row: vanilla caps ink the row
        # at the top of their line, so a band starting on the text line would
        # leave the letters flush against its edge.
        draw.line([(FIELD_LEFT, HEIGHT - 1), (FIELD_RIGHT, HEIGHT - 1)], fill=BAND)
    elif kind == "label":
        draw.rectangle([FIELD_LEFT, 9, FIELD_RIGHT, RULE_ROW - 1], fill=BAND)
        # The accent rule closes the title band and keeps the three panels apart.
        draw.line([(FIELD_LEFT, RULE_ROW), (FIELD_RIGHT, RULE_ROW)], fill=accent + (255,))
    elif kind == "status":
        draw.rectangle([FIELD_LEFT, STATUS_ROW, FIELD_RIGHT, STATUS_ROW + 8], fill=BAND)
    elif kind.startswith("body"):
        if kind == "body_bottom":
            # The status band starts one row early, leaving the same 1 px gap
            # above its text as the title band has above the panel name.
            draw.line([(FIELD_LEFT, FIELD_BOTTOM + 1), (FIELD_RIGHT, FIELD_BOTTOM + 1)],
                      fill=BAND)
        draw.rectangle([FIELD_LEFT, FIELD_TOP, FIELD_RIGHT, FIELD_BOTTOM], fill=FIELD)
        draw.line([(FIELD_LEFT, FIELD_TOP), (FIELD_RIGHT, FIELD_TOP)], fill=FIELD_EDGE)
        draw.line([(FIELD_LEFT, FIELD_TOP), (FIELD_LEFT, FIELD_BOTTOM)], fill=FIELD_EDGE)
        draw.line([(FIELD_LEFT, FIELD_BOTTOM), (FIELD_RIGHT, FIELD_BOTTOM)], fill=LIGHT)
        draw.line([(FIELD_RIGHT, FIELD_TOP), (FIELD_RIGHT, FIELD_BOTTOM)], fill=LIGHT)

    # Line -> panel pixel offset. The body is the field: its top edge, the plain
    # rows and its bottom edge.
    offsets = {
        "top": 0,
        "label": 9,
        "body_top": FIELD_TOP,
        "body": FIELD_TOP + 9,
        "body_bottom": FIELD_BOTTOM - HEIGHT + 2,
        "status": STATUS_ROW,
        "bottom": STATUS_ROW + HEIGHT,
    }
    top = offsets[kind]
    return image.crop((0, top, WIDTH, top + HEIGHT))


def font_definition() -> dict:
    providers = []
    for name, glyph, _accent, _colour, _title in PANELS:
        providers.append({
            "type": "bitmap",
            "file": f"sovereignmc:font/menu_label_{name}.png",
            "chars": [glyph], "ascent": ASCENT, "height": GLYPH_HEIGHT,
        })
    for kind, glyph in (("top", TOP_GLYPH), ("body_top", BODY_TOP_GLYPH),
                        ("body", BODY_GLYPH), ("body_bottom", BODY_BOTTOM_GLYPH),
                        ("status", STATUS_GLYPH), ("bottom", BOTTOM_GLYPH)):
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
    return index * (WIDTH + 5)


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
    rows = [TOP_GLYPH, None, BODY_TOP_GLYPH] + [BODY_GLYPH] * (BODY_ROWS - 2) + \
           [BODY_BOTTOM_GLYPH, STATUS_GLYPH, BOTTOM_GLYPH]
    line_width = panel_left(2) + WIDTH + 1
    for row in rows:
        glyphs = [PANELS[index][1] if row is None else row for index in range(3)]
        components, pen = glyph_row(glyphs)
        flat.extend(components)
        if row is None:
            for index, panel in enumerate(PANELS):
                title = panel[4]
                left = panel_left(index) + (WIDTH - text_width(title)) // 2
                if left != pen:
                    flat.append(advance(left - pen))
                flat.append({"text": title, "color": panel[3], "font": TEXT_FONT, "bold": True})
                pen = left + text_width(title)
        # Pad every row out to the panel rows' width so the client's per-line
        # centring cannot shift the panels against each other.
        if pen < line_width:
            flat.append(advance(line_width - pen))
        flat.append({"text": "\n"})
    return flat


def dialog() -> dict:
    return {
        "type": "minecraft:notice",
        "title": "SovereignMC",
        "body": {"type": "minecraft:plain_message", "width": 600, "contents": contents()},
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

    for name, _glyph, accent, _colour, _title in PANELS:
        path = os.path.join(texture_dir, f"menu_label_{name}.png")
        panel_slice(accent, "label").save(path)
        print(path)
    for kind in ("top", "body_top", "body", "body_bottom", "status", "bottom"):
        path = os.path.join(texture_dir, f"menu_{kind}.png")
        panel_slice(PANELS[0][2], kind).save(path)
        print(path)

    font_path = os.path.join(font_dir, "menu.json")
    with open(font_path, "w", encoding="utf-8") as handle:
        json.dump(font_definition(), handle, indent=2)
        handle.write("\n")
    print(font_path)

    print("/dialog show @s " + snbt(dialog(), args.escape))


if __name__ == "__main__":
    main()
