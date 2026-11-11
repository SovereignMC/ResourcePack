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
    assets/sovereignmc/textures/font/menu_panel_<panel>.png  192x216 RGBA
    assets/sovereignmc/textures/font/menu_status.png         192x9 RGBA
    assets/sovereignmc/textures/font/menu_bottom.png         192x9 RGBA
    assets/sovereignmc/font/menu.json

`menu_panel_<panel>.png` is the whole 24 row field in one glyph: the vanilla
field art with that panel's screenshot cropped into the inset area and the
caption laid out under it, so the client draws the field in one line and the
remaining field rows only carry the click overlays.

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
STATUS_GLYPH = "\uE00B"
BOTTOM_GLYPH = "\uE00C"
# 192 x 9 and fully transparent except for one pixel in the last column, which
# keeps the glyph's advance at 193 while the field art above it stays visible.
# The client picks the hovered character by x, line by line, so every field row
# needs its own hit glyph to carry the panel's click and hover events.
HIT_GLYPH = "\uE010"

# The field: a 24 row composite per panel, carrying the screenshot and caption.
ART_TOP = FIELD_TOP + 1
ART_LEFT, ART_RIGHT = FIELD_LEFT + 1, FIELD_RIGHT - 1
ART_WIDTH = ART_RIGHT - ART_LEFT + 1
ART_HEIGHT = 144
CAPTION_TOP = ART_TOP + ART_HEIGHT + 1
CAPTION_BOTTOM = FIELD_BOTTOM - 1
CAPTION_PADDING = 4
CAPTION_COLOR = "#E8E8E8"

# The caption is a text component: a string, or a list of spans to colour part
# of it (the Discord invite keeps the brand blurple).
DISCORD_BLURPLE = "#5865F2"

PANELS = (
    ("events", "\uE005", (0xE0, 0x7B, 0x24), "#FFC24D", "EVENTS", "\uE00D", [
        {"text": "We regularly host PvP, War,\nMovecraft Events.\nCheck the "},
        {"text": "Discord Server", "color": DISCORD_BLURPLE},
        {"text": "\nfor updates."},
    ]),
    ("nations", "\uE006", (0xC9, 0xA2, 0x27), "#FFE08A", "NATIONS", "\uE00E",
     "1:750 Earth Map Geopol Towny\nPlanes, Ships, PvP,\nWars and Industry"),
    ("practice", "\uE007", (0x2F, 0x86, 0xB8), "#8FE3FF", "PRACTICE", "\uE00F",
     "Practice your PvP skills or Design cutting-edge ships in Plots, "
     "the sky's the limit"),
)
ART_DIR = "art"
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


def hit_slice() -> Image.Image:
    """Invisible click target: no ink, but the last column keeps the advance."""
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    image.putpixel((WIDTH - 1, 0), (0, 0, 0, 1))
    return image


