"""FTP anonymous-login check — via curl, not the interactive ftp client."""
from __future__ import annotations

from .base import BaseTool


class FtpTool(BaseTool):
    name   = "ftp"
    binary = "curl"
    description = (
        "Check the FTP service for anonymous login — a classic, still "
        "commonly-found misconfiguration and a real OSCP-lab foothold. Uses "
        "curl rather than the interactive `ftp` client (non-interactive, "
        "scriptable, and gives a clean exit code/error instead of a stuck "
        "prompt) to log in as anonymous:anonymous@example.com and list the "
        "root directory. A 0 exit code with a directory listing means "
        "anonymous access is allowed; edit -u for a different credential."
    )
    example = "curl -s --connect-timeout 5 -u anonymous:anonymous@example.com ftp://10.10.10.5/"
    install_hints = {
        "brew": "brew install curl",
        "apt": "sudo apt install -y curl",
    }
    timeout_seconds = 20

    def build_command(self, fast: bool = False) -> list[str]:
        base = [
            "curl", "--connect-timeout", "5",
            "-u", "anonymous:anonymous@example.com",
            f"ftp://{self.target}/",
        ]
        if fast:
            return ["curl", "-s"] + base[1:]
        # Full pass: -v surfaces the actual protocol exchange (230 login
        # response, PWD/LIST replies) instead of just the bare listing.
        return ["curl", "-s", "-v"] + base[1:]

    def get_timeout(self, fast: bool = False) -> int:
        return 10 if fast else 20

    def is_negative_result(self, exit_code: int) -> bool:
        # curl's CURLE_LOGIN_DENIED — the server actively refused the
        # anonymous credential rather than curl failing to run the check
        # at all. Confirmed against a real vsftpd 3.0.3 instance
        # (`530 Login incorrect.`) that returns exactly this code for a
        # correctly-denied anonymous login — a clean, completed negative
        # test, not a tool failure, so the checklist item should still
        # land on DONE rather than FAILED (red) for it. Every other
        # non-zero code (7 = couldn't connect, 28 = timeout, ...) is a
        # real failure and is deliberately left alone.
        return exit_code == 67

    def mock_output(self) -> str:
        return f"""\
*   Trying {self.target}:21...
* Connected to {self.target} (21) port 21
< 220 (vsFTPd 3.0.3)
> USER anonymous
< 331 Please specify the password.
> PASS anonymous@example.com
< 230 Login successful.
> PWD
< 257 "/" is the current directory
> TYPE I
< 200 Switching to Binary mode.
> PASV
< 227 Entering Passive Mode.
> LIST
< 150 Here comes the directory listing.
-rw-r--r--    1 0        0             120 Jan 02 03:04 notes.txt
drwxr-xr-x    2 0        0            4096 Jan 02 03:04 backup
< 226 Directory send OK.

⚠  Notable findings:
   Anonymous FTP login accepted — see WSTG-ATHN-02 / OSCP-ENUM-10
   World-readable directory contents visible without credentials

[SIMULATED — curl not found on this machine, target: {self.target}]"""
