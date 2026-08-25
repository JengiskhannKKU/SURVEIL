"""Interactive installer for the enumeration tool binaries.

Reuses each tool wrapper's `install_hints` (surveil/tools/*_tool.py) as the
single source of truth for install commands — nothing here is duplicated
into a shell script. Lets the tester pick a subset rather than install all
18 at once, with a recommended starter set pre-selected: the 7 tools whose
output `findings_extractor.py` auto-parses into findings.
"""
from __future__ import annotations

import shutil
import subprocess

from rich import box
from rich.console import Console
from rich.table import Table

from .tools import TOOL_REGISTRY

RECOMMENDED = {"nmap", "httpx", "whatweb", "nuclei", "wafw00f", "subfinder", "nikto"}

# Preference order when a tool offers more than one install method.
_MANAGER_ORDER = ("brew", "apt", "go", "pip", "gem")
_MANAGER_BINARY = {"brew": "brew", "apt": "apt-get", "go": "go", "pip": "pip3", "gem": "gem"}


def _manager_available(key: str) -> bool:
    if key == "pip":
        return shutil.which("pip") is not None or shutil.which("pip3") is not None
    return shutil.which(_MANAGER_BINARY.get(key, key)) is not None


def _resolve_command(key: str, command: str) -> str:
    """Adapt a hint command to what's actually on PATH (e.g. pip -> pip3)."""
    if key == "pip" and shutil.which("pip") is None and shutil.which("pip3"):
        return command.replace("pip ", "pip3 ", 1)
    return command


def pick_install_command(hints: dict[str, str]) -> tuple[str, str] | None:
    """Return (manager, command) for the best install method on this host, or None."""
    for key in _MANAGER_ORDER:
        if key in hints and _manager_available(key):
            return key, _resolve_command(key, hints[key])
    return None


def run_interactive(console: Console) -> None:
    tools = []
    for name, cls in sorted(TOOL_REGISTRY.items()):
        tool = cls(target="")
        tools.append(
            {
                "name": name,
                "cls": cls,
                "available": tool.is_available(),
                "recommended": name in RECOMMENDED,
            }
        )

    selected = {t["name"] for t in tools if t["recommended"] and not t["available"]}

    def render() -> None:
        table = Table(box=box.SIMPLE, header_style="bold")
        table.add_column("#", width=3)
        table.add_column("", width=3)
        table.add_column("Tool")
        table.add_column("Status")
        table.add_column("Install via")
        for i, t in enumerate(tools, 1):
            mark = "[green]x[/green]" if t["name"] in selected else " "
            if t["available"]:
                status = "[dim]already installed[/dim]"
            else:
                status = "[yellow]not installed[/yellow]"
            choice = pick_install_command(t["cls"].install_hints)
            via = choice[0] if choice else "[dim]none for this host[/dim]"
            label = t["name"] + (" [cyan](recommended)[/cyan]" if t["recommended"] else "")
            table.add_row(str(i), f"[{mark}]", label, status, via)
        console.print(table)

    console.print(
        "[bold]surveil — tool installer[/bold]\n"
        "Recommended tools (the ones auto-finding extraction understands) are "
        "pre-selected below.\n"
        "Type numbers to toggle (e.g. [cyan]1 3 5[/cyan]), [cyan]a[/cyan]=all, "
        "[cyan]r[/cyan]=recommended only, [cyan]n[/cyan]=none, Enter to install "
        "the selection, [cyan]q[/cyan] to quit without installing.\n"
    )

    while True:
        render()
        choice = console.input("\n> ").strip().lower()
        if choice == "":
            break
        if choice == "q":
            console.print("[yellow]Aborted — nothing installed.[/yellow]")
            return
        if choice == "a":
            selected = {t["name"] for t in tools if not t["available"]}
            continue
        if choice == "r":
            selected = {t["name"] for t in tools if t["recommended"] and not t["available"]}
            continue
        if choice == "n":
            selected = set()
            continue
        for part in choice.split():
            if not part.isdigit():
                continue
            idx = int(part) - 1
            if not (0 <= idx < len(tools)):
                continue
            t = tools[idx]
            if t["available"]:
                continue
            if t["name"] in selected:
                selected.discard(t["name"])
            else:
                selected.add(t["name"])

    if not selected:
        console.print("[yellow]Nothing selected — exiting.[/yellow]")
        return

    console.print(f"\n[bold]Installing {len(selected)} tool(s)...[/bold]\n")
    results: list[tuple[str, bool]] = []
    for t in tools:
        if t["name"] not in selected:
            continue
        choice = pick_install_command(t["cls"].install_hints)
        if choice is None:
            console.print(
                f"[red]x[/red] {t['name']} — no automatic install method on this host "
                f"(needs one of: {', '.join(t['cls'].install_hints) or 'none listed'})"
            )
            results.append((t["name"], False))
            continue
        manager, command = choice
        console.print(f"[cyan]→ {t['name']}[/cyan] via {manager}: [dim]{command}[/dim]")
        proc = subprocess.run(command, shell=True)
        ok = proc.returncode == 0
        results.append((t["name"], ok))
        console.print("  [green]done[/green]\n" if ok else "  [red]failed[/red]\n")

    console.print("[bold]Summary[/bold]")
    for name, ok in results:
        console.print(f"  {'[green]✓[/green]' if ok else '[red]✗[/red]'} {name}")
