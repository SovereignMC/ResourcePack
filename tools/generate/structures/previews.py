#!/usr/bin/env python3
"""Generate the `sovereignmc:structure_preview` font from the structure bbmodels.

    python3 tools/generate/structures/previews.py [--pack-dir .]

Reads tools/generate/structures/styles.json, renders every bbmodels/<model_prefix><family>.bbmodel with
render.py (running animation at t=0 when the model has one, else the rest pose) and writes

  assets/sovereignmc/textures/font/structure_preview/*.png   montage + hero strips (<= 72 px tall)
  assets/sovereignmc/font/structure_preview.json             bitmap providers (ascent 7)
  tools/generate/structures/preview_manifest.json            glyph manifest read by StructuresRevamped

Missing models are skipped with a warning (empty montage cell, empty hero list). Output is
deterministic; the generated files are committed (like the gui_skins font). Never edit them by hand.
Codepoints: montage strips U+E000 + style*8 + strip; hero strips U+E100 + (style*families + family)*2 + strip
(reserved even while a model is missing, so adding a model later never renumbers other glyphs).
"""
import argparse
import io
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render  # noqa: E402

FONT_ID = "sovereignmc:structure_preview"
STRIP_MAX = 72
CELL = 60
COLS, ROWS = 6, 3
HERO = 144
VIEW = "iso_ne"
MONTAGE_BASE = 0xE000
HERO_BASE = 0xE100
MONTAGE_SSAA = 4
HERO_SSAA = 3
MARGIN = 0.04


def log(msg):
    print("previews.py: " + msg, file=sys.stderr)


def pose_faces(model):
    name = "running" if "running" in model.animations else None
    return model.faces(name, 0.0)


def cut(img, height_max=STRIP_MAX):
    strips, y = [], 0
    while y < img.height:
        h = min(height_max, img.height - y)
        strips.append((y, h, img.crop((0, y, img.width, y + h))))
        y += h
    return strips


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack-dir", default=render.PACK_ROOT)
    ap.add_argument("--check", action="store_true",
                    help="write nothing; exit 1 if the committed outputs differ from what would be generated")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.pack_dir)
    with open(os.path.join(HERE, "styles.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    styles, families = cfg["styles"], cfg["families"]
    if len(families) > COLS * ROWS:
        raise SystemExit("more families than montage cells")

    tex_dir = os.path.join(root, "assets", "sovereignmc", "textures", "font", "structure_preview")
    outputs = {}

    manifest = {"font": FONT_ID, "strip_height": STRIP_MAX, "styles": [s["id"] for s in styles],
                "families": list(families),
                "montage": {"width": COLS * CELL, "height": ROWS * CELL,
                            "cells": [{"family": fam, "x": (i % COLS) * CELL, "y": (i // COLS) * CELL,
                                       "w": CELL, "h": CELL} for i, fam in enumerate(families)],
                            "strips": {}},
                "hero": {"width": HERO, "height": HERO, "strips": {}}}
    providers = []

    for si, style in enumerate(styles):
        sid = style["id"]
        manifest["montage"]["strips"][sid] = []
        manifest["hero"]["strips"][sid] = {fam: [] for fam in families}
        models = {}
        for fam in families:
            path = os.path.join(root, "bbmodels", style["model_prefix"] + fam + ".bbmodel")
            if not os.path.isfile(path):
                log("warning: missing model %s (style %s): cell left empty" % (os.path.relpath(path, root), sid))
                continue
            m = render.Model.load(path)
            models[fam] = (m, pose_faces(m))
        # montage: one scale for every family of the style so sizes are comparable
        scale = None
        for fam, (m, fs) in models.items():
            s, _ = render.fit(m.points(faces=fs), [VIEW], CELL, MARGIN)
            scale = s if scale is None else min(scale, s)
        montage = Image.new("RGBA", (COLS * CELL, ROWS * CELL), (0, 0, 0, 0))
        for i, fam in enumerate(families):
            if fam not in models:
                continue
            m, fs = models[fam]
            _, cs = render.fit(m.points(faces=fs), [VIEW], CELL, MARGIN)
            im = render.render(m, VIEW, CELL, scale=scale, centre=cs[VIEW], ssaa=MONTAGE_SSAA, faces=fs)
            montage.alpha_composite(im, ((i % COLS) * CELL, (i // COLS) * CELL))
        for k, (y, h, img) in enumerate(cut(montage)):
            if k >= 8:
                raise SystemExit("montage needs more than 8 strips")
            code = MONTAGE_BASE + si * 8 + k
            name = "montage_%s_%d" % (sid, k)
            outputs[name + ".png"] = img
            manifest["montage"]["strips"][sid].append({"char": chr(code), "y": y, "height": h})
            providers.append((code, name, h))
        for fi, fam in enumerate(families):
            if fam not in models:
                continue
            m, fs = models[fam]
            s, cs = render.fit(m.points(faces=fs), [VIEW], HERO, MARGIN)
            hero = render.render(m, VIEW, HERO, scale=s, centre=cs[VIEW], ssaa=HERO_SSAA, faces=fs)
            for k, (y, h, img) in enumerate(cut(hero)):
                code = HERO_BASE + (si * len(families) + fi) * 2 + k
                name = "hero_%s_%s_%d" % (sid, fam, k)
                outputs[name + ".png"] = img
                manifest["hero"]["strips"][sid][fam].append({"char": chr(code), "y": y, "height": h})
                providers.append((code, name, h))

    providers.sort()
    lines = ['    {"type":"bitmap","file":"sovereignmc:font/structure_preview/%s.png","ascent":7,"height":%d,"chars":["\\u%04X"]}'
             % (name, h, code) for code, name, h in providers]
    font_text = '{\n  "providers": [\n' + ",\n".join(lines) + "\n  ]\n}\n"
    manifest_text = json.dumps(manifest, indent=2) + "\n"
    blobs = {}
    for fn, img in outputs.items():
        buf = io.BytesIO()
        img.save(buf, "PNG", optimize=False, compress_level=9)
        blobs[fn] = buf.getvalue()
    font_path = os.path.join(root, "assets", "sovereignmc", "font", "structure_preview.json")
    man_path = os.path.join(HERE, "preview_manifest.json")

    def read(path, mode="rb"):
        try:
            with open(path, mode) as f:
                return f.read()
        except OSError:
            return None
    if a.check:
        bad = []
        for fn, data in blobs.items():
            if read(os.path.join(tex_dir, fn)) != data:
                bad.append(fn)
        for fn in os.listdir(tex_dir) if os.path.isdir(tex_dir) else []:
            if fn.endswith(".png") and fn not in blobs:
                bad.append(fn + " (stale)")
        if read(font_path) != font_text.encode("utf-8"):
            bad.append("structure_preview.json")
        if read(man_path) != manifest_text.encode("utf-8"):
            bad.append("preview_manifest.json")
        if bad:
            log("OUT OF DATE: " + ", ".join(bad[:12]) + (" ..." if len(bad) > 12 else ""))
            sys.exit(1)
        log("up to date")
        return
    os.makedirs(tex_dir, exist_ok=True)
    for fn in os.listdir(tex_dir):  # drop stale strips of removed models
        if fn.endswith(".png") and fn not in blobs:
            os.remove(os.path.join(tex_dir, fn))
    for fn, data in blobs.items():
        with open(os.path.join(tex_dir, fn), "wb") as f:
            f.write(data)
    with open(font_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(font_text)
    with open(man_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(manifest_text)
    log("wrote %d PNGs, %d font providers" % (len(outputs), len(providers)))


if __name__ == "__main__":
    main()
