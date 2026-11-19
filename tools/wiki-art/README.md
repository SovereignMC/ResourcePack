# wiki-art

Renders the art for the in-game SovereignWiki (dialog-based) from the live wiki
(`https://wiki-content.sovereignmc.net`). The plugin parses the markdown itself; this tool only
produces what needs a resource pack: images, nav icons and the heading font.

## What it writes

Everything under `assets/sovereignwiki/` plus `tools/wiki-art/allocations.json`:

- `font/images.json` - one bitmap provider per image variant (`wide` <= 424 px, `narrow` <= 296 px,
  max height 540, never upscaled). Textures are 2x oversampled. Each 9 px row is split into n = ceil(W/128) column chunks (the client packs glyphs into 256x256 texel pages, so a cell must be <= 256 texels), one codepoint per chunk; the plugin joins chunks with a -1 px `tinsel:spacing` gap.
- `font/icons.json` - the nav icons (SVG path strings from `/embed/nav.json`) as white 16x16 cells.
- `font/heading.json` - 1.5x vanilla font for headings (bitmap over `minecraft:font/ascii.png`, height 12, ascent 4, so the glyph is vertically centred in a 2-line 18 px row; space = 6). A char whose vanilla advance is `a` advances `(int)(0.5 + 1.5*(a-1)) + 1`.
- `textures/font/wiki/img/<sha1-12>_<variant>.png`, `textures/font/wiki/icon/<sha1-12>.png`
- `index.json` - the schema the plugin reads; also published as the release asset `wiki-index.json`.

Every chunk cell gets a near-invisible alpha=1 texel in its last column so the glyph advance is exactly
`chunkWidth + 1` (row advance = `width + 1`, `width` = n * chunkWidth). The generator re-checks all of this and fails the run on a violation.

## Codepoints

Allocation is append-only and stored in `allocations.json`: images from U+F0000, icons from U+100000,
keyed `<sha1>:<variant>:<row>:<col>` and `icon:<sha1-of-path>`. Textures and providers of images that are
no longer referenced are removed, but their codepoints are never reused, so a pack that is one release
behind the index only lacks new images. Do not edit or reorder this file by hand.

## Running locally

```bash
pip install -r tools/wiki-art/requirements.txt   # also needs libcairo2
python3 tools/wiki-art/generate.py               # from the pack root
python3 tools/wiki-art/generate.py --offline-dir DIR   # DIR mirrors the site (pages.json, embed/nav.json, ...)
```

Downloads are cached in `tools/wiki-art/.cache/` (gitignored). A re-run with no wiki change rewrites
nothing (`generatedAt` only moves when other output changed). `.github/workflows/wiki-art.yml` runs it
hourly, commits on change and dispatches `squash-release.yml`.

`ascii_chars.json` is the vanilla `ascii.png` chars grid used by `heading.json`.
