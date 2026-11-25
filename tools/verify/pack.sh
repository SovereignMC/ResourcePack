#!/usr/bin/env bash
# Verifies argentum pack integrity:
#   * every "parent": "argentum:..." resolves to models/<path>.json
#   * every texture ref (textures.* values) resolves to textures/<path>.png
#   * every items/*.json "model" ref resolves to models/<path>.json OR is allowlisted
#   * argentum texture refs must be category-subfoldered (no flat refs)
#   * assets/** paths must be valid resource locations
#   * warns on unreferenced PNGs
#   * pack.mcmeta follows the 1.21.9+ format rules while still loading on 1.21.8:
#     min_format/max_format present, pack_format + supported_formats kept in step with
#     them while format 64 is supported, every overlay entry valid and its directory present
#   * every bitmap font provider has ascent <= height (else the client drops the whole font)
#
# Exit 0 = clean (warnings allowed); exit 1 = hard failure.
# Requires bash and jq.
# Usage: tools/verify/pack.sh

set -uo pipefail
export LC_ALL=C # ASCII ranges and byte order, like the PowerShell -cnotmatch check

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." || { echo "verify-pack: cannot cd to repo root" >&2; exit 1; }

if ! command -v jq >/dev/null 2>&1; then
    echo "verify-pack: jq is required (apt install jq / brew install jq)" >&2
    exit 1
fi

warns=()
fails=()
referenced=()
all_textures=()

tmpdir=$(mktemp -d) || { echo "verify-pack: cannot create temp dir" >&2; exit 1; }
trap 'rm -rf -- "$tmpdir"' EXIT

contains() {
    local needle=$1 x
    shift
    for x in "$@"; do
        [[ $x == "$needle" ]] && return 0
    done
    return 1
}

canon() {
    readlink -f -- "$1" 2>/dev/null || printf '%s\n' "$1"
}

# items defs whose model ref has no models/item/*.json today (machine items / energy work
# pending). Keep in sync with the pack.
MODEL_REF_WARNLIST=(
    'item/alternator' 'item/big_capacitor' 'item/brewer' 'item/carbonado_capacitor'
    'item/connector' 'item/electric_motor' 'item/elevator_block' 'item/energized_capacitor'
    'item/fluid_pump' 'item/heater' 'item/large_capacitor' 'item/medium_capacitor'
    'item/small_capacitor' 'item/steam_turbine' 'item/transformer' 'item/water_tank'
)

# Texture category subfolders (keep in sync with README.md). A ref into any other
# subfolder is a hard failure so new categories are added deliberately.
declare -A TEXTURE_CATEGORIES=(
    [item]='sigils metallurgy dust components consumables ui tools'
    [block]='machines basic_machines capacitors crates supply'
)

while IFS= read -r -d '' png; do
    all_textures+=("$(canon "$png")")
done < <(find assets/argentum/textures -type f -name '*.png' -print0)

