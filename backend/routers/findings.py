from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from surveil import state
from surveil.models import Finding, Severity
from surveil.scoring import score_from_vector, severity_from_score

from ..deps import get_item, load_engagement

router = APIRouter(prefix="/api/engagements/{eng_id}/items/{item_id}/findings", tags=["findings"])


class NewFinding(BaseModel):
    title: str
    severity: Severity = Severity.MEDIUM
    description: str = ""
    evidence: str = ""
    cvss_vector: str = ""
    cwe_id: str = ""
    remediation: str = ""
    verified: bool = False


class FindingUpdate(BaseModel):
    title: str | None = None
    severity: Severity | None = None
    description: str | None = None
    evidence: str | None = None
    remediation: str | None = None
    verified: bool | None = None


@router.post("")
def add_finding(eng_id: str, item_id: str, body: NewFinding) -> Finding:
    engagement = load_engagement(eng_id)
    item = get_item(engagement, item_id)

    severity = body.severity
    cvss_score = 0.0
    if body.cvss_vector:
        cvss_score = score_from_vector(body.cvss_vector) or 0.0
        severity = Severity(severity_from_score(cvss_score))

    finding = Finding(
        checklist_item_id=item_id,
        title=body.title,
        severity=severity,
        description=body.description or body.title,
        evidence=body.evidence,
        cvss_vector=body.cvss_vector,
        cvss_score=cvss_score,
        cwe_id=body.cwe_id,
        remediation=body.remediation,
        verified=body.verified,
        tool="manual",
    )
    item.findings.append(finding)
    state.save(engagement)
    return finding


@router.patch("/{finding_id}")
def update_finding(eng_id: str, item_id: str, finding_id: str, body: FindingUpdate) -> Finding:
    engagement = load_engagement(eng_id)
    item = get_item(engagement, item_id)
    finding = next((f for f in item.findings if f.id == finding_id), None)
    if finding is None:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(finding, field, value)

    state.save(engagement)
    return finding


@router.delete("/{finding_id}")
def delete_finding(eng_id: str, item_id: str, finding_id: str) -> dict:
    engagement = load_engagement(eng_id)
    item = get_item(engagement, item_id)
    before = len(item.findings)
    item.findings = [f for f in item.findings if f.id != finding_id]
    if len(item.findings) == before:
        raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found")
    state.save(engagement)
    return {"deleted": finding_id}
