from __future__ import annotations

from fastapi import APIRouter, HTTPException

from surveil.tools import TOOL_REGISTRY
from surveil.wordlists import discover_wordlists

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("")
def list_tools() -> list[dict]:
    return [
        {
            "name": name,
            "description": cls.description,
            "example": cls.example,
            "uses_wordlist": cls.uses_wordlist,
        }
        for name, cls in sorted(TOOL_REGISTRY.items())
    ]


@router.get("/{tool_name}/command")
def preview_command(tool_name: str, target: str, fast: bool = False) -> dict:
    tool_cls = TOOL_REGISTRY.get(tool_name)
    if tool_cls is None:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")
    tool = tool_cls(target)
    return {
        "command": tool.build_command(fast=fast),
        "available": tool.is_available(),
    }


@router.get("/wordlists")
def list_wordlists() -> list[dict]:
    return [{"label": label, "path": path} for label, path in discover_wordlists()]
