from __future__ import annotations

from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from surveil import seclists_remote
from surveil.checklist import (
    CATEGORY_LABELS,
    NUCLEI_TAGS,
    WORDLIST_CATEGORY,
    apply_tool_overrides,
)
from surveil.tools import TOOL_REGISTRY
from surveil.wordlists import (
    CATEGORY_KEYWORDS,
    discover_wordlists,
    discover_wordlists_grouped,
)

router = APIRouter(prefix="/api/tools", tags=["tools"])


class DownloadWordlistRequest(BaseModel):
    path: str  # repo-relative path, e.g. "Discovery/Web-Content/common.txt"


@router.get("")
def list_tools() -> list[dict]:
    return [
        {
            "name": name,
            "description": cls.description,
            "example": cls.example,
            "uses_wordlist": cls.uses_wordlist,
            "available": cls(target="").is_available(),
            "install_hints": cls.install_hints,
            "modes": cls.modes,
            "domain_only": cls.domain_only,
            "help_flag": cls.help_flag,
        }
        for name, cls in sorted(TOOL_REGISTRY.items())
    ]


@router.get("/{tool_name}/command")
def preview_command(
    tool_name: str,
    target: str,
    fast: bool = False,
    mode: Optional[str] = None,
    item_id: Optional[str] = None,
) -> dict:
    tool_cls = TOOL_REGISTRY.get(tool_name)
    if tool_cls is None:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")
    tool = tool_cls(target)
    if mode is not None:
        if mode not in tool_cls.modes and mode not in ("quick", "full"):
            raise HTTPException(status_code=400, detail=f"Unknown mode '{mode}' for {tool_name}")
        command = tool.build_command_for_mode(mode)
    else:
        command = tool.build_command(fast=fast)

    # Metadata for the two UI hints (recommended wordlist / nuclei tags) —
    # cheap dict lookups, computed here regardless of tool so the response
    # can report them even when null.
    category = WORDLIST_CATEGORY.get(item_id or "") if tool_cls.uses_wordlist else None
    nuclei_tags = NUCLEI_TAGS.get(item_id or "") if tool_name == "nuclei" else None

    # The actual command swap (wordlist category / nuclei tags / curl-wget
    # overrides) lives in surveil.checklist.apply_tool_overrides() — shared
    # with the real execution path (surveil.orchestrator.Orchestrator) so a
    # recommendation actually takes effect on an unedited run, not just in
    # this preview text.
    command = apply_tool_overrides(
        tool_name, item_id or "", command, uses_wordlist=tool_cls.uses_wordlist
    )

    return {
        "command": command,
        "available": tool.is_available(),
        "recommended_category": category,
        "recommended_category_label": CATEGORY_LABELS.get(category) if category else None,
        "nuclei_tags": nuclei_tags,
    }


@lru_cache(maxsize=32)
def _cached_help(tool_name: str) -> str:
    tool_cls = TOOL_REGISTRY[tool_name]
    return tool_cls(target="").run_help()


@router.get("/{tool_name}/help")
def tool_help(tool_name: str) -> dict:
    """The tool's own --help output, straight from the installed binary —
    cached after the first call since it can't change without reinstalling
    the tool, and shelling out on every dialog open would be wasteful.
    """
    tool_cls = TOOL_REGISTRY.get(tool_name)
    if tool_cls is None:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")
    if not tool_cls(target="").is_available():
        return {"available": False, "text": ""}
    try:
        return {"available": True, "text": _cached_help(tool_name)}
    except Exception as exc:  # noqa: BLE001 - surface any help-flag failure as text, not a 500
        return {"available": True, "text": f"Could not run {tool_name} {tool_cls.help_flag}: {exc}"}


@router.get("/wordlists")
def list_wordlists() -> list[dict]:
    return [{"label": label, "path": path} for label, path in discover_wordlists()]


