from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from oculus import state
from oculus.models import Engagement, ManualPathEntry

from ..deps import load_engagement

router = APIRouter(prefix="/api/engagements/{eng_id}/paths", tags=["paths"])


class NewManualPath(BaseModel):
    path: str
    status: Optional[int] = None
    note: str = ""


class PathRef(BaseModel):
    path: str


def _normalize(path: str) -> str:
    path = path.strip()
    if not path.startswith("/"):
        path = f"/{path}"
    return path


@router.post("")
def add_manual_path(eng_id: str, body: NewManualPath) -> Engagement:
    engagement = load_engagement(eng_id)
    path = _normalize(body.path)
    # Upsert: re-adding a path that's already a manual entry updates it in
    # place instead of creating a duplicate node in the tree.
    engagement.manual_paths = [p for p in engagement.manual_paths if p.path != path]
    engagement.manual_paths.append(ManualPathEntry(path=path, status=body.status, note=body.note))
    # Adding a path back should un-hide it if it was previously removed —
    # otherwise it'd silently vanish again behind the hide-list.
    engagement.removed_paths = [p for p in engagement.removed_paths if p != path]
    state.save(engagement)
    return engagement


@router.post("/remove")
def remove_path(eng_id: str, body: PathRef) -> Engagement:
    """Removes a path from the tree. A manual entry is deleted outright;
    an auto-discovered one (parsed from a tool's raw output, which this
    app never mutates) is hidden via `removed_paths` instead."""
    engagement = load_engagement(eng_id)
    path = _normalize(body.path)
    was_manual = any(p.path == path for p in engagement.manual_paths)
    if was_manual:
        engagement.manual_paths = [p for p in engagement.manual_paths if p.path != path]
    elif path not in engagement.removed_paths:
        engagement.removed_paths.append(path)
    state.save(engagement)
    return engagement


@router.post("/restore")
def restore_path(eng_id: str, body: PathRef) -> Engagement:
    """Un-hides a previously-removed auto-discovered path."""
    engagement = load_engagement(eng_id)
    path = _normalize(body.path)
    engagement.removed_paths = [p for p in engagement.removed_paths if p != path]
    state.save(engagement)
    return engagement
