"""Discover wordlist files on the host for wordlist-based tools (ffuf, gobuster, ...)."""
from __future__ import annotations

import os
from pathlib import Path

from . import config as _config

# Point this at your own wordlist directory (a SecLists checkout, a
# company-internal list, whatever) to have it searched first, ahead of the
# common install locations below, and used as the default for ffuf/gobuster
# instead of whatever those tools' hardcoded defaults assume. Accepts a
# directory (searched recursively for *.txt) or a single file path.
# The web UI's Settings dialog sets this persistently (~/.surveil/
# config.json, see surveil/config.py) instead, which takes priority over
# this env var if both are set.
WORDLIST_DIR_ENV = "SURVEIL_WORDLIST_DIR"

# Common locations across Kali/Debian (dirb/seclists packages), Homebrew,
# and manual SecLists checkouts. Most dev machines will have none of
# these — that's fine, the caller falls back to the bundled wordlist below.
_SEARCH_ROOTS = [
    Path("/usr/share/wordlists"),
    Path("/usr/share/seclists"),
    Path("/opt/homebrew/share/wordlists"),
    Path("/opt/homebrew/share/seclists"),
    Path.home() / "wordlists",
    Path.home() / "SecLists",
    Path.home() / ".local/share/wordlists",
]

# Small wordlist shipped with surveil itself, so ffuf/gobuster have a real,
# working default on any OS out of the box — their own conventional default
# (/usr/share/wordlists/dirb/common.txt) is a Kali/Debian package path that
# doesn't exist on macOS or a bare Linux box, and running either tool
# against it just fails with "no such file or directory".
BUNDLED_WORDLIST = Path(__file__).parent / "data" / "wordlists" / "common.txt"

# A real SecLists checkout (what Kali's `seclists` package installs, and
# what most manual setups use) has 50+ categories — Passwords, Usernames,
# Fuzzing, Discovery/DNS, Discovery/Web-Content, etc. — with plain
# alphabetical sorting, "Discovery/DNS" and "Discovery/Infrastructure"
# sort ahead of "Discovery/Web-Content", the one actually relevant to
# ffuf/gobuster's directory/file brute-forcing. A small, fixed result cap
# combined with pure alphabetical order meant the picker filled up with
# DNS/infrastructure wordlists before ever reaching Web-Content. These
# keywords bump anything path-matching them to the front instead.
_DIR_BRUTEFORCE_KEYWORDS = (
    "web-content", "webcontent", "discovery",
    "dirb", "dirbuster", "raft", "directory-list", "common.txt",
)


def _priority(path: Path) -> int:
    lower = str(path).lower()
    for i, kw in enumerate(_DIR_BRUTEFORCE_KEYWORDS):
        if kw in lower:
            return i
    return len(_DIR_BRUTEFORCE_KEYWORDS)


def _configured_root() -> Path | None:
    value = _config.get_wordlist_dir() or os.environ.get(WORDLIST_DIR_ENV)
    return Path(value) if value else None


def _search_roots() -> list[Path]:
    configured = _configured_root()
    return ([configured] if configured else []) + _SEARCH_ROOTS


def discover_wordlists(limit: int = 150) -> list[tuple[str, str]]:
    """Return (label, path) pairs for .txt wordlists found on this host.

    Scans SURVEIL_WORDLIST_DIR/the configured Settings-dialog directory (if
    set) plus a fixed, shallow set of common install directories (no
    exhaustive filesystem walk). Within each root, directory/file
    brute-force-relevant wordlists (see _DIR_BRUTEFORCE_KEYWORDS) are
    returned first, alphabetically after that — so a bounded limit still
    surfaces the wordlists actually useful for ffuf/gobuster on a large
    real install (e.g. Kali's SecLists package) instead of getting cut off
    partway through an unrelated category. Does not include the bundled
    fallback wordlist — that's only used by default_wordlist() when
    nothing else is found.
    """
    found: list[tuple[str, str]] = []
    for root in _search_roots():
        if not root.is_dir():
            continue
        candidates = sorted(
            (p for p in root.rglob("*.txt") if p.is_file()),
            key=lambda p: (_priority(p), str(p)),
        )
        for path in candidates:
            try:
                label = str(path.relative_to(root.parent))
            except ValueError:
                label = str(path)
            found.append((label, str(path)))
            if len(found) >= limit:
                return found
    return found


def default_wordlist() -> str:
    """Best available default wordlist path for tools that need one.

    Order: the persisted config (~/.surveil/config.json, set via the web
    UI's Settings dialog) or SURVEIL_WORDLIST_DIR env var — whichever is
    set, config wins if both are (used directly if it's a file, or the
    first .txt found under it if it's a directory) -> first wordlist
    discovered in the common install locations -> the wordlist bundled
    with surveil, which always exists regardless of host/OS.
    """
    configured = _configured_root()
    if configured:
        if configured.is_file():
            return str(configured)
        if configured.is_dir():
            hits = sorted(
                (p for p in configured.rglob("*.txt") if p.is_file()),
                key=lambda p: (_priority(p), str(p)),
            )
            if hits:
                return str(hits[0])

    discovered = discover_wordlists(limit=1)
    if discovered:
        return discovered[0][1]

    return str(BUNDLED_WORDLIST)
