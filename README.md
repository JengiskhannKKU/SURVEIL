# surveil

**Deterministic, OWASP WSTG checklist-driven web application penetration testing.**

surveil is a terminal-native tool that brings together web application enumeration tooling under a single interactive interface. It provides a structured OWASP WSTG checklist, deterministic tool orchestration (no AI in the enumeration loop), finding management with CVSS scoring, and professional report generation — all offline. A browser-based web app (FastAPI + Next.js) is also available on top of the same engine — see [Web app](#web-app-fastapi--nextjs) below.

> Working on this repo across sessions? See `HISTORY.md` for a running
> log of what's been done and what the next agent should pick up.

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

- **Tool Orchestration Layer** — wraps 16 tools via subprocess: `nmap`, `httpx`, `whatweb`, `wafw00f`, `subfinder`, `nuclei`, `arjun`, `dnsx`, `gowitness`, `wpscan`, `amass`, `ffuf`, `gobuster`, `katana`, `nikto`, `testssl` (see `TOOL_REGISTRY` in `surveil/tools/__init__.py`). Falls back to realistic simulated output when a tool is not installed (demo mode). Each tool supports a **Fast** and a **Full** command variant, and its exact command line is editable before running.
- **Checklist & State Engine** — OWASP WSTG INFO + CONF items (20 items) with status tracking, Textual TUI, JSON persistence, and a saved-engagement picker.
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

## Web app (FastAPI + Next.js)

Alongside the CLI/TUI, `surveil` has a browser-based interface: a FastAPI
backend (`backend/`) that wraps the same orchestrator/state/report engine,
and a Next.js frontend (`frontend/`) with a checklist UI, a Run Tool dialog
that streams live tool output over a WebSocket, findings management, and
report downloads.

**Quickest start** — one script that sets up and runs both:

```bash
./run.sh                    # backend on :8000, frontend on :3000
./run.sh 8001 3001           # or custom ports
```

It creates `venv/` and `frontend/node_modules` on first run if they don't
exist, waits for the backend to answer `/api/health` before starting the
frontend, and stops both cleanly on Ctrl+C. `./run-backend.sh [port]` and
`./run-frontend.sh [port]` run each half on its own, for when you want them
in separate terminals (e.g. to watch their logs independently).

### Manual setup

### 1. Backend

```bash
pip install -e ".[web]"
uvicorn backend.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # points at http://127.0.0.1:8000 by default
npm run dev
```

Open http://localhost:3000 — a landing page with a link into the dashboard
at `/engagements` (the engagement list). The backend reads/writes the same
`~/.surveil/engagements/` JSON store as the CLI and TUI, so engagements are
shared across all three interfaces.

No authentication — same single-user/local trust model as the CLI. Don't
expose port 8000/3000 beyond a trusted network without adding one.

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

## Keeping the local venv and Docker image in sync

The local venv (`pip install -e .`) and the Docker image (`surveil:latest`)
are two separate installs of the same source — nothing keeps them in sync
automatically, so it's easy for one to drift ahead of the other (e.g. after
pulling changes, or mid-development). A `Makefile` target rebuilds both
together and confirms they agree:

```bash
make sync           # pip install -e . locally, docker compose build, then verify
make check-version  # just check whether they currently agree
```

`check-version` compares `surveil --version` between the two and fails
loudly on a mismatch instead of you discovering it as "the TUI in Docker
doesn't have the feature I just added." Bump `version` in both
`pyproject.toml` and `surveil/__init__.py` (`__version__`) when you want
drift like this to be catchable — the two are not auto-derived from each
other.

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
| `surveil delete <id> [<id> ...]` | Delete one or more engagements (`-y`/`--yes` skips the confirmation prompt) |
| `surveil install-tools` | Interactively install enumeration tool binaries (pick a subset, recommended ones pre-selected) — also `./install-tools.sh` |

---

## TUI Key Bindings

| Key | Action |
|---|---|
| `↑ / ↓` | Navigate checklist items |
| `N` | Jump to the next pending item |
| `R` | Run a tool for the selected item |
| `A` | Add a finding manually |
| `D` | Mark item as Done |
| `S` | Skip item |
| `U` | Reset item to pending |
| `G` | Generate report |
| `?` | Show the in-app help/manual |
| `Ctrl+Q` | Quit |

On the findings table, `Enter` opens a finding's full detail (description,
evidence, remediation) with `V` to verify/unverify and `X` to delete a
false positive — both work by keyboard even if the dialog's buttons have
scrolled out of view.

---

## Using the TUI

### Choosing an engagement

Running `surveil tui` with no `--id`:
- 0 saved engagements → prints a message telling you to run `surveil new` first.
- 1 saved engagement → opens it directly, no extra step.
- 2+ saved engagements → shows a picker (ID, name, target, progress, findings, Crit/High counts, created date). `↑`/`↓` to navigate, `Enter` to open, `Ctrl+Q` to cancel.

`surveil tui --id <engagement-id>` skips the picker and opens that engagement directly.

The picker can also delete engagements without leaving the TUI: `Space`
marks/unmarks the row under the cursor, and `X` deletes all marked rows
(or just the current row if none are marked) after a confirmation dialog.
Equivalent to `surveil delete <id> [<id> ...]` from the command line — see
CLI Reference below.

