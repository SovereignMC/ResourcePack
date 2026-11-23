"""Sniper scope camera overlay. Run: python3 tools/generate/guns/scope_overlay.py

Writes assets/sovereignmc/textures/misc/sniper_scope.png (1280x720), used as the
`minecraft:equippable` camera_overlay "sovereignmc:misc/sniper_scope". The client stretches it over
the whole screen ignoring the aspect ratio, so it is drawn for 16:9: opaque black outside a round
(on a 16:9 screen) view of diameter 92 % of the height, a soft dark vignette ring just inside the
edge, and a thin black mil-dot reticle (alpha 255, everything else inside the circle transparent).
Deterministic: supersampled 4x, then box-downscaled.
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets" / "sovereignmc" / "textures" / "misc" / "sniper_scope.png"
W, H = 1280, 720
SS = 4
DIAMETER = 0.92 * H
VIGNETTE = 14.0        # px of gradient inside the edge
BLACK = (0, 0, 0)


def build():
    w, h = W * SS, H * SS
    cx, cy = w / 2, h / 2
    r = DIAMETER / 2 * SS
    vig = VIGNETTE * SS
    # alpha mask: 255 outside the circle, vignette ramp 200 -> 0 over `vig` px inside, 0 in the view
    alpha = Image.new("L", (w, h), 255)
    ad = ImageDraw.Draw(alpha)
    steps = int(vig)
    for i in range(steps):
        rr = r - i
        a = int(round(200 * (1 - i / steps) ** 2))
        ad.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=a)
    ad.ellipse((cx - (r - vig), cy - (r - vig), cx + (r - vig), cy + (r - vig)), fill=0)

    # reticle (alpha 255 lines)
    ret = ImageDraw.Draw(alpha)
    gap = 26 * SS                     # open centre
    thin = 1.0 * SS                   # fine crosshair line half... full width in px
    post = 5.0 * SS                   # thick posts toward the edges
    post_start = r * 0.62
    reach = r - vig * 0.4
    for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        # fine line from the gap to the post, thick post to the vignette
        for a0, a1, wd in ((gap, post_start, thin), (post_start, reach, post)):
            x0, y0 = cx + sx * a0, cy + sy * a0
            x1, y1 = cx + sx * a1, cy + sy * a1
            half = wd / 2
            ret.rectangle((min(x0, x1) - (half if sy else 0), min(y0, y1) - (half if sx else 0),
                           max(x0, x1) + (half if sy else 0), max(y0, y1) + (half if sx else 0)), fill=255)
    # mil dots every 40 px along both axes between the gap and the posts, plus a centre dot
    dot = 3.2 * SS
    for k in range(1, 8):
        d = (gap + 14 * SS) + k * 40 * SS
        if d > post_start - 20 * SS:
            break
        for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = cx + sx * d, cy + sy * d
            ret.ellipse((x - dot / 2, y - dot / 2, x + dot / 2, y + dot / 2), fill=255)
    cd = 2.2 * SS
    ret.ellipse((cx - cd, cy - cd, cx + cd, cy + cd), fill=255)

    alpha = alpha.resize((W, H), Image.BOX)
    img = Image.new("LA", (W, H), (0, 255))
    img.putalpha(alpha)
    return img


def main():
    img = build()
    # palette-friendly: black everywhere, only alpha varies
    pal = img.getchannel("A").point(lambda v: v)
    out = Image.merge("RGBA", (Image.new("L", (W, H), 0),) * 3 + (pal,))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
