#!/usr/bin/env bash
# Install hermes-local-models (auto-llamacpp) on macOS / Linux into Hermes home.
# Wires Hermes so it automatically uses local llama-server (llama.cpp).
# Usage:
#   chmod +x install.sh
#   ./install.sh
#   ./install.sh --cpu --skip-start --no-shortcuts
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
DEST="$HERMES_HOME/scripts"
DOCS="$HERMES_HOME"
PY="${PYTHON:-python3}"

NO_SHORTCUTS=0
CPU=0
SKIP_START=0
for arg in "$@"; do
  case "$arg" in
    --no-shortcuts) NO_SHORTCUTS=1 ;;
    --cpu) CPU=1 ;;
    --skip-start) SKIP_START=1 ;;
    -h|--help)
      echo "Usage: ./install.sh [--cpu] [--skip-start] [--no-shortcuts]"
      exit 0
      ;;
  esac
done

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "ERROR: $PY not found. Install Python 3.10+."
  exit 1
fi

# Resolve absolute interpreter path (LaunchAgents / systemd have a minimal PATH)
PY_ABS="$("$PY" -c 'import sys; print(sys.executable)' 2>/dev/null || true)"
if [[ -z "${PY_ABS}" || ! -e "${PY_ABS}" ]]; then
  PY_ABS="$(command -v "$PY" || true)"
fi
if [[ -z "${PY_ABS}" || ! -e "${PY_ABS}" ]]; then
  echo "ERROR: could not resolve absolute path for $PY"
  exit 1
fi
# Prefer realpath when available (Homebrew shims)
if command -v realpath >/dev/null 2>&1; then
  PY_ABS="$(realpath "$PY_ABS" 2>/dev/null || echo "$PY_ABS")"
fi
echo "Python: $PY_ABS"
PY="$PY_ABS"

mkdir -p "$DEST"
for f in sync_atomic_models.py ensure_local_router.py start_hermes_desktop_local.py \
         patch_hermes_config.py paths.py start-hermes-local.ps1; do
  if [[ -f "$REPO_ROOT/scripts/$f" ]]; then
    cp -f "$REPO_ROOT/scripts/$f" "$DEST/$f"
    echo "Installed $f -> $DEST"
  fi
