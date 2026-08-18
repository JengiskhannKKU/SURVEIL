#!/usr/bin/env bash
# Run the surveil Next.js frontend dev server.
#
# Usage: ./run-frontend.sh [port] [backend_port]
#   port          - defaults to 3000
#   backend_port  - defaults to 8000; written into .env.local so the
#                   frontend talks to the backend on the right port
#
# Open http://localhost:<port> in your browser — that's the frontend.
# The backend (see run-backend.sh) only serves /api/* and /ws/*; hitting
# its port directly in a browser 404s on everything else, which is
# expected, not a bug.
set -euo pipefail

PORT="${1:-3000}"
BACKEND_PORT="${2:-8000}"
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
	echo "No .env.local found — copying .env.example."
	cp .env.example .env.local
fi

# Keep NEXT_PUBLIC_API_URL / NEXT_PUBLIC_WS_URL in .env.local pointed at
# whatever port the backend is actually running on, so a custom backend
# port (e.g. `./run.sh 3000 3001`) doesn't silently leave the frontend
# talking to the default :8000. Other lines in .env.local are untouched.
set_env_var() {
	local key="$1" value="$2"
	if grep -q "^${key}=" .env.local; then
		sed -i.bak "s|^${key}=.*|${key}=${value}|" .env.local && rm -f .env.local.bak
	else
		echo "${key}=${value}" >>.env.local
	fi
}
set_env_var NEXT_PUBLIC_API_URL "http://127.0.0.1:${BACKEND_PORT}"
set_env_var NEXT_PUBLIC_WS_URL "ws://127.0.0.1:${BACKEND_PORT}"

echo "Starting frontend dev server on http://localhost:$PORT (backend expected on :$BACKEND_PORT)"
exec npm run dev -- -p "$PORT"
