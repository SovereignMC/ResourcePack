#!/usr/bin/env python3
"""Draw the tablist header art and the small rank-tag font used by TAB on the proxy.

Fonts:
    sovereignmc:tab        U+E100 U+E10F U+E102   rule: 360 GUI px, #9FC3D4 over a 1 px dark
                                                  under-shade, 40 px fades at both ends,
                                                  1 texel per GUI px in a 5 px cell
                                                  (ascent 5) so it lands on rows 3-4 of its line
                           U+E101 U+E10F U+E103   "SovereignMC" wordmark in Cinzel Bold small
                                                  caps, 200 x 29 GUI px at 2 texels per GUI px
                                                  (ascent 4: drawn from its line down over the
                                                  next three empty header lines)
                           U+E10F                 -1 px space that joins the halves
    sovereignmc:tab_small  5 px capitals for A-Z, 0-9 and - _ . + (lowercase maps to the
                           same capitals). "[" and "]" are zero-width spaces, so a LuckPerms
                           prefix such as "&8[&#D883E6Duke&8] " renders as just "DUKE " in
                           the tablist while chat keeps the brackets.

Client limits these follow (the 1.21.8/1.21.11 font loader, see tools/verify/glyphs.py):
    * a bitmap provider's ascent may not exceed its height, or the whole font is dropped;
    * a glyph cell larger than 256 px either way does not fit the 256x256 font atlas and
      renders as a missing-glyph box. So the rule and the wordmark are each split into two
      cells of the same image, drawn as  left, U+E10F (-1 px), right. The client measures a
      glyph's advance from its last inked column, so a left cell whose last column is empty
      gets one alpha-1 texel there (PackSquash must keep these PNGs lossless, see
      .github/workflows/squash-release.yml).

The proxy's TAB config uses them as:
    header: '', <rule>, <wordmark>, '', '', '', <rule>, ''
        <rule>     = <font:sovereignmc:tab>\ue100\ue10f\ue102</font>
        <wordmark> = <font:sovereignmc:tab>\ue101\ue10f\ue103</font>
    groups.yml _DEFAULT_:
        tabprefix:     "<font:sovereignmc:tab_small><!shadow>%luckperms-prefix%"
        customtabname: "<font:minecraft:default><shadow:#000000:0.75>%condition:nick%"
    Nothing is closed: TAB parses prefix + name as one string, so a closing tag would also
    close the name colour that ends the LuckPerms prefix (and TAB prints "</!shadow>" as text).

Writes (relative to --pack-dir):
    assets/sovereignmc/textures/font/tab/{tab_rule,tab_wordmark,small_caps}.png
    assets/sovereignmc/font/{tab,tab_small}.json

    python3 tools/generate/gui/tablist.py --pack-dir . [--cinzel PATH/Cinzel-Bold.ttf]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

TEXELS = 2          # texels per GUI pixel for the header art
SUPERSAMPLE = 4     # wordmark is drawn larger, then downsampled
RULE_WIDTH = 360    # GUI px
RULE_COLOR = (159, 195, 212)
SHADE = (20, 26, 32)

SMALL_GLYPHS = {
    'A': ["010", "101", "111", "101", "101"], 'B': ["110", "101", "110", "101", "110"],
    'C': ["011", "100", "100", "100", "011"], 'D': ["110", "101", "101", "101", "110"],
    'E': ["111", "100", "110", "100", "111"], 'F': ["111", "100", "110", "100", "100"],
    'G': ["011", "100", "101", "101", "011"], 'H': ["101", "101", "111", "101", "101"],
    'I': ["111", "010", "010", "010", "111"], 'J': ["001", "001", "001", "101", "010"],
    'K': ["101", "101", "110", "101", "101"], 'L': ["100", "100", "100", "100", "111"],
    'M': ["10001", "11011", "10101", "10001", "10001"], 'N': ["1001", "1101", "1011", "1001", "1001"],
    'O': ["010", "101", "101", "101", "010"], 'P': ["110", "101", "110", "100", "100"],
    'Q': ["010", "101", "101", "110", "011"], 'R': ["110", "101", "110", "101", "101"],
    'S': ["011", "100", "010", "001", "110"], 'T': ["111", "010", "010", "010", "010"],
    'U': ["101", "101", "101", "101", "111"], 'V': ["101", "101", "101", "101", "010"],
    'W': ["10001", "10001", "10101", "11011", "10001"], 'X': ["101", "101", "010", "101", "101"],
    'Y': ["101", "101", "010", "010", "010"], 'Z': ["111", "001", "010", "100", "111"],
    '0': ["111", "101", "101", "101", "111"], '1': ["010", "110", "010", "010", "111"],
    '2': ["110", "001", "010", "100", "111"], '3': ["110", "001", "010", "001", "110"],
    '4': ["101", "101", "111", "001", "001"], '5': ["111", "100", "110", "001", "110"],
    '6': ["011", "100", "111", "101", "111"], '7': ["111", "001", "010", "010", "010"],
    '8': ["111", "101", "111", "101", "111"], '9': ["111", "101", "111", "001", "110"],
    '-': ["000", "000", "111", "000", "000"], '_': ["000", "000", "000", "000", "111"],
    '.': ["0", "0", "0", "0", "1"], '+': ["000", "010", "111", "010", "000"],
}


def find_cinzel(explicit: str | None) -> str:
    if explicit:
        return explicit
    for pattern in ("~/.local/share/fonts/Cinzel-Bold.ttf", "/usr/share/fonts/**/Cinzel-Bold.ttf",
                    "~/.fonts/Cinzel-Bold.ttf"):
        hits = glob.glob(os.path.expanduser(pattern), recursive=True)
        if hits:
            return hits[0]
    sys.exit("Cinzel-Bold.ttf not found; pass --cinzel (Google Fonts, OFL)")


def wordmark(font_path: str, gui_h: int = 36) -> Image.Image:
    h = gui_h * TEXELS * SUPERSAMPLE
    big = ImageFont.truetype(font_path, int(h * 0.80))
    small = ImageFont.truetype(font_path, int(h * 0.80 * 0.86))  # Cinzel lowercase = small caps
    mask = Image.new("L", (h * 8, h), 0)
    draw = ImageDraw.Draw(mask)
    x, base, track = int(h * 0.12), int(h * 0.86), int(h * 0.015)
    for text, face in (("S", big), ("overeign", small), ("MC", big)):
        for ch in text:
            draw.text((x, base), ch, font=face, fill=255, anchor="ls")
            x += int(face.getlength(ch)) + track
    box = mask.getbbox()
    pad = int(h * 0.08)
    mask = mask.crop((box[0] - pad, 0, box[2] + pad * 2, h))
    w = mask.width
    unit = TEXELS * SUPERSAMPLE

    outline = mask.filter(ImageFilter.MaxFilter(2 * (unit // 2 + 1) + 1)).filter(ImageFilter.MaxFilter(5))
    shadow = ImageChops.offset(outline.filter(ImageFilter.GaussianBlur(unit * 1.2)), unit, unit)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    img.paste((10, 14, 18, 150), (0, 0), shadow)
    img.paste(SHADE + (255,), (0, 0), outline)

    top, mid, bot = (226, 238, 245), (164, 196, 214), (112, 148, 172)
    y0, y1 = mask.getbbox()[1], mask.getbbox()[3]
    grad = Image.new("RGBA", (w, h))
    gd = ImageDraw.Draw(grad)
    for y in range(h):
        t = min(max((y - y0) / max(1, y1 - y0), 0), 1)
        a, b, f = (top, mid, t / .5) if t < .5 else (mid, bot, (t - .5) / .5)
        gd.line([(0, y), (w, y)], fill=tuple(int(p + (q - p) * f) for p, q in zip(a, b)) + (255,))
    img.paste(grad, (0, 0), mask)
    bevel = ImageChops.subtract(mask, ImageChops.offset(mask, unit // 2, unit // 2))
    img.paste((245, 251, 255, 255), (0, 0), bevel.point(lambda v: v * 0.55))

    out = img.resize((w // SUPERSAMPLE, h // SUPERSAMPLE), Image.Resampling.LANCZOS)
    out = out.crop(out.getbbox())
    if out.height % TEXELS:
        canvas = Image.new("RGBA", (out.width, out.height + 1), (0, 0, 0, 0))
        canvas.paste(out, (0, 0))
        out = canvas
    return out


RULE_CELL = 5       # GUI px tall: blank, colour, shade, blank, blank (ascent 5 <= height 5)


ATLAS = 256         # the client's font atlas is 256x256: no glyph cell may be larger
JOIN = "\ue10f"     # -1 px space between the halves of a split glyph


def rule() -> Image.Image:
    """1 texel per GUI px: a flat line gains nothing from more texels."""
    w, h, fade = RULE_WIDTH, RULE_CELL, 40
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for x in range(w):
        a = min(1, x / fade, (w - 1 - x) / fade)
        px[x, 1] = RULE_COLOR + (int(255 * a),)
        px[x, 2] = SHADE + (int(150 * a),)
    return img


def split_cells(img: Image.Image, cells: int) -> Image.Image:
    """Pad to a whole number of equal cells no wider than the atlas, and pin each left
    cell's last column so its advance reaches the next cell."""
    cell_w = -(-img.width // cells)
    if cell_w > ATLAS or img.height > ATLAS:
        raise SystemExit(f"{img.size} does not fit {cells} cells of at most {ATLAS} px")
    out = Image.new("RGBA", (cell_w * cells, img.height), (0, 0, 0, 0))
    out.paste(img, (0, 0))
    for c in range(cells - 1):
        x = (c + 1) * cell_w - 1
        if all(out.getpixel((x, y))[3] == 0 for y in range(out.height)):
            out.putpixel((x, 0), (0, 0, 0, 1))
    return out


def small_font() -> tuple[Image.Image, list[str]]:
    chars = list(SMALL_GLYPHS) + [c.lower() for c in SMALL_GLYPHS if c.isalpha()]
    cols = 16
    rows = (len(chars) + cols - 1) // cols
    img = Image.new("RGBA", (cols * 5, rows * 6), (0, 0, 0, 0))  # 5 px glyph + blank row
    for i, ch in enumerate(chars):
        ox, oy = (i % cols) * 5, (i // cols) * 6
        for y, line in enumerate(SMALL_GLYPHS[ch.upper()]):
            for x, bit in enumerate(line):
                if bit == "1":
                    img.putpixel((ox + x, oy + y), (255, 255, 255, 255))
    lines = ["".join(chars[r * cols:(r + 1) * cols]).ljust(cols, "\u0000") for r in range(rows)]
    return img, lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--pack-dir", default=".")
    parser.add_argument("--cinzel", help="path to Cinzel-Bold.ttf")
    args = parser.parse_args()

    tex_dir = os.path.join(args.pack_dir, "assets/sovereignmc/textures/font/tab")
    font_dir = os.path.join(args.pack_dir, "assets/sovereignmc/font")
    os.makedirs(tex_dir, exist_ok=True)

    mark = split_cells(wordmark(find_cinzel(args.cinzel)), 2)
    mark.save(os.path.join(tex_dir, "tab_wordmark.png"), optimize=True)
    split_cells(rule(), 2).save(os.path.join(tex_dir, "tab_rule.png"), optimize=True)
    small, lines = small_font()
    small.save(os.path.join(tex_dir, "small_caps.png"), optimize=True)

    tab = {"providers": [
        {"type": "space", "advances": {JOIN: -1}},
        {"type": "bitmap", "file": "sovereignmc:font/tab/tab_rule.png",
         "chars": ["\ue100\ue102"], "ascent": RULE_CELL, "height": RULE_CELL},
        {"type": "bitmap", "file": "sovereignmc:font/tab/tab_wordmark.png",
         "chars": ["\ue101\ue103"], "ascent": 4, "height": mark.height // TEXELS},
    ]}
    tab_small = {"providers": [
        {"type": "space", "advances": {" ": 3, "[": 0, "]": 0}},
        {"type": "bitmap", "file": "sovereignmc:font/tab/small_caps.png",
         "ascent": 6, "height": 6, "chars": lines},
    ]}
    for name, data in (("tab.json", tab), ("tab_small.json", tab_small)):
        with open(os.path.join(font_dir, name), "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
    print(f"wordmark {mark.width // TEXELS}x{mark.height // TEXELS} GUI px in 2 cells, "
          f"rule {RULE_WIDTH} GUI px, {sum(len(l.rstrip(chr(0))) for l in lines)} small glyphs")


if __name__ == "__main__":
    main()
