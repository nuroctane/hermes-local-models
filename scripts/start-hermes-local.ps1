# Legacy single-model launcher: start llama-server (llama.cpp) for Hermes (port 8080).
# Prefer ensure_local_router.py + auto-llamacpp multi-model bridge.
# Usage:
#   .\start-hermes-local.ps1 coder
#   .\start-hermes-local.ps1 gemma
#   .\start-hermes-local.ps1 stop
#   .\start-hermes-local.ps1 status
param(
  [Parameter(Position = 0)]
  [ValidateSet("coder", "gemma", "stop", "status")]
  [string]$Profile = "coder",
  [int]$Port = 8080,
  [int]$CtxSize = 0,
  [switch]$Cpu
)

$ErrorActionPreference = "Stop"
$ModelsRoot = Join-Path $env:APPDATA "Atomic Chat\data\llamacpp\models"
$CudaServer = Join-Path $env:APPDATA "Atomic Chat\data\llamacpp\backends\turboquant-windows-x64-cuda-13.3-61ee3eb\windows-x64-cuda-13.3\build\bin\llama-server.exe"
$CpuServer = Join-Path $env:APPDATA "Atomic Chat\data\llamacpp\backends\turboquant-windows-x64-cpu-61ee3eb\windows-x64-cpu\build\bin\llama-server.exe"

function Get-ListenerPid([int]$ListenPort) {
  try {
    $c = Get-NetTCPConnection -LocalPort $ListenPort -State Listen -ErrorAction SilentlyContinue |
      Select-Object -First 1
    if ($c) { return $c.OwningProcess }
  } catch {}
  return $null
}

function Test-LocalApi([int]$ListenPort) {
  try {
    return Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/v1/models" -f $ListenPort) -TimeoutSec 3
  } catch {
    return $null
  }
}

if ($Profile -eq "status") {
  $pidOn = Get-ListenerPid $Port
  $api = Test-LocalApi $Port
  if ($api) {
    Write-Host ("UP on :{0} (pid={1})" -f $Port, $pidOn)
    foreach ($m in $api.data) { Write-Host ("  model id: {0}" -f $m.id) }
  } else {
    Write-Host ("DOWN - nothing on http://127.0.0.1:{0}/v1/models" -f $Port)
  }
  exit 0
}

if ($Profile -eq "stop") {
  $pidOn = Get-ListenerPid $Port
  if ($pidOn) {
    Stop-Process -Id $pidOn -Force -ErrorAction SilentlyContinue
    Write-Host ("Stopped pid {0} on port {1}" -f $pidOn, $Port)
  } else {
    Write-Host ("No listener on port {0}" -f $Port)
  }
  exit 0
}

if ($Profile -eq "coder") {
  $alias = "qwen3-coder"
  $modelPath = Join-Path $ModelsRoot "AtomicChat\qwen3-coder-30b-a3b-IQ4_XS\model.gguf"
  # Hermes agent requires >= 64K context_length in config; match server -c
  $ctxDefault = 65536
} else {
  $alias = "gemma-3n"
  $modelPath = Join-Path $ModelsRoot "bartowski\google_gemma-3n-E4B-it-IQ4_XS\model.gguf"
  $ctxDefault = 65536
}

if (-not (Test-Path $modelPath)) {
  throw ("Model GGUF not found: {0}" -f $modelPath)
}

if ($Cpu -or -not (Test-Path $CudaServer)) {
  $server = $CpuServer
} else {
  $server = $CudaServer
}
if (-not (Test-Path $server)) {
  throw "llama-server.exe not found under Atomic Chat backends"
}

$existing = Get-ListenerPid $Port
if ($existing) {
  Write-Host ("Port {0} already in use (pid={1}). Run: .\\start-hermes-local.ps1 stop" -f $Port, $existing)
  $api = Test-LocalApi $Port
  if ($api) {
    Write-Host "Existing server models:"
    foreach ($m in $api.data) { Write-Host ("  {0}" -f $m.id) }
  }
  exit 1
}

if ($CtxSize -gt 0) { $ctx = $CtxSize } else { $ctx = $ctxDefault }

Write-Host "Starting llama-server"
Write-Host ("  profile : {0}" -f $Profile)
Write-Host ("  server  : {0}" -f $server)
Write-Host ("  model   : {0}" -f $modelPath)
Write-Host ("  alias   : {0}" -f $alias)
Write-Host ("  port    : {0}" -f $Port)
Write-Host ("  ctx     : {0}" -f $ctx)
Write-Host ("  api     : http://127.0.0.1:{0}/v1" -f $Port)

# Quote paths for spaces (e.g. "Atomic Chat"). Single string ArgumentList is
# more reliable on Windows than a string array for Start-Process.
$ngl = if ($Cpu) { "0" } else { "99" }
$argString = '-m "{0}" -a {1} --host 127.0.0.1 --port {2} -c {3} -ngl {4} --jinja' -f $modelPath, $alias, $Port, $ctx, $ngl
$wd = Split-Path $server -Parent
Start-Process -FilePath $server -ArgumentList $argString -WorkingDirectory $wd -WindowStyle Minimized

Write-Host "Waiting for /v1/models ..."
$ok = $false
for ($i = 0; $i -lt 120; $i++) {
  Start-Sleep -Seconds 2
  $api = Test-LocalApi $Port
  if ($api) {
    Write-Host ("Ready after ~{0} sec" -f ($i * 2))
    foreach ($m in $api.data) { Write-Host ("  model id: {0}" -f $m.id) }
    $ok = $true
    break
  }
  if (($i % 10) -eq 0) {
    Write-Host ("  still loading... {0} sec" -f ($i * 2))
  }
}
if (-not $ok) {
  Write-Host "Timed out waiting for server. Check GPU VRAM or try: .\\start-hermes-local.ps1 gemma -Cpu"
  exit 2
}

Write-Host ""
Write-Host "Hermes usage:"
Write-Host ("  hermes chat -m {0}" -f $alias)
Write-Host "Stop with: .\\start-hermes-local.ps1 stop"
