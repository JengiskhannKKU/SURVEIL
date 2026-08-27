"""dalfox tool wrapper — reflected/DOM XSS scanning."""
from __future__ import annotations

from .base import BaseTool, base_url


class DalfoxTool(BaseTool):
    name   = "dalfox"
    binary = "dalfox"
    description = (
        "Fuzz every URL parameter for reflected and DOM-based XSS, confirming "
        "each hit with a real headless-browser-verified payload rather than "
        "just a raw reflection (fewer false positives than a generic scanner). "
        "Doesn't cover stored XSS — that needs a submit-then-revisit workflow "
        "a URL-fuzzing tool can't do on its own; test that manually."
    )
    example = "dalfox url https://example.com/search?q=test --silence"
    install_hints = {
        "brew": "brew install dalfox",
        "go": "go install github.com/hahwul/dalfox/v2@latest",
    }
    timeout_seconds = 180

    def build_command(self, fast: bool = False) -> list[str]:
        url = base_url(self.target)
        if fast:
            # --skip-bav skips dalfox's extra "basic another vulnerability"
            # checks (SQLi/SSTI/open-redirect probes bundled alongside its
            # XSS fuzzing) so the fast pass stays focused and quick.
            return ["dalfox", "url", url, "--skip-bav", "--silence"]
        return ["dalfox", "url", url, "--silence"]

    def get_timeout(self, fast: bool = False) -> int:
        return 60 if fast else 180

    def mock_output(self) -> str:
        url = base_url(self.target)
        return f"""\
 _____        ___ ______
|  __ \\      | | |  ____|
| |  | | __ _| | | |__ ___  __
| |  | |/ _` | | |  __/ _ \\ \\/ /
| |__| | (_| | | | | | (_) >  <
|_____/ \\__,_|_|_|_|  \\___/_/\\_\\        v2.9.1

[*] Target URL: {url}
[*] Generated 12 parameter test case(s)
[*] Start scanning..

[POC][GET] Payload: <script>alert(1)</script>
 URL: {url}/search?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E
 Param: q
 Type: Reflected

[POC][GET] Payload: "><img src=x onerror=alert(document.domain)>
 URL: {url}/profile?name=%22%3E%3Cimg+src%3Dx+onerror%3Dalert(document.domain)%3E
 Param: name
 Type: Reflected

[*] Scan completed in 22.8s — 2 vulnerable parameter(s) found

[SIMULATED — dalfox not found on this machine]"""
