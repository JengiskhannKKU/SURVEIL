"""commix tool wrapper — automated OS command injection detection."""
from __future__ import annotations

from .base import BaseTool, base_url


class CommixTool(BaseTool):
    name   = "commix"
    binary = "commix"
    description = (
        "Test every URL parameter and crawled form for OS command injection — "
        "inputs that might reach a shell (file names, hostnames passed to a "
        "ping/nslookup-style utility, export/convert tools). Runs non-interactively "
        "(--batch) so it never blocks waiting for a prompt."
    )
    example = "commix --url=\"https://example.com/ping?host=1\" --batch --level=1"
    help_flag = "--help"
    install_hints = {
        "apt": "sudo apt install -y commix",
        "git": "git clone https://github.com/commixproject/commix.git "
               "&& sudo ln -s $PWD/commix/commix.py /usr/local/bin/commix "
               "&& chmod +x commix/commix.py",
    }
    timeout_seconds = 240

    def build_command(self, fast: bool = False) -> list[str]:
        url = base_url(self.target)
        if fast:
            return ["commix", "--url", url, "--batch", "--level=1"]
        # --crawl=1 also tests forms discovered one link deep, not just the
        # target URL's own querystring — same idea as sqlmap's --crawl.
        return ["commix", "--url", url, "--batch", "--level=2", "--crawl=1"]

    def get_timeout(self, fast: bool = False) -> int:
        return 90 if fast else 240

    def mock_output(self) -> str:
        url = base_url(self.target)
        return f"""\
                                    _
   ___ ___ ___ ___ ___ ___
  |  _| . |     |     |_ -|
  |___|___|_|_|_|_|_|_|___|  v4.0

+ Copyright (C) 2014-2026 Anastasios Stasinopoulos

[!] Legal disclaimer: usage against targets without prior mutual consent is illegal.

[info] Testing connection to the target URL... [ SUCCESS ]
[info] Testing URL '{url}/ping?host=1'
[info] Setting the (GET) 'host' parameter as testable...
[info] Checking if the target is protected by some kind of WAF/IPS...
[info] Testing the (GET) 'host' parameter for OS command injection...
[info] Heuristic (basic) tests detected that the (GET) 'host' parameter might be injectable.
[info] Testing the classic injection technique...
[info] The (GET) 'host' parameter is vulnerable via the classic injection technique.

  ⚠  Command injection confirmed — 'host' (GET) parameter, classic technique

[info] Skipping further tests for the (GET) 'host' parameter.

[SIMULATED — commix not found on this machine]"""
