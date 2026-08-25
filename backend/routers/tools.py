from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from surveil import seclists_remote
from surveil.checklist import CATEGORY_LABELS, WORDLIST_CATEGORY
from surveil.tools import TOOL_REGISTRY
from surveil.wordlists import discover_wordlists, discover_wordlists_grouped, recommend_wordlist

router = APIRouter(prefix="/api/tools", tags=["tools"])


class DownloadWordlistRequest(BaseModel):
    path: str  # repo-relative path, e.g. "Discovery/Web-Content/common.txt"


def _swap_wordlist_flag(command: list[str], new_path: str) -> list[str]:
    """Replace the value following a `-w` flag in *command*, if present."""
    cmd = list(command)
    for i, tok in enumerate(cmd):
        if tok == "-w" and i + 1 < len(cmd):
            cmd[i + 1] = new_path
            break
    return cmd


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

    # If this test has a recommended wordlist category (see
    # checklist.WORDLIST_CATEGORY — e.g. an admin-panel list for
    # "Enumerate Admin Interfaces") *and* this tool actually takes a
    # wordlist, use it in place of the tool's plain generic default, so
    # the same tool suggests a different, more relevant wordlist depending
    # on which test it's being run for. Irrelevant (and left null in the
    # response) for tools that don't use a wordlist at all.
    category = WORDLIST_CATEGORY.get(item_id or "") if tool_cls.uses_wordlist else None
    if category:
        command = _swap_wordlist_flag(command, recommend_wordlist(category))

    return {
        "command": command,
        "available": tool.is_available(),
        "recommended_category": category,
        "recommended_category_label": CATEGORY_LABELS.get(category) if category else None,
    }


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
    its top-level folder — for picking exactly one file to download rather
    than cloning the whole (multi-GB) repo. *q* filters by substring on the
    path; *item_id* flags the category matching the current test's
    recommendation, same as `/wordlists/grouped`.
    """
    try:
        files = seclists_remote.list_remote_wordlists()
    except seclists_remote.RemoteFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    query = (q or "").strip().lower()
    if query:
        files = [f for f in files if query in f["path"].lower()]

    category = WORDLIST_CATEGORY.get(item_id or "")
    groups: dict[str, list[dict]] = {}
    for f in files:
        groups.setdefault(f["category"], []).append(
            {
                "label": f["path"],
                "path": f["path"],
                "size": f["size"],
                "downloaded": seclists_remote.is_downloaded(f["path"]),
            }
        )

    def sort_key(cat: str) -> tuple[int, str]:
        is_recommended = category is not None and cat.lower() == category.lower()
        return (0 if is_recommended else 1, cat)

    # SecLists' "Fuzzing" folder alone has 4600+ files — sending every one
    # over the wire on an unfiltered browse is pure waste when the dialog
    # only ever shows a handful before the tester expands or searches.
    # Once they've actually typed a query, honor it in full (a narrowed
    # search shouldn't then hide a match behind this same cap).
    PER_CATEGORY_CAP = 40 if not query else None

    ordered = []
    for cat, items in sorted(groups.items(), key=lambda kv: sort_key(kv[0])):
        items = sorted(items, key=lambda w: w["label"])
        total = len(items)
        ordered.append(
            {
                "category": cat,
                "recommended": sort_key(cat)[0] == 0,
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
