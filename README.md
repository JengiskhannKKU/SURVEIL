# surveil

**Deterministic, OWASP WSTG checklist-driven web application penetration testing.**

surveil is a terminal-native tool that brings together web application enumeration tooling under a single interactive interface. It provides a structured OWASP WSTG checklist, deterministic tool orchestration (no AI in the enumeration loop), finding management with CVSS scoring, and professional report generation — all offline.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  surveil  (CLI / TUI)                       │
├────────────────┬────────────────────┬───────────────────────┤
│  Tool          │  Checklist &       │  Reporting            │
│  Orchestration │  State Engine      │  Engine               │
│  Layer         │                    │                       │
│                │  OWASP WSTG items  │  Markdown (.md)       │
│  nmap          │  Status tracking   │  Word (.docx)         │
│  httpx         │  Finding mgmt      │  CVSS v3.1 scoring    │
│  whatweb       │  Textual TUI       │  OWASP / CWE mapping  │
│  wafw00f       │  JSON persistence  │  Audit trail          │
│  subfinder     │  Auto-extraction   │                       │
│  nuclei, arjun │  (unverified       │                       │
│  dnsx, ffuf    │   findings)        │                       │
│  gobuster      │                    │                       │
│  gowitness     │                    │                       │
│  katana, nikto │                    │                       │
│  testssl       │                    │                       │
│  wpscan, amass │                    │                       │
└────────────────┴────────────────────┴───────────────────────┘
```

- **Tool Orchestration Layer** — wraps 16 tools via subprocess: `nmap`, `httpx`, `whatweb`, `wafw00f`, `subfinder`, `nuclei`, `arjun`, `dnsx`, `gowitness`, `wpscan`, `amass`, `ffuf`, `gobuster`, `katana`, `nikto`, `testssl` (see `TOOL_REGISTRY` in `surveil/tools/__init__.py`). Falls back to realistic simulated output when a tool is not installed (demo mode).
- **Checklist & State Engine** — OWASP WSTG INFO + CONF items (20 items) with status tracking, Textual TUI, JSON persistence.
- **Auto-Finding Extraction** (`surveil/findings_extractor.py`) — parses raw output from `nmap`, `httpx`, `whatweb`, `nuclei`, `wafw00f`, `subfinder`, and `nikto` into `Finding` objects (auto CVSS scoring, OWASP/CWE mapping) flagged `verified=False`, so a tester gets a starting point to confirm or dismiss rather than a blank checklist.
- **Reporting Engine** — CVSS v3.1 base score calculator, OWASP/CWE metadata, Markdown and .docx export.

---

## Run with Docker (recommended — works on any machine)

The Docker image bundles Python, the `surveil` CLI/TUI, and all 16
enumeration binaries (`nmap`, `whatweb`, `wafw00f`, `subfinder`, `httpx`,
`nuclei`, `arjun`, `dnsx`, `gowitness`, `wpscan`, `amass`, `ffuf`,
`gobuster`, `katana`, `nikto`, `testssl.sh`), so scans produce real tool
output instead of the simulated fallback — no local Python setup or tool
installation required.

Note: `gowitness` needs a Chromium/Chrome binary at runtime to actually
capture screenshots, which the image does not bundle (it adds real
weight for one tool's use case) — expect `gowitness` to error rather than
silently fall back to simulated output unless you install a browser in
a derived image.

### 1. Build the image

```bash
docker compose build
# or, without compose:
docker build -t surveil:latest .
```

### 2. Run the CLI

```bash
# Create a new engagement
docker compose run --rm surveil new --target example.com --name "Example Corp Assessment"

# Check status
docker compose run --rm surveil status

# Generate a report (written inside the container's /data volume)
docker compose run --rm surveil report --format md --output /data/report.md
```

Without compose, using `docker run` directly (mount a named volume so
engagement state and reports survive across container runs):

```bash
docker volume create surveil-data

docker run --rm -it \
  -v surveil-data:/data \
  surveil:latest new --target example.com --name "Example Corp Assessment"

docker run --rm -it -v surveil-data:/data surveil:latest status
```

### 3. Open the interactive TUI

The TUI needs an interactive TTY:

```bash
docker compose run --rm surveil tui
# or
docker run --rm -it -v surveil-data:/data surveil:latest tui
```

### 4. Copy a generated report out of the container

Reports are written into the `/data` volume inside the container. To copy
one to your host:

```bash
docker run --rm -v surveil-data:/data -v "$(pwd)":/out alpine \
  cp /data/report_<engagement-id>.md /out/
