# Extract firmware images from a Razer "CustomerFWU2Point5" firmware updater.
# The updater is a self-extracting zip; the firmware lives in DeviceUpdater.resources:
#   - main MCU: one .NET string resource per Intel HEX line, Dev<N>FWLine<i> (multi-device updaters, e.g. the
#     Huntsman Mini) or DevFWLine<i> (single-device updaters, e.g. the Huntsman V3 Pro Mini)
#   - optional second target ("Flash FW", FlashFWType/FlashFWVer): byte[] resources FlashFWSector<i>
#   plus metadata (PID, BLPID, versions, ...).
#
# Usage: pwsh tools/extract_razer_fw.ps1 -Updater <updater.exe> -OutDir <dir>
param(
    [Parameter(Mandatory)] [string] $Updater,
    [Parameter(Mandatory)] [string] $OutDir
)
$ErrorActionPreference = 'Stop'

$extract = Join-Path $OutDir 'updater_extracted'
New-Item -ItemType Directory -Force $extract | Out-Null
7z x $Updater -o"$extract" -y | Out-Null

$res = Join-Path $extract 'DeviceUpdater.resources'
$rr = [System.Resources.ResourceReader]::new($res)
$h = @{}
$e = $rr.GetEnumerator()
while ($e.MoveNext()) { $h[$e.Key] = $e.Value }
$rr.Close()

'Metadata:'
$h.Keys | Where-Object { $_ -notmatch 'FWLine\d+$|^FlashFWSector\d+$' } | Sort-Object | ForEach-Object { '  {0,-18} {1}' -f $_, $h[$_] }

$fwDir = Join-Path $OutDir 'firmware'
New-Item -ItemType Directory -Force $fwDir | Out-Null

function Write-Hex($prefix, $suffix) {
    $n = $h["${prefix}FWLineNum"]
    if (-not $n) { return }
    $lines = 0..($n - 1) | ForEach-Object { $h["${prefix}FWLine$_"] }
    if ($lines -contains $null) { throw "$prefix is missing HEX lines" }
    $name = ($h["ProductName$suffix"] -replace '\s', '') + "_${prefix}_v$($h["DevFWVer$suffix"]).hex"
    $out = Join-Path $fwDir ($name -replace '^(.*?)_Dev', '$1_dev')
    [IO.File]::WriteAllLines($out, $lines)
    "Wrote $out ($n lines)"
}

if ($h['DeviceNum']) {
    for ($dev = 1; $dev -le $h['DeviceNum']; $dev++) { Write-Hex "Dev$dev" $dev }
} else {
    Write-Hex 'Dev' ''
}

$sectors = $h.Keys | Where-Object { $_ -match '^FlashFWSector(\d+)$' } | Sort-Object { [int]($_ -replace '\D', '') }
if ($sectors) {
    $buf = [System.Collections.Generic.List[byte]]::new()
    foreach ($k in $sectors) { $buf.AddRange([byte[]]$h[$k]) }
    $name = if ($h['RYFWFileName']) { $h['RYFWFileName'] } else { "flashfw_v$($h['FlashFWVer']).bin" }
    $out = Join-Path $fwDir $name
    [IO.File]::WriteAllBytes($out, $buf.ToArray())
    "Wrote $out ($($buf.Count) bytes from $(@($sectors).Count) FlashFW sectors, FlashFWFileSize=$($h['FlashFWFileSize']))"
}