### Running a tool: Fast/Full, wordlist picker, editable command, and a guide

Pressing `R` on a checklist item opens the Run Tool dialog:
- **Guide** — a one-line description of what the tool does plus an example invocation, shown above the command field and updated as you change the selected tool.
- **Fast / Full scan switch** — Fast uses a quicker, narrower-scope command (fewer ports/templates/threads, shorter timeouts, or the tool's own `--fast`-style flag); Full (the default) is the thorough variant. Toggling it updates the command preview live.
- **Wordlist picker** — for directory/file brute-forcing tools (`ffuf`, `gobuster`), a "Select wordlist" button opens a card-based picker with two tabs, plus a "tool default" option. Picking a wordlist swaps just the `-w <path>` argument in the command, leaving everything else untouched. Hidden for tools that don't take a wordlist.
  - **Local** — wordlists actually present on the host, scanning common locations like `/usr/share/wordlists`, `/usr/share/seclists`, `~/SecLists`, etc. (see `surveil/wordlists.py`), grouped the way a real SecLists checkout reads (`Discovery`, `Passwords`, `Usernames`, ...).
  - **SecLists (GitHub)** — browse every wordlist in [danielmiessler/SecLists](https://github.com/danielmiessler/SecLists) without cloning the ~1GB repo. Picking a file **installs only that one file** (via GitHub's API + raw file CDN) into this project's own `surveil/data/wordlists_downloaded/` (gitignored — downloaded per checkout, not committed), mirroring the repo's own folder structure, and selects it immediately. A file installed this way then also shows up under the **Local** tab from then on (see `surveil/seclists_remote.py`). The category listing itself is cached for 24h (in `~/.surveil/seclists_tree_cache.json`) to stay well under GitHub's unauthenticated API rate limit.

  The default wordlist (used by "tool default" and by `ffuf`/`gobuster`'s
  Fast/Full commands) resolves in this order: the **Settings** dialog's
  wordlist directory (gear icon in the nav bar — persisted to
  `~/.surveil/config.json`, no restart needed) → the `SURVEIL_WORDLIST_DIR`
  env var (point it at a directory to search, or a specific wordlist
  file, e.g. a SecLists checkout) → the first wordlist found in the common
  install locations above → a small wordlist bundled with surveil itself
  (`surveil/data/wordlists/common.txt`), so `ffuf`/`gobuster` have a real,
  working default out of the box on any OS — their own conventional
  default (`/usr/share/wordlists/dirb/common.txt`) is a Kali/Debian
  package path that doesn't exist on macOS or a bare Linux box.

  ```bash
  export SURVEIL_WORDLIST_DIR=~/SecLists/Discovery/Web-Content
  ```
- **Editable command line** — the exact command about to run is shown in an editable field; change flags, timeouts, whatever you need (including hand-typing a wordlist path the picker didn't find). Leave it untouched and the normal simulated-fallback behavior applies if the binary isn't installed. Edit it, and it always executes for real — a missing binary then surfaces as a real error instead of demo output. **Reset Command** restores the tool's default for the current Fast/Full selection.

### Reading tool output

Raw tool output streams into the Tool Output panel live as it runs (and replays the same way when you reselect a completed item), with line-level highlighting: HTTP status codes color-coded by class (2xx green, 3xx yellow, 4xx/5xx red), nuclei-style `[severity]` tags colored to match the findings table, URLs, CVE IDs, and `[+]`/`[-]`/`⚠` markers picked out, and the `SIMULATED` banner bolded so it's obvious when you're looking at demo data rather than a real scan. See `surveil/output_formatter.py`.

---

## Checklist Coverage

| Category | Items |
|---|---|
| Information Gathering (INFO) | WSTG-INFO-01 … WSTG-INFO-10 |
| Configuration Management (CONF) | WSTG-CONF-01 … WSTG-CONF-10 |

---

## Tool Wrappers

Each wrapper tries the real binary first. If not installed, it returns realistic simulated output so the demo always works. All 16 are registered in `TOOL_REGISTRY` (`surveil/tools/__init__.py`) and invokable from both the CLI and TUI. Every wrapper also carries a `description` and `example` (shown as the guide in the TUI's Run Tool dialog) and a Fast/Full `build_command(fast=...)` variant.

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

### Installing the tool binaries

None of the 16 tools are required — each falls back to simulated demo
output when its binary isn't found. To get real output, install what you
need with:

```bash
./install-tools.sh
# or, if you already have the venv set up:
surveil install-tools
```

This is interactive and lets you pick a subset rather than all 16 at once —
the 7 tools auto-finding extraction understands (`nmap`, `httpx`, `whatweb`,
`nuclei`, `wafw00f`, `subfinder`, `nikto`) are pre-selected as a recommended
starter set. Each tool installs via the best package manager available on
your host (`brew`/`apt`/`go`/`pip`/`gem`, in that preference order — see
`install_hints` on each wrapper in `surveil/tools/*_tool.py`); tools with no
install method available for your OS are reported, not silently skipped.
The web UI's Run Tool dialog and tool picker show the same install commands
inline for whatever isn't installed yet.

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
