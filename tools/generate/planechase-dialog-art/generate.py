#!/usr/bin/env python3
"""
Pre-renders every PlaneChase bogie and rail piece as custom-font glyph art for SovereignTinsel dialogs.

Reads the bogie bbmodels (bettermodel names in PlaneChase rails/bogies.yml) and the four rail piece item models,
renders each with a small numpy z-buffer rasteriser (orthographic 3/4 view, nearest texture sampling,
alpha cutout, Minecraft-style face shading) and writes:

    assets/planechase/textures/font/dialog/<thumb|large>/<id path>.png
    assets/planechase/font/dialog_art.json
    <plugin index>   (PlaneChase rails/dialog-art.json)
    tools/generate/planechase-dialog-art/allocations.json   append-only codepoint allocation

Glyph conventions follow tools/wiki-art: 9 px rows split into column chunks of at most 128 px (256 texels),
2x oversampled textures, an alpha=1 texel in the last column of every chunk cell so the advance is exact,
height 9 / ascent 7, chunks joined by a -1 px space glyph.

Example:
    python3 tools/generate/planechase-dialog-art/generate.py --pack-root .
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

TOOL_DIR = Path(__file__).resolve().parent
NS = "planechase"
FONT_NAME = "dialog_art"

VARIANTS = {"thumb": (96, 54), "large": (224, 108)}
ROW_GUI = 9
MAX_CHUNK_GUI = 128
MAX_CELL_TEXELS = 256
OVERSAMPLE = 2
ROW_TEXELS = ROW_GUI * OVERSAMPLE
SSAA = 2
MARGIN_GUI = 1
CP_START = 0xF8000
CP_END = 0xFFFFD
JOINER = ""
RAILS = ["rail_straight", "rail_curve", "rail_switch", "rail_buffer"]
SIZES = ("small", "large", "extra_large")

YAW = math.radians(225.0)
PITCH = math.radians(30.0)

FACES = {
    "north": ((0, 0, -1), (-1, 0, 0), (0, -1, 0)),
    "south": ((0, 0, 1), (1, 0, 0), (0, -1, 0)),
    "east": ((1, 0, 0), (0, 0, -1), (0, -1, 0)),
    "west": ((-1, 0, 0), (0, 0, 1), (0, -1, 0)),
    "up": ((0, 1, 0), (1, 0, 0), (0, 0, 1)),
    "down": ((0, -1, 0), (1, 0, 0), (0, 0, -1)),
}

WARNED: set[str] = set()


def warn(msg: str) -> None:
    if msg not in WARNED:
        WARNED.add(msg)
        print("warn: " + msg, file=sys.stderr)


class Assets:
    def __init__(self, root: Path):
        self.root = root
        self.textures: dict[str, np.ndarray | None] = {}
        self.models: dict[str, dict | None] = {}

    def texture(self, ref: str) -> np.ndarray | None:
        ns, _, path = ref.rpartition(":")
        key = f"{ns or 'minecraft'}:{path}"
        if key not in self.textures:
            f = self.root / "assets" / (ns or "minecraft") / "textures" / f"{path}.png"
            if f.is_file():
                im = Image.open(f).convert("RGBA")
                if im.height > im.width and im.height % im.width == 0:
                    im = im.crop((0, 0, im.width, im.width))
                self.textures[key] = np.asarray(im, dtype=np.uint8)
            else:
                warn(f"missing texture {key}, using neutral grey")
                self.textures[key] = None
        return self.textures[key]

    def model(self, ref: str) -> dict | None:
        ns, _, path = ref.rpartition(":")
        key = f"{ns or 'minecraft'}:{path}"
        if key not in self.models:
            f = self.root / "assets" / (ns or "minecraft") / "models" / f"{path}.json"
            self.models[key] = json.loads(f.read_text("utf-8")) if f.is_file() else None
        return self.models[key]

    def bbmodel(self, name: str) -> dict:
        f = self.root / "bbmodels" / f"{name}.bbmodel"
        if not f.is_file():
            raise SystemExit(f"bbmodel not found: {f}")
        return json.loads(f.read_text("utf-8"))

    def resolve(self, ref: str) -> tuple[list[dict], dict[str, str], bool]:
        """Elements, merged textures and whether the chain ends in item/generated."""
        textures: dict[str, str] = {}
        elements: list[dict] | None = None
        generated = False
        cur: str | None = ref
        for _ in range(16):
            if cur is None:
                break
            if cur.rpartition(":")[2] in ("item/generated", "builtin/generated"):
                generated = True
                break
            m = self.model(cur)
            if m is None:
                warn(f"model not found: {cur}")
                break
            for k, v in m.get("textures", {}).items():
                textures.setdefault(k, v)
            if elements is None and "elements" in m:
                elements = m["elements"]
            cur = m.get("parent")
        return elements or [], textures, generated


def resolve_tex(textures: dict[str, str], ref: str) -> str | None:
    for _ in range(16):
        if not ref.startswith("#"):
            return ref or None
        nxt = textures.get(ref[1:])
        if nxt is None:
            return None
        ref = nxt
    return None


def rot_matrix(axis: str, angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


class Quad:
    """A parallelogram face: corner at texture (0,0), edge vectors along texture u and v."""

    __slots__ = ("origin", "du", "dv", "normal", "uv", "rot", "tex", "shade")

    def __init__(self, origin, du, dv, normal, uv, rot, tex):
        self.origin, self.du, self.dv, self.normal = origin, du, dv, normal
        self.uv, self.rot, self.tex = uv, rot, tex
        self.shade = 1.0


def default_uv(fname: str, f: np.ndarray, t: np.ndarray) -> tuple[float, float, float, float]:
    x1, y1, z1 = f
    x2, y2, z2 = t
    return {
        "down": (x1, 16 - z2, x2, 16 - z1),
        "up": (x1, z1, x2, z2),
        "north": (16 - x2, 16 - y2, 16 - x1, 16 - y1),
        "south": (x1, 16 - y2, x2, 16 - y1),
        "west": (z1, 16 - y2, z2, 16 - y1),
        "east": (16 - z2, 16 - y2, 16 - z1, 16 - y1),
    }[fname]


def build_quads(assets: Assets, ref: str) -> tuple[list[Quad], bool]:
    elements, textures, generated = assets.resolve(ref)
    quads: list[Quad] = []
    if generated:
        tex_ref = resolve_tex(textures, "#layer0")
        if tex_ref:
            quads.append(Quad(np.array([0.0, 16.0, 8.0]), np.array([16.0, 0, 0]), np.array([0, -16.0, 0]),
                              np.array([0.0, 0, 1]), (0, 0, 16, 16), 0, tex_ref))
        return quads, True
    for el in elements:
        f = np.array(el["from"], dtype=float)
        t = np.array(el["to"], dtype=float)
        size = t - f
        center = (f + t) / 2
        mat = None
        origin = None
        r = el.get("rotation")
        if r and r.get("angle", 0):
            ang = math.radians(r["angle"])
            mat = rot_matrix(r["axis"], ang)
            if r.get("rescale"):
                k = 1.0 / math.cos(ang)
                scale = np.array([k if a != r["axis"] else 1.0 for a in "xyz"])
                mat = mat @ np.diag(scale)
            origin = np.array(r.get("origin", [8, 8, 8]), dtype=float)
        for fname, face in el.get("faces", {}).items():
            if fname not in FACES:
                continue
            tex_ref = resolve_tex(textures, face.get("texture", ""))
            if tex_ref is None:
                warn(f"unresolved texture {face.get('texture')} in {ref}")
                continue
            n, u_dir, v_dir = (np.array(a, dtype=float) for a in FACES[fname])
            du = u_dir * float(np.abs(u_dir) @ size)
            dv = v_dir * float(np.abs(v_dir) @ size)
            corner = center + n * size / 2 - du / 2 - dv / 2
            uv = face.get("uv") or default_uv(fname, f, t)
            normal = n
            if mat is not None:
                corner = origin + mat @ (corner - origin)
                du, dv = mat @ du, mat @ dv
                normal = mat @ n
                normal = normal / (np.linalg.norm(normal) or 1.0)
            quads.append(Quad(corner, du, dv, normal, tuple(uv), int(face.get("rotation", 0)) % 360, tex_ref))
    return quads, False


def euler_zyx(rot: list[float]) -> np.ndarray:
    """Blockbench Euler order ZYX: matrix Rz @ Ry @ Rx, angles in degrees."""
    x, y, z = (math.radians(a) for a in rot)
    return rot_matrix("z", z) @ rot_matrix("y", y) @ rot_matrix("x", x)


def bb_parent_chains(model: dict) -> dict[str, list[tuple[np.ndarray, np.ndarray]]]:
    """Element uuid -> (origin, matrix) of its ancestor groups, innermost first; hidden groups drop their elements."""
    groups = {g["uuid"]: g for g in model.get("groups", [])}
    chains: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {}

    def walk(node, chain: list, hidden: bool) -> None:
        if isinstance(node, str):
            chains[node] = None if hidden else list(chain)
            return
        g = {**groups.get(node.get("uuid"), {}), **node}
        hid = hidden or g.get("visibility") is False or g.get("export") is False
        entry = (np.array(g.get("origin", [0, 0, 0]), dtype=float), euler_zyx(g.get("rotation", [0, 0, 0])))
        for child in node.get("children", []):
            walk(child, [entry] + chain, hid)

    for node in model.get("outliner", []):
        walk(node, [], False)
    return chains


def build_quads_bb(assets: Assets, name: str) -> list[Quad]:
    """Rest pose of a Blockbench bbmodel: cube elements in their group hierarchy, textures embedded."""
    model = assets.bbmodel(name)
    res = model.get("resolution", {"width": 16, "height": 16})
    tex_refs: list[tuple[str, float, float]] = []
    for i, t in enumerate(model.get("textures", [])):
        ref = f"bbmodel_{name}:{i}"
        src = t.get("source", "")
        if src.startswith("data:") and ";base64," in src:
            im = Image.open(io.BytesIO(base64.b64decode(src.split(";base64,", 1)[1]))).convert("RGBA")
            assets.textures[ref] = np.asarray(im, dtype=np.uint8)
        else:
            warn(f"{name}: texture {i} has no embedded source")
            assets.textures[ref] = None
        tex_refs.append((ref, float(t.get("uv_width") or res["width"]), float(t.get("uv_height") or res["height"])))
    chains = bb_parent_chains(model)
    quads: list[Quad] = []
    for el in model["elements"]:
        if el.get("type", "cube") != "cube":
            warn(f"{name}: skipped non-cube element type {el.get('type')}")
            continue
        if el.get("export") is False or el.get("visibility") is False:
            continue
        chain = chains.get(el["uuid"], [])
        if chain is None:
            continue
        inflate = float(el.get("inflate", 0) or 0)
        f = np.array(el["from"], dtype=float) - inflate
        t = np.array(el["to"], dtype=float) + inflate
        size = t - f
        center = (f + t) / 2
        eo = np.array(el.get("origin", [0, 0, 0]), dtype=float)
        mats = [(eo, euler_zyx(el.get("rotation", [0, 0, 0])))] + chain
        for fname, face in el.get("faces", {}).items():
            tidx = face.get("texture")
            if fname not in FACES or tidx is None or tidx >= len(tex_refs):
                continue
            ref, uw, vh = tex_refs[tidx]
            n, u_dir, v_dir = (np.array(a, dtype=float) for a in FACES[fname])
            du = u_dir * float(np.abs(u_dir) @ size)
            dv = v_dir * float(np.abs(v_dir) @ size)
            corner = center + n * size / 2 - du / 2 - dv / 2
            normal = n
            for o, m in mats:
                corner = o + m @ (corner - o)
                du, dv, normal = m @ du, m @ dv, m @ normal
            uv = face.get("uv") or [0, 0, uw, vh]
            uv16 = (uv[0] * 16 / uw, uv[1] * 16 / vh, uv[2] * 16 / uw, uv[3] * 16 / vh)
            quads.append(Quad(corner, du, dv, normal, uv16, int(face.get("rotation", 0)) % 360, ref))
    return quads


def shade_of(n: np.ndarray) -> float:
    x2, y2, z2 = n[0] ** 2, n[1] ** 2, n[2] ** 2
    return float(0.6 * x2 + 0.8 * z2 + (1.0 if n[1] > 0 else 0.5) * y2)


def render(assets: Assets, ref: str, out_w: int, out_h: int) -> Image.Image:
    if ref.startswith("bbmodel:"):
        quads, flat = build_quads_bb(assets, ref.split(":", 1)[1]), False
    else:
        quads, flat = build_quads(assets, ref)
    if not quads:
        raise RuntimeError(f"{ref}: nothing to render")
    view = np.eye(3) if flat else rot_matrix("x", PITCH) @ rot_matrix("y", YAW)
    W, H = out_w * SSAA, out_h * SSAA
    margin = MARGIN_GUI * OVERSAMPLE * SSAA
    pts = []
    for q in quads:
        q.origin, q.du, q.dv = view @ q.origin, view @ q.du, view @ q.dv
        facing = q.normal if (view @ q.normal)[2] >= 0 else -q.normal
        q.shade = 1.0 if flat else shade_of(facing)
        o = q.origin
        pts += [o, o + q.du, o + q.dv, o + q.du + q.dv]
    P = np.array(pts)
    minx, maxx = P[:, 0].min(), P[:, 0].max()
    miny, maxy = P[:, 1].min(), P[:, 1].max()
    scale = min((W - 2 * margin) / max(maxx - minx, 1e-6), (H - 2 * margin) / max(maxy - miny, 1e-6))
    if flat:
        tex0 = assets.texture(quads[0].tex)
        tw = tex0.shape[1] if tex0 is not None else 16
        per_texel = max(SSAA, math.floor(scale * 16.0 / tw / SSAA) * SSAA)
        scale = per_texel * tw / 16.0
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    color = np.zeros((H, W, 3), dtype=np.float32)
    alpha = np.zeros((H, W), dtype=np.float32)
    zbuf = np.full((H, W), -np.inf, dtype=np.float32)

    for q in quads:
        o, du, dv = q.origin, q.du, q.dv
        o2 = np.array([(o[0] - cx) * scale + W / 2, H / 2 - (o[1] - cy) * scale])
        a2 = np.array([du[0] * scale, -du[1] * scale])
        b2 = np.array([dv[0] * scale, -dv[1] * scale])
        det = a2[0] * b2[1] - a2[1] * b2[0]
        if abs(det) < 1e-6:
            continue
        xs = [o2[0], o2[0] + a2[0], o2[0] + b2[0], o2[0] + a2[0] + b2[0]]
        ys = [o2[1], o2[1] + a2[1], o2[1] + b2[1], o2[1] + a2[1] + b2[1]]
        x0, x1 = max(0, int(math.floor(min(xs)))), min(W - 1, int(math.ceil(max(xs))))
        y0, y1 = max(0, int(math.floor(min(ys)))), min(H - 1, int(math.ceil(max(ys))))
        if x1 < x0 or y1 < y0:
            continue
        px, py = np.meshgrid(np.arange(x0, x1 + 1) + 0.5 - o2[0], np.arange(y0, y1 + 1) + 0.5 - o2[1])
        s = (px * b2[1] - py * b2[0]) / det
        t = (a2[0] * py - a2[1] * px) / det
        inside = (s >= 0) & (s < 1) & (t >= 0) & (t < 1)
        if not inside.any():
            continue
        z = o[2] + s * du[2] + t * dv[2]
        if q.rot == 90:
            ss, tt = t, 1 - s
        elif q.rot == 180:
            ss, tt = 1 - s, 1 - t
        elif q.rot == 270:
            ss, tt = 1 - t, s
        else:
            ss, tt = s, t
        u1, v1, u2, v2 = q.uv
        uu = (u1 + ss * (u2 - u1)) / 16.0
        vv = (v1 + tt * (v2 - v1)) / 16.0
        tex = assets.texture(q.tex)
        if tex is None:
            rgb = np.full(s.shape + (3,), 128.0, dtype=np.float32)
            a = np.ones(s.shape, dtype=bool)
        else:
            th, tw = tex.shape[:2]
            ix = np.clip(np.floor(uu * tw).astype(int), 0, tw - 1)
            iy = np.clip(np.floor(vv * th).astype(int), 0, th - 1)
            texel = tex[iy, ix]
            rgb = texel[..., :3].astype(np.float32)
            a = texel[..., 3] >= 128
        window_z = zbuf[y0:y1 + 1, x0:x1 + 1]
        write = inside & a & (z > window_z)
        if not write.any():
            continue
        window_z[write] = z[write]
        color[y0:y1 + 1, x0:x1 + 1][write] = rgb[write] * q.shade
        alpha[y0:y1 + 1, x0:x1 + 1][write] = 1.0

    premult = (color * alpha[..., None]).reshape(out_h, SSAA, out_w, SSAA, 3).mean(axis=(1, 3))
    a_out = alpha.reshape(out_h, SSAA, out_w, SSAA).mean(axis=(1, 3))
    rgb_out = premult / np.maximum(a_out[..., None], 1e-6)
    a_bin = np.where(a_out >= 0.5, 255, 0).astype(np.uint8)
    img = np.dstack([np.clip(rgb_out, 0, 255).astype(np.uint8), a_bin])
    img[a_bin == 0] = 0
    return Image.fromarray(img, "RGBA")


def build_sheet(rendered: Image.Image, gui_w: int, gui_h: int) -> tuple[Image.Image, int, int, int]:
    rows = math.ceil(gui_h / ROW_GUI)
    n = math.ceil(gui_w / MAX_CHUNK_GUI)
    cw = math.ceil(gui_w / n)
    sheet = Image.new("RGBA", (n * cw * OVERSAMPLE, rows * ROW_TEXELS), (0, 0, 0, 0))
    sheet.paste(rendered, (0, 0))
    for r in range(rows):
        for c in range(n):
            x = (c + 1) * cw * OVERSAMPLE - 1
            y0 = r * ROW_TEXELS
            col = sheet.crop((x, y0, x + 1, y0 + ROW_TEXELS)).getchannel("A")
            if col.getextrema()[1] == 0:
                sheet.putpixel((x, y0 + ROW_TEXELS - 1), (0, 0, 0, 1))
    return sheet, rows, n, cw


def read_bogies(yml: Path) -> list[tuple[str, str]]:
    """(id, "bbmodel:<bettermodel name>") for every style and size of bogies.yml."""
    out = []
    style = size = None
    in_styles = False
    for line in yml.read_text("utf-8").splitlines():
        if line.startswith("styles:"):
            in_styles = True
            continue
        if not in_styles:
            continue
        m = re.match(r"^  ([a-z0-9_]+):\s*$", line)
        if m:
            style, size = m.group(1), None
            continue
        m = re.match(r"^      ([a-z_]+):\s*$", line)
        if m and m.group(1) in SIZES:
            size = m.group(1)
            continue
        m = re.match(r"^        bettermodel:\s*(\S+)\s*$", line)
        if m and style and size:
            out.append((f"{NS}:bogie_{size}_{style}", f"bbmodel:{m.group(1)}"))
    return out


class Allocations:
    def __init__(self, path: Path):
        data = json.loads(path.read_text("utf-8")) if path.is_file() else {}
        self.map: dict[str, int] = dict(data.get("allocations", {}))
        self.next = max(int(data.get("next", CP_START)), CP_START)

    def get(self, key: str) -> int:
        if key not in self.map:
            if self.next > CP_END:
                raise RuntimeError("codepoint range exhausted")
            self.map[key] = self.next
            self.next += 1
        return self.map[key]

    def dumps(self) -> str:
        return json.dumps({"v": 1, "next": self.next, "allocations": dict(sorted(self.map.items()))},
                          indent=1, ensure_ascii=False) + "\n"


def write_if_changed(path: Path, data: bytes) -> None:
    if path.is_file() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True, compress_level=9)
    return buf.getvalue()


def self_check(root: Path, index: dict, font_path: Path, expected_ids: list[str]) -> None:
    errors: list[str] = []
    font = json.loads(font_path.read_text("utf-8"))
    seen: dict[str, str] = {}
    for p in font["providers"]:
        if p["type"] == "space":
            continue
        if p["height"] != ROW_GUI or p["ascent"] != 7:
            errors.append(f"{p['file']}: bad height/ascent")
        tex = Image.open(root / "assets" / NS / "textures" / p["file"].split(":", 1)[1]).convert("RGBA")
        rows, cols = len(p["chars"]), len(p["chars"][0])
        cw, ch = tex.width / cols, tex.height / rows
        if cw != int(cw) or ch != int(ch) or cw > MAX_CELL_TEXELS or ch > MAX_CELL_TEXELS or ch != ROW_TEXELS:
            errors.append(f"{p['file']}: cell {cw}x{ch} texels invalid")
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
                if adv != cw // 2 + 1:
                    errors.append(f"{p['file']}: cell r{r}c{c} advance {adv} != {cw // 2 + 1}")
    for rid in expected_ids:
        img = index["images"].get(rid)
        if img is None:
            errors.append(f"{rid}: missing from index")
            continue
        for vn, (gw, _) in VARIANTS.items():
            v = img.get(vn)
            if v is None:
                errors.append(f"{rid}:{vn}: missing")
                continue
            chunks = [row.split(JOINER) for row in v["rows"]]
            n = len(chunks[0])
            for row in chunks:
                if len(row) != n or any(len(c) != 1 or c not in seen for c in row):
                    errors.append(f"{rid}:{vn}: bad row codepoints")
            if v["width"] != n * math.ceil(gw / n) + 1:
                errors.append(f"{rid}:{vn}: width {v['width']} mismatch")
    for rid in index["images"]:
        if rid not in expected_ids:
            errors.append(f"{rid}: not expected")
    if errors:
        for e in errors[:40]:
            print("self-check: " + e, file=sys.stderr)
        raise SystemExit(f"self-check failed ({len(errors)} errors)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack-root", default=".")
    ap.add_argument("--plugin-index", default=None,
                    help="where to write dialog-art.json (default ../PlaneChase/src/main/resources/rails/dialog-art.json)")
    ap.add_argument("--bogies-yml", default=None, help="PlaneChase rails/bogies.yml (default next to the plugin index)")
    ap.add_argument("--only", default=None, help="render only ids containing this text (PNGs only, no index or font)")
    args = ap.parse_args()

    root = Path(args.pack_root).resolve()
    index_path = Path(args.plugin_index) if args.plugin_index else \
        root.parent / "PlaneChase" / "src" / "main" / "resources" / "rails" / "dialog-art.json"
    yml = Path(args.bogies_yml) if args.bogies_yml else index_path.parent / "bogies.yml"
    assets = Assets(root)
    alloc = Allocations(TOOL_DIR / "allocations.json")

    jobs = read_bogies(yml)
    if not jobs:
        raise SystemExit(f"no bogies read from {yml}")
    bogie_count = len(jobs)
    for r in RAILS:
        item_def = root / "assets" / NS / "items" / f"{r}.json"
        ref = f"{NS}:item/{r}"
        if item_def.is_file():
            ref = json.loads(item_def.read_text("utf-8")).get("model", {}).get("model", ref)
        jobs.append((f"{NS}:{r}", ref))
    ids = [i for i, _ in jobs]
    if len(set(ids)) != len(ids):
        raise SystemExit("duplicate ids")

    providers: list[dict] = [{"type": "space", "advances": {JOINER: -1}}]
    images: dict[str, dict] = {}
    tex_root = root / "assets" / NS / "textures" / "font" / "dialog"
    keep: dict[str, set[str]] = {v: set() for v in VARIANTS}
    for rid, ref in jobs:
        if args.only and args.only not in rid:
            continue
        path = rid.split(":", 1)[1]
        entry = {}
        for vn, (gw, gh) in VARIANTS.items():
            sheet, rows, n, cw = build_sheet(render(assets, ref, gw * OVERSAMPLE, gh * OVERSAMPLE), gw, gh)
            fname = f"{path}.png"
            keep[vn].add(fname)
            write_if_changed(tex_root / vn / fname, png_bytes(sheet))
            chars = [[chr(alloc.get(f"{rid}:{vn}:{r}:{c}")) for c in range(n)] for r in range(rows)]
            providers.append({"type": "bitmap", "file": f"{NS}:font/dialog/{vn}/{fname}",
                              "height": ROW_GUI, "ascent": 7, "chars": ["".join(r) for r in chars]})
            entry[vn] = {"width": n * cw + 1, "rows": [JOINER.join(r) for r in chars]}
        images[rid] = entry
        print(f"rendered {rid}")
    if args.only:
        return 0
    for vn in VARIANTS:
        d = tex_root / vn
        if d.is_dir():
            for f in d.iterdir():
                if f.is_file() and f.name not in keep[vn]:
                    f.unlink()

    font_path = root / "assets" / NS / "font" / f"{FONT_NAME}.json"
    write_if_changed(font_path, (json.dumps({"providers": providers}, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    index = {"font": f"{NS}:{FONT_NAME}", "images": images}
    write_if_changed(index_path, (json.dumps(index, indent=1, ensure_ascii=True) + "\n").encode("utf-8"))
    write_if_changed(TOOL_DIR / "allocations.json", alloc.dumps().encode("utf-8"))
    self_check(root, index, font_path, ids)
    print(f"ok: {len(images)} images ({bogie_count} bogies, {len(RAILS)} rails), "
          f"U+{CP_START:X}..U+{alloc.next - 1:X}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
