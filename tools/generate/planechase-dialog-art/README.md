# planechase-dialog-art

Pre-renders every PlaneChase bogie and rail piece as custom-font glyph art for SovereignTinsel dialogs,
using the same glyph technique as `tools/wiki-art` (see its README).

## Run

```bash
python3 tools/generate/planechase-dialog-art/generate.py                      # from the pack root
python3 tools/generate/planechase-dialog-art/generate.py --plugin-index PATH  # PlaneChase dialog-art.json
python3 tools/generate/planechase-dialog-art/generate.py --only bogie_small   # debug: PNGs only
```

Needs Python 3, Pillow and numpy. The default plugin index is
`../PlaneChase/src/main/resources/rails/dialog-art.json` relative to the pack root; `bogies.yml` is read from
the same directory (`--bogies-yml` overrides).

## Inputs

- Every bogie's BetterModel source `bbmodels/<name>.bbmodel` (`name` = the `bettermodel:` value of each size in
  `rails/bogies.yml`), id `planechase:bogie_<size>_<style>`. Unlike the item models (frame and wheels only) these
  carry the full bogie: cylinders, pistons, rods and axles. Rest pose as stored, no animation applied. Only `cube`
  elements are read (all 27 bogies are cubes only); element `rotation` is Blockbench Euler ZYX about the element
  `origin`, then the `outliner` group origins and rotations, groups or elements with `visibility` / `export` false are
  skipped, faces without a `texture` are hidden, `inflate` is honoured, face `uv` is in pixels of the texture's
  `uv_width` / `uv_height` (else `resolution`), textures are the embedded base64 PNG `source`.
- The four rail piece item models, resolved from `assets/planechase/items/rail_{straight,curve,switch,buffer}.json`.
  They are `item/generated` sprites and are drawn flat front-on at an integer texel scale.

For rails: parents, `#texture` variables, element rotation (with `rescale`), face `uv` / `rotation` are resolved; `tintindex`
is ignored. A missing texture is drawn neutral grey with a warning (vanilla textures are not needed by these models).

## Rendering

numpy z-buffer, orthographic view (yaw 225, pitch 30, the vanilla GUI angle), nearest texture sampling, alpha
cutout, per-face shading (top 1.0, north/south 0.8, east/west 0.6, bottom 0.5), 2x supersampled and
box-filtered, auto-fitted with a 1 px margin onto a transparent background.

| Variant | Display px | Rows x chunks | Texture texels |
|---|---|---|---|
| `thumb` | 96 x 54 | 6 x 1 | 192 x 108 |
| `large` | 224 x 108 | 12 x 2 | 448 x 216 |

## Outputs

- `assets/planechase/textures/font/dialog/<thumb|large>/<id path>.png`
- `assets/planechase/font/dialog_art.json`: one bitmap provider per image (height 9, ascent 7) plus a space
  provider `"": -1` that joins the chunks of a row.
- the plugin index: `{"font": "planechase:dialog_art", "images": {"<id>": {"thumb"|"large": {"width", "rows"}}}}`;
  `width` is the exact advance of each row string in px (chunks x chunk width + 1).
- `allocations.json`: append-only codepoints from U+F8000, key `<id>:<variant>:<row>:<col>`. Never edit or reorder;
  codepoints of removed images are never reused. (Separate font file, so no clash with the wiki's U+F0000 range.)

The run self-checks cells (<= 256 texels, exact advance markers), unique codepoints, equal row widths and that
every `bogies.yml` entry and all four rails are present, and fails otherwise.
