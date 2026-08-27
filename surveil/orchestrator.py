"""Tool Orchestration Layer — runs tool wrappers and updates checklist state."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Callable, Optional

from .checklist import apply_tool_overrides
from .findings_extractor import extract_findings
from .models import ChecklistItem, Engagement, Status
from .tools import TOOL_REGISTRY
from .tools.base import ToolResult


class Orchestrator:
    """Co-ordinates tool execution for a checklist item."""

    def __init__(self, engagement: Engagement):
        self.engagement = engagement

    def run_tool(
        self,
        item: ChecklistItem,
        tool_name: str,
        on_line: Callable[[str], None] | None = None,
        custom_command: list[str] | None = None,
        fast: bool = False,
    ) -> ToolResult:
        """
        Execute *tool_name* against the engagement target.

        - Sets item status to RUNNING before execution.
        - Stores raw output in item.tool_outputs[tool_name].
        - Sets item status to DONE on success, FAILED on error.
        - Records elapsed time.
        - If *custom_command* is given, it replaces the tool's default
          command line and always executes for real (see BaseTool.run).
        - Otherwise the tool's Fast/Full command is used, with this item's
          recommended wordlist category / nuclei tags / curl-wget override
          swapped in via apply_tool_overrides() — the same swap the Run
          Tool dialog's preview applies, so it actually takes effect on a
          real run instead of only affecting the previewed text.
        """
        tool_cls = TOOL_REGISTRY.get(tool_name)
        if tool_cls is None:
            raise ValueError(f"Unknown tool: {tool_name!r}")

        item.status = Status.RUNNING
        item.started_at = item.started_at or datetime.now()

        tool = tool_cls(self.engagement.target)
        default_command = None
        if custom_command is None:
            default_command = apply_tool_overrides(
                tool_name, item.id, tool.build_command(fast=fast), uses_wordlist=tool_cls.uses_wordlist
            )
        result = tool.run(
            on_line=on_line, override_command=custom_command, default_command=default_command, fast=fast
        )

        item.tool_outputs[tool_name] = result.output
        item.time_elapsed_seconds = (
            (item.time_elapsed_seconds or 0) + result.elapsed_seconds
        )

        # Re-running a tool replaces its still-unverified auto findings so
        # results don't pile up on repeat scans; anything the tester has
        # already verified is left alone.
        item.findings = [
            f for f in item.findings if not (f.tool == tool_name and not f.verified)
        ]
        item.findings.extend(extract_findings(tool_name, item.id, result.output))

        if result.success:
            item.status = Status.DONE
            item.completed_at = datetime.now()
        else:
            item.status = Status.FAILED

        return result

    def run_all_tools(
        self,
        item: ChecklistItem,
        on_line: Callable[[str], None] | None = None,
    ) -> list[ToolResult]:
        """Run every tool associated with *item* that has a wrapper registered."""
        results: list[ToolResult] = []
        available = [t for t in item.tools if t in TOOL_REGISTRY]
        for tool_name in available:
            result = self.run_tool(item, tool_name, on_line=on_line)
            results.append(result)
        # If no tools have wrappers, mark as done anyway so user can add manual findings
        if not available:
            item.status = Status.DONE
            item.completed_at = datetime.now()
        return results

    def mark_done(self, item: ChecklistItem) -> None:
        item.status = Status.DONE
        item.completed_at = item.completed_at or datetime.now()

    def mark_skipped(self, item: ChecklistItem) -> None:
        item.status = Status.SKIPPED
        item.completed_at = datetime.now()

    def reset(self, item: ChecklistItem) -> None:
        item.status = Status.PENDING
        item.started_at = None
        item.completed_at = None
        item.time_elapsed_seconds = None
        item.tool_outputs.clear()
