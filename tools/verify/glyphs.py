#!/usr/bin/env python3
"""Check that every font in the pack loads in the 1.21.8 and 1.21.11 clients.

The rules are the client's own (FontManager, GlyphProviderDefinition and the provider
codecs, identical in 1.21.8 and 1.21.11). They fail in two ways:

  file dropped      the font JSON fails to parse or any provider fails its codec, and
                    FontManager.loadResourceStack discards the WHOLE file ("Unable to load
                    font"): every glyph of that font becomes a missing-glyph box.
  provider dropped  the definition parses but its resource cannot be loaded (missing or
                    unreadable texture, ttf or hex zip) and the client logs "Failed to load
                    builder ..., rejecting": that provider's glyphs become boxes.

Codec rules checked (a failure drops the whole file):
  * top level: {"providers": [...]}, each provider an object with a known "type":
    bitmap, ttf, space, unihex or reference; optional "filter" maps uniform/jp to booleans
  * bitmap: "file" identifier, "ascent" int, "height" int (default 8), "chars" a non-empty
    list of strings, first line non-empty, every line the same number of codepoints,
    ascent <= height
  * space: "advances" maps exactly one codepoint per key to a number
  * ttf: "file" identifier, "size"/"oversample" numbers, "shift" two numbers in
    [-512, 512], "skip" a string or list of strings
  * unihex: "hex_file" identifier, "size_overrides" entries with single-codepoint
    "from" < "to" and int "left"/"right"
  * reference: "id" identifier
  * identifiers: [a-z0-9_.-] namespace, [a-z0-9/_.-] path

Load rules checked (a failure drops the provider):
  * bitmap texture at assets/<ns>/textures/<path> exists and decodes; its size divides
    evenly into the chars grid (the client floors the cell size, so a remainder shifts
    every glyph); no cell is larger than the 256x256 font atlas (the glyph would render
    as a missing-glyph box even though the font loads)
  * ttf file at assets/<ns>/font/<path>; unihex zip at assets/<ns>/<path>
  * reference target is a font in the pack or a vanilla font; no reference cycles

Warnings (load, but probably not what was meant): a codepoint declared twice in one
provider (the client logs it), a codepoint defined by two bitmap providers of one font
(the first one listed wins), a float where the client reads an int.

minecraft: resources the pack does not override are vanilla. Pass --client-jar to check
them against a real client; without it, a reference to an unknown vanilla font warns.

Runs on the source tree or on the built zip (what players download, after PackSquash):

    python3 tools/verify/glyphs.py                    # source tree (repo root)
    python3 tools/verify/glyphs.py --zip /tmp/pack.zip
    python3 tools/verify/glyphs.py --client-jar ~/.minecraft/versions/1.21.11/1.21.11.jar

Exit 0 = every font loads (warnings allowed); 1 = something would not load in game.
Requires python3 and Pillow.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import zipfile

try:
    from PIL import Image
except ImportError:
    sys.exit("verify-glyphs: Pillow is required (pip install pillow)")

PROVIDER_TYPES = ("bitmap", "ttf", "space", "unihex", "reference")
FONT_OPTIONS = ("uniform", "jp")
NAMESPACE_RE = re.compile(r"^[a-z0-9_.-]+$")
PATH_RE = re.compile(r"^[a-z0-9/_.-]+$")
# Fonts the vanilla client ships, for references the pack does not define itself.
VANILLA_FONTS = {
    "minecraft:default", "minecraft:uniform", "minecraft:alt", "minecraft:illageralt",
    "minecraft:include/default", "minecraft:include/space", "minecraft:include/unifont",
}
# Font textures both target clients ship (identical lists in 1.21.8 and 1.21.11).
VANILLA_FONT_TEXTURES = {
    f"assets/minecraft/textures/font/{name}.png"
    for name in ("ascii", "accented", "nonlatin_european", "asciillager", "ascii_sga")
}
# FontTexture is 256x256: a glyph cell larger than that never gets stitched and the client
# substitutes the missing glyph (FontTexture.Node.insert returns null, FontSet falls back).
ATLAS = 256
FONT_PATH_RE = re.compile(r"^(?:(format_[^/]+)/)?assets/([^/]+)/font/(.+)\.json$")


class Source:
    """Pack files from a directory or a zip, plus optional client jars for vanilla."""

    def __init__(self, pack_dir: str | None, zip_path: str | None, jars: list[str]):
        self.pack_dir = pack_dir
        self.zip = zipfile.ZipFile(zip_path) if zip_path else None
        self.jars = [zipfile.ZipFile(j) for j in jars]
        if self.zip is not None:
            self.names = [n for n in self.zip.namelist() if not n.endswith("/")]
        else:
            self.names = []
            for root, dirs, files in os.walk(pack_dir):
                dirs[:] = [d for d in dirs if d not in (".git", "ignored", "tools", "bbmodels")]
                for name in files:
                    rel = os.path.relpath(os.path.join(root, name), pack_dir).replace(os.sep, "/")
                    self.names.append(rel)
        self.name_set = set(self.names)

    def read(self, rel: str) -> bytes:
        if self.zip is not None:
            return self.zip.read(rel)
        with open(os.path.join(self.pack_dir, rel), "rb") as handle:
            return handle.read()

    def find(self, overlay: str | None, rel: str) -> str | None:
        """Pack path for an assets/ path: the overlay's copy first, then the base pack."""
        if overlay and f"{overlay}/{rel}" in self.name_set:
            return f"{overlay}/{rel}"
        return rel if rel in self.name_set else None

    def vanilla(self, rel: str) -> bytes | None:
        for jar in self.jars:
            try:
                return jar.read(rel)
            except KeyError:
                continue
        return None


