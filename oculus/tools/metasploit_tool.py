"""Metasploit Framework wrapper — module search via msfconsole (Docker-based)."""
from __future__ import annotations

import subprocess

from .base import BaseTool, _subprocess_env, resolve_binary


class MetasploitTool(BaseTool):
    name   = "metasploit"
    binary = "docker"
    description = (
        "Search the Metasploit Framework's module database by product/version/CVE — "
        "the OSCP-methodology exploit-lookup step, same idea as searchsploit but a "
        "different (and often more current, actively-maintained) database, and one "
        "that can go straight from 'found a module' to 'configure and run it' inside "
        "the same session. Like `zap`, this runs via Rapid7's own official Docker "
        "image rather than a local install — Metasploit itself (Ruby + ~2500 modules) "
        "is a genuinely heavy framework, not something worth baking into this app's "
        "own image; the first run pulls the image (confirmed ~1.7GB) and msfconsole's "
        "own module-cache boot takes real time even after that. The default command "
        "below only searches (`search <target>; exit`) — it never configures or fires "
        "a module on its own; edit the command to add `use <module>`, `set RHOSTS "
        "...`, `run` etc. yourself once you've found what you're looking for."
    )
    example = 'docker run --rm metasploitframework/metasploit-framework ./msfconsole -q -x "search apache 2.4.49; exit"'
    install_hints = {
        "docker": "Install Docker Desktop (or the Docker Engine) — "
                  "https://docs.docker.com/get-docker/. No separate Metasploit "
                  "install needed; the image is pulled automatically on first run.",
    }
    # msfconsole's own module-cache boot is slow even before the search runs —
    # confirmed comparable to zap's JVM-boot overhead, same generous ceiling.
    timeout_seconds = 300

    def build_command(self, fast: bool = False) -> list[str]:
        # Same honest-placeholder shape as searchsploit_tool.py: this doesn't
        # scan the target, it searches a local module database by whatever
        # product/version/CVE string you give it — the bare target string is
        # a harmless default, not a claim that it's a meaningful search term.
        #
        # "./msfconsole", not bare "msfconsole": confirmed via a real run
        # that the official image never puts msfconsole on PATH — it lives
        # at the image's own WORKDIR (/usr/src/metasploit-framework/
        # msfconsole). The bare name fails with "su-exec: msfconsole: No
        # such file or directory", since `docker run <image> msfconsole
        # ...` overrides the image's own default CMD (which itself uses
        # "./msfconsole") without changing WORKDIR.
        return [
            "docker", "run", "--rm", "metasploitframework/metasploit-framework",
            "./msfconsole", "-q", "-x", f"search {self.target}; exit",
        ]

    def get_timeout(self, fast: bool = False) -> int:
        return 180 if fast else 300

    def run_help(self) -> str:
        # BaseTool's default runs [self.binary, self.help_flag] — that would
        # be `docker -h`, Docker's own help, since "docker" is just the
        # transport here. Run msfconsole's real `search -h` inside the
        # container instead — the actual flags this wrapper's search uses.
        resolved = resolve_binary(self.binary)
        if resolved is None:
            raise FileNotFoundError(self.binary)
        proc = subprocess.run(
            [
                resolved, "run", "--rm", "metasploitframework/metasploit-framework",
                "./msfconsole", "-q", "-x", "search -h; exit",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            env=_subprocess_env(),
            stdin=subprocess.DEVNULL,
        )
        return ((proc.stdout or "") + (proc.stderr or "")).strip()

    def mock_output(self) -> str:
        # Matches msfconsole's real `search` table shape — module path,
        # disclosure date, rank, whether it has a `check` action, one-line
        # description. Illustrative sample hits, not a claim these apply to
        # the actual target searched (same honesty note as searchsploit's
        # own mock — see that file).
        return f"""\
[*] Starting persistent handler(s)...

Matching Modules
================

   #  Name                                          Disclosure Date  Rank       Check  Description
   -  ----                                          ----------------  ----       -----  -----------
   0  exploit/unix/ftp/vsftpd_234_backdoor           2011-07-03        excellent  No     VSFTPD v2.3.4 Backdoor Command Execution
   1  exploit/multi/http/apache_normalize_path_rce   2021-10-05        excellent  Yes    Apache Path Traversal and Remote Code Execution

⚠  No real match for '{self.target}' — that's expected, this searches by
   product/version/CVE, not hostname. Edit the command above with the
   actual service name + version identified via nmap -sV / whatweb /
   httpx first, same as searchsploit.

[SIMULATED — docker (or the metasploitframework/metasploit-framework image) not available on this machine]"""
