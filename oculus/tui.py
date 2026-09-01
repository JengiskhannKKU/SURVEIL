"""Textual TUI — Checklist & State Engine with interactive findings management."""
from __future__ import annotations

import shlex
import threading
from datetime import datetime
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Rule,
    Select,
    Static,
    Switch,
    Tree,
)
from textual.widgets.tree import TreeNode

from .models import ChecklistItem, Engagement, Finding, Severity, Status
from .orchestrator import Orchestrator
from .output_formatter import format_tool_line
from .scoring import score_from_vector, severity_from_score
from .report import generate_markdown
from .tools import TOOL_REGISTRY
from .wordlists import discover_wordlists


# ============================================================
# CSS
# ============================================================
APP_CSS = """
Screen {
    background: #0d1117;
}

Header {
    background: #161b22;
    color: #58a6ff;
    text-style: bold;
    border-bottom: solid #30363d;
}

Footer {
    background: #161b22;
    color: #8b949e;
    border-top: solid #30363d;
}

#body {
    height: 1fr;
}

/* ─── Sidebar ───────────────────────────────────────────── */
#sidebar {
    width: 38;
    background: #0d1117;
    border-right: solid #30363d;
    padding: 0;
}

#sidebar-title {
    background: #161b22;
    color: #58a6ff;
    text-style: bold;
    width: 100%;
    padding: 0 1;
    height: 3;
    content-align: left middle;
}

#sidebar-target {
    background: #0d1117;
    color: #3fb950;
    text-style: bold;
    padding: 1 1 0 1;
    height: 2;
}

#sidebar-progress {
    background: #0d1117;
    color: #8b949e;
    padding: 0 1;
    height: 2;
}

#sidebar-severity {
    background: #0d1117;
    padding: 0 1 1 1;
    height: auto;
}

#checklist-tree {
    background: #0d1117;
    color: #c9d1d9;
    padding: 0 0 0 0;
}

#checklist-tree > .tree--guides {
    color: #30363d;
}

#checklist-tree > .tree--cursor {
    background: #1f6feb;
    color: #ffffff;
}

/* ─── Content area ──────────────────────────────────────── */
#content {
    width: 1fr;
    background: #0d1117;
}

/* ─── Item detail panel ─────────────────────────────────── */
#detail-panel {
    height: 40%;
    border-bottom: solid #30363d;
    padding: 1 2;
    background: #0d1117;
}

#detail-title {
    color: #58a6ff;
    text-style: bold;
    height: 2;
}

#detail-meta {
    color: #8b949e;
    height: 2;
}

#detail-desc {
    color: #c9d1d9;
    height: auto;
    margin-top: 1;
}

#detail-tools-label {
    color: #3fb950;
    text-style: bold;
    height: 2;
    margin-top: 1;
}

#tool-output-log {
    height: 1fr;
    background: #010409;
    border: solid #30363d;
    margin-top: 1;
    border-title-color: #8b949e;
}

/* ─── Findings panel ────────────────────────────────────── */
#findings-panel {
    height: 60%;
    padding: 1 2;
    background: #0d1117;
}

#findings-title {
    color: #f0883e;
    text-style: bold;
    height: 2;
}

#findings-table {
    height: 1fr;
    background: #010409;
    border: solid #30363d;
}

/* ─── Action buttons ────────────────────────────────────── */
#action-bar {
    height: 3;
    align: left middle;
    padding: 0 1;
    background: #161b22;
    border-top: solid #30363d;
}

Button {
    margin: 0 1 0 0;
    min-width: 12;
}

Button.-primary   { background: #1f6feb; color: white; }
Button.-success   { background: #238636; color: white; }
Button.-warning   { background: #9e6a03; color: white; }
Button.-error     { background: #da3633; color: white; }
Button.-default   { background: #21262d; color: #c9d1d9; }

/* ─── Modals ────────────────────────────────────────────── */
ModalScreen {
    background: rgba(0,0,0,0.7);
    align: center middle;
}

#modal-box {
    background: #161b22;
    border: solid #30363d;
    width: 70;
    height: auto;
    padding: 2 3;
}

#modal-title {
    color: #58a6ff;
    text-style: bold;
    height: 3;
}

.modal-label {
    color: #8b949e;
    height: 2;
    margin-top: 1;
}

Input {
    background: #0d1117;
    border: solid #30363d;
    color: #c9d1d9;
    margin-bottom: 1;
}

Input:focus {
    border: solid #58a6ff;
}

Select {
    background: #0d1117;
    border: solid #30363d;
    margin-bottom: 1;
}

.modal-buttons {
    height: 3;
    align: right middle;
    margin-top: 1;
}

#tool-guide {
    height: auto;
    margin-top: 1;
    color: #8b949e;
}

.scan-mode-row {
    height: 3;
    align: left middle;
    margin-top: 1;
}

.scan-mode-row Switch {
    margin: 0 1;
}

#picker-hint {
    background: #161b22;
    color: #8b949e;
    padding: 1 2;
    height: 3;
}

#picker-table {
    margin: 0 2;
}

#splash {
    align: center middle;
    background: #0d1117;
}

#splash-text {
    color: #8b949e;
    text-align: center;
    width: 60;
}

#help-text {
    height: auto;
    margin-top: 1;
    margin-bottom: 1;
    color: #c9d1d9;
}

#run-tool-modal-box {
    background: #161b22;
    border: solid #30363d;
    width: 96;
    height: auto;
    max-height: 90%;
    padding: 2 3;
}

#finding-modal-box {
    background: #161b22;
    border: solid #30363d;
    width: 76;
    height: auto;
    max-height: 90%;
    padding: 2 3;
}

#finding-detail-log {
    height: auto;
    max-height: 16;
    background: #010409;
    border: solid #30363d;
    margin: 1 0;
    color: #c9d1d9;
}
"""


