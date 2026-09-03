"""searchsploit tool wrapper — offline exploit-db search by service/version."""
from __future__ import annotations

from .base import BaseTool


class SearchsploitTool(BaseTool):
    name   = "searchsploit"
    binary = "searchsploit"
    description = (
        "Search the local exploit-db mirror for known exploits by product/version — "
        "the standard OSCP-methodology step after fingerprinting a service (nmap -sV, "
        "whatweb, httpx) turns up a concrete name and version. Unlike every other tool "
        "wrapped here, this doesn't scan the target at all — there's nothing network-"
        "facing about it, it just greps a local offline database — so the default "
        "command below searches for the bare target string as a harmless placeholder; "
        "edit it to the actual product/version you identified (e.g. 'vsftpd 2.3.4', "
        "'Apache 2.4.49') before running for a result that means anything."
    )
    example = "searchsploit --disable-colour apache 2.4.49"
    install_hints = {
        "apt": "sudo apt install -y exploitdb",
        "brew": "brew install exploitdb",
        "git": "git clone https://gitlab.com/exploit-database/exploitdb.git",
    }

    def build_command(self, fast: bool = False) -> list[str]:
        # No fast/full distinction — it's a single local database lookup,
        # not a scan with a time budget to trade off. --disable-colour:
        # confirmed via a real run that searchsploit emits ANSI highlight
        # codes on its matched search terms even when stdout is a pipe
        # (not a TTY) — this app has no ANSI-stripping anywhere in its
        # output pipeline, so left on, those escape codes would show up
        # as literal junk text in the UI instead of being rendered.
        return ["searchsploit", "--disable-colour", self.target]

    def mock_output(self) -> str:
        # Real searchsploit output shape (confirmed against its own default
        # table format): a title/path table, then a Shellcodes summary line.
        # The target itself won't genuinely match anything real (it's a
        # hostname/IP, not a product name) — these are illustrative sample
        # hits so the demo output at least looks like a real exploitdb
        # search, not a claim that these specific CVEs apply to this target.
        return f"""\
Exploits: No Results
Shellcodes: No Results

⚠  No matches for '{self.target}' — that's expected, searchsploit searches
   by product/version, not hostname. Edit the command above with the
   actual service name + version identified via nmap -sV / whatweb /
   httpx first, e.g.:

Exploit Title                                                              |  Path
---------------------------------------------------------------------------|---------------------------------
vsftpd 2.3.4 - Backdoor Command Execution                                  | unix/remote/49757.py
Apache 2.4.49 - Path Traversal & Remote Code Execution (CVE-2021-41773)    | multiple/webapps/50383.sh
ProFTPD 1.3.5 - 'mod_copy' Remote Command Execution                        | linux/remote/36742.py
---------------------------------------------------------------------------|---------------------------------
Shellcodes: No Results

[SIMULATED — searchsploit not found on this machine]"""
