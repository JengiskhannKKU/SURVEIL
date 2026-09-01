#!/usr/bin/env bash
# Interactively install oculus's enumeration tool binaries — not all 16 at
# once, just the ones you pick (recommended set pre-selected).
#
# Usage: ./install-tools.sh
#
# Thin wrapper around `oculus install-tools` (see oculus/tool_installer.py
# for the actual picker/install logic and oculus/tools/*_tool.py for the
# per-tool install commands). Creates ./venv and installs oculus into it
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

if ! command -v oculus >/dev/null 2>&1; then
	echo "Installing oculus into venv..."
	pip install -e . -q
fi

exec oculus install-tools
