# Extract Intel HEX firmware images from a Razer "CustomerFWU2Point5" firmware updater.
# The updater is a self-extracting zip; the firmware lives in DeviceUpdater.resources as one
# .NET string resource per HEX line (Dev<N>FWLine<i>), plus metadata (PID, BLPID, versions).
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
$h.Keys | Where-Object { $_ -notmatch 'FWLine\d+$' } | Sort-Object | ForEach-Object { '  {0,-18} {1}' -f $_, $h[$_] }

$fwDir = Join-Path $OutDir 'firmware'
New-Item -ItemType Directory -Force $fwDir | Out-Null
for ($dev = 1; $dev -le $h['DeviceNum']; $dev++) {
    $n = $h["Dev${dev}FWLineNum"]
    $lines = 0..($n - 1) | ForEach-Object { $h["Dev${dev}FWLine$_"] }
    if ($lines -contains $null) { throw "Dev$dev is missing HEX lines" }
    $name = ($h["ProductName$dev"] -replace '\s', '') + "_dev${dev}_v$($h["DevFWVer$dev"]).hex"
    $out = Join-Path $fwDir $name
    [IO.File]::WriteAllLines($out, $lines)
    "Wrote $out ($n lines)"
}
