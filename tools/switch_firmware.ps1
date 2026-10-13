# Switch the Razer Huntsman Mini between QMK and Razer's stock firmware over USB, without opening the case.
# Requires the boot shim on the keyboard (any QMK build from huntsman-mini/qmk installs it).
#
#   pwsh tools/switch_firmware.ps1 -To stock    # QMK -> stock: restores your Razer settings + flashes stock
#   pwsh tools/switch_firmware.ps1 -To qmk      # stock -> QMK
#   add -DryRun to only print what would run
#
# Uses: .venv (hidapi) for tools/enter_bootloader.py, and QMK Toolbox's dfu-util (with its DFU driver).
# Stock files come from YOUR OWN SWD backup (huntsman-mini/dumps, never published):
#   stock_with_shim.bin                 tools/make_stock_image.py output
#   pre_qmk_eeprom_08080000_8K.bin      Razer settings + serial, restored to the data EEPROM
param(
    [Parameter(Mandatory)] [ValidateSet('qmk', 'stock')] [string] $To,
    [switch] $DryRun
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$py = Join-Path $repo '.venv/Scripts/python.exe'
$dfu = Join-Path $env:LOCALAPPDATA 'QMK/Toolbox/dfu-util.exe'
$images = @{
    qmk         = Join-Path $repo 'huntsman-mini/qmk/build/razer_huntsman_mini_via.bin'
    stock       = Join-Path $repo 'huntsman-mini/dumps/stock_with_shim.bin'
    stockEeprom = Join-Path $repo 'huntsman-mini/dumps/pre_qmk_eeprom_08080000_8K.bin'
}

$need = @($py, $dfu, $images[$To])
if ($To -eq 'stock') { $need += $images.stockEeprom }
foreach ($f in $need) { if (-not (Test-Path $f)) { throw "missing: $f" } }

function Invoke-Step($what, [scriptblock] $cmd, [string] $successPattern) {
    Write-Host "== $what"
    if ($DryRun) { Write-Host "   (dry run) $cmd"; return }
    $out = & $cmd 2>&1 | ForEach-Object { "$_" }
    $out | Where-Object { $_ -match 'bootloader|stock|QMK|Downloading element|downloaded|rror' } | ForEach-Object { Write-Host "   $_" }
    # dfu-util's exit status after "leave" isn't reliable (the device resets), so flash steps check its output
    $ok = if ($successPattern) { [bool]($out -match $successPattern) } else { $LASTEXITCODE -eq 0 }
    if (-not $ok) { throw "failed: $what" }
}

function Get-MiniState {
    $d = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
        Where-Object { $_.InstanceId -match '^USB\\VID_(5248|0483|1532)&PID_(0257|DF11)\\' }
    if (-not $d) { return 'none' }
    ($d | ForEach-Object {
        if ($_.InstanceId -match 'VID_0483') { 'bootloader' } elseif ($_.InstanceId -match 'VID_1532') { 'stock' } else { 'qmk' }
    }) -join ','
}

Invoke-Step 'enter the bootloader' { & $py (Join-Path $repo 'tools/enter_bootloader.py') }

if ($To -eq 'stock') {
    Invoke-Step 'restore Razer settings (data EEPROM @ 0x08080000)' {
        & $dfu -a 2 -d 0483:df11 -s 0x08080000 -D $images.stockEeprom
    } 'File downloaded successfully'
}
Invoke-Step "flash $To image @ 0x08000000" { & $dfu -a 0 -d 0483:df11 -s 0x08000000:leave -D $images[$To] } 'File downloaded successfully'

if ($DryRun) { return }
$t0 = Get-Date
while (((Get-Date) - $t0).TotalSeconds -lt 20) {
    $state = Get-MiniState
    if ($state -eq $To) { Write-Host ("== done: the Mini is running {0} ({1:N1} s)" -f $To, ((Get-Date) - $t0).TotalSeconds); return }
    Start-Sleep -Milliseconds 250
}
throw "the Mini did not come back as '$To' (now: $(Get-MiniState)); replug it, or hold Esc while plugging in to reach the bootloader"
