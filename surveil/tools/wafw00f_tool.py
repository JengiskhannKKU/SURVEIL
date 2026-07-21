"""wafw00f tool wrapper — WAF detection."""
from __future__ import annotations

from .base import BaseTool


class Wafw00fTool(BaseTool):
    name   = "wafw00f"
    binary = "wafw00f"
    description = "Detect whether a Web Application Firewall sits in front of the target."
    example = "wafw00f https://example.com -a"

    def build_command(self, fast: bool = False) -> list[str]:
        if fast:
            return ["wafw00f", f"https://{self.target}"]
        return ["wafw00f", f"https://{self.target}", "-a"]

    def mock_output(self) -> str:
        return f"""\
                   ______
                  /      \\
                 (  W00f! )
                  \\      /
                  ~~~~V~~~~~
                   WAFW00F

[*] Checking https://{self.target}
[+] Generic Detection results:
[-] No WAF detected by the generic detection

[*] Checking https://{self.target} with 80 different WAF fingerprints
[-] Generic Detection results: No WAF detected

    Site at https://{self.target} does not seem to be behind a WAF

    ⚠  No WAF detected — active scanning results are reliable,
       but the application has no additional layer of protection.
       Recommend evaluating deployment of a WAF (Cloudflare, AWS WAF).

[~] Number of requests: 4

[SIMULATED — wafw00f not found on this machine]"""
