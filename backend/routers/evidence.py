from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from oculus import evidence_store, state
from oculus.models import ChecklistItem, Evidence

from ..deps import get_item, load_engagement

router = APIRouter(prefix="/api/engagements/{eng_id}/items/{item_id}/evidence", tags=["evidence"])

# Generous enough for a screenshot, a PoC script, a short PCAP — not
# generous enough for a tester to accidentally choke the server (and the
# engagement JSON that references it) uploading something huge by mistake.
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def _find_evidence(item: ChecklistItem, evidence_id: str) -> Evidence:
    for e in item.evidence:
        if e.id == evidence_id:
            return e
    raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")


@router.post("")
async def upload_evidence(
    eng_id: str,
    item_id: str,
    file: UploadFile = File(...),
    description: str = Form(""),
) -> ChecklistItem:
    engagement = load_engagement(eng_id)
    item = get_item(engagement, item_id)

    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(data)} bytes) — {_MAX_UPLOAD_BYTES // (1024 * 1024)}MB max.",
        )

    evidence = Evidence(
        filename=file.filename or "file",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        description=description,
    )
    evidence.stored_name = evidence_store.save_file(
        eng_id, item_id, evidence.id, evidence.filename, data
    )
    item.evidence.append(evidence)
    state.save(engagement)
    return item


@router.patch("/{evidence_id}")
def update_evidence_description(eng_id: str, item_id: str, evidence_id: str, description: str = Form("")) -> ChecklistItem:
    engagement = load_engagement(eng_id)
    item = get_item(engagement, item_id)
    ev = _find_evidence(item, evidence_id)
    ev.description = description
    state.save(engagement)
    return item


@router.delete("/{evidence_id}")
def delete_evidence(eng_id: str, item_id: str, evidence_id: str) -> ChecklistItem:
    engagement = load_engagement(eng_id)
    item = get_item(engagement, item_id)
    ev = _find_evidence(item, evidence_id)
    evidence_store.delete_file(eng_id, item_id, ev.stored_name)
    item.evidence = [e for e in item.evidence if e.id != evidence_id]
    state.save(engagement)
    return item


@router.get("/{evidence_id}/file")
def get_evidence_file(eng_id: str, item_id: str, evidence_id: str) -> FileResponse:
    engagement = load_engagement(eng_id)
    item = get_item(engagement, item_id)
    ev = _find_evidence(item, evidence_id)
    path = evidence_store.file_path(eng_id, item_id, ev.stored_name)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Evidence file missing on disk")
    return FileResponse(path, media_type=ev.content_type, filename=ev.filename)
