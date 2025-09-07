#!/usr/bin/env zsh
# Simple endpoint checker: queries common API endpoints and prints status + body.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

BASE_URL=${BASE_URL:-http://127.0.0.1:8000}
USER=""
PASS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -u|--user)
      USER="$2"; shift 2;;
    -p|--pass|--password)
      PASS="$2"; shift 2;;
    -h|--help)
      echo "Usage: $0 [-u user] [-p pass] [--base-url URL]"; exit 0;;
    --base-url)
      BASE_URL="$2"; shift 2;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

curl_opts=( -sS -i -w "\n---HTTP-STATUS:%{http_code}---\n" )
auth_opts=()
if [[ -n "$USER" && -n "$PASS" ]]; then
  auth_opts=( -u "${USER}:${PASS}" )
fi

echo "Checking APIs at $BASE_URL"

do_req() {
  method=$1; path=$2; data=${3:-}
  url="$BASE_URL$path"
  echo "\n==> $method $path"
  if [[ -n "$data" ]]; then
    curl "${curl_opts[@]}" "${auth_opts[@]}" -H "Content-Type: application/json" -X "$method" -d "$data" "$url"
  else
    curl "${curl_opts[@]}" "${auth_opts[@]}" -X "$method" "$url"
  fi
}

# Safe read-only endpoints
do_req GET /api/hello
do_req GET /api/debug/ip
do_req GET /api/users
do_req GET /api/users/phanith.chhim
do_req GET /api/users/phanith.chhim/permissions
do_req GET /api/roles
do_req GET /api/roles/permissions/1

# Non-destructive POSTs to exercise login/signout and permission checks
if [[ -n "$USER" && -n "$PASS" ]]; then
  do_req POST /api/login "{\"username\": \"${USER}\", \"password\": \"${PASS}\"}"
else
  do_req POST /api/login "{\"username\": \"phanith.chhim\", \"password\": \"Nith@2010\"}"
fi

do_req POST /api/signout "{\"username\": \"phanith.chhim\"}"

echo "\nFinished checks. For full test runs use ./scripts/run_tests.sh"