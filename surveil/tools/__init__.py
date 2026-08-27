"""Tools sub-package."""
from .base import ToolResult, run_tool
from .nmap_tool import NmapTool
from .httpx_tool import HttpxTool
from .whatweb_tool import WhatwebTool
from .wafw00f_tool import Wafw00fTool
from .subfinder_tool import SubfinderTool
from .nuclei_tool import NucleiTool
from .arjun_tool import ArjunTool
from .dnsx_tool import DnsxTool
from .gowitness_tool import GowitnessTool
from .wpscan_tool import WpscanTool
from .amass_tool import AmassTool
from .ffuf_tool import FfufTool
from .gobuster_tool import GobusterTool
from .katana_tool import KatanaTool
from .nikto_tool import NiktoTool
from .testssl_tool import TestsslTool
from .sqlmap_tool import SqlmapTool
from .hydra_tool import HydraTool
from .naabu_tool import NaabuTool
from .dalfox_tool import DalfoxTool
from .commix_tool import CommixTool
from .curl_tool import CurlTool
from .wget_tool import WgetTool

TOOL_REGISTRY: dict[str, type] = {
    "nmap":      NmapTool,
    "httpx":     HttpxTool,
    "whatweb":   WhatwebTool,
    "wafw00f":   Wafw00fTool,
    "subfinder": SubfinderTool,
    "nuclei":    NucleiTool,
    "arjun":     ArjunTool,
    "dnsx":      DnsxTool,
    "gowitness": GowitnessTool,
    "wpscan":    WpscanTool,
    "amass":     AmassTool,
    "ffuf":      FfufTool,
    "gobuster":  GobusterTool,
    "katana":    KatanaTool,
    "nikto":     NiktoTool,
    "testssl":   TestsslTool,
    "sqlmap":    SqlmapTool,
    "hydra":     HydraTool,
    "naabu":     NaabuTool,
    "dalfox":    DalfoxTool,
    "commix":    CommixTool,
    "curl":      CurlTool,
    "wget":      WgetTool,
}

__all__ = [
    "ToolResult", "run_tool",
    "NmapTool", "HttpxTool", "WhatwebTool",
    "Wafw00fTool", "SubfinderTool", "NucleiTool",
    "ArjunTool", "DnsxTool", "GowitnessTool",
    "WpscanTool", "AmassTool",
    "FfufTool", "GobusterTool", "KatanaTool",
    "NiktoTool", "TestsslTool", "SqlmapTool", "HydraTool",
    "NaabuTool", "DalfoxTool", "CommixTool",
    "CurlTool", "WgetTool",
    "TOOL_REGISTRY",
]