```

(Or generate straight into a bind-mounted directory: add
`-v "$(pwd)/reports:/data/reports"` and pass `--output /data/reports/report.md`.)

### Data persistence

Engagement state (`~/.surveil/engagements/`) lives under `/data` inside
the container, which is backed by the `surveil-data` Docker volume (or
whatever volume/bind-mount you attach at `/data`). Nothing is sent outside
the container or over the network except the actual scans you run against
your target.

---

## Run without Docker (local Python)

```bash
pip install -e .
```

Requires Python ≥ 3.9. Enumeration tools (`nmap`, `httpx`, `whatweb`,
`wafw00f`, `subfinder`, `nuclei`, `arjun`, `dnsx`, `gowitness`, `wpscan`,
`amass`) are optional — any tool not found on `PATH` falls back to
simulated output automatically.

### Quick Start

```bash
# 1. Create a new engagement
surveil new --target example.com --name "Example Corp Assessment"

# 2. Open the interactive TUI
surveil tui

# 3. (or) Check status from the command line
surveil status

# 4. Generate a report
surveil report --format md --output report.md
```

---

## CLI Reference

| Command | Description |
|---|---|
| `surveil new --target <host>` | Create a new engagement with 20 OWASP WSTG items |
| `surveil list` | List all saved engagements |
| `surveil tui` | Open the interactive Textual TUI |
| `surveil status` | Show checklist progress and severity summary |
| `surveil report -f md` | Generate Markdown report |
| `surveil report -f docx` | Generate Word document report |
| `surveil add-finding --item WSTG-INFO-02 ...` | Add a finding from CLI |
| `surveil delete <id>` | Delete an engagement |

---

## TUI Key Bindings

| Key | Action |
|---|---|
| `↑ / ↓` | Navigate checklist items |
| `R` | Run a tool for the selected item |
| `A` | Add a finding manually |
| `D` | Mark item as Done |
| `S` | Skip item |
| `G` | Generate report |
| `Ctrl+Q` | Quit |

---

## Checklist Coverage

| Category | Items |
|---|---|
| Information Gathering (INFO) | WSTG-INFO-01 … WSTG-INFO-10 |
| Configuration Management (CONF) | WSTG-CONF-01 … WSTG-CONF-10 |

---

## Tool Wrappers

Each wrapper tries the real binary first. If not installed, it returns realistic simulated output so the demo always works. All 16 are registered in `TOOL_REGISTRY` (`surveil/tools/__init__.py`) and invokable from both the CLI and TUI.

| Tool | Purpose | Checklist Items |
|---|---|---|
| `nmap` | Port scanning & service fingerprinting | INFO-02, CONF-01, CONF-06 |
| `httpx` | HTTP probing & header analysis | INFO-02, CONF-07, CONF-08 |
| `whatweb` | Technology & CMS fingerprinting | INFO-02, INFO-08 |
| `wafw00f` | WAF detection | INFO-10, CONF-10 |
| `subfinder` | Subdomain discovery | INFO-01, CONF-09 |
| `nuclei` | Template-based vulnerability scanning | CONF-02, CONF-05, CONF-08 |
| `arjun` | Hidden HTTP parameter discovery | INFO-04 |
| `dnsx` | DNS resolution & enumeration | INFO-01, CONF-09 |
| `gowitness` | Screenshot capture of web pages | INFO-04 |
| `wpscan` | WordPress-specific vulnerability scanning | INFO-08 |
| `amass` | Passive subdomain enumeration | INFO-01 |
| `ffuf` | Directory/file brute-forcing | INFO-04, CONF-01, CONF-04, CONF-05 |
| `gobuster` | Directory brute-forcing | CONF-04, CONF-05 |
| `katana` | Web crawling & endpoint discovery | INFO-04 |
| `nikto` | Web server vulnerability scanning | CONF-02 |
| `testssl` | TLS/SSL configuration analysis | CONF-06 |

Auto-finding extraction (`surveil/findings_extractor.py`) currently covers
`nmap`, `httpx`, `whatweb`, `nuclei`, `wafw00f`, `subfinder`, and `nikto`;
the other 9 tools' output is stored and viewable but not yet auto-parsed
into findings.

---

## Data Storage

Engagements are saved as JSON files in `~/.surveil/engagements/`
(or `/data/.surveil/engagements/` inside the Docker container,
since `$HOME` is set to `/data` there). No cloud, no external API calls.

---

## Design Principles (from proposal)

- **Deterministic enumeration** — the enumeration loop never calls an LLM. Tools run directly via subprocess.
- **Evidence chain** — every finding links to raw tool output for audit traceability.
- **Confidence flag** — findings distinguish *tool-detected (unverified)* from *tester-verified*.
- **Offline-first** — no data leaves the machine.
- **Time tracking** — elapsed time per checklist item is recorded for baseline analysis.
