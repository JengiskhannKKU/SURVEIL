"""OWASP ZAP wrapper — spidering + passive scan via zap-baseline.py."""
from __future__ import annotations

import subprocess

from .base import BaseTool, _subprocess_env, base_url, resolve_binary


class ZapTool(BaseTool):
    name   = "zap"
    binary = "docker"
    description = (
        "OWASP ZAP's baseline scan: spiders the target to map its execution "
        "paths, then runs ZAP's passive scan rules against everything found — "
        "no active attacks, so it's safe to run against a target you're only "
        "authorized to passively assess. Runs via ZAP's own official Docker "
        "image (zap-baseline.py), not a local ZAP install — the first run "
        "pulls the image (confirmed ~1.2GB), and output tends to arrive in "
        "one large burst near the end rather than streaming line-by-line "
        "(the JVM inside the container buffers it), both noticeably heavier "
        "than every other tool wrapped here."
    )
    example = "docker run --rm -t zaproxy/zap-stable zap-baseline.py -t https://example.com -m 5 -I"
    install_hints = {
        "docker": "Install Docker Desktop (or the Docker Engine) — "
                  "https://docs.docker.com/get-docker/. No separate ZAP "
                  "install needed; the image is pulled automatically on "
                  "first run.",
    }
    # zap-baseline.py itself boots a JVM, spiders, then runs passive scan
    # rules — comfortably the slowest single tool wrapped here even before
    # counting the image pull. 10 minutes covers a real -m 5 spider budget
    # plus JVM boot/passive-scan time with room to spare.
    timeout_seconds = 600

    def build_command(self, fast: bool = False) -> list[str]:
        url = base_url(self.target)
        minutes = "1" if fast else "5"
        return [
            "docker", "run", "--rm", "-t", "zaproxy/zap-stable",
            "zap-baseline.py", "-t", url, "-m", minutes,
            # -I: exit 0 even when the passive scan finds WARN/FAIL alerts —
            # finding things is the whole point of running this, and
            # without -I a "successful" scan that found issues would report
            # a nonzero exit code, which oculus's own success/failure
            # status tracking would misread as "the tool run failed"
            # rather than "the tool ran fine and found something."
            "-I",
        ]

    def get_timeout(self, fast: bool = False) -> int:
        return 180 if fast else 600

    def run_help(self) -> str:
        # BaseTool's default runs [self.binary, self.help_flag] — that
        # would be `docker -h`, showing Docker's own help instead of
        # zap-baseline.py's, since "docker" is just the transport here,
        # not the actual tool. Run zap-baseline.py's real -h inside the
        # container instead, same idea, right target.
        resolved = resolve_binary(self.binary)
        if resolved is None:
            raise FileNotFoundError(self.binary)
        proc = subprocess.run(
            [resolved, "run", "--rm", "zaproxy/zap-stable", "zap-baseline.py", "-h"],
            capture_output=True,
            text=True,
            timeout=30,
            env=_subprocess_env(),
            stdin=subprocess.DEVNULL,
        )
        return ((proc.stdout or "") + (proc.stderr or "")).strip()

    def mock_output(self) -> str:
        # Matches zap-baseline.py's real reporting format (confirmed via a
        # live run): "Using the Automation Framework", one PASS line per
        # clean passive-scan rule (dozens, by rule ID), then a WARN-NEW/
        # FAIL-NEW block per rule that actually fired with an affected-URL
        # list, then one tab-separated summary line.
        url = base_url(self.target)
        return f"""\
Using the Automation Framework
Total of 14 URLs
PASS: Vulnerable JS Library (Powered by Retire.js) [10003]
PASS: Cookie Without Secure Flag [10011]
PASS: Content-Type Header Missing [10019]
PASS: Information Disclosure - Suspicious Comments [10027]
PASS: Directory Browsing [10033]
PASS: Strict-Transport-Security Header [10035]
PASS: X-Powered-By Header Information Leak [10037]
PASS: Absence of Anti-CSRF Tokens [10202]
WARN-NEW: X-Frame-Options Header Not Set [10020] x 5
	{url} (200 OK)
	{url}/login (200 OK)
	{url}/admin (200 OK)
WARN-NEW: Cookie No HttpOnly Flag [10010] x 1
	{url}/login (200 OK)
WARN-NEW: Sub Resource Integrity Attribute Missing [90003] x 2
	{url} (200 OK)
FAIL-NEW: 0	FAIL-INPROG: 0	WARN-NEW: 3	WARN-INPROG: 0	INFO: 0	IGNORE: 0	PASS: 41

⚠  Notable findings:
   X-Frame-Options Header Not Set — clickjacking risk, see WSTG-CLNT-09
   Cookie No HttpOnly Flag — session cookie readable via JavaScript/XSS
   Sub Resource Integrity Attribute Missing — a compromised third-party script could run unmodified

[SIMULATED — docker (or the zaproxy/zap-stable image) not available on this machine]"""
