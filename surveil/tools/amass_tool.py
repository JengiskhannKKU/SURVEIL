"""amass tool wrapper — OWASP Amass passive subdomain enumeration."""
from __future__ import annotations

from .base import BaseTool


class AmassTool(BaseTool):
    name   = "amass"
    binary = "amass"
    description = "Passive OWASP Amass subdomain enumeration across many data sources."
    example = "amass enum -passive -d example.com -timeout 10"
    install_hints = {
        "brew": "brew install amass",
        "apt": "sudo apt install -y amass",
    }

    def build_command(self, fast: bool = False) -> list[str]:
        if fast:
            return ["amass", "enum", "-passive", "-d", self.target, "-timeout", "1"]
        return ["amass", "enum", "-passive", "-d", self.target, "-timeout", "10"]

    def mock_output(self) -> str:
        return f"""\
[amass] OWASP Amass passive subdomain enumeration for: {self.target}

[*] Querying data sources for subdomains of {self.target}...

www.{self.target}              (CertSpotter)
mail.{self.target}             (SecurityTrails)
dev.{self.target}              (CertSpotter, Censys)
staging.{self.target}          (SecurityTrails)
api.{self.target}              (VirusTotal, Censys)
admin.{self.target}            (HackerTarget)
vpn.{self.target}              (Shodan)
cdn.{self.target}              (CertSpotter, crt.sh)
portal.{self.target}           (SecurityTrails)
old.{self.target}              (Wayback Machine)
beta.{self.target}             (crt.sh)
docs.{self.target}             (VirusTotal)
internal.{self.target}         (Censys)

[*] OWASP Amass v4.2.0 — passive enumeration completed
[*] 13 subdomains discovered across 8 data sources in 2m 47s

Data sources used:
   CertSpotter     — 4 results
   SecurityTrails  — 3 results
   Censys          — 3 results
   VirusTotal      — 2 results
   crt.sh          — 2 results
   HackerTarget    — 1 result
   Shodan          — 1 result
   Wayback Machine — 1 result

⚠  Interesting subdomains detected:
   dev.{self.target}        — development environment may be less hardened
   staging.{self.target}    — may expose pre-release features
   admin.{self.target}      — administrative interface
   internal.{self.target}   — internal resource exposed externally
   old.{self.target}        — legacy application, likely unpatched
   beta.{self.target}       — beta environment, potential misconfigurations

[SIMULATED — amass not found on this machine]"""
