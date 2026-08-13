from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from surveil import state
from surveil.models import ChecklistItem
from surveil.orchestrator import Orchestrator

from ..deps import get_item, load_engagement

router = APIRouter(prefix="/api/engagements/{eng_id}/items", tags=["items"])


class NotesUpdate(BaseModel):
    notes: str


@router.post("/{item_id}/mark-done")
def mark_done(eng_id: str, item_id: str) -> ChecklistItem:
    engagement = load_engagement(eng_id)
    item = get_item(engagement, item_id)
    Orchestrator(engagement).mark_done(item)
    state.save(engagement)
    return item


@router.post("/{item_id}/skip")
def skip(eng_id: str, item_id: str) -> ChecklistItem:
    engagement = load_engagement(eng_id)
    item = get_item(engagement, item_id)
    Orchestrator(engagement).mark_skipped(item)
    state.save(engagement)
    return item


@router.post("/{item_id}/reset")
def reset(eng_id: str, item_id: str) -> ChecklistItem:
    engagement = load_engagement(eng_id)
    item = get_item(engagement, item_id)
    Orchestrator(engagement).reset(item)
    state.save(engagement)
    return item


@router.patch("/{item_id}/notes")
def update_notes(eng_id: str, item_id: str, body: NotesUpdate) -> ChecklistItem:
    engagement = load_engagement(eng_id)
    item = get_item(engagement, item_id)
    item.notes = body.notes
    state.save(engagement)
    return item
