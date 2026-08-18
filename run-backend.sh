#!/usr/bin/env bash
# Run the surveil FastAPI backend.
#
# Usage: ./run-backend.sh [port]
#   port  - defaults to 8000
#
# Creates ./venv if it doesn't exist yet and installs surveil + the
# "web" extra (fastapi/uvicorn/websockets) into it before starting.
set -euo pipefail

PORT="${1:-8000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
	echo "python3 not found — install Python 3.9+ first." >&2
	exit 1
fi

if [ ! -d venv ]; then
	echo "Creating venv..."
	python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

if ! python -c "import fastapi, uvicorn" >/dev/null 2>&1; then
	echo "Installing surveil + web extras into venv..."
	pip install -e ".[web]" -q
fi

echo "Starting backend on http://127.0.0.1:$PORT"
exec uvicorn backend.main:app --reload --port "$PORT"
