# Log every USB device that appears or disappears (polls every 200 ms). Catches brief enumerations,
# including failed ones ("Unknown USB Device"). Usage: pwsh tools/usb_watch.ps1 -Log <file> [-Minutes 30]
param([Parameter(Mandatory)] [string] $Log, [int] $Minutes = 30)

function Snapshot {
    $h = @{}
    Get-PnpDevice -PresentOnly -Class USB, HIDClass, Keyboard -ErrorAction SilentlyContinue |
        Where-Object { $_.InstanceId -match '^USB\\' } |
        ForEach-Object { $h[$_.InstanceId] = "$($_.Status) $($_.FriendlyName)" }
    $h
}

$prev = Snapshot
"$(Get-Date -Format HH:mm:ss.fff) watcher started, $($prev.Count) USB devices present" | Tee-Object -FilePath $Log -Append
$end = (Get-Date).AddMinutes($Minutes)
while ((Get-Date) -lt $end) {
    Start-Sleep -Milliseconds 200
    $cur = Snapshot
    foreach ($k in $cur.Keys) { if (-not $prev.ContainsKey($k)) { "$(Get-Date -Format HH:mm:ss.fff) + $k  [$($cur[$k])]" | Tee-Object -FilePath $Log -Append } }
    foreach ($k in $prev.Keys) { if (-not $cur.ContainsKey($k)) { "$(Get-Date -Format HH:mm:ss.fff) - $k" | Tee-Object -FilePath $Log -Append } }
    $prev = $cur
}
"$(Get-Date -Format HH:mm:ss.fff) watcher stopped" | Tee-Object -FilePath $Log -Append
