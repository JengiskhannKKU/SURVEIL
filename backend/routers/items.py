from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from oculus import state
from oculus.models import ChecklistItem, Engagement, Status
from oculus.orchestrator import Orchestrator

from .. import ws
from ..deps import get_item, load_engagement

router = APIRouter(prefix="/api/engagements/{eng_id}/items", tags=["items"])


class NotesUpdate(BaseModel):
    notes: str


class NewChecklistItem(BaseModel):
    name: str
    description: str = ""
    category: str
    category_code: str = ""
    tools: list[str] = []
    references: list[str] = []


class ChecklistItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    category_code: str | None = None
    tools: list[str] | None = None
    references: list[str] | None = None


def _slug(text: str) -> str:
    letters = re.sub(r"[^A-Za-z0-9]+", "", text).upper()
    return letters[:6] or "GEN"


def _generate_item_id(engagement: Engagement, category_code: str) -> str:
    base = f"CUSTOM-{_slug(category_code)}"
    existing = {i.id for i in engagement.checklist_items}
    n = 1
    while f"{base}-{n:02d}" in existing:
        n += 1
    return f"{base}-{n:02d}"


@router.post("")
def create_item(eng_id: str, body: NewChecklistItem) -> ChecklistItem:
    engagement = load_engagement(eng_id)
    category_code = body.category_code.strip() or _slug(body.category)
    item = ChecklistItem(
        id=_generate_item_id(engagement, category_code),
        name=body.name,
        description=body.description,
        category=body.category,
        category_code=category_code,
        tools=body.tools,
        references=body.references,
    )
    engagement.checklist_items.append(item)
    state.save(engagement)
    return item


@router.patch("/{item_id}")
def update_item(eng_id: str, item_id: str, body: ChecklistItemUpdate) -> ChecklistItem:
    engagement = load_engagement(eng_id)
    item = get_item(engagement, item_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    state.save(engagement)
    return item


@router.delete("/{item_id}")
def delete_item(eng_id: str, item_id: str) -> dict:
    engagement = load_engagement(eng_id)
    before = len(engagement.checklist_items)
    engagement.checklist_items = [i for i in engagement.checklist_items if i.id != item_id]
    if len(engagement.checklist_items) == before:
        raise HTTPException(status_code=404, detail=f"Checklist item '{item_id}' not found")
    state.save(engagement)
    return {"deleted": item_id}


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


@router.post("/{item_id}/cancel")
def cancel(eng_id: str, item_id: str) -> dict:
    """Stop a tool currently running on this item.

    Signals the run's cancel_event (see backend/ws.py) — the worker thread
    kills the real subprocess (whole process group, so nothing lingers),
    appends "[CANCELLED]" to whatever output it had produced so far, and
    saves that as this item's result. Works whether or not the Run Tool
    dialog that started the run is still open — the run itself isn't tied
    to that WebSocket's lifetime, so this REST endpoint is the only way to
    stop one that was started from a session that's since navigated away.
    """
    engagement = load_engagement(eng_id)
    item = get_item(engagement, item_id)
    if item.status != Status.RUNNING:
        raise HTTPException(status_code=409, detail=f"{item_id} has no tool currently running.")
    found = ws.cancel_run(eng_id, item_id)
    if not found:
        # Status says RUNNING but no cancel_event is registered — the run
        # must have just finished between the tester's click and this
        # request landing. Not an error; the item's real status will
        # reflect that on the next fetch.
        raise HTTPException(status_code=409, detail=f"{item_id}'s run just finished — nothing to cancel.")
    return {"cancelling": item_id}


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
