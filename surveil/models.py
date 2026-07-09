"""surveil — Data models."""
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


class Engagement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    target: str
    scope_notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    checklist_items: list[ChecklistItem] = []

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
