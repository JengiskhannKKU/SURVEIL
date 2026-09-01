"""sqlmap tool wrapper — automated SQL injection detection/exploitation."""
from __future__ import annotations

from .base import BaseTool, base_url


class SqlmapTool(BaseTool):
    name   = "sqlmap"
    binary = "sqlmap"
    description = (
        "Detect and exploit SQL injection. The default command crawls the "
        "target and tests every link/form parameter it finds — for a faster, "
        "targeted run against a known injectable endpoint, edit the command "
        "to a specific -u \"https://target/page?id=1\" instead."
    )
    example = "sqlmap -u https://example.com --crawl=2 --forms --batch --level=2 --risk=1"
    help_flag = "-hh"
    install_hints = {
        "brew": "brew install sqlmap",
        "apt": "sudo apt install -y sqlmap",
        "pip": "pip install sqlmap",
    }
    timeout_seconds = 420

    def build_command(self, fast: bool = False) -> list[str]:
        url = base_url(self.target)
        if fast:
            return [
                "sqlmap", "-u", url,
                "--crawl=1", "--forms", "--batch",
                "--level=1", "--risk=1",
            ]
        return [
            "sqlmap", "-u", url,
            "--crawl=2", "--forms", "--batch",
            "--level=2", "--risk=1",
        ]

    def get_timeout(self, fast: bool = False) -> int:
        return 120 if fast else 420

    def mock_output(self) -> str:
        return f"""\
        ___
       __H__
 ___ ___[.]_____ ___ ___  {{1.8}}
|_ -| . [.]     | .'| . |
|___|_  [.]_|_|_|__,|  _|
      |_|V...       |_|   https://sqlmap.org

[*] starting @ 15:00:00 /2026-07-07/

[15:00:01] [INFO] testing connection to the target URL
[15:00:01] [INFO] searching for forms
[15:00:02] [INFO] found a total of 2 forms
[15:00:02] [INFO] using '{self.target}' as the output directory
[15:00:03] [INFO] testing URL 'https://{self.target}/search?q=test'
[15:00:03] [INFO] testing 'AND boolean-based blind - WHERE or HAVING clause'
[15:00:05] [INFO] testing 'MySQL >= 5.0 AND error-based - WHERE, HAVING, ORDER BY or GROUP BY clause'
[15:00:07] [WARNING] parameter 'q' does not seem to be injectable
[15:00:07] [INFO] testing URL 'https://{self.target}/login' (POST form)
[15:00:08] [INFO] testing 'AND boolean-based blind - WHERE or HAVING clause'
[15:00:09] [INFO] testing parameter 'username'
sqlmap identified the following injection point(s):
---
Parameter: username (POST)
    Type: boolean-based blind
    Title: AND boolean-based blind - WHERE or HAVING clause
    Payload: username=admin' AND 4821=4821 AND 'a'='a&password=x

    Type: error-based
    Title: MySQL >= 5.0 AND error-based - WHERE, HAVING, ORDER BY or GROUP BY clause
    Payload: username=admin' AND (SELECT 2946 FROM(SELECT COUNT(*),CONCAT(...)) x)-- -&password=x

    Type: time-based blind
    Title: MySQL >= 5.0.12 AND time-based blind
    Payload: username=admin' AND SLEEP(5)-- -&password=x
---
[15:00:14] [INFO] the back-end DBMS is MySQL
web application technology: PHP 7.4.33, Apache 2.4.52
back-end DBMS: MySQL >= 5.0

[15:00:14] [WARNING] parameter 'username' is vulnerable — do not exploit further without written authorization

⚠  Notable findings:
   SQL injection (boolean/error/time-based) in the login form's 'username' POST parameter
   Back-end DBMS fingerprinted: MySQL >= 5.0 — informs payload selection for confirmation

[*] ending @ 15:00:15 /2026-07-07/

[SIMULATED — sqlmap not found on this machine]"""
