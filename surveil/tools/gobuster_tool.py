"""gobuster tool wrapper — directory brute-forcing."""
from __future__ import annotations

from .base import BaseTool


class GobusterTool(BaseTool):
    name   = "gobuster"
    binary = "gobuster"
    description = "Brute-force directories using a wordlist (similar to ffuf)."
    uses_wordlist = True
    example = "gobuster dir -u https://example.com -w /usr/share/wordlists/dirb/common.txt -t 50 -q --no-error"
    install_hints = {
        "brew": "brew install gobuster",
        "apt": "sudo apt install -y gobuster",
        "go": "go install github.com/OJ/gobuster/v3@latest",
    }

    def build_command(self, fast: bool = False) -> list[str]:
        return [
            "gobuster", "dir",
            "-u", f"https://{self.target}",
            "-w", "/usr/share/wordlists/dirb/common.txt",
            "-t", "100" if fast else "50",
            "-q", "--no-error",
        ]

    def mock_output(self) -> str:
        return f"""\
/admin                (Status: 301) [Size: 178] [--> https://{self.target}/admin/]
/api                  (Status: 301) [Size: 178] [--> https://{self.target}/api/]
/assets               (Status: 301) [Size: 178] [--> https://{self.target}/assets/]
/backup               (Status: 403) [Size: 564]
/cgi-bin              (Status: 403) [Size: 564]
/config               (Status: 403) [Size: 564]
/css                  (Status: 301) [Size: 178] [--> https://{self.target}/css/]
/dashboard            (Status: 302) [Size: 0] [--> https://{self.target}/login]
/images               (Status: 301) [Size: 178] [--> https://{self.target}/images/]
/js                   (Status: 301) [Size: 178] [--> https://{self.target}/js/]
/login                (Status: 200) [Size: 3892]
/logout               (Status: 302) [Size: 0] [--> https://{self.target}/login]
/robots.txt           (Status: 200) [Size: 734]
/server-status        (Status: 403) [Size: 564]
/uploads              (Status: 403) [Size: 564]
/wp-admin             (Status: 301) [Size: 178] [--> https://{self.target}/wp-admin/]
[SIMULATED — gobuster not found on this machine]"""
