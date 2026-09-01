"""Shared ~/.oculus home directory resolution + one-time legacy migration.

This project was renamed from "surveil" to "oculus" — anyone who used it
before the rename has real engagement data and settings sitting under
~/.surveil. Rather than silently losing access to that on upgrade,
ensure_home() renames ~/.surveil -> ~/.oculus in place the first time
either state.py or config.py touches it (idempotent: a no-op once the
migration has already happened, or if the tester never had a ~/.surveil
to begin with).
"""
from __future__ import annotations

from pathlib import Path

_LEGACY_HOME = Path.home() / ".surveil"
HOME = Path.home() / ".oculus"


def ensure_home() -> Path:
    if not HOME.exists() and _LEGACY_HOME.exists():
        _LEGACY_HOME.rename(HOME)
    HOME.mkdir(parents=True, exist_ok=True)
    return HOME
