"""Base class and helpers for all tool wrappers."""
from __future__ import annotations

import shutil
import subprocess
import textwrap
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable


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


def run_tool(
    command: list[str],
    timeout: int = 120,
    on_line: Callable[[str], None] | None = None,
) -> tuple[int, str]:
    """Run *command* via subprocess; stream each line to *on_line* callback."""
    lines: list[str] = []
    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line)
            if on_line:
                on_line(line.rstrip())
        proc.wait(timeout=timeout)
        return proc.returncode, "".join(lines)
    except FileNotFoundError:
        return 127, f"[ERROR] Command not found: {command[0]}"
    except subprocess.TimeoutExpired:
        proc.kill()
        return 124, "".join(lines) + "\n[TIMEOUT]"


class BaseTool(ABC):
    """Abstract base for all tool wrappers."""

    name: str = ""
    binary: str = ""

    def __init__(self, target: str):
        self.target = target

    def is_available(self) -> bool:
        return shutil.which(self.binary) is not None

    @abstractmethod
    def build_command(self) -> list[str]:
        ...

    @abstractmethod
    def mock_output(self) -> str:
        ...

    def run(
        self,
        on_line: Callable[[str], None] | None = None,
    ) -> ToolResult:
        start = time.monotonic()
        if not self.is_available():
            output = self.mock_output()
            elapsed = time.monotonic() - start
            if on_line:
                for line in output.splitlines():
                    on_line(line)
            return ToolResult(
                tool=self.name,
                command=" ".join(self.build_command()),
                output=output,
                exit_code=0,
                elapsed_seconds=elapsed,
                simulated=True,
            )
        cmd = self.build_command()
        exit_code, output = run_tool(cmd, on_line=on_line)
        elapsed = time.monotonic() - start
        return ToolResult(
            tool=self.name,
            command=" ".join(cmd),
            output=output,
            exit_code=exit_code,
            elapsed_seconds=elapsed,
            simulated=False,
        )
