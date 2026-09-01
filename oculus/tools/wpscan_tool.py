"""wpscan tool wrapper — WordPress-specific vulnerability scanner."""
from __future__ import annotations

from .base import BaseTool, base_url


class WpscanTool(BaseTool):
    name   = "wpscan"
    binary = "wpscan"
    description = "Enumerate WordPress version, plugins/themes, and known vulnerabilities."
    example = "wpscan --url https://example.com --enumerate vp,vt,u --no-banner --format cli"
    help_flag = "--help"
    install_hints = {
        "brew": "brew install wpscanteam/tap/wpscan",
        "gem": "gem install wpscan",
    }
    timeout_seconds = 300

    def build_command(self, fast: bool = False) -> list[str]:
        url = base_url(self.target)
        if fast:
            return [
                "wpscan",
                "--url", url,
                "--enumerate", "vp",
                "--no-banner",
                "--format", "cli",
            ]
        return [
            "wpscan",
            "--url", url,
            "--enumerate", "vp,vt,u",
            "--no-banner",
            "--format", "cli",
        ]

    def mock_output(self) -> str:
        return f"""\
[wpscan] WordPress vulnerability scan for: {self.target}

[+] URL: https://{self.target}/ [200 OK]
[+] Started: Mon Jul 14 09:15:23 2025

[+] WordPress version 6.4.3 identified (Insecure, released on 2024-01-30)
 |  Found By: Meta Generator (passive detection)
 |  Confirmed By: Unique Fingerprinting (aggressive detection)
 |  [!] 2 vulnerabilities identified:
 |
 |  [!] Title: WordPress 6.4.x — Authenticated Stored XSS via Block Editor
 |      Fixed in: 6.4.4
 |      Reference: https://wpscan.com/vulnerability/xxxx-xxxx-xxxx
 |
 |  [!] Title: WordPress 6.4.x — SQL Injection in WP_Query (authenticated)
 |      Fixed in: 6.4.5
 |      Reference: https://wpscan.com/vulnerability/yyyy-yyyy-yyyy

[+] WordPress theme in use: flavor-developer
 |  Location: https://{self.target}/wp-content/themes/flavor-developer/
 |  Detected By: CSS Style In Homepage (passive detection)
 |  Version: 2.1.0 (80% confidence)
 |  [!] The version is out of date, the latest version is 2.3.1

[+] Enumerating Vulnerable Plugins (via passive methods)
 |  [+] contact-form-7
 |   |  Location: https://{self.target}/wp-content/plugins/contact-form-7/
 |   |  Version: 5.8.3 (100% confidence)
 |   |  [!] Title: Contact Form 7 < 5.8.4 — Reflected XSS
 |   |      Fixed in: 5.8.4
 |
 |  [+] elementor
 |   |  Location: https://{self.target}/wp-content/plugins/elementor/
 |   |  Version: 3.18.2 (100% confidence)
 |   |  No known vulnerabilities for this version

[+] Enumerating Vulnerable Themes (via passive methods)
 |  No vulnerable themes found.

[+] Enumerating Users (via brute force)
 |  [+] admin         (ID: 1) — found via Author Id Brute Forcing
 |  [+] editor        (ID: 2) — found via Author Id Brute Forcing
 |  [+] contributor   (ID: 5) — found via Author Id Brute Forcing

[+] Finished: Mon Jul 14 09:16:04 2025
[+] Elapsed time: 00:00:41

⚠  Notable findings:
   WordPress core is outdated (6.4.3) — 2 known vulnerabilities
   contact-form-7 plugin has a known Reflected XSS (< 5.8.4)
   Theme flavor-developer is outdated (2.1.0 → 2.3.1)
   3 user accounts enumerated — brute-force target surface

[SIMULATED — wpscan not found on this machine]"""
