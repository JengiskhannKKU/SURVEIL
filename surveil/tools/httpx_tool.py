"""httpx tool wrapper — HTTP probing and header analysis."""
from __future__ import annotations

from .base import BaseTool


class HttpxTool(BaseTool):
    name   = "httpx"
    binary = "httpx"
    description = "Probe HTTP(S) endpoints for status, title, tech stack, and response headers."
    example = (
        "httpx -u example.com -title -tech-detect -status-code -content-length "
        "-response-header -follow-redirects -silent"
    )

    def build_command(self, fast: bool = False) -> list[str]:
        if fast:
            return ["httpx", "-u", self.target, "-status-code", "-silent", "-timeout", "5"]
        return [
            "httpx",
            "-u", self.target,
            "-title", "-tech-detect",
            "-status-code", "-content-length",
            "-response-header",
            "-follow-redirects",
            "-silent",
        ]

    def mock_output(self) -> str:
        return f"""\
http://{self.target} [301] → https://{self.target}/
https://{self.target} [200] [Welcome | {self.target}]
  Content-Length: 24310
  Server: nginx/1.18.0 (Ubuntu)
  X-Powered-By: PHP/7.4.33
  Set-Cookie: PHPSESSID=abc123; path=/  (missing Secure; missing HttpOnly)
  X-Frame-Options: SAMEORIGIN
  X-Content-Type-Options: nosniff

  ⚠  Missing headers:
    - Content-Security-Policy
    - Strict-Transport-Security
    - Referrer-Policy
    - Permissions-Policy

  Technologies: nginx, PHP 7.4, jQuery 3.3.1, Bootstrap 4.6
  Redirects: http → https (correct)

https://{self.target}:8080 [200] [Apache Tomcat 9.0.73]
  Server: Apache-Coyote/1.1
  ⚠  Tomcat Manager exposed — check default credentials (tomcat:tomcat)

[SIMULATED — httpx not found on this machine]"""
