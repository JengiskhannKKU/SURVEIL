from __future__ import annotations

from typing import Optional

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
            "available": cls(target="").is_available(),
            "install_hints": cls.install_hints,
            "modes": cls.modes,
            "domain_only": cls.domain_only,
        }
        for name, cls in sorted(TOOL_REGISTRY.items())
    ]


@router.get("/{tool_name}/command")
def preview_command(
    tool_name: str, target: str, fast: bool = False, mode: Optional[str] = None
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
    return {
        "command": command,
        "available": tool.is_available(),
    }


@router.get("/wordlists")
def list_wordlists() -> list[dict]:
    return [{"label": label, "path": path} for label, path in discover_wordlists()]
