"""Tools sub-package."""
from .base import ToolResult, run_tool
from .nmap_tool import NmapTool
from .httpx_tool import HttpxTool
from .whatweb_tool import WhatwebTool
from .wafw00f_tool import Wafw00fTool
from .subfinder_tool import SubfinderTool
from .nuclei_tool import NucleiTool

TOOL_REGISTRY: dict[str, type] = {
    "nmap":      NmapTool,
    "httpx":     HttpxTool,
    "whatweb":   WhatwebTool,
    "wafw00f":   Wafw00fTool,
    "subfinder": SubfinderTool,
    "nuclei":    NucleiTool,
}

__all__ = [
    "ToolResult", "run_tool",
    "NmapTool", "HttpxTool", "WhatwebTool",
    "Wafw00fTool", "SubfinderTool", "NucleiTool",
    "TOOL_REGISTRY",
]
