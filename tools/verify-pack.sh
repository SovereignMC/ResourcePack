#!/usr/bin/env bash
# Verifies argentum pack integrity:
#   * every "parent": "argentum:..." resolves to models/<path>.json
#   * every texture ref (textures.* values) resolves to textures/<path>.png
#   * every items/*.json "model" ref resolves to models/<path>.json OR is allowlisted
#   * argentum texture refs must be category-subfoldered (no flat refs)
#   * assets/** paths must be valid resource locations
#   * warns on unreferenced PNGs
#
# Exit 0 = clean (warnings allowed); exit 1 = hard failure.
# Requires bash and jq.
# Usage: tools/verify-pack.sh

set -uo pipefail
export LC_ALL=C # ASCII ranges and byte order, like the PowerShell -cnotmatch check

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." || { echo "verify-pack: cannot cd to repo root" >&2; exit 1; }

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

# pack.mcmeta sanity
if [[ -f pack.mcmeta ]]; then
    jq empty -- pack.mcmeta 2>/dev/null || fails+=('pack.mcmeta is not valid JSON')
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