# ============================================================
# Modal — Add Finding
# ============================================================
class AddFindingModal(ModalScreen[Optional[Finding]]):
    """Modal dialog to add a finding to the selected checklist item."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, item_id: str):
        super().__init__()
        self._item_id = item_id

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Label("Add Finding", id="modal-title")
            yield Label("Title", classes="modal-label")
            yield Input(placeholder="e.g. Missing Content-Security-Policy header", id="inp-title")
            yield Label("Severity", classes="modal-label")
            yield Select(
                [(s.value.upper(), s.value) for s in Severity],
                value="medium",
                id="sel-severity",
            )
            yield Label("Description", classes="modal-label")
            yield Input(placeholder="Describe the finding...", id="inp-desc")
            yield Label("Evidence (optional)", classes="modal-label")
            yield Input(placeholder="Paste evidence snippet...", id="inp-evidence")
            yield Label("CVSS Vector (optional)", classes="modal-label")
            yield Input(placeholder="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N", id="inp-cvss")
            yield Label("CWE ID (optional)", classes="modal-label")
            yield Input(placeholder="CWE-200", id="inp-cwe")
            yield Label("Remediation (optional)", classes="modal-label")
            yield Input(placeholder="How to fix...", id="inp-remediation")
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Add Finding", variant="primary", id="btn-add")

    @on(Button.Pressed, "#btn-cancel")
    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#btn-add")
    def action_add(self) -> None:
        title = self.query_one("#inp-title", Input).value.strip()
        if not title:
            self.notify("Title is required.", severity="error")
            return

        sev_val  = self.query_one("#sel-severity", Select).value or "medium"
        desc     = self.query_one("#inp-desc", Input).value.strip()
        evidence = self.query_one("#inp-evidence", Input).value.strip()
        cvss_vec = self.query_one("#inp-cvss", Input).value.strip()
        cwe_id   = self.query_one("#inp-cwe", Input).value.strip()
        remediation = self.query_one("#inp-remediation", Input).value.strip()

        cvss_score = 0.0
        if cvss_vec:
            cvss_score = score_from_vector(cvss_vec) or 0.0
            if not cvss_score:
                sev_val = severity_from_score(cvss_score)

        finding = Finding(
            checklist_item_id=self._item_id,
            title=title,
            severity=Severity(sev_val),
            description=desc or title,
            evidence=evidence,
            cvss_vector=cvss_vec,
            cvss_score=cvss_score,
            cwe_id=cwe_id,
            remediation=remediation,
            verified=True,
            tool="manual",
        )
        self.dismiss(finding)


# ============================================================
# Modal — Run Tool
# ============================================================
class RunToolModal(ModalScreen[Optional[tuple[str, Optional[list[str]], bool]]]):
    """Select which tool to run for the current item, with a fast/full scan
    toggle, a per-tool guide, and an editable command line.

    Dismisses with ``(tool_name, custom_command, fast)`` — *custom_command*
    is ``None`` if the tester left the default command untouched (so the
    normal simulated-fallback behavior still applies, and *fast* picks
    which built-in variant to run), or the edited argv list if they
    changed it (which always executes for real, ignoring *fast*).
    """

    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    def __init__(self, item: ChecklistItem, target: str):
        super().__init__()
        self._item = item
        self._target = target

    def compose(self) -> ComposeResult:
        available = self._item.tools
        with VerticalScroll(id="run-tool-modal-box"):
            yield Label(f"Run Tool — {self._item.id}", id="modal-title")
            yield Label("Select a tool to execute:", classes="modal-label")
            yield Select(
                [(t, t) for t in available],
                value=available[0] if available else None,
                id="sel-tool",
            )
            yield Static("", id="tool-guide")
            with Horizontal(classes="scan-mode-row"):
                yield Label("Fast scan", classes="modal-label")
                yield Switch(value=False, id="switch-fast")
                yield Label(
                    "[dim](off = Full/thorough scan, the default; on = a quicker, narrower first pass)[/dim]",
                    classes="modal-label",
                )
            yield Label("Wordlist:", id="wordlist-label", classes="modal-label")
            yield Select([], id="sel-wordlist", allow_blank=True)
            yield Label("Command (edit before running, e.g. change flags/wordlist/timeout):", classes="modal-label")
            yield Input(id="inp-command")
            yield Label(
                "If the tool isn't installed and the command above is untouched, it "
                "runs in [bold yellow]SIMULATED[/bold yellow] mode. Editing the command "
                "always executes for real — a missing binary then shows a real error.",
                classes="modal-label",
            )
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Reset Command", variant="default", id="btn-reset-cmd")
                yield Button("Run", variant="success", id="btn-run")

    def on_mount(self) -> None:
        self._refresh_command_preview()

    def _is_fast(self) -> bool:
        return self.query_one("#switch-fast", Switch).value

    def _default_command_for(self, tool_name: str, fast: bool) -> Optional[list[str]]:
        tool_cls = TOOL_REGISTRY.get(tool_name)
        if tool_cls is None:
            return None
        return tool_cls(self._target).build_command(fast=fast)

    def _refresh_command_preview(self) -> None:
        tool_name = self.query_one("#sel-tool", Select).value
        if not tool_name:
            return
        tool_name = str(tool_name)
        tool_cls = TOOL_REGISTRY.get(tool_name)

        cmd = self._default_command_for(tool_name, self._is_fast())
        self.query_one("#inp-command", Input).value = shlex.join(cmd) if cmd else ""

        guide = self.query_one("#tool-guide", Static)
        if tool_cls and (tool_cls.description or tool_cls.example):
            guide.update(
                f"[dim]{tool_cls.description}[/dim]\n"
                f"[dim]e.g.[/dim] [cyan]{tool_cls.example}[/cyan]"
            )
        else:
            guide.update("")

        self._refresh_wordlist_row(tool_cls, cmd)

    def _current_wordlist(self, cmd: Optional[list[str]]) -> Optional[str]:
        if not cmd or "-w" not in cmd:
            return None
        idx = cmd.index("-w")
        return cmd[idx + 1] if idx + 1 < len(cmd) else None

    def _refresh_wordlist_row(self, tool_cls, cmd: Optional[list[str]]) -> None:
        uses_wordlist = bool(tool_cls and tool_cls.uses_wordlist)
        label = self.query_one("#wordlist-label", Label)
        select = self.query_one("#sel-wordlist", Select)
        label.display = uses_wordlist
        select.display = uses_wordlist
        if not uses_wordlist:
            return

        current = self._current_wordlist(cmd)
        options: list[tuple[str, str]] = []
        if current:
            options.append((f"{current}  (tool default)", current))
        for wl_label, wl_path in discover_wordlists():
            if wl_path != current:
                options.append((wl_label, wl_path))

        if not options:
            select.set_options([("(no wordlist path in command — edit manually)", "none")])
            select.value = "none"
            return

        select.set_options(options)
        select.value = current if current else options[0][1]

    @on(Select.Changed, "#sel-wordlist")
    def wordlist_changed(self) -> None:
        path = self.query_one("#sel-wordlist", Select).value
        if not path or path == "none":
            return
        cmd_input = self.query_one("#inp-command", Input)
        try:
            argv = shlex.split(cmd_input.value) if cmd_input.value.strip() else []
        except ValueError:
            return
        if "-w" in argv:
            idx = argv.index("-w")
            if idx + 1 < len(argv):
                argv[idx + 1] = str(path)
            else:
                argv.append(str(path))
        else:
            argv += ["-w", str(path)]
        cmd_input.value = shlex.join(argv)

    @on(Select.Changed, "#sel-tool")
    def tool_changed(self) -> None:
        self._refresh_command_preview()

    @on(Switch.Changed, "#switch-fast")
    def fast_toggled(self) -> None:
        self._refresh_command_preview()

    @on(Button.Pressed, "#btn-reset-cmd")
    def reset_command(self) -> None:
        self._refresh_command_preview()

    @on(Button.Pressed, "#btn-cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#btn-run")
    def run(self) -> None:
        tool_name = self.query_one("#sel-tool", Select).value
        if not tool_name:
            self.dismiss(None)
            return
        tool_name = str(tool_name)
        fast = self._is_fast()

        cmd_str = self.query_one("#inp-command", Input).value.strip()
        try:
            edited_cmd = shlex.split(cmd_str) if cmd_str else []
        except ValueError as exc:
            self.notify(f"Invalid command: {exc}", severity="error")
            return

        default_cmd = self._default_command_for(tool_name, fast) or []
        custom_command = edited_cmd if edited_cmd != default_cmd else None
        self.dismiss((tool_name, custom_command, fast))


# ============================================================
# Modal — Report preview
# ============================================================
class ReportModal(ModalScreen[None]):
    """Show the generated Markdown report."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    def __init__(self, report_text: str, out_path: str):
        super().__init__()
        self._report = report_text
        self._path   = out_path

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Label(f"Report generated → {self._path}", id="modal-title")
            log = RichLog(id="report-preview", markup=True, highlight=True)
            yield log
            yield Button("Close [ESC]", variant="default", id="btn-close")

    def on_mount(self) -> None:
        log = self.query_one("#report-preview", RichLog)
        # Show first 60 lines as preview
        preview_lines = self._report.splitlines()[:60]
        for line in preview_lines:
            log.write(line)
        if len(self._report.splitlines()) > 60:
            log.write("… (truncated — see full file)")

    @on(Button.Pressed, "#btn-close")
    def close(self) -> None:
        self.dismiss(None)


