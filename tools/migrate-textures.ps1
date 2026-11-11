# One-shot migration: moves argentum texture PNGs into category subfolders and
# rewrites texture references inside assets/argentum JSONs.
#
# IMPORTANT: keep this file pure ASCII. Windows PowerShell 5.1 reads .ps1 files
# without a BOM using the ANSI codepage, where UTF-8 dashes/arrows decode to
# cp1252 curly-quote bytes that break string parsing.
#
# Idempotent: files already moved are skipped. Operates on the repo root.
# Usage: powershell -ExecutionPolicy Bypass -File tools/migrate-textures.ps1 [-DryRun]

param([switch]$DryRun, [switch]$Resume)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)  # repo root

if (-not (Test-Path ".git")) { Write-Error "Not a git repo; refusing to run."; exit 1 }
if (-not $Resume) {
    $dirty = @(git status --porcelain | Where-Object { -not $_.StartsWith('??') })
    if ($dirty.Count -gt 0) {
        Write-Error "Working tree dirty (tracked files modified); commit or stash first, or use -Resume to continue an interrupted run."
        exit 1
    }
}

# ---------------------------------------------------------------------------
# Mapping tables (doc: ArgentumRevamped/.idea/implementation.md section 1.2)
# ---------------------------------------------------------------------------

$ITEM_DELETE = @(
    'bb_brass', 'bb_crucible_gray', 'bb_gun_base_color', 'bb_gun_light_color',
    'gun_base_color', 'brass'
)

# exact item maps (checked before globs)
$ITEM_COMPONENTS = @(
    'alchemy_catalyst', 'battery', 'circuit_board_advanced', 'circuit_board_quantum',
    'ciruit_board_basic',   # misspelled file: renamed to circuit_board_basic during the move
    'copper_electrode', 'copper_wire', 'crucible_gray', 'drill_bit', 'electromagnet',
    'electronic_chip', 'graphite_electrode', 'grindstone_core', 'gun_light_color',
    'handheld_radar', 'industrial_bucket', 'magnet', 'mixing_blade',
    'portable_armour_repair_kit', 'quantum_drill_bit', 'quantum_electrode',
    'reinforced_drill_bit', 'reinforced_industrial_bucket', 'reinforced_welding_rod',
    'sawmill_blade', 'titanium_electrode', 'welding_rod'
)
$ITEM_CONSUMABLES = @(
    'carbon_chunk', 'compressed_carbon', 'condensed_lava', 'condensed_water',
    'cooling_salt', 'ender_essence_1', 'ender_essence_2', 'essence_of_life_1', 'sulfate'
)
$ITEM_UI = @('inputarrow', 'outputarrow')
$ITEM_TOOLS = @('climbing_pickaxe', 'gold_pan', 'nether_gold_pan')
$ITEM_METALLURGY_EXPLICIT = @(
    'chromium_steel', 'hardened_steel', 'nickel_alloy', 'modest_alloy', 'phosphor_bronze',
    'unrefined_gold_ore'
)
# renames: old texture name -> new texture name (inside the target category)
$ITEM_RENAME = @{ 'ciruit_board_basic' = 'circuit_board_basic' }

$BLOCK_MACHINES = @(
    'brewer_bottomtop', 'brewer_side', 'alternator', 'electric_motor', 'heater',
    'steam_turbine', 'fluid_pump', 'graphene_sheet', 'nickel_alloy', 'tungsten_carbide',
    'transformer_bottom', 'transformer_side', 'transformer_top',
    'water_tank_bottom', 'water_tank_side', 'water_tank_top'
)
$BLOCK_SUPPLY = @('supply_hopper_bottom', 'supply_hopper_side', 'elevator_block')
# Slimefun-style basic machines (flat 2D icons, used by item/generated models)
$BLOCK_BASIC_MACHINES = @(
    'enhanced_crafting_table', 'grind_stone', 'ore_crusher', 'compressor', 'smeltery',
    'pressure_chamber', 'ore_washer', 'table_saw', 'automated_panning_machine',
    'composter', 'crucible', 'block_placer', 'output_chest', 'automatic_ignition_chamber',
    'reinforced_furnace', 'carbonado_edged_furnace'
)

