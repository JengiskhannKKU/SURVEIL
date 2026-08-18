"""whatweb tool wrapper — technology and CMS fingerprinting."""
from __future__ import annotations

from .base import BaseTool


class WhatwebTool(BaseTool):
    name   = "whatweb"
    binary = "whatweb"
    description = "Fingerprint web technologies, CMS, and frameworks in use."
    example = "whatweb --color=never -v example.com"
    install_hints = {
        "brew": "brew install whatweb",
        "apt": "sudo apt install -y whatweb",
    }

    def build_command(self, fast: bool = False) -> list[str]:
        if fast:
            return ["whatweb", "--color=never", "-a", "1", self.target]
        return ["whatweb", "--color=never", "-v", self.target]

    def mock_output(self) -> str:
        return f"""\
WhatWeb report for https://{self.target}
Status    : 200 OK
Title     : Welcome | {self.target}
IP        : 93.184.216.34
Country   : UNITED STATES, US

Summary   : Bootstrap[4.6.0], Cookies[PHPSESSID], Country[UNITED STATES][US],
            Email[admin@{self.target}], HTML5, HTTPServer[Ubuntu Linux][nginx/1.18.0],
            HttpOnly[PHPSESSID], IP[93.184.216.34], JQuery[3.3.1],
            Open-Graph-Protocol, PHP[7.4.33], PasswordField[password],
            Script[text/javascript], Title[Welcome | {self.target}],
            X-Frame-Options[SAMEORIGIN], X-UA-Compatible[IE=edge]

Detected plugins:
[+] PHP
    Version : 7.4.33
    ⚠  End-of-life — PHP 7.4 reached EOL 2022-11-28. Upgrade to PHP 8.2+

[+] nginx
    Version : 1.18.0 (Ubuntu)
    ⚠  nginx 1.18.0 has known CVEs: CVE-2021-23017 (CVSS 7.7 — resolver buffer overflow)

[+] jQuery
    Version : 3.3.1
    ⚠  jQuery < 3.5.0 — prototype pollution (CVE-2019-11358, CVSS 6.1)

[+] WordPress (not detected)
[+] Apache (not detected)

[SIMULATED — whatweb not found on this machine]"""
