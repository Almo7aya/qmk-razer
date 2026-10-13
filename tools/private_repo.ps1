# Private companion repo for files that must never go public (Razer firmware/updaters, dumps, decompiled code, ...).
#
# It is a second git repository over the SAME working tree: its git dir is .private.git (ignored by the public repo),
# and it tracks exactly the files the public .gitignore excludes, at their normal paths. Scripts keep working, and
# cloning the private repo next to a public clone and copying it over restores everything.
#
#   pwsh tools/private_repo.ps1 init -Remote <url>   one-time setup
#   pwsh tools/private_repo.ps1 status               what would be added/changed
#   pwsh tools/private_repo.ps1 sync [-Message ..]   add new/changed private files and commit
#   pwsh tools/private_repo.ps1 push                 push to the private remote
param(
    [Parameter(Mandatory, Position = 0)] [ValidateSet('init', 'status', 'sync', 'push')] [string] $Command,
    [string] $Remote,
    [string] $Message
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
$gd = Join-Path $repo '.private.git'

# Ignored-by-public files that are NOT worth keeping (reinstallable or regenerable)
$skip = @(
    '^\.venv/', '^\.tools/', '^\.claude/', '__pycache__/', '\.pyc$',
    '^huntsman-mini/re/updater/ghidra/'   # 105 MB Ghidra DB of Razer's updater DLL; regenerate with decompile_fwupdaterdll.py
)

function PGit { git --git-dir=$gd @args; if ($LASTEXITCODE -ne 0) { throw "git $args failed" } }

function Get-PrivateFiles {
    git ls-files --others --ignored --exclude-standard |
        Where-Object { $f = $_; -not ($skip | Where-Object { $f -match $_ }) } |
        Where-Object { $_ -notmatch '^\.private\.git/' }
}

switch ($Command) {
    'init' {
        if (Test-Path $gd) { throw ".private.git already exists" }
        git init -q --bare -b main $gd
        PGit config core.bare false
        PGit config core.worktree '..'
        PGit config status.showUntrackedFiles no
        # Store everything byte-exact: the public .gitattributes (eol=lf) must not touch Razer's files
        # (e.g. driver .inf files covered by .cat signatures)
        PGit config core.autocrlf false
        Set-Content -Path (Join-Path $gd 'info/attributes') -Value '* -text' -Encoding ascii
        if ($Remote) { PGit remote add origin $Remote }
        Write-Host "initialised $gd"
    }
    'status' {
        $files = Get-PrivateFiles
        $tracked = @(PGit ls-files)
        $new = $files | Where-Object { $_ -notin $tracked }
        Write-Host ("{0} private files, {1} not yet in the private repo" -f @($files).Count, @($new).Count)
        $new | ForEach-Object { Write-Host "  + $_" }
        PGit status --short
    }
    'sync' {
        $list = Join-Path $gd 'sync-files.txt'
        Get-PrivateFiles | Set-Content -Encoding utf8 $list
        PGit add -f --pathspec-from-file=$list
        PGit add -u
        $staged = PGit diff --cached --name-only
        if (-not $staged) { Write-Host 'nothing to commit'; return }
        if (-not $Message) { $Message = "Private files sync $(Get-Date -Format 'yyyy-MM-dd HH:mm')" }
        $Message | git --git-dir=$gd commit -q -F -
        Write-Host ("committed {0} changed files" -f @($staged).Count)
    }
    'push' {
        PGit push -u origin main
    }
}