# resource locations only allow [a-z0-9_.-/]; spaces/uppercase make assets unloadable
while IFS= read -r -d '' f; do
    rel=${f#assets/}
    rel=${rel//\\//}
    if [[ ! $rel =~ ^[a-z0-9_./-]+$ ]]; then
        fails+=("invalid resource location (allowed: a-z 0-9 _ . - /): assets/$rel")
    fi
done < <(find assets -type f -print0)

test_model_ref() {
    local ref=$1 file=$2
    local model_file="assets/argentum/models/$ref.json"
    if [[ ! -f $model_file ]]; then
        if contains "$ref" "${MODEL_REF_WARNLIST[@]}"; then
            warns+=("model ref not found (allowlisted): $ref in $file")
        else
            fails+=("model ref not found: $ref in $file")
        fi
    fi
}

test_texture_ref() {
    local ref=$1 file=$2
    local tex_file="assets/argentum/textures/$ref.png"
    if [[ $ref =~ ^(item|block)/[^/]+$ ]]; then
        warns+=("texture ref not in a category subfolder: argentum:$ref in $file")
    elif [[ $ref =~ ^(item|block)/([^/]+)/ ]]; then
        local kind=${BASH_REMATCH[1]} category=${BASH_REMATCH[2]}
        if ! contains "$category" ${TEXTURE_CATEGORIES[$kind]}; then
            fails+=("texture ref uses unknown category '$category': argentum:$ref in $file (add it to TEXTURE_CATEGORIES + README)")
        fi
    fi
    if [[ -f $tex_file ]]; then
        referenced+=("$(canon "$tex_file")")
    else
        fails+=("texture ref not found: argentum:$ref in $file")
    fi
}

# Emits "kind<TAB>path" for every argentum ref, mirroring the recursive walk of the
# PowerShell version: "parent"/"model" refs resolve to models, "textures.*" to textures.
read -r -d '' JQ_REFS <<'JQ'
  (.. | objects | select(has("parent")) | .parent
     | strings | select(startswith("argentum:")) | "parent\t" + .[9:]),
  (.. | objects | select((.textures? | type) == "object") | .textures[]
     | strings | select(startswith("argentum:")) | "texture\t" + .[9:]),
  (.. | objects | select((.model? | type) == "object") | .model.model
     | strings | select(startswith("argentum:")) | "model\t" + .[9:])
JQ

json_count=0
while IFS= read -r -d '' json; do
    rel=${json#./}
    if ! refs=$(jq -r "$JQ_REFS" -- "$json" 2>/dev/null); then
        fails+=("unparseable JSON: $rel")
        continue
    fi
    json_count=$((json_count + 1))
    if [[ -n $refs ]]; then
        while IFS=$'\t' read -r kind ref; do
            [[ -n $ref ]] || continue
            case $kind in
                parent | model) test_model_ref "$ref" "$rel" ;;
                texture) test_texture_ref "$ref" "$rel" ;;
            esac
        done <<<"$refs"
    fi
done < <(find assets/argentum -type f -name '*.json' -print0)

printf 'Scanned %d argentum JSON file(s), %d texture PNG(s).\n' \
    "$json_count" "${#all_textures[@]}"

# inverse check: unreferenced PNGs
printf '%s\n' "${all_textures[@]}" | sort -u >"$tmpdir/all"
printf '%s\n' "${referenced[@]}" | sort -u >"$tmpdir/referenced"
if [[ ${#all_textures[@]} -gt 0 ]]; then
    while IFS= read -r tex; do
        [[ -n $tex ]] || continue
        warns+=("texture not referenced by any JSON: ${tex#"$PWD"/}")
    done < <(comm -23 "$tmpdir/all" "$tmpdir/referenced")
fi

# fonts: the client rejects the whole font file when a bitmap provider's ascent exceeds its
# height (default 8), and every glyph of that font then renders as a missing-glyph box.
while IFS= read -r -d '' font; do
    if ! bad=$(jq -r '.providers[]? | select(.type == "bitmap")
            | select((.ascent // 0) > (.height // 8))
            | "\(.file): ascent \(.ascent) > height \(.height // 8)"' -- "$font" 2>/dev/null); then
        fails+=("font is not valid JSON: $font")
        continue
    fi
    while IFS= read -r line; do
        [[ -n $line ]] && fails+=("$font: $line")
    done <<<"$bad"
done < <(find assets format_* -path '*/font/*.json' -print0 2>/dev/null)

# pack.mcmeta: the rules of the 1.21.9+ loader (PackFormat.IntermediaryFormat.validate).
# 64 is the last resource format without minor versions (1.21.7-1.21.8): while the pack or
# any overlay reaches it, the old fields must be present and agree with the new ones.
read -r -d '' JQ_MCMETA <<'JQ'
  def major: if type == "array" then .[0] else . end;
  def lo: if type == "array" and length > 1 then [.[0], .[1]] else [major, 0] end;
  def hi: if type == "array" and length > 1 then [.[0], .[1]] else [major, 1000000000] end;
  def oldrange: if type == "array" and length == 2 then . else null end;
  def check($ctx; $min; $max; $old; $oldname; $needold):
    if ($min == null) or ($max == null) then "\($ctx): needs both min_format and max_format"
    elif ($min | lo) > ($max | hi) then "\($ctx): min_format is greater than max_format"
    elif (($min | major) <= 64) or $needold then
      if ($old | oldrange) == null then "\($ctx): \($oldname) [min, max] is required while format 64 (1.21.7-1.21.8) is supported"
      elif $old[0] != ($min | major) then "\($ctx): \($oldname) starts at \($old[0]) but min_format at \($min | major)"
      elif ($old[1] != ($max | major)) and ($old[1] != 64) then "\($ctx): \($oldname) must end at \($max | major) or 64, not \($old[1])"
      else empty end
    elif $old != null then "\($ctx): \($oldname) must be removed when only formats above 64 are supported"
    else empty end;
  (.pack // {}) as $p
  | ((.overlays.entries // []) | map(
        [(.min_format // null | if . == null then 1000000000 else major end),
         (.formats | oldrange | if . == null then 1000000000 else .[0] end)] | min
      ) | (min // 1000000000) <= 64) as $overlayneedold
  | check("pack"; $p.min_format; $p.max_format; $p.supported_formats; "supported_formats"; false),
    (if (($p.min_format // 65) | major) <= 64 then
       if ($p.pack_format | type) != "number" then "pack: pack_format is required while format 64 is supported"
       elif $p.pack_format < ($p.min_format | major) or $p.pack_format > ($p.max_format | major) then "pack: pack_format \($p.pack_format) is outside min_format..max_format"
       else empty end
     else empty end),
    ((.overlays.entries // [])[] |
       if (.directory | type) != "string" or (.directory | test("^[a-z0-9_.-]+$") | not) then "overlay \(.directory): directory must match [a-z0-9_.-]+"
       else check("overlay \(.directory)"; .min_format; .max_format; .formats; "formats"; $overlayneedold) end)
JQ

if [[ -f pack.mcmeta ]]; then
    if jq empty -- pack.mcmeta 2>/dev/null; then
        while IFS= read -r msg; do
            [[ -n $msg ]] && fails+=("pack.mcmeta $msg")
        done < <(jq -r "$JQ_MCMETA" -- pack.mcmeta 2>&1)
        while IFS= read -r dir; do
            [[ -n $dir && -d $dir/assets ]] || fails+=("pack.mcmeta overlay directory missing: $dir/assets")
        done < <(jq -r '.overlays.entries[]?.directory | strings' -- pack.mcmeta)
    else
        fails+=('pack.mcmeta is not valid JSON')
    fi
else
    fails+=('pack.mcmeta missing')
fi

if [[ ${#warns[@]} -gt 0 ]]; then
    echo
    echo "WARNINGS: ${#warns[@]}"
    for w in "${warns[@]}"; do
        echo "  [warn] $w"
    done
fi
if [[ ${#fails[@]} -gt 0 ]]; then
    echo
    echo "FAILURES: ${#fails[@]}"
    for f in "${fails[@]}"; do
        echo "  [fail] $f"
    done
    exit 1
fi
echo 'verify-pack: OK'
exit 0
