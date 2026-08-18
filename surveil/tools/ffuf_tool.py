"""ffuf tool wrapper — directory/file brute-forcing."""
from __future__ import annotations

from .base import BaseTool


class FfufTool(BaseTool):
    name   = "ffuf"
    binary = "ffuf"
    description = "Brute-force directories/files on the target using a wordlist."
    uses_wordlist = True
    example = (
        "ffuf -u https://example.com/FUZZ -w /usr/share/wordlists/dirb/common.txt "
        "-mc 200,301,302,403 -t 50 -c -s"
    )
    install_hints = {
        "brew": "brew install ffuf",
        "apt": "sudo apt install -y ffuf",
        "go": "go install github.com/ffuf/ffuf/v2@latest",
    }
    timeout_seconds = 300

    def build_command(self, fast: bool = False) -> list[str]:
        cmd = [
            "ffuf",
            "-u", f"https://{self.target}/FUZZ",
            "-w", "/usr/share/wordlists/dirb/common.txt",
            "-mc", "200,301,302,403",
            "-t", "50",
            "-c", "-s",
        ]
        if fast:
            cmd += ["-maxtime", "30"]
        return cmd

    def mock_output(self) -> str:
        return f"""\
[Status: 200, Size: 1245, Words: 89, Lines: 32, Duration: 120ms]
| URL | https://{self.target}/admin
[Status: 301, Size: 178, Words: 6, Lines: 8, Duration: 45ms]
| URL | https://{self.target}/admin -> https://{self.target}/admin/
[Status: 200, Size: 3892, Words: 214, Lines: 67, Duration: 98ms]
| URL | https://{self.target}/login
[Status: 301, Size: 178, Words: 6, Lines: 8, Duration: 52ms]
| URL | https://{self.target}/api
[Status: 403, Size: 564, Words: 12, Lines: 14, Duration: 38ms]
| URL | https://{self.target}/backup
[Status: 200, Size: 87, Words: 3, Lines: 5, Duration: 41ms]
| URL | https://{self.target}/.env
[Status: 200, Size: 734, Words: 42, Lines: 28, Duration: 55ms]
| URL | https://{self.target}/robots.txt
[Status: 200, Size: 2104, Words: 115, Lines: 43, Duration: 63ms]
| URL | https://{self.target}/sitemap.xml
[Status: 200, Size: 41, Words: 1, Lines: 2, Duration: 37ms]
| URL | https://{self.target}/.git/HEAD
[Status: 200, Size: 1893, Words: 98, Lines: 51, Duration: 72ms]
| URL | https://{self.target}/config.php.bak

:: Progress: [4614/4614] :: Job [1/1] :: 312 req/sec :: Duration: [0:00:15] :: Errors: 0 ::
[SIMULATED — ffuf not found on this machine]"""
