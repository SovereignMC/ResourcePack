# Rendering text components offline

`tools/render_text.py` draws a Minecraft text component the way the 1.21.11 client
will, so layout mistakes (wrapped lines, clipped glyphs, wrong advances) show up on
disk instead of in game. Fonts resolve pack-first, exactly like the resource stack:
anything under `assets/<namespace>/font/` in this pack wins, the rest falls back to
the client jar.

## Requirements

- `python3` with Pillow.
- A Minecraft **client jar** for the published font pages (`minecraft:default`).
  Grab the URL from `https://launchermeta.mojang.com/mc/game/version_manifest_v2.json`
  -> your version -> `downloads.client.url`. Point at it with `--client-jar`, or set
  `MC_CLIENT_JAR`, or drop it where auto-detection looks (`~/.minecraft/versions/*/`,
  Prism instances). An unpacked `assets/` tree also works via `--assets-dir`.

```bash
python3 tools/render_text.py --client-jar ~/client-1.21.11.jar --self-test
```

`--self-test` asserts the ported metrics (line pitch 9, ascent 7, `A`=6, `I`=4,
bold +1, space 4, pack slice 97/7/96×9, `tinsel:spacing` steps, wrap counts).
It must print `0 failure(s)`; if not, the client's metrics changed and every render
below is suspect.

## Feeding it a component

| input | example |
|---|---|
| SNBT as typed in a command | `--snbt '{text:"hi",color:"#FFC24D"}'` |
| JSON component | `--component '{"text":"hi","extra":[{"text":"!"}]}'` |
| JSON array of components | `--component '[{"text":"a"},{"text":"\n"},{"text":"b"}]'` |
| file: component, array, body or whole dialog | `--json dialog.json` |
| nothing | renders `tools/generate_menu_background.py`'s banner |

Dialog and body shapes are unwrapped automatically: `{"body":{"contents":…,"width":…}}`
and `{"contents":…,"width":…}` both work, and the declared `width` becomes the wrap
width unless `--width` overrides it.

```bash
# the menu banner, at 3x
python3 tools/render_text.py --client-jar ~/client.jar

# how the translucent plate reads over the world (bright backdrop)
python3 tools/render_text.py --client-jar ~/client.jar --bg 6b8299 --zoom 3

# a styled line, no wrapping
python3 tools/render_text.py --client-jar ~/client.jar --width 0 \
  --snbt '{text:"Styled: ",color:"#8FE3FF",extra:[{text:"bold ",bold:1b},{text:"italic ",italic:1b},{text:"under ",underlined:1b},{text:"strike",strikethrough:1b}]}'
```

## Flags

| flag | default | meaning |
|---|---|---|
| `--pack-dir` | `.` | pack root; `assets/` is read from here first |
| `--width` | 310 (or the body's own) | wrap width in font px; `0` disables width wrapping but still honours `\n` |
| `--zoom` | 3 | nearest-neighbour upscale |
| `--out` | `/tmp/text_render.png` | output PNG |
| `--align` | `left` | `center` centres each line inside the width |
| `--bg` | `121216` | dialog box colour, `RRGGBB`; bright values expose translucency |
| `--client-jar` / `--assets-dir` | auto-detect | source of `minecraft:default` |
| `--self-test` | | verify the ported rules |

## Reading the output

Each line is printed with its measured width and a text preview, then any warnings:

```
line  2:  89 px  'the lazy dog and '
WARN line 2 is 89 px wide, over the declared width 80 -> the client wraps it
WARN no glyph for U+0075 in tinsel:hud_background
WARN line 0: glyph box y=-2..18 exceeds the body box 4..67 -> clipped
```

- **over the declared width** — the game splits the line; re-check your advances.
- **no glyph in `<font>`** — that codepoint has no provider in that font, so the
  client draws the missing-glyph box. Use another font for it (e.g. Latin text with a
  PUA-only font like `tinsel:hud_background` will always warn).
- **exceeds the body box** — the glyph is taller than `9 px × lines + 8`; the client
  scissors it. This is what a >9 px tall glyph in a text line looks like.

## Fonts and glyph ids in this pack

| font | glyphs |
|---|---|
| `sovereignmc:menu` | `\uE004`/`\uE006`/`\uE008` accent bars, `\uE00A` title row, `\uE00B` body row, `\uE005`/`\uE007`/`\uE009` footers |
| `sovereignmc:logo` | `\uE002` type logo, `\uE003` mark |
| `sovereignmc:spaces` | `U+CE000`…`U+D2000`, advances −8192…+8192 |
| `tinsel:spacing` | power-of-two steps: `U+E000`…`U+E00A` = +1…+1024, `U+F8FF`…`U+F8F5` = −1…−1024 |
| `tinsel:hud_background` | bar slices, `ascent 13 / height 20` |

Anything not listed is whatever the pack ships under `assets/<ns>/font/`.

## Rules the renderer ports

| rule | client source |
|---|---|
| bitmap glyph: cell = `texW/cols × texH/rows`, `scale = height/rows`, `advance = (int)(0.5 + inkWidth*scale) + 1` | `goh.a(baz)` |
| bold adds 1 px to the advance, glyph drawn twice at +1 | `fwp.a(boolean)`, `gio.d.a` boldOffset |
| text lines are a fixed 9 px band; glyph top = `lineY + 7 - ascent` | `gio` (`y + 9.0f`), `fwo.g()/h()` |
| body box = `width + 8 × lines*9 + 8`, content scissored | `gjp` padding `a = 4` |
| provider order, first match wins, `reference` includes resolved recursively | `gnr.a(int)` |

## Limits

- `unihex`/`ttf` providers are not implemented: codepoints only unifont covers warn
  as missing and advance 6 px.
- `translate`, `score`, `selector`, `nbt` components are not evaluated — they render
  their key/raw payload and warn.
- `obfuscated` is not randomised; text renders normally.
- Italic is an approximate shear, not the client's exact transform.
- Only the text body is drawn: no dialog title, buttons, or surrounding chrome.
