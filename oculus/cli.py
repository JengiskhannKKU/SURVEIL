"""CLI entry point for oculus."""
from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from . import __version__
from .checklist import build_checklist
from .models import Engagement, Finding, Severity
from .scoring import score_from_vector, severity_from_score

console = Console()


# ============================================================
# Root group
# ============================================================
@click.group()
@click.version_option(__version__, prog_name="oculus")
def main() -> None:
    """oculus\n
    Deterministic, OWASP WSTG checklist-driven web application
    penetration testing with structured finding management and
    professional report generation.
    """


# ============================================================
# oculus new
# ============================================================
@main.command()
@click.option("--target", "-t", required=True, help="Target hostname or IP (e.g. example.com)")
@click.option("--name",   "-n", default="",    help="Engagement name (defaults to target)")
@click.option("--notes",  "-N", default="",    help="Scope notes")
def new(target: str, name: str, notes: str) -> None:
    """Create a new engagement with the full OWASP WSTG checklist."""
    from . import state

    engagement = Engagement(
        target=target,
        name=name or target,
        scope_notes=notes,
        checklist_items=build_checklist(),
    )
    path = state.save(engagement)

    console.print(
        Panel(
            f"[bold green]✓ Engagement created[/bold green]\n\n"
            f"  ID:      [cyan]{engagement.id}[/cyan]\n"
            f"  Name:    {engagement.name}\n"
            f"  Target:  [bold]{engagement.target}[/bold]\n"
            f"  Items:   {engagement.total_items} OWASP WSTG checklist items\n"
            f"  Saved:   [dim]{path}[/dim]\n\n"
            f"[dim]Run  [bold]oculus tui[/bold]  to open the interactive checklist.[/dim]",
            title="[bold]oculus — New Engagement[/bold]",
            border_style="green",
        )
    )


# ============================================================
# oculus list
# ============================================================
@main.command("list")
def list_engagements() -> None:
    """List all saved engagements."""
    from . import state

    rows = state.list_all()
    if not rows:
        console.print("[yellow]No engagements found. Run [bold]oculus new --target <host>[/bold] to start.[/yellow]")
        return

    table = Table(
        "ID", "Name", "Target", "Created", "Progress", "Findings",
        "CRIT", "HIGH", "MED",
        box=box.ROUNDED, border_style="dim",
        title="[bold cyan]Saved Engagements[/bold cyan]",
    )
    for r in rows:
        table.add_row(
            r["id"], r["name"], r["target"], r["created_at"],
            r["progress"], str(r["findings"]),
            f"[red]{r['critical']}[/red]" if r["critical"] else "0",
            f"[orange3]{r['high']}[/orange3]" if r["high"] else "0",
            f"[yellow]{r['medium']}[/yellow]" if r["medium"] else "0",
        )
    console.print(table)


# ============================================================
# oculus tui
# ============================================================
@main.command()
@click.option("--id", "eng_id", default="", help="Engagement ID (skips the picker and opens it directly)")
def tui(eng_id: str) -> None:
    """Open the interactive TUI for an engagement.

    With no --id, shows a picker to choose among saved engagements
    (skipped automatically if there's only one).
    """
    from . import state
    from .tui import run_tui, run_engagement_picker

    if eng_id:
        try:
            engagement = state.load(eng_id)
        except FileNotFoundError:
            console.print(f"[red]Engagement '{eng_id}' not found.[/red]")
            raise SystemExit(1)
    else:
        summaries = state.list_all()
        if not summaries:
            console.print("[yellow]No engagement found. Run [bold]oculus new --target <host>[/bold] first.[/yellow]")
            raise SystemExit(1)
        if len(summaries) == 1:
            engagement = state.load(summaries[0]["id"])
            console.print(f"[dim]Opening the only saved engagement: [bold]{engagement.id}[/bold] ({engagement.name})[/dim]")
        else:
            selected_id = run_engagement_picker(summaries)
            if not selected_id:
                raise SystemExit(0)
            engagement = state.load(selected_id)

    run_tui(engagement)


# ============================================================
# oculus status
# ============================================================
@main.command()
@click.option("--id", "eng_id", default="", help="Engagement ID (defaults to latest)")
def status(eng_id: str) -> None:
    """Show checklist progress and finding summary."""
    from . import state

    if eng_id:
        try:
            engagement = state.load(eng_id)
        except FileNotFoundError:
            console.print(f"[red]Engagement '{eng_id}' not found.[/red]")
            raise SystemExit(1)
    else:
        engagement = state.load_latest()
        if engagement is None:
            console.print("[yellow]No engagement found.[/yellow]")
            raise SystemExit(1)

    sev = engagement.findings_by_severity
    console.print(
        Panel(
            f"  [bold]Target[/bold]:    {engagement.target}\n"
            f"  [bold]Progress[/bold]:  {engagement.done_items}/{engagement.total_items} items\n"
            f"  [bold]Findings[/bold]:  {engagement.total_findings} total\n"
            f"  [red]  Critical: {sev['critical']}[/red]   "
            f"[orange3]High: {sev['high']}[/orange3]   "
            f"[yellow]Medium: {sev['medium']}[/yellow]   "
            f"[cyan]Low: {sev['low']}[/cyan]   "
            f"[dim]Info: {sev['info']}[/dim]",
            title=f"[bold]{engagement.name}[/bold]  [dim]({engagement.id})[/dim]",
            border_style="cyan",
        )
    )

    # Checklist table
    table = Table(
        "ID", "Name", "Status", "Findings", "Elapsed",
        box=box.SIMPLE, show_header=True,
        header_style="bold",
    )
    status_colors = {
        "pending": "dim", "running": "yellow",
        "done": "green", "skipped": "dim", "failed": "red",
    }
    for item in engagement.checklist_items:
        col = status_colors.get(item.status.value, "")
        elapsed = f"{item.time_elapsed_seconds:.1f}s" if item.time_elapsed_seconds else "—"
        table.add_row(
            f"[dim]{item.id}[/dim]",
            item.name[:45],
            f"[{col}]{item.status.icon} {item.status.value}[/{col}]",
            str(len(item.findings)),
            elapsed,
        )
    console.print(table)


