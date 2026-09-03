from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from oculus import state
from oculus.checklist import build_checklist, build_oscp_checklist
from oculus.models import Engagement

from ..deps import load_engagement

router = APIRouter(prefix="/api/engagements", tags=["engagements"])

# Methodology tag -> checklist builder. "other" intentionally falls back to
# the WSTG checklist as a starting point (see frontend/src/lib/
# methodologies.ts's own description of that option) rather than having a
# third checklist shape with nothing to actually distinguish it.
_CHECKLIST_BUILDERS = {
    "wstg": build_checklist,
    "oscp": build_oscp_checklist,
}


class NewEngagement(BaseModel):
    target: str
    name: str = ""
    notes: str = ""
    icon: str = "web"
    methodology: str = "wstg"


@router.get("")
def list_engagements() -> list[dict]:
    return state.list_all()


@router.post("")
def create_engagement(body: NewEngagement) -> Engagement:
    methodology = body.methodology or "wstg"
    build = _CHECKLIST_BUILDERS.get(methodology, build_checklist)
    engagement = Engagement(
        target=body.target,
        name=body.name or body.target,
        icon=body.icon or "web",
        methodology=methodology,
        scope_notes=body.notes,
        checklist_items=build(),
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
