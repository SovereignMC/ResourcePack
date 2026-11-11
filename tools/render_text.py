#!/usr/bin/env python3
"""Render any Minecraft text component exactly as the 1.21.11 client lays it out.

Fonts come from this pack first (sovereignmc:*, tinsel:*, argentum:*, ...) with
anything missing falling through to the Minecraft client jar, which is the same
resource-stack order the game uses.

The metrics are transcribed from the decompiled client jar:

  goh.a(baz)     bitmap glyph: cell = texW/cols x texH/rows, scale = height/rows,
                 ascent as declared, advance = (int)(0.5 + inkWidth*scale) + 1
  fwp.a(boolean) bold adds 1 px to the advance
  gio            a text line is a fixed 9 px band; glyph top = lineY + 7 - ascent
  gjp            body box = width + 2*4 padding, lines*9 + 2*4 padding; anything
                 outside is clipped, never scrolled

Usage:
    python3 tools/render_text.py --snbt '{text:"hi",font:"sovereignmc:menu"}'
    python3 tools/render_text.py --component '{"text":"hi","color":"#FFC24D"}'
    python3 tools/render_text.py --json dialog.json --width 310 --zoom 4
    python3 tools/render_text.py                       # the generated menu banner
    python3 tools/render_text.py --self-test
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys
import zipfile

from PIL import Image, ImageDraw

LINE_HEIGHT = 9
FONT_ASCENT = 7
BODY_PADDING = 4
VANILLA_FONT = "minecraft:default"

NAMED_COLORS = {
    "black": "#000000", "dark_blue": "#0000AA", "dark_green": "#00AA00",
    "dark_aqua": "#00AAAA", "dark_red": "#AA0000", "dark_purple": "#AA00AA",
    "gold": "#FFAA00", "gray": "#AAAAAA", "dark_gray": "#555555", "blue": "#5555FF",
    "green": "#55FF55", "aqua": "#55FFFF", "red": "#FF5555", "light_purple": "#FF55FF",
    "yellow": "#FFFF55", "white": "#FFFFFF",
}
STYLE_KEYS = ("font", "color", "bold", "italic", "underlined", "strikethrough", "obfuscated")


# --------------------------------------------------------------------------- SNBT


def parse_snbt(text: str):
    """Minimal SNBT reader: enough for component arguments pasted out of a command."""
    position = 0

    def skip():
        nonlocal position
        while position < len(text) and text[position] in " \t\n\r":
            position += 1

    def read_string():
        nonlocal position
        quote = text[position]
        position += 1
        out = []
        while position < len(text):
            ch = text[position]
            position += 1
            if ch == quote:
                return "".join(out)
            if ch == "\\" and position < len(text):
                esc = text[position]
                position += 1
                if esc == "u":
                    out.append(chr(int(text[position:position + 4], 16)))
                    position += 4
                else:
                    out.append({"n": "\n", "t": "\t", "r": "\r", "\\": "\\",
                                '"': '"', "'": "'"}.get(esc, esc))
                continue
            out.append(ch)
        raise ValueError("unterminated string")

    def read_value():
        nonlocal position
        skip()
        ch = text[position]
        if ch == "{":
            position += 1
            result = {}
            while True:
                skip()
                if text[position] == "}":
                    position += 1
                    return result
                key = read_string() if text[position] in "\"'" else read_bare(":")
                skip()
                if text[position] != ":":
                    raise ValueError(f"expected ':' at {position}")
                position += 1
                result[key] = read_value()
                skip()
                if text[position] == ",":
                    position += 1
        if ch == "[":
            position += 1
            result_list = []
            while True:
                skip()
                if text[position] == "]":
                    position += 1
                    return result_list
                result_list.append(read_value())
                skip()
                if text[position] == ",":
                    position += 1
        if ch in "\"'":
            return read_string()
        raw = read_bare(",}]")
        lowered = raw.lower()
        if lowered in ("true", "false"):
            return lowered == "true"
        if lowered.endswith("b"):
            return raw[:-1] not in ("0",)
        if lowered.endswith(("f", "d")):
            return float(raw[:-1])
        try:
            return int(raw)
        except ValueError:
            return raw

    def read_bare(stop: str):
        nonlocal position
        start = position
        while position < len(text) and text[position] not in stop:
            position += 1
        return text[start:position].strip()

    value = read_value()
    skip()
    if position != len(text):
        raise ValueError(f"trailing input at {position}")
    return value


# ------------------------------------------------------------------------ assets


class AssetSource:
    """Pack assets first, then the client jar / unpacked assets, like the game."""

    def __init__(self, pack_dir: str, client_jar: str | None, assets_dir: str | None):
        self.pack_dir = pack_dir
        self.jar = zipfile.ZipFile(client_jar) if client_jar else None
        self.assets_dir = assets_dir
        self.fonts: dict[str, FontSet] = {}

    def read(self, namespace: str, kind: str, path: str) -> bytes:
        rel = f"assets/{namespace}/{kind}/{path}"
        local = os.path.join(self.pack_dir, rel)
        if os.path.isfile(local):
            with open(local, "rb") as handle:
                return handle.read()
        if self.jar is not None:
            try:
                return self.jar.read(rel)
            except KeyError:
                pass
        if self.assets_dir:
            candidate = os.path.join(self.assets_dir, namespace, kind, path)
            if os.path.isfile(candidate):
                with open(candidate, "rb") as handle:
                    return handle.read()
        raise FileNotFoundError(rel)

    def image(self, namespace: str, path: str) -> Image.Image:
        return Image.open(io.BytesIO(self.read(namespace, "textures", path))).convert("RGBA")

    def font(self, font_id: str) -> FontSet:
        if font_id in self.fonts:
            return self.fonts[font_id]
        namespace, path = font_id.split(":", 1)
        try:
            definition = json.loads(self.read(namespace, "font", path + ".json"))
        except FileNotFoundError:
            print(f"WARN font {font_id} not found, falling back to {VANILLA_FONT}")
            font = FontSet(font_id, self.font(VANILLA_FONT).providers, font_id)
            self.fonts[font_id] = font
            return font
        font = FontSet(font_id, self._providers(namespace, definition["providers"]), font_id)
        self.fonts[font_id] = font
        return font

    def _providers(self, namespace: str, providers: list) -> list:
        out: list = []
        for provider in providers:
            kind = provider["type"]
            if kind == "reference":
                inner_ns, inner_path = provider["id"].split(":", 1)
                definition = json.loads(self.read(inner_ns, "font", inner_path + ".json"))
                out.extend(self._providers(inner_ns, definition["providers"]))
            elif kind == "space":
                out.append(SpaceProvider({ord(ch): int(adv)
                                          for ch, adv in provider["advances"].items()}))
            elif kind == "bitmap":
                file_ns, file_path = provider["file"].split(":", 1)
                rows = [[ord(ch) for ch in line] for line in provider["chars"]]
                out.append(BitmapProvider(self.image(file_ns, file_path), rows,
                                          provider["ascent"], provider.get("height", 8)))
            else:
                out.append(UnsupportedProvider(kind))
        return out


# ---------------------------------------------------------------------- metrics


class Glyph:
    def __init__(self, sprite: Image.Image | None, advance: int, ascent: int, size):
        self.sprite = sprite
        self.advance = advance
        self.ascent = ascent
        self.size = size

    def advance_for(self, bold: bool) -> int:
        return self.advance + (1 if bold else 0)


class SpaceGlyph(Glyph):
    def __init__(self, advance: int):
        super().__init__(None, advance, FONT_ASCENT, (0, 0))


def ink_width(image: Image.Image) -> int:
    alpha = image.getchannel("A")
    for x in range(image.width - 1, -1, -1):
        for y in range(image.height):
            if alpha.getpixel((x, y)):
                return x + 1
    return 0


class SpaceProvider:
    def __init__(self, advances: dict[int, int]):
        self.advances = advances

    def has(self, codepoint: int) -> bool:
        return codepoint in self.advances

    def glyph(self, codepoint: int) -> Glyph:
        return SpaceGlyph(self.advances[codepoint])


class BitmapProvider:
    def __init__(self, image: Image.Image, rows: list[list[int]], ascent: int, height: int):
        self.image = image
        cols, cell_rows = len(rows[0]), len(rows)
        self.cell_width = image.width // cols
        self.cell_height = image.height // cell_rows
        self.scale = height / self.cell_height
        self.ascent = ascent
        self.positions: dict[int, tuple[int, int]] = {}
        for y, row in enumerate(rows):
            for x, codepoint in enumerate(row):
                if codepoint:
                    self.positions.setdefault(codepoint, (x, y))

    def has(self, codepoint: int) -> bool:
        return codepoint in self.positions

    def glyph(self, codepoint: int) -> Glyph:
        col, row = self.positions[codepoint]
        cell = self.image.crop((col * self.cell_width, row * self.cell_height,
                                (col + 1) * self.cell_width, (row + 1) * self.cell_height))
        size = (round(self.cell_width * self.scale), round(self.cell_height * self.scale))
        sprite = cell.resize(size, Image.Resampling.NEAREST) if size != cell.size else cell
        return Glyph(sprite, int(0.5 + ink_width(cell) * self.scale) + 1,
                     round(self.ascent * self.scale), size)


class UnsupportedProvider:
    def __init__(self, kind: str):
        self.kind = kind

    def has(self, codepoint: int) -> bool:
        return False

    def glyph(self, codepoint: int):
        return None


class FontSet:
    def __init__(self, font_id: str, providers: list, label: str):
        self.font_id = font_id
        self.providers = providers
        self.label = label
        self._cache: dict[int, Glyph | None] = {}

    def glyph(self, codepoint: int) -> Glyph | None:
        if codepoint not in self._cache:
            found = None
            for provider in self.providers:
                if provider.has(codepoint):
                    found = provider.glyph(codepoint)
                    break
            self._cache[codepoint] = found
        return self._cache[codepoint]


# --------------------------------------------------------------------- component


def resolve_color(value) -> tuple[int, int, int]:
    if not value:
        return (255, 255, 255)
    value = NAMED_COLORS.get(value, value)
    value = str(value).lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def flatten(component, inherited: dict | None = None, warnings: list[str] | None = None):
    """Component -> [(text, style)] with parent style inheritance, like the client."""
    warnings = warnings if warnings is not None else []
    style = dict(inherited or {})
    if isinstance(component, str):
        return [{"text": component, "style": style}]
    if isinstance(component, list):
        out: list[dict] = []
        for child in component:
            out.extend(flatten(child, style, warnings))
        return out
    if not isinstance(component, dict):
        return [{"text": str(component), "style": style}]
    for key in STYLE_KEYS:
        if key in component:
            style[key] = component[key]
    pieces: list[dict] = []
    if "text" in component:
        pieces.append({"text": component["text"], "style": style})
    elif "translate" in component:
        warnings.append(f"translate key {component['translate']!r} is not resolved "
                        f"(no lang file); rendered as its key")
        pieces.append({"text": str(component["translate"]), "style": style})
    elif "keybind" in component:
        warnings.append(f"keybind {component['keybind']!r} rendered as its id")
        pieces.append({"text": str(component["keybind"]), "style": style})
    elif "selector" in component or "score" in component or "nbt" in component:
        kind = next(k for k in ("selector", "score", "nbt") if k in component)
        warnings.append(f"{kind} component needs a live world; rendered as its text")
        pieces.append({"text": str(component[kind]), "style": style})
    else:
        pieces.append({"text": "", "style": style})
    for child in component.get("extra", []):
        pieces.extend(flatten(child, style, warnings))
    return pieces


def to_chars(spans: list[dict]) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for span in spans:
        for ch in span["text"]:
            out.append((ch, span["style"]))
    return out


# ---------------------------------------------------------------------- renderer


class Renderer:
    def __init__(self, source: AssetSource):
        self.source = source
        self.warnings: list[str] = []
        self._advance_cache: dict[tuple[str, int, bool], int] = {}

    def advance(self, ch: str, style: dict) -> int:
        font_id = style.get("font", VANILLA_FONT)
        bold = bool(style.get("bold"))
        key = (font_id, ord(ch), bold)
        if key not in self._advance_cache:
            glyph = self.source.font(font_id).glyph(ord(ch))
            if glyph is None:
                self.warnings.append(f"no glyph for U+{ord(ch):04X} in {font_id}")
                return 6 + (1 if bold else 0)
            self._advance_cache[key] = glyph.advance_for(bold)
        return self._advance_cache[key]

    def wrap(self, chars: list[tuple[str, dict]], width: int | None) -> list[list[tuple[str, dict]]]:
        """Split on newlines always; greedy wrap at the last space when a width is set."""
        lines: list[list[tuple[str, dict]]] = []
        current: list[tuple[str, dict]] = []
        used = 0
        last_space = None
        for ch, style in chars:
            if ch == "\n":
                lines.append(current)
                current, used, last_space = [], 0, None
                continue
            advance = self.advance(ch, style)
            if width is not None and current and used + advance > width:
                if last_space is not None and last_space > 0:
                    lines.append(current[:last_space])
                    current = current[last_space:]
                else:
                    lines.append(current)
                    current = []
                used = sum(self.advance(c, s) for c, s in current)
                last_space = None
            current.append((ch, style))
            used += advance
            if ch == " ":
                last_space = len(current)
        if current or not lines:
            lines.append(current)
        return lines

    def render(self, component, width: int | None = 310, zoom: int = 3,
               align: str = "left", background=(18, 18, 20, 235),
               wrap: bool = True) -> Image.Image:
        spans = flatten(component, None, self.warnings)
        chars = to_chars(spans)
        lines = self.wrap(chars, width if wrap else None)
        widths = [sum(self.advance(c, s) for c, s in line) for line in lines]
        content_width = max(widths) if widths else 1
        box_width = (min(width, max(content_width, 1)) if width else content_width) \
            + BODY_PADDING * 2
        box_height = len(lines) * LINE_HEIGHT + BODY_PADDING * 2

        canvas = Image.new("RGBA", (box_width, box_height), background)
        draw = ImageDraw.Draw(canvas)

        for index, line in enumerate(lines):
            if width is not None and widths[index] > width:
                self.warnings.append(
                    f"line {index} is {widths[index]} px wide, over the declared "
                    f"width {width}")
            top = BODY_PADDING + index * LINE_HEIGHT
            pen = BODY_PADDING
            if align == "center" and width is not None:
                pen += (width - widths[index]) // 2
            for ch, style in line:
                font_id = style.get("font", VANILLA_FONT)
                glyph = self.source.font(font_id).glyph(ord(ch))
                bold = bool(style.get("bold"))
                if glyph is None:
                    pen += self.advance(ch, style)
                    continue
                color = resolve_color(style.get("color"))
                if glyph.sprite is not None:
                    sprite = _tint(glyph.sprite, color)
                    if style.get("italic"):
                        sprite = _shear(sprite)
                    y = top + FONT_ASCENT - glyph.ascent
                    if y < BODY_PADDING or y + sprite.height > box_height - BODY_PADDING:
                        self.warnings.append(
                            f"line {index}: glyph box y={y}..{y + sprite.height} exceeds "
                            f"the body box {BODY_PADDING}..{box_height - BODY_PADDING} -> clipped")
                    placed = _clip(sprite, pen, y, box_width, box_height)
                    if placed is not None:
                        canvas.alpha_composite(placed[0], placed[1])
                        if bold:
                            second = _clip(sprite, pen + 1, y, box_width, box_height)
                            if second is not None:
                                canvas.alpha_composite(second[0], second[1])
                advance = glyph.advance_for(bold)
                if style.get("underlined"):
                    draw.line([(pen, top + LINE_HEIGHT - 1),
                               (pen + advance - 1, top + LINE_HEIGHT - 1)], fill=color)
                if style.get("strikethrough"):
                    draw.line([(pen, top + LINE_HEIGHT // 2),
                               (pen + advance - 1, top + LINE_HEIGHT // 2)], fill=color)
                pen += advance
        return canvas.resize((box_width * zoom, box_height * zoom), Image.Resampling.NEAREST)


def _tint(sprite: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    if color == (255, 255, 255):
        return sprite
    out = Image.new("RGBA", sprite.size, color + (255,))
    out.putalpha(sprite.getchannel("A"))
    return out


def _shear(sprite: Image.Image, factor: float = 0.5) -> Image.Image:
    """Approximate the client's italic shear: each row shifts right towards the top."""
    width = sprite.width + int(sprite.height * factor) + 1
    out = Image.new("RGBA", (width, sprite.height))
    for y in range(sprite.height):
        offset = int((sprite.height - 1 - y) * factor)
        out.alpha_composite(sprite.crop((0, y, sprite.width, y + 1)), (offset, y))
    return out


