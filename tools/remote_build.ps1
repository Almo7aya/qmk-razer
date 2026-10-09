# Build the QMK firmware on a remote build server and copy the result back.
# The server needs a QMK checkout at /root/qmk_firmware and the QMK CLI in /root/qmk-venv.
# Server address: -Server/-Port, or tools/build-server.local.json (gitignored): {"server": "user@host", "port": 22}
# Usage: pwsh tools/remote_build.ps1 [-Keyboard razer/huntsman_mini] [-Keymap via]
param(
    [string] $Keyboard = 'razer/huntsman_mini',
    [string] $Keymap = 'default',
    [string] $Server,
    [int] $Port
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent

$localCfg = Join-Path $PSScriptRoot 'build-server.local.json'
if ((-not $Server) -and (Test-Path $localCfg)) {
    $cfg = Get-Content $localCfg -Raw | ConvertFrom-Json
    $Server = $cfg.server
    if (-not $Port) { $Port = $cfg.port }
}
if (-not $Server) { throw "No build server: pass -Server user@host or create $localCfg" }
if (-not $Port) { $Port = 22 }

$local = Join-Path $repo "huntsman-mini/qmk/keyboards/$Keyboard"
$remoteKb = "/root/qmk_firmware/keyboards/$Keyboard"
$outDir = Join-Path $repo 'huntsman-mini/qmk/build'
New-Item -ItemType Directory -Force $outDir | Out-Null

# Fresh copy of the keyboard directory on the server
ssh -o BatchMode=yes -p $Port $Server "rm -rf '$remoteKb' && mkdir -p '$(Split-Path $remoteKb -Parent)'".Replace('\', '/')
scp -q -r -P $Port $local "${Server}:$(Split-Path $remoteKb -Parent)".Replace('\', '/')

# Compile
$target = ($Keyboard -replace '/', '_') + "_$Keymap"
ssh -o BatchMode=yes -p $Port $Server ". /root/qmk-venv/bin/activate && cd /root/qmk_firmware && qmk compile -kb $Keyboard -km $Keymap -j 8"
if ($LASTEXITCODE -ne 0) { throw "remote build failed" }

# Fetch artifacts
foreach ($ext in 'bin', 'elf', 'map') {
    $remote = if ($ext -eq 'bin') { "/root/qmk_firmware/$target.bin" } else { "/root/qmk_firmware/.build/$target.$ext" }
    scp -q -P $Port "${Server}:$remote" (Join-Path $outDir "$target.$ext")
}
Get-ChildItem $outDir -Filter "$target.*" | Select-Object Name, Length
