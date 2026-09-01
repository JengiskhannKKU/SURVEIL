"""oculus — Data models."""
from __future__ import annotations

import math
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Status(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE    = "done"
    SKIPPED = "skipped"
    FAILED  = "failed"

    @property
    def icon(self) -> str:
        return {"pending": "○", "running": "◎", "done": "✓",
                "skipped": "—", "failed": "✗"}[self.value]

    @property
    def rich_color(self) -> str:
        return {"pending": "dim", "running": "yellow", "done": "green",
                "skipped": "dim", "failed": "red"}[self.value]


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"

    @property
    def rich_color(self) -> str:
        return {"critical": "bold red", "high": "red", "medium": "yellow",
                "low": "cyan", "info": "dim"}[self.value]

    @property
    def badge(self) -> str:
        return {"critical": "CRIT", "high": "HIGH", "medium": "MED ",
                "low": "LOW ", "info": "INFO"}[self.value]


# ---------------------------------------------------------------------------
# Core data models
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    checklist_item_id: str
    title: str
    severity: Severity
    description: str
    evidence: str = ""
    raw_output: str = ""
    owasp_category: str = ""
    cwe_id: str = ""
    cvss_vector: str = ""
    cvss_score: float = 0.0
    verified: bool = False
    remediation: str = ""
    tool: str = "manual"
    created_at: datetime = Field(default_factory=datetime.now)


class ChecklistItem(BaseModel):
    id: str                          # e.g. "WSTG-INFO-02"
    name: str
    description: str
    category: str                    # Human-readable e.g. "Information Gathering"
    category_code: str               # Short code e.g. "INFO"
    tools: list[str] = []
    references: list[str] = []
    status: Status = Status.PENDING
    findings: list[Finding] = []
    tool_outputs: dict[str, str] = {}   # tool_name -> raw stdout
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    time_elapsed_seconds: Optional[float] = None
    owasp_ref: str = ""
    cwe_ids: list[str] = []
    notes: str = ""


class ManualPathEntry(BaseModel):
    """A path/endpoint a tester adds by hand to the engagement-wide Paths/
    Endpoints tree (see entry 41's aggregation), for something found
    outside an auto-run tool — manual testing, a report from someone
    else, a path noticed in a screenshot. Distinct from the tool-parsed
    entries in ChecklistItem.tool_outputs, which are never mutated."""
    path: str
    status: Optional[int] = None
    note: str = ""
    added_at: datetime = Field(default_factory=datetime.now)


class ManualPortEntry(BaseModel):
    """A port a tester adds by hand to the engagement-wide Ports summary —
    same rationale as ManualPathEntry, for a port found outside an
    auto-run tool (nmap/naabu)."""
    port: int
    protocol: str = "tcp"
    service: str = ""
    note: str = ""
    added_at: datetime = Field(default_factory=datetime.now)


class Engagement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    target: str
    # Key into frontend/src/lib/engagementIcons.tsx's fixed icon set — a
    # free-text field would need sanitizing wherever it's rendered, and a
    # curated set (web/api/mobile/cloud/...) covers what a pentest target
    # actually is far better than an arbitrary icon library would anyway.
    icon: str = "web"
    # Testing strategy/methodology tag chosen at creation (see
    # frontend/src/lib/methodologies.ts) — "wstg" (default), "oscp", or
    # "other". Every option currently builds the same real OWASP WSTG
    # checklist below (checklist.build_checklist()); this is a tag for
    # now, not yet a different checklist generator — a genuine distinct
    # OSCP-style checklist needs its own properly-sourced content, not a
    # guessed one, and is a deliberate follow-up rather than part of this
    # change.
    methodology: str = "wstg"
    scope_notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    checklist_items: list[ChecklistItem] = []
    # Paths/Endpoints tree (entry 41) additions — manually added entries,
    # plus a hide-list for auto-discovered paths a tester wants gone from
    # the tree (a false positive, an irrelevant static asset, ...). Can't
    # actually edit the underlying tool_outputs text a path was parsed
    # from, so "removing" an auto-discovered path just hides it here
    # instead — see paths.py's remove_path().
    manual_paths: list[ManualPathEntry] = []
    removed_paths: list[str] = []
    # Same pattern as manual_paths/removed_paths, for the Ports summary —
    # removed_ports keys are "port/protocol" strings (e.g. "3306/tcp") to
    # disambiguate the rare case of the same port number open on both
    # tcp and udp.
    manual_ports: list[ManualPortEntry] = []
    removed_ports: list[str] = []

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------
    @property
    def total_items(self) -> int:
        return len(self.checklist_items)

    @property
    def done_items(self) -> int:
        return sum(1 for i in self.checklist_items
                   if i.status in (Status.DONE, Status.SKIPPED))

    @property
    def total_findings(self) -> int:
        return sum(len(i.findings) for i in self.checklist_items)

    @property
    def findings_by_severity(self) -> dict[str, int]:
        counts: dict[str, int] = {s.value: 0 for s in Severity}
        for item in self.checklist_items:
            for f in item.findings:
                counts[f.severity.value] += 1
        return counts

    def get_item(self, item_id: str) -> Optional[ChecklistItem]:
        for item in self.checklist_items:
            if item.id == item_id:
                return item
        return None

    def items_by_category(self) -> dict[str, list[ChecklistItem]]:
        result: dict[str, list[ChecklistItem]] = {}
        for item in self.checklist_items:
            result.setdefault(item.category, []).append(item)
        return result
