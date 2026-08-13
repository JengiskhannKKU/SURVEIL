from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from surveil import state
from surveil.checklist import build_checklist
from surveil.models import Engagement

from ..deps import load_engagement

router = APIRouter(prefix="/api/engagements", tags=["engagements"])


class NewEngagement(BaseModel):
    target: str
    name: str = ""
    notes: str = ""


@router.get("")
def list_engagements() -> list[dict]:
    return state.list_all()


@router.post("")
def create_engagement(body: NewEngagement) -> Engagement:
    engagement = Engagement(
        target=body.target,
        name=body.name or body.target,
        scope_notes=body.notes,
        checklist_items=build_checklist(),
    )
    state.save(engagement)
    return engagement


@router.get("/{eng_id}")
def get_engagement(eng_id: str) -> Engagement:
    return load_engagement(eng_id)


@router.delete("/{eng_id}")
def delete_engagement(eng_id: str) -> dict:
    if not state.delete(eng_id):
        raise HTTPException(status_code=404, detail=f"Engagement '{eng_id}' not found")
    return {"deleted": eng_id}
