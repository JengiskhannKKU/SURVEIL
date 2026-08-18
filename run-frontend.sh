#!/usr/bin/env bash
# Run the surveil Next.js frontend dev server.
#
# Usage: ./run-frontend.sh [port]
#   port  - defaults to 3000
#
# Expects the backend to already be running (see run-backend.sh or the
# "Web app" section of README.md) — the frontend just talks to it over
# NEXT_PUBLIC_API_URL / NEXT_PUBLIC_WS_URL from frontend/.env.local.
set -euo pipefail

PORT="${1:-3000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

cd "$FRONTEND_DIR"

if ! command -v npm >/dev/null 2>&1; then
	echo "npm not found — install Node.js first (https://nodejs.org)." >&2
	exit 1
fi

if [ ! -d node_modules ]; then
	echo "Installing frontend dependencies..."
	npm install
fi

if [ ! -f .env.local ]; then
	echo "No .env.local found — copying .env.example (points at http://127.0.0.1:8000)."
	cp .env.example .env.local
fi

echo "Starting frontend dev server on http://localhost:$PORT"
exec npm run dev -- -p "$PORT"