def parse_identifier(value) -> tuple[str, str] | None:
    if not isinstance(value, str):
        return None
    namespace, _, path = value.rpartition(":")
    namespace = namespace or "minecraft"
    if ":" in namespace or not NAMESPACE_RE.match(namespace) or not path or not PATH_RE.match(path):
        return None
    return namespace, path


def codepoints(text: str) -> list[int]:
    # json.loads already joins surrogate pairs, so one str element is one codepoint
    return [ord(ch) for ch in text]


class Checker:
    def __init__(self, source: Source):
        self.source = source
        self.fails: list[str] = []
        self.warns: list[str] = []
        self.fonts: dict[str, list[tuple[str, dict]]] = {}  # font id -> [(file, provider)]
        self.references: dict[str, set[str]] = {}
        self.glyph_count = 0
        self.provider_count = 0

    # ---------------------------------------------------------------- codec

    def is_int(self, where: str, value, field: str) -> bool:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        if isinstance(value, float) and not value.is_integer():
            self.warns.append(f"{where}: \"{field}\" {value} is read as int {int(value)}")
        return True

    def check_codec(self, where: str, provider) -> list[str]:
        """Errors that make the client's codec reject this provider (and the whole file)."""
        if not isinstance(provider, dict):
            return ["provider is not an object"]
        kind = provider.get("type")
        if kind not in PROVIDER_TYPES:
            return [f"unknown provider type {kind!r} (expected one of {', '.join(PROVIDER_TYPES)})"]
        errors: list[str] = []
        if "filter" in provider:
            flt = provider["filter"]
            if not isinstance(flt, dict) or any(k not in FONT_OPTIONS or not isinstance(v, bool)
                                                for k, v in flt.items()):
                errors.append(f"\"filter\" must map {'/'.join(FONT_OPTIONS)} to true/false")

        def ident(field: str, required: bool = True):
            if field not in provider:
                if required:
                    errors.append(f"missing \"{field}\"")
                return None
            parsed = parse_identifier(provider[field])
            if parsed is None:
                errors.append(f"\"{field}\" {provider[field]!r} is not a valid identifier")
            return parsed

        def number(field: str):
            if field in provider and (isinstance(provider[field], bool)
                                      or not isinstance(provider[field], (int, float))):
                errors.append(f"\"{field}\" must be a number")

        if kind == "bitmap":
            ident("file")
            height = provider.get("height", 8)
            if not self.is_int(where, height, "height"):
                errors.append("\"height\" must be an int")
                height = None
            if "ascent" not in provider:
                errors.append("missing \"ascent\"")
                ascent = None
            elif not self.is_int(where, provider["ascent"], "ascent"):
                errors.append("\"ascent\" must be an int")
                ascent = None
            else:
                ascent = provider["ascent"]
            chars = provider.get("chars")
            if not isinstance(chars, list) or not all(isinstance(line, str) for line in chars):
                errors.append("\"chars\" must be a list of strings")
            elif not chars or not chars[0]:
                errors.append("Expected to find data in codepoint grid")
            else:
                width = len(codepoints(chars[0]))
                for i, line in enumerate(chars[1:], 1):
                    if len(codepoints(line)) != width:
                        errors.append(f"chars line {i} has {len(codepoints(line))} codepoints, "
                                      f"line 0 has {width}; pad with \\u0000")
                        break
            if ascent is not None and height is not None and int(ascent) > int(height):
                errors.append(f"ascent {ascent} is higher than height {height}")
        elif kind == "space":
            advances = provider.get("advances")
            if not isinstance(advances, dict):
                errors.append("\"advances\" must be an object")
            else:
                for key, value in advances.items():
                    if len(key) != 1:
                        errors.append(f"advances key {key!r} must be exactly one codepoint")
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        errors.append(f"advances[{key!r}] must be a number")
        elif kind == "ttf":
            ident("file")
            number("size")
            number("oversample")
            if "shift" in provider:
                shift = provider["shift"]
                if (not isinstance(shift, list) or len(shift) != 2
                        or any(isinstance(v, bool) or not isinstance(v, (int, float))
                               or not -512 <= v <= 512 for v in shift)):
                    errors.append("\"shift\" must be two numbers in [-512, 512]")
            if "skip" in provider:
                skip = provider["skip"]
                if not isinstance(skip, str) and not (
                        isinstance(skip, list) and all(isinstance(s, str) for s in skip)):
                    errors.append("\"skip\" must be a string or a list of strings")
        elif kind == "unihex":
            ident("hex_file")
            for i, entry in enumerate(provider.get("size_overrides", [])):
                ok = (isinstance(entry, dict)
                      and all(isinstance(entry.get(k), str) and len(entry[k]) == 1 for k in ("from", "to"))
                      and all(self.is_int(where, entry.get(k), k) for k in ("left", "right")))
                if not ok:
                    errors.append(f"size_overrides[{i}] needs one-codepoint from/to and int left/right")
                elif ord(entry["from"]) >= ord(entry["to"]):
                    errors.append(f"size_overrides[{i}]: invalid range, from must be below to")
        elif kind == "reference":
            ident("id")
        return errors

    # ----------------------------------------------------------------- load

    def check_load(self, where: str, overlay: str | None, provider: dict) -> None:
        kind = provider["type"]
        if kind == "bitmap":
            namespace, path = parse_identifier(provider["file"])
            rel = f"assets/{namespace}/textures/{path}"
            found = self.source.find(overlay, rel)
            data = self.source.read(found) if found else None
            if data is None and namespace == "minecraft":
                data = self.source.vanilla(rel)
                if data is None and not self.source.jars and rel in VANILLA_FONT_TEXTURES:
                    return
                if data is None and not self.source.jars:
                    self.warns.append(f"{where}: {rel} is not in the pack; assuming vanilla")
                    return
            if data is None:
                self.fails.append(f"{where}: texture {rel} is missing")
                return
            try:
                image = Image.open(io.BytesIO(data))
                image.load()
            except Exception as exc:  # the client's NativeImage.read would throw too
                self.fails.append(f"{where}: texture {rel} does not decode ({type(exc).__name__})")
                return
            grid = [codepoints(line) for line in provider["chars"]]
            cols, rows = len(grid[0]), len(grid)
            w, h = image.size
            if w // cols == 0 or h // rows == 0:
                self.fails.append(f"{where}: {rel} is {w}x{h}, too small for a {cols}x{rows} grid")
            elif w // cols > ATLAS or h // rows > ATLAS:
                self.fails.append(f"{where}: {rel} glyph cells are {w // cols}x{h // rows}, larger than "
                                  f"the {ATLAS}x{ATLAS} font atlas; the client draws them as "
                                  f"missing-glyph boxes (split the image into more cells)")
            if w // cols and h // rows and (w % cols or h % rows):
                self.fails.append(f"{where}: {rel} is {w}x{h}, which does not divide into a "
                                  f"{cols}x{rows} grid (cells would be {w / cols:g}x{h / rows:g})")
            seen: set[int] = set()
            for line in grid:
                for cp in line:
                    if cp == 0:
                        continue
                    if cp in seen:
                        self.warns.append(f"{where}: codepoint U+{cp:04X} declared twice in one provider")
                    seen.add(cp)
            self.glyph_count += len(seen)
        elif kind == "ttf":
            namespace, path = parse_identifier(provider["file"])
            rel = f"assets/{namespace}/font/{path}"
            if not self.source.find(overlay, rel) and not (
                    namespace == "minecraft" and (self.source.vanilla(rel) or not self.source.jars)):
                self.fails.append(f"{where}: ttf file {rel} is missing")
        elif kind == "unihex":
            namespace, path = parse_identifier(provider["hex_file"])
            rel = f"assets/{namespace}/{path}"
            found = self.source.find(overlay, rel)
            data = self.source.read(found) if found else (
                self.source.vanilla(rel) if namespace == "minecraft" else None)
            if data is None:
                if not (namespace == "minecraft" and not self.source.jars):
                    self.fails.append(f"{where}: unihex file {rel} is missing")
                return
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as hexzip:
                    if not any(n.endswith(".hex") for n in hexzip.namelist()):
                        self.fails.append(f"{where}: {rel} holds no .hex file")
            except zipfile.BadZipFile:
                self.fails.append(f"{where}: {rel} is not a zip")
        elif kind == "space":
            self.glyph_count += len(provider["advances"])

    # ----------------------------------------------------------------- run

    def run(self) -> None:
        font_files = sorted(n for n in self.source.names if FONT_PATH_RE.match(n))
        for rel in font_files:
            overlay, namespace, path = FONT_PATH_RE.match(rel).groups()
            font_id = f"{namespace}:{path}"
            try:
                document = json.loads(self.source.read(rel).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.fails.append(f"{rel}: not valid JSON ({exc}) -> whole font dropped")
                continue
            providers = document.get("providers") if isinstance(document, dict) else None
            if not isinstance(providers, list):
                self.fails.append(f"{rel}: missing \"providers\" list -> whole font dropped")
                continue
            codec_errors = []
            for index, provider in enumerate(providers):
                for error in self.check_codec(f"{rel} providers[{index}]", provider):
                    codec_errors.append(f"providers[{index}]: {error}")
            if codec_errors:
                for error in codec_errors:
                    self.fails.append(f"{rel}: {error} -> whole font dropped")
                continue
            entries = self.fonts.setdefault(font_id, [])
            for index, provider in enumerate(providers):
                self.provider_count += 1
                where = f"{rel} providers[{index}]"
                self.check_load(where, overlay, provider)
                entries.append((where, provider))
                if provider["type"] == "reference":
                    target = "%s:%s" % parse_identifier(provider["id"])
                    self.references.setdefault(font_id, set()).add(target)
        self.check_references()
        self.check_shadowed()
        self.font_file_count = len(font_files)

    def check_references(self) -> None:
        for font_id, targets in sorted(self.references.items()):
            for target in sorted(targets):
                if target in self.fonts:
                    continue
                namespace, path = target.split(":", 1)
                if namespace == "minecraft" and (
                        target in VANILLA_FONTS
                        or self.source.vanilla(f"assets/minecraft/font/{path}.json")):
                    continue
                if namespace == "minecraft" and not self.source.jars:
                    self.warns.append(f"{font_id}: references {target}, not in the pack or the known "
                                      f"vanilla fonts (pass --client-jar to check)")
                else:
                    self.fails.append(f"{font_id}: references missing font {target}")
        state: dict[str, int] = {}

        def visit(node: str, trail: list[str]) -> None:
            state[node] = 1
            for nxt in sorted(self.references.get(node, ())):
                if state.get(nxt) == 1:
                    cycle = trail[trail.index(nxt):] + [nxt] if nxt in trail else [node, nxt]
                    self.fails.append(f"reference cycle: {' -> '.join(cycle)}")
                elif state.get(nxt) is None and nxt in self.references:
                    visit(nxt, trail + [nxt])
            state[node] = 2

        for node in sorted(self.references):
            if node not in state:
                visit(node, [node])

    def check_shadowed(self) -> None:
        for font_id, entries in sorted(self.fonts.items()):
            owner: dict[int, str] = {}
            for where, provider in entries:
                if provider["type"] == "bitmap":
                    cps = {cp for line in provider["chars"] for cp in codepoints(line) if cp}
                else:
                    # space and reference providers commonly pin a few codepoints ahead of
                    # a bitmap on purpose (vanilla's default font does it for U+0020)
                    continue
                for cp in sorted(cps):
                    if cp in owner and owner[cp] != where.split(" ")[0]:
                        continue  # same glyph from an overlay copy of this font file
                    if cp in owner:
                        self.warns.append(f"{font_id}: U+{cp:04X} is defined by more than one "
                                          f"provider; the first one listed wins")
                    else:
                        owner[cp] = where.split(" ")[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--pack-dir", default=None, help="pack root (default: repo root)")
    parser.add_argument("--zip", help="check a built pack zip instead of the source tree")
    parser.add_argument("--client-jar", action="append", default=[],
                        help="client jar for vanilla resources (repeatable)")
    args = parser.parse_args()
    pack_dir = args.pack_dir or os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    source = Source(None if args.zip else pack_dir, args.zip, args.client_jar)
    checker = Checker(source)
    checker.run()

    for warn in checker.warns:
        print(f"  [warn] {warn}")
    for fail in checker.fails:
        print(f"  [fail] {fail}")
    target = args.zip or pack_dir
    summary = (f"{checker.font_file_count} font files, {checker.provider_count} providers, "
               f"{checker.glyph_count} glyphs in {target}")
    if checker.fails:
        print(f"verify-glyphs: FAILED ({len(checker.fails)} failure(s), {summary})")
        sys.exit(1)
    print(f"verify-glyphs: OK ({len(checker.warns)} warning(s), {summary})")


if __name__ == "__main__":
    main()
