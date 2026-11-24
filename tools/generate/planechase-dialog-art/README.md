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

- Every `item:` model of `rails/bogies.yml` (`models/item/bogie/<size>/<style>/item.json`, the frame with
  wheels merged), id `planechase:bogie_<size>_<style>`.
- The four rail piece item models, resolved from `assets/planechase/items/rail_{straight,curve,switch,buffer}.json`.
  They are `item/generated` sprites and are drawn flat front-on at an integer texel scale.

Parents, `#texture` variables, element rotation (with `rescale`), face `uv` / `rotation` are resolved; `tintindex`
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
