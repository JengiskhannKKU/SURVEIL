"""Persisted app-wide settings (~/.oculus/config.json).

Separate from engagement state (~/.oculus/engagements/) — this is for
settings that apply across all engagements, currently just the wordlist
directory override. Set via the web UI's Settings dialog or by editing
the file directly; takes priority over the OCULUS_WORDLIST_DIR env var
(oculus/wordlists.py) since it's the more explicit, most-recently-set
value.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ._home import ensure_home

_CONFIG_PATH = Path.home() / ".oculus" / "config.json"


def _load_raw() -> dict:
    ensure_home()
    if not _CONFIG_PATH.is_file():
        return {}
    try:
        return json.loads(_CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_raw(data: dict) -> None:
    ensure_home()
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(data, indent=2))


def get_wordlist_dir() -> Optional[str]:
    return _load_raw().get("wordlist_dir") or None


def set_wordlist_dir(value: Optional[str]) -> None:
    data = _load_raw()
    if value:
        data["wordlist_dir"] = value
    else:
        data.pop("wordlist_dir", None)
    _save_raw(data)