@router.get("/wordlists/grouped")
def list_wordlists_grouped(item_id: Optional[str] = None) -> dict:
    """Every wordlist found on this host, grouped by category (SecLists'
    own Discovery/Fuzzing/Passwords/... folders, Kali's sibling dirb/
    dirbuster/wfuzz/... dirs, etc.) — powers the "Select wordlist" dialog's
    card layout. If *item_id* has a recommended category (see
    checklist.WORDLIST_CATEGORY), the matching group(s) sort first and are
    flagged `recommended: true`.
    """
    category = WORDLIST_CATEGORY.get(item_id or "")
    return {
        "recommended_category": category,
        "recommended_category_label": CATEGORY_LABELS.get(category) if category else None,
        "groups": discover_wordlists_grouped(category),
    }


@router.get("/wordlists/remote/browse")
def browse_remote_wordlists(q: Optional[str] = None, item_id: Optional[str] = None) -> dict:
    """Every wordlist file in github.com/danielmiessler/SecLists, grouped by
    its top-level folder — for picking exactly one file to install rather
    than cloning the whole (multi-GB) repo. *q* filters by substring on the
    path.

    If *item_id* has a recommended category (see checklist.WORDLIST_CATEGORY
    — e.g. "admin" for "Enumerate Admin Interfaces"), individual files whose
    *path* matches that category's keywords (CATEGORY_KEYWORDS, the same
    lookup the Local tab and recommend_wordlist() already use) are flagged
    `recommended: true` and collected into a synthetic "Recommended" group
    pinned first — a plain top-level-folder match (e.g. "Discovery") isn't
    useful signal on its own since SecLists' folders are broad topics, not
    per-test categories; the file's own name is what actually indicates fit
    (".../Discovery/Web-Content/admin-panels.txt" for an admin-interfaces
    test, for instance).
    """
    try:
        files = seclists_remote.list_remote_wordlists()
    except seclists_remote.RemoteFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    query = (q or "").strip().lower()
    if query:
        files = [f for f in files if query in f["path"].lower()]

    category = WORDLIST_CATEGORY.get(item_id or "")
    keywords = CATEGORY_KEYWORDS.get(category or "", (category,) if category else ())

    def is_recommended(path: str) -> bool:
        lower = path.lower()
        return category is not None and any(kw in lower for kw in keywords)

    groups: dict[str, list[dict]] = {}
    recommended_files: list[dict] = []
    for f in files:
        entry = {
            "label": f["path"],
            "path": f["path"],
            "size": f["size"],
            "downloaded": seclists_remote.is_downloaded(f["path"]),
            "recommended": is_recommended(f["path"]),
        }
        groups.setdefault(f["category"], []).append(entry)
        if entry["recommended"]:
            recommended_files.append(entry)

    def sort_key(cat: str) -> tuple[int, str]:
        return (1, cat)

    # SecLists' "Fuzzing" folder alone has 4600+ files — sending every one
    # over the wire on an unfiltered browse is pure waste when the dialog
    # only ever shows a handful before the tester expands or searches.
    # Once they've actually typed a query, honor it in full (a narrowed
    # search shouldn't then hide a match behind this same cap).
    PER_CATEGORY_CAP = 40 if not query else None

    ordered = []
    if recommended_files:
        recommended_sorted = sorted(recommended_files, key=lambda w: w["label"])
        ordered.append(
            {
                "category": "Recommended",
                "recommended": True,
                "total": len(recommended_sorted),
                "truncated": False,
                # Capped separately from PER_CATEGORY_CAP — this group is
                # meant as a short, high-signal shortlist, not a full browse.
                "wordlists": recommended_sorted[:20],
            }
        )
    for cat, items in sorted(groups.items(), key=lambda kv: sort_key(kv[0])):
        items = sorted(items, key=lambda w: w["label"])
        total = len(items)
        ordered.append(
            {
                "category": cat,
                "recommended": False,
                "total": total,
                "truncated": PER_CATEGORY_CAP is not None and total > PER_CATEGORY_CAP,
                "wordlists": items[:PER_CATEGORY_CAP] if PER_CATEGORY_CAP else items,
            }
        )
    return {
        "recommended_category": category,
        "recommended_category_label": CATEGORY_LABELS.get(category) if category else None,
        "groups": ordered,
    }


@router.post("/wordlists/remote/download")
def download_remote_wordlist(body: DownloadWordlistRequest) -> dict:
    try:
        local_path = seclists_remote.download_wordlist(body.path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except seclists_remote.RemoteFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"path": local_path}
