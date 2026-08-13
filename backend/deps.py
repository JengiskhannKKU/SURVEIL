"""Shared helpers for loading/saving engagements and items in API routes."""
from __future__ import annotations

from fastapi import HTTPException

from surveil import state
from surveil.models import ChecklistItem, Engagement


def load_engagement(eng_id: str) -> Engagement:
    try:
        return state.load(eng_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Engagement '{eng_id}' not found")


def get_item(engagement: Engagement, item_id: str) -> ChecklistItem:
    item = engagement.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Checklist item '{item_id}' not found")
    return item
