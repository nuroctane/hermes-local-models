# Install hermes-local-models into Hermes home and wire Desktop/Startup shortcuts.
# Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
param(
  [switch]$NoShortcuts,
  [switch]$Cpu,
  [switch]$SkipStart
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
$Dest = Join-Path $env:LOCALAPPDATA "hermes\scripts"
$DocsDest = Join-Path $env:LOCALAPPDATA "hermes"
$Py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Py) { throw "python not found on PATH" }
# Absolute interpreter (Startup shortcuts have a limited environment)
try {
  $PyAbs = & $Py -c "import sys; print(sys.executable)" 2>$null
  if ($PyAbs -and (Test-Path $PyAbs)) { $Py = $PyAbs.Trim() }
} catch {}
Write-Host "Python: $Py"
$Pyw = $null
$pywCandidate = Join-Path (Split-Path $Py -Parent) "pythonw.exe"
if (Test-Path $pywCandidate) {
  $Pyw = $pywCandidate
} else {
  $PywCmd = Get-Command pythonw -ErrorAction SilentlyContinue
  if ($PywCmd) { $Pyw = $PywCmd.Source }
}
if (-not $Pyw) { $Pyw = $Py }

New-Item -ItemType Directory -Force -Path $Dest | Out-Null

$files = @(
  "paths.py",
  "sync_atomic_models.py",
  "ensure_local_router.py",
  "start_hermes_desktop_local.py",
  "patch_hermes_config.py",
  "start-hermes-local.ps1"
)
foreach ($f in $files) {
  $src = Join-Path $RepoRoot "scripts\$f"
  if (Test-Path $src) {
    Copy-Item -Force $src (Join-Path $Dest $f)
    Write-Host "Installed $f -> $Dest"
  }
}

Copy-Item -Force (Join-Path $RepoRoot "docs\LOCAL_MODELS.md") (Join-Path $DocsDest "LOCAL_MODELS.md")
Write-Host "Installed LOCAL_MODELS.md -> $DocsDest"

# Patch Hermes config for custom local primary + nvidia fallback if not already
& $Py (Join-Path $Dest "sync_atomic_models.py")
& $Py (Join-Path $RepoRoot "scripts\patch_hermes_config.py")

if (-not $NoShortcuts) {
  $Wsh = New-Object -ComObject WScript.Shell

  $startup = [Environment]::GetFolderPath("Startup")
  $sc1 = $Wsh.CreateShortcut((Join-Path $startup "Hermes Local Model Router.lnk"))
  $sc1.TargetPath = $Pyw
  $sc1.Arguments = "`"$(Join-Path $Dest 'ensure_local_router.py')`" start"
  $sc1.WorkingDirectory = $Dest
  $sc1.WindowStyle = 7
  $sc1.Description = "Start Hermes multi-model local router (Atomic Chat GGUFs)"
  $sc1.Save()
  Write-Host "Startup: Hermes Local Model Router.lnk ($Pyw)"

  $desk = [Environment]::GetFolderPath("Desktop")
  $sc2 = $Wsh.CreateShortcut((Join-Path $desk "Hermes Desktop (Local Models).lnk"))
  $sc2.TargetPath = $Py
  $sc2.Arguments = "`"$(Join-Path $Dest 'start_hermes_desktop_local.py')`""
  $sc2.WorkingDirectory = $Dest
  $sc2.Description = "Ensure local models router then open Hermes Desktop"
  $sc2.Save()
  Write-Host "Desktop: Hermes Desktop (Local Models).lnk"
}

if (-not $SkipStart) {
  $args = @((Join-Path $Dest "ensure_local_router.py"), "start")
  if ($Cpu) { $args += "--cpu" }
  & $Py @args
}

Write-Host ""
Write-Host "Install complete."
Write-Host "  Docs:  $DocsDest\LOCAL_MODELS.md"
Write-Host "  API:   http://127.0.0.1:8080/v1/models"
Write-Host "  Start: python $Dest\ensure_local_router.py start"
