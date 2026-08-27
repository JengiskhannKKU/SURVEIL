"""amass tool wrapper — OWASP Amass passive subdomain enumeration."""
from __future__ import annotations

from .base import BaseTool


class AmassTool(BaseTool):
    name   = "amass"
    binary = "amass"
    description = (
        "Passive OWASP Amass subdomain enumeration across many data sources. "
        "Note: amass v5 (the current `brew`/`apt` release) needs a separately "
        "running `amass engine` process and fails fast with a confusing "
        "'engine did not respond' error without one — see the note this adds "
        "to the output if that happens, or install v4 instead (below) to "
        "avoid it entirely."
    )
    example = "amass enum -passive -d example.com -timeout 10"
    install_hints = {
        "brew": "brew install amass",
        "apt": "sudo apt install -y amass",
        # Pins v4's single-shot CLI via the /v4/ module path — sidesteps the
        # v5 engine requirement entirely rather than needing a second
        # long-running process. Same install this app's own Docker image uses.
        "go": "go install github.com/owasp-amass/amass/v4/...@master",
    }
    domain_only = True

    def build_command(self, fast: bool = False) -> list[str]:
        if fast:
            return ["amass", "enum", "-passive", "-d", self.target, "-timeout", "1"]
        return ["amass", "enum", "-passive", "-d", self.target, "-timeout", "10"]

    def get_timeout(self, fast: bool = False) -> int:
        # amass's own -timeout flag above is in MINUTES (1 / 10) — the
        # subprocess kill timeout (seconds) must be at least that long plus
        # a buffer, or we truncate a scan amass itself is still budgeting
        # time for. The old blanket 120s default was killing full runs
        # 8+ minutes before amass's own 10-minute budget was up.
        return 90 if fast else 660

    def postprocess_output(self, output: str, exit_code: int) -> str:
        # amass v5 rewrote the CLI into a client/server split: `enum` is now
        # just a client that talks to a separately running `amass engine`
        # process (default http://127.0.0.1:4000) and fails almost
        # instantly — not after a real scan timeout — if it can't reach
        # one. The v4 flags above (-passive/-d/-timeout) are still valid
        # syntax under v5, which is exactly why this fails opaquely instead
        # of with a clear "unknown flag" error: the command parses fine,
        # it just can never reach an engine that was never started.
        if "did not respond" in output.lower() and "engine" in output.lower():
            return output + """

[surveil note] This isn't a slow scan timing out — it's OWASP Amass v5's
new client/server architecture. `amass enum` now requires a separately
running `amass engine` process (default: http://127.0.0.1:4000) and
fails almost immediately if it can't reach one. To fix, either:

  1. Run `amass engine` in another terminal, then re-run this test, or
  2. Install amass v4's single-shot CLI instead (same one this app's own
     Docker image uses — no background engine needed):
       go install github.com/owasp-amass/amass/v4/...@master
  3. Or skip amass for this test — subfinder (also mapped here) already
     covers passive subdomain enumeration without needing an engine.

If you did start `amass engine` and still see this, something else may
already be bound to its default port 4000 — check with `lsof -i :4000`
(macOS/Linux) and free it or point `enum` at a different one with `-engine`."""
        return output

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