def _clip(sprite: Image.Image, x: int, y: int, width: int, height: int):
    left, top = max(x, 0), max(y, 0)
    right, bottom = min(x + sprite.width, width), min(y + sprite.height, height)
    if left >= right or top >= bottom:
        return None
    return sprite.crop((left - x, top - y, right - x, bottom - y)), (left, top)


# -------------------------------------------------------------------------- main


def find_client_jar(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    if os.environ.get("MC_CLIENT_JAR"):
        return os.environ["MC_CLIENT_JAR"]
    patterns = [
        "~/.minecraft/versions/*/*.jar",
        "~/.local/share/PrismLauncher/instances/*/minecraft/versions/*/*.jar",
        "~/.lunarclient/offline/**/client*.jar",
    ]
    for pattern in patterns:
        for candidate in sorted(glob.glob(os.path.expanduser(pattern))):
            try:
                with zipfile.ZipFile(candidate) as jar:
                    if "assets/minecraft/font/default.json" in jar.namelist():
                        return candidate
            except zipfile.BadZipFile:
                continue
    return None


def resolve_input(document, fallback_width: int | None):
    """Accept a dialog, a dialog body, a bare component, or an array of them."""
    width = fallback_width
    node = document
    if isinstance(node, dict) and "body" in node:
        node = node["body"]
    if isinstance(node, dict) and "contents" in node:
        if node.get("width") is not None:
            width = int(node["width"])
        node = node["contents"]
    return node, width


def default_component() -> dict:
    """The menu banner from tools/generate_menu_background.py, if it is present."""
    import importlib.util
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "generate_menu_background.py")
    if not os.path.isfile(path):
        return {"text": "hello"}
    spec = importlib.util.spec_from_file_location("generate_menu_background", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.dialog()


def self_test(source: AssetSource) -> int:
    """Assert the ported rules against the values measured in game."""
    failures = []

    def check(name, got, want):
        if got != want:
            failures.append(f"{name}: got {got!r}, want {want!r}")

    vanilla = source.font(VANILLA_FONT)
    check("line height", LINE_HEIGHT, 9)
    check("vanilla ascent", FONT_ASCENT, 7)
    check("'A' advance", vanilla.glyph(ord("A")).advance, 6)
    check("'I' advance", vanilla.glyph(ord("I")).advance, 4)
    check("bold adds 1 px", vanilla.glyph(ord("A")).advance_for(True), 7)
    check("space advance", vanilla.glyph(ord(" ")).advance, 4)

    if os.path.isdir(os.path.join(source.pack_dir, "assets/sovereignmc/font")):
        menu = source.font("sovereignmc:menu")
        glyph = menu.glyph(0xE004)
        if glyph is not None:
            check("192 px slice advance", glyph.advance, 193)
            check("slice ascent", glyph.ascent, 7)
            check("slice drawn size", glyph.size, (192, 9))
        hit = menu.glyph(0xE010)
        if hit is not None:
            # Transparent per-row click target: no ink, but a full 193 px advance.
            check("hit glyph advance", hit.advance, 193)
            check("hit glyph drawn size", hit.size, (192, 9))
        field = menu.glyph(0xE00D)
        if field is not None:
            # One tall glyph carries the whole 24 row field; the client and this
            # renderer both place its top on the glyph's line.
            check("field ascent", field.ascent, 7)
            check("field drawn size", field.size, (192, 216))
            check("field advance", field.advance, 193)
        spacing = source.font("tinsel:spacing")
        check("tinsel -256", spacing.glyph(0xF8F7).advance, -256)
        check("tinsel +32", spacing.glyph(0xE005).advance, 32)

    renderer = Renderer(source)
    check("snbt parse", parse_snbt('{text:"x",bold:1b,extra:[{text:"y"}]}'),
          {"text": "x", "bold": True, "extra": [{"text": "y"}]})
    words = to_chars(flatten({"text": "aa bb cc"}))
    check("wrap at 30 px", len(renderer.wrap(words, 30)), 2)
    check("wrap at 20 px", len(renderer.wrap(words, 20)), 3)
    check("hard break without spaces", len(renderer.wrap(
        to_chars(flatten({"text": "aaaaaa"})), 13)), 3)
    check("bold in advance", renderer.advance("A", {"bold": True}), 7)

    image = renderer.render({"text": "x"}, width=100, zoom=1)
    check("single line body height", image.height, LINE_HEIGHT + BODY_PADDING * 2)

    for failure in failures:
        print("FAIL", failure)
    print(f"self-test: {len(failures)} failure(s)")
    return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", default=".")
    parser.add_argument("--json", help="file holding a JSON component or dialog")
    parser.add_argument("--component", help="inline JSON component")
    parser.add_argument("--snbt", help="inline SNBT component, as typed in a command")
    parser.add_argument("--width", type=int, default=310,
                        help="wrap width in font pixels; 0 disables wrapping")
    parser.add_argument("--out", default="/tmp/text_render.png")
    parser.add_argument("--zoom", type=int, default=3)
    parser.add_argument("--align", choices=("left", "center"), default="left")
    parser.add_argument("--bg", default="121216",
                        help="box colour RRGGBB; try a bright tone to see translucent plates")
    parser.add_argument("--client-jar", help="Minecraft client jar, for minecraft:default")
    parser.add_argument("--assets-dir", help="unpacked assets/ tree instead of a jar")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    jar = find_client_jar(args.client_jar)
    if jar is None and not args.assets_dir:
        sys.exit("no client jar found: pass --client-jar PATH or --assets-dir DIR "
                 "(the vanilla default font lives in the client jar)")
    source = AssetSource(args.pack_dir, jar, args.assets_dir)

    if args.self_test:
        sys.exit(self_test(source))

    if args.snbt:
        document = parse_snbt(args.snbt)
    elif args.component:
        document = json.loads(args.component)
    elif args.json:
        with open(args.json, encoding="utf-8") as handle:
            document = json.load(handle)
    else:
        document = default_component()

    renderer = Renderer(source)
    grey = tuple(int(args.bg[i:i + 2], 16) for i in (0, 2, 4))
    component, resolved_width = resolve_input(document, args.width)
    width = args.width if args.width else resolved_width
    width = width or None
    image = renderer.render(component, width=width, zoom=args.zoom, align=args.align,
                            background=grey + (235,), wrap=bool(width))
    image.save(args.out)

    spans = flatten(component)
    chars = to_chars(spans)
    lines = renderer.wrap(chars, width)
    for index, line in enumerate(lines):
        used = sum(renderer.advance(c, s) for c, s in line)
        text = "".join(c for c, _s in line)
        print(f"line {index:2d}: {used:3d} px  {text[:60]!r}")
    for warning in renderer.warnings:
        print("WARN", warning)
    print(f"wrote {args.out} ({image.width}x{image.height}, zoom {args.zoom}, "
          f"{len(lines)} line(s))")


if __name__ == "__main__":
    main()
