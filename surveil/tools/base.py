"""Base class and helpers for all tool wrappers."""
from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import textwrap
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def base_url(target: str) -> str:
    """Turn a bare target into a URL, respecting an explicit scheme.

    - If *target* already has a scheme (e.g. the tester typed
      "http://192.168.2.11"), it's used as-is.
    - A bare IPv4 target defaults to http:// — internal/lab targets are
      commonly plain HTTP with no TLS configured, and hardcoding https://
      here (the previous behavior in several wrappers) meant every request
      failed to connect and the tool "succeeded" with silently zero
      results, indistinguishable from a real empty scan.
    - A bare hostname defaults to https://, still the more common case for
      a real domain.
    """
    if "://" in target:
        return target
    host = target.split(":")[0]
    scheme = "http" if _IPV4_RE.match(host) else "https"
    return f"{scheme}://{target}"


@dataclass
class ToolResult:
    tool: str
    command: str
    output: str
    exit_code: int
    elapsed_seconds: float
    simulated: bool = False          # True when tool not installed → mock data

    @property
    def success(self) -> bool:
        return self.exit_code == 0


def _extra_bin_dirs() -> list[Path]:
    """Directories to search for tool binaries beyond $PATH.

    `go install` puts binaries in $GOBIN (or $GOPATH/bin, which defaults to
    ~/go/bin) — neither is on PATH by default on a lot of setups. Without
    this, a tool installed via `go install` (httpx, subfinder, nuclei, dnsx,
    katana, gowitness — see each wrapper's install_hints) reports as "not
    installed" and the app silently falls back to simulated output.
    """
    dirs: list[Path] = []
    gobin = os.environ.get("GOBIN")
    if gobin:
        dirs.append(Path(gobin))
    gopath = os.environ.get("GOPATH") or str(Path.home() / "go")
    dirs.append(Path(gopath) / "bin")
    return dirs


def resolve_binary(name: str) -> str | None:
    """Find *name* on PATH, or in a known extra install location (e.g. Go's bin dir).

    Returns the resolved absolute path (for actually invoking it — a bare
    name only found in an extra dir won't resolve via subprocess's own PATH
    lookup), or None if not found anywhere.
    """
    found = shutil.which(name)
    if found:
        return found
    for directory in _extra_bin_dirs():
        candidate = directory / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _subprocess_env() -> dict[str, str]:
    """Environment for a spawned tool subprocess: this process's own env,
    with the Go bin dirs (see `_extra_bin_dirs()`) prepended to PATH.

    `BaseTool.run()` already resolves *cmd[0]* to a full path via
    `resolve_binary()` before calling `run_tool()`, which covers a bare
    "dnsx" invocation. But dnsx's own wrapper (see `dnsx_tool.py`) has to
    shell out — `["sh", "-c", "echo target | dnsx ..."]` — since dnsx reads
    its target from stdin; there, *cmd[0]* is "sh", not "dnsx", so that
    resolution never reaches the *nested* dnsx call at all, and the child
    shell falls back to its own inherited PATH, which may not include
    dnsx's actual location (a `go install` binary, PATH-invisible by
    default). Prepending the same extra dirs to the subprocess's PATH here
    fixes that case and any other shell-wrapped tool the same way, without
    needing to parse/rewrite each such command string individually.
    """
    env = dict(os.environ)
    extra = [str(d) for d in _extra_bin_dirs() if d.is_dir()]
    if extra:
        env["PATH"] = os.pathsep.join(extra) + os.pathsep + env.get("PATH", "")
    return env


def run_tool(
    command: list[str],
    timeout: int = 120,
    on_line: Callable[[str], None] | None = None,
) -> tuple[int, str]:
    """Run *command* via subprocess; stream each line to *on_line* callback.

    The read loop runs in a background thread so *timeout* is enforced by
    wall-clock time regardless of whether the process is producing output —
    a plain `for line in proc.stdout: ...` followed by `proc.wait(timeout=)`
    (the previous implementation) blocks on the read itself with no
    deadline, so *timeout* only ever took effect after the process had
    already exited on its own. That made the timeout a no-op for any tool
    that hangs or runs long without emitting a line.
    """
    lines: list[str] = []
    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=_subprocess_env(),
            # Own process group so a timeout can kill the whole tree (see
            # below) — several tools here are themselves shell scripts that
            # spawn their own subprocesses (testssl.sh -> openssl, for one),
            # and killing only the direct child leaves those grandchildren
            # holding the stdout pipe open, so the reader thread never sees
            # EOF and the timeout effectively doesn't end the run.
            start_new_session=True,
        )
    except FileNotFoundError:
        return 127, f"[ERROR] Command not found: {command[0]}"

    def reader() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line)
            if on_line:
                on_line(line.rstrip())

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass  # already gone
        thread.join(timeout=5)  # let the reader drain whatever's left and exit
        return 124, "".join(lines) + "\n[TIMEOUT]"

    proc.wait()
    return proc.returncode, "".join(lines)


