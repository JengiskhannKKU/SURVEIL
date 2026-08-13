from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from surveil import state
from surveil.models import ChecklistItem, Engagement
from surveil.orchestrator import Orchestrator

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
