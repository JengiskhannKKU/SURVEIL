"""arjun tool wrapper — hidden HTTP parameter discovery."""
from __future__ import annotations

from .base import BaseTool


class ArjunTool(BaseTool):
    name   = "arjun"
    binary = "arjun"
    description = "Discover hidden/undocumented HTTP GET parameters via brute force."
    example = "arjun -u https://example.com --stable -t 10"
    install_hints = {"pip": "pip install arjun"}

    def build_command(self, fast: bool = False) -> list[str]:
        if fast:
            return ["arjun", "-u", f"https://{self.target}", "-t", "20"]
        return ["arjun", "-u", f"https://{self.target}", "--stable", "-t", "10"]

    def mock_output(self) -> str:
        return f"""\
[arjun] Hidden HTTP parameter discovery for: {self.target}

    _
   /_| _ '
  (  |/ /(//)
      _/

[*] Probing {self.target} for hidden parameters...
[*] Testing with default wordlist (large) — 10 threads, stable mode

[GET] https://{self.target}
  [+] debug          — reflected in response (200 OK, +312 bytes)
  [+] admin          — reflected in response (200 OK, +89 bytes)
  [+] test           — reflected in response (200 OK, +45 bytes)
  [+] callback       — reflected in response (200 OK, +227 bytes)
  [+] redirect       — triggers 302 redirect
  [+] next           — triggers 302 redirect

[POST] https://{self.target}
  [+] token          — reflected in response (200 OK, +198 bytes)
  [+] api_key        — reflected in response (403 Forbidden)
  [+] debug          — reflected in response (200 OK, +312 bytes)

[*] Scan completed in 47.23s
[*] Found 8 hidden parameters across GET/POST methods

⚠  Notable findings:
   debug     — may enable verbose error output or debug panels
   admin     — could expose administrative functionality
   api_key   — parameter accepted; may bypass auth with valid key
   redirect  — potential open-redirect vector
   next      — potential open-redirect vector
   callback  — may be exploitable for SSRF or XSS via JSONP

[SIMULATED — arjun not found on this machine]"""
