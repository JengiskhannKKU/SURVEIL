from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from oculus import state
from oculus.models import Engagement, ManualPortEntry

from ..deps import load_engagement

router = APIRouter(prefix="/api/engagements/{eng_id}/ports", tags=["ports"])


class NewManualPort(BaseModel):
    port: int
    protocol: str = "tcp"
    service: str = ""
    note: str = ""


class PortRef(BaseModel):
    port: int
    protocol: str = "tcp"


def _key(port: int, protocol: str) -> str:
    return f"{port}/{protocol}"


@router.post("")
def add_manual_port(eng_id: str, body: NewManualPort) -> Engagement:
    engagement = load_engagement(eng_id)
    key = _key(body.port, body.protocol)
    # Upsert, same reasoning as add_manual_path().
    engagement.manual_ports = [
        p for p in engagement.manual_ports if _key(p.port, p.protocol) != key
    ]
    engagement.manual_ports.append(
        ManualPortEntry(port=body.port, protocol=body.protocol, service=body.service, note=body.note)
    )
    engagement.removed_ports = [p for p in engagement.removed_ports if p != key]
    state.save(engagement)
    return engagement


@router.post("/remove")
def remove_port(eng_id: str, body: PortRef) -> Engagement:
    """Removes a port from the summary. A manual entry is deleted outright;
    an auto-discovered one (parsed from nmap/naabu's raw output, which this
    app never mutates) is hidden via `removed_ports` instead."""
    engagement = load_engagement(eng_id)
    key = _key(body.port, body.protocol)
    was_manual = any(_key(p.port, p.protocol) == key for p in engagement.manual_ports)
    if was_manual:
        engagement.manual_ports = [
            p for p in engagement.manual_ports if _key(p.port, p.protocol) != key
        ]
    elif key not in engagement.removed_ports:
        engagement.removed_ports.append(key)
    state.save(engagement)
    return engagement


@router.post("/restore")
def restore_port(eng_id: str, body: PortRef) -> Engagement:
    """Un-hides a previously-removed auto-discovered port."""
    engagement = load_engagement(eng_id)
    key = _key(body.port, body.protocol)
    engagement.removed_ports = [p for p in engagement.removed_ports if p != key]
    state.save(engagement)
    return engagement
