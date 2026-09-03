"""mysql client wrapper — unauthenticated/default-credential database enumeration."""
from __future__ import annotations

from .base import BaseTool


class MysqlTool(BaseTool):
    name   = "mysql"
    binary = "mysql"
    description = (
        "Test the MySQL/MariaDB service itself for unauthenticated access — "
        "default install root with no password is a real, commonly-tested "
        "OSCP finding, distinct from SQL injection via a web app (see "
        "sqlmap for that). The default command tries root/blank against port "
        "3306 and lists every database plus the user table if it connects; "
        "edit -u/-p for a different credential, or add -P <port> if MySQL is "
        "on a non-default port."
    )
    example = 'mysql -h 10.10.10.5 -u root --connect-timeout=5 -e "SHOW DATABASES;"'
    install_hints = {
        "brew": "brew install mysql-client",
        "apt": "sudo apt install -y mysql-client",
    }
    timeout_seconds = 30

    def build_command(self, fast: bool = False) -> list[str]:
        base = [
            "mysql", "-h", self.target, "-u", "root",
            "--connect-timeout=5", "--protocol=TCP",
        ]
        if fast:
            # Fast pass: just prove blank-root auth works at all.
            return base + ["-e", "SELECT VERSION(), CURRENT_USER();"]
        # Full pass: also enumerate what's actually there once connected.
        return base + [
            "-e",
            "SHOW DATABASES; SELECT user, host, authentication_string FROM mysql.user;",
        ]

    def get_timeout(self, fast: bool = False) -> int:
        return 15 if fast else 30

    def mock_output(self) -> str:
        return f"""\
+--------------------+
| Database           |
+--------------------+
| information_schema |
| mysql              |
| performance_schema |
| app_db             |
+--------------------+
+------+-----------+-------------------------------------------+
| user | host      | authentication_string                      |
+------+-----------+-------------------------------------------+
| root | %         |                                             |
| app  | localhost | *2470C0C06DEE42FD1618BB99005ADCA2EC9D1E19  |
+------+-----------+-------------------------------------------+

⚠  Notable findings:
   root@{self.target} authenticated with no password — critical, immediate remediation required
   root has host '%' (any host) — remote root login is possible

[SIMULATED — mysql client not found on this machine, target: {self.target}]"""
