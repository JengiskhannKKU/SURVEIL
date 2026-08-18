"""katana tool wrapper — web crawling and endpoint discovery."""
from __future__ import annotations

from .base import BaseTool


class KatanaTool(BaseTool):
    name   = "katana"
    binary = "katana"
    description = "Crawl the target site to discover reachable endpoints/URLs."
    example = "katana -u https://example.com -d 3 -jc -silent -nc"
    install_hints = {
        "brew": "brew install projectdiscovery/tap/katana",
        "go": "go install github.com/projectdiscovery/katana/cmd/katana@latest",
    }

    def build_command(self, fast: bool = False) -> list[str]:
        return [
            "katana",
            "-u", f"https://{self.target}",
            "-d", "1" if fast else "3",
            "-jc", "-silent", "-nc",
        ]

    def mock_output(self) -> str:
        return f"""\
https://{self.target}/
https://{self.target}/login
https://{self.target}/register
https://{self.target}/admin/dashboard
https://{self.target}/api/v1/users
https://{self.target}/api/v1/auth/login
https://{self.target}/api/v1/auth/register
https://{self.target}/api/v1/config
https://{self.target}/api/v2/graphql
https://{self.target}/assets/js/app.bundle.js
https://{self.target}/assets/js/vendor.chunk.js
https://{self.target}/assets/js/runtime.js
https://{self.target}/static/css/main.css
https://{self.target}/static/js/analytics.js
https://{self.target}/wp-login.php
https://{self.target}/wp-admin/admin-ajax.php
https://{self.target}/xmlrpc.php
https://{self.target}/wp-json/wp/v2/users
https://{self.target}/wp-json/wp/v2/posts
https://{self.target}/contact
https://{self.target}/contact?action=submit
https://{self.target}/search?q=
https://{self.target}/profile/settings
https://{self.target}/account/password/reset
https://{self.target}/uploads/2026/
https://{self.target}/backup/db_dump.sql
https://{self.target}/.well-known/security.txt
https://{self.target}/robots.txt
https://{self.target}/sitemap.xml
https://{self.target}/favicon.ico
[SIMULATED — katana not found on this machine]"""
