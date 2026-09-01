#!/usr/bin/env bash
# Run the whole oculus web app in Docker: backend + frontend, no local
# Python/Node install needed — just Docker.
#
# Usage: ./run-docker.sh [up|down|logs|build]
#   up     (default) - build if needed and start backend + frontend
#   down             - stop and remove the containers (data volume kept)
#   logs             - follow both services' logs
#   build            - rebuild both images from current source
#
# Open http://localhost:3000 once it's up — that's the UI. The backend
# only serves /api/* and /ws/* on :8000; opening that port directly in a
# browser 404s on everything else (expected, not a bug).
#
# Engagement data persists in the `oculus-data` Docker volume across
# `down`/`up` cycles — it's only gone if you `docker compose down -v`.
#
# The CLI/TUI isn't started by this script (it needs an interactive
# terminal and isn't part of "the web app") — run it directly with:
#   docker compose run --rm oculus <args>
#   docker compose run --rm oculus tui
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v docker >/dev/null 2>&1; then
	echo "docker not found — install Docker Desktop first (https://docker.com)." >&2
	exit 1
fi

if ! docker info >/dev/null 2>&1; then
	echo "Docker daemon isn't running — start Docker Desktop first." >&2
	exit 1
fi

ACTION="${1:-up}"

case "$ACTION" in
up)
	echo "Building (if needed) and starting backend + frontend..."
	docker compose up --build -d backend frontend
	echo
	echo "Frontend: http://localhost:3000"
	echo "Backend:  http://localhost:8000 (API/WS only, not a browsable UI)"
	echo
	echo "Follow logs with: ./run-docker.sh logs"
	echo "Stop with:        ./run-docker.sh down"
	;;
down)
	docker compose down
	;;
logs)
	docker compose logs -f backend frontend
	;;
build)
	docker compose build backend frontend
	;;
*)
	echo "Usage: ./run-docker.sh [up|down|logs|build]" >&2
	exit 1
	;;
esac
