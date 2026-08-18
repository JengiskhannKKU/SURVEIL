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

# Small wordlists shipped with surveil itself, so ffuf/gobuster have a
# real, working default on any OS out of the box — their own conventional
# default (/usr/share/wordlists/dirb/common.txt) is a Kali/Debian package
# path that doesn't exist on macOS or a bare Linux box, and running either
# tool against it just fails with "no such file or directory". One per
# category recognized by recommend_wordlist() below, plus a general
# common.txt used when no category applies.
_BUNDLED_DIR = Path(__file__).parent / "data" / "wordlists"
BUNDLED_WORDLIST = _BUNDLED_DIR / "common.txt"

# Keywords used to recognize a discovered wordlist as matching a test
# category (see checklist.WORDLIST_CATEGORY) — covers common SecLists-style
# naming as well as the category name itself.
_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "admin": ("admin",),
    "api": ("api", "swagger", "endpoint", "graphql"),
    "backup": ("backup", "old-files", "old_files"),
    "extensions": ("extension", "raft-small-files", "filenames"),
    "metafiles": ("metafile", "seo"),
    "common": ("common", "raft-small-directories", "directory-list", "dirb"),
}

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


def _all_candidates() -> list[tuple[Path, Path]]:
    """(path, root) pairs for every *.txt under every search root.

    Kali's `seclists` apt package puts a full SecLists checkout at
    /usr/share/wordlists/seclists, alongside sibling tool-specific lists
    (dirb, dirbuster, wfuzz, rockyou.txt, fasttrack.txt, metasploit,
    legion, fern-wifi, dnsmap.txt, nmap.lst, sqlmap.txt, wifite.txt,
    john.lst — see `ls /usr/share/wordlists` on a real Kali box) — all
    picked up here since /usr/share/wordlists itself is a search root and
    this recurses. `*.lst` is included too since several of Kali's own
    wordlists (nmap.lst, john.lst) use that extension instead of .txt.
    """
    _extensions = (".txt", ".lst")
    seen: set[Path] = set()
    out: list[tuple[Path, Path]] = []
    for root in _search_roots():
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.suffix.lower() not in _extensions or not path.is_file() or path in seen:
                continue
            seen.add(path)
            out.append((path, root))
    return out


def _category_for(path: Path, root: Path) -> str:
    """Group a discovered wordlist the way it'd read on a real Kali box.

    A SecLists checkout (root/seclists/<Discovery|Fuzzing|Passwords|...>)
    is broken out by its own top-level folder (matches the categories seen
    running `ls /usr/share/wordlists/seclists` on Kali: Discovery, Fuzzing,
    Miscellaneous, Passwords, Pattern-Matching, Payloads, Usernames,
    Web-Shells). Everything else groups by the first path segment under its
    search root (dirb, dirbuster, wfuzz, ...), or "Other" for a file sitting
    directly in the root (rockyou.txt, fasttrack.txt, ...).
    """
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return "Other"
    if not parts:
        return "Other"
    if parts[0].lower() == "seclists" and len(parts) > 2:
        return f"SecLists/{parts[1]}"
    if parts[0].lower() == "seclists":
        return "SecLists"
    if len(parts) > 1:
        return parts[0]
    return "Other"


def discover_wordlists(limit: int = 500) -> list[tuple[str, str]]:
    """Return (label, path) pairs for wordlists found on this host.

    Scans SURVEIL_WORDLIST_DIR/the configured Settings-dialog directory (if
    set) plus a fixed, shallow set of common install directories (no
    exhaustive filesystem walk) — see `_SEARCH_ROOTS`. Directory/file
    brute-force-relevant wordlists (see `_DIR_BRUTEFORCE_KEYWORDS`) sort
    first, alphabetically after that, so a bounded limit still surfaces the
    wordlists actually useful for ffuf/gobuster first. Does not include the
    bundled fallback wordlist — that's only used by `default_wordlist()`
    when nothing else is found.
    """
    candidates = sorted(_all_candidates(), key=lambda pr: (_priority(pr[0]), str(pr[0])))
    found: list[tuple[str, str]] = []
    for path, root in candidates[:limit]:
        try:
            label = str(path.relative_to(root.parent))
        except ValueError:
            label = str(path)
        found.append((label, str(path)))
    return found


