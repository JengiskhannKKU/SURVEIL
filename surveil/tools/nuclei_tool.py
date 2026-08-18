"""nuclei tool wrapper — template-based vulnerability scanning."""
from __future__ import annotations

from .base import BaseTool


class NucleiTool(BaseTool):
    name   = "nuclei"
    binary = "nuclei"
    description = "Match the target against community vulnerability/misconfiguration templates."
    example = (
        "nuclei -u https://example.com -tags misconfig,exposure,headers,tech "
        "-severity low,medium,high,critical -silent"
    )
    install_hints = {
        "brew": "brew install projectdiscovery/tap/nuclei",
        "go": "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
    }

    def build_command(self, fast: bool = False) -> list[str]:
        if fast:
            return [
                "nuclei",
                "-u", f"https://{self.target}",
                "-tags", "misconfig,exposure",
                "-severity", "high,critical",
                "-silent",
            ]
        return [
            "nuclei",
            "-u", f"https://{self.target}",
            "-tags", "misconfig,exposure,headers,tech",
            "-severity", "low,medium,high,critical",
            "-silent",
        ]

    def mock_output(self) -> str:
        return f"""\
[nuclei] Template-based scanning: https://{self.target}
[*] Loading templates: misconfig, exposure, headers, tech

[2026-07-07 15:01:23] [missing-csp] [http] [medium] https://{self.target}
    info: Content-Security-Policy header is missing
    matcher: response header does not contain 'content-security-policy'

[2026-07-07 15:01:24] [missing-hsts] [http] [medium] https://{self.target}
    info: Strict-Transport-Security header is missing
    matcher: response header does not contain 'strict-transport-security'

[2026-07-07 15:01:25] [tech-detect:php] [http] [info] https://{self.target}
    info: PHP detected via X-Powered-By header (7.4.33 — EOL)

[2026-07-07 15:01:26] [tomcat-manager-exposed] [http] [high] https://{self.target}:8080/manager/html
    info: Apache Tomcat Manager exposed without IP restriction

[2026-07-07 15:01:27] [http-trace-method] [http] [low] https://{self.target}
    info: TRACE method enabled — Cross-Site Tracing (XST) risk

[2026-07-07 15:01:28] [phpinfo-disclosure] [http] [medium] https://{self.target}/info.php
    info: phpinfo() page accessible at /info.php — exposes full PHP config

[nuclei] Scan complete. 6 findings. Templates: 847 matched.

[SIMULATED — nuclei not found on this machine]"""
