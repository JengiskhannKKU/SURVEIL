"""enum4linux-ng wrapper — SMB/NetBIOS enumeration."""
from __future__ import annotations

from .base import BaseTool


class Enum4linuxTool(BaseTool):
    name   = "enum4linux"
    binary = "enum4linux-ng"
    description = (
        "SMB/NetBIOS enumeration against a target's SMB service (usually port 445): "
        "users, groups, shares (including anonymous/null-session access), password "
        "policy, OS/domain info. A genuine OSCP/PWK-lab staple — SMB misconfiguration "
        "is one of the most common real foothold paths. Runs enum4linux-ng, the "
        "actively-maintained Python rewrite of the original Perl enum4linux (same "
        "checks, structured/YAML-style output, real CVE/vuln checks the original "
        "never had)."
    )
    example = "enum4linux-ng -A 192.168.1.10"
    # Not on PyPI (confirmed: `pipx install enum4linux-ng` fails with "No
    # matching distribution found") — git clone + its own requirements.txt
    # is the real install path, not a package-manager one-liner.
    install_hints = {
        "git": "git clone https://github.com/cddmp/enum4linux-ng.git && "
               "pip install -r enum4linux-ng/requirements.txt",
    }
    timeout_seconds = 120

    def build_command(self, fast: bool = False) -> list[str]:
        if fast:
            # -U -S : just users + shares, the two fastest, highest-signal
            # checks — skips the policy/group/OS enumeration -A also runs.
            return ["enum4linux-ng", "-U", "-S", self.target]
        # -A: "do all simple enumeration" (users, groups, shares, password
        # policy, OS info, printers) — enum4linux-ng's own recommended
        # default for a first pass against an unknown target.
        return ["enum4linux-ng", "-A", self.target]

    def get_timeout(self, fast: bool = False) -> int:
        return 45 if fast else 120

    def mock_output(self) -> str:
        # Matches enum4linux-ng's real section-banner output shape (======
        # headers per check, confirmed against its own README/sample runs).
        return f"""\
ENUM4LINUX - next generation (v1.3.4)

 ==========================
|    Target Information    |
 ==========================
[*] Target ........... {self.target}
[*] Username ......... ''
[*] Random Username .. 'eoxfvqoz'
[*] Password ......... ''

 ================================
|    Domain Information via SMB  |
 ================================
[+] Got domain/workgroup name: WORKGROUP

 ===================================
|    RPC Session Check on {self.target}    |
 ===================================
[+] Server allows session using username '', password ''

 ============================
|    Shares via RPC    |
 ============================
[+] Enumerating shares
Share             Type      Comment
-----             ----      -------
ADMIN$            Disk      Remote Admin
C$                Disk      Default share
IPC$              IPC       Remote IPC
backups           Disk

[+] Anonymous access to 'backups' share: READ

 ============================
|    Users via RPC    |
 ============================
[+] Enumerating users via 'querydispinfo'
index: 0x1 RID: 0x3e8 acb: 0x00000210 Account: administrator	Name: (null)	Desc: Built-in account for administering the computer/domain
index: 0x2 RID: 0x3f4 acb: 0x00000210 Account: backup_svc	Name: Backup Service Account	Desc: (null)

⚠  Notable findings:
   Anonymous/null-session access allowed — real credential-free foothold
   Anonymous READ on share 'backups' — worth pulling and reviewing its contents
   Local account 'backup_svc' found — a real target for password spraying/OSCP-ENUM-07

[SIMULATED — enum4linux-ng not found on this machine]"""
