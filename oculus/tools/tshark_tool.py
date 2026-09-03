"""tshark wrapper — offline cleartext-credential extraction from a captured pcap."""
from __future__ import annotations

from .base import BaseTool


class TsharkTool(BaseTool):
    name   = "tshark"
    binary = "tshark"
    description = (
        "Extract cleartext credentials/protocol activity from an already-"
        "captured .pcap file — unlike every other tool wrapped here, this "
        "doesn't touch the network target at all, it reads a local file "
        "(a pcap downloaded from the target, saved as this checklist "
        "item's own evidence, or captured during a MITM). The default "
        "command below reads the *target* string as a placeholder file "
        "path — edit it to the real path of the pcap you want analyzed "
        "before running for a result that means anything."
    )
    example = (
        'tshark -r loot.pcap -Y "ftp.request.command || http.request" '
        "-T fields -e frame.time -e ip.src -e ftp.request.command -e ftp.request.arg"
    )
    install_hints = {
        "brew": "brew install wireshark  # installs tshark too",
        "apt": "sudo apt install -y tshark",
    }
    timeout_seconds = 30

    def build_command(self, fast: bool = False) -> list[str]:
        if fast:
            # Quick overview: what protocols/how much traffic is actually
            # in this pcap, before digging into any one of them by name.
            return ["tshark", "-r", self.target, "-q", "-z", "io,phs"]
        # Full pass: pull out the cleartext-credential-bearing protocols
        # an OSCP-style box most commonly leaks over — FTP USER/PASS,
        # HTTP requests (Basic auth headers, form posts), POP3/IMAP/SMTP
        # logins — as flat fields instead of a full packet dump.
        return [
            "tshark", "-r", self.target,
            "-Y", "ftp.request.command || http.request || smtp.req.command "
                  "|| pop.request.command || imap.request",
            "-T", "fields",
            "-e", "frame.time", "-e", "ip.src", "-e", "ip.dst",
            "-e", "ftp.request.command", "-e", "ftp.request.arg",
            "-e", "http.request.method", "-e", "http.request.full_uri",
            "-e", "http.authorization",
        ]

    def mock_output(self) -> str:
        return f"""\
2026-07-07 15:00:01.123456\t10.10.14.1\t10.129.34.27\tUSER\tanonymous
2026-07-07 15:00:01.234567\t10.10.14.1\t10.129.34.27\tPASS\ts3cr3tP@ss

⚠  Notable findings:
   FTP USER/PASS sent in cleartext — a recovered credential is worth
   trying against every other open service too (SSH, the web app login).

Note: the *target* string ('{self.target}') was used as the file path
above — that only produces a real result if it happens to already be a
.pcap. Edit the command to point at the actual capture you want analyzed
(e.g. a file downloaded from the target, or one saved as this item's own
evidence) before running for real.

[SIMULATED — tshark not found on this machine]"""
