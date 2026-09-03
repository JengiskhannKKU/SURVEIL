"""redis-cli wrapper — unauthenticated Redis access check."""
from __future__ import annotations

from .base import BaseTool


class RedisTool(BaseTool):
    name   = "redis"
    binary = "redis-cli"
    description = (
        "Check Redis for unauthenticated access — Redis has no auth enabled "
        "by default, and an exposed instance is a real, well-known foothold "
        "(CONFIG SET dir/dbfilename + SAVE to drop a webshell or an SSH "
        "authorized_keys entry is the classic follow-on). The default "
        "command just runs PING/INFO to confirm access without auth; once "
        "confirmed, follow up manually with `redis-cli -h <target>` "
        "interactively for the exploitation step."
    )
    example = "redis-cli -h 10.10.10.5 --no-auth-warning PING"
    install_hints = {
        "brew": "brew install redis",
        "apt": "sudo apt install -y redis-tools",
    }
    timeout_seconds = 20

    def build_command(self, fast: bool = False) -> list[str]:
        base = ["redis-cli", "-h", self.target, "--no-auth-warning"]
        if fast:
            return base + ["PING"]
        return base + ["INFO", "server"]

    def get_timeout(self, fast: bool = False) -> int:
        return 10 if fast else 20

    def mock_output(self) -> str:
        return f"""\
PONG
# Server
redis_version:6.0.16
os:Linux 5.4.0-x86_64
process_id:812
tcp_port:6379
run_id:8f3c1a2b9d4e5f60718293a4b5c6d7e8f9012345
uptime_in_seconds:184320
config_file:

⚠  Notable findings:
   Redis reachable at {self.target}:6379 with no authentication required
   CONFIG SET dir/dbfilename + SAVE can be used to write an arbitrary file — see OSCP-EXPLOIT phase

[SIMULATED — redis-cli not found on this machine, target: {self.target}]"""
