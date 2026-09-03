"""gowitness tool wrapper — screenshot capture of web pages."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .base import BaseTool, _subprocess_env, base_url, resolve_binary

# gowitness v3's default `chromedp` driver `exec`s a real Chrome-compatible
# binary directly — confirmed via a real run against this app's own Docker
# image: "exec: \"google-chrome\": executable file not found in $PATH".
# Despite --chrome-path's own help text implying it downloads one by
# default, that didn't happen here, so locate a real binary ourselves and
# pass it explicitly rather than relying on gowitness to find/fetch one.
_CHROME_BINARY_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
_CHROME_APP_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)


def _find_chrome() -> str | None:
    for name in _CHROME_BINARY_NAMES:
        found = shutil.which(name)
        if found:
            return found
    for path in _CHROME_APP_PATHS:
        if Path(path).is_file():
            return path
    return None


class GowitnessTool(BaseTool):
    name   = "gowitness"
    binary = "gowitness"
    description = (
        "Capture a screenshot of the target's web page for visual triage. "
        "Saved to ./screenshots/ (relative to wherever the backend process "
        "runs) — oculus doesn't display the image itself yet, just the "
        "text summary line gowitness prints (status code, title, whether a "
        "screenshot was captured)."
    )
    example = "gowitness scan single -u https://example.com -T 30"
    install_hints = {"go": "go install github.com/sensepost/gowitness@latest"}

    def build_command(self, fast: bool = False) -> list[str]:
        url = base_url(self.target)
        # gowitness v3 rewrote its CLI entirely from v2's `gowitness single
        # <url> --timeout N` to a `scan` subcommand family — confirmed
        # directly: `go install .../gowitness@latest` now installs v3, and
        # the old v2 invocation fails with 'unknown command "single"'. `-u`
        # (not a bare positional) and `-T` (capital; lowercase `-t` is now
        # thread count, a different flag) are both real v3 flags, confirmed
        # against `gowitness scan single --help`.
        timeout = "10" if fast else "30"
        cmd = ["gowitness", "scan", "single", "-u", url, "-T", timeout]
        chrome = _find_chrome()
        if chrome:
            cmd += ["--chrome-path", chrome]
        return cmd

    def run_help(self) -> str:
        # BaseTool's default runs [self.binary, self.help_flag] — under v3
        # that's top-level `gowitness --help`, which only lists the
        # scan/report/version subcommands, not the actual -u/-T/etc. flags
        # a tester would want to see for the exact invocation this wrapper
        # uses. Run `scan single --help` instead, the right target.
        resolved = resolve_binary(self.binary)
        if resolved is None:
            raise FileNotFoundError(self.binary)
        proc = subprocess.run(
            [resolved, "scan", "single", "--help"],
            capture_output=True,
            text=True,
            timeout=15,
            env=_subprocess_env(),
            stdin=subprocess.DEVNULL,
        )
        return ((proc.stdout or "") + (proc.stderr or "")).strip()

    def mock_output(self) -> str:
        url = base_url(self.target)
        # Matches gowitness v3's real (much terser than v2's) default
        # output — confirmed against a live run: one WARN about no writers
        # configured, then one INFO line with the actual result fields.
        return f"""\
2026-08-27 16:00:00 WARN no writers have been configured. to persist probe results, add writers using --write-* flags
2026-08-27 16:00:04 INFO result 🤖 target={url} status-code=200 title="{self.target.split('.')[0].capitalize()} — Welcome" have-screenshot=true

⚠  Notable findings:
   Screenshot saved to ./screenshots/ for visual review (not yet displayed in oculus's UI)

[SIMULATED — gowitness not found on this machine]"""
