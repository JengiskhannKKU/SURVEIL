"""Discover wordlist files on the host for wordlist-based tools (ffuf, gobuster, ...)."""
from __future__ import annotations

from pathlib import Path

# Common locations across Kali/Debian (dirb/seclists packages), Homebrew,
# and manual SecLists checkouts. Most dev machines will have none of
# these — that's fine, the caller falls back to the tool's own default.
_SEARCH_ROOTS = [
    Path("/usr/share/wordlists"),
    Path("/usr/share/seclists"),
    Path("/opt/homebrew/share/wordlists"),
    Path("/opt/homebrew/share/seclists"),
    Path.home() / "wordlists",
    Path.home() / "SecLists",
    Path.home() / ".local/share/wordlists",
]


def discover_wordlists(limit: int = 25) -> list[tuple[str, str]]:
    """Return (label, path) pairs for .txt wordlists found on this host.

    Scans a fixed, shallow set of common install directories (no
    exhaustive filesystem walk) and returns real files sorted by path.
    """
    found: list[tuple[str, str]] = []
    for root in _SEARCH_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.txt")):
            if not path.is_file():
                continue
            try:
                label = str(path.relative_to(root.parent))
            except ValueError:
                label = str(path)
            found.append((label, str(path)))
            if len(found) >= limit:
                return found
    return found
