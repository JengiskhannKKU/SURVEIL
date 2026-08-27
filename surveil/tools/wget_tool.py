"""wget tool wrapper — lightweight file/path existence & fetch checks."""
from __future__ import annotations

from .base import BaseTool, base_url


class WgetTool(BaseTool):
    name   = "wget"
    binary = "wget"
    description = (
        "Lightweight check for whether a specific file/path exists and what it "
        "contains — good for a one-off fetch (robots.txt, crossdomain.xml, a "
        "path another test already told you about) rather than brute-forcing a "
        "whole wordlist. Several checklist items point this at the well-known "
        "path that test is actually about instead of the bare target root."
    )
    example = "wget -S --spider https://example.com/robots.txt"
    install_hints = {
        "brew": "brew install wget",
        "apt": "sudo apt install -y wget",
    }

    def build_command(self, fast: bool = False) -> list[str]:
        url = base_url(self.target)
        if fast:
            # --spider: don't download, just check it exists and show headers.
            return ["wget", "-S", "--spider", url]
        # -O -: print the actual content to stdout instead of writing a file.
        return ["wget", "-S", "-O", "-", url]

    def mock_output(self) -> str:
        url = base_url(self.target)
        return f"""\
--2026-08-27 15:00:00--  {url}/robots.txt
Resolving example.com... 93.184.216.34
Connecting to example.com|93.184.216.34|:443... connected.
HTTP request sent, awaiting response...
  HTTP/1.1 200 OK
  Server: nginx/1.18.0 (Ubuntu)
  Content-Type: text/plain
  Content-Length: 142
Length: 142 [text/plain]

User-agent: *
Disallow: /admin/
Disallow: /internal/
Disallow: /backup/
Sitemap: {url}/sitemap.xml

⚠  Disallowed paths are a hint list, not access control — see WSTG-INFO-03.
   /admin/, /internal/, /backup/ are worth checking directly.

[SIMULATED — wget not found on this machine, target: {url}]"""
