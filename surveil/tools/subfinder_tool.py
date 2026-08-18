"""subfinder tool wrapper — passive subdomain discovery."""
from __future__ import annotations

from .base import BaseTool


class SubfinderTool(BaseTool):
    name   = "subfinder"
    binary = "subfinder"
    description = "Passively enumerate subdomains from public data sources."
    example = "subfinder -d example.com -silent -all"
    install_hints = {
        "brew": "brew install projectdiscovery/tap/subfinder",
        "go": "go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
    }

    def build_command(self, fast: bool = False) -> list[str]:
        if fast:
            return ["subfinder", "-d", self.target, "-silent", "-timeout", "10"]
        return ["subfinder", "-d", self.target, "-silent", "-all"]

    def mock_output(self) -> str:
        return f"""\
[subfinder] Passive subdomain enumeration for: {self.target}
[*] Using sources: CertSpotter, Censys, Shodan, SecurityTrails, VirusTotal...

www.{self.target}
mail.{self.target}
dev.{self.target}
staging.{self.target}
api.{self.target}
admin.{self.target}
vpn.{self.target}
old.{self.target}
backup.{self.target}
test.{self.target}

[*] Found 10 subdomains for {self.target} in 3.41s

⚠  Interesting subdomains detected:
   dev.{self.target}     — development environment may be less hardened
   staging.{self.target} — may expose pre-release features
   admin.{self.target}   — administrative interface
   backup.{self.target}  — potential data exposure
   old.{self.target}     — legacy application, likely unpatched

[SIMULATED — subfinder not found on this machine]"""
