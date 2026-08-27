"""naabu tool wrapper — fast SYN-based port scanning."""
from __future__ import annotations

from .base import BaseTool


class NaabuTool(BaseTool):
    name   = "naabu"
    binary = "naabu"
    description = (
        "Fast port discovery — scans far more ports per second than nmap by "
        "skipping service/version detection entirely. Use this first to find "
        "which ports are open, then run nmap against just those for banners "
        "and script output."
    )
    example = "naabu -host example.com -top-ports 100 -silent"
    install_hints = {"go": "go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"}
    timeout_seconds = 300

    def build_command(self, fast: bool = False) -> list[str]:
        if fast:
            return ["naabu", "-host", self.target, "-top-ports", "100", "-silent"]
        # -p - : every port, 1-65535. Genuinely slow (the whole reason naabu
        # exists is to make this tractable at all vs. nmap's default -sV
        # per-port overhead), hence the longer timeout below.
        return ["naabu", "-host", self.target, "-p", "-", "-silent"]

    def get_timeout(self, fast: bool = False) -> int:
        return 60 if fast else 300

    def mock_output(self) -> str:
        return f"""\

     _  _
_ __ __ _ __ _| |__ _  _
| ' \\/ _` / _` | '_ \\ || |
|_|_|_\\__,_\\__,_|_.__/\\_,_|
                     v2.3.3

                projectdiscovery.io

[INF] Running with default port range
{self.target}:22
{self.target}:80
{self.target}:443
{self.target}:3306
{self.target}:6379
{self.target}:8080

[SIMULATED — naabu not found on this machine]"""
