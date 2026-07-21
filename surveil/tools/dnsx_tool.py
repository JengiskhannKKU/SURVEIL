"""dnsx tool wrapper — DNS resolution and enumeration."""
from __future__ import annotations

from .base import BaseTool


class DnsxTool(BaseTool):
    name   = "dnsx"
    binary = "dnsx"
    description = "Resolve DNS record types (A/AAAA/CNAME/MX/NS/TXT) for the target."
    example = "echo example.com | dnsx -a -aaaa -cname -mx -ns -txt -resp -silent"

    def build_command(self, fast: bool = False) -> list[str]:
        if fast:
            return ["sh", "-c", f"echo {self.target} | dnsx -a -cname -resp -silent"]
        return [
            "sh", "-c",
            f"echo {self.target} | dnsx -a -aaaa -cname -mx -ns -txt -resp -silent",
        ]

    def mock_output(self) -> str:
        return f"""\
[dnsx] DNS resolution and enumeration for: {self.target}

[A] {self.target}
  → 104.21.34.180
  → 172.67.182.95

[AAAA] {self.target}
  → (no AAAA records found)

[CNAME] {self.target}
  → (no CNAME — resolves directly)
[CNAME] www.{self.target}
  → {self.target}.cdn.cloudflare.net.
[CNAME] status.{self.target}
  → stats.uptimerobot.com.   ⚠ potential dangling CNAME — verify target exists

[MX] {self.target}
  → 1  aspmx.l.google.com.
  → 5  alt1.aspmx.l.google.com.
  → 10 alt2.aspmx.l.google.com.

[NS] {self.target}
  → ann.ns.cloudflare.com.
  → bob.ns.cloudflare.com.

[TXT] {self.target}
  → "v=spf1 include:_spf.google.com include:mailgun.org ~all"
  → "google-site-verification=AbCdEfGhIjKlMnOpQrStUvWxYz1234567890"
  → "MS=ms12345678"

[*] Query completed in 1.82s

⚠  Notable findings:
   Dangling CNAME: status.{self.target} → stats.uptimerobot.com. (subdomain takeover risk)
   SPF record permits mailgun.org — verify this is intentional
   Multiple MX records point to Google Workspace

[SIMULATED — dnsx not found on this machine]"""
