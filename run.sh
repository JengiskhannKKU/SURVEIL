#!/usr/bin/env bash
# Run the whole oculus web app: backend + frontend together.
#
# Usage: ./run.sh [backend_port] [frontend_port]
#   backend_port  - defaults to 8000
#   frontend_port - defaults to 3000
#
# Open http://localhost:<frontend_port> in your browser — that's the UI.
# The backend only serves /api/* and /ws/*; opening its port directly
# 404s on everything else (expected).
#
# Starts the backend, waits for it to answer /api/health, then starts
# the frontend (which gets the backend's port written into its
# .env.local, so a non-default backend_port doesn't leave it pointed at
# the wrong place). Ctrl+C (or any exit) stops both — including
# uvicorn's reloader subprocess and npm's "next dev" child, which a
# plain `kill` on the top-level PID would otherwise leave running.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BACKEND_PORT="${1:-8000}"
FRONTEND_PORT="${2:-3000}"

BACKEND_PID=""
FRONTEND_PID=""

# Recursively TERM a process and everything it spawned (uvicorn's
# --reload worker, npm's "next dev" child, etc. don't die with a
# single-PID kill).
kill_tree() {
	local pid="$1"
	local child
	for child in $(pgrep -P "$pid" 2>/dev/null || true); do
		kill_tree "$child"
	done
	kill -TERM "$pid" 2>/dev/null || true
}

cleanup() {
	trap '' EXIT INT TERM
	echo
	echo "Shutting down..."
	[ -n "$FRONTEND_PID" ] && kill_tree "$FRONTEND_PID"
	[ -n "$BACKEND_PID" ] && kill_tree "$BACKEND_PID"
}
trap cleanup EXIT INT TERM

echo "Starting backend on port $BACKEND_PORT..."
./run-backend.sh "$BACKEND_PORT" &
BACKEND_PID=$!

echo -n "Waiting for backend to be ready"
ready=0
for _ in $(seq 1 30); do
	if curl -sf "http://127.0.0.1:$BACKEND_PORT/api/health" >/dev/null 2>&1; then
		ready=1
		break
	fi
	echo -n "."
	sleep 1
done
echo

if [ "$ready" -ne 1 ]; then
	echo "Backend did not become healthy in time — check its output above." >&2
	exit 1
fi
echo "Backend ready."

echo "Starting frontend on port $FRONTEND_PORT..."
./run-frontend.sh "$FRONTEND_PORT" "$BACKEND_PORT" &
FRONTEND_PID=$!

# `wait -n` would be simpler but isn't supported by the bash 3.2 macOS
# ships by default — poll instead so this stays portable.
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
	sleep 1
done
