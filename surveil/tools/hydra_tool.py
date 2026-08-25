"""hydra tool wrapper — online brute-force login testing."""
from __future__ import annotations

from pathlib import Path

from .base import BaseTool

_BUNDLED_DIR = Path(__file__).parent.parent / "data" / "wordlists"


class HydraTool(BaseTool):
    name   = "hydra"
    binary = "hydra"
    description = (
        "Brute-force login credentials — defaults to SSH (the most commonly "
        "exposed brute-forceable service) using bundled username/password "
        "lists. For a web login form or another protocol, edit the command "
        "(e.g. swap 'ssh://target' for 'target http-post-form "
        "\"/login:user=^USER^&pass=^PASS^:F=incorrect\"' or 'ftp://target')."
    )
    uses_wordlist = False  # takes two lists (-L/-P), not the single -w the picker assumes
    example = "hydra -L usernames.txt -P passwords.txt -f -t 4 ssh://example.com"
    install_hints = {
        "brew": "brew install hydra",
        "apt": "sudo apt install -y hydra",
    }
    timeout_seconds = 300

    def build_command(self, fast: bool = False) -> list[str]:
        users = _BUNDLED_DIR / "usernames.txt"
        passwords = _BUNDLED_DIR / "passwords.txt"
        return [
            "hydra",
            "-L", str(users),
            "-P", str(passwords),
            "-f",  # stop on first valid pair found
            "-t", "8" if fast else "4",
            f"ssh://{self.target}",
        ]

    def get_timeout(self, fast: bool = False) -> int:
        return 90 if fast else 300

    def mock_output(self) -> str:
        return f"""\
Hydra v9.5 (c) 2023 by van Hauser/THC & David Maciejak - for legal purposes only

Hydra (https://github.com/vanhauser-thc/thc-hydra) starting at 2026-07-07 15:00:00
[WARNING] Restorefile (you have 10 seconds to abort... use option -I to skip waiting)
[DATA] max 4 tasks per 1 server, overall 4 tasks, 190 login tries (l:19/p:10), ~48 tries per task
[DATA] attacking ssh://{self.target}:22/

[STATUS] 76.00 tries/min, 76 tries in 00:01h, 114 to do in 00:02h, 4 active
[22][ssh] host: {self.target}   login: admin   password: admin123
[STATUS] attack finished for {self.target} (valid pair found)

1 of 1 target successfully completed, 1 valid password found
Hydra finished at 2026-07-07 15:01:42

⚠  Notable findings:
   Weak/default SSH credential accepted: admin:admin123 — immediate remediation required
   No account lockout observed after repeated failed attempts — see WSTG-ATHN-03

[SIMULATED — hydra not found on this machine]"""
