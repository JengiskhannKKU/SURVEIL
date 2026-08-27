"""curl tool wrapper — lightweight manual HTTP inspection."""
from __future__ import annotations

from .base import BaseTool, base_url


class CurlTool(BaseTool):
    name   = "curl"
    binary = "curl"
    description = (
        "Lightweight manual HTTP request/response inspection — no install needed "
        "on almost any machine. The default just dumps response headers; several "
        "checklist items (HTTP methods, CORS, Host header injection, RIA cross "
        "domain policy) override this with the exact flags/headers/path that test "
        "actually needs. Edit the command for anything else — e.g. -X POST -d "
        "'field=value' for a form, or -b 'session=...' to send a specific cookie."
    )
    example = "curl -sS -I https://example.com"
    install_hints = {
        "brew": "brew install curl",
        "apt": "sudo apt install -y curl",
    }

    def build_command(self, fast: bool = False) -> list[str]:
        url = base_url(self.target)
        if fast:
            # -I: HEAD request, headers only — the quick default for "what
            # does this endpoint send back" checks.
            return ["curl", "-sS", "-I", url]
        # -i: full GET with headers included above the body; -L: follow
        # redirects, since a lot of what's interesting (final security
        # headers, RIA policy content) only shows up after landing on the
        # real page.
        return ["curl", "-sS", "-i", "-L", url]

    def mock_output(self) -> str:
        url = base_url(self.target)
        return f"""\
HTTP/1.1 200 OK
Date: Thu, 27 Aug 2026 15:00:00 GMT
Server: nginx/1.18.0 (Ubuntu)
Content-Type: text/html; charset=UTF-8
Content-Length: 24310
Set-Cookie: PHPSESSID=abc123def456; path=/
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
Connection: keep-alive

⚠  Notable:
   Set-Cookie missing Secure and HttpOnly flags — see WSTG-SESS-02
   No Content-Security-Policy / Strict-Transport-Security header — see WSTG-CONF-02/07
   Server header discloses exact version — see WSTG-INFO-02

[SIMULATED — curl not found on this machine, target: {url}]"""
