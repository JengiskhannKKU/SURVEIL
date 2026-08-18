"""nmap tool wrapper — port scanning and service fingerprinting."""
from __future__ import annotations

from .base import BaseTool


class NmapTool(BaseTool):
    name   = "nmap"
    binary = "nmap"
    description = "Port-scan common web ports and fingerprint service versions/scripts."
    example = "nmap -sV -sC -p 80,443,8080,8443,8000,8888,3000 --open -T4 example.com"
    install_hints = {
        "brew": "brew install nmap",
        "apt": "sudo apt install -y nmap",
    }

    def build_command(self, fast: bool = False) -> list[str]:
        if fast:
            return ["nmap", "-sV", "--top-ports", "20", "--open", "-T5", self.target]
        return [
            "nmap", "-sV", "-sC",
            "-p", "80,443,8080,8443,8000,8888,3000",
            "--open", "-T4",
            self.target,
        ]

    def mock_output(self) -> str:
        return f"""\
Starting Nmap 7.94 ( https://nmap.org ) at 2026-07-07 15:00 +07
Nmap scan report for {self.target} (93.184.216.34)
Host is up (0.032s latency).

PORT     STATE SERVICE   VERSION
80/tcp   open  http      nginx 1.18.0 (Ubuntu)
| http-title: Welcome to {self.target}
|_Requested resource was https://{self.target}/
| http-methods:
|   Supported Methods: GET POST OPTIONS TRACE
|_  Potentially risky methods: TRACE
443/tcp  open  ssl/http  nginx 1.18.0 (Ubuntu)
| ssl-cert: Subject: commonName={self.target}
| Not valid before: 2025-01-01T00:00:00
|_Not valid after:  2026-01-01T00:00:00
| http-security-headers:
|   X-Frame-Options: SAMEORIGIN
|_  (No Content-Security-Policy detected)
8080/tcp open  http      Apache Tomcat 9.0.73
|_http-title: Apache Tomcat/9.0.73
| http-auth-info:
|_  Authentication: Basic realm="Tomcat Manager Application"

Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Nmap done: 1 IP address (1 host up) scanned in 18.23 seconds
[SIMULATED — nmap not found on this machine]"""
