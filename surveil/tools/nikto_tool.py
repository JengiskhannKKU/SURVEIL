"""nikto tool wrapper — web server vulnerability scanner."""
from __future__ import annotations

from .base import BaseTool


class NiktoTool(BaseTool):
    name   = "nikto"
    binary = "nikto"

    def build_command(self) -> list[str]:
        return [
            "nikto",
            "-h", f"https://{self.target}",
            "-Tuning", "1234567890",
            "-nointeractive",
            "-Display", "1",
        ]

    def mock_output(self) -> str:
        return f"""\
- Nikto v2.5.0
---------------------------------------------------------------------------
+ Target IP:          93.184.216.34
+ Target Hostname:    {self.target}
+ Target Port:        443
---------------------------------------------------------------------------
+ SSL Info:        Subject:  /CN={self.target}
                   Ciphers:  TLS_AES_256_GCM_SHA384
                   Issuer:   /C=US/O=Let's Encrypt/CN=R3
+ Start Time:         2026-07-07 15:00:00 (GMT+7)
---------------------------------------------------------------------------
+ Server: nginx/1.18.0 (Ubuntu)
+ /: The anti-clickjacking X-Frame-Options header is present but set to SAMEORIGIN.
+ /: No Content-Security-Policy header detected. See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
+ /: The X-Content-Type-Options header is not set. This could allow the user agent to render the content of the site in a different fashion to the MIME type. See: https://www.netsparker.com/web-vulnerability-scanner/vulnerabilities/missing-content-type-header/
+ OSVDB-3092: /admin/: This might be interesting.
+ OSVDB-3233: /info.php: PHP information file found. Contains sensitive configuration details.
+ OSVDB-3268: /backup/: Directory indexing found.
+ OSVDB-3092: /login.php: Admin login page/section found.
+ OSVDB-6694: /.env: Environment configuration file found. May contain credentials or API keys.
+ OSVDB-3092: /.git/HEAD: Git repository metadata found. Source code may be exposed.
+ /server-status: Apache mod_status found. Server metrics exposed. See: https://httpd.apache.org/docs/2.4/mod/mod_status.html
+ OPTIONS: Allowed HTTP Methods: GET, POST, OPTIONS, HEAD, TRACE .
+ OSVDB-877: TRACE: HTTP TRACE method is active which suggests the host is vulnerable to XST. See: https://owasp.org/www-community/attacks/Cross_Site_Tracing
+ /config.php.bak: Backup configuration file found. May contain database credentials.
+ nginx/1.18.0 appears to be outdated (current is at least 1.25.4).
+ 7915 requests: 0 error(s) and 14 item(s) reported on remote host
+ End Time:           2026-07-07 15:05:42 (GMT+7) (342 seconds)
---------------------------------------------------------------------------
+ 1 host(s) tested
[SIMULATED — nikto not found on this machine]"""
