#!/usr/bin/env python3
"""
Render the art side of the in-game SovereignWiki into the pack.

Reads the live wiki content (pages.json, every page's markdown, /embed/nav.json),
downloads every referenced image and renders:

    assets/sovereignwiki/font/images.json         one bitmap provider per image variant
    assets/sovereignwiki/font/icons.json          one bitmap provider per nav icon
    assets/sovereignwiki/font/heading.json        2x vanilla font for headings
    assets/sovereignwiki/textures/font/wiki/img/<sha1-12>_<variant>.png
    assets/sovereignwiki/textures/font/wiki/icon/<sha1-12>.png
    assets/sovereignwiki/index.json               what the plugin reads (also a release asset)
    tools/wiki-art/allocations.json               append-only codepoint allocation

Output is deterministic: with no change on the wiki a re-run rewrites nothing, which is
what lets the hourly workflow commit only when something changed.

Example:
    python3 tools/wiki-art/generate.py --pack-root .
"""

from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import cairosvg
from PIL import Image, ImageOps

DEFAULT_BASE = "https://wiki-content.sovereignmc.net"
USER_AGENT = "SovereignMC-wiki-art/1 (+https://github.com/SovereignMC/ResourcePack)"
NS = "sovereignwiki"

VARIANTS = {"wide": 424, "narrow": 296}  # max GUI width per variant
MAX_HEIGHT = 540  # GUI px (60 rows)
# Extra variants, generated only for images that occur inside a table cell.
TABLE_VARIANTS = {"w128": 128, "w96": 96, "w64": 64}
TABLE_MAX_HEIGHT = 192
ROW_GUI = 9  # one codepoint = one 9px line
MAX_CHUNK_GUI = 128  # client font pages are 256x256 texels: a glyph cell must fit, so OVERSAMPLE*cw <= 256 (always true at 1x or 2x)
MAX_CELL_TEXELS = 256
CHUNK_GAP = -1  # the plugin joins chunks with a -1 px tinsel:spacing gap
OVERSAMPLE = 1  # texels per GUI px; all GUI-space values are independent of it
ROW_TEXELS = ROW_GUI * OVERSAMPLE

IMAGE_CP_START = 0xF0000
IMAGE_CP_END = 0xFFFFD
ICON_CP_START = 0x100000
ICON_CP_END = 0x10FFFD

ICON_CELL = 16
ICON_STROKE = 1.8  # same as the site's sidebar (Sidebar.astro)

TOOL_DIR = Path(__file__).resolve().parent
CACHE_DIR = TOOL_DIR / ".cache"

IMG_MD_RE = re.compile(r'!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+(?:"[^"]*"|\'[^\']*\'))?\s*\)')
IMG_HTML_RE = re.compile(r'<img\b[^>]*?\bsrc\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', re.I | re.S)


class Source:
    """Fetches wiki content from the live site or from an offline mirror directory."""

    def __init__(self, base: str, offline_dir: Path | None):
        self.base = base.rstrip("/")
        self.offline = offline_dir

    def get(self, path: str, cache: bool = False) -> bytes:
        if self.offline is not None:
            return (self.offline / path.lstrip("/")).read_bytes()
        url = self.base + path
        cache_file = CACHE_DIR / hashlib.sha1(url.encode()).hexdigest()
        if cache and cache_file.is_file():
            return cache_file.read_bytes()
        last: Exception | None = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = resp.read()
                if cache:
                    CACHE_DIR.mkdir(parents=True, exist_ok=True)
                    cache_file.write_bytes(data)
                return data
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (400, 401, 403, 404, 410):
                    break
            except Exception as e:  # network hiccup
                last = e
            time.sleep(1 + attempt)
        raise RuntimeError(f"GET {url}: {last}")


def quote_path(path: str) -> str:
    return urllib.parse.quote(urllib.parse.unquote(path), safe="/-._~")


def image_key(ref: str, page_md: str, base: str) -> str | None:
    """Resolve a markdown/html image reference to a root-relative key, or None to skip."""
    ref = html.unescape(ref).strip()
    if not ref or ref.startswith(("data:", "#")):
        return None
    joined = urllib.parse.urljoin(base + page_md, ref)
    u = urllib.parse.urlsplit(joined)
    if u.scheme not in ("http", "https"):
        return None
    if u.netloc != urllib.parse.urlsplit(base).netloc:
        return None
    if u.path.lower().endswith(".svg"):
        return None
    return u.path or None