function Resolve-ItemCategory([string]$name) {
    if ($ITEM_DELETE -contains $name) { return '_DELETE_' }
    if ($ITEM_RENAME.ContainsValue($name)) { return 'components' }  # canonical post-rename names
    if ($name -like 'sigil_*') { return 'sigils' }
    if ($ITEM_COMPONENTS -contains $name) {
        if ($ITEM_RENAME.ContainsKey($name)) { return "components&$($ITEM_RENAME[$name])" }
        return 'components'
    }
    if ($ITEM_CONSUMABLES -contains $name) { return 'consumables' }
    if ($ITEM_UI -contains $name) { return 'ui' }
    if ($ITEM_TOOLS -contains $name) { return 'tools' }
    if ($name -like 'impure_*_dust' -or $name -like 'pure_*_dust' -or
        $name -eq 'sulfur_dust' -or $name -eq 'unrefined_gold_dust') { return 'dust' }
    if ($ITEM_METALLURGY_EXPLICIT -contains $name) { return 'metallurgy' }
    if ($name -like '*_ingot') { return 'metallurgy' }
    if ($name -like 'raw_*') { return 'metallurgy' }
    return $null
}

function Resolve-BlockCategory([string]$name) {
    if ($name -like '*_capacitor_bottom' -or $name -like '*_capacitor_side' -or
        $name -like '*_capacitor_top') { return 'capacitors' }
    if ($name -like 'output_crate_*') { return 'crates' }
    if ($BLOCK_SUPPLY -contains $name) { return 'supply' }
    if ($BLOCK_MACHINES -contains $name) { return 'machines' }
    if ($BLOCK_BASIC_MACHINES -contains $name) { return 'basic_machines' }
    if ($name -like 'enhanced_furnace_*') { return 'basic_machines' }
    return $null
}

# ---------------------------------------------------------------------------
# Pass 1 - plan texture moves (and assert total coverage)
# "components&new_name" encoding marks a rename-in-move
# ---------------------------------------------------------------------------

$plan = @()   # @{ Src; Dest; Rename }
foreach ($kind in @('item', 'block')) {
    $dir = "assets/argentum/textures/$kind"
    foreach ($png in Get-ChildItem $dir -Filter *.png -File) {
        $name = [IO.Path]::GetFileNameWithoutExtension($png.Name)
        $cat = if ($kind -eq 'item') { Resolve-ItemCategory $name } else { Resolve-BlockCategory $name }
        if ($null -eq $cat) {
            Write-Error ("UNMAPPED texture: {0}/{1} - extend the mapping tables." -f $dir, $png.Name)
            exit 1
        }
        if ($cat -eq '_DELETE_') {
            $plan += [ordered]@{ Src = $png.FullName; Dest = $null; Rename = $false }
            continue
        }
        $target = $name; $sub = $cat
        $amp = $cat.IndexOf('&')
        if ($amp -ge 0) {
            $sub = $cat.Substring(0, $amp)
            $target = $cat.Substring($amp + 1)
        }
        $dest = Join-Path (Join-Path (Split-Path $png.FullName -Parent) $sub) "$target.png"
        $plan += [ordered]@{ Src = $png.FullName; Dest = $dest; Rename = ($name -ne $target) }
    }
}

$moves   = @($plan | Where-Object { $_.Dest })
$deletes = @($plan | Where-Object { -not $_.Dest })
$renames = @($moves | Where-Object { $_.Rename })
$movesPlan   = 0 -join ''
$movesPlan   = $moves.Count
Write-Host ("Plan: {0} move(s) ({1} renamed), {2} delete(s)" -f $movesPlan, $renames.Count, $deletes.Count)
if ($DryRun) {
    foreach ($p in $plan) {
        $destName = if ($p.Dest) { [IO.Path]::GetFileName($p.Dest) } else { 'DELETE' }
        Write-Host ("  {0} -> {1}" -f (Split-Path $p.Src -Leaf), $destName)
    }
    foreach ($r in $renames) { Write-Host ("  RENAME: {0} => {1}" -f (Split-Path $r.Src -Leaf), $r.Dest) }
    Write-Host 'DryRun only - nothing touched.'
    exit 0
}

# ---------------------------------------------------------------------------
# Pass 2 - execute moves/deletes via git (history preserved)
# ---------------------------------------------------------------------------

$movedCount = 0; $deletedCount = 0
foreach ($p in $moves) {
    if (Test-Path $p.Src) {
        New-Item -ItemType Directory -Force (Split-Path $p.Dest -Parent) | Out-Null
        if (Test-Path $p.Dest) { Write-Error "Destination already exists: $($p.Dest)"; exit 1 }
        git mv $p.Src $p.Dest
        if ($LASTEXITCODE -ne 0) { Write-Error "git mv failed: $($p.Src)"; exit 1 }
        $movedCount++
    } elseif (Test-Path $p.Dest) {
        # already migrated in an earlier run
    } else {
        Write-Error "Source AND destination missing: $($p.Src)"; exit 1
    }
}
foreach ($p in $deletes) {
    if (Test-Path $p.Src) {
        git rm -q $p.Src
        if ($LASTEXITCODE -ne 0) { Write-Error "git rm failed: $($p.Src)"; exit 1 }
        $deletedCount++
    }
}
Write-Host ("Moved {0} texture(s), deleted {1} texture(s)." -f $movedCount, $deletedCount)