# ============================================================
# Modal — Help / Manual
# ============================================================
class HelpModal(ModalScreen[None]):
    """Show the manual guide / help."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("?", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        help_text = (
            "[bold cyan]Navigation[/bold cyan]\n"
            "  [bold]↑ / ↓[/bold]    : Navigate checklist items\n"
            "  [bold]n[/bold]      : Jump to the next pending item\n"
            "  [bold]Enter[/bold]  : (on a finding row) view detail / verify / delete\n"
            "\n"
            "[bold cyan]Actions[/bold cyan]\n"
            "  [bold]r[/bold]      : Run tool for the selected item\n"
            "  [bold]a[/bold]      : Add a manual finding\n"
            "  [bold]d[/bold]      : Mark item as Done\n"
            "  [bold]s[/bold]      : Skip item\n"
            "  [bold]u[/bold]      : Reset/unmark item to pending\n"
            "  [bold]g[/bold]      : Generate report\n"
            "  [bold]?[/bold]      : Show this help screen\n"
            "  [bold]Ctrl+Q[/bold] : Quit application\n"
            "\n"
            "[bold cyan]Findings[/bold cyan]\n"
            "  Running a tool auto-extracts findings from its output, flagged\n"
            "  [yellow]Unverified[/yellow] until you confirm them. Select a row and press\n"
            "  [bold]Enter[/bold] to view full evidence/remediation, mark it Verified,\n"
            "  or delete it as a false positive.\n"
            "\n"
            "[bold cyan]Running Tools[/bold cyan]\n"
            "  The Run Tool dialog shows what each tool does and an example\n"
            "  command, plus a [bold]Fast scan[/bold] switch (a quicker, narrower\n"
            "  first pass — fewer ports/templates/threads — vs. the default Full\n"
            "  scan). The command line itself is editable before running; leaving\n"
            "  it untouched keeps the normal simulated-fallback behavior when a\n"
            "  tool isn't installed, while editing it always executes for real.\n"
            "\n"
            "[bold cyan]Status Indicators[/bold cyan]\n"
            "  ○ [dim]Pending[/dim]   : Not started\n"
            "  ◎ [yellow]Running[/yellow]   : Tool currently executing\n"
            "  ✓ [green]Done[/green]      : Completed\n"
            "  — [dim]Skipped[/dim]   : Marked as skipped\n"
            "  ✗ [red]Failed[/red]    : Tool execution failed\n"
        )
        with Vertical(id="modal-box"):
            yield Label("Manual Guide", id="modal-title")
            yield Static(help_text, id="help-text")
            with Horizontal(classes="modal-buttons"):
                yield Button("Close [ESC]", variant="default", id="btn-close")

    @on(Button.Pressed, "#btn-close")
    def close(self) -> None:
        self.dismiss(None)


# ============================================================
# Modal — Generic yes/no confirmation
# ============================================================
class ConfirmModal(ModalScreen[bool]):
    """Generic confirm/cancel dialog. Dismisses with True (confirmed) or False."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, message: str, confirm_label: str = "Delete"):
        super().__init__()
        self._message = message
        self._confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Label("Confirm", id="modal-title")
            yield Static(self._message, classes="modal-label")
            with Horizontal(classes="modal-buttons"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button(self._confirm_label, variant="error", id="btn-confirm")

    def action_cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#btn-cancel")
    def cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#btn-confirm")
    def confirm(self) -> None:
        self.dismiss(True)


# ============================================================
# Modal — Finding detail / verify / delete
# ============================================================
class FindingDetailModal(ModalScreen[str]):
    """Show a finding's full detail with verify/dismiss/delete actions.

    Dismisses with one of: "", "verify", "unverify", "delete".
    """

    BINDINGS = [
        Binding("escape", "close",          "Close"),
        Binding("v",      "toggle_verify",  "Verify/Unverify"),
        Binding("x",      "delete_finding",  "Delete"),
    ]

    def __init__(self, finding: Finding):
        super().__init__()
        self._finding = finding

    def compose(self) -> ComposeResult:
        f = self._finding
        color = f.severity.rich_color
        verified_str = (
            "[green]✓ Verified[/green]" if f.verified else "[yellow]⚠ Unverified (tool-detected)[/yellow]"
        )
        body = (
            f"[{color}]{f.severity.badge}[/{color}]  {verified_str}\n\n"
            f"[bold]Tool:[/bold] {f.tool}    [bold]CVSS:[/bold] {f.cvss_score or '—'} "
            f"({f.cvss_vector or 'n/a'})    [bold]CWE:[/bold] {f.cwe_id or '—'}\n\n"
            f"[bold]Description[/bold]\n{f.description}\n\n"
            f"[bold]Evidence[/bold]\n{f.evidence or '(none)'}\n\n"
            f"[bold]Remediation[/bold]\n{f.remediation or '(none)'}"
        )
        with VerticalScroll(id="finding-modal-box"):
            yield Label(f.title, id="modal-title")
            log = RichLog(id="finding-detail-log", markup=True, highlight=True)
            yield log
            with Horizontal(classes="modal-buttons"):
                yield Button("Close [ESC]", variant="default", id="btn-close")
                yield Button(
                    "Mark Unverified [V]" if f.verified else "Mark Verified [V]",
                    variant="warning" if f.verified else "success",
                    id="btn-toggle-verify",
                )
                yield Button("Delete [X]", variant="error", id="btn-delete")
        self._body_text = body

    def on_mount(self) -> None:
        log = self.query_one("#finding-detail-log", RichLog)
        for line in self._body_text.splitlines():
            log.write(line)

    def action_close(self) -> None:
        self.dismiss("")

    def action_toggle_verify(self) -> None:
        self.dismiss("unverify" if self._finding.verified else "verify")

    def action_delete_finding(self) -> None:
        self.dismiss("delete")

    @on(Button.Pressed, "#btn-close")
    def close(self) -> None:
        self.action_close()

    @on(Button.Pressed, "#btn-toggle-verify")
    def toggle_verify(self) -> None:
        self.action_toggle_verify()

    @on(Button.Pressed, "#btn-delete")
    def delete(self) -> None:
        self.action_delete_finding()


# ============================================================
# Main TUI App
# ============================================================
class ChecklistApp(App[None]):
    """oculus TUI."""

    TITLE    = "oculus"
    CSS      = APP_CSS

    BINDINGS = [
        Binding("?",       "show_help",       "Help",        show=True),
        Binding("r",       "run_tool",        "Run Tool",    show=True),
        Binding("a",       "add_finding",     "Add Finding", show=True),
        Binding("d",       "mark_done",       "Mark Done",   show=True),
        Binding("s",       "mark_skip",       "Skip",        show=True),
        Binding("u",       "mark_reset",      "Reset",       show=True),
        Binding("n",       "next_pending",    "Next Pending", show=True),
        Binding("g",       "gen_report",      "Report",      show=True),
        Binding("ctrl+q",  "quit",            "Quit",        show=True),
    ]

    def __init__(self, engagement: Engagement):
        super().__init__()
        self.engagement    = engagement
        self.orchestrator  = Orchestrator(engagement)
        self._selected_id: Optional[str] = None
        self._running_ids: set[str] = set()

    # --------------------------------------------------------
    # Layout
    # --------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            # Left sidebar: Tree checklist
            with Vertical(id="sidebar"):
                yield Static(f"{self.engagement.name}", id="sidebar-title")
                yield Static(f"Target: [bold white]{self.engagement.target}[/bold white]", id="sidebar-target")
                yield Static("", id="sidebar-progress")
                yield Static("", id="sidebar-severity")
                yield Tree("OWASP WSTG", id="checklist-tree")

            # Right content
            with Vertical(id="content"):
                # Detail panel (top)
                with Vertical(id="detail-panel"):
                    yield Static("Select a checklist item", id="detail-title")
                    yield Static("", id="detail-meta")
                    yield Static("", id="detail-desc")
                    yield Static("", id="detail-tools-label")
                    log = RichLog(id="tool-output-log", markup=True, highlight=True)
                    log.border_title = "Tool Output"
                    yield log

                # Findings panel (bottom)
                with Vertical(id="findings-panel"):
                    yield Static("Findings", id="findings-title")
                    table = DataTable(id="findings-table", cursor_type="row")
                    yield table

                # Action bar
                with Horizontal(id="action-bar"):
                    yield Button("Run Tool [r]",    variant="success",  id="btn-run")
                    yield Button("Add Finding [a]", variant="primary",  id="btn-add")
                    yield Button("Done [d]",         variant="default",  id="btn-done")
                    yield Button("Skip [s]",          variant="default",  id="btn-skip")
                    yield Button("Reset [u]",         variant="default",  id="btn-reset")
                    yield Button("Report [g]",      variant="warning",  id="btn-report")

        yield Footer()

    # --------------------------------------------------------
    # Mount: populate tree and table
    # --------------------------------------------------------
    def on_mount(self) -> None:
        self._item_nodes: dict[str, TreeNode] = {}
        self._build_tree(select_first=True)
        self._init_table()
        self._update_progress()
        self.sub_title = f"Target: {self.engagement.target}  •  ID: {self.engagement.id}"

    def _build_tree(self, select_first: bool = False) -> None:
        tree = self.query_one("#checklist-tree", Tree)
        tree.root.expand()
        tree.show_root = False

        self._item_nodes = {}
        first_node = None
        first_pending_node = None

        by_cat = self.engagement.items_by_category()
        for cat, items in by_cat.items():
            done  = sum(1 for i in items if i.status in (Status.DONE, Status.SKIPPED))
            total = len(items)
            cat_node = tree.root.add(
                f"[bold cyan]{cat}[/bold cyan] [{done}/{total}]",
                expand=True,
            )
            for item in items:
                icon  = item.status.icon
                color = item.status.rich_color
                label = f"[{color}]{icon}[/{color}] [dim]{item.id}[/dim] {item.name}"
                node = cat_node.add_leaf(label, data=item.id)
                self._item_nodes[item.id] = node
                if first_node is None:
                    first_node = node
                if first_pending_node is None and item.status == Status.PENDING:
                    first_pending_node = node

        if select_first:
            target = first_pending_node or first_node
            if target is not None:
                tree.select_node(target)

    def _init_table(self) -> None:
        table = self.query_one("#findings-table", DataTable)
        table.add_columns("SEV", "TITLE", "TOOL", "CVSS", "VERIFIED", "ID")

    def _update_progress(self) -> None:
        eng  = self.engagement
        prog = self.query_one("#sidebar-progress", Static)
        prog.update(
            f" [dim]Progress: {eng.done_items}/{eng.total_items}  "
            f"Findings: {eng.total_findings}[/dim]"
        )

        sev_colors = {
            "critical": "bold red", "high": "red",
            "medium": "yellow", "low": "cyan", "info": "dim",
        }
        counts = eng.findings_by_severity
        unverified = sum(
            1 for item in eng.checklist_items for f in item.findings if not f.verified
        )
        parts = [
            f"[{sev_colors[sev]}]{sev.upper()[:4]} {n}[/{sev_colors[sev]}]"
            for sev, n in counts.items() if n
        ]
        sev_line = "  ".join(parts) if parts else "[dim]No findings yet[/dim]"
        if unverified:
            sev_line += f"   [yellow]({unverified} unverified)[/yellow]"
        self.query_one("#sidebar-severity", Static).update(f" {sev_line}")

    def _refresh_tree(self) -> None:
        tree = self.query_one("#checklist-tree", Tree)
        tree.clear()
        self._build_tree()
        self._update_progress()

    # --------------------------------------------------------
    # Tree selection
    # --------------------------------------------------------
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        item_id = event.node.data
        if not item_id:
            return
        item = self.engagement.get_item(item_id)
        if item is None:
            return
        self._selected_id = item_id
        self._show_item(item)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "findings-table":
            return
        item = self._current_item()
        if item is None:
            return
        finding_id = str(event.row_key.value)
        finding = next((f for f in item.findings if f.id == finding_id), None)
        if finding is None:
            return
        self._open_finding_detail(item, finding)

    def _show_item(self, item: ChecklistItem) -> None:
        # Title + status
        color = item.status.rich_color
        icon  = item.status.icon
        self.query_one("#detail-title", Static).update(
            f"[bold cyan]{item.id}[/bold cyan]  {item.name}  "
            f"[{color}]{icon} {item.status.value.upper()}[/{color}]"
        )
        # Meta
        elapsed = f"{item.time_elapsed_seconds:.1f}s" if item.time_elapsed_seconds else "—"
        findings_count = len(item.findings)
        self.query_one("#detail-meta", Static).update(
            f"[dim]OWASP: {item.owasp_ref}   CWE: {', '.join(item.cwe_ids) or '—'}   "
            f"Elapsed: {elapsed}   Findings: {findings_count}[/dim]"
        )
        # Description
        self.query_one("#detail-desc", Static).update(item.description)
        # Tools label
        tools_str = "  ".join(f"[green]{t}[/green]" for t in item.tools) or "[dim]none[/dim]"
        self.query_one("#detail-tools-label", Static).update(
            f"[bold]Tools:[/bold]  {tools_str}"
        )
        # Tool output log
        log = self.query_one("#tool-output-log", RichLog)
        log.clear()
        if item.tool_outputs:
            for tool_name, output in item.tool_outputs.items():
                log.write(f"[bold yellow]── {tool_name} ──────[/bold yellow]")
                for line in output.splitlines():
                    log.write(format_tool_line(line))
        else:
            log.write("[dim]No tool output yet. Press [bold]R[/bold] to run a tool.[/dim]")

        # Findings table
        self._refresh_findings_table(item)

    def _refresh_findings_table(self, item: ChecklistItem) -> None:
        table = self.query_one("#findings-table", DataTable)
        table.clear()
        sev_colors = {
            "critical": "bold red",
            "high":     "red",
            "medium":   "yellow",
            "low":      "cyan",
            "info":     "dim",
        }
        for f in item.findings:
            col = sev_colors.get(f.severity.value, "")
            sev_cell = f"[{col}]{f.severity.badge}[/{col}]"
            ver_cell = "[green]Yes[/green]" if f.verified else "[yellow]No[/yellow]"
            table.add_row(
                sev_cell,
                f.title[:55] + ("…" if len(f.title) > 55 else ""),
                f.tool,
                f"{f.cvss_score:.1f}" if f.cvss_score else "—",
                ver_cell,
                f.id,
                key=f.id,
            )

    # --------------------------------------------------------
    # Actions
    # --------------------------------------------------------
    def _current_item(self) -> Optional[ChecklistItem]:
        if not self._selected_id:
            return None
        return self.engagement.get_item(self._selected_id)

    @work()
    async def action_run_tool(self) -> None:
        item = self._current_item()
        if item is None:
            self.notify("Select a checklist item first.", severity="warning")
            return
        if not item.tools:
            self.notify("No tools configured for this item.", severity="warning")
            return
        if item.id in self._running_ids:
            self.notify(f"{item.id} already has a tool running.", severity="warning")
            return

        result = await self.push_screen_wait(RunToolModal(item, self.engagement.target))
        if not result:
            return
        tool_name, custom_command, fast = result

        self._running_ids.add(item.id)
        mode = "fast" if fast else "full"
        self.notify(f"Running {tool_name} ({mode})…", timeout=2)
        self._run_tool_worker(item, tool_name, custom_command, fast)

    @work(thread=True)
    def _run_tool_worker(
        self,
        item: ChecklistItem,
        tool_name: str,
        custom_command: Optional[list[str]] = None,
        fast: bool = False,
    ) -> None:
        log = self.query_one("#tool-output-log", RichLog)
        self.call_from_thread(log.clear)
        if custom_command:
            shown_cmd = shlex.join(custom_command)
        else:
            mode_tag = " [fast]" if fast else ""
            shown_cmd = f"{tool_name}{mode_tag} {self.engagement.target}"
        self.call_from_thread(
            log.write,
            f"[bold yellow]$ {shown_cmd}[/bold yellow]",
        )

        def on_line(line: str) -> None:
            self.call_from_thread(log.write, format_tool_line(line))

        try:
            self.orchestrator.run_tool(
                item, tool_name, on_line=on_line, custom_command=custom_command, fast=fast,
            )

            from . import state
            state.save(self.engagement)

            if self._selected_id == item.id:
                self.call_from_thread(self._show_item, item)
            self.call_from_thread(self._refresh_tree)
            self.call_from_thread(self.notify, f"{tool_name} finished.", timeout=3)
        finally:
            self._running_ids.discard(item.id)

    @work()
    async def action_add_finding(self) -> None:
        item = self._current_item()
        if item is None:
            self.notify("Select a checklist item first.", severity="warning")
            return

        finding = await self.push_screen_wait(AddFindingModal(item.id))
        if finding is None:
            return
        item.findings.append(finding)

        from . import state
        state.save(self.engagement)

        self._show_item(item)
        self._update_progress()
        self.notify(
            f"Finding '{finding.title[:40]}' added [{finding.severity.value.upper()}].",
            timeout=4,
        )

    def action_mark_done(self) -> None:
        item = self._current_item()
        if item is None:
            self.notify("Select a checklist item first.", severity="warning")
            return
        self.orchestrator.mark_done(item)
        from . import state
        state.save(self.engagement)
        self._show_item(item)
        self._refresh_tree()
        self.notify(f"{item.id} marked DONE.", timeout=2)

    def action_mark_skip(self) -> None:
        item = self._current_item()
        if item is None:
            self.notify("Select a checklist item first.", severity="warning")
            return
        self.orchestrator.mark_skipped(item)
        from . import state
        state.save(self.engagement)
        self._show_item(item)
        self._refresh_tree()
        self.notify(f"{item.id} skipped.", timeout=2)

    def action_mark_reset(self) -> None:
        item = self._current_item()
        if item is None:
            self.notify("Select a checklist item first.", severity="warning")
            return
        self.orchestrator.reset(item)
        from . import state
        state.save(self.engagement)
        self._show_item(item)
        self._refresh_tree()
        self.notify(f"{item.id} reset to pending.", timeout=2)

    def action_next_pending(self) -> None:
        items = self.engagement.checklist_items
        if not items:
            return
        start = 0
        if self._selected_id:
            for i, it in enumerate(items):
                if it.id == self._selected_id:
                    start = i + 1
                    break
        for offset in range(len(items)):
            it = items[(start + offset) % len(items)]
            if it.status == Status.PENDING:
                node = self._item_nodes.get(it.id)
                if node is not None:
                    self.query_one("#checklist-tree", Tree).select_node(node)
                return
        self.notify("No pending items remaining.", timeout=3)

    @work()
    async def _open_finding_detail(self, item: ChecklistItem, finding: Finding) -> None:
        action = await self.push_screen_wait(FindingDetailModal(finding))
        if action == "verify":
            finding.verified = True
        elif action == "unverify":
            finding.verified = False
        elif action == "delete":
            item.findings = [f for f in item.findings if f.id != finding.id]
        else:
            return

        from . import state
        state.save(self.engagement)
        self._show_item(item)
        self._update_progress()
        self.notify("Finding updated.", timeout=2)

    async def action_gen_report(self) -> None:
        from pathlib import Path
        from . import state

        out_path = Path.cwd() / f"report_{self.engagement.id}.md"
        report_text = generate_markdown(self.engagement, out_path=out_path)
        state.save(self.engagement)
        await self.push_screen(ReportModal(report_text, str(out_path)))

    async def action_show_help(self) -> None:
        await self.push_screen(HelpModal())

    # ─── Button aliases ──────────────────────────────────────
    @on(Button.Pressed, "#btn-run")
    def _btn_run(self) -> None:
        self.action_run_tool()

    @on(Button.Pressed, "#btn-add")
    def _btn_add(self) -> None:
        self.action_add_finding()

    @on(Button.Pressed, "#btn-done")
    def _btn_done(self) -> None:
        self.action_mark_done()

    @on(Button.Pressed, "#btn-skip")
    def _btn_skip(self) -> None:
        self.action_mark_skip()

    @on(Button.Pressed, "#btn-reset")
    def _btn_reset(self) -> None:
        self.action_mark_reset()

    @on(Button.Pressed, "#btn-report")
    async def _btn_report(self) -> None:
        await self.action_gen_report()


# ============================================================
# Engagement Picker — choose a saved engagement to open
# ============================================================
class EngagementPickerApp(App[Optional[str]]):
    """Standalone picker shown by `oculus tui` (no --id) when more than
    one saved engagement exists. Exits with the chosen engagement ID, or
    None if the user quit without picking one.

    Also supports deleting engagements right from the picker: Space marks/
    unmarks the row under the cursor, and X deletes all marked rows (or
    just the current row if none are marked) after a confirmation.
    """

    TITLE = "oculus — Select Engagement"
    CSS   = APP_CSS

    BINDINGS = [
        Binding("enter",   "select",        "Open",          show=True),
        Binding("space",   "toggle_mark",   "Mark/Unmark",   show=True),
        Binding("x",       "delete_marked", "Delete",        show=True),
        Binding("ctrl+q",  "quit_none",     "Quit",          show=True),
    ]

    def __init__(self, summaries: list[dict]):
        super().__init__()
        self._summaries = summaries
        self._marked: set[str] = set()
        self._mark_col = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="picker-hint")
        yield DataTable(id="picker-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#picker-table", DataTable)
        columns = table.add_columns(
            "✓", "ID", "Name", "Target", "Progress", "Findings", "Crit", "High", "Created"
        )
        self._mark_col = columns[0]
        self._populate_table()
        table.focus()
        self._update_hint()

    def _populate_table(self) -> None:
        table = self.query_one("#picker-table", DataTable)
        table.clear()
        for s in self._summaries:
            table.add_row(
                "", s["id"], s["name"], s["target"], s["progress"],
                str(s["findings"]), str(s["critical"]), str(s["high"]), s["created_at"],
                key=s["id"],
            )

    def _update_hint(self) -> None:
        hint = self.query_one("#picker-hint", Static)
        if not self._summaries:
            hint.update(" No saved engagements remain. Ctrl+Q to quit, then run 'oculus new'.")
            return
        marked_note = f"  •  {len(self._marked)} marked for deletion" if self._marked else ""
        hint.update(
            f" {len(self._summaries)} saved engagement(s) — Enter: open  •  "
            f"Space: mark/unmark  •  X: delete marked (or current row){marked_note}"
        )

    def _current_row_key(self) -> Optional[str]:
        table = self.query_one("#picker-table", DataTable)
        if not table.row_count:
            return None
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        return str(row_key.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.exit(str(event.row_key.value))

    def action_select(self) -> None:
        eng_id = self._current_row_key()
        if eng_id is not None:
            self.exit(eng_id)

    def action_toggle_mark(self) -> None:
        eng_id = self._current_row_key()
        if eng_id is None:
            return
        if eng_id in self._marked:
            self._marked.discard(eng_id)
            mark = ""
        else:
            self._marked.add(eng_id)
            mark = "[bold red]●[/bold red]"
        table = self.query_one("#picker-table", DataTable)
        table.update_cell(eng_id, self._mark_col, mark)
        self._update_hint()

    @work()
    async def action_delete_marked(self) -> None:
        ids = list(self._marked) if self._marked else [
            i for i in [self._current_row_key()] if i is not None
        ]
        if not ids:
            return

        label = f"engagement '{ids[0]}'" if len(ids) == 1 else f"{len(ids)} engagements ({', '.join(ids)})"
        confirmed = await self.push_screen_wait(
            ConfirmModal(f"Delete {label}? This cannot be undone.")
        )
        if not confirmed:
            return

        from . import state
        deleted = [eng_id for eng_id in ids if state.delete(eng_id)]

        self._summaries = [s for s in self._summaries if s["id"] not in deleted]
        self._marked -= set(deleted)
        self._populate_table()
        self._update_hint()
        self.notify(f"Deleted {len(deleted)} engagement(s).", timeout=3)

    def action_quit_none(self) -> None:
        self.exit(None)


def run_engagement_picker(summaries: list[dict]) -> Optional[str]:
    """Show the picker and return the chosen engagement ID, or None if cancelled."""
    return EngagementPickerApp(summaries).run()


# ============================================================
# Entry point
# ============================================================
def run_tui(engagement: Engagement) -> None:
    app = ChecklistApp(engagement)
    app.run()