# ============================================================
# oculus report
# ============================================================
@main.command()
@click.option("--id",     "eng_id", default="",   help="Engagement ID (defaults to latest)")
@click.option("--output", "-o",     default="",   help="Output file path")
@click.option("--format", "-f",     default="md", type=click.Choice(["md", "docx"]),
              help="Report format")
def report(eng_id: str, output: str, format: str) -> None:
    """Generate a pentest report (Markdown or .docx)."""
    from . import state
    from .report import generate_markdown, generate_docx

    if eng_id:
        try:
            engagement = state.load(eng_id)
        except FileNotFoundError:
            console.print(f"[red]Engagement '{eng_id}' not found.[/red]")
            raise SystemExit(1)
    else:
        engagement = state.load_latest()
        if engagement is None:
            console.print("[yellow]No engagement found.[/yellow]")
            raise SystemExit(1)

    ext     = "docx" if format == "docx" else "md"
    out_path = Path(output) if output else Path.cwd() / f"report_{engagement.id}.{ext}"

    if format == "md":
        generate_markdown(engagement, out_path=out_path)
    else:
        generate_docx(engagement, out_path=out_path)

    console.print(
        f"[bold green]✓ Report generated:[/bold green]  [cyan]{out_path}[/cyan]\n"
        f"  Findings: {engagement.total_findings}   "
        f"Progress: {engagement.done_items}/{engagement.total_items}"
    )


# ============================================================
# oculus add-finding  (quick CLI shortcut)
# ============================================================
@main.command("add-finding")
@click.option("--id",       "eng_id",  default="",  help="Engagement ID")
@click.option("--item",     "item_id", required=True, help="Checklist item ID e.g. WSTG-INFO-02")
@click.option("--title",    "-t",      required=True)
@click.option("--severity", "-s",      default="medium",
              type=click.Choice([s.value for s in Severity]))
@click.option("--desc",     "-d",      default="")
@click.option("--cvss",     "-c",      default="")
@click.option("--cwe",                 default="")
@click.option("--remediation", "-r",   default="")
@click.option("--verified",    is_flag=True, default=False)
def add_finding(
    eng_id: str, item_id: str, title: str, severity: str,
    desc: str, cvss: str, cwe: str, remediation: str, verified: bool,
) -> None:
    """Add a finding to a checklist item from the command line."""
    from . import state

    engagement = state.load(eng_id) if eng_id else state.load_latest()
    if engagement is None:
        console.print("[red]No engagement found.[/red]")
        raise SystemExit(1)

    item = engagement.get_item(item_id)
    if item is None:
        console.print(f"[red]Item '{item_id}' not found.[/red]")
        raise SystemExit(1)

    cvss_score = 0.0
    if cvss:
        cvss_score = score_from_vector(cvss) or 0.0
        severity = severity_from_score(cvss_score)

    finding = Finding(
        checklist_item_id=item_id,
        title=title,
        severity=Severity(severity),
        description=desc or title,
        cvss_vector=cvss,
        cvss_score=cvss_score,
        cwe_id=cwe,
        remediation=remediation,
        verified=verified,
        tool="manual",
    )
    item.findings.append(finding)
    state.save(engagement)

    console.print(
        f"[bold green]✓ Finding added[/bold green]  "
        f"[cyan]{finding.id}[/cyan]  [{severity.upper()}]  {title}"
    )


# ============================================================
# oculus delete
# ============================================================
@main.command()
@click.argument("eng_ids", nargs=-1, required=True)
@click.option("--yes", "-y", is_flag=True, help="Skip the confirmation prompt")
def delete(eng_ids: tuple[str, ...], yes: bool) -> None:
    """Delete one or more engagements by ID (e.g. oculus delete abc123 def456)."""
    from . import state

    ids = list(dict.fromkeys(eng_ids))  # de-dupe, preserve order

    if not yes:
        label = f"engagement '{ids[0]}'" if len(ids) == 1 else f"{len(ids)} engagements ({', '.join(ids)})"
        if not click.confirm(f"Delete {label}?"):
            console.print("[yellow]Aborted.[/yellow]")
            raise SystemExit(0)

    deleted: list[str] = []
    missing: list[str] = []
    for eng_id in ids:
        if state.delete(eng_id):
            deleted.append(eng_id)
        else:
            missing.append(eng_id)

    if deleted:
        console.print(f"[green]Deleted {len(deleted)} engagement(s): {', '.join(deleted)}[/green]")
    if missing:
        console.print(f"[red]Not found: {', '.join(missing)}[/red]")
    if missing and not deleted:
        raise SystemExit(1)


# ============================================================
# oculus install-tools
# ============================================================
@main.command("install-tools")
def install_tools() -> None:
    """Interactively install enumeration tool binaries (not all-or-nothing).

    Shows all 16 tools with their install status; recommended ones (the
    tools auto-finding extraction understands) are pre-selected. Pick a
    subset, then installs each via the best available package manager
    (brew/apt/go/pip/gem) for this host.
    """
    from .tool_installer import run_interactive

    run_interactive(console)