def panel_art(name: str, caption: str | list[dict], pack_dir: str,
              client_jar: str | None) -> Image.Image:
    """The whole 24 row field: vanilla field art, the screenshot and its caption.

    Drawing it as one glyph keeps the client from re-pitching the field, so the
    screenshot lands on exact pixels; `menu.json` gives it ascent 7 and height
    216, which the renderer and the client both read as "top of this line".
    """
    image = Image.new("RGBA", (WIDTH, HEIGHT * BODY_ROWS), (0, 0, 0, 0))
    rows = [panel_slice(PANELS[0][2], "body_top")]
    rows += [panel_slice(PANELS[0][2], "body")] * (BODY_ROWS - 2)
    rows.append(panel_slice(PANELS[0][2], "body_bottom"))
    for index, row in enumerate(rows):
        image.paste(row, (0, index * HEIGHT))

    source = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     ART_DIR, f"{name}.png")).convert("RGB")
    crop_width = min(source.width, round(source.height * ART_WIDTH / ART_HEIGHT))
    left = (source.width - crop_width) // 2
    shot = source.crop((left, 0, left + crop_width, source.height))
    shot = shot.resize((ART_WIDTH, ART_HEIGHT), Image.Resampling.LANCZOS)
    # Composite rows are panel rows shifted by FIELD_TOP.
    origin = -FIELD_TOP
    image.paste(shot, (ART_LEFT, ART_TOP + origin))

    import render_text

    jar = render_text.find_client_jar(client_jar)
    if jar is None:
        raise SystemExit("no client jar: the caption needs minecraft:default")
    renderer = render_text.Renderer(render_text.AssetSource(pack_dir, jar, None))
    width = ART_WIDTH - 2 * CAPTION_PADDING
    if isinstance(caption, str):
        caption = [{"text": caption}]
    rendered = renderer.render({"color": CAPTION_COLOR, "font": TEXT_FONT,
                                "extra": caption},
                               width=width, zoom=1, background=(0, 0, 0, 0))
    pad = render_text.BODY_PADDING
    band = rendered.crop((pad, pad, rendered.width - pad, rendered.height - pad))
    lines = []
    for index in range(band.height // HEIGHT):
        strip = band.crop((0, index * HEIGHT, band.width, (index + 1) * HEIGHT))
        ink = strip.getbbox()
        if ink is not None:
            lines.append(strip.crop((ink[0], 0, ink[2], HEIGHT)))
    band_height = CAPTION_BOTTOM - CAPTION_TOP + 1
    top = CAPTION_TOP + origin + (band_height - len(lines) * HEIGHT) // 2
    ImageDraw.Draw(image).rectangle(
        [ART_LEFT, CAPTION_TOP + origin, ART_RIGHT, CAPTION_BOTTOM + origin], fill=BAND)
    for index, line in enumerate(lines):
        x = ART_LEFT + (ART_WIDTH - line.width) // 2
        image.alpha_composite(line, (x, top + index * HEIGHT))
    return image


def font_definition() -> dict:
    providers = []
    for name, glyph, _accent, _colour, _title, art_glyph, _caption in PANELS:
        providers.append({
            "type": "bitmap",
            "file": f"sovereignmc:font/menu_label_{name}.png",
            "chars": [glyph], "ascent": ASCENT, "height": GLYPH_HEIGHT,
        })
    for name, _glyph, _accent, _colour, _title, art_glyph, _caption in PANELS:
        providers.append({
            "type": "bitmap",
            "file": f"sovereignmc:font/menu_panel_{name}.png",
            "chars": [art_glyph], "ascent": ASCENT, "height": HEIGHT * BODY_ROWS,
        })
    providers.append({
        "type": "bitmap",
        "file": "sovereignmc:font/menu_hit.png",
        "chars": [HIT_GLYPH], "ascent": ASCENT, "height": GLYPH_HEIGHT,
    })
    for kind, glyph in (("top", TOP_GLYPH), ("status", STATUS_GLYPH),
                        ("bottom", BOTTOM_GLYPH)):
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


def panel_events(index: int) -> dict:
    """Click and hover for panel `index`, added to every component of its column."""
    return {
        "click_event": {"action": "custom", "id": f"sovereignmc:menu/{index}"},
        "hover_event": {"action": "show_text",
                        "value": {"text": f"Click to join {PANELS[index][0]}"}},
    }


def advance_for(delta: int, index: int) -> dict:
    return {**advance(delta), **panel_events(index)}


def glyph_row(glyphs) -> tuple[list[dict], int]:
    components: list[dict] = []
    pen = 0
    for index, glyph in enumerate(glyphs):
        left = panel_left(index)
        if left != pen:
            components.append(advance_for(left - pen, index))
        components.append({"text": glyph, "font": FONT_ID, **panel_events(index)})
        pen = left + WIDTH + 1
    return components, pen


def contents() -> list[dict]:
    flat: list[dict] = []
    # `None` is the title row, `"field"` the 24 row composite, `"blank"` one of
    # the field rows the composite covers, which still needs a hit glyph: the
    # client resolves the hovered component per line and by x.
    rows = [TOP_GLYPH, None, "field"] + ["blank"] * (BODY_ROWS - 1) + \
           [STATUS_GLYPH, BOTTOM_GLYPH]
    line_width = panel_left(2) + WIDTH + 1
    for row in rows:
        if row == "blank":
            components, pen = glyph_row([HIT_GLYPH] * 3)
            flat.extend(components)
        else:
            if row == "field":
                glyphs = [panel[5] for panel in PANELS]
            else:
                glyphs = [PANELS[index][1] if row is None else row for index in range(3)]
            components, pen = glyph_row(glyphs)
            flat.extend(components)
        if row is None:
            for index, panel in enumerate(PANELS):
                title = panel[4]
                left = panel_left(index) + (WIDTH - text_width(title)) // 2
                if left != pen:
                    flat.append(advance_for(left - pen, index))
                flat.append({"text": title, "color": panel[3], "font": TEXT_FONT,
                             "bold": True, **panel_events(index)})
                pen = left + text_width(title)
        # Pad every row out to the panel rows' width so the client's per-line
        # centring cannot shift the panels against each other.
        if pen < line_width:
            flat.append(advance_for(line_width - pen, len(PANELS) - 1))
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
    parser.add_argument("--client-jar",
                        help="Minecraft client jar, for the captions' minecraft:default")
    parser.add_argument("--escape", action="store_true",
                        help="emit \\uXXXX escapes instead of raw auxiliary characters")
    args = parser.parse_args()

    texture_dir = os.path.join(args.pack_dir, "assets/sovereignmc/textures/font")
    font_dir = os.path.join(args.pack_dir, "assets/sovereignmc/font")
    os.makedirs(texture_dir, exist_ok=True)
    os.makedirs(font_dir, exist_ok=True)

    for name, _glyph, accent, _colour, _title, _art_glyph, caption in PANELS:
        path = os.path.join(texture_dir, f"menu_label_{name}.png")
        panel_slice(accent, "label").save(path)
        print(path)
        path = os.path.join(texture_dir, f"menu_panel_{name}.png")
        panel_art(name, caption, args.pack_dir, args.client_jar).save(path)
        print(path)
    path = os.path.join(texture_dir, "menu_hit.png")
    hit_slice().save(path)
    print(path)
    for kind in ("top", "status", "bottom"):
        path = os.path.join(texture_dir, f"menu_{kind}.png")
        panel_slice(PANELS[0][2], kind).save(path)
        print(path)
    for stale in (f"menu_{kind}.png" for kind in ("body_top", "body", "body_bottom")):
        path = os.path.join(texture_dir, stale)
        if os.path.exists(path):
            os.remove(path)
            print(f"removed {path}")

    font_path = os.path.join(font_dir, "menu.json")
    with open(font_path, "w", encoding="utf-8") as handle:
        json.dump(font_definition(), handle, indent=2)
        handle.write("\n")
    print(font_path)

    print("/dialog show @s " + snbt(dialog(), args.escape))


if __name__ == "__main__":
    main()