done
chmod +x "$DEST"/*.py 2>/dev/null || true

cp -f "$REPO_ROOT/docs/LOCAL_MODELS.md" "$DOCS/LOCAL_MODELS.md"
echo "Installed LOCAL_MODELS.md -> $DOCS"

# Sync may fail if no GGUFs yet; patch still wires local primary
if ! "$PY" "$DEST/sync_atomic_models.py"; then
  echo "WARNING: sync_atomic_models failed (no models yet?). Continuing config patch."
fi
"$PY" "$DEST/patch_hermes_config.py"

if [[ "$NO_SHORTCUTS" -eq 0 ]]; then
  # LaunchAgent for login autostart (macOS)
  if [[ "$(uname -s)" == "Darwin" ]]; then
    LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
    mkdir -p "$LAUNCH_AGENTS"
    LABEL="xyz.nuroctane.hermes-local-router"
    PLIST="$LAUNCH_AGENTS/${LABEL}.plist"
    UID_NUM="$(id -u)"
    DOMAIN="gui/${UID_NUM}"

    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PY}</string>
    <string>${DEST}/ensure_local_router.py</string>
    <string>start</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <false/>
  <key>WorkingDirectory</key>
  <string>${DEST}</string>
  <key>StandardOutPath</key>
  <string>${HERMES_HOME}/logs/launchagent-router.out.log</string>
  <key>StandardErrorPath</key>
  <string>${HERMES_HOME}/logs/launchagent-router.err.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>HERMES_HOME</key>
    <string>${HERMES_HOME}</string>
  </dict>
</dict>
</plist>
EOF
    mkdir -p "$HERMES_HOME/logs"

    # Unload any previous job (modern + legacy)
    launchctl bootout "${DOMAIN}/${LABEL}" 2>/dev/null || true
    launchctl unload "$PLIST" 2>/dev/null || true

    LOADED=0
    if launchctl bootstrap "${DOMAIN}" "$PLIST" 2>/tmp/hermes-la-bootstrap.err; then
      LOADED=1
      echo "LaunchAgent loaded via bootstrap: $PLIST"
    elif launchctl load "$PLIST" 2>/tmp/hermes-la-load.err; then
      LOADED=1
      echo "LaunchAgent loaded via legacy load: $PLIST"
    fi

    if [[ "$LOADED" -ne 1 ]]; then
      echo "ERROR: Failed to load LaunchAgent ${LABEL}"
      echo "  plist: $PLIST"
      if [[ -f /tmp/hermes-la-bootstrap.err ]]; then
        echo "  bootstrap stderr:"
        cat /tmp/hermes-la-bootstrap.err || true
      fi
      if [[ -f /tmp/hermes-la-load.err ]]; then
        echo "  load stderr:"
        cat /tmp/hermes-la-load.err || true
      fi
      echo "Try manually:"
      echo "  launchctl bootstrap gui/\$(id -u) $PLIST"
      echo "  launchctl print gui/\$(id -u)/${LABEL}"
      exit 1
    fi

    # Verify job is registered (best-effort)
    if launchctl print "${DOMAIN}/${LABEL}" >/dev/null 2>&1; then
      echo "LaunchAgent verified: ${DOMAIN}/${LABEL}"
    else
      echo "WARNING: launchctl print could not verify ${DOMAIN}/${LABEL}"
      echo "  Check: launchctl print ${DOMAIN}/${LABEL}"
    fi

    APP_SCRIPT="$HOME/Applications/Hermes Desktop (Auto llama.cpp).command"
    mkdir -p "$HOME/Applications"
    cat > "$APP_SCRIPT" <<EOF
#!/bin/bash
cd "$DEST"
exec "$PY" "$DEST/start_hermes_desktop_local.py"
EOF
    chmod +x "$APP_SCRIPT"
    echo "Launcher: $APP_SCRIPT"
    # Remove legacy launcher name if present
    LEGACY_APP="$HOME/Applications/Hermes Desktop Local Models.command"
    if [[ -f "$LEGACY_APP" ]]; then
      rm -f "$LEGACY_APP"
      echo "Removed legacy launcher: $LEGACY_APP"
    fi
  else
    # Linux: user systemd unit optional
    UNIT_DIR="$HOME/.config/systemd/user"
    mkdir -p "$UNIT_DIR"
    UNIT="$UNIT_DIR/hermes-local-router.service"
    cat > "$UNIT" <<EOF
[Unit]
Description=Hermes auto-llamacpp router (llama-server / llama.cpp)
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$DEST
Environment=HERMES_HOME=$HERMES_HOME
Environment=PATH=/usr/local/bin:/usr/bin:/bin
ExecStart=$PY $DEST/ensure_local_router.py start
ExecStop=$PY $DEST/ensure_local_router.py stop

[Install]
WantedBy=default.target
EOF
    if command -v systemctl >/dev/null 2>&1; then
      systemctl --user daemon-reload
      if systemctl --user enable --now hermes-local-router.service; then
        echo "systemd user unit enabled: $UNIT"
      else
        echo "WARNING: systemctl enable failed for hermes-local-router.service"
        echo "  Unit written to: $UNIT"
        echo "  Try: systemctl --user enable --now hermes-local-router.service"
      fi
    else
      echo "systemd user unit written (systemctl not available): $UNIT"
    fi
  fi
fi

if [[ "$SKIP_START" -eq 0 ]]; then
  if [[ "$CPU" -eq 1 ]]; then
    "$PY" "$DEST/ensure_local_router.py" start --cpu
  else
    "$PY" "$DEST/ensure_local_router.py" start
  fi
fi

echo ""
echo "Install complete (Unix, auto-llamacpp)."
echo "  Hermes home: $HERMES_HOME"
echo "  Docs:        $DOCS/LOCAL_MODELS.md"
echo "  Provider:    auto-llamacpp (Hermes -> llama-server / llama.cpp)"
echo "  API:         http://127.0.0.1:8080/v1/models"
echo "  Start:       $PY $DEST/ensure_local_router.py start"
echo ""
echo "macOS tip: brew install llama.cpp   # if Atomic/Jan backends missing"
echo "Models:    ~/Library/Application Support/Atomic Chat/data/llamacpp/models"
echo "       or  ~/Library/Application Support/Jan/data/llamacpp/models"
echo ""
echo "Mac smoke check (after install):"
echo "  curl -s http://127.0.0.1:8080/v1/models | python3 -m json.tool"
echo "  launchctl print gui/\$(id -u)/xyz.nuroctane.hermes-local-router | head"
echo "  open ~/Applications/Hermes\\ Desktop\\ \\(Auto\\ llama.cpp\\).command"
