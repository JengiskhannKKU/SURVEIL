"""Evidence file storage — the actual bytes for ChecklistItem.evidence.

Files live at ~/.oculus/evidence/<engagement id>/<item id>/<evidence id>_<
original filename> — a real path on disk, not inlined into the
engagement's own JSON (see models.Evidence's docstring for why). Shares
the same ~/.oculus home as engagement state/config (oculus/_home.py), so
it migrates and gets Docker-bind-mounted the same way — no separate
storage location for a tester to lose track of.
"""
from __future__ import annotations

import re
from pathlib import Path

from ._home import ensure_home

_EVIDENCE_ROOT = Path.home() / ".oculus" / "evidence"

# Real filesystem paths from a tester-controlled original filename — strip
# anything that isn't a safe path segment character so a crafted filename
# (e.g. "../../etc/passwd" or one embedding a path separator) can't escape
# the per-item evidence directory.
_UNSAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(name: str) -> str:
    name = Path(name).name  # drop any directory components outright
    cleaned = _UNSAFE_CHARS_RE.sub("_", name).strip("._") or "file"
    return cleaned[:150]  # generous but bounded — some filesystems cap ~255


def item_dir(engagement_id: str, item_id: str) -> Path:
    ensure_home()
    d = _EVIDENCE_ROOT / engagement_id / item_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_file(engagement_id: str, item_id: str, evidence_id: str, filename: str, data: bytes) -> str:
    """Writes *data* to disk and returns the stored filename (evidence-id-
    prefixed, so two uploads of the same original filename never collide)."""
    stored_name = f"{evidence_id}_{_safe_filename(filename)}"
    path = item_dir(engagement_id, item_id) / stored_name
    path.write_bytes(data)
    return stored_name


def file_path(engagement_id: str, item_id: str, stored_name: str) -> Path:
    return item_dir(engagement_id, item_id) / stored_name


def delete_file(engagement_id: str, item_id: str, stored_name: str) -> None:
    path = file_path(engagement_id, item_id, stored_name)
    path.unlink(missing_ok=True)
