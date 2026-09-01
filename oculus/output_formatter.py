"""Line-level highlighting for raw tool output shown in the TUI.

Recognizes common patterns across the 16 tool wrappers (HTTP status
codes, nuclei-style severity tags, +/-/warning markers, URLs, CVE IDs,
the SIMULATED banner) and wraps them in Rich markup. Everything else is
escaped so literal brackets in tool output (e.g. ffuf's
``[Status: 200, Size: 1245, ...]``) can never be misread as markup tags.
"""
from __future__ import annotations

import re
from rich.markup import escape

_SEVERITY_COLORS = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "cyan",
    "info": "dim",
}

_TOKEN_RE = re.compile(
    r"(?P<url>https?://\S+)"
    r"|\[(?P<bstatus>\d{3})\]"
    r"|Status:\s*(?P<lstatus>\d{3})"
    r"|\[(?P<sev>critical|high|medium|low|info)\]"
    r"|(?P<cve>CVE-\d{4}-\d{4,7})"
    r"|(?P<bplus>\[\+\])"
    r"|(?P<bminus>\[\-\])"
    r"|(?P<lineplus>^\+(?=\s))"
    r"|(?P<warn>⚠)",
    re.IGNORECASE,
)


def _status_color(code: str) -> str:
    n = int(code)
    if 200 <= n < 300:
        return "green"
    if 300 <= n < 400:
        return "yellow"
    if 400 <= n < 500:
        return "red"
    if n >= 500:
        return "bold red"
    return "white"


def format_tool_line(line: str) -> str:
    """Return *line* as Rich markup with recognized patterns highlighted."""
    out: list[str] = []
    pos = 0
    for m in _TOKEN_RE.finditer(line):
        if m.start() > pos:
            out.append(escape(line[pos:m.start()]))
        text = escape(m.group(0))

        if m.group("url"):
            out.append(f"[cyan]{text}[/cyan]")
        elif m.group("bstatus"):
            color = _status_color(m.group("bstatus"))
            out.append(f"[{color}]{text}[/{color}]")
        elif m.group("lstatus"):
            color = _status_color(m.group("lstatus"))
            out.append(f"[{color}]{text}[/{color}]")
        elif m.group("sev"):
            color = _SEVERITY_COLORS.get(m.group("sev").lower(), "")
            out.append(f"[{color}]{text}[/{color}]" if color else text)
        elif m.group("cve"):
            out.append(f"[bold magenta]{text}[/bold magenta]")
        elif m.group("bplus") or m.group("lineplus"):
            out.append(f"[green]{text}[/green]")
        elif m.group("bminus"):
            out.append(f"[red]{text}[/red]")
        elif m.group("warn"):
            out.append(f"[yellow]{text}[/yellow]")
        else:
            out.append(text)
        pos = m.end()

    if pos < len(line):
        out.append(escape(line[pos:]))

    result = "".join(out)
    if "SIMULATED" in line.upper():
        result = f"[bold yellow]{result}[/bold yellow]"
    return result
