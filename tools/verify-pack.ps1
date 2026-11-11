# Verifies argentum pack integrity:
#   * every "parent": "argentum:..." resolves to models/<path>.json
#   * every texture ref (textures.* values) resolves to textures/<path>.png
#   * every items/*.json "model" ref resolves to models/<path>.json OR is allowlisted
#   * argentum texture refs must be category-subfoldered (no flat refs)
#   * warns on unreferenced PNGs
#
# Exit 0 = clean (warnings allowed); exit 1 = hard failure.
# Usage: powershell -ExecutionPolicy Bypass -File tools/verify-pack.ps1

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)  # repo root

$warn = New-Object System.Collections.Generic.List[string]
$fail = New-Object System.Collections.Generic.List[string]
$referencedTextures = New-Object System.Collections.Generic.List[string]
$allTextures = New-Object System.Collections.Generic.List[string]

# items defs whose model ref has no models/item/*.json today (machine items / energy work
# pending). Keep in sync with the pack.
$MODEL_REF_WARNLIST = @(
    'item/alternator', 'item/big_capacitor', 'item/brewer', 'item/carbonado_capacitor',
    'item/connector', 'item/electric_motor', 'item/elevator_block', 'item/energized_capacitor',
    'item/fluid_pump', 'item/heater', 'item/large_capacitor', 'item/medium_capacitor',
    'item/small_capacitor', 'item/steam_turbine', 'item/transformer', 'item/water_tank'
)

# Texture category subfolders (keep in sync with README.md). A ref into any other
# subfolder is a hard failure so new categories are added deliberately.
$TEXTURE_CATEGORIES = @{
    'item'  = @('sigils', 'metallurgy', 'dust', 'components', 'consumables', 'ui', 'tools')
    'block' = @('machines', 'basic_machines', 'capacitors', 'crates', 'supply')
}

foreach ($png in Get-ChildItem 'assets/argentum/textures' -Recurse -Filter *.png -File) {
    $allTextures.Add($png.FullName)
}

# resource locations only allow [a-z0-9_.-/]; spaces/uppercase make assets unloadable
$assetsRoot = (Resolve-Path 'assets').Path
foreach ($f in Get-ChildItem 'assets' -Recurse -File) {
    $relAsset = $f.FullName.Substring($assetsRoot.Length + 1).Replace([char]92, [char]47)
    if ($relAsset -cnotmatch '^[a-z0-9_.\-/]+$') {
        $fail.Add("invalid resource location (allowed: a-z 0-9 _ . - /): assets/$relAsset")
    }
}

function Test-ModelRef([string]$refPath, [string]$file) {
    $modelFile = Join-Path 'assets/argentum' ("models/" + $refPath + ".json")
    if (-not (Test-Path $modelFile)) {
        if ($MODEL_REF_WARNLIST -contains $refPath) {
            $warn.Add("model ref not found (allowlisted): $refPath in $file")
        } else {
            $fail.Add("model ref not found: $refPath in $file")
        }
    }
}

function Test-TextureRef([string]$refPath, [string]$file) {
    $texFile = Join-Path 'assets/argentum' ("textures/" + $refPath + ".png")
    if ($refPath -match '^(item|block)/[^/]+$') {
        $warn.Add("texture ref not in a category subfolder: argentum:$refPath in $file")
    } elseif ($refPath -match '^(item|block)/([^/]+)/') {
        if ($TEXTURE_CATEGORIES[$Matches[1]] -notcontains $Matches[2]) {
            $fail.Add("texture ref uses unknown category '$($Matches[2])': argentum:$refPath in $file (add it to TEXTURE_CATEGORIES + README)")
        }
    }
    if (Test-Path $texFile) {
        $referencedTextures.Add((Resolve-Path $texFile).Path)
    } else {
        $fail.Add("texture ref not found: argentum:$refPath in $file")
    }
}

function Walk-Json($node, [string]$file) {
    if ($node -is [PSCustomObject]) {
        $parent = $node.PSObject.Properties['parent']
        if ($parent -and ($parent.Value -is [string])) {
            $v = [string]$parent.Value
            if ($v -match '^argentum:(.+)$') { Test-ModelRef $Matches[1] $file }
        }
        $tex = $node.PSObject.Properties['textures']
        if ($tex -and $tex.Value -is [PSCustomObject]) {
            foreach ($prop in $tex.Value.PSObject.Properties) {
                $v = [string]$prop.Value
                if ($v -match '^argentum:(.+)') { Test-TextureRef $Matches[1] $file }
            }
        }
        $mdl = $node.PSObject.Properties['model']
        if ($mdl -and ($mdl.Value -is [PSCustomObject])) {
            $ref = $mdl.Value.PSObject.Properties['model']
            if ($ref -and ($ref.Value -is [string])) {
                $v = [string]$ref.Value
                if ($v -match '^argentum:(.+)') { Test-ModelRef $Matches[1] $file }
            }
        }
        foreach ($prop in $node.PSObject.Properties) {
            if ($prop.Name -in @('parent', 'textures', 'model')) { continue }
            Walk-Json $prop.Value $file
        }
    } elseif ($node -is [System.Collections.IEnumerable] -and $node -isnot [string]) {
        foreach ($e in $node) { Walk-Json $e $file }
    }
}

$jsonCount = 0
foreach ($json in Get-ChildItem 'assets/argentum' -Recurse -Filter *.json -File) {
    $root = (Get-Location).Path
    $rel = $json.FullName.Substring($root.Length + 1)
    try { $doc = ConvertFrom-Json -InputObject ([IO.File]::ReadAllText($json.FullName)) -ErrorAction Stop }
    catch { $fail.Add("unparseable JSON: $rel"); continue }
    $jsonCount++
    Walk-Json $doc $rel
}

Write-Host ("Scanned {0} argentum JSON file(s), {1} texture PNG(s)." -f $jsonCount, $allTextures.Count)

# inverse check: unreferenced PNGs
$referencedSet = New-Object 'System.Collections.Generic.HashSet[string]'
foreach ($r in $referencedTextures) { [void]$referencedSet.Add($r) }
foreach ($t in $allTextures) {
    if (-not $referencedSet.Contains($t)) {
        $warn.Add("texture not referenced by any JSON: $t")
    }
}

# pack.mcmeta sanity
if (Test-Path 'pack.mcmeta') {
    try { ConvertFrom-Json -InputObject ([IO.File]::ReadAllText('pack.mcmeta')) | Out-Null }
    catch { $fail.Add('pack.mcmeta is not valid JSON') }
} else {
    $fail.Add('pack.mcmeta missing')
}

if ($warn.Count -gt 0) {
    Write-Host ''
    Write-Host ('WARNINGS: ' + $warn.Count)
    $warn | ForEach-Object { Write-Host ("  [warn] " + $_) }
}
if ($fail.Count -gt 0) {
    Write-Host ''
    Write-Host ('FAILURES: ' + $fail.Count)
    $fail | ForEach-Object { Write-Host ("  [fail] " + $_) }
    exit 1
}
Write-Host 'verify-pack: OK'
exit 0
