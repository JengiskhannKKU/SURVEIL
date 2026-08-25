"""Browse and selectively download individual wordlist files from
https://github.com/danielmiessler/SecLists without cloning the whole
repository (multiple GB — `git clone`-ing it just to use two wordlists is
wasteful, and not everyone wants that much disk committed to it).

Two operations:
  - `list_remote_wordlists()` — one GitHub API call to list every file in
    the repo (cached to disk for a day; unauthenticated API calls are
    rate-limited to 60/hour, and the tree barely changes hour to hour).
  - `download_wordlist(path)` — fetches exactly that one file's raw
    content and saves it under `CACHE_DIR`, mirroring the repo's own
    directory structure, so it also shows up in the normal local wordlist
    discovery/grouping (`surveil/wordlists.py`) once downloaded.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

GITHUB_API_TREE_URL = (
    "https://api.github.com/repos/danielmiessler/SecLists/git/trees/master?recursive=1"
)
RAW_BASE_URL = "https://raw.githubusercontent.com/danielmiessler/SecLists/master/"

# Downloaded files land here, mirroring the repo's own path structure
# (e.g. CACHE_DIR/Discovery/Web-Content/common.txt) — kept separate from
# surveil's bundled wordlists (surveil/data/wordlists) and registered as a
# surveil/wordlists.py search root, so a file downloaded here is
# immediately usable everywhere the local wordlist picker already looks.
CACHE_DIR = Path.home() / ".surveil" / "wordlists" / "seclists"

_TREE_CACHE_PATH = CACHE_DIR.parent / "seclists_tree_cache.json"
_TREE_CACHE_TTL_SECONDS = 24 * 3600
_USER_AGENT = "surveil-wordlist-browser"


class RemoteFetchError(RuntimeError):
    """Network/API failure talking to GitHub — distinct from a programming
    error so callers (the backend route) can turn it into a clean 502
    instead of a 500 traceback."""


def _fetch_json(url: str, timeout: int) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        raise RemoteFetchError(f"Could not reach GitHub: {exc}") from exc


def list_remote_wordlists(force_refresh: bool = False) -> list[dict]:
    """Every *.txt file in the SecLists repo, as [{"path", "category", "size"}, ...].

    *category* is the top-level folder (Discovery, Fuzzing, Passwords,
    Usernames, Pattern-Matching, Payloads, Web-Shells, Miscellaneous —
    matching what `ls` on the repo itself shows), so the picker can group
    these the same way it groups a real local SecLists checkout.
    """
    if not force_refresh and _TREE_CACHE_PATH.is_file():
        try:
            cached = json.loads(_TREE_CACHE_PATH.read_text())
            if time.time() - cached.get("fetched_at", 0) < _TREE_CACHE_TTL_SECONDS:
                return cached["files"]
        except (json.JSONDecodeError, OSError, KeyError):
            pass  # corrupt/unreadable cache — just refetch below

    data = _fetch_json(GITHUB_API_TREE_URL, timeout=30)
    if data.get("truncated"):
        # SecLists has ~5-6k files; GitHub's tree API truncates past 100k
        # entries/7MB of response, well above that — this should never
        # trip, but if the repo ever grows into it, better a visible flag
        # than a silently incomplete list.
        pass

    files = []
    for entry in data.get("tree", []):
        path = entry.get("path", "")
        if entry.get("type") != "blob" or not path.endswith(".txt"):
            continue
        parts = path.split("/")
        category = parts[0] if len(parts) > 1 else "Other"
        files.append({"path": path, "category": category, "size": entry.get("size", 0)})

    CACHE_DIR.parent.mkdir(parents=True, exist_ok=True)
    _TREE_CACHE_PATH.write_text(json.dumps({"fetched_at": time.time(), "files": files}))
    return files


def local_cache_path(remote_path: str) -> Path:
    return CACHE_DIR / remote_path


def is_downloaded(remote_path: str) -> bool:
    return local_cache_path(remote_path).is_file()


def download_wordlist(remote_path: str) -> str:
    """Download exactly one file from SecLists (not the whole repo).

    No-ops (just returns the existing path) if already cached from a
    previous download. Returns the local absolute path, ready to pass
    straight to a tool's -w flag.
    """
    dest = local_cache_path(remote_path)
    if dest.is_file():
        return str(dest)

    # remote_path ultimately comes from a request query param a tester
    # could hand-edit — refuse anything that would escape CACHE_DIR.
    normalized = Path(remote_path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValueError(f"Invalid wordlist path: {remote_path}")

    url = RAW_BASE_URL + remote_path
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        raise RemoteFetchError(f"Could not download {remote_path}: {exc}") from exc

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    return str(dest)