TABLE_HTML_RE = re.compile(r"<table\b.*?</table\s*>", re.I | re.S)


def collect_refs(markdown: str) -> list[tuple[str, bool]]:
    """Image refs as (ref, inside_table). Tables: raw HTML <table> spans and GFM rows (lines starting with '|')."""
    spans = [m.span() for m in TABLE_HTML_RE.finditer(markdown)]
    pos = 0
    for line in markdown.splitlines(keepends=True):
        if line.lstrip().startswith("|"):
            spans.append((pos, pos + len(line)))
        pos += len(line)

    def in_table(i: int) -> bool:
        return any(a <= i < b for a, b in spans)

    refs = [(m.group(1), in_table(m.start())) for m in IMG_MD_RE.finditer(markdown)]
    refs += [(m.group(1) or m.group(2), in_table(m.start())) for m in IMG_HTML_RE.finditer(markdown)]
    return refs


# ---------------------------------------------------------------- textures

def png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True, compress_level=9)
    return buf.getvalue()


def quantize_keep_alpha(rgba: Image.Image) -> Image.Image:
    """Palette image with an RGBA palette; the last entry (index len-1) is reserved
    for the advance marker (rgb 0, alpha 1)."""
    if rgba.getchannel("A").getextrema()[0] == 255:
        q = rgba.convert("RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT,
                                         dither=Image.Dither.FLOYDSTEINBERG)
        pal = q.getpalette("RGB") or []
        entries = [(pal[i], pal[i + 1], pal[i + 2], 255) for i in range(0, len(pal), 3)]
    else:
        q = rgba.quantize(colors=255, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
        pal = q.getpalette("RGBA") or []
        entries = [tuple(pal[i:i + 4]) for i in range(0, len(pal), 4)]
    used = q.getextrema()[1] + 1
    entries = entries[:used]
    marker = len(entries)
    entries.append((0, 0, 0, 1))
    flat = [c for e in entries for c in e]
    q.putpalette(flat, rawmode="RGBA")
    q.info.pop("transparency", None)
    return q, marker


def force_advance_markers(p: Image.Image, marker: int, cell_w: int, cell_h: int, rows: int, cols: int) -> None:
    """Make the rightmost texel column of every chunk cell non-transparent."""
    rgba_a = p.convert("RGBA").getchannel("A")
    for r in range(rows):
        y0 = r * cell_h
        for c in range(cols):
            x = (c + 1) * cell_w - 1
            col = rgba_a.crop((x, y0, x + 1, y0 + cell_h))
            if col.getextrema()[1] == 0:
                p.putpixel((x, y0 + cell_h - 1), marker)


def build_variant(src: Image.Image, max_w: int, max_h: int = MAX_HEIGHT) -> dict:
    """Returns png, width (n*cw, padded), height (true), rows, chunks, chunk width."""
    sw, sh = src.size
    s = min(1.0, max_w / sw, max_h / sh)
    gw = max(1, min(max_w, round(sw * s)))
    gh = max(1, min(max_h, round(sh * s)))
    rows = math.ceil(gh / ROW_GUI)
    tw, th = gw * OVERSAMPLE, gh * OVERSAMPLE
    scaled = src.resize((tw, th), Image.Resampling.LANCZOS)
    n = math.ceil(gw / MAX_CHUNK_GUI)
    cw = math.ceil(gw / n)
    sheet = Image.new("RGBA", (n * cw * OVERSAMPLE, rows * ROW_TEXELS), (0, 0, 0, 0))
    sheet.paste(scaled, (0, 0))
    q, marker = quantize_keep_alpha(sheet)
    force_advance_markers(q, marker, cw * OVERSAMPLE, ROW_TEXELS, rows, n)
    return {"png": png_bytes(q), "width": n * cw, "height": gh, "rows": rows, "chunks": n, "cw": cw}


def load_image(data: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(data))
    im.seek(0)
    im = ImageOps.exif_transpose(im)
    return im.convert("RGBA")


def render_icon(d: str) -> bytes:
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{ICON_CELL}" '
        f'height="{ICON_CELL}" fill="none" stroke="#ffffff" stroke-width="{ICON_STROKE}" '
        f'stroke-linecap="round" stroke-linejoin="round"><path d="{html.escape(d, quote=True)}"/></svg>'
    )
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=ICON_CELL, output_height=ICON_CELL)
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    # keep white, vary only alpha, so the plugin can tint with text colour
    a = im.getchannel("A")
    out = Image.new("RGBA", im.size, (255, 255, 255, 0))
    out.putalpha(a)
    if a.crop((ICON_CELL - 1, 0, ICON_CELL, ICON_CELL)).getextrema()[1] == 0:
        out.putpixel((ICON_CELL - 1, ICON_CELL - 1), (255, 255, 255, 1))
    return png_bytes(out)