class BaseTool(ABC):
    """Abstract base for all tool wrappers."""

    name: str = ""
    binary: str = ""

    # Shown in the TUI's Run Tool dialog as a guide for what this tool does
    # and what a real invocation looks like.
    description: str = ""
    example: str = ""

    # Directory/file brute-forcing tools take a wordlist via -w <path>; the
    # TUI shows a wordlist picker for these instead of just a free-text edit.
    uses_wordlist: bool = False

    # True for tools that do subdomain/DNS enumeration against a domain
    # name (subfinder, amass, dnsx) — structurally meaningless against a
    # bare IP target (there's no such thing as "subdomains of an IP"), so
    # they'll reliably run "successfully" and return nothing. The UI warns
    # before running one of these against an IP-looking target.
    domain_only: bool = False

    # Install commands by package manager, shown to the tester when the
    # binary isn't on PATH (so they know how to get real output instead of
    # the simulated fallback). Keys are free-form labels ("brew", "apt",
    # "go", "pip", "gem", ...); omit any that don't apply to this tool.
    install_hints: dict[str, str] = {}

    # Named scan-mode presets beyond the plain Fast/Full toggle (e.g. nmap's
    # UDP scan, all-ports scan, OS detection). Maps mode key -> human label,
    # shown as a "Scan mode" dropdown in the Run Tool dialog instead of the
    # Fast switch when non-empty. Empty for tools that only have Fast/Full.
    modes: dict[str, str] = {}

    # Ceiling for how long a real subprocess run is allowed before being
    # killed, in seconds. The old blanket 120s default silently truncated
    # several tools with longer scan budgets of their own (amass's -timeout
    # flag defaults to far longer than that, for instance). Override per
    # tool as needed; AmassTool overrides get_timeout() directly since its
    # own -timeout flag (minutes) differs sharply between fast and full.
    timeout_seconds: int = 180

    def __init__(self, target: str):
        self.target = target

    def is_available(self) -> bool:
        return resolve_binary(self.binary) is not None

    def get_timeout(self, fast: bool = False) -> int:
        return self.timeout_seconds

    @abstractmethod
    def build_command(self, fast: bool = False) -> list[str]:
        """Build the command line to run.

        *fast* selects a quicker, narrower-scope variant (fewer ports/
        templates/threads/timeout) for a fast first pass; the default
        (``False``) is the full/thorough scan.
        """
        ...

    @abstractmethod
    def mock_output(self) -> str:
        ...

    def build_command_for_mode(self, mode: str) -> list[str]:
        """Build the command line for a named entry in *modes*.

        Default implementation only understands "quick" (fast=True) and
        "full" (fast=False), so tools that don't override *modes* still work
        if called with those two keys. Tools with richer modes (see
        NmapTool) override this to handle their own mode keys.
        """
        if mode == "quick":
            return self.build_command(fast=True)
        return self.build_command(fast=False)

    def run(
        self,
        on_line: Callable[[str], None] | None = None,
        override_command: list[str] | None = None,
        fast: bool = False,
    ) -> ToolResult:
        """Run the tool.

        If *override_command* is given (e.g. a tester-edited command line),
        it always executes for real — a missing binary surfaces as a real
        error rather than silently falling back to simulated output, since
        the tester explicitly chose that command. Otherwise *fast* selects
        which built-in command variant (fast vs. full) to run.
        """
        start = time.monotonic()
        if override_command is None and not self.is_available():
            output = self.mock_output()
            elapsed = time.monotonic() - start
            if on_line:
                for line in output.splitlines():
                    on_line(line)
            return ToolResult(
                tool=self.name,
                command=" ".join(self.build_command(fast=fast)),
                output=output,
                exit_code=0,
                elapsed_seconds=elapsed,
                simulated=True,
            )
        cmd = override_command if override_command is not None else self.build_command(fast=fast)
        # A tester-edited or scan-mode command may be more thorough than the
        # plain default, so use the "full" timeout ceiling for it rather
        # than whatever *fast* happens to be set to.
        timeout = self.get_timeout(fast=False if override_command is not None else fast)
        # Resolve the binary to its full path in case it's only found via
        # the extra search locations (e.g. Go's bin dir) — subprocess's own
        # PATH lookup won't find it there on its own.
        resolved = resolve_binary(cmd[0])
        exec_cmd = [resolved, *cmd[1:]] if resolved else cmd
        exit_code, output = run_tool(exec_cmd, timeout=timeout, on_line=on_line)
        elapsed = time.monotonic() - start
        return ToolResult(
            tool=self.name,
            command=" ".join(cmd),
            output=output,
            exit_code=exit_code,
            elapsed_seconds=elapsed,
            simulated=False,
        )
