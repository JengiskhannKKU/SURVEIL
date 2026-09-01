"""arjun tool wrapper — hidden HTTP parameter discovery."""
from __future__ import annotations

from .base import BaseTool, base_url


class ArjunTool(BaseTool):
    name   = "arjun"
    binary = "arjun"
    description = (
        "Discover hidden/undocumented HTTP GET parameters via brute force. "
        "Full mode uses arjun's --stable flag for fewer false positives, which "
        "arjun's own code forces to single-threaded regardless of any -t flag — "
        "genuinely slow (can take several minutes) against the full ~26k-word "
        "default list, hence the long timeout budget below. Fast mode trades "
        "that thoroughness for arjun's own smaller ~800-word list instead."
    )
    example = "arjun -u https://example.com --stable"
    install_hints = {"pip": "pip install arjun"}
    # --stable (used by the non-fast command below) forces arjun's own
    # thread count to 1 no matter what -t is passed — confirmed directly in
    # arjun's source (__main__.py: "if mem.var['stable'] ...: threads = 1").
    # That, combined with the ~26k-word default list, routinely took well
    # over the old 180s blanket default against a real target and timed
    # out — this is what a real bug report against 192.168.2.15 traced
    # back to. 900s is a generous budget for a single-threaded full-list
    # run; get_timeout() below applies it only to the non-fast command.
    timeout_seconds = 900

    def build_command(self, fast: bool = False) -> list[str]:
        url = base_url(self.target)
        if fast:
            # -w small: arjun's own bundled ~800-word list — keeps Fast
            # mode actually fast, unlike the default ~26k-word list used
            # below, which takes minutes even multi-threaded.
            return ["arjun", "-u", url, "-w", "small", "-t", "20"]
        # No -t here: arjun silently ignores it under --stable (see above),
        # so passing one would just be misleading about what's controlling
        # the speed.
        return ["arjun", "-u", url, "--stable"]

    def get_timeout(self, fast: bool = False) -> int:
        return 90 if fast else 900

    def mock_output(self) -> str:
        # GET only, matching the real default: arjun's own -m METHOD flag
        # defaults to GET and neither build_command() variant above adds
        # -m POST, so a real run never actually probes POST bodies unless
        # a tester edits the command to add one.
        return f"""\
[arjun] Hidden HTTP parameter discovery for: {self.target}

    _
   /_| _ '
  (  |/ /(//)
      _/

[*] Probing {self.target} for hidden parameters...
[*] Testing with default wordlist (large, ~26k params) — single-threaded, stable mode

[GET] https://{self.target}
  [+] debug          — reflected in response (200 OK, +312 bytes)
  [+] admin          — reflected in response (200 OK, +89 bytes)
  [+] test           — reflected in response (200 OK, +45 bytes)
  [+] callback       — reflected in response (200 OK, +227 bytes)
  [+] redirect       — triggers 302 redirect
  [+] next           — triggers 302 redirect

[*] Scan completed in 4m 12s
[*] Found 6 hidden parameters

⚠  Notable findings:
   debug     — may enable verbose error output or debug panels
   admin     — could expose administrative functionality
   redirect  — potential open-redirect vector
   next      — potential open-redirect vector
   callback  — may be exploitable for SSRF or XSS via JSONP

[SIMULATED — arjun not found on this machine]"""