# ---------------------------------------------------------------- allocation

class Allocations:
    def __init__(self, path: Path):
        self.path = path
        data = json.loads(path.read_text("utf-8")) if path.is_file() else {}
        self.map: dict[str, int] = dict(data.get("allocations", {}))
        nxt = data.get("next", {})
        self.next_image = max(int(nxt.get("image", IMAGE_CP_START)), IMAGE_CP_START)
        self.next_icon = max(int(nxt.get("icon", ICON_CP_START)), ICON_CP_START)

    def get(self, key: str, icon: bool = False) -> int:
        if key in self.map:
            return self.map[key]
        if icon:
            cp = self.next_icon
            if cp > ICON_CP_END:
                raise RuntimeError("icon codepoint range exhausted")
            self.next_icon += 1
        else:
            cp = self.next_image
            if cp > IMAGE_CP_END:
                raise RuntimeError("image codepoint range exhausted")
            self.next_image += 1
        self.map[key] = cp
        return cp

    def dumps(self) -> bytes:
        data = {
            "v": 1,
            "next": {"image": self.next_image, "icon": self.next_icon},
            "allocations": dict(sorted(self.map.items())),
        }
        return (json.dumps(data, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


# ---------------------------------------------------------------- output

class Writer:
    def __init__(self):
        self.changed = False

    def write(self, path: Path, data: bytes) -> None:
        if path.is_file() and path.read_bytes() == data:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.changed = True

    def prune(self, directory: Path, keep: set[str]) -> int:
        n = 0
        if directory.is_dir():
            for f in sorted(directory.iterdir()):
                if f.is_file() and f.name not in keep:
                    f.unlink()
                    n += 1
                    self.changed = True
        return n


def dump_json(obj, indent: int | None = 2) -> bytes:
    return (json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=False) + "\n").encode("utf-8")


def self_check(root: Path, index: dict) -> None:
    """Re-reads the written pack files and fails the run if the client would mis-render them."""
    ns_dir = root / "assets" / NS
    seen: dict[str, str] = {}
    errors: list[str] = []
    for name in ("images", "icons", "heading"):
        for p in json.loads((ns_dir / "font" / f"{name}.json").read_text("utf-8"))["providers"]:
            if p["type"] != "bitmap" or not p["file"].startswith(f"{NS}:"):
                continue  # vanilla ascii.png: 8x8 cells
            if p["ascent"] > p["height"]:
                errors.append(f"{p['file']}: ascent > height")
            tex = Image.open(root / "assets" / NS / "textures" / p["file"].split(":", 1)[1]).convert("RGBA")
            rows, cols = len(p["chars"]), len(p["chars"][0])
            cw, ch = tex.width / cols, tex.height / rows
            if cw != int(cw) or ch != int(ch) or cw > MAX_CELL_TEXELS or ch > MAX_CELL_TEXELS:
                errors.append(f"{p['file']}: cell {cw}x{ch} texels does not fit a {MAX_CELL_TEXELS}px font page")
                continue
            cw, ch = int(cw), int(ch)
            alpha = tex.getchannel("A")
            for r, row in enumerate(p["chars"]):
                if len(row) != cols:
                    errors.append(f"{p['file']}: ragged row {r}")
                for c, cp in enumerate(row):
                    if cp in seen:
                        errors.append(f"codepoint U+{ord(cp):X} in {p['file']} and {seen[cp]}")
                    seen[cp] = p["file"]
                    cell = alpha.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))
                    bb = cell.point(lambda a: 255 if a else 0).getbbox()
                    adv = int(0.5 + (bb[2] if bb else 0) * (p["height"] / ch)) + 1
                    exp = cw // OVERSAMPLE + 1 if "/img/" in p["file"] else 9
                    if adv != exp:
                        errors.append(f"{p['file']}: cell r{r}c{c} advance {adv} != {exp}")
    for key, img in index["images"].items():
        for vn, v in img["variants"].items():
            n = v["chunks"]
            if v["chunkGap"] != -1 or v["advance"] != v["width"] + 1 or len(v["rows"][0]) != n:
                errors.append(f"{key}:{vn}: bad index entry")
            for row in v["rows"]:
                if len(row) != n or any(c not in seen for c in row):
                    errors.append(f"{key}:{vn}: row codepoints missing from providers")
            # row advance = n * (cw + 1) - (n - 1) = n*cw + 1
            if v["width"] % n or n * (v["width"] // n + 1) + (n - 1) * CHUNK_GAP != v["advance"]:
                errors.append(f"{key}:{vn}: row advance mismatch")
    for d, v in index["icons"].items():
        if v["char"] not in seen:
            errors.append(f"icon {d}: not in a provider")
    if errors:
        for e in errors[:30]:
            print("self-check: " + e, file=sys.stderr)
        raise SystemExit(f"self-check failed ({len(errors)} errors)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content-base", default=DEFAULT_BASE)
    ap.add_argument("--pack-root", default=".")
    ap.add_argument("--offline-dir", default=None,
                    help="read content from a local mirror of the site instead of the network")
    args = ap.parse_args()

    root = Path(args.pack_root).resolve()
    base = args.content_base.rstrip("/")
    src = Source(base, Path(args.offline_dir) if args.offline_dir else None)
    ns_dir = root / "assets" / NS
    img_dir = ns_dir / "textures" / "font" / "wiki" / "img"
    icon_dir = ns_dir / "textures" / "font" / "wiki" / "icon"
    alloc = Allocations(TOOL_DIR / "allocations.json")
    out = Writer()

    # ---- content
    pages = json.loads(src.get("/pages.json"))["pages"]
    nav = json.loads(src.get("/embed/nav.json"))
    refs: dict[str, None] = {}
    table_keys: set[str] = set()
    page_fail = 0
    for p in pages:
        try:
            md = src.get(p["md"]).decode("utf-8", "replace")
        except Exception as e:
            page_fail += 1
            print(f"warn: page markdown unavailable: {p['md']}: {e}", file=sys.stderr)
            continue
        for ref, in_tbl in collect_refs(md):
            key = image_key(ref, p["md"], base)
            if key:
                refs[key] = None
                if in_tbl:
                    table_keys.add(key)
    keys = sorted(refs)

    # ---- images
    images: dict[str, dict] = {}
    missing: list[str] = []
    sha_variants: dict[str, dict[str, dict]] = {}  # sha1 -> variant -> info
    key_sha: dict[str, str] = {}
    table_shas: set[str] = set()
    decoded: dict[str, Image.Image] = {}
    total_bytes = 0
    keep_img: set[str] = set()
    for key in keys:
        try:
            data = src.get(quote_path(key), cache=True)
            sha = hashlib.sha1(data).hexdigest()
            if sha not in sha_variants:
                im = load_image(data)
                variants = {}
                for vname, max_w in VARIANTS.items():
                    variants[vname] = build_variant(im, max_w)
                sha_variants[sha] = variants
                decoded[sha] = im
            if key in table_keys and sha not in table_shas:
                table_shas.add(sha)
                if sha not in decoded:
                    decoded[sha] = load_image(data)
                for vname, max_w in TABLE_VARIANTS.items():
                    sha_variants[sha][vname] = build_variant(decoded[sha], max_w, TABLE_MAX_HEIGHT)
            key_sha[key] = sha
        except Exception as e:
            print(f"warn: image failed: {key}: {e}", file=sys.stderr)
            missing.append(key)

    providers = []
    for sha in sorted(sha_variants):
        for vname in [*VARIANTS, *(TABLE_VARIANTS if sha in table_shas else ())]:
            v = sha_variants[sha][vname]
            fname = f"{sha[:12]}_{vname}.png"
            keep_img.add(fname)
            out.write(img_dir / fname, v["png"])
            total_bytes += len(v["png"])
            v["chars"] = [
                "".join(chr(alloc.get(f"{sha}:{vname}:{r}:{c}")) for c in range(v["chunks"]))
                for r in range(v["rows"])
            ]
            providers.append({
                "type": "bitmap",
                "file": f"{NS}:font/wiki/img/{fname}",
                "height": ROW_GUI,
                "ascent": 7,
                "chars": v["chars"],
            })
    for key in keys:
        if key in key_sha:
            sha = key_sha[key]
            images[key] = {
                "sha1": sha,
                "variants": {
                    vn: {"font": f"{NS}:images", "width": v["width"], "height": v["height"],
                         "advance": v["width"] + 1, "chunks": v["chunks"],
                         "chunkGap": CHUNK_GAP, "rows": v["chars"]}
                    for vn, v in sha_variants[sha].items()
                    if vn in VARIANTS or key in table_keys
                },
            }
    out.write(ns_dir / "font" / "images.json", dump_json({"providers": providers}))
    out.prune(img_dir, keep_img)

    # ---- icons
    icon_paths = sorted({i["icon"] for i in nav.get("items", []) if isinstance(i.get("icon"), str) and i["icon"]})
    icons: dict[str, dict] = {}
    icon_providers = []
    keep_icon: set[str] = set()
    for d in icon_paths:
        h = hashlib.sha1(d.encode("utf-8")).hexdigest()
        fname = f"{h[:12]}.png"
        png = render_icon(d)
        keep_icon.add(fname)
        out.write(icon_dir / fname, png)
        total_bytes += len(png)
        ch = chr(alloc.get(f"icon:{h}", icon=True))
        icon_providers.append({
            "type": "bitmap",
            "file": f"{NS}:font/wiki/icon/{fname}",
            "height": 8,
            "ascent": 7,
            "chars": [ch],
        })
        icons[d] = {"font": f"{NS}:icons", "char": ch, "advance": 9}
    out.write(ns_dir / "font" / "icons.json", dump_json({"providers": icon_providers}))
    out.prune(icon_dir, keep_icon)

    # ---- heading (2x vanilla)
    ascii_cfg = json.loads((TOOL_DIR / "ascii_chars.json").read_text("utf-8"))
    heading = {"providers": [
        {"type": "space", "advances": {" ": 6}},
        {"type": "bitmap", "file": ascii_cfg["file"], "height": 12, "ascent": 4, "chars": ascii_cfg["chars"]},
    ]}
    out.write(ns_dir / "font" / "heading.json", dump_json(heading))

    out.write(TOOL_DIR / "allocations.json", alloc.dumps())

    # ---- index (generatedAt only moves when something else changed)
    index_path = ns_dir / "index.json"
    index = {
        "v": 2,
        "generatedAt": None,
        "source": f"{base}/pages.json",
        "images": images,
        "icons": icons,
        "heading": {"font": f"{NS}:heading", "scale": 1.5, "height": 12, "ascent": 4, "spaceAdvance": 6},
        "missing": sorted(missing),
    }
    prev_stamp = None
    if index_path.is_file():
        try:
            old = json.loads(index_path.read_text("utf-8"))
            prev_stamp = old.get("generatedAt")
            old_cmp = dict(old, generatedAt=None)
            if old_cmp != index:
                out.changed = True
        except ValueError:
            out.changed = True
    else:
        out.changed = True
    index["generatedAt"] = (
        prev_stamp if (prev_stamp and not out.changed)
        else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    out.write(index_path, dump_json(index, indent=1 if False else 2))

    self_check(root, index)

    print(f"pages: {len(pages)} (markdown failed: {page_fail})")
    print(f"images: {len(images)} refs ok, {len(missing)} missing, {len(sha_variants)} unique sources")
    print(f"icons: {len(icons)}")
    print(f"texture bytes: {total_bytes} ({total_bytes / 1048576:.2f} MiB)")
    used_cps = sum(len(r) for p in providers + icon_providers for r in p["chars"])
    print(f"codepoints: {used_cps} in use, {len(alloc.map)} allocated")
    if total_bytes > 8 * 1048576:
        print("warn: texture total exceeds the ~8 MB budget", file=sys.stderr)
    print("changed: " + ("yes" if out.changed else "no"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
