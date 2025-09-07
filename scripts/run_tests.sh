#!/usr/bin/env zsh
# Start mock server (if not running) and run pytest with marker control.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="$PROJECT_ROOT/.venv"
ACTIVATE="$VENV/bin/activate"

MODE="default"
CLI_USER=""
CLI_PASS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)
      MODE="all"; shift ;;
    --integration)
      MODE="integration"; shift ;;
    --manual)
      MODE="manual"; shift ;;
    -u|--user|--username)
      CLI_USER="$2"; shift 2 ;;
    -p|--pass|--password)
      CLI_PASS="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--all|--integration|--manual] [-u|--user USER] [-p|--password PASS]"; exit 0 ;;
    *)
      echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# Activate venv if present
if [[ -f "$ACTIVATE" ]]; then
  # shellcheck source=/dev/null
  . "$ACTIVATE"
  PY="$VENV/bin/python"
else
  PY="$(which python)"
fi

PYTEST_ARGS=("-q")
if [[ "$MODE" == "all" ]]; then
  : # no marker filter
elif [[ "$MODE" == "integration" ]]; then
  PYTEST_ARGS+=("-m" "integration")
elif [[ "$MODE" == "manual" ]]; then
  PYTEST_ARGS+=("-m" "manual")
else
  PYTEST_ARGS+=("-m" "not manual")
fi

# Start mock server if not listening on 8000
MOCK_PID=""
if ! lsof -iTCP:8000 -sTCP:LISTEN -Pn >/dev/null 2>&1; then
  echo "Starting mock API..."
  nohup "$PY" -m scripts.mock_api &>/tmp/mock_api.log &
  MOCK_PID=$!
  echo $MOCK_PID > /tmp/mock_api.pid
  echo "Waiting for mock API to be ready..."
  for i in {1..30}; do
    if curl -sSf http://127.0.0.1:8000/api/hello >/dev/null 2>&1; then
      echo "Mock API ready"
      break
    fi
    sleep 0.5
  done
else
  echo "Mock API already running"
fi

# Set AUTH_USERNAME/AUTH_PASSWORD from CLI args if provided; otherwise keep existing env or set placeholders
if [[ -n "$CLI_USER" ]]; then
  export AUTH_USERNAME="$CLI_USER"
else
  : ${AUTH_USERNAME:="phanith.chhim"}
fi

if [[ -n "$CLI_PASS" ]]; then
  export AUTH_PASSWORD="$CLI_PASS"
else
  : ${AUTH_PASSWORD:="changeme"}
fi

echo "Running pytest ${PYTEST_ARGS[*]}"
set +e
"$PY" -m pytest "${PYTEST_ARGS[@]}"
RC=$?
set -e

# Cleanup mock server if we started it
if [[ -n "$MOCK_PID" ]]; then
  echo "Stopping mock API (pid $MOCK_PID)"
  kill "$MOCK_PID" || true
  rm -f /tmp/mock_api.pid
fi

echo "Mock server log: /tmp/mock_api.log"
exit $RC
