#!/usr/bin/env bash
# Generate Minecraft resource-pack assets from bbmodels/*.bbmodel using BetterModel.
#
# BetterModel has no standalone converter: it generates its pack from the models
# directory while the plugin is enabled. So this script boots a throwaway Paper
# server with the real BetterModel jar, lets it import every model and write its
# resource pack, then copies the generated namespace into assets/.
#
#   tools/generate/bettermodel/generate.sh
#   BETTERMODEL_VERSION=3.7.0 PAPER_VERSION=26.3 tools/generate/bettermodel/generate.sh
#
# Output: assets/<BETTERMODEL_NAMESPACE>/ (default assets/bettermodel/).
# The output is generated, not committed; the release workflow regenerates it.
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
models_dir="$root/bbmodels"
namespace="${BETTERMODEL_NAMESPACE:-bettermodel}"
bm_version="${BETTERMODEL_VERSION:-3.7.0}"
paper_version="${PAPER_VERSION:-1.21.8}"
java_bin="${JAVA_BIN:-java}"
work_dir="${BETTERMODEL_WORK_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/bettermodel.XXXXXX")}"
keep_work="${BETTERMODEL_KEEP_WORK:-0}"
timeout_seconds="${BETTERMODEL_TIMEOUT:-300}"

log() { printf '[bettermodel] %s\n' "$*"; }
die() { printf '[bettermodel] ERROR: %s\n' "$*" >&2; exit 1; }

cleanup() {
    if [[ "$keep_work" != "1" ]]; then
        rm -rf "$work_dir"
    else
        log "kept work directory: $work_dir"
    fi
}
trap cleanup EXIT

[[ -d "$models_dir" ]] || die "missing models directory: $models_dir"
shopt -s nullglob
models=("$models_dir"/*.bbmodel "$models_dir"/*.ajmodel)
shopt -u nullglob
if (( ${#models[@]} == 0 )); then
    log "no .bbmodel files in bbmodels/, nothing to generate"
    rm -rf "$root/assets/$namespace"
    exit 0
fi
log "found ${#models[@]} model(s) in ${models_dir#"$root"/}"

if ! command -v "$java_bin" >/dev/null 2>&1; then
    die "Java not found ($java_bin). Paper ${paper_version}+ needs Java 25 or newer."
fi
java_major="$("$java_bin" -version 2>&1 | sed -n 's/.*version "\([0-9][0-9]*\).*/\1/p' | head -n 1)"
if [[ -n "$java_major" ]] && (( java_major < 25 )); then
    die "Java ${java_major} found, but Paper ${paper_version} needs Java 25 or newer. Set JAVA_BIN=/path/to/java25."
fi

server="$work_dir/server"
mkdir -p "$server/plugins/BetterModel/models"

cp "${models[@]}" "$server/plugins/BetterModel/models/"

# Player-limb models (first-person viewmodels) live in bbmodels/players/ and are
# loaded by BetterModel's player animation module from plugins/BetterModel/players/.
mkdir -p "$server/plugins/BetterModel/players"
shopt -s nullglob
player_models=("$models_dir"/players/*.bbmodel)
shopt -u nullglob
if (( ${#player_models[@]} > 0 )); then
    cp "${player_models[@]}" "$server/plugins/BetterModel/players/"
    log "found ${#player_models[@]} player model(s) in bbmodels/players"
fi

log "downloading Paper ${paper_version}"
paper_url="$(python3 - "$paper_version" <<'PY'
import json, sys, urllib.request

version = sys.argv[1]
url = f"https://fill.papermc.io/v3/projects/paper/versions/{version}/builds"
with urllib.request.urlopen(url, timeout=60) as response:
    builds = json.load(response)
for build in builds:
    download = build.get("downloads", {}).get("server:default")
    if build.get("channel") == "STABLE" and download:
        print(download["url"])
        break
else:
    raise SystemExit(f"no stable Paper build with a server download for {version}")
PY
)" || die "could not resolve a Paper ${paper_version} build"

curl -fsSL --retry 3 -o "$server/paper.jar" "$paper_url" \
    || die "failed to download Paper"

log "downloading BetterModel ${bm_version}"
bm_url="https://github.com/toxicity188/BetterModel/releases/download/${bm_version}/bettermodel-${bm_version}-paper.jar"
if ! curl -fsSL --retry 3 -o "$server/plugins/BetterModel.jar" "$bm_url"; then
    # v2 releases use a capitalised asset name.
    bm_url="https://github.com/toxicity188/BetterModel/releases/download/${bm_version}/BetterModel-${bm_version}-paper.jar"
    curl -fsSL --retry 3 -o "$server/plugins/BetterModel.jar" "$bm_url" \
        || die "failed to download BetterModel ${bm_version}"
fi

printf 'eula=true\n' > "$server/eula.txt"
cat > "$server/server.properties" <<'EOF'
online-mode=false
server-port=25599
enable-query=false
enable-rcon=false
max-players=1
view-distance=2
simulation-distance=2
spawn-protection=0
generate-structures=false
level-type=minecraft:flat
motd=BetterModel asset generation
EOF

cat > "$server/plugins/BetterModel/config.yml" <<EOF
debug:
  pack: true
module:
  model: true
  player-animation: true
  player-armor: false
pack:
  use-obfuscation: false
metrics: false
version-check: false
sight-trace: false
namespace: ${namespace}
pack-type: folder
build-folder-location: BetterModel/build
merge-with-external-resources: false
EOF

log_file="$work_dir/server.log"
fifo="$work_dir/server.stdin"
mkfifo "$fifo"
# Open both ends ourselves so the server can start before we write "stop".
exec 3<>"$fifo"

log "starting Paper (generation happens during server startup)"
(
    cd "$server"
    exec "$java_bin" -Xms512M -Xmx1536M -jar paper.jar --nogui <&3
) >"$log_file" 2>&1 &
server_pid=$!

build_dir="$server/plugins/BetterModel/build"
deadline=$((SECONDS + timeout_seconds))
loaded=0
while kill -0 "$server_pid" 2>/dev/null; do
    if grep -q 'BetterModel.*Plugin is loaded' "$log_file" 2>/dev/null; then
        loaded=1
        break
    fi
    if (( SECONDS >= deadline )); then
        log "timed out after ${timeout_seconds}s waiting for BetterModel"
        break
    fi
    sleep 2
done

if (( loaded )); then
    printf 'stop\n' >&3
fi

# Give the server a moment to stop cleanly, then make sure it is gone.
for _ in {1..30}; do
    kill -0 "$server_pid" 2>/dev/null || break
    sleep 1
done
if kill -0 "$server_pid" 2>/dev/null; then
    kill "$server_pid" 2>/dev/null || true
fi
wait "$server_pid" 2>/dev/null || true
exec 3>&-

if (( ! loaded )); then
    tail -n 80 "$log_file" >&2 || true
    die "BetterModel did not finish loading; see the server log above"
fi
[[ -f "$build_dir/pack.mcmeta" ]] || die "BetterModel produced no pack metadata in $build_dir"
[[ -d "$build_dir/assets/$namespace" ]] || die "BetterModel produced no assets/$namespace directory"

dest="$root/assets/$namespace"
rm -rf "$dest"
cp -a "$build_dir/assets/$namespace" "$dest"

# Player limb models are named by mixed-case hashes, which are not valid resource locations.
python3 "$(dirname -- "${BASH_SOURCE[0]}")/fix_names.py" "$namespace" --pack-dir "$root"

count="$(find "$dest" -type f | wc -l | tr -d ' ')"
log "wrote $count file(s) to assets/$namespace/"
