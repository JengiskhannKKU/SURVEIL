from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from surveil.checklist import CATEGORY_LABELS, WORDLIST_CATEGORY
from surveil.tools import TOOL_REGISTRY
from surveil.wordlists import discover_wordlists, recommend_wordlist

router = APIRouter(prefix="/api/tools", tags=["tools"])


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
