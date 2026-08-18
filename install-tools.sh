#!/usr/bin/env bash
# Interactively install surveil's enumeration tool binaries — not all 16 at
# once, just the ones you pick (recommended set pre-selected).
#
# Usage: ./install-tools.sh
#
# Thin wrapper around `surveil install-tools` (see surveil/tool_installer.py
# for the actual picker/install logic and surveil/tools/*_tool.py for the
# per-tool install commands). Creates ./venv and installs surveil into it
# first if that hasn't been done yet.
set -euo pipefail

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

if ! command -v surveil >/dev/null 2>&1; then
	echo "Installing surveil into venv..."
	pip install -e . -q
fi

exec surveil install-tools