# ---------------------------------------------------------------------------
# Pass 3 - rewrite texture refs inside JSONs, text-preserving so Blockbench
# models with ~300-line element arrays are not reformatted. Only values inside
# the "textures" { ... } object are rewritten (texture refs by JSON semantics);
# parent/model refs and "minecraft:" refs are untouched.
# ---------------------------------------------------------------------------

function Resolve-PackRef([string]$kind, [string]$name) {
    # resolves a texture ref to its pack-relative PNG path; falls back to the other kind
    # (e.g. an item model may reference a texture that physically lives under textures/block)
    $cat = if ($kind -eq 'item') { Resolve-ItemCategory $name } else { Resolve-BlockCategory $name }
    if ($cat -eq '_DELETE_') { return '_DELETED_TEXTURE_' }
    if ($null -ne $cat) {
        $amp = $cat.IndexOf('&')
        if ($amp -ge 0) {
            return ("{0}/{1}/{2}" -f $kind, $cat.Substring(0, $amp), $cat.Substring($amp + 1))
        }
        return ("{0}/{1}/{2}" -f $kind, $cat, $name)
    }
    $otherKind = if ($kind -eq 'item') { 'block' } else { 'item' }
    $outerKindResult = if ($otherKind -eq 'item') { Resolve-ItemCategory $name } else { Resolve-BlockCategory $name }
    $otherCat = $outerKindResult
    if ($otherCat -eq '_DELETE_' -or $null -eq $otherCat) { return $null }
    $amp = $otherCat.IndexOf('&')
    if ($amp -ge 0) {
        return ("{0}/{1}/{2}" -f $otherKind, $otherCat.Substring(0, $amp), $otherCat.Substring($amp + 1))
    }
    return ("{0}/{1}/{2}" -f $otherKind, $otherCat, $name)
}

$utf8 = New-Object System.Text.UTF8Encoding($false)
$script:refsRewritten = 0
$filesChanged = 0
foreach ($json in Get-ChildItem 'assets/argentum' -Recurse -Filter *.json -File) {
    $text = [IO.File]::ReadAllText($json.FullName)
    $open = $text.IndexOf('"textures"')
    if ($open -lt 0) { continue }   # no textures object in this file
    $braceStart = $text.IndexOf('{', $open)
    if ($braceStart -lt 0) { continue }

    # find the matching closing brace, respecting string literals (\" escapes)
    $depth = 0; $inString = $false; $braceEnd = -1
    for ($i = $braceStart; $i -lt $text.Length; $i++) {
        $c = $text[$i]
        if ($inString) {
            if ($c -eq '\') { $i++ }        # skip escaped char
            elseif ($c -eq '"') { $inString = $false }
        } else {
            if ($c -eq '"') { $inString = $true }
            elseif ($c -eq '{') { $depth++ }
            elseif ($c -eq '}') {
                $depth--
                if ($depth -eq 0) { $braceEnd = $i; break }
            }
        }
    }
    if ($braceEnd -lt 0) { Write-Error "Unbalanced textures object in $($json.FullName)"; exit 1 }

    $slice = $text.Substring($braceStart, $braceEnd - $braceStart + 1)
    $newSlice = [regex]::Replace($slice, '"argentum:(item|block)/([a-z0-9_]+)"', {
        param($m)
        $resolved = Resolve-PackRef $m.Groups[1].Value $m.Groups[2].Value
        if ($resolved -eq '_DELETED_TEXTURE_') {
            Write-Error "JSON references a deleted texture: $($m.Value) in $($json.FullName)"; exit 1
        }
        if ($null -eq $resolved) {
            Write-Error "JSON reference '$($m.Value)' unmapped in $($json.FullName)"; exit 1
        }
        $newV = '"argentum:' + $resolved + '"'
        if ($newV -ne $m.Value) { $script:refsRewritten++ }
        return $newV
    })
    if ($newSlice -ne $slice) {
        $newText = $text.Remove($braceStart, $slice.Length).Insert($braceStart, $newSlice)
        [IO.File]::WriteAllText($json.FullName, $newText, $utf8)
        $filesChanged++
    }
}
Write-Host ("Rewrote {0} texture ref(s) across {1} JSON file(s)." -f $script:refsRewritten, $filesChanged)

Write-Host ''
Write-Host 'DONE. Review with git status / git diff, then run tools/verify-pack.ps1'
