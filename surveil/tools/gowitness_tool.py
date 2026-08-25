"""gowitness tool wrapper — screenshot capture of web pages."""
from __future__ import annotations

from .base import BaseTool, base_url


class GowitnessTool(BaseTool):
    name   = "gowitness"
    binary = "gowitness"
    description = "Capture a screenshot of the target's web page for visual triage."
    example = "gowitness single https://example.com --timeout 30"
    help_flag = "--help"
    install_hints = {"go": "go install github.com/sensepost/gowitness@latest"}

    def build_command(self, fast: bool = False) -> list[str]:
        url = base_url(self.target)
        if fast:
            return ["gowitness", "single", url, "--timeout", "10"]
        return ["gowitness", "single", url, "--timeout", "30"]

    def mock_output(self) -> str:
        return f"""\
[gowitness] Screenshot capture for: {self.target}

[*] Navigating to https://{self.target} (timeout: 30s)
[*] Waiting for page load...
[*] Page loaded successfully

   URL          : https://{self.target}
   Final URL    : https://www.{self.target}/
   Status Code  : 200 OK
   Title        : {self.target.split('.')[0].capitalize()} — Welcome
   Content-Type : text/html; charset=UTF-8
   Server       : cloudflare
   Screenshot   : screenshots/https-{self.target.replace('.', '-')}.png

[+] Screenshot saved: screenshots/https-{self.target.replace('.', '-')}.png (1366x768, 284 KB)
[*] Redirects followed:
      https://{self.target} → 301 → https://www.{self.target}/

[*] Capture completed in 4.17s

⚠  Notable findings:
   Redirect detected: HTTP → HTTPS with www prefix
   Server header exposes: cloudflare
   Screenshot saved for visual review

[SIMULATED — gowitness not found on this machine]"""