def discover_wordlists_grouped(recommended_category: str | None = None) -> list[dict]:
    """Every wordlist found on this host, grouped the way a tester browsing
    /usr/share/wordlists by hand would see it (see `_category_for`).

    Each group is `{"category": str, "recommended": bool, "wordlists":
    [{"label": str, "path": str}]}`, sorted with the group matching
    *recommended_category* (if any) first, then alphabetically. Wordlists
    within a group are alphabetical by label. Used by the frontend's
    "Select wordlist" card dialog — unlike `discover_wordlists()`, nothing
    here is capped by _DIR_BRUTEFORCE_KEYWORDS priority, so password lists,
    username lists, etc. are just as reachable as directory-brute-force ones.
    """
    groups: dict[str, list[tuple[str, str]]] = {}
    for path, root in _all_candidates():
        category = _category_for(path, root)
        try:
            label = str(path.relative_to(root.parent))
        except ValueError:
            label = str(path)
        groups.setdefault(category, []).append((label, str(path)))

    # Always offer surveil's own bundled wordlists too (see WORDLIST_CATEGORY
    # in checklist.py) — the only wordlists guaranteed to exist on a machine
    # with no Kali/SecLists install (e.g. this dev laptop), so the dialog is
    # never empty.
    bundled = sorted(p for p in _BUNDLED_DIR.glob("*.txt") if p.is_file())
    if bundled:
        groups["Bundled (built-in)"] = [(p.name, str(p)) for p in bundled]

    keywords = _CATEGORY_KEYWORDS.get(recommended_category or "", (recommended_category or "",))
    bundled_match = recommended_category and (_BUNDLED_DIR / f"{recommended_category}.txt").is_file()

    def group_is_recommended(category: str, wordlists: list[tuple[str, str]]) -> bool:
        if recommended_category is None:
            return False
        if category.lower() in {kw.lower() for kw in keywords}:
            return True
        if category == "Bundled (built-in)" and bundled_match:
            return True
        # a category name alone (e.g. "SecLists/Discovery") is too broad to
        # match keywords like "admin" — also check whether any wordlist
        # *within* the group does (e.g. .../Discovery/Web-Content/admin-panels.txt)
        return any(any(kw in path.lower() for kw in keywords) for _label, path in wordlists)

    def sort_key(category: str) -> tuple[int, str]:
        is_recommended = group_is_recommended(category, groups.get(category, []))
        return (0 if is_recommended else 1, category)

    result = []
    for category in sorted(groups, key=sort_key):
        wordlists = sorted(groups[category], key=lambda lp: lp[0])
        result.append({
            "category": category,
            "recommended": sort_key(category)[0] == 0,
            "wordlists": [{"label": label, "path": path} for label, path in wordlists],
        })
    return result


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


def recommend_wordlist(category: str | None) -> str:
    """Best wordlist for a specific test category (checklist.WORDLIST_CATEGORY).

    Order: a discovered wordlist whose path matches the category's
    keywords (_CATEGORY_KEYWORDS) -> a category-specific wordlist bundled
    with surveil -> the general default_wordlist(). *category* being None
    or unrecognized (e.g. a custom tester-added checklist item) just falls
    straight through to default_wordlist().
    """
    if not category:
        return default_wordlist()

    keywords = _CATEGORY_KEYWORDS.get(category, (category,))
    for _label, path in discover_wordlists():
        lower = path.lower()
        if any(kw in lower for kw in keywords):
            return path

    bundled = _BUNDLED_DIR / f"{category}.txt"
    if bundled.is_file():
        return str(bundled)

    return default_wordlist()
