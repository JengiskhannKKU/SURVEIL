# oculus — project history

Running log of work sessions on this repo, kept for continuity across
agent sessions. Newest entry on top. Each entry: what was done, what
was verified, and what the next agent should pick up.

---

## 2026-09-03 (57) — Three real gaps found by actually running the OSCP checklist against a live HTB target

**Done (user: ran the app themselves against a real, authorized HTB
target — HTB "Cap", 10.129.34.27 — and asked what OCULUS is missing;
Claude-in-Chrome still wasn't connecting, so verification here was done
by driving the same `/ws/engagements/{id}/items/{id}/run` WebSocket the
UI itself uses, directly, against the live target over the tester's own
HTB VPN):**

1. **`OSCP-ENUM-02`'s default nmap command was hardcoded to web ports,
   silently dropping whatever OSCP-ENUM-01 had already found.** Real
   run: OSCP-ENUM-01/RECON-02 found 21 (ftp)/22 (ssh)/80 (http) open;
   OSCP-ENUM-02's unedited "full" command (`-p
   80,443,8080,8443,8000,8888,3000`) then only ever touched port 80,
   even though its own description says "every open port found above."
   Fixed in `oculus/checklist.py`: `apply_tool_overrides()` (already the
   shared mechanism for wordlist-category/nuclei-tag/curl-wget
   overrides — see entries 16 and earlier) gained an `engagement`
   parameter and a new nmap branch, `_apply_nmap_override()`, that —
   for `OSCP-ENUM-02` specifically — swaps `-p <web ports>` for every
   port this engagement's own earlier nmap output already reported
   open (`_discovered_ports()`), falling back to the original web-port
   default when nothing's been scanned yet. Wired through
   `Orchestrator.run_tool` (has `self.engagement` already) and the Run
   Tool dialog's command-preview endpoint (`GET
   /api/tools/{tool}/command`, which didn't have engagement context at
   all before — added an `eng_id` query param, `backend/routers/tools.py`
   loads the engagement if given; `frontend/src/lib/api.ts`'s
   `previewCommand()` and its one call site in `RunToolDialog.tsx` now
   pass `engagementId` through). Re-ran the real scan afterward:
   command became `nmap -sV -sC -p 21,22,80 --open -T4 10.129.34.27`.
2. **A tool's own non-zero exit code was always `Status.FAILED`, even
   when that exit code is a normal, correct negative test result.**
   Real run: the new `ftp` tool (entry 56) correctly found anonymous
   FTP login denied (`530 Login incorrect`, curl exit 67 =
   CURLE_LOGIN_DENIED) — a clean, completed test — but the checklist
   item still showed red/FAILED, indistinguishable from the tool having
   actually crashed. `ToolResult.success` (`oculus/tools/base.py`) is
   no longer just `exit_code == 0`; `BaseTool` gained an overridable
   `is_negative_result(exit_code) -> bool` hook (default: always
   False, unchanged behavior for every existing tool) that a wrapper
   can use for its own confirmed "ran fine, found nothing" codes.
   `FtpTool` overrides it for curl's 67 specifically — every other
   non-zero curl code (connection refused, timeout, ...) is still a
   real failure. Re-ran for real afterward: same 530 response, now
   `success=True`, item status `done`.
3. **`_INTERESTING_PORTS` auto-finding (open FTP/MySQL/Redis/RDP/...
   ports get flagged as a Finding automatically) only ever fired from
   `extract_naabu`, never `extract_nmap`** — despite nmap being the
   port scanner every checklist item in this app actually maps to. Real
   run: nmap found port 21 open, zero Findings were generated for it.
   `oculus/findings_extractor.py`: factored the shared per-port lookup
   into `_interesting_port_findings(item_id, tool, ports, output)` (used
   by both extractors now) and added the missing call from
   `extract_nmap()` (parses nmap's own `21/tcp open ...` table lines).
   Re-ran for real afterward: `OSCP-ENUM-02` now carries a "FTP Service
   Exposed" (medium, CWE-16) Finding, tool="nmap".

**Verified (all three against the same live, authorized target, not
mocked — nmap runs take ~130s each over the tester's VPN, so this was
genuinely slow to confirm, not assumed):**
- `python3 -c "from oculus.checklist import build_checklist,
  build_oscp_checklist"` still builds clean; `_discovered_ports()` /
  `apply_tool_overrides()` tested directly against the real engagement's
  already-saved nmap output (`['21','22','80']` recovered correctly).
- `tsc --noEmit`, `eslint`, `next build` all clean on the frontend
  changes (`api.ts`, `RunToolDialog.tsx`).
- Rebuilt (`docker compose build backend frontend`) and recreated
  (`docker compose up -d backend frontend`) both live containers.
- Re-ran `ftp` on `OSCP-ENUM-11` for real: `success=True`, item status
  `done` (was `failed` before the fix, same real 530 response both
  times).
- Re-ran `nmap` on `OSCP-ENUM-02` for real: command line confirmed as
  `-p 21,22,80` (was the hardcoded web-port list before the fix); item
  now carries an auto-extracted "FTP Service Exposed" Finding that
  didn't exist before.

**Next steps for the next agent:**
1. `is_negative_result()` is only implemented for `ftp_tool.py`'s curl
   exit 67 — hydra (no valid credential pair), sqlmap (not injectable),
   nikto (clean scan) are the same likely-affected shape flagged in the
   original report but *not yet confirmed* against a real non-zero exit
   from any of them; add overrides only once actually confirmed, per
   the docstring's own warning against guessing a code.
2. `_apply_nmap_override()` is scoped to `OSCP-ENUM-02` only (the one
   item whose own description explicitly asks for "every open port
   found above"); the WSTG checklist is web-only by design (see
   checklist.py's module docstring) so this wasn't extended there.
3. The other gaps from the same live-testing report — evidence not in
   Markdown/.docx export, metasploit/enum4linux/mysql/ftp/redis missing
   findings-extractor entries, no PostgreSQL/MSSQL/Oracle client — are
   still open, not part of this entry's scope (user asked specifically
   for items 1-3).

---

## 2026-09-03 (56) — feat: mysql/ftp/redis service-enumeration tools

**Done (user: "add database tools in project example mysql, ftp, other
etc"):**
- New wrapped tools, same `BaseTool` pattern as every other wrapper:
  - `oculus/tools/mysql_tool.py` — `mysql -h <target> -u root` (blank
    password), fast mode just proves the login, full mode also lists
    every database plus `mysql.user`. Real, commonly-tested OSCP finding
    (default-install blank root), distinct from web-app SQL injection
    (`sqlmap` already covers that).
  - `oculus/tools/ftp_tool.py` — anonymous FTP login check via `curl
    ftp://<target>/ -u anonymous:anonymous@example.com` rather than the
    interactive `ftp` client (non-interactive, scriptable, clean exit
    code instead of a stuck prompt). Full mode adds `-v` to show the
    actual login/PWD/LIST protocol exchange.
  - `oculus/tools/redis_tool.py` — `redis-cli PING`/`INFO server`
    against the target with no auth, since Redis ships with no
    authentication by default and an exposed instance is a well-known
    real foothold (CONFIG SET dir/dbfilename + SAVE).
- Registered all three in `oculus/tools/__init__.py`'s `TOOL_REGISTRY`
  — the backend's `/api/tools` endpoint and the frontend's Run Tool
  dialog are both fully dynamic off this registry already, so no
  frontend or router changes were needed.
- `oculus/checklist.py`: `OSCP-ENUM-10` ("Database Service
  Enumeration") had `tools=[]` with a comment "no CLI tool wrapped for
  this yet" — wired it to `["mysql", "redis"]`, keeping the note about
  PostgreSQL/MSSQL/Oracle still needing a manual client since those
  weren't asked for. Added a new `OSCP-ENUM-11` ("FTP Anonymous Login
  Check") item using `ftp`, distinct from nmap's own `-sC` default
  script pass (which touches on the same check but doesn't confirm/list
  as unambiguously).
- `Dockerfile`: added `default-mysql-client` (provides the `mysql`
  binary — confirmed the plain `mysql-client` package name is a
  transitional/virtual package on Debian bookworm) and `redis-tools`
  (provides `redis-cli`); `curl` was already installed for the ftp tool.

**Verified:**
- `python3 -c "from oculus.checklist import build_checklist,
  build_oscp_checklist"` — both build without error (the module's own
  `_validate_tool_references()` runs at import time and would raise on
  an unregistered tool name), OSCP checklist now 34 items, no duplicate
  IDs.
- Printed each new tool's `build_command()`/`mock_output()` directly —
  correct flags, no exceptions.
- Rebuilt (`docker compose build backend`) and recreated (`docker
  compose up -d backend`) the live backend container; confirmed via a
  real `GET /api/tools` that `mysql`/`ftp`/`redis` are present (30
  tools total, up from 27).
- Created a real OSCP-methodology engagement via `POST
  /api/engagements` against the live container and confirmed
  `OSCP-ENUM-10`/`OSCP-ENUM-11` carry the new tools; deleted the test
  engagement afterward.

**Next steps for the next agent:**
1. None of the three new tools have a `findings_extractor.py` entry
   yet (same gap already flagged for metasploit/enum4linux in entry
   52) — a real mysql blank-root hit or ftp anonymous-login hit
   currently has to be read from raw output, not auto-flagged as a
   Finding.
2. `oculus`/`backend` service image was rebuilt and recreated;
   `frontend` was untouched (no frontend code changed) and does not
   need a rebuild for this entry.

---

## 2026-09-03 (55) — feat: nmap port-state column in the Ports summary

**Done (user: "at Ports, can you add column that tell this nmap port
states" — pasted nmap's own six-state definitions):**
- `engagementPorts.ts`: added a `PortState` union (`open` / `closed` /
  `filtered` / `unfiltered` / `open|filtered` / `closed|filtered`) and a
  `PORT_STATE_INFO` map of the definitions the user pasted, and a
  `state: PortState | null` field on `EngagementPortEntry`.
- The nmap-table regex (`NMAP_PORT_RE`) already captured a `state` group
  per match but immediately discarded it after an `if
  (!state.startsWith("open")) continue` filter — so today, every entry
  in this summary was silently assumed "open" with no way to tell
  open from open|filtered, and no way for a non-`--open` nmap run to
  surface the other four states at all. Now the real captured state is
  kept and stored (validated against `PORT_STATE_INFO`'s keys), and the
  `open`-only filter is gone — any of nmap's six real states will now
  show up here if nmap reports it.
- Confirmed via `nmap_tool.py` that `build_command()` passes `--open`
  unconditionally in every mode today, so in practice only `open` and
  `open|filtered` will actually appear until/unless a tester edits the
  nmap command by hand (dropping `--open`, running a UDP/ACK scan,
  etc.) — deliberately did *not* change `--open` itself, since removing
  it turns a full-port scan into thousands of "closed" lines; that's a
  scan-behavior tradeoff for the user to opt into, not something to
  flip silently under a "add a column" request.
- naabu-derived and manually-added entries have no real state signal
  (naabu's bare `host:port` lines and a manual add both only ever mean
  "confirmed open") — both default to `state: "open"`.
- `PortsDialog.tsx`: new colored `Chip` per row (green open, amber
  filtered/open|filtered, blue unfiltered, gray closed/closed|filtered),
  each with a per-state tooltip; a small info icon next to the dialog's
  "Ports" title opens a tooltip listing all six state definitions
  (the user's own pasted text) for tester reference even though only
  two will normally appear.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Rebuilt (`docker compose build frontend`) and recreated (`docker
  compose up -d frontend`) the live frontend container; confirmed
  `GET /` still returns 200 afterward.

**Next steps for the next agent:**
1. Browser E2E (open the Ports dialog against a real nmap run, confirm
   the state chip and tooltip render correctly) not performed — same
   outstanding Claude-in-Chrome connection issue as prior entries.
2. If a future request wants the other four states to actually appear
   in practice, that means changing `nmap_tool.py`'s `build_command()`
   to drop `--open` (at least in one mode) — flagged here, not done,
   per the reasoning above.

---

## 2026-09-03 (54) — Fix: "MUI: The `value` provided to the Tabs component is invalid"

**Done (user report: a real browser console error — "None of the Tabs'
children match with 'null'. You can provide one of the following values:
nmap." — thrown from `ItemDetail.tsx`'s Tool output `<Tabs>`):**
- Root cause: `activeOutput` was plain `useState` seeded once at mount
  from `Object.keys(item.tool_outputs)[0] ?? null`. Two ways that goes
  stale without anything re-syncing it: (1) the item has no tool output
  yet at mount (a fresh checklist item), so it starts `null` — and stays
  `null` even after `item.tool_outputs` later gains an entry through any
  path other than `RunToolDialog`'s own `onDone` (the *only* place that
  was manually calling `setActiveOutput` after the fact) — entry 53's
  `EvidencePanel` is exactly such a path, since uploading evidence
  replaces the whole `item` prop (including whatever `tool_outputs` now
  has) via its own `onChange`. (2) Passing that raw `null` straight to
  MUI's `<Tabs value=>` is itself invalid regardless — MUI wants `false`
  for "nothing selected," not `null`.
- Split the raw click/run-driven pick (`selectedOutput`, a tester
  action, updated in exactly the two places it always was) from a new
  *derived* `activeOutput` — computed at render time as `selectedOutput`
  when it still names a real tab, else the first available one — same
  "derive a safe fallback instead of syncing state via an effect" idiom
  `effectiveOutputView` a few lines below already uses in this same
  file, not a new pattern. `<Tabs value={activeOutput ?? false}>` fixes
  the MUI-specific half of the bug on top.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Traced every `setActiveOutput` call site by hand (grep, not
  assumption) — confirmed both real update paths (`selectOutputTab` on
  a manual tab click, `RunToolDialog`'s `onDone` after a run finishes)
  correctly now call `setSelectedOutput`, and that `activeOutput` itself
  is never written to directly anywhere — it's purely derived.
- Rebuilt (`docker compose build frontend`) and recreated
  (`docker compose up -d frontend`) the live frontend container;
  confirmed the engagement detail page (`GET /engagements/{id}`) still
  returns 200 afterward.

**Next steps for the next agent:**
1. Browser E2E (reproducing the original crash scenario — a fresh item
   with no tool output, upload evidence, confirm the console stays
   clean, then run a real tool and confirm the tab still auto-selects)
   not performed — same outstanding Claude-in-Chrome connection issue as
   prior entries.

---

## 2026-09-03 (53) — Per-item evidence upload (drag-and-drop files/photos)

**Done (user request: "each checklists can upload evidences, such as
photos, descriptions, files anything... redirect to real path can drop
and drag... easy to use"):**
- New `oculus/models.py` `Evidence` model
  (id/filename/stored_name/content_type/size_bytes/description/
  uploaded_at), attached as `ChecklistItem.evidence: list[Evidence]`.
  Deliberately **not** inlined file bytes into the engagement's own
  JSON (base64 or otherwise) — that would bloat every load/save of the
  engagement for files that can run into MBs each, the same reasoning
  already applied to `tool_outputs` staying as plain text rather than
  something heavier.
- New `oculus/evidence_store.py`: the real path on disk —
  `~/.oculus/evidence/<engagement id>/<item id>/<evidence id>_<
  sanitized filename>`. Same `~/.oculus` home as engagement state/
  config (via `_home.ensure_home()`), so it automatically gets entry
  51's Docker-host bind-mount and entry 45's legacy-path migration for
  free, not a second storage location to keep in sync by hand.
  Filenames are sanitized (non-`[A-Za-z0-9._-]` chars stripped, any
  directory components dropped) before touching the filesystem — an
  uploaded file's *name* is tester-controlled input, not something to
  trust as a raw path segment.
- New `backend/routers/evidence.py`: `POST .../evidence` (multipart
  upload, 25MB cap), `PATCH .../evidence/{id}` (description only),
  `DELETE .../evidence/{id}` (removes the DB record *and* the file on
  disk), `GET .../evidence/{id}/file` (serves the real file back,
  `FileResponse` with the original filename/content-type — what an
  `<img>` thumbnail or a "download" link points at).
- `pyproject.toml`'s `web` extra gained `python-multipart` — FastAPI's
  file-upload support silently depends on it at request time (not
  import time), so its absence wasn't caught until a real upload
  actually ran.
- New `frontend/src/components/EvidencePanel.tsx`: a dashed dropzone
  (drag-and-drop, or click to open a native file picker — real
  accessibility fallback, not drag-only) uploads immediately on
  drop/select; each uploaded file becomes a card below it — an inline
  thumbnail for images, a generic file icon otherwise, filename, size,
  and an editable description (save-on-blur, same UX pattern as the
  existing per-item Notes field) — with a hover-revealed remove button.
  Wired into `ItemDetail.tsx` between the Findings panel and Notes.
- `frontend/src/lib/api.ts`'s `uploadEvidence()` bypasses the shared
  `request()` helper on purpose — it always sets `Content-Type:
  application/json`, which would break a real multipart upload (the
  browser has to set its own `Content-Type` with the multipart
  boundary for `FormData`, not have one forced on it).

**Verified:**
- **Real bug caught and fixed by actually running it, not just reading
  the code**: the first real upload attempt returned a real `500`
  (confirmed via `docker logs`, not guessed) — `Evidence.stored_name`
  had no default, but the router constructs the object *before*
  computing `stored_name` (which itself needs the object's own
  generated `id`), so Pydantic validation failed at construction time
  on every single upload. Fixed by defaulting `stored_name: str = ""`
  in the model.
- **Full real round-trip against the live backend**, not a unit test:
  uploaded a real hand-built PNG via `curl -F file=@...` → confirmed
  the file landed at the real path inside the container
  (`/data/.oculus/evidence/<eng>/<item>/<id>_<name>.png`) *and* on the
  real host filesystem at the same relative path under `~/.oculus/`
  (proving entry 51's shared bind-mount extends to evidence
  automatically, not just engagement JSON) *and* byte-identical when
  fetched back via `GET .../file` (`diff` against the original — zero
  differences). Updated its description via `PATCH`, confirmed the
  change stuck. Deleted it via `DELETE`, confirmed both the JSON record
  and the real file on disk were gone afterward.
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Rebuilt both images and recreated both live containers; re-ran the
  full upload/update/delete round-trip against the fresh build (not
  just the hot-patched one used to find the bug) — same correct
  result. Confirmed all pre-existing engagements survived every
  rebuild throughout.

**Next steps for the next agent:**
1. Browser E2E (actually dragging a file onto the dropzone, watching
   the thumbnail/description UI) not performed — same outstanding
   Claude-in-Chrome connection issue as prior entries.
2. No image thumbnail resizing/compression — a full-resolution photo
   renders at its uploaded size inside a 110px-tall card via CSS
   `object-fit: contain`, fine for typical screenshot sizes but would
   waste bandwidth on a genuinely huge photo. Not optimized here; the
   25MB upload cap is the only real ceiling in place.
3. Evidence isn't included in the Markdown/.docx report export yet —
   findings/tool_outputs are, evidence files aren't referenced at all.
   Worth adding if a tester wants uploaded screenshots to show up in
   the generated report, not just in the live UI.

---

## 2026-09-03 (52) — Deeper OSCP checklist + metasploit/enum4linux tools

**Done (user request: "add more details checklist oscp style. and
script and any want tools? if you want you can add such as
metasploit"):**
- `oculus/checklist.py`'s `build_oscp_checklist()` grew from 25 items/
  8 categories to **33 items/9 categories**: new items for vhost/
  subdomain fuzzing on web ports (`OSCP-ENUM-09`, ffuf `-H "Host:
  FUZZ.<target>"`), database service enumeration (`OSCP-ENUM-10`,
  manual), a Metasploit-based exploit lookup alongside searchsploit's
  (`OSCP-VULN-04`, `OSCP-PRIVL-03`, `OSCP-PRIVW-03`), buffer overflow
  exploitation (`OSCP-EXPLOIT-04`, manual — needs a debugger attached
  to the target, genuinely outside what a network-facing recon
  orchestrator can automate), and a new **Active Directory** category
  (`OSCP-AD-01/02`: AD enumeration, Kerberoasting/AS-REP roasting) —
  newer PEN-200 syllabus revisions weigh AD attack chains heavily, and
  it didn't fit cleanly into either the generic Enumeration or a
  single-host Privilege Escalation checklist. `OSCP-ENUM-04` (SMB
  enumeration) switched from a `tools=[]` manual-guidance item to a
  real `tools=["enum4linux"]` one, closing the exact gap entry 48
  flagged as a known next step.
- Two new tool wrappers:
  - `oculus/tools/enum4linux_tool.py` — wraps `enum4linux-ng` (the
    actively-maintained Python rewrite of the original enum4linux):
    users/groups/shares/password-policy/OS-info via SMB. **Not on
    PyPI** (confirmed the hard way: `pipx install enum4linux-ng`
    really does fail with "No matching distribution found", tried
    before falling back to a `git clone` install — same lesson as
    entry 48's `exploitdb` apt-package assumption failing the same
    way). Also needed `smbclient` *and* the separate `samba-common-bin`
    Debian package (`smbclient` alone doesn't provide `net`/
    `nmblookup` — confirmed via `dpkg -L smbclient` genuinely not
    listing them, not assumed) — enum4linux-ng shells out to all four
    at runtime and refuses to start without them.
  - `oculus/tools/metasploit_tool.py` — Metasploit Framework module
    search via `msfconsole -q -x "search <term>; exit"`. Same
    Docker-based shape as `zap` (entry 46) rather than baked into this
    app's own image — Metasploit's ~2500 Ruby modules make the
    official image genuinely heavy (~1.7GB). Same honest-placeholder
    default as `searchsploit` (entry 48): searches the bare target
    string, documented as a harmless placeholder meant to be edited
    with a real product/version.
- `Dockerfile`: added `smbclient`/`samba-common-bin` (apt) and
  enum4linux-ng's own `git clone` + `pip install -r requirements.txt`
  (metasploit needs no Dockerfile change at all — it runs entirely via
  the `docker run` passthrough already set up for `zap`).

**Verified:**
- `_validate_tool_references()` (the existing import-time guard)
  passed clean against both checklists together — no unregistered
  tool references snuck in.
- **Two real build failures caught and fixed, not assumed to work**:
  `apt install exploitdb`-style attempt for enum4linux-ng
  (`pipx install enum4linux-ng`) really failed on a real build (not
  on PyPI) — switched to git+requirements.txt. Then a real
  `enum4linux-ng` run against `scanme.nmap.org` failed with "The
  following dependend tools are missing: nmblookup, net, rpcclient,
  smbclient" — `smbclient` the Debian package only provides two of
  those four; added `samba-common-bin` for the other two, confirmed
  via `dpkg -L smbclient` directly. Full real run afterward: exit code
  0, correct real output (scanme.nmap.org genuinely doesn't run SMB).
- **A third real bug caught the same way**: `docker run
  metasploitframework/metasploit-framework msfconsole ...` failed with
  `su-exec: msfconsole: No such file or directory` — the official
  image never puts `msfconsole` on `PATH` (confirmed via `which
  msfconsole` inside the image genuinely returning nothing); its own
  default `CMD` uses the relative `./msfconsole` from its own
  `WORKDIR`, which a custom command has to match too. Fixed and
  re-verified: real `search vsftpd 2.3.4` inside a real container,
  through `MetasploitTool.run()`, returned the exact real
  `exploit/unix/ftp/vsftpd_234_backdoor` module — a real, well-known
  CVE, not a fabricated result. (Also noted for the record: a real
  `WARNING: image's platform (linux/amd64) does not match host
  platform (linux/arm64/v8)` on Apple Silicon — works fine under
  emulation, just slower than a native-arch image would be.)
- Rebuilt both images from a clean build (not hot-patched) and
  recreated both containers; confirmed via the live API that all 27
  tools register correctly and `build_oscp_checklist()` returns 33
  items/9 categories. All pre-existing engagements survived every
  rebuild in this entry.

**Next steps for the next agent:**
1. Browser E2E not performed — same outstanding connection issue as
   prior entries.
2. `metasploit`/`enum4linux` aren't in `findings_extractor.py`'s
   auto-extraction set — both have genuinely parseable output shapes
   (msfconsole's module table, enum4linux-ng's structured sections),
   a reasonable follow-up if wanted.
3. OSCP-AD-02 (Kerberoasting/AS-REP Roasting) is guidance-only by
   design (needs valid domain credentials and Kerberos-aware tooling
   this app doesn't orchestrate) — if Impacket ever gets wrapped for
   another reason, revisit whether `GetUserSPNs.py`/`GetNPUsers.py`
   belong there as real tools instead.

---

## 2026-09-03 (51) — Fix: Docker and `./run.sh` had two entirely separate datasets

**Done (user report: "database that saved at docker and run from the
run.sh not at same here"):**
- Root cause: engagement state resolves to `~/.oculus` (`Path.home() /
  ".oculus"`, see `oculus/_home.py`), but "home" meant something
  different in each run mode — the Docker `backend`/`oculus` services
  set `HOME=/data` (a named Docker volume, `surveil-data`), while
  `./run.sh`/`run-backend.sh` run a real process on the host, where
  `Path.home()` is the tester's actual `~`. Two completely different
  directories, silently diverging every time an engagement was created
  in one mode and not the other. Confirmed directly, not assumed: the
  host had 7 real engagements the Docker volume had never seen, and the
  Docker volume had 6 the host had never seen — zero overlap.
- **Merged both real datasets first**, before changing anything: copied
  the Docker volume's `.oculus/engagements/*.json` into the host's real
  `~/.oculus/engagements/` with `cp -n` (never overwrite — the ID sets
  were disjoint anyway, so this was a pure union, not a case needing
  conflict resolution) via a throwaway `alpine` container mounting both.
  13 total engagements confirmed present afterward, not lost.
- `docker-compose.yml`: both the `backend` and `oculus` (CLI) services
  now bind-mount `${HOME}/.oculus:/data/.oculus` *in addition to* the
  existing `surveil-data:/data` named volume — Docker lets a more
  specific mount target shadow part of a broader one, so this redirects
  just the engagement-state subpath to the host's real `~/.oculus` while
  leaving everything else under `/data` (nuclei's template cache,
  wpscan's API-token cache, other tool caches — real disk space worth
  keeping, but nothing that needs to match the host) in the named
  volume exactly as before. From here on, Docker and every local
  `run.sh`/CLI invocation always read/write the exact same files.

**Verified:**
- Inspected both real datasets before touching anything (`docker run
  --rm -v <volume>:/data alpine ls ...` for the Docker side, plain `ls`
  for the host side) — confirmed the disjoint-set diagnosis was correct,
  not assumed from the bug report alone.
- After merging: recreated the backend container with the new bind
  mount (`docker compose up -d backend`) and hit the real live API —
  `GET /api/engagements` → all 13 engagements present. Ran the real
  local CLI (`oculus list`, through the freshly-fixed `venv/` from entry
  50) — same 13 IDs, confirmed by direct comparison, proving Docker and
  the host are now genuinely reading the identical directory rather than
  two directories that merely happen to match right after a one-time
  merge.

**Next steps for the next agent:**
1. None outstanding — this closes out the storage-location split
   cleanly at the config level, not just a one-time data merge that
   would silently re-diverge on the next engagement created in either
   mode.
2. `${HOME}` in `docker-compose.yml` is a shell-environment substitution
   Compose reads at `docker compose` invocation time — works correctly
   on macOS/Linux where `$HOME` is always exported, but worth knowing
   this specific mechanism if the project ever needs to run somewhere
   `$HOME` isn't set (unusual, not a real concern for this project's
   actual local-single-user use case).

---

## 2026-09-03 (50) — Fix: CORS 400 when frontend runs on a non-3000 port

**Done (user report: a real `./run.sh 8000 3001` session — frontend dev
server on a custom port, per entry 47's own recommendation for real-time
local changes — logged `OPTIONS /api/engagements HTTP/1.1" 400 Bad
Request` repeatedly):**
- Root cause, found directly in `backend/main.py`, not guessed:
  `CORSMiddleware`'s `allow_origins` was a **hardcoded** two-entry list —
  `http://localhost:3000` and `http://127.0.0.1:3000` — literally
  nothing else. The moment the frontend runs on any other port (exactly
  what `run-frontend.sh`/`run.sh` both take a port argument to support,
  entry 50's own report being a real example), the browser's CORS
  preflight `OPTIONS` request gets rejected before the real `GET`/`POST`
  ever has a chance to run.
- Swapped the fixed list for `allow_origin_regex=r"^http://(localhost|
  127\.0\.0\.1)(:\d+)?$"` — any port on localhost/127.0.0.1, still
  scoped to local dev only (not opened to the wider internet).

**Verified:**
- Started a real standalone `uvicorn` instance (not the Docker one) on a
  throwaway port and sent real preflight `OPTIONS` requests with `curl`:
  `Origin: http://localhost:3001` → `200 OK` with `access-control-allow-
  origin: http://localhost:3001` (previously would have been the exact
  400 in the bug report); `Origin: http://localhost:3000` → still `200
  OK` (no regression to the original working case); `Origin:
  http://evil.example.com` → still `400 Bad Request` (confirmed the fix
  didn't accidentally open this up to arbitrary origins — still scoped
  to localhost only).
- Rebuilt (`docker compose build backend`) and recreated
  (`docker compose up -d backend`) the live container; re-ran the same
  real preflight check against the live `:8000` — same correct `200` +
  matching `access-control-allow-origin` header. Confirmed all 6 real
  engagements survived the rebuild.

**Next steps for the next agent:**
1. None outstanding for this fix — it's a small, fully-verified change.
   If a genuinely non-localhost frontend origin is ever needed (e.g.
   accessing the dev server from another device on the LAN, which
   `run-frontend.sh`'s own "Network: http://192.168.x.x:PORT" line from
   `next dev` already advertises), the regex would need widening beyond
   localhost/127.0.0.1 — not done here since the reported bug was
   specifically about local custom ports, not LAN access.

---

## 2026-09-03 (49) — New Engagement popup redesign: dropdown icon, card methodology, real delete confirm

**Done (user request: "redesign at when add engagements at pop-up,
icons to dropdown, and checklists style for select by cards components,
and when remove implement ui"):**
- `IconPicker` (New Engagement dialog): was a wrapping row of 12 plain
  icon-only buttons — replaced with a proper MUI `Select` dropdown.
  Closed state shows the selected icon + label via `renderValue`; each
  `MenuItem` shows its own icon (in that icon's color) + label via
  `ListItemIcon`/`ListItemText`. Same 12 options from
  `engagementIcons.tsx`, just a compact single-control picker instead of
  a grid that ate a lot of dialog vertical space.
- `MethodologyPicker`: was three small chip-style buttons with the
  selected one's description shown as a separate line below — replaced
  with three actual card components (one per methodology), each showing
  an icon in a colored tile, the label, and its own description text
  directly on the card face, selected state shown via a colored border +
  glow (the same visual language `EngagementCard`'s hover state already
  uses elsewhere on this page). `frontend/src/lib/methodologies.ts`
  gained an `Icon`/`color` per methodology (`SecurityIcon` teal for
  WSTG, `TerminalIcon` orange for OSCP, `TuneIcon` purple for Other) to
  back the new card icon tiles.
- Delete confirmation: `handleDelete()` called the browser's native
  `confirm()` — replaced with a real `Dialog` (`deleteTarget` state
  holding the id/name to delete, opened by the card's delete button,
  matching this app's own dialog styling instead of an unstyled native
  popup). Shows what's actually being deleted and what's lost (checklist
  items, findings, tool output), with a disabled-while-in-flight
  Cancel/Delete pair instead of the old fire-and-forget `handleDelete`.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Rebuilt (`docker compose build frontend`) and recreated
  (`docker compose up -d frontend`) the live frontend container;
  confirmed `GET /engagements` still returns 200 and all 6 real
  engagements survived the redeploy (this entry touches no backend/
  data-layer code — a sanity check on the redeploy itself, not a test of
  the UI changes).
- Browser E2E (opening New Engagement, using the icon dropdown and
  methodology cards, deleting an engagement through the new confirm
  dialog) **not** performed — same outstanding Claude-in-Chrome
  connection issue noted in prior entries.

**Next steps for the next agent:**
1. Browser E2E still outstanding — worth a manual click-through once the
   extension connection issue is sorted, especially the methodology
   cards' responsive stacking on mobile widths (`xs: "column"`) and the
   Select dropdown's keyboard navigation.
2. The checklist-item delete flow in `ItemDetail.tsx` still uses the
   same native `confirm()` this entry replaced on the engagements page —
   left alone since the request's "when remove implement ui" read as
   scoped to the engagement-delete flow specifically (paired with "add
   engagement" earlier in the same sentence), not a request to sweep
   every `confirm()` in the app. Worth the same treatment if asked.

---

## 2026-09-03 (48) — Real OSCP-style checklist + searchsploit tool

**Done (user request: "implement OSCP-style checklists and script" —
the deliberate follow-up flagged back in entry 45, when methodology
selection first shipped as a tag-only feature over building a real
distinct checklist under time pressure. Scoped via AskUserQuestion
first: a genuinely different phase-based structure reusing existing
tools where the architecture allows it and guidance-only where it
can't, plus `searchsploit` as the one new tool wrapper):**
- Researched the real OSCP/PEN-200 methodology (a fork agent ran
  WebSearch against OffSec's own PEN-200 materials plus several
  widely-cited community methodology writeups) rather than authoring the
  phase structure from memory — confirmed phase ordering (Recon →
  Enumeration → Vulnerability Analysis → Exploitation → Privilege
  Escalation → Post-Exploitation → Proof/Reporting, with "enumeration"
  conventionally ~80% of real exam/lab time) and that Linux/Windows
  privesc, while one phase in OffSec's own materials, is treated as two
  separate checklists in essentially every practical writeup since the
  tools/techniques don't overlap at all.
- New `oculus/checklist.py`: `build_oscp_checklist()` — 25 items across
  8 categories (RECON/ENUM/VULN/EXPLOIT/PRIVL/PRIVW/POST/PROOF), a real
  distinct structure, not a relabeled copy of `build_checklist()`'s WSTG
  categories. Automated with tools already wrapped here wherever this
  app's own architecture allows it (nmap/naabu for port scans,
  ffuf/gobuster/katana for web enum, hydra for credential testing,
  nuclei/nikto/zap for vuln scanning, sqlmap/commix for exploitation
  where a web app is in scope) — `tools=[]` guidance-only where it
  structurally can't be (SMB/SNMP enum with no wrapped tool yet,
  exploitation, privesc *enumeration* — LinPEAS/WinPEAS run **on** an
  already-compromised host, this app only ever reaches a target over the
  network — and post-exploitation), with real concrete commands named in
  the description text for each manual item rather than a vague "do this
  by hand."
- New `oculus/tools/searchsploit_tool.py` — the one genuinely new tool
  wrapper. Architecturally unlike every other tool here: it doesn't scan
  the target at all, just greps a local offline exploit-db mirror by
  product/version — so `build_command()` defaults to searching the bare
  target string as an honest placeholder (documented as such in the
  description) rather than pretending there's a meaningful default,
  since a real search needs whatever service/version enumeration
  actually found. `--disable-colour` added after a real run showed
  searchsploit emits ANSI highlight codes on stdout even when piped (not
  a TTY) — this app has no ANSI-stripping anywhere in its output
  pipeline, so left on that would've shown as literal escape-code junk
  in the UI.
- `backend/routers/engagements.py`: new `_CHECKLIST_BUILDERS` dict
  (`{"wstg": build_checklist, "oscp": build_oscp_checklist}`) —
  `create_engagement()` now actually picks the right builder based on
  the `methodology` field instead of always building WSTG regardless of
  what was selected (the real change from entry 45's tag-only version).
  `oculus/cli.py`'s `new` command gained a matching `--methodology`
  option (mirrors the same builder dict) — the CLI had no way at all to
  create an OSCP engagement before this, a real gap now closed alongside
  the web path rather than left web-only.
- `oculus/report.py`: the Markdown report's executive-summary sentence
  was hardcoded to always claim "OWASP WSTG checklist-driven" regardless
  of what methodology actually built the engagement — a real inaccuracy
  an OSCP-methodology report would otherwise have shipped with. New
  `_methodology_label()` (mirrors `frontend/src/lib/methodologies.ts`'s
  labels) makes it say what actually happened.
- `frontend/src/lib/methodologies.ts`: OSCP's description updated from
  "a planned follow-up, not yet implemented" to actually describe the
  real checklist now built. `toolLogos.ts` gained a `searchsploit` badge.
- `Dockerfile`: added `exploitdb` (provides `searchsploit`) — first tried
  as a plain `apt install` alongside sqlmap/hydra (same pattern those
  use), which **actually failed on a real build** (`E: Unable to locate
  package exploitdb` — not packaged for Debian bookworm's default repos,
  an assumption caught by actually running the build rather than
  trusting it). Switched to a `git clone` install from the official
  exploitdb repo, same pattern already used for nikto/testssl.sh/commix.
- `README.md`: tool count 24 → 25 everywhere it was cited, `searchsploit`
  added to the Tool Wrappers table, and the Checklist Coverage section
  now documents both checklists (previously WSTG-only) with the real
  phase/category breakdown for OSCP.

**Verified:**
- `_validate_tool_references()` (the import-time guard that already
  existed for the WSTG checklist) extended to validate
  `build_oscp_checklist()`'s tool references too, not just trusted by
  inspection — both checklists' items checked together against the real
  `TOOL_REGISTRY` on every import.
- Direct Python check against the real running container:
  `build_oscp_checklist()` → 25 items, 8 real distinct categories,
  correct tool mappings per item (dumped and read every item ID +
  category + tools list).
- `generate_markdown()` on a real `Engagement(methodology="oscp", ...)`
  → confirmed the executive summary now says "OSCP/PEN-200-style
  checklist-driven" instead of the previously-hardcoded WSTG claim.
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- **Full Docker rebuild + real live verification**, not just unit-level:
  first build attempt genuinely failed on the `exploitdb` apt package
  (caught and fixed as described above, not assumed to work). Rebuilt
  clean afterward; confirmed `which searchsploit chromium` inside the
  live container, confirmed all 5 real pre-existing engagements survived
  the rebuild. Ran a **real** `searchsploit --disable-colour "vsftpd
  2.3.4"` through the actual `SearchsploitTool.run()` code path —
  genuine exploit-db hits for the real, well-known vsftpd 2.3.4 backdoor
  CVE, exit code 0, no ANSI codes in the output. Created a real
  engagement via `POST /api/engagements` with `"methodology":"oscp"` —
  confirmed all 25 items with correct IDs/categories/tools came back,
  confirmed the engagement's own page loads (200) through the live
  frontend container, then deleted the test engagement. Confirmed via
  `GET /api/tools/searchsploit/command` that the live command preview
  endpoint (the same one the Run Tool dialog calls) reflects
  `--disable-colour` — caught and fixed a real staleness gap here too:
  the first check against the live server showed the *old* command
  without the flag, because editing the file on disk doesn't reload an
  already-running (non-`--reload`) uvicorn process — required an actual
  rebuild+recreate to confirm, not just re-reading the source file.

**Next steps for the next agent:**
1. `searchsploit` isn't in `findings_extractor.py`'s auto-extraction set
   — its output (a title/path table) has a genuinely parseable shape,
   unlike testssl's fixed-width columns, so this would be a reasonable
   follow-up if a tester wants matched exploits to land as findings
   automatically rather than just reading the raw output.
2. OSCP-ENUM-04 (SMB enum) and OSCP-ENUM-08 (SNMP/other) are guidance-
   only because no SMB/SNMP tool is wrapped here yet
   (`smbclient`/`enum4linux`/`crackmapexec`, `snmpwalk`) — real gaps, not
   fabricated ones; wrapping one of these would be a natural next
   OSCP-checklist improvement, following the same pattern `searchsploit`
   just established.
3. Browser E2E (creating an OSCP engagement via the actual New Engagement
   dialog, confirming the methodology picker's description text renders,
   running searchsploit from the Run Tool dialog) not performed — same
   outstanding Claude-in-Chrome connection issue noted in prior entries.

---

## 2026-09-01 (47) — Fix: Run Tool dialog output vanishes on close/reopen

**Done (user report: "when collapse the result then open again it
dissapear" — confirmed via AskUserQuestion this meant the Run Tool
dialog specifically, not the checklist sidebar or a Tree view node):**
- Root cause: `RunToolDialog`'s streamed output (`lines` state) is local
  component state, and the parent only renders the dialog at all while
  `showRun` is true (`{showRun && <RunToolDialog .../>}` in
  `ItemDetail.tsx`) — closing it unmounts the component entirely,
  discarding `lines`. Reopening creates a **brand-new** instance that
  always started from `useState<string[]>([])`, regardless of whether
  the tool had already finished and its output was sitting right there,
  saved, in `item.tool_outputs`.
- `RunToolDialog.tsx`: `lines`' initial value is now a lazy `useState`
  initializer (`() => savedLinesFor(toolName)`) that seeds it from
  `item.tool_outputs[toolName]` when present, instead of always starting
  blank — so reopening the dialog for an item that already ran shows
  that run's real saved output immediately.
- New `savedLinesFor(name)` helper is also called directly from the tool
  `<Select>`'s `onChange` (not a `toolName`-watching `useEffect` — that
  approach was tried first but tripped this repo's `react-hooks/set-
  state-in-effect` lint rule, same class of issue as `ItemDetail.tsx`'s
  `selectOutputTab` fix back in entry 35) so switching the tool dropdown
  mid-session shows *that* tool's own last-known output instead of
  leaving the previously-selected tool's stale terminal content on
  screen. The tool `<Select>` is already `disabled={running}`, so
  neither path can ever fire mid-stream and clobber a live run —
  `run()`'s own `setLines([])` at the start of a fresh run still
  correctly clears whatever was just restored.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean — the initial
  `useEffect`-based version of this fix genuinely failed lint
  (`Calling setState synchronously within an effect can trigger
  cascading renders`), confirmed by running eslint against it before
  switching to the lazy-initializer + onChange-handler approach that
  passes clean.
- Rebuilt (`docker compose build frontend`) and recreated
  (`docker compose up -d frontend`) the live frontend container;
  confirmed `GET /api/engagements` still returns all 4 real engagements
  afterward (this fix touches no backend/data-layer code, so this was a
  sanity check that the redeploy itself didn't disturb anything, not a
  test of the fix).
- Browser E2E (opening Run Tool, running a real tool, closing the
  dialog, reopening it, confirming the output is still there; also
  switching the tool dropdown mid-session to confirm the other tool's
  own last output shows instead) **not** performed — same outstanding
  Claude-in-Chrome connection issue noted in prior entries.

**Next steps for the next agent:**
1. Browser E2E still outstanding — worth a manual click-through once the
   extension connection issue is sorted.
2. This only restores output for a tool that has **already run and
   finished** (or failed/was cancelled) at least once for this item —
   reopening the dialog while a run is genuinely still in progress
   server-side still shows the `alreadyRunningElsewhere` warning banner
   instead of resuming the live stream, exactly as documented as a known
   gap back in entry 25. Not attempted here; a real fix for that needs a
   run-registry/pub-sub the backend doesn't have yet, not a frontend-only
   change like this one.

---

## 2026-09-01 (46) — Fix: gowitness `exec: "google-chrome": ... not found`

**Done (user report: a real `gowitness scan single -u http://192.168.2.11
-T 30` run failed with `failed to initialize chrome context: exec:
"google-chrome": executable file not found in $PATH`):**
- Root cause: gowitness v3's default `chromedp` driver `exec`s a real
  Chrome-compatible binary directly — this Docker image never installed
  one. `--chrome-path`'s own `--help` text implies it downloads a
  platform-appropriate binary by default when unset, but that plainly
  didn't happen here (confirmed by reproducing the exact reported error
  against this app's own image before touching anything).
- `Dockerfile`: added `chromium` (Debian's package, much lighter than
  installing real Google Chrome which isn't in Debian's default repos at
  all) to the apt install list.
- `oculus/tools/gowitness_tool.py`: new `_find_chrome()` — checks
  `google-chrome`/`google-chrome-stable`/`chromium`/`chromium-browser` on
  PATH, then macOS's Chrome/Chromium `.app` bundle paths (for a local
  non-Docker dev machine) — and `build_command()` now passes
  `--chrome-path <resolved>` explicitly whenever one is found, rather
  than continuing to rely on gowitness's own unreliable-in-practice
  auto-detection. No-op (unchanged command) when nothing is found
  anywhere, same as before this fix.
- **Found and fixed a real Docker-volume-orphaning incident along the
  way, not just a hypothetical**: the local working directory had been
  renamed from `SURVEIL` to `OCULUS` (by the user, outside this
  session) since entry 45's rename work. Since `docker-compose.yml`'s
  `surveil-data` volume key has no project-name override, Compose now
  derives a *different* volume name (`oculus_surveil-data`) than the one
  the pre-rename containers had been using (`surveil_surveil-data`) —
  exactly the failure mode entry 45 flagged as a risk of ever renaming
  the local folder or Compose project name. Confirmed directly: the
  freshly-recreated `oculus-backend-1` container really was on a
  different, near-empty volume, missing 3 of 4 real engagements
  (`SecureBank`, `internal lab 2`, and one more). Fixed by copying the
  missing engagement JSON files across from the old volume to the new
  one with a temporary `alpine` container mounting both (`cp -n`, so it
  never overwrites anything already in the new volume) — not a
  compose-file change, since the new volume name is itself now stable
  and correct for the renamed directory going forward.

**Verified:**
- Reproduced the exact reported error first, against this app's own
  pre-fix image, before assuming the diagnosis was right.
- `docker exec oculus-backend-1 chromium --version` → real Chromium
  151.0.7922.173, confirming the apt package actually installed and is
  runnable in the built image.
- `GowitnessTool('192.168.2.11').build_command()` → confirmed
  `--chrome-path /usr/bin/chromium` is now appended automatically.
- **Full real run through the actual application code path**: called
  `GowitnessTool('example.com').run(fast=True)` directly inside the
  rebuilt live container — `exit_code: 0`,
  `have-screenshot=true`, no Chrome-related error at all (the exact
  failure mode reported is gone). Confirmed the screenshot file was
  genuinely written to disk (`/app/screenshots/https---example.com.jpeg`)
  — not just a claimed success in the log line.
- Volume merge: listed both volumes' `.oculus/engagements/*.json`
  contents before touching anything, confirmed the file sets didn't
  collide (four distinct engagement IDs total), copied, then confirmed
  via the live `/api/engagements` endpoint that all four real
  engagements (`SecureBank`, `__test_style`, `internal lab 2`, `internal
  lab1`) are visible again — including `__test_style` (methodology
  `oscp`), which the user evidently created themselves to try out
  entry 45's methodology picker.

**Next steps for the next agent:**
1. Incidental finding, not fixed here (out of scope for this report):
   `docker-compose.yml`'s `backend` service sets `working_dir: /app`,
   which overrides the `Dockerfile`'s `WORKDIR /data` — so gowitness's
   default relative `./screenshots/` path resolves to `/app/screenshots`,
   **outside** the persistent `/data` volume. Screenshots are lost on
   every container recreation (confirmed: an old one,
   `screenshots/http---192.168.2.15.jpeg`, ended up accidentally
   committed into the repo itself in entry 45's rename commit, which is
   how this was even noticed). Worth either passing gowitness
   `--screenshot-path /data/screenshots` explicitly or changing the
   compose `working_dir` — not attempted here since it's unrelated to
   the reported Chrome error and touches a different, real design
   question (should screenshots be gitignored-but-persisted, or
   deliberately ephemeral?) that's worth asking about rather than
   guessing.
2. If the local directory or Docker Compose project name is ever renamed
   again, the same volume-orphaning failure mode will recur — this entry
   fixed the *data* (merged the volumes) but not the *structural* cause
   (`docker-compose.yml`'s volume still has no `external: true` pin).
   Entry 45 already discussed the tradeoffs of pinning it; still
   unresolved.

---

## 2026-09-01 (45) — Rename surveil -> OCULUS, engagement methodology tag, live-log noise filter

**Done (user request, three parts — scoped via AskUserQuestion before
starting the first two):**

**1. Full rename to OCULUS** — user explicitly chose "Everything,
including repo/Docker/git remote":
- `surveil/` package directory -> `oculus/` via `git mv` (preserves
  history), then a repo-wide case-variant token substitution
  (`surveil`->`oculus`, `Surveil`->`Oculus`, `SURVEIL`->`OCULUS`) across
  every source file (Python imports, Dockerfile, docker-compose.yml,
  pyproject.toml, shell scripts, frontend branding strings, README.md,
  HISTORY.md) — confirmed no false-positive matches first (checked for
  "surveillance" specifically, since that would have partially corrupted
  under a plain substring replace; none found). `venv/` and
  `surveil.egg-info/` (both gitignored build artifacts, not source)
  deliberately left untouched — they regenerate from a fresh `pip
  install -e .` rather than needing hand-editing.
- **Real data-loss risk caught and fixed, not just assumed handled:**
  a blanket substitution would have renamed the Docker named volume key
  `surveil-data` -> `oculus-data` in `docker-compose.yml`. Docker volumes
  aren't renamed by editing a YAML key — Compose would have silently
  provisioned a **new, empty** volume under the new name and orphaned
  every existing engagement sitting in the old one (confirmed two real
  ones existed: `SecureBank` and `internal lab 1`, the latter created by
  the user during this session, not a test engagement). Reverted just
  that one identifier back to `surveil-data` with a comment explaining
  why, so the exact same Docker volume keeps being used.
- Added new `oculus/_home.py`: `ensure_home()` renames `~/.surveil` ->
  `~/.oculus` in place (idempotent — no-op once migrated, or if there
  was never a `~/.surveil`) the first time either `state.py` or
  `config.py` touches the home directory. This is what actually makes
  existing engagement data reachable under the new path *inside* the
  still-same Docker volume — the volume-identity fix above and this
  path-migration fix are two different problems (Docker volume object
  identity vs. the filesystem path within it) that both needed solving,
  not one.
- `docker-compose.yml`'s `frontend` service (previously no explicit
  `image:`, so Compose named it `surveil-frontend` off the project name)
  now has an explicit `image: oculus-frontend:latest` to match the
  backend's already-explicit `oculus:latest`.
- **Deliberately not done**: renaming the local working directory itself
  (still `SURVEIL` on disk) and the Docker Compose *project* name
  (defaults to the directory name, hence containers are still named
  `surveil-backend-1`/`surveil-frontend-1`). Explained why in the plan:
  renaming the project name would change which Docker volume name
  Compose resolves `surveil-data` to internally (`<project>_surveil-
  data`), which would itself orphan data again unless the volume is
  separately marked `external: true` with its exact current internal
  name — decided this was compounding risk for a purely cosmetic
  container-name detail nobody sees in the app itself, so left it alone.
- GitHub repo renamed `JengiskhannKKU/SURVEIL` -> `JengiskhannKKU/OCULUS`
  via `gh repo rename` (confirmed `gh auth status` was already
  authenticated as the repo owner first), local `origin` remote URL
  updated to match, all commits pushed.

**2. Engagement methodology tag** — user chose "just tag the engagement
for now" over authoring a real distinct OSCP checklist under time
pressure:
- `oculus/models.py`: new `Engagement.methodology: str = "wstg"`.
  `backend/routers/engagements.py`'s `NewEngagement`/`create_engagement`
  thread it through; `state.list_all()`'s summary dict includes it too.
- New `frontend/src/lib/methodologies.ts`: three options (`wstg`/`oscp`/
  `other`), each with a label and an honest description — the OSCP and
  Other entries explicitly say they currently build the same real WSTG
  checklist underneath, not a fabricated distinct one, so a tester isn't
  misled about what selecting them actually does today.
- New engagement dialog gained a `MethodologyPicker` (same selectable-
  chip pattern as entry 36's icon picker), defaulting to `wstg` — a
  selection always exists, satisfying "must select" without needing a
  separate empty/required-field state. Each `EngagementCard` on the
  dashboard now shows a small methodology chip next to its name.

**3. Live-run output: Raw/Filtered toggle** (user pasted a real example:
ffuf's repeating `:: Progress: [.../...] :: Job [1/1] :: N req/sec ::
Duration: ... :: Errors: 0 ::` ticker line, which can number in the
thousands over a long run and bury any actual finding underneath):
- New `frontend/src/lib/logFilter.ts`: `NOISE_LINE_RE`/`isNoiseLine()`/
  `filterNoiseLines()` — factored out of `pathTree.ts`'s existing
  (already-correct, already-matches-`^::`) `IGNORE_LINE_RE` rather than
  writing a second pattern, since the same lines that are noise for path-
  parsing are noise for live-log readability too. `pathTree.ts` now
  imports it instead of duplicating the regex.
- `RunToolDialog.tsx`'s live-streaming terminal panel gained a Raw/
  Filtered `ToggleButtonGroup` plus a plain substring search box (same UI
  pattern as entry 35's saved-output filter) — "Filtered" hides ticker
  lines and shows a live "(N hidden)" count; the auto-scroll-to-bottom
  effect now tracks the filtered/searched line count, not just the raw
  one, so it still scrolls correctly when the visible line count changes
  independently of new output arriving.

**Verified:**
- Case-variant substitution: manually checked for "surveillance" (would
  have partially corrupted) before running — none present, safe to do a
  plain substring replace.
- `docker exec ... python3 -c "from oculus.checklist import
  build_checklist; ..."` — real import against the actual running
  container, clean.
- Migration logic (`ensure_home()`) unit-tested standalone first (a
  temp `$HOME` with a simulated `~/.surveil/engagements/abc123.json` ->
  confirmed it lands at `~/.oculus/engagements/abc123.json` and the old
  path is gone) before trusting it against real data.
- **Full rebuild + real data survival check**, not assumed: rebuilt both
  Docker images from a clean `docker compose build backend frontend`,
  recreated both containers, then confirmed via the live API that both
  pre-existing real engagements (`SecureBank`, `internal lab 1`) were
  still present with all their data intact and now report
  `"methodology": "wstg"` (the field's default, applied automatically to
  data that predates the field entirely — same backward-compat pattern
  used for `icon` in entry 36). Directly inspected the container's `/data`
  filesystem afterward: `.oculus/engagements/{dca42490,4d126044}.json`
  present, no leftover `.surveil` directory.
- `docker compose run --rm oculus --help` — real CLI entrypoint under the
  new name, full command listing returned correctly.
- Created a real engagement via `POST /api/engagements` with
  `"methodology":"oscp"` through the live API — response correctly
  carried it through and still built the real 97-item WSTG checklist (as
  designed for this scoping choice); deleted the test engagement after.
- `npx tsc --noEmit`, `eslint`, `next build` all clean throughout — no
  new errors beyond the two pre-existing warnings in `page.tsx` noted
  back in entry 26 (unused `Paper`/`FEATURES`, unrelated to this change).

**Next steps for the next agent:**
1. The local working directory is still named `SURVEIL` on disk, and
   Docker container names are still `surveil-backend-1`/`surveil-
   frontend-1` (Compose project name, derived from the directory name) —
   both deliberate, disclosed exceptions explained above. If the user
   wants those renamed too, the volume needs `external: true` with its
   exact current name first, or the existing `surveil-data` volume will
   get orphaned the same way this entry's rename almost orphaned it.
2. The local `venv/` and `surveil.egg-info/` (gitignored, untouched by
   this rename) are now stale — anyone using the local non-Docker path
   should re-run `pip install -e ".[dev,web]"` (or `make install`) to
   get a clean `oculus`-named editable install; the Docker path (this
   session's primary verified path) is unaffected.
3. A real distinct OSCP-style checklist (different items/structure than
   WSTG, not just a tag) remains unimplemented by design — flagged as a
   genuine content-authoring task in the scoping question, not attempted
   here.
4. (Resolved before this entry was finalized) `seclists_remote.py`'s
   `list_remote_wordlists()` initially didn't call `ensure_home()` before
   touching `~/.oculus/seclists_tree_cache.json` — added the same call
   there too, for consistency with `state.py`/`config.py`, rather than
   leaving it as a known gap.

---

## 2026-09-01 (44) — hydra: dual wordlist pickers (-L usernames / -P passwords)

**Done (user report: "at hydra tool can't select the wordlists"):**
- Root cause, found directly in the code rather than assumed: hydra's
  wrapper already had `uses_wordlist = False` with an explicit comment —
  "takes two lists (-L/-P), not the single -w the picker assumes". The
  Run Tool dialog's wordlist picker only ever knew how to manage one
  `-w <path>` flag (ffuf/gobuster's shape), so it had been deliberately
  disabled for hydra rather than built to handle two — a real gap, not a
  bug in the existing single-wordlist code path.
- `oculus/tools/base.py`: new `BaseTool.wordlist_slots: dict[str, str]`
  (empty by default) — maps a CLI flag to the `wordlists.
  CATEGORY_KEYWORDS` category to recommend for that flag's own picker.
  `hydra_tool.py` sets `wordlist_slots = {"-L": "usernames", "-P":
  "passwords"}` — both categories already existed in
  `CATEGORY_KEYWORDS` (added earlier for the general wordlist-discovery
  feature, just never wired to anything that used them until now).
- `backend/routers/tools.py`: `list_tools()` now includes
  `wordlist_slots` in each tool's JSON. `/wordlists/grouped` and
  `/wordlists/remote/browse` both gained an optional `category` query
  param that overrides the existing `item_id`-derived recommendation
  outright — needed because hydra's -L/-P categories are fixed
  (always "usernames"/"passwords") regardless of which checklist item
  it happens to be running under, unlike ffuf/gobuster's per-item
  `WORDLIST_CATEGORY` mapping.
- `WordlistPickerDialog.tsx` gained an optional `categoryOverride` prop
  (threaded into both its Local and SecLists/GitHub tabs) and an optional
  `title` prop (defaults to "Select wordlist", set to "Select usernames
  wordlist" / "Select passwords wordlist" for hydra's two instances).
- `RunToolDialog.tsx`: when `tool.wordlist_slots` is non-empty, renders
  one "Usernames: ..." / "Passwords: ..." button per flag (alongside,
  never together with, the existing single `uses_wordlist` button — a
  tool sets at most one of the two). New `applySlotWordlist(flag, path)`
  mirrors the existing `applyWordlist()` but is parameterized by flag
  instead of hardcoding `-w`, so picking a wordlist for `-L` only touches
  the `-L <path>` portion of the command, leaving `-P` (and anything
  else) untouched. `resetCommand()` also clears the new `slotPaths` state.

**Verified:**
- `docker exec oculus-backend-1 python3 -c "from oculus.tools import
  TOOL_REGISTRY; ..."` — `TOOL_REGISTRY['hydra'].wordlist_slots` returns
  the real `{'-L': 'usernames', '-P': 'passwords'}` dict; `build_checklist()`
  still imports clean (no reference-validation regressions from the new
  class attribute).
- `npx tsc --noEmit`, `eslint`, `next build` all clean across every
  touched file.
- Rebuilt **both** images and recreated both containers. Hit the real
  live backend: `GET /api/tools` → hydra's entry now includes
  `"wordlist_slots": {"-L": "usernames", "-P": "passwords"}`. `GET
  /api/tools/wordlists/grouped?category=usernames` → real response with
  `"recommended_category": "usernames"` and the bundled/SecLists groups
  correctly reordered around it (same for `category=passwords`,
  confirming the new override param actually takes priority over the
  item_id path, since no `item_id` was even passed). `GET
  /api/tools/hydra/command?target=example.com&fast=false` → confirmed
  the real built command still correctly uses hydra's bundled
  `usernames.txt`/`passwords.txt` by default (no regression to the
  existing default-command path from adding the new attribute).

**Next steps for the next agent:**
1. Browser E2E (opening the Run Tool dialog for hydra, clicking each of
   the two new wordlist buttons, confirming the picker opens pre-sorted
   to the right category and editing the command correctly per-flag) not
   performed — same outstanding Claude-in-Chrome connection issue as
   entries 35/36/38/39/40/41/42/43.
2. `wordlist_slots` is a general mechanism (any future tool with more
   than one wordlist-shaped flag can use it the same way hydra does now)
   — not audited whether any other already-wrapped tool has the same
   gap hydra did; hydra was fixed because it was reported, not because a
   full audit was done.

---

## 2026-09-01 (43) — "Paths" rename + a parallel "Ports" summary button

**Done (user request: "remove button Paths/Endpoints to Paths, and can
you implement like Paths button at Ports"):**
- Renamed the header button label from "Paths/Endpoints" to "Paths"
  (the underlying feature/endpoints are unchanged — cosmetic label only).
- Refactored entry 42's large inline Paths dialog JSX out of
  `[id]/page.tsx` into its own `frontend/src/components/PathsDialog.tsx`
  — the page component was getting unwieldy with two parallel summary
  features living inline, and extracting it first made the new Ports
  feature's structure obvious to mirror rather than duplicating ~200
  lines of dialog chrome by hand.
- New **Ports** button and `PortsDialog.tsx`, full feature parity with
  Paths: add a port by hand (port/protocol/service/note), remove one
  (deletes if manual, hides if auto-discovered — same distinction as
  paths), a collapsible "Show hidden" restore list, a live count badge,
  and a real-time "N new ports discovered (tool)" toast — all riding the
  same existing `engagement`-state real-time plumbing as Paths, no new
  polling added. Rendered as a simple row-per-port list (port/protocol,
  service, version, a purple "manual" chip, a red sensitive-port chip)
  rather than a tree/graph, since ports don't have Paths' natural
  hierarchical shape.
- `oculus/models.py`: new `ManualPortEntry` (port/protocol/service/note)
  + `Engagement.manual_ports`/`removed_ports` (the latter keyed as
  `"port/protocol"` strings, e.g. `"3306/tcp"`, to disambiguate the same
  port number open on both tcp and udp). New `backend/routers/ports.py`
  mirrors `paths.py` exactly: `POST /ports` (add/upsert), `POST
  /ports/remove`, `POST /ports/restore`, registered in `main.py`.
- New `frontend/src/lib/engagementPorts.ts`: `collectEngagementPorts()`
  parses nmap's real table output (`80/tcp   open  http      nginx
  1.18.0...`) and naabu's real `-silent` bare `host:port` lines, merges
  by `port/protocol` key (nmap's richer service/version wins over
  naabu's bare port when both found the same one), and exposes
  `sensitivePortLabel()` — a port→label lookup deliberately kept in sync
  with `oculus/findings_extractor.py`'s existing `_INTERESTING_PORTS`
  list (3306 MySQL, 6379 Redis, 3389 RDP, ...) so the same ports get
  flagged here as would be flagged as findings.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean across every
  touched/new file.
- Direct logic test (`npx tsx`) against nmap's real table shape (3 ports,
  including a duplicate `80/tcp` also reported bare by naabu) merged with
  naabu's real bare-port lines: correctly deduped to 5 entries sorted by
  port number, nmap's richer `service`/`version` preserved over naabu's
  bare duplicate for port 80; `sensitivePortLabel(3306)` → `"MySQL"`,
  `sensitivePortLabel(80)` → `null`.
- Rebuilt **both** images and recreated both containers; `GET
  /api/health` → `{"status":"ok"}`.
- **Full live round-trip against the real backend**: `POST
  /api/engagements/{id}/ports` with a real manual port → appeared in
  `manual_ports`. `POST .../ports/remove` on that same port → deleted
  outright (`manual_ports` empty, `removed_ports` still empty). `POST
  .../ports/remove` on a port that only exists in this engagement's
  auto-discovered tool output → landed in `removed_ports` (hidden, not
  deleted). `POST .../ports/restore` on that same port → `removed_ports`
  back to empty. All three matched the design on the first real try,
  same as entry 42's path round-trip. `GET /api/engagements/{id}` on the
  live container confirms all four new keys
  (`manual_paths`/`removed_paths`/`manual_ports`/`removed_ports`) are
  present and the engagement detail page still returns 200.

**Next steps for the next agent:**
1. Browser E2E (the Ports button/dialog, the add-port form, remove/
   restore, confirming the sensitive-port chip renders) not performed —
   same outstanding Claude-in-Chrome connection issue as entries
   35/36/38/39/40/41/42.
2. `sensitivePortLabel()`'s list is hand-kept in sync with Python's
   `_INTERESTING_PORTS` rather than shared from one source of truth —
   if that Python list changes, this frontend copy needs a matching edit.
   Worth exposing it from a backend endpoint instead if the two ever
   drift, though duplication was the simpler choice for now (small, rarely-
   changed list).

---

## 2026-09-01 (42) — Add/remove path entries + a node-link graph view

**Done (user request: "implement user can add or remove path tree, or
visualize path" — scoped via AskUserQuestion: manual add/remove with
backend persistence, plus a graphical node-link diagram alongside the
existing list-style tree):**
- `oculus/models.py`: new `ManualPathEntry` (path/status/note/added_at)
  and `Engagement.manual_paths: list[ManualPathEntry]` +
  `removed_paths: list[str]`. Can't edit the raw text a tool's output is
  parsed from, so "removing" an auto-discovered path just hides it via
  `removed_paths` instead of mutating anything; a manual entry is deleted
  outright.
- New `backend/routers/paths.py` (registered in `main.py`): `POST
  /api/engagements/{id}/paths` (add/upsert a manual entry — re-adding an
  existing path updates it in place and un-hides it if it had been
  removed), `POST .../paths/remove` (deletes if manual, else hides), `POST
  .../paths/restore` (un-hides). All three return the updated `Engagement`
  so the frontend can set state directly, same pattern as every other
  mutation endpoint in this app.
- `frontend/src/lib/engagementPaths.ts`: `collectEngagementPaths()` now
  takes `manualPaths`/`removedPaths`, filters hidden paths out entirely,
  and merges in manual entries (tagged `manual: true`, `itemId: null`) —
  a manual annotation always wins a path collision over an unannotated
  auto-discovered duplicate. `pathTree.ts`'s `TreeNode`/`buildPathTree()`
  gained a `manual` flag threaded through (optional on the input, default
  `false`, so `ItemDetail.tsx`'s existing per-item Tree view call sites
  don't need updating).
- `DirectoryTree.tsx`: new optional `onRemove` prop — a red "×" appears on
  hover next to the existing "run here" button for any real (`observed`)
  node when supplied; a small purple "manual" chip marks hand-added
  entries. Also fixed a latent bug found while touching this file: the
  tree's own wrapper `Box` hardcoded `maxHeight: 320` regardless of what
  the caller wanted — added a `maxHeight` prop (default `320`, unchanged
  for existing callers) so the new engagement-wide dialog can size it to
  fill the available space instead.
- New `frontend/src/components/PathGraph.tsx` — a hand-rolled SVG node-
  link diagram of the same `TreeNode` tree (no graph-layout library added;
  the tree is shallow/narrow enough that a plain depth-as-x, leaf-order-
  as-y layout with bezier connector lines reads fine). Same status color
  coding as the tree view, same remove-on-click, native title tooltips
  plus a real MUI `Tooltip` overlay for status detail.
- Engagement page (`[id]/page.tsx`): the Paths/Endpoints dialog (entry 41)
  gained an add-path mini-form (path/status/note + submit), a Tree/Graph
  `ToggleButtonGroup`, `onRemove` wired to the new `/paths/remove`
  endpoint, and a collapsible "Show hidden (N)" section listing
  `removed_paths` with a restore button each — so hiding a path is
  reversible from the UI, not just via a raw API call.

**Also fixed in this entry (user report caught mid-build: "the new path
from nikto doesn't add to paths/endpoints"):** `pathTree.ts`'s
`parseDiscoveredPaths()` had no case at all for nikto's real output shape
— `+ /admin/: This might be interesting.` or, when OSVDB-tagged, `+
OSVDB-3092: /admin/: This might be interesting.` — so every nikto finding
that names a path was silently invisible to both the per-item Tree view
and this entry's new engagement-wide summary, not just a new-feature gap.
New `NIKTO_RE`, gated to `toolName === "nikto"` (same reasoning as the
existing ffuf bare-path fallback: `+ <word>:` alone is too generic a
shape to assume "path" for every tool). No status code in this output
format, so nikto-derived entries carry `status: null`, same as
katana/bare-URL ones.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean across every
  touched file.
- `docker exec oculus-backend-1 python3 -c "from oculus.models import
  Engagement; ..."` — a hand-built legacy JSON payload with no
  `manual_paths`/`removed_paths` keys at all loads with both defaulting
  to `[]` (same backward-compat pattern as entry 36's `icon` field).
- Direct logic test (`npx tsx`) against nikto's real `mock_output()` shape
  (banner/SSL-info/target lines plus four real `+ .../OSVDB-.../` finding
  lines): `parseDiscoveredPaths()` now correctly extracts exactly the 4
  real paths (`/admin/`, `/info.php`, `/backup/`, `/login.php`) and
  correctly ignores the non-path `+ Server:`/`+ SSL Info:`/`+ Start
  Time:` lines.
- Rebuilt **both** images (`docker compose build backend frontend`) and
  recreated both containers; confirmed `GET /api/health` → `{"status":
  "ok"}` and the engagement detail page still returns 200 through the
  live frontend container.
- **Full live round-trip against the real backend**, not just a unit
  test: `POST /api/engagements/{id}/paths` with a real manual entry →
  confirmed it appears in `manual_paths` on the response. `POST
  .../paths/remove` on that same path → confirmed it's deleted outright
  (`manual_paths` empty, `removed_paths` still empty — correct, since a
  manual entry never touches the hide-list). `POST .../paths/remove` on a
  path that only exists in auto-discovered tool output → confirmed it
  lands in `removed_paths` instead (hidden, not deleted, since there's no
  underlying manual entry to delete). `POST .../paths/restore` on that
  same path → confirmed `removed_paths` goes back to empty. All three
  behaviors matched the design exactly on the first real try.

**Next steps for the next agent:**
1. Browser E2E (the add-path form, the remove "×" on both Tree and Graph
   views, the hidden-paths restore list, confirming nikto's paths now
   actually render) not performed — same outstanding Claude-in-Chrome
   connection issue as entries 35/36/38/39/40/41.
2. `PathGraph.tsx`'s layout is a simple depth/leaf-order placement, not a
   real tidy-tree algorithm — fine for the shallow trees this app
   actually produces (a handful of path segments deep), but would need a
   real layout algorithm (or a library) if ever used for something with
   much deeper nesting or many more siblings per node.
3. The nikto path-parsing gap fixed here was found by the user testing a
   real nikto run, not caught by this session's own review of
   `parseDiscoveredPaths()` — worth a dedicated audit of every tool
   wrapped in this app against `pathTree.ts`'s supported line shapes,
   since other tools that can name a discovered path in their own output
   (`wpscan`, `sqlmap` crawling, `dalfox`) may have the same gap and just
   haven't been reported yet.

---

## 2026-09-01 (41) — Engagement-wide "Paths/Endpoints" summary, live + notifying

**Done (user request: "add Paths/Endpoints button for see path tree
summary at above and tell status also if tool run any tool that find
path or endpoints, will update real time and notificate to user"):**
- Entries 34/35's ffuf status-tree work was scoped to a single checklist
  item's Tool output panel — there was no engagement-wide view of every
  path any tool had found across the whole engagement. New
  `frontend/src/lib/engagementPaths.ts`: `collectEngagementPaths()` runs
  the existing `parseDiscoveredPaths()` (entry 34) over **every**
  checklist item's **every** tool output, deduping by path (preferring
  whichever duplicate actually carries a status code, since the same
  `/admin` might turn up once via `katana` with no status and once via
  `ffuf` with a real one).
- New **Paths/Endpoints** button in the engagement page's top header row
  (next to View Report/Markdown/Word — "at above" per the request),
  showing a live count badge (`Paths/Endpoints (14)`). Opens a `Dialog`
  with a status breakdown (`200 × 8`, `403 × 3`, ...) reusing the same
  green/amber color coding as entry 34's `StatusChip`, then the full
  aggregated tree via the existing `DirectoryTree` component (reused as-
  is, not reimplemented) — "Run here" on a node here just points the
  tester back to that path's own checklist item's Tree view, since
  running a tool needs a specific item/target context this aggregate
  view doesn't have.
- **Real-time**: didn't add a second polling/websocket path — the
  summary is a `useMemo` over `engagement.checklist_items`, and
  `engagement` already updates live from the existing plumbing (entry
  25's 3s poll-while-anything-is-running loop, plus `RunToolDialog`'s
  `onDone`/`onStart` callbacks) — so the button's count and the dialog's
  tree just ride that same existing real-time state, no new
  infrastructure needed.
- **Notification**: new effect diffs the current path set against a
  `knownPathsRef` (a plain ref, not state) each time `pathEntries`
  recomputes; any path not seen before fires `toast.info("N new paths
  discovered (tool)")`. The very first computation (initial page load, or
  after switching to a different engagement id) seeds the ref silently
  instead of toasting once per pre-existing path — only *newly*
  discovered paths during the session notify.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Direct logic test (`npx tsx`) against two checklist items' real tool
  output shapes (ffuf's `[Status: N]`/`| URL |` pairs on one item,
  katana's bare-URL-per-line on another, both including the same
  `/admin` path): `collectEngagementPaths()` correctly deduped to 3
  entries, keeping ffuf's `status: 200` for `/admin` over katana's
  `status: null` duplicate; `collectStatuses()` and `buildPathTree()`
  both correct against the deduped set.
- Rebuilt (`docker compose build frontend`) and recreated
  (`docker compose up -d frontend`) the live container per the now-
  standard last step; confirmed `GET /engagements/{id}` on a real
  existing engagement still returns 200 through the live container.
- Browser E2E (opening the dialog against a real multi-tool engagement,
  running a tool and watching the count/toast update live) **not**
  performed — same outstanding Claude-in-Chrome connection issue as
  entries 35/36/38/39/40.

**Next steps for the next agent:**
1. Browser E2E still outstanding — same combined-pass note as entries
   39/40.
2. The "new paths" toast doesn't say *which* checklist item found them
   (only which tool) — a tester with many items running at once might
   want that too. Not added since `EngagementPathEntry` already carries
   `itemId`, straightforward to include in the toast message if asked.

---

## 2026-09-01 (40) — Checklist sidebar: all category tabs collapsed by default

**Done (user request: "can you set default at checklists bar on left
side to close all tab"):**
- `Checklist.tsx`'s `collapsed` state (a `Set` of category names whose
  card list is hidden) previously started as an empty `Set()` — every
  category tab (INFO, CONF, ATHN, ...) rendered fully expanded on first
  load, all 11 sections' items stacked open at once.
- Can't just change the initial `useState` value to
  `new Set(categories)`, since `categories` is empty on this component's
  very first render — the parent engagement page hasn't finished
  fetching yet, so that would collapse nothing. Added a one-shot
  `useEffect` guarded by a `didDefaultCollapse` ref: the first time
  `categories` actually arrives non-empty, it collapses all of them once
  and never again — so a tab a tester deliberately reopens afterward
  (e.g. adding a new checklist item, which re-runs the `categories`
  `useMemo`) doesn't get silently re-collapsed out from under them.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Confirmed `categories` (from the parent `[id]/page.tsx`) and
  `item.category` use exactly the same strings (both come straight off
  `checklist_items[].category`), so the collapsed `Set`'s membership
  check lines up correctly against real category names, not a
  case/formatting mismatch.
- Rebuilt (`docker compose build frontend`) and recreated
  (`docker compose up -d frontend`) the live container per the now-
  standard last step; `GET /engagements` still returns 200 after the swap.
- Browser E2E (opening a real engagement, confirming all tabs render
  collapsed on first load, then confirming clicking one still expands/
  collapses normally and a second unrelated tab isn't affected) **not**
  performed — same outstanding Claude-in-Chrome connection issue as
  entries 35/36/38/39.

**Next steps for the next agent:**
1. Browser E2E still outstanding — same combined-pass note as entry 39.

---

## 2026-09-01 (39) — Bordered icon buttons on entry 38's expand/zoom row

**Done (user follow-up to entry 38: "add border at button more
outstanding ui" — confirmed via AskUserQuestion this meant specifically
the new icon buttons from entry 38, not every IconButton app-wide):**
- The expand button (next to the Raw/Tree/Pretty toggle) and the
  zoom-out/zoom-in/close buttons inside the expanded popup were plain
  borderless `IconButton`s — icon floating with no visible boundary,
  reading as inert/decorative next to the bordered `ToggleButtonGroup`
  sitting right beside them.
- New shared `BORDERED_ICON_BUTTON_SX` constant in `ItemDetail.tsx`: a
  subtle `1px solid rgba(255,255,255,0.14)` border + `borderRadius: 1`,
  teal (`primary.main`) border + faint teal background tint on hover
  (matching the app's existing accent color, `GREEN` in `theme.ts`), and
  a dimmer border for the disabled zoom-limit state. Applied to all four
  buttons (expand, zoom out, zoom in, close) rather than restyling each
  inline, so they read as one consistent control group.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Rebuilt (`docker compose build frontend`) and recreated
  (`docker compose up -d frontend`) the live `oculus-frontend-1`
  container per the now-standard last step (entries 35/37/38); confirmed
  `GET /engagements` still returns 200 after the swap.
- Browser E2E (visually confirming the border/hover state) **not**
  performed — same outstanding Claude-in-Chrome connection issue as
  entries 35/36/38.

**Next steps for the next agent:**
1. Browser E2E still outstanding across entries 35/36/38/39 — worth one
   combined manual pass once the extension connection issue is sorted,
   rather than four separate follow-ups.

---

## 2026-09-01 (38) — Expand-to-popup + zoom for the Tool output panel

**Done (user request: "at the result can you implement can show popup
window for scaling result to see" — the inline Tool output panel is
capped at a small `maxHeight`/font size so the rest of the checklist item
stays usable, which makes a long/dense result genuinely hard to read in
place):**
- `ItemDetail.tsx`: extracted the Raw/Tree/Pretty body rendering (three
  near-identical blocks that were inline before) into one shared
  `renderOutputBody(fontSize, maxHeight)` function, parameterized instead
  of duplicated, so the same logic drives both the small inline panel and
  the new popup at a different size — one source of truth for what
  "the result" actually looks like in each view.
- New expand button (small `OpenInFull` icon) next to the Raw/Tree/Pretty
  toggle opens a `Dialog` (`maxWidth="lg"`, 85vh tall) showing the same
  active tab's output at a much larger `maxHeight` and an adjustable zoom
  level (`ZoomIn`/`ZoomOut`, 75%–250% in 25% steps, shown as a live "N%"
  readout) — scales the body's font size, which is what "scaling to see"
  actually means for a monospace text/tree panel like this one.
  The popup also carries its own copy of the filter/status-chip row (same
  `filterQuery`/`statusFilter` state as the inline panel, entry 35 — not
  a separate filter), so a tester can filter *and* zoom in the same view
  rather than having to set a filter in the small panel first.
- Popup and inline panel share state (`activeOutput`, `outputView`,
  filters) — closing the popup and looking at the inline panel again
  shows the same tab/view/filter, no separate "popup mode" to fall out of
  sync with.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Confirmed (again, same lesson as entries 35/37) that the real running
  app is the Docker Compose `oculus-frontend-1` container, not a bare
  dev server — rebuilt (`docker compose build frontend`) and recreated
  (`docker compose up -d frontend`) it so this change is actually live,
  then confirmed `GET /engagements` on the live container still returns
  200 after the swap.
- Browser E2E (clicking the expand button, dragging the zoom slider
  through a real result) **not** performed — Claude-in-Chrome extension
  connection issue, same outstanding item as entries 35/36.

**Next steps for the next agent:**
1. Browser E2E still outstanding — see entries 35/36's same note. Worth
   a manual click-through: open a tool output, hit expand, zoom in/out,
   confirm the Tree view's "Run here" buttons still work at the larger
   size.
2. Zoom only scales font size (`fontSize: 12 * zoom`), not layout spacing
   (padding/line-height stay fixed) — fine for the 75%–250% range chosen,
   but worth widening line-height proportionally too if a much larger
   zoom range is ever wanted.

---

## 2026-09-01 (37) — Fix: `zap` shows "not installed" even with Docker Desktop running

**Done (user report: the app's own install-hints message told them to
"Install Docker Desktop... docker desktop already installed but isn't
installed" — i.e. Docker Desktop *is* running on the host, but the app
still treats `zap` as unavailable):**
- Root cause, exactly the gap flagged as a known limitation back in entry
  27: **this app's own backend runs inside its own Docker container**
  (`oculus-backend-1`, confirmed via `docker ps`) — Docker Desktop
  running on the host is irrelevant to what that *container* can see.
  Two things were missing inside it: the `docker` CLI wasn't installed at
  all (confirmed: not in the image), and even if it were, nothing wired
  the container up to actually reach the host's Docker daemon.
  `ZapTool.is_available()` (inherited from `BaseTool`) just checks
  whether `docker` resolves on `PATH` — false on both counts, hence the
  "not installed" hint despite Docker Desktop being right there on the
  host.
- `Dockerfile`: added `docker.io` to the backend image's apt install list
  — this installs the `docker` **client** only; no `dockerd` runs inside
  the container itself.
- `docker-compose.yml`: backend service now mounts the host's
  `/var/run/docker.sock` into the container at the same path. That's what
  actually lets the `docker` CLI *inside* the container talk to the *host's*
  Docker Desktop daemon — installing the CLI alone doesn't do this by
  itself, both pieces were needed together. Documented the real tradeoff
  inline: this hands the backend container root-equivalent control over
  the host (the standard Docker-socket-mount caveat) — acceptable for a
  local single-user pentest tool, explicitly flagged as not something to
  do on a shared/multi-tenant host.

**Verified:**
- `docker compose build backend` — clean rebuild with the new
  `docker.io` layer.
- `docker exec oculus-backend-1 which docker` → `/usr/bin/docker`;
  `docker exec oculus-backend-1 docker ps` → real output listing the
  host's own running containers (`oculus:latest`, `oculus-frontend`),
  proving the socket-mount actually reaches the host daemon, not just
  that the CLI binary exists.
- Hit the real running backend: `GET /api/tools` → `zap`'s
  `"available"` flipped `false` → `true` (recreated the container after
  the image rebuild — a plain `docker compose build` doesn't restart the
  already-running container on its own, confirmed the hard way: `zap`
  still showed `available: false` immediately after the build until
  `docker compose up -d backend` recreated it).
- **Full real scan through the actual application code path**, not just
  a preview: `docker exec oculus-backend-1 python3 -c "ZapTool(...).run()"`
  against `example.com` — `exit_code: 0`, real ZAP output (dozens of real
  `PASS:` rule lines). First tried `scanme.nmap.org` (this project's usual
  authorized test target) and got a real (not simulated) connection
  failure — `Connection refused` on port 443, since that host doesn't
  serve HTTPS at all — confirming the run was genuinely hitting the
  network via the real container, not returning canned/simulated output;
  switched to `example.com` (does serve HTTPS) for the clean pass.

**Next steps for the next agent:**
1. This closes out entry 27's item 2 ("if oculus's own backend is ever
   run inside Docker, zap won't be available there unless given access
   to the host's Docker socket") — that limitation no longer applies for
   the `docker compose up` path. `README.md`'s ZAP/Docker callout section
   (added in entry 27) should be revisited to reflect that this is now
   solved for the shipped compose setup, not still an open caveat.
2. The `docker compose run --rm oculus ...` CLI/TUI service (profile
   `cli`) does **not** get the same socket mount — only the `backend`
   service does. `zap` would still show unavailable there. Not fixed
   here since it wasn't reported and the web UI is the primary interface;
   worth mirroring the same `volumes:` addition to the `oculus` service
   if a CLI/TUI user hits the same report for that path.

---

## 2026-09-01 (36) — Icon picker on New Engagement (like each tool's own badge)

**Done (user request: "when create new engagement can you implement can
select icon or use like icon tools" — i.e. give an engagement a
selectable icon the same way each tool already has its own colored badge
in `toolLogos.ts`):**
- New `frontend/src/lib/engagementIcons.tsx` — a fixed, curated set of 12
  icon options keyed by what a pentest engagement's target actually is
  (`web`/`api`/`mobile`/`cloud`/`network`/`database`/`iot`/`auth`/
  `ecommerce`/`corporate`/`cli`/`other`), each a real MUI icon + a
  distinct color, same pattern as `toolLogos.ts`'s per-tool monogram+color
  table. Chose a curated key set over a free-text/open icon library
  deliberately: cheap to store (a short string, no sanitizing needed
  anywhere it's rendered) and every option is genuinely relevant to this
  app's domain, matching the "like icon tools" ask directly.
- `oculus/models.py`: `Engagement` gained `icon: str = "web"`.
  `oculus/state.py`'s `list_all()` summary dict now includes it.
  `backend/routers/engagements.py`'s `NewEngagement` body gained
  `icon: str = "web"`, threaded into `create_engagement()`.
  `frontend/src/lib/types.ts`: `Engagement`/`EngagementSummary` both
  gained `icon: string`. `api.ts`'s `createEngagement()` gained an `icon`
  param.
- `frontend/src/app/engagements/page.tsx`: new `IconPicker` — a row of
  selectable icon buttons (highlighted border+tint in that icon's own
  color when selected) added to the New Engagement dialog, defaulting to
  `web`. `EngagementCard` now renders the chosen icon in a small colored
  tile next to the engagement's name (previously just name+ID, no visual
  identity at all beyond that).
- Backward compatible by construction, not by special-casing: Pydantic's
  field default (`icon: str = "web"`) means every engagement saved before
  this change (no `icon` key in its JSON at all) validates and loads with
  `icon="web"` automatically — confirmed directly against a hand-built
  legacy JSON payload missing the field entirely, not just assumed from
  reading the Pydantic docs.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- `python3 -c "from oculus.models import Engagement; ..."` — direct
  construction with `icon='api'` round-trips correctly through
  `model_dump_json()`; a legacy JSON blob with no `icon` key at all loads
  with `icon='web'` (the backward-compatibility case above).
- Found mid-session that the actual running app is **Docker Compose**
  (`oculus-backend-1`/`oculus-frontend-1`, `docker ps` confirmed —
  earlier sessions' "full browser E2E" entries were against this same
  setup, not a bare local dev server as briefly assumed while investigating
  entry 35's failed connection). Rebuilt both images
  (`docker compose build backend frontend`) and recreated the containers
  (`docker compose up -d backend frontend`) so the real running app
  reflects this change, then confirmed against the **live** container
  over the network: `POST /api/engagements` with `"icon":"mobile"` →
  response echoed `"icon":"mobile"`; `GET /api/engagements` on the
  pre-existing `securebank` engagement (created before this change)
  correctly shows `"icon":"web"` (the default, not an error/null) proving
  the backward-compat path holds against real on-disk data, not just the
  hand-built test payload above. Test engagements created during this
  verification deleted afterward (`DELETE /api/engagements/{id}` x2).
  `GET /engagements` on the live frontend container returns 200.
- Browser E2E (clicking through the actual icon picker UI) **not**
  performed — the Claude-in-Chrome extension reported "not connected"
  both before and after the container rebuild in this session, same
  outstanding issue noted in entry 35.

**Next steps for the next agent:**
1. Browser E2E is still outstanding for both this entry and entry 35 —
   the Claude-in-Chrome extension connection issue affects any session
   trying to visually verify UI changes right now, not something specific
   to this feature. Worth checking whether the extension itself needs
   reinstalling/restarting, and until then doing a manual click-through.
2. Only wired into creation — there's no "edit an existing engagement's
   icon" path (no update-engagement endpoint exists at all yet, icon or
   otherwise). Worth adding if a tester wants to change one after the
   fact, not attempted here since it wasn't asked for.
3. Since the real running app is Docker Compose (not a local dev
   server), **every future frontend/backend change needs `docker compose
   build backend frontend && docker compose up -d backend frontend`
   before it's actually live** — confirmed the hard way this session
   (entry 35's fix landed in source but the running containers were still
   serving the pre-fix image the whole time it was reported "done").
   Worth doing this rebuild+recreate as a standard last step for any
   future oculus change, not just re-running `tsc`/`eslint`/`next build`
   against source.

---

## 2026-09-01 (35) — Tool output: always-visible Raw view + text/status filter

**Done (user follow-up to entry 34: "each tool can you add button for see
raw result and filter and at the filter result at ffuf show status also
that 200,301,302 or 403"):**
- `ItemDetail.tsx`'s Tool output Raw/Tree/Pretty `ToggleButtonGroup` was
  previously only rendered at all when a Tree or Pretty view was also
  available (`{(discoveredTree || prettyResult) && (...)}`) — an output
  with neither (most tools: nmap, nuclei, etc.) showed raw text with no
  toggle at all, not even a "Raw" button, just an implicit view. Now
  always rendered so every tool's output has an explicit **Raw** button,
  with Tree/Pretty added alongside only when actually applicable — same
  underlying content, just consistently surfaced per the request.
- New filter row (always shown once any tool output exists): a **Filter
  output…** text search box (plain case-insensitive substring match,
  works against any tool's raw lines — nmap, curl, whatever) plus, only
  when the active output is ffuf/gobuster-shaped, a **status filter**
  (`All` / one chip per status code actually present in that run's
  results — commonly `200`/`301`/`302`/`403`, not a hardcoded fixed set,
  since a run might also turn up e.g. `401` or `500`). Chips reuse the
  same color coding as entry 34's `StatusChip` (`200` green, `401`/`403`
  amber).
- `frontend/src/lib/pathTree.ts`: two new exports —
  `collectStatuses(entries)` (distinct status codes present, sorted, for
  the chip list) and `filterRawByStatus(output, status)` (filters ffuf's
  paired `[Status: N]` + `| URL |` lines, or gobuster's inline `(Status:
  N)` line, down to just the matching ones — passthrough/no-op for any
  other tool's output shape, since those never carry a status code to
  filter on in the first place).
- The status filter and text filter both apply to **both** the Raw view
  (via `filterRawByStatus` + per-line substring match) and the Tree view
  (by filtering the `{path, status}` entries before `buildPathTree()`,
  rather than filtering the already-built tree) — switching between Raw
  and Tree while a filter is active shows the same filtered result either
  way. `DirectoryTree` gained an `emptyMessage` prop so an empty *filtered*
  tree reads as "No discovered paths match this filter" rather than the
  pre-existing "couldn't be parsed at all" message, which would have been
  misleading when the real cause is just an active filter.
- Filters reset when switching output tabs (a status filter that made
  sense for ffuf shouldn't silently carry over and hide everything in an
  unrelated nmap tab) — done via a `selectOutputTab()` handler on the
  `Tabs`' `onChange`, not a `useEffect`, since resetting state
  synchronously inside an effect body triggers React's
  `set-state-in-effect` lint rule (cascading-render risk) — caught by
  `eslint` during this session, not assumed.

**Verified:**
- `npx tsc --noEmit`, `eslint`, and `next build` all clean.
- Direct logic test (via `npx tsx`, not just type-checking) against
  ffuf's own real `mock_output()` shape from entry 34: `collectStatuses`
  correctly returned `[200, 301, 403]`; `buildPathTree` on
  status-403-only-filtered entries produced a tree containing only
  `/backup`; `filterRawByStatus(mock, 200)` and `filterRawByStatus(mock,
  403)` each correctly kept only their matching `[Status: N]`/`| URL |`
  pairs while preserving the trailing `:: Progress: ...` summary line
  verbatim in both.
- Browser E2E **not** performed this round — the Claude-in-Chrome
  extension reported "not connected" when attempted (browser extension
  session issue, not a code issue); confirmed the actual running
  `next-server` process is `next dev` (turbopack dev build, hot-reloads
  on save), so no separate rebuild/restart was needed for this fix to be
  live, but a human should click through the new Filter box and status
  chips in a real browser to confirm the UI renders as expected before
  calling this fully done.

**Next steps for the next agent:**
1. Browser E2E is still outstanding for this entry specifically (see
   above) — worth doing once the Claude-in-Chrome extension connection is
   working again, or manually.
2. The text filter is a plain substring match on raw lines / discovered
   paths — no regex/AND-of-terms support. Fine for the "find 200s
   containing /api" kind of use this was built for; would need a real
   query mini-language if a tester wants more than that.

---

## 2026-09-01 (34) — ffuf: per-endpoint status (200 open vs. needs permission)

**Done (user request: "can you add status at ffuf for user know any
endpoint can access 200, or must have a permisson for access"):**
- Root-caused first: `oculus/tools/ffuf_tool.py`'s real `build_command()`
  ran ffuf with `-s` (silent), which strips the `[Status: N, ...]` line
  from every match entirely — so even though `mock_output()` already
  showed a status per URL (its own `-v`-style verbose format, `[Status:
  200, ...]` immediately followed by `| URL | ...`), a real run never
  actually produced that information at all. Fixed by dropping `-s` in
  favor of `-v`, and added `401` to `-mc` alongside the existing
  `200,301,302,403` — 401/403 are the two codes that mean "exists but
  needs credentials," which is exactly the distinction being asked for.
- `oculus/findings_extractor.py`: `extract_ffuf()` rewritten to pair each
  `[Status: N]` line with the `| URL |` line that follows it (falls back
  to the old bare-path-per-line parse for pre-existing saved runs from
  before `-v` replaced `-s`, which carry no status at all).
  `extract_gobuster()` similarly now captures its already-inline `(Status:
  N)` instead of discarding it. Both now thread a `path → status` map into
  `_flag_interesting_paths()`, which appends a plain-English note to each
  finding's description: "(HTTP 200 — publicly accessible)" vs. "(HTTP
  401/403 — requires permission/authentication to access)".
- `frontend/src/lib/pathTree.ts`: `parseDiscoveredPaths()` now returns
  `{path, status}[]` instead of bare strings (captures ffuf's `[Status:
  ...]` line the same way the Python extractor does), and `TreeNode`
  gained a `status: number | null` field set by `buildPathTree()`.
- `frontend/src/components/DirectoryTree.tsx`: new `StatusChip` — a small
  outlined chip next to each discovered leaf node, green "200 open" or
  amber "401/403 needs auth" (any other code shown as a plain gray
  number), so a tester scanning the Tree view can tell open vs.
  permission-walled endpoints apart without opening Raw output.

**Verified:**
- `python3 -c "from oculus.tools.ffuf_tool import FfufTool; from
  oculus.findings_extractor import extract_ffuf; ..."` against the real
  `mock_output()` (which already used the `-v` shape) — confirmed
  `.env`/`.git`/`config.php.bak` findings now say "(HTTP 200 — publicly
  accessible)" and the `/backup` finding says "(HTTP 403 — requires
  permission/authentication to access)".
- `python3 -c "from oculus.checklist import build_checklist; ..."` —
  import-time tool-reference validator passes clean.
- `npx tsc --noEmit` and `eslint` clean on `pathTree.ts`,
  `DirectoryTree.tsx`, `ItemDetail.tsx` (its call site didn't need
  changes — it only checks `paths.length > 0`, agnostic to element shape).

**Next steps for the next agent:**
1. Not done here (out of scope, UI-only ask): a real ffuf run's finding
   description now correctly separates open vs. auth-walled per path, but
   `_flag_interesting_paths()` still assigns the same fixed severity
   regardless of status (e.g. an admin panel that's 401-walled and one
   that's wide open at 200 both currently score the same). Worth
   revisiting if a tester wants the *severity*, not just the description
   text, to reflect that distinction.
2. `gobuster`'s `DirectoryTree`/`StatusChip` path also benefits from this
   fix automatically (its output already carried inline status, just
   wasn't captured) — not separately verified against a real gobuster run
   this session, only against the parsing logic directly.

---

## 2026-09-01 (33) — Cancel a running tool (stop + resume/edit)

**Done (user report: a run stuck taking too long had no way to stop it —
had to wait it out before running a different tool or a faster edited
command):**
- `oculus/tools/base.py`: `run_tool()` rewritten to poll a
  `cancel_event: threading.Event | None` every 0.25s alongside the
  existing timeout deadline, instead of one blocking
  `thread.join(timeout=timeout)` — that blocking form couldn't react to
  anything mid-wait. On cancel, kills the whole process group (same
  `os.killpg(..., SIGKILL)` the timeout path already used, so
  grandchildren like testssl.sh's spawned openssl don't linger) and
  returns exit code `CANCELLED_EXIT_CODE` (130, new module constant) with
  `[CANCELLED]` appended to whatever output had streamed so far.
  `BaseTool.run()` and `Orchestrator.run_tool()` both thread the new
  `cancel_event` param through unchanged otherwise.
- `backend/ws.py`: new module-level `_RUNNING: dict[(eng_id, item_id),
  threading.Event]` registry and `cancel_run(eng_id, item_id) -> bool`
  helper. The run's `cancel_event` is registered right before the worker
  thread starts and popped in its `finally` — deliberately **not** tied
  to the WebSocket connection's lifetime, same as the run itself already
  isn't (per entry on background-run streaming), so a stop request works
  even from a browser tab/dialog that wasn't the one that started the
  run. The "done" WS message now includes `result.cancelled` (exit code
  == `CANCELLED_EXIT_CODE`) so the frontend can show "stopped" instead of
  a generic failure.
- `backend/routers/items.py`: new `POST
  /api/engagements/{id}/items/{item_id}/cancel` — 409s if the item isn't
  currently `RUNNING`, or if it says `RUNNING` but no `cancel_event` is
  registered (the run finished in the gap between the tester's click and
  the request landing — not an error). Otherwise calls
  `ws.cancel_run()` and returns 200 immediately; the actual kill/save
  happens asynchronously in the worker thread, same as it always did.
- `frontend/src/components/RunToolDialog.tsx`: a **Stop** button next to
  Run while this dialog's own WebSocket is watching a live run, and a
  **Stop it** button on the existing "already running in the background"
  warning Alert (for a run started from a different dialog/tab — no live
  ws here, so the button just calls the REST endpoint and the item prop
  catches up via the parent's existing 3s polling). Cancelling
  re-enables the command field and Run button immediately — the point
  being able to edit the command (lower a timeout/thread flag) and rerun
  right away instead of waiting out the original run.
- `frontend/src/lib/types.ts` / `api.ts`: `RunResult.cancelled: boolean`
  added; new `api.cancelRun(engId, itemId)`.

**Verified:**
- Direct `run_tool()` call with a `sleep 30` and a `cancel_event` set
  after 1.5s from another thread: returned in 1.53s (not 30s), exit code
  130, output `"\n[CANCELLED]"`.
- Process-group kill confirmed real: `bash -c 'sleep 30 & wait'` (nested
  child, same shape as testssl.sh→openssl) cancelled after 1s — `pgrep -f
  "sleep 30"` found nothing lingering afterward.
- Full backend API test: started a real run over a WebSocket
  (`custom_command` executes for real regardless of tool name), cancelled
  via a separate REST call from an unrelated process mid-run — item
  flipped to `failed` with `tool_outputs: {"curl": "...\n[CANCELLED]"}`
  in ~1.5s total instead of the command's real 20s duration.
- Specifically reproduced the "no dialog watching it" case end-to-end:
  opened a WS, sent a slow command, closed the WS immediately after the
  first output line arrived (run keeps going server-side, confirmed
  status still `running`), then cancelled via REST from a completely
  separate call — worked, `failed` status with `[CANCELLED]` output.
  409 confirmed on a second cancel attempt (nothing left to stop) and on
  an item that was never running.
- Full browser E2E: opened WSTG-INFO-02, selected `curl`, edited the
  command to `sleep 20`, hit Run, confirmed the **Stop** button appears
  next to Run while it's going, clicked it, confirmed within ~2s the
  dialog shows the amber "Stopped — partial output saved..." message,
  the command field and Run button re-enable, and a "curl stopped" toast
  appears — matching the reported need to stop-then-edit-then-rerun.
  Zero console errors. Test engagements and Playwright script deleted
  after use.
- `npx tsc --noEmit` clean; `python3 -c "from backend.main import app"`
  imports with no circular-import issues (`backend/routers/items.py`
  imports `backend/ws.py`, not the reverse).

**Next steps for the next agent:**
- None outstanding. A cancelled run's item lands in the existing
  `FAILED` status (same bucket a timeout already uses) rather than a new
  dedicated status — kept deliberately minimal to avoid touching every
  frontend status icon/color/order list (`frontend/src/lib/severity.ts`'s
  `STATUS_ORDER`, `Checklist.tsx`'s icons, etc.) for what the `output`
  text (`[CANCELLED]` vs `[TIMEOUT]`) already disambiguates. Revisit only
  if a tester specifically asks to distinguish "I stopped it" from "it
  actually failed" in the checklist sidebar itself, not just inside the
  Run Tool dialog (which already does distinguish them via
  `result.cancelled`).

---

## 2026-08-27 (32) — Fix: gowitness v2→v3 CLI rewrite broke the wrapper's command

**Done (user report: `gowitness single http://192.168.2.15 --timeout
30` → `An error has occured. The error was: unknown command "single"
for "gowitness"`):**
- Root-caused by installing gowitness fresh (`go install
  github.com/sensepost/gowitness@latest`) — it now installs v3 (banner:
  "v3, with <3 by @leonjza"), which rewrote the CLI entirely from v2's
  bare `gowitness single <url> --timeout N` to a `scan` subcommand
  family. Confirmed the real v3 invocation directly against `gowitness
  scan single --help`: `gowitness scan single -u <url> -T <timeout>` —
  note `-u` is a real flag now (not a bare positional) and `-T`
  (capital) is the timeout; lowercase `-t` was repurposed to thread
  count in v3, a different flag entirely.
- `oculus/tools/gowitness_tool.py`: `build_command()` rewritten to the
  real v3 command. `example` updated to match.
- `run_help()` overridden (previously used `BaseTool`'s default): the
  generic `[binary, help_flag]` form would run top-level `gowitness
  --help`, which only lists the `scan`/`report`/`version` subcommand
  families, not the actual `-u`/`-T` flags a tester needs for this
  wrapper's exact invocation. Now runs `gowitness scan single --help`
  directly — same pattern used for `zap` in entry 31.
- `mock_output()` rewritten to match v3's real (much terser than v2's)
  default output: one `WARN` about no writers configured, then one
  `INFO result` line with the actual result fields (status code,
  title, `have-screenshot`).

**Verified:**
- Real `run_tool()` call against `https://example.com` through the
  actual application code path: `exit_code: 0`, real captured output
  (`WARN no writers have been configured...` /
  `INFO result 🤖 target=https://example.com status-code=200
  title="Example Domain" have-screenshot=true`).
- `run_help()` confirmed to return the real `scan single --help` text
  (correct ASCII banner + `-u`/`-T`/etc. flags), not the top-level
  subcommand list.
- Hit the real backend API (`GET /api/tools/gowitness/command?
  target=192.168.2.15&fast=false`) — returned the exact fixed command,
  confirming the fix against the user's own reported target.
- Full browser E2E against a fresh test engagement: opened WSTG-INFO-07
  → Run Tool → gowitness → Run, confirmed the old `unknown command
  "single"` error text is gone and the dialog reaches "✓ Done — output
  saved to this item." with the real `have-screenshot=true` result
  streamed into the terminal panel. Zero console errors. Test
  engagement and Playwright test script deleted after use.
- `npx tsc --noEmit` clean (backend/tool-only fix, no frontend changes
  needed); `python3 -c "from oculus.checklist import build_checklist;
  ..."` import-time validation passes (24 tools, no import errors).

**Next steps for the next agent:**
- None outstanding for this fix. If gowitness majors again in the
  future, same approach applies: reinstall fresh, diff `--help` output
  against the wrapper's `build_command()`, don't assume the old syntax
  still works.

---

## 2026-08-27 (31) — OWASP ZAP integration (Docker-based), mapped to WSTG-INFO-07

**Done (user question: "wstg-info-07 it use spider ZAP, in my project
can integrate?" — an exploratory question, confirmed the approach and
tradeoff with the user via AskUserQuestion before building):**
- New `oculus/tools/zap_tool.py` — wraps ZAP's own official automation
  script, `zap-baseline.py` (spider + passive scan rules, **no active
  attacks**), via `docker run --rm -t zaproxy/zap-stable
  zap-baseline.py -t <url> -m <mins> -I`. Architecturally different
  from every other tool wrapped here: `binary = "docker"`, the actual
  scanner runs inside a container ZAP ships and maintains, not a local
  install. `-I` forces exit 0 even when the passive scan finds WARN/FAIL
  alerts — without it, a scan that successfully found real issues would
  report a nonzero exit code, which oculus's own status tracking would
  misread as "the tool run failed" rather than "ran fine, found things."
  Fast = `-m 1` (1-minute spider budget), Full = `-m 5`.
- `run_help()` overridden: the inherited default would run `docker -h`
  (since `binary` is `"docker"`, not the actual tool) and show Docker's
  own help instead of `zap-baseline.py`'s — now runs `docker run --rm
  zaproxy/zap-stable zap-baseline.py -h` instead, the right target.
- `oculus/checklist.py`: added to `WSTG-INFO-07`'s tools alongside
  `katana`/`gowitness` — the real WSTG-INFO-07 methodology names ZAP's
  spider explicitly (confirmed against the real page in an earlier
  audit this session, entry 27).
- New `extract_zap()` in `oculus/findings_extractor.py` — parses
  `WARN-NEW`/`FAIL-NEW` alert blocks (`<title> [<rule-id>] x <count>`
  followed by tab-indented affected URLs), zap-baseline.py's own real
  reporting format. `FAIL-NEW` → HIGH, `WARN-NEW` → MEDIUM (its own
  pass/fail threshold, not ZAP's separate internal risk rating, which
  isn't in this short-format output at all).
- `frontend/src/lib/toolLogos.ts`: added a `zap` badge, and — found
  while in this file — `curl`/`wget` had been missing their own badge
  entries since they were added (falling back to a generic gray
  monogram), fixed alongside.

**Verified:**
- Ran the real `zaproxy/zap-stable` image (confirmed size: 1.16GB
  content / 3.6GB on disk, not the "few hundred MB" first guessed —
  corrected in the description before committing) against
  `scanme.nmap.org` (an nmap.org-authorized test target) through the
  actual `oculus.tools.base.run_tool()` code path: exit code 0 (the
  `-I` flag confirmed working), 10 real `WARN-NEW` alerts found,
  completed in 46s.
- Ran `extract_zap()` against that **real captured output** (not just
  the mock) — correctly extracted all 10 real findings at the expected
  severities.
- Confirmed via the real `--help` output (fetched through the backend's
  `/api/tools/zap/help` endpoint) that every flag used in
  `build_command()` (`-t`, `-m`, `-I`) is real and correctly spelled.
- Full browser E2E: Tools catalog shows the zap card with correct logo/
  description/example/install status; Run Tool dialog's Tool dropdown
  correctly lists `zap` for WSTG-INFO-07 with the real command preview;
  Help button shows the real `zap-baseline.py` usage text fetched live.
  Zero console errors. Test engagement deleted after use.
- `npx tsc --noEmit` clean; `python3 -c "from oculus.checklist import
  build_checklist; ..."` import-time validation passes (24 tools, 17
  extractors registered).

**Next steps for the next agent:**
1. `zap`'s output arrives mostly buffered in one large burst near the
   end rather than streaming line-by-line (confirmed against a real
   run) — this is the JVM inside ZAP's own container buffering its
   output, not something `PYTHONUNBUFFERED` (entry 30) can fix since
   ZAP isn't Python. Not pursued further; documented as a known
   limitation in the tool's own description rather than silently
   left unexplained.
2. If oculus's own backend is ever run *inside* Docker (see
   `docker-compose.yml`), `zap` won't be available there unless that
   container is given access to the host's Docker socket — Docker-in-
   Docker wasn't set up for this feature. Documented as a callout in
   `README.md`'s Tool Wrappers section rather than solved; the CLI/
   local-Python and `./run.sh` backend paths aren't affected.

---

## 2026-08-27 (30) — Fix: arjun `[TIMEOUT]` against a real target, plus a broader live-streaming bug

**Done (user report: `arjun -u http://192.168.2.15 --stable -t 10 ->
[TIMEOUT]`):**
- Root-caused against arjun's real installed source (not assumed):
  `--stable` **silently forces arjun's own thread count to 1**
  regardless of any `-t` flag — confirmed directly in
  `arjun/__main__.py`: `if mem.var['stable'] or mem.var['delay']:
  mem.var['threads'] = 1`. So the `-t 10` in the reported command was
  never doing anything; combined with arjun's default ~26k-word
  wordlist (confirmed: `wc -l db/large.txt` → 25889) run fully
  single-threaded against a real host, the old blanket 180s
  (`BaseTool.timeout_seconds` default) was never going to be enough —
  this is a genuinely slow tool by design when run this way, not a
  hang or a broken command.
- `oculus/tools/arjun_tool.py`: full-mode timeout raised to 900s
  (`timeout_seconds = 900`, applied via `get_timeout()`). Also fixed
  Fast mode, which had a real, separate bug: it still scanned the
  full ~26k-word list (only upping thread count), unlike every other
  tool's Fast variant in this codebase (narrower scope, not just more
  parallelism) — now uses arjun's own bundled `small` wordlist
  (confirmed: 835 words vs. large's 25889), genuinely fast. Dropped
  the misleading `-t 10` from the full command since arjun ignores it
  under `--stable` anyway. `mock_output()` corrected to match real
  default behavior too (GET-only — arjun's own `-m` defaults to GET
  and neither command variant adds `-m POST`; the old mock's `[POST]`
  section was never accurate).
- **Bigger fix found along the way**: confirmed arjun's stdout is
  **fully block-buffered when not a TTY** (a subprocess pipe never
  is) — `timeout 8s` on a real `--stable` run produced **zero** output
  without `PYTHONUNBUFFERED=1`, vs. 8 real lines *within the same 8s*
  with it. This meant arjun's "live" output streaming was never
  actually live — nothing arrived until the process exited on its
  own, and a run killed by our own timeout (the exact scenario a
  tester hits) lost 100% of its output instead of showing whatever
  had run so far. `oculus/tools/base.py`'s `_subprocess_env()` now
  sets `PYTHONUNBUFFERED=1` for every tool subprocess — fixes this for
  arjun and any other Python-based wrapped tool (sqlmap, wafw00f,
  commix), harmless no-op for every non-Python tool (nmap, Go
  binaries, etc.), since they don't read that env var at all.

**Verified:**
- Read arjun's actual installed source to confirm the `--stable` →
  `threads=1` behavior and the real wordlist sizes, rather than
  guessing.
- Direct real-tool test (not simulated): ran real arjun against
  `scanme.nmap.org` (nmap.org's authorized test target) with the new
  Fast command (`-w small -t 20`) — completed in well under the new
  90s Fast timeout. Ran the new Full command (`--stable`, no `-t`) —
  confirmed via raw shell (`timeout 8s`, redirected to a file) that it
  produces zero bytes without `PYTHONUNBUFFERED=1` and real progress
  lines with it.
- Confirmed the fix through the **actual application code path**, not
  just raw shell: called `oculus.tools.base.run_tool()` directly with
  the real arjun `--stable` command and a live `on_line` callback —
  7 real lines arrived within 0.2 seconds of starting. Confirmed
  separately that a timed-out/killed run still preserves and returns
  whatever output arrived before the kill (previously this would have
  been empty).
- Confirmed `wafw00f` (another Python-based wrapped tool) still runs
  and produces correct output with the new env var set — the global
  change doesn't break anything already working.
- `python3 -c "from oculus.checklist import build_checklist; ..."` —
  import-time validation passes clean. Hit the live backend's preview
  endpoint with the exact target from the report (`192.168.2.15`) and
  confirmed both Fast and Full commands build correctly.

**Next steps for the next agent:**
1. `PYTHONUNBUFFERED=1` is now set globally for all tool subprocesses.
   If a future Python-based tool wrapper is added, its live output
   should stream correctly out of the box — no per-tool env var
   needed, this was intentionally fixed at the shared `_subprocess_env()`
   level specifically so it wouldn't need repeating.
2. Even with the raised 900s Full-mode timeout, arjun's `--stable`
   mode is inherently slow (single-threaded, ~26k words) — a
   tester in a real hurry should reach for Fast mode (now genuinely
   fast) rather than waiting out Full mode, or hand-edit the command
   to add `-w medium` (10984 words) as a middle ground between the two
   bundled sizes.

---

## 2026-08-27 (29) — Pretty-format toggle: added XML and JavaScript

**Done (user follow-up: "did you add other languages? such as python,
javascript, typescript or anything? for prettier format" — answer at
the time was no, only JSON/HTML; this entry adds two of them for
real):**
- `frontend/src/lib/prettyFormat.ts`: reworked detection to check the
  output's own `Content-Type` response header first (from curl -i/
  wget -S's header block) — far more reliable than guessing from the
  bytes, and it's already sitting right there in the tool's own
  output. `application/xml`/`text/xml`/`*+xml` → xml,
  `application/javascript`/`text/javascript`/`application/
  x-javascript`/`application/ecmascript` → javascript, plus the
  existing json/html mappings. Content-sniffing (the original
  approach) is now the fallback for output with no header block at
  all (e.g. `wget -O -` without `-S`) — JS sniffing in particular
  requires **two or more** distinct JS-specific signals (function
  declarations, arrow functions, `const`/`let`/`var` assignment,
  `import ... from`, `console.log`, DOM API calls) together before
  tagging something as JS, specifically to avoid a plain log line that
  happens to contain the word "function" getting misdetected —
  verified this guard directly (see below).
- XML reuses the existing HTML tag-reflow-and-indent formatter
  (renamed `formatMarkup`, took a `treatAllAsPaired` flag since XML
  has no void-tag list the way HTML does) rather than writing a
  second near-identical indenter.
- New `formatJavaScript()`: a string-literal-aware reflow (tracks
  whether it's inside `"`/`'`/`` ` `` so a `;` or `{` inside a string
  doesn't split the line) that breaks a minified/single-line script
  into one statement per line and indents by brace depth. Not a real
  parser/AST formatter — good enough to make a fetched `.js` file
  reviewable, which is literally what WSTG-INFO-05 calls for
  ("Gather JavaScript files and review the JS code").
- `frontend/src/components/PrettyOutput.tsx`: added `renderJsLine`
  (keywords/strings/comments/numbers/punctuation each colored, same
  token-regex-per-line approach as the existing JSON/HTML renderers)
  and widened the tag/attribute-name character classes in the markup
  renderer (now `[\w:.-]`) so namespaced XML tags like `<xhtml:link>`
  and `xmlns:xhtml=` highlight correctly, not just plain HTML tags.
  Renamed `renderHtmlLine` → `renderMarkupLine` since it's now shared
  by both "html" and "xml" kinds via a `RENDERERS` lookup table.
- Python/TypeScript were considered and **not** added: this app's tool
  output realistically never contains raw Python source (no wrapped
  tool emits it), and TypeScript is never served over HTTP as `.ts` —
  browsers/servers only ever deliver compiled JS, so a `curl`/`wget`
  fetch of "TypeScript" is indistinguishable from plain JavaScript at
  the network level. Both would be speculative additions with no real
  trigger in this app, unlike JSON/HTML/XML/JS which all come from
  genuine curl/wget response bodies.

**Verified:**
- `npx tsc --noEmit`, `eslint` clean.
- Standalone logic test (5 cases): sitemap.xml-shaped output with
  `Content-Type: application/xml` → correctly detected as `xml`; a
  `.js` file with `Content-Type: application/javascript` → correctly
  detected as `javascript`; bare JS with no header block (multiple
  signals) → still detected via sniffing; a plain scan log →
  correctly returns no match; a log line that happens to contain the
  word "function" once → correctly does **not** false-positive as JS
  (confirms the "≥2 signals" guard actually holds).
- Full browser E2E against a real engagement: ran `curl` for real
  against `https://httpbin.org/xml` — confirmed "Pretty XML" appears
  and renders the declaration/comments/tags/attributes correctly
  colored and indented. Ran `curl` again against a real, genuinely
  minified file, `https://code.jquery.com/jquery-3.7.1.slim.min.js`
  (detected via its real `Content-Type: application/javascript`
  header) — confirmed "Pretty JS" appears and reflows the single
  massive minified line into indented, syntax-highlighted statements.
  Zero console errors in both runs. Test engagement deleted after use.

---

## 2026-08-27 (28) — Raw / Pretty JSON / Pretty HTML toggle on tool output

**Done (user request: "on the result can you add button can show raw
logs, and prettier format such as prettier json, html, ..."):**
- New `frontend/src/lib/prettyFormat.ts` — zero-dependency detector +
  formatter. Splits an HTTP-response-shaped output (curl -i / wget -S:
  header block, blank line, body — detected by the first line matching
  `HTTP/...` or a `Header: value` pattern) into headers + body, then
  tries the body as JSON (`JSON.parse` + `JSON.stringify(..., null,
  2)`) and falls back to a minimal HTML indenter (reflows a blob onto
  one tag per line, indents by nesting depth via open/close tracking —
  not a real parser, just enough to make a dumped page readable).
  Returns `null` (no toggle shown) when the output is neither — most
  tool output is plain text logs, and forcing a formatter on those
  would be noise, not a feature.
- New `frontend/src/components/PrettyOutput.tsx` — regex-token
  syntax highlighter for the two supported kinds (JSON: keys/strings/
  numbers/booleans/punctuation each colored; HTML: tag names/attribute
  names/attribute values/comments each colored), matching the existing
  `HighlightedOutput.tsx`'s token-regex-per-line pattern rather than
  introducing a different approach.
- `frontend/src/components/ItemDetail.tsx`: the Tool Output panel's
  existing Raw/Tree toggle (for ffuf/gobuster/katana discovered-path
  results) is now a three-way Raw/Tree/Pretty toggle — "Pretty" only
  appears when `detectAndFormat()` actually finds JSON or HTML in the
  active tab's output, labeled with which one ("Pretty JSON" / "Pretty
  HTML") so it's clear what's about to render. Falls back to Raw
  whenever the currently active tab has neither, same guard the
  existing Tree toggle already had.

**Verified:**
- `npx tsc --noEmit`, `eslint` clean on all three files.
- Standalone logic test (4 cases): curl -i output with a JSON body →
  correctly split headers from body and pretty-printed just the body;
  plain nmap output → correctly returns `null` (no false-positive
  toggle); curl -i output with an HTML body → detected as HTML; bare
  JSON with no header block → still detected and formatted.
- Full browser E2E against a real engagement: ran `curl` for real
  against `https://httpbin.org/json`, confirmed the "Pretty JSON"
  toggle appears and renders syntax-highlighted, correctly-indented
  JSON (keys teal, strings amber, numbers highlighted) with the HTTP
  headers left as plain text above it. Ran `curl` again against
  `https://httpbin.org/html`, confirmed "Pretty HTML" appears and
  renders properly nested/indented, syntax-highlighted markup (tag
  names bold teal). Zero console errors both times. Test engagement
  deleted after use.

**Next steps for the next agent:**
1. Only wired into `ItemDetail.tsx`'s persisted Tool Output panel (the
   "result" a tester reviews after a run finishes) — deliberately not
   added to `RunToolDialog.tsx`'s live-streaming output panel, since
   reformatting a JSON/HTML body mid-stream (before the closing
   brace/tag has even arrived) doesn't make sense for a formatter that
   needs the whole body to parse. If that's ever wanted, it would need
   to wait for the "done" message before attempting it, not run on
   every streamed line.
2. The HTML indenter is intentionally minimal (regex-based reflow +
   depth counting, not a real HTML/DOM parser) — it'll misindent on
   genuinely malformed markup (unclosed tags, tags split across what
   it thinks are boundaries) since it doesn't validate structure, only
   assumes it's roughly well-formed. Good enough for "make a wall of
   minified HTML readable," not a substitute for a real parser if that
   ever becomes necessary.

---

## 2026-08-27 (27) — Audit: Information Gathering (INFO-01…10) against the real WSTG v4.2 methodology

**Done (user request: pasted the full official WSTG-INFO-03 methodology
page and asked whether "each owasp wstg, each only information
gathering 10 checklist that the tools complete... and the result can
following the objectives on that checklist"):**
- Pulled the actual official methodology for all 10 Information
  Gathering items directly from the OWASP source (`gh api` to list the
  real files in `OWASP/www-project-web-security-testing-guide`, then
  fetched each `.md`'s real "Test Objectives"/"How to Test"/"Tools"
  sections) and compared them one by one against `oculus/checklist.py`'s
  current `tools=[...]`/description for INFO-01 through INFO-10, rather
  than going from memory or assumption.
- **Real finding, not previously known:** WSTG v4.2 officially **merged
  WSTG-INFO-09 into WSTG-INFO-08** — INFO-09's real page is now just a
  one-line redirect stub ("This content has been merged into...").
  Didn't delete the item (would renumber/break existing 97-item
  engagements' saved data) — added an honest note to its description
  citing this, so a tester isn't confused about why INFO-08 and INFO-09
  overlap so much.
- **Real gap, fixed:** WSTG-INFO-05 ("Review Webpage Content for
  Information Leakage") explicitly calls for finding hardcoded API
  keys/tokens/credentials in HTML/JS — `nuclei` wasn't mapped to this
  item at all, despite already being wrapped and despite having a
  template category built exactly for this. Confirmed real coverage
  before adding it (not assumed): `nuclei -tl -tags exposure,token`
  actually lists real templates from the installed template set.
  Added `nuclei` to INFO-05's tools with a `NUCLEI_TAGS` override for
  `exposure,token` (same swap-by-item-id pattern as every other
  `NUCLEI_TAGS` entry).
- The other 8 items (INFO-01/02/03/04/06/07/08/10) were checked
  against their real "How to Test"/"Tools" sections and found to
  already match reasonably well — e.g. INFO-01's real methodology is
  entirely manual search-engine dorking (Google/Shodan operators),
  which no CLI tool can automate; the existing `subfinder`/`amass`
  mapping already carries an honest disclaimer about this rather than
  overclaiming coverage. No changes made where the existing mapping
  was already a reasonable, honest fit — this was a targeted fix for
  the two real gaps found, not a wholesale rewrite.

**Verified:**
- `python3 -c "from oculus.checklist import build_checklist; ..."` —
  import-time tool-reference validator (including the `NUCLEI_TAGS`
  cross-check) passes clean with the new entry.
- Hit the real running backend: `GET /api/tools/nuclei/command?...
  item_id=WSTG-INFO-05` returns `-tags exposure,token` in the preview.
- Confirmed via direct `Orchestrator.run_tool()` call that the **real
  executed** command (not just the preview) carries the same tags —
  this reuses the `apply_tool_overrides()` fix from entry 23, so the
  override actually reaches execution rather than only showing up
  cosmetically.
- `npx tsc --noEmit` clean (no frontend changes — descriptions/tools
  render from the API dynamically).

**Next steps for the next agent:**
1. Only Information Gathering (INFO-01…10) was audited this round —
   the same real-methodology-vs-implementation comparison hasn't been
   done for the other 11 WSTG sections (CONF, IDNT, ATHN, ATHZ, SESS,
   INPV, ERRH, CRYP, BUSL, CLNT, APIT) in this pass. Worth repeating
   the same process (`gh api` to list real files, fetch, diff against
   `checklist.py`) since INFO turned up two genuine, previously-unknown
   gaps despite already having gone through multiple "audit tool
   correctness" passes earlier in this project's history — there may
   be more like the INFO-09 merge or the INFO-05 nuclei gap elsewhere.
2. Not pursued (out of scope for a "fix real gaps" pass, would be a
   bigger feature): WSTG-INFO-03's real methodology covers multiple
   metafiles (robots.txt, sitemap.xml, security.txt, humans.txt,
   `.well-known/` variants) but the `wget` override only fetches
   `/robots.txt` by default (one path per run, by design — see
   `WGET_PATH_SUFFIX`). ffuf's paired "metafiles" wordlist category
   fuzzes for the others, so coverage exists, just split across two
   tools/runs rather than one command hitting all of them.

---

## 2026-08-27 (26) — Dashboard card layout + logo on the landing page

**Done (user request: "At the dashboard can you change the layout to
cards component, and on landing can you add the logo"):**
- `frontend/src/app/engagements/page.tsx` (the "Dashboard" nav link,
  the engagement list): replaced the `<Table>` row list with a
  responsive card grid (1 col mobile, 2 tablet, 3 desktop) — new
  `EngagementCard` component per engagement showing name, ID, target,
  progress bar, findings count + severity chips (crit/high), created
  date, and a delete icon; whole card is a `Link` to the engagement.
  Widened the page from `maxWidth="md"` to `"lg"` so 3 columns have
  room. Removed the now-unused `Table`/`TableBody`/`TableCell`/
  `TableHead`/`TableRow` imports.
  - Also fixed a stray, badly-indented `<Box component="img"
    src="/logo.svg">` insertion already sitting in this file's header
    (found while reading the file — looked like a leftover
    linter/partial-edit artifact, not wired into any layout) by
    properly integrating it next to the "Engagements" title, matching
    the treatment already used in `NavBar.tsx`.
  - Found and deleted a stray test engagement (`__amasstest`,
    `356b0583`) left over from this session's earlier amass-v5
    debugging — a real cleanup miss, not part of this feature.
- `frontend/src/app/page.tsx` (the landing page): added the same
  `logo.svg` above the `[ OCULUS ]` bracket text, sized larger (88px)
  with a two-layer teal glow (`drop-shadow`) matching the big
  "OCULUS" heading's own glow treatment right below it, in its own
  `FadeIn` so it animates in first.

**Verified:**
- `npx tsc --noEmit` clean. `eslint` clean on both edited files (two
  pre-existing warnings in `page.tsx` — unused `Paper` import and
  `FEATURES` array — predate this change, tied to an already-commented-
  out features section; left alone, out of scope).
- `next build` succeeds.
- Full browser E2E: landing page screenshot confirms the logo renders
  correctly above the wordmark with visible glow. Dashboard screenshot
  confirms the card grid renders correctly with real engagement data
  (4 real engagements after cleaning up the stray test one). Confirmed
  by direct interaction: hovering a card shows the teal glow/border
  (screenshot-verified), clicking a card navigates to
  `/engagements/<id>` correctly, and the existing search-by-name/target
  filter still works against the new card grid. Zero console errors
  throughout.

**Next steps for the next agent:**
1. The commented-out `FEATURES` grid on the landing page (four feature
   cards — OWASP WSTG, tools, live streaming, CVSS reporting) predates
   this session and is still disabled; its copy is also stale (says
   "20 structured Information Gathering & Configuration Management
   items" and "16 integrated tools" — both long out of date, 97 items
   and 23 tools now). Not touched here since it's off and out of scope,
   but worth either updating and re-enabling or deleting outright next
   time someone's in this file.

---

## 2026-08-27 (25) — Background tool runs: persisted status, duplicate-run guard, live sidebar

**Done (user request: "when running tools then click close it not
running that tools, can you implement it can running behind
background and when back to that checklists it can show progress
running tools status at checklists bar also"):**
- Root-caused first, not assumed: confirmed directly (raw WebSocket
  client, closing mid-scan) that a tool run **already** keeps executing
  server-side after the Run Tool dialog/WebSocket is closed — the
  worker is a daemon thread independent of the WS connection. The real
  bug was that nothing *showed* this: `item.status` only ever flipped
  to `RUNNING` in memory, never persisted to disk until the run
  finished, so a closed dialog left the checklist looking exactly like
  nothing had happened, and reopening the dialog to run again could
  silently start a **second overlapping run** racing the first on the
  same `tool_outputs`/findings.
- `backend/ws.py`: persists `status=RUNNING` (+ `started_at`) to disk
  immediately, before the subprocess even starts — not just at the end
  — so any other request/page load sees it right away. Added a
  duplicate-run guard: a second start request for an item already
  `RUNNING` is rejected with a clear message instead of silently racing.
- `frontend/src/components/RunToolDialog.tsx`: new `onStart` callback,
  fired on the first real "line" back from the server (proof the
  backend accepted the run, not just requested it) — lets the parent
  optimistically flip local state to "running" immediately, since the
  backend's own status write alone doesn't reach an already-open
  browser tab's React state without either this or a refetch. Also
  shows an inline warning + disables Run when opened for an item that's
  already running in the background (from a previous dialog session),
  instead of only surfacing the backend's rejection after the fact.
- `frontend/src/components/Checklist.tsx`: the sidebar's per-item status
  icon now pulses (framer-motion) for `status === "running"` — it
  already rendered a distinct icon/color for that status, just
  statically, easy to miss.
- `frontend/src/components/ItemDetail.tsx`: **Run tool** button becomes
  an amber "Running in background…" pill (still clickable — opens the
  dialog's new warning state) while the item is running.
- `frontend/src/app/engagements/[id]/page.tsx`: polls (3s) and re-fetches
  the engagement while any item is `running`, so status flips from
  running → done on its own if the tester is just sitting on the page
  (covers e.g. two tabs, or the item that was optimistically flagged
  running by `onStart` eventually needing the real final state). Added
  an "N running in background" pulsing header indicator alongside the
  progress/severity bars.

**Verified:**
- Backend, directly: opened a raw WebSocket, started a real `nmap` scan
  on `WSTG-CONF-01`/`scanme.nmap.org` (an nmap.org-authorized scan
  target), read 2 lines, closed the connection — confirmed via polling
  the REST API over the next ~20s that the item transitioned to `done`
  with the real nmap output saved, proving the backend was never the
  actual problem.
  - Confirmed `status=running` is visible via a **separate** connection
    while a run is genuinely still in progress (not just after the
    fact).
  - Confirmed a duplicate start attempt on the same item while the
    first is still running gets rejected with the new error message,
    not silently accepted.
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser E2E end-to-end: started a real nmap run, closed the
  dialog after 2.5s — confirmed the header immediately showed "1
  running in background" and the item's button changed to "Running in
  background…" **without any navigation or manual refresh** (this only
  passed after adding the `onStart` optimistic-update fix — the first
  pass caught exactly the staleness bug being fixed). Navigated away
  and back — confirmed the running state persisted across a fresh page
  load (the actual backend persistence fix). Reopened the Run Tool
  dialog on the still-running item — confirmed the new warning banner
  and disabled Run button. Left the page open and polled — confirmed it
  auto-updated to "Done" with the real finding, with zero manual
  interaction. Zero console errors throughout. Test engagement deleted
  after use.

**Next steps for the next agent:**
1. The Run Tool dialog doesn't reconnect to a run's *live* output if
   reopened while it's still going (it shows the warning banner, not a
   resumed stream) — the backend has no run-registry/pub-sub a new
   WebSocket could subscribe to. Worth building if testers want to
   watch a long scan's progress after closing and reopening the dialog,
   not just know that it's running.
2. Polling is timer-based (3s), not push-based — fine for this app's
   scale (one tester, one engagement open at a time) but would need a
   real pub/sub (or Server-Sent Events) to scale to multiple
   simultaneous viewers of the same engagement.

---

## 2026-08-27 (23) — curl/wget as basic tools + fixed a real "recommendation never executes" bug

**Done (user request: "can you add basic tools or basic command bash
such wget script,, curl scripts or anything each wstg"):**
- New `oculus/tools/curl_tool.py` / `wget_tool.py` — lightweight,
  almost-always-already-installed alternatives to the heavier wrappers,
  for a quick manual header/existence check. Mapped onto ~18 checklist
  items chosen for genuine fit, not padding: HTTP methods (`curl -X
  OPTIONS`), CORS/Host-header spoofing (`curl -H`), RIA cross-domain
  policy and robots.txt/`.git/HEAD` existence (`wget`), cookie
  attributes, error handling, clickjacking headers, and a few more —
  see `CURL_ARGS`/`CURL_PATH_SUFFIX`/`WGET_PATH_SUFFIX` in
  `oculus/checklist.py`. Deliberately skipped items where the generic
  command wouldn't add real value over what nmap/testssl/nuclei already
  do (e.g. `WSTG-CRYP-01`, TLS auditing — testssl already owns that).
- **Found and fixed a real pre-existing bug while wiring in the
  per-item overrides**: `NUCLEI_TAGS`/`WORDLIST_CATEGORY` (and now
  `CURL_ARGS`) only ever affected the *previewed* command text in the
  Run Tool dialog — the actual subprocess that runs on an unedited
  "Run" click ignored the checklist item entirely and used the tool's
  plain generic default. Root cause: `item_id` never reached
  `Orchestrator.run_tool()`'s real-execution path, only the preview
  endpoint. Confirmed directly: `nuclei` on the SSRF checklist item
  was really running its generic misconfig scan, not SSRF templates,
  every time — unless the tester happened to edit the command box.
  Fixed by extracting the swap logic into one shared
  `oculus.checklist.apply_tool_overrides()`, called from both the
  preview endpoint and `Orchestrator.run_tool()`. `BaseTool.run()`
  gained a `default_command` parameter, distinct from the existing
  `override_command` (tester-edited, always-real) — `default_command`
  is the item-aware default and still respects the simulated-fallback-
  when-not-installed behavior, unlike `override_command`.

**Verified:**
- Import-time `_validate_tool_references()` (extended to also check
  `CURL_ARGS`/`CURL_PATH_SUFFIX`/`WGET_PATH_SUFFIX`) passes clean.
- Direct `Orchestrator.run_tool()` calls confirmed the *real executed*
  command (not just the preview) now reflects the override: `curl` on
  `WSTG-CONF-06` really runs `-X OPTIONS`; `nuclei` on `WSTG-INPV-19`
  really runs `-tags ssrf` — both previously silent regressions now
  fixed. Confirmed the simulated-fallback path still works and now
  shows the *item-aware* command even in simulated mode (nice side
  effect, not just a fix).
- Full browser E2E: opened WSTG-CONF-06, selected curl, clicked Run
  *without editing anything* — confirmed a real HTTP/2 405 response
  came back (the correct result for an actual `OPTIONS` request against
  that real target), proving the override reached the real subprocess
  through the actual UI, not just a unit test.
- `npx tsc --noEmit` clean (no frontend changes needed — same reasoning
  as prior tool additions).
- Full Docker build (after the logo/favicon work below interrupted this
  entry — closed the loop once that was done): **passed clean**. Ran
  the built image directly and confirmed `curl`/`wget` both resolve and
  report available (`apt install curl wget` did the job — not
  guaranteed present in the `python:3.11-slim-bookworm` base, and
  wasn't), and confirmed a *real* override-applying run inside the
  container: `curl` on `WSTG-CONF-06` executed `-X OPTIONS` for real
  and got back an actual `HTTP/2 405` from the network — the
  Orchestrator fix above verified inside the shipped image, not just
  locally. Test image removed after use (`docker rmi`).

**Next steps for the next agent:**
1. `README.md`'s tool table/ASCII diagram and the Docker section's
   binary count/list are now stale again (still say counts from before
   this session's additions) — worth a dedicated pass rather than the
   spot-fixes made here under time pressure (a logo/favicon request
   interrupted this work mid-stream).

---

## 2026-08-27 (24) — Project logo + favicon

**Done (user request: "use this picture for logo on this project, and
change it to favicon also", attaching a teal eye/radar-scope image):**
- No tool in this environment can save a pasted conversation image
  straight to disk, so the image was recreated as a hand-authored SVG
  instead — actually the better outcome for a logo/favicon (vector,
  scales cleanly from 16px to any size, tiny file, no external asset
  dependency) rather than a worse one born of the limitation. Matched
  its exact motif (eye lens, iris/pupil rings, radar arcs above/below,
  crosshair with corner tick marks, a radar-sweep beam) and its color
  in the app's own theme teal (`#5eead4`, `GREEN` in
  `frontend/src/lib/theme.ts`) rather than eyeballing a color match —
  so it now reads as this app's own mark, not a copy of an external one.
  Source: `frontend/public/logo.svg`.
- Wired into the Next.js App Router's icon conventions: `frontend/src/
  app/icon.svg` (modern browsers, SVG favicon), `favicon.ico` (legacy
  fallback, generated as a real multi-resolution 16/32/48px `.ico` via
  Pillow — rendered from the SVG via a throwaway Playwright HTML-wrapper
  script since neither `rsvg-convert` nor ImageMagick's `convert` exist
  on this machine, then packed into one `.ico` with `PIL.Image.save
  (format="ICO", sizes=[...])`), and `apple-icon.png` (180×180, iOS
  home-screen icon). All three are Next.js special-file names — no
  metadata config needed, confirmed via the generated `<link rel=
  icon/apple-touch-icon>` tags on a real page load.
- Added the same SVG next to the `[ OCULUS ]` wordmark in
  `frontend/src/components/NavBar.tsx` (22px, subtle teal drop-shadow
  matching the app's terminal-glow aesthetic) and at the top of
  `README.md`.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean; build output
  confirms Next.js registered `/icon.svg` and `/apple-icon.png` as
  routes.
- Full browser E2E: `GET /icon.svg`, `/favicon.ico`, `/apple-icon.png`
  all return 200; the page's actual `<link rel="icon">` /
  `apple-touch-icon` tags point at the right generated URLs. Screenshot
  of the nav bar confirms the logo renders correctly next to the
  wordmark. Zero console errors. Throwaway render script and PNG
  intermediates deleted after use.

**Next steps for the next agent:**
1. If the user ever provides the source image as an actual file (not a
   pasted conversation attachment), it could replace `logo.svg` with a
   closer pixel-for-pixel trace, or be used to derive an even more
   detailed icon — the current version is a faithful but hand-authored
   recreation of the described image, not a 1:1 trace of the original
   pixels.

---

## 2026-08-27 (22) — Fix: cryptic "Amass engine did not respond" error

**Done (user report: "at install command can you add label OS for tell
user should use what script to install" [entry 21] was followed by the
user hitting: "The Amass engine did not respond: the Amass engine did
not respond within the timeout period"):**
- Root-caused for real, not guessed: OWASP Amass rewrote its CLI
  between v4 and v5 into a client/server split. `amass enum` (and even
  `amass enum -h`!) now unconditionally tries to reach a separately
  running `amass engine` process (default `http://127.0.0.1:4000`) and
  fails with exactly this message if it can't — this is **not** a slow
  scan timing out, it fails almost immediately (confirmed: `amass -h`
  alone reproduces it). Confirmed via `amass -version` this dev machine
  has v5.1.1 (current `brew`/`apt` release) while this app's own
  Dockerfile installs v4 (`go install .../amass/v4/...@master` — the
  `/v4/` module path pins the old single-shot CLI), so Docker users
  never hit this but a local `brew install amass` user always will.
  Also found the specific reason no engine could ever be reached on
  this machine: an unrelated process already has port 4000 bound
  (`lsof -i :4000`) — confirmed, left untouched (not oculus's to kill).
- `oculus/tools/base.py`: new `BaseTool.postprocess_output(output,
  exit_code) -> str` hook, called in `run()` after a *real* (non-
  simulated) run, default no-op. Deliberately not a blanket "clean up
  every tool's error output" mechanism — just an extension point for
  the rare case where a tool's real output is accurate but genuinely
  inscrutable. Also pushes any appended lines through the existing
  `on_line` live-stream callback (checked: `output != raw_output`) so a
  tester watching the run live sees the note too, not just on replay.
- `oculus/tools/amass_tool.py`: overrides it — detects `"did not
  respond"` + `"engine"` in real output and appends a clear explanation
  + three concrete fixes (start `amass engine` yourself; install v4 via
  `go install .../amass/v4/...@master`, added as a new `install_hints`
  entry; or just use `subfinder`, already paired on the same checklist
  item, which needs no engine). `description` also gained a short
  heads-up about this so it's visible before a tester even runs it.

**Verified:**
- Reproduced the exact real error directly against real amass v5 on
  this machine (`AmassTool(...).run(fast=True)`) — confirmed the note
  gets appended to `ToolResult.output` and that it also arrives via the
  live `on_line` stream (not just the final saved result).
- Full browser E2E against a real (temporary) engagement: ran amass for
  real via the actual Run Tool dialog, confirmed the guide box shows
  the new description heads-up before running, confirmed the note is
  present in the saved tool output afterward (`/api/engagements/.../
  ...` dump). One run took longer than expected to finish (amass v5
  apparently holds some local lock/state across back-to-back
  invocations against the same target) but it did complete correctly
  and save the right output — a real quirk of amass v5 itself, not a
  regression in `run_tool()`'s subprocess-timeout enforcement (already
  covered by the existing 90s/660s ceiling either way). Test engagement
  deleted after use.
- `python3 -c "from oculus.checklist import build_checklist; ..."` —
  import-time tool-reference validator still passes with the new
  `install_hints` entry.

**Next steps for the next agent:**
1. If amass v5 support is ever worth doing properly (auto-managing a
   background `amass engine` process for the tool's lifetime, picking a
   free port, tearing it down after), that's a real architecture change
   — `BaseTool.run()` currently assumes one subprocess per run. Not
   attempted here; the fix in this entry makes the *failure* clear
   rather than attempting to make v5 actually work standalone.
2. `postprocess_output()` is a new, currently single-use extension
   point — fine to leave unused elsewhere, but worth remembering it
   exists if another tool's real (not simulated) error output is ever
   reported as similarly confusing.

---

## 2026-08-27 (21) — OS label on each install-command chip

**Done (user request: "at install command can you add label OS for
tell user should use what script to install"):**
- `InstallHints.tsx` (the not-installed-tool warning shown in the Run
  Tool dialog, the Tools catalog, and the Help dialog — one shared
  component) now shows a second small chip next to each package-manager
  chip (`brew`/`apt`/`go`/`pip`/`gem`/`git`/...) naming the OS(es) that
  command actually targets — `brew` → macOS, `apt` → "Linux (Debian/
  Ubuntu/Kali)", `go`/`pip`/`gem`/`git` → macOS/Linux, anything
  unrecognized → "Cross-platform" rather than guessing wrong
  (`MGR_OS` lookup table). Fixes a real ambiguity: "go" or "pip" alone
  doesn't tell a tester whether it'll work on their machine the way
  "brew"/"apt" obviously do.
- Restructured `CopyRow` to two lines (chips on top, command+copy
  button below) instead of cramming both chips into the same row as
  the command box — the original single-row layout squeezed the
  command text down to a couple of visible characters in the Tools
  catalog's ~380px-wide cards.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser E2E: Tools catalog card for `commix` (not installed on
  this dev machine) shows "Linux (Debian/Ubuntu/Kali)" next to `apt`
  and "macOS/Linux" next to `git`, both fully visible with the command
  box keeping its full width. Same component re-checked inside the
  wider Run Tool dialog (selecting `commix` on a fresh engagement's
  WSTG-INPV-12) — renders correctly there too. Zero console errors.
  Test engagement deleted after use.

---

## 2026-08-27 (20) — Three new tools: naabu, dalfox, commix

**Done (user request: "can you implement by add other tools for pentest
more complete"):**
- Audited every checklist item's `tools=[...]` mapping (script dump of
  all 97 items) to find genuine gaps rather than guessing — the three
  additions below each fill a specific one instead of duplicating a
  tool the checklist already had:
  - **naabu** (`oculus/tools/naabu_tool.py`) — ProjectDiscovery's fast
    SYN-based port scanner. Mapped alongside `nmap` on WSTG-CONF-01
    (Network Infrastructure Configuration) as a fast pre-scan pass;
    nmap remains the tool for banner/version detail on whatever naabu
    finds open. Fast mode: top 100 ports. Full: all 65535 (`-p -`).
  - **dalfox** (`oculus/tools/dalfox_tool.py`) — reflected/DOM XSS
    fuzzer that confirms each hit in a real browser context instead of
    just flagging a raw string reflection (fewer false positives than
    nuclei's generic XSS templates). Mapped alongside `nuclei` on
    WSTG-INPV-01 (Reflected XSS) only — deliberately **not** added to
    WSTG-INPV-02 (Stored XSS), since dalfox's URL-fuzzing approach
    can't do the submit-then-revisit workflow stored XSS actually needs.
  - **commix** (`oculus/tools/commix_tool.py`) — automated OS command
    injection tester (parameter + crawled-form fuzzing, `--batch` so it
    never blocks on a prompt). Mapped alongside `nuclei` on
    WSTG-INPV-12 (Command Injection).
- New `findings_extractor.py` extractors for all three: `extract_naabu`
  (flags exposure of a curated list of sensitive ports — DB/cache/
  Docker-API/RDP/VNC/Telnet/FTP — not every open port, same
  "only the interesting ones" pattern as `_flag_interesting_paths` for
  ffuf/gobuster), `extract_dalfox` (parses its `[POC]`/`URL:`/`Param:`/
  `Type:` block), `extract_commix` (parses its "parameter is vulnerable
  via the ... technique" confirmation line). Two new `COMMON_VECTORS`
  entries in `scoring.py`: `command_injection` (10.0/CRITICAL) and
  `reflected_xss` (6.1/MEDIUM — the standard real-world CVSS for a
  typical reflected XSS, not guessed).
- `Dockerfile`: `naabu` and `dalfox` are Go tools, added to the
  existing `go install` batch in the build stage (`naabu` additionally
  needs `libpcap-dev` at build time for its SYN-scan mode — added to
  that stage only, not the runtime image). `commix` isn't packaged for
  Debian, so it's git-cloned like `nikto`/`testssl.sh` with a tiny
  `/usr/local/bin/commix` shell shim that execs `commix.py` — same
  pattern as those two, not a new one.
- 21 tools now registered (was 18).

**Verified:**
- Import-time `_validate_tool_references()` guard (catches a checklist
  item pointing at an unregistered tool name) passes clean.
- Ran each new tool's `build_command()` (fast + full) and
  `mock_output()` through its extractor directly: naabu flags MySQL +
  Redis from its mock port list, dalfox extracts both mock XSS POCs at
  the correct CVSS-computed MEDIUM severity, commix extracts its mock
  command-injection confirmation at CRITICAL. All correct.
- Hit the real running backend (`/api/tools`, `/api/tools/{name}/command`)
  — all three appear, correct default command per tool, `available:
  false` (accurate — none installed on this dev machine).
- Confirmed via a **freshly created** engagement (not an old one) that
  WSTG-CONF-01/INPV-01/INPV-12 now default to naabu/dalfox/commix
  respectively in the Run Tool dialog, and all three show correctly in
  the Tools catalog (logo, description, example, install hints — both
  `apt` and `git` hints render for commix). Confirmed via a **pre-existing**
  engagement that its checklist items correctly keep their old tool
  list — checklist items snapshot `build_checklist()` at creation time
  and never resync, so this is expected, not a regression. Zero console
  errors. Test engagement deleted after use.
- `npx tsc --noEmit` clean. The only frontend change needed was adding
  3 entries to `frontend/src/lib/toolLogos.ts` (distinct badge colors —
  the Tools catalog/Run Tool dialog already render whatever `/api/tools`
  returns, so they picked up the new tools with no other UI changes;
  without the new entries they'd have shown a plain gray fallback badge).
- Full Docker build of the image with all three new tools included —
  **passed clean**. Ran the built image directly (`docker run --rm
  --entrypoint sh oculus:tooltest -c "..."`) and confirmed `naabu
  -version`, `dalfox version`, and `commix --version` all execute for
  real, and `BaseTool.is_available()` returns `True` for all three from
  inside the container. Test image removed after verification
  (`docker rmi`). `libpcap-dev` in the Go build stage was in fact needed
  for naabu's build to succeed with SYN-scan support.

**Next steps for the next agent:**
1. Real-machine verification of the new tools' actual output format
   (as opposed to the hand-authored mock output) hasn't happened — the
   extractors are built against documented/typical output shapes for
   each tool, not a captured real run. Worth a real run against a
   deliberately vulnerable target (DVWA, WebGoat) to confirm the regexes
   actually match.
2. Other real gaps noticed during the audit but not filled this round
   (all currently `tools=[]`, correctly manual-only per WSTG, or a
   deliberate scope call — not oversights): WSTG-BUSL-* (business logic
   flaws — inherently un-automatable), WSTG-SESS-03/06/07/08 (session
   fixation/CSRF/hijacking/timeout — mostly workflow-driven), and a few
   WSTG-CLNT items. A JWT-specific tool (e.g. jwt_tool) for
   WSTG-SESS-05's token-weakness testing was considered and deferred —
   it needs an actual captured token as input, not just a target URL,
   which doesn't fit this app's "run a tool against a target" model
   without more plumbing (a way to feed it a token from a previous
   tool's output).

---

## 2026-08-25 (19) — Help button on the item detail page itself, next to Run tool

**Done (user request: "add help button next from run tool button for
display option each tools"):**
- Entry 18 (below) put a **Help** button inside the *Run Tool dialog*,
  scoped to whichever single tool was currently selected in the
  dropdown. This adds a *second* **Help** button directly on the
  checklist item page, right next to the **Run tool** button itself —
  so a tester can see what every tool mapped to this test does, and
  each one's full real `--help` output, *before* opening Run Tool and
  picking one.
- New `frontend/src/components/ItemToolsHelpDialog.tsx`: lists this
  item's tools (`item.tools`, filtered from `allTools` the same way
  `RunToolDialog` already does) as cards — logo, install status,
  description — each with an **Options** button. Clicking one opens
  the existing `ToolHelpDialog` (entry 18) stacked on top, showing that
  tool's real `--help` output. No new backend endpoint needed — reuses
  `GET /api/tools/{tool_name}/help` entirely.
- `ItemDetail.tsx`: added the **Help** button next to **Run tool**,
  shown under the same `hasRunnableTools` condition (hidden for items
  with no tools mapped, same as Run tool itself).

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser E2E against a real engagement (Snoopbee Lab3): opened
  WSTG-INFO-02, confirmed Help renders next to Run tool, clicked it,
  confirmed the dialog lists all three mapped tools (`httpx` installed,
  `nmap` installed, `whatweb` not installed) with correct badges;
  clicked httpx's Options, confirmed the nested dialog shows real
  `httpx -h` output stacked correctly over the tools list. Zero
  console errors. Screenshots visually confirmed.
- Rebuilt (`npm run build`) and restarted the `next start` process
  afterward — same stale-chunk gotcha as entry 18, now a known pattern:
  always restart `next start` after `npm run build` if it was already
  running.

**Next steps for the next agent:**
1. Same two tools now separately show help — the Run Tool dialog's
   internal Help button (entry 18, scoped to the currently-selected
   tool) and this page-level one (entry 19, scoped to all of the
   item's tools). Consider whether the internal one is still pulling
   its weight now that this exists, or whether it's redundant enough
   to drop in favor of just this one launched from inside Run Tool too.

---

## 2026-08-25 (18) — Real per-tool `--help` output, shown from the Run Tool dialog

**Done (user request: "add helping function near running button for
describe each options on the tools such as `nmap -help`"):**
- `BaseTool` (`oculus/tools/base.py`) gained `help_flag` (default `-h`)
  and `run_help()`, which shells out to the resolved binary with that
  flag and returns its raw stdout+stderr, exit code ignored (nikto and
  testssl.sh both exit non-zero on their own help flag by design).
  Overridden per tool where the real CLI doesn't take plain `-h`:
  `nikto` → `-Help`, `gowitness`/`wpscan`/`testssl.sh`/`whatweb` →
  `--help`, `sqlmap` → `-hh` (the extended/advanced option listing
  rather than the terse default).
- New backend endpoint `GET /api/tools/{tool_name}/help`, cached
  in-process via `functools.lru_cache` (help text can't change without
  reinstalling the binary, so there's no reason to re-run the subprocess
  on every dialog open). Returns `{"available": false, "text": ""}`
  without shelling out at all when the binary isn't on PATH — nothing
  to run.
- `list_tools()` now also returns each tool's `help_flag`, mirrored into
  the frontend's `ToolInfo` type.
- New `frontend/src/components/ToolHelpDialog.tsx`: shows the real
  `--help` text verbatim in a monospace scrollable panel, titled e.g.
  `nmap -h`, with the tool's logo. For a not-installed tool it falls
  back to the existing description/example/install-hints instead of
  trying to run anything.
- A **Help** button (outlined, `HelpOutlineIcon`) now sits directly next
  to **Run** in `RunToolDialog.tsx` — this is deliberately *not* a
  hand-maintained summary of each tool's flags (18 tools × however many
  flags each, drifting from whatever version is actually installed);
  it's the tool's own current `--help` output, guaranteed accurate
  because it comes straight from the binary being run.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Hit `/api/tools/{name}/help` directly for `nmap`, `nikto`, `testssl`,
  `wpscan`, `gobuster`, `ffuf`, `sqlmap` — each returned real, correctly
  flagged help text (confirmed the override tools actually used their
  overridden flag, not a generic `-h`).
- Full browser E2E against a real engagement (Snoopbee Lab3): opened
  Run Tool on WSTG-INFO-02, confirmed the Help button renders next to
  Run, clicked it, confirmed the dialog opens showing the selected
  tool's (`httpx`) real `-h` output rendered correctly with logo/title.
  Zero console errors.
- **Environment note, not a code bug:** mid-session, `npm run build`
  (run to typecheck this change) overwrote `.next` while the existing
  `next start` production server (PID still serving the old build) was
  running, so it started 500ing on every JS chunk and the app got stuck
  on "Loading engagement…". Not caused by this feature's code — fixed
  by restarting the `next start` process so it picked up the fresh
  build. Worth knowing if a future agent sees the same symptom after
  running `npm run build` against a live `next start` server.

**Next steps for the next agent:**
1. Help text isn't searchable/filterable within the dialog — for a tool
   like `nmap` or `sqlmap` with a very long help output, a future
   improvement could add a client-side filter box.
2. The Tools catalog (`ToolsCatalog.tsx`, entry 16 below) still shows
   only the curated one-line `example` command, not the full `--help`
   — could link out to this same dialog from there too, so "what are
   all of `nikto`'s flags" is answerable without first navigating into
   a checklist item.

---

## 2026-08-25 (17) — Keyboard shortcut: R opens Run Tool dialog

**Done (user request: "where helping function? add shortkey for run
script and write on frontend button for short key"):**
- The README already documented "Pressing `R` opens the Run Tool
  dialog" as a shortcut, but it was never actually wired up — this
  session implemented it for real. `ItemDetail.tsx` now has a
  `keydown` listener (mirroring the guard pattern `Checklist.tsx`'s
  existing ↑/↓ shortcut already uses) that opens the Run Tool dialog on
  `r`/`R`, skipped while focus is inside any `INPUT`/`TEXTAREA`/`SELECT`
  — including this item's own Notes textarea — so typing notes
  containing the letter "r" can never accidentally pop the dialog open.
  Also skipped when the item has no runnable tools.
- The **Run tool** button itself now visibly shows the shortcut: a
  small monospace `R` badge as its `endIcon`, so the hint is discoverable
  without reading the README.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser E2E against a real engagement (Snoopbee Lab3): confirmed
  the button renders with the "R" badge, confirmed the dialog is closed
  before any keypress, confirmed pressing `r` on the page opens it,
  confirmed closing it and then typing "r" inside the Notes textarea
  does *not* reopen it (guard works). Zero console errors. Screenshot
  of the button with its badge visually confirmed.

**Next steps for the next agent:**
1. No other documented-but-unverified shortcuts are currently known —
   worth a quick README sweep next time a "where's feature X" question
   comes up, since this is the second time a doc got ahead of the code.

---

## 2026-08-25 (16) — Tool logos, descriptions everywhere, and a Tools catalog

**Done (user request: "can you add each tools's logo and can you
implement description each option tools and show example to use or
help"):**
- `frontend/src/lib/toolLogos.ts`: a fixed 2-letter monogram + color per
  tool (18 entries), *not* real project logos/wordmarks — pulling in 18
  external brand image assets (network fetches at runtime, licensing/
  trademark questions, wildly inconsistent art styles across CLI
  security tools) wasn't worth it for a local single-user tool. A
  consistent, instantly-recognizable colored badge per tool, styled to
  match the app's own terminal theme, gets the same practical benefit
  (visually distinguishing tools at a glance) without any of that.
- New `frontend/src/components/ToolLogo.tsx`: renders that badge,
  dimmed when the tool isn't installed, tooltip shows the full name.
- New `frontend/src/components/ToolsCatalog.tsx`: a searchable reference
  dialog listing all 18 tools — logo, description, a copyable example
  command, install status, and (for a not-installed tool) the same
  `InstallHints` component the Run Tool dialog already uses. This is
  the "show example to use or help" part — a standalone reference, not
  tied to any specific checklist item, for "what does `X` do and how do
  I invoke it" independent of actually running anything. Opened via a
  new wrench icon in `NavBar.tsx`, next to Settings.
- `RunToolDialog.tsx`'s Tool dropdown: every option now shows its logo,
  description, and install status (previously: bare tool name, only the
  *selected* one got a description, shown separately below in the guide
  Alert). The guide Alert itself also gained the tool's logo as its icon
  for visual consistency with the dropdown and the new catalog.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser E2E: opened the Tools catalog from the nav bar, confirmed
  all 18 tool cards render with logo/description/example/install-status
  (including a live "not installed" card showing real install hints for
  a tool genuinely missing on this dev machine); confirmed the search
  box narrows correctly (typed "sql injection", got exactly the sqlmap
  card, no unrelated tools); confirmed the Run Tool dialog's Tool
  dropdown shows the same logo + description + install status per
  option. Zero console errors.

**Next steps for the next agent:**
1. No place currently shows a checklist item's *own* `tools` list as a
   set of logo badges outside the Run Tool dialog (e.g. on the item
   detail page itself, before opening Run Tool) — could be a nice
   at-a-glance addition if testers want to see which tools an item uses
   without opening the dialog first.
2. The monogram/color assignments in `toolLogos.ts` are arbitrary
   (chosen for visual distinctness, not derived from anything) — fine
   as an internal convention, but worth knowing if a tester ever asks
   "why is nuclei red" expecting it to mean something.

---

## 2026-08-25 (15) — Fix: duplicate findings in the report

**Done (user bug report: "some testing process it found the finding the
same then report it display duplicated finding"):**
- **Confirmed against real data before writing any fix**: dumped every
  finding across all 3 real engagements on this dev machine, grouped by
  (tool, title) — "Snoopbee Lab1" had "Server Version Disclosure:
  Apache/httpd" 4 times, "Snoopbee Lab3" had it 3 times. Root cause:
  findings are tracked per checklist item (correct — each item's own
  `run_tool()` genuinely re-derives findings from that run's output),
  but several checklist items now run the *same* tool (`nmap` alone is
  mapped to `WSTG-INFO-02`/`04`, `WSTG-CONF-01`/`06` since the WSTG
  coverage expansion two sessions ago) — running nmap from each of those
  4 items independently produces its own Finding object for the same
  real-world fact. `orchestrator.run_tool()` already dedupes *within* a
  single item/tool re-run (clears that tool's prior unverified findings
  before adding new ones) — there was just no dedup *across* items.
- Fixed at the report layer specifically (not the underlying data model
  — the per-item findings panel correctly keeps its own per-item list,
  since each item genuinely did detect it): new
  `oculus/report.py::_deduplicate_findings()` groups by `(tool,
  title)` — deliberately *not* also `evidence`, since the same real
  finding's evidence text can differ slightly between runs
  (`_grep_context()` in `findings_extractor.py` captures a few
  surrounding lines around the match, which shifts depending on exactly
  where the match lands in that run's output) — and returns one
  representative Finding per group plus every checklist item ID it
  recurred under (preferring an already-verified instance as the
  representative, if any of the duplicates were manually verified).
- Both `generate_markdown()` and `generate_docx()` now use this for
  their Detailed Findings section (now shows a "Checklist Items" row
  listing all of them, e.g. `WSTG-CONF-01, WSTG-CONF-06, WSTG-INFO-02,
  WSTG-INFO-04`, instead of 4 identical blocks) and their severity-count
  totals (previously `engagement.total_findings`/`findings_by_severity`,
  which count raw per-item findings — now `len(deduped)` /
  per-severity counts over the deduped list, so the Executive Summary's
  numbers match what Detailed Findings actually lists below it).
  Added a one-line note in the Markdown report explaining the dedup so
  a tester comparing it against the raw per-item "Findings" count in
  the Checklist Coverage table isn't confused by the two numbers
  legitimately differing.

**Verified:**
- Ran `_deduplicate_findings()` directly against the real "Snoopbee
  Lab1" engagement: 5 raw findings → 2 deduplicated, with the
  recurring one correctly listing all 4 checklist items.
- Generated the actual Markdown report and confirmed "Server Version
  Disclosure" now appears exactly once (was 4), with the "Checklist
  Items" field listing all 4 IDs; confirmed the Finding Severity
  Summary's Total now reads 2, matching the deduplicated list below it.
- Generated a real `.docx` via `generate_docx()` and confirmed it
  completes without error (37.7KB output).
- Curled the live backend's `/report/content` endpoint and confirmed
  the JSON response matches (1 occurrence, not 4).
- Full browser E2E against the same real engagement's View Report
  dialog: confirmed exactly 1 occurrence of the finding title, all 4
  checklist items listed, the dedup note visible, and the Total now
  reading 2. Zero console errors.

**Next steps for the next agent:**
1. Deliberately left `Engagement.total_findings`/`findings_by_severity`
   (in `oculus/models.py`) untouched — those still return raw,
   non-deduplicated counts, and feed the dashboard's `SeverityBar` on
   the engagement page (outside the report). The user's report was
   specifically about the report showing duplicates; the dashboard
   wasn't reported as wrong and per-item semantics there are arguably
   correct as-is (each item's own progress/findings count should
   reflect what that item detected). Worth revisiting only if the
   dashboard count itself gets reported as confusing.
2. The dedup key `(tool, title)` is intentionally coarse — two
   genuinely different findings from the same tool that happen to earn
   an identical auto-generated title (rare, since most extractor
   titles embed a specific value like a version number or path) would
   incorrectly merge. Not observed in the real data checked here, but
   worth knowing if a report ever seems to be missing a finding that
   should be listed separately.

---

## 2026-08-25 (14) — Report layout: collapsible sections, colored finding cards

**Done (user follow-up: "can you adjust the layout on report more read
easier" — the just-shipped View Report dialog rendered the whole
markdown string as one unbroken scroll, so reaching "Detailed Findings"
meant scrolling past a 97-row Checklist Coverage table first, and
finding blocks were plain text headers with no visual separation):**
- `ReportView.tsx`: `splitIntoSections()` splits the markdown string on
  its own top-level `## ` headers (Overview / Executive Summary /
  Checklist Coverage / Detailed Findings / Appendix — Raw Tool Output —
  matching `oculus/report.py`'s own structure exactly, no backend
  change needed) and renders each as a collapsible MUI `Accordion` with
  a size chip (row/sub-heading count) so a collapsed section still
  communicates its size without opening it.
- **Checklist Coverage** and **Appendix — Raw Tool Output** — the two
  genuinely long, skim-once sections — start collapsed.
  **Overview**/**Executive Summary**/**Detailed Findings** — what a
  tester actually opens this dialog to see — start expanded.
- Individual finding headings (`### 🔴 [CRITICAL] Title`) now render
  with a colored left border matching their severity emoji (parsed from
  the heading's own text via a small `textOf()` walker, no change to
  the markdown source), so findings are scannable as colored cards
  instead of identical plain headers.
- Long tables and evidence code blocks now cap at a fixed max-height
  with their own internal scroll (was: the whole dialog just kept
  growing), and table headers stick to the top of that scroll area.
- Dialog widened from `maxWidth="md"` to `"lg"` — tables (finding field
  table, checklist coverage) were cramped at the old width.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser E2E against the same real "Snoopbee Lab1" engagement:
  confirmed Checklist Coverage starts collapsed with a "20" count chip,
  clicking it expands the real 20-row table with a sticky header;
  confirmed Detailed Findings starts expanded showing a real finding's
  full field table/description/evidence/remediation; confirmed Appendix
  starts collapsed with a "56" chip and expands to real per-item tool
  output sections. Zero console errors.

**Next steps for the next agent:**
1. Section expand/collapse state resets every time the dialog reopens
   (no persistence) — reasonable default, but worth reconsidering if
   testers report wanting their expand choices remembered across opens.
2. `splitIntoSections()` assumes `report.py`'s exact `## ` section
   structure — if a future report.py change adds/renames/removes a
   top-level section, it'll just show up as its own new Accordion
   automatically (nothing hardcoded beyond the collapsed-by-default
   title set), so this should stay robust to most structural changes
   without a frontend update, but worth a quick check if that ever happens.

---

## 2026-08-25 (13) — In-app rendered report ("View Report")

**Done (user request: "can you implement the result like markdown on
interface can you show what we found at engagements" — the existing
"Markdown"/"Word" buttons only ever triggered a file download; there
was no way to see the report's content without downloading it first):**
- `backend/routers/reports.py`: new `GET /api/engagements/{id}/report/
  content` returning `{"content": "<markdown string>"}` — the exact
  same string `generate_markdown()` already produced for the file
  download, just returned as JSON instead of a `FileResponse`. No
  changes to `oculus/report.py` needed; it already returned the string
  directly regardless of whether `out_path` was given.
- New `frontend/src/components/ReportView.tsx`: a dialog that fetches
  that endpoint and renders it with `react-markdown` + `remark-gfm`
  (added as new dependencies — the report uses GFM tables throughout,
  which the base `react-markdown` doesn't parse without the plugin).
  Custom component overrides for every element the report actually
  uses (headings, tables, code blocks/spans, hr, links, lists) so it
  reads like the rest of the app's terminal theme instead of
  `react-markdown`'s browser-default styling — green heading accents,
  black bordered code blocks, bordered tables matching the existing
  Tool Output panel's look.
- New **View Report** button on the engagement page (next to the
  existing Markdown/Word download buttons, which are unchanged) opens
  it.

**Verified:**
- Curled the new endpoint directly against a real engagement, confirmed
  the returned JSON's `content` matches what the file-download endpoint
  produces.
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser E2E against the user's own real "Snoopbee Lab1"
  engagement (real findings, not synthetic test data): opened View
  Report, confirmed the header table, Finding Severity Summary table,
  and Checklist Coverage table all render correctly; scrolled to a real
  finding block and confirmed its own field table, description,
  evidence code block (real nmap/wafw00f output), and remediation text
  all render correctly. Zero console errors.

**Next steps for the next agent:**
1. The dialog re-fetches and regenerates the report on every open (no
   caching) — fine at this data scale, would need a caching layer if a
   report ever got large enough for `generate_markdown()` itself to be
   slow.
2. No in-dialog way to jump from a finding in the report straight to
   that checklist item's detail panel (the report is read-only/
   self-contained) — worth adding if this becomes a frequently-used
   view rather than an occasional "let me see everything at once" check.

---

## 2026-08-25 (12) — Auto-finding extraction: 7 → 13 of 18 tools

**Done (user picked this from two suggested next steps — extend
auto-finding extraction vs. add a test suite — after I recommended it
as the higher-leverage one since findings are the actual deliverable of
a pentest tool, and 11 of 18 tools' output was going unparsed):**
- 6 new extractors in `oculus/findings_extractor.py`, registered in
  `EXTRACTORS`:
  - `extract_sqlmap` — parses sqlmap's own real reporting format
    (`Parameter: NAME (METHOD)` blocks with `Type:`/`Payload:` lines,
    plus the `back-end DBMS is X` line) into one CRITICAL finding per
    confirmed injection point.
  - `extract_hydra` — parses hydra's real
    `[PORT][service] host: H  login: U  password: P` line format into
    one CRITICAL "weak/default credential" finding per pair found, plus
    a MEDIUM finding if hydra's own "no lockout observed" note appears.
  - `extract_wpscan` — parses the outdated-core version+count, every
    `[!] Title: ... / Fixed in: ... / Reference: ...` vulnerability
    block (core and plugin/theme alike), and enumerated usernames.
  - `extract_dnsx` — flags a dangling CNAME as HIGH (not the full
    confirmed-takeover CRITICAL — see below).
  - `extract_ffuf` / `extract_gobuster` — share a new
    `_flag_interesting_paths()` helper: both discover paths by brute
    force, so a `.env`/`.git`/`backup`/`config`/`admin`/... match in a
    discovered path means the same thing regardless of which of the two
    tools found it.
- New `COMMON_VECTORS` entries in `scoring.py`: `sql_injection`,
  `default_credentials`, `known_cve_vulnerability`,
  `sensitive_path_exposed`.
- **Bug caught and fixed during self-review, before it ever shipped**:
  `_make_finding()`'s existing behavior (used by every extractor
  already) is that a passed `cvss_vector` gets auto-scored and *that
  score's severity overrides whatever `severity=` was passed*. My first
  draft of `_flag_interesting_paths()` used one shared high-impact
  vector for every "interesting path" category — which flattened
  "Admin Interface Discovered" (meant to be LOW) and "Environment
  Configuration File Exposed" (meant to be HIGH) to the same computed
  severity. Fixed by only attaching the shared vector to the genuinely
  high-impact categories (`.env`, `.git`) and leaving the rest with no
  vector, so their explicit manual severity stands — same fix applied
  to `extract_wpscan` (per-vulnerability severity now sniffed from the
  vuln's own title, same approach `extract_nikto` already used,
  since WPScan's text report doesn't carry a CVSS score per entry — a
  fixed vector there was scoring a plugin XSS the same as a core RCE).
- **Also fixed**: `extract_dnsx`'s dangling-CNAME finding initially used
  the pre-existing (previously unused) `subdomain_takeover` vector,
  which scored it a full 10.0/CRITICAL — overstating certainty, since
  dnsx only flags this as *potential* (it can't confirm the target
  resource is actually deprovisioned). Changed to a manual HIGH
  severity with no CVSS vector instead.

**Verified:**
- Ran `extract_findings()` directly against each of the 6 new tools'
  real `mock_output()` text (not hand-written test fixtures — the
  actual strings `RunToolDialog` shows a tester) and inspected every
  resulting title/severity for correctness, iterating twice to catch
  the two severity bugs above before considering it done.
- Full real WebSocket round-trip against the live backend
  (`ws://.../items/{id}/run`) for `sqlmap`: confirmed a real run
  produces the same critical SQL-injection finding automatically,
  proving the wiring through `Orchestrator.run_tool()` →
  `extract_findings()` → the item's `findings` list works end-to-end,
  not just the extractor function in isolation.
- Also ran `hydra`/`ffuf` over real WebSocket calls against a
  nonexistent test domain — both are genuinely installed on this dev
  machine and correctly found nothing (real tool behavior against an
  unreachable target, not an extractor bug — confirmed by reading the
  actual captured raw output, which was empty/a real connection
  failure banner).
- Full browser E2E (throwaway Playwright script, deleted after use):
  injected a real sqlmap finding via the extractor, confirmed the
  engagement's progress bar correctly shows "1 critical" and the
  finding renders in the item detail panel. Zero console errors.
- `backend.main` and `oculus.cli` both import clean; `_validate_tool_
  references()` (unrelated to this change but always runs at import)
  still passes.

**Next steps for the next agent:**
1. 5 tools still have no extractor: `amass`, `arjun`, `gowitness`,
   `katana`, `testssl`. `testssl`'s output is fixed-width columnar text
   (`Rating`, `Vulnerable`, protocol/cipher tables) that doesn't fit the
   line-regex approach every other extractor here uses — worth a
   dedicated column-aware parser rather than forcing the same pattern.
   `katana`/`gowitness` are crawling/screenshot tools without an
   obvious "this line is a finding" signal in their own output — might
   not be worth extracting from at all versus staying raw-output-only.
2. `arjun`'s mock output already flags "may bypass auth", "potential
   SSRF/XSS" per discovered parameter in its own "Notable findings"
   block — same shape as the `⚠ Notable findings:` sections several
   other tools already have; a generic "parse the tool's own Notable
   findings block" extractor could plausibly cover arjun plus catch any
   future tool that follows the same convention, instead of one
   bespoke parser per tool.
3. The test-suite option (the other thing suggested alongside this one)
   is still untouched — worth revisiting once this extends further,
   since a real test suite would have caught the two severity bugs
   above via assertions instead of manual inspection.

---

## 2026-08-25 (11) — Real per-item tool correctness fixes: nuclei tags, wordlist categories

**Done (user request: "each script for run each testing is it correct
output? can you check it and if the tools not enough you can add any
tools" — an audit of whether the 97 checklist items' tool mappings
actually test what they claim to, following the previous entry's full
WSTG coverage expansion):**
- Audited every tool shared across multiple checklist items for the
  "same command regardless of which test invoked it" failure mode.
  Found it was real for **nuclei**, mapped to 35 different items: its
  `build_command()` has one fixed `-tags` value
  (`misconfig,exposure,headers,tech`) — correct for a few items, but
  running "nuclei" from e.g. the SSRF or SSTI checklist item silently
  ran the exact same generic misconfig scan as every other nuclei-
  mapped item, never loading SSRF/SSTI templates at all.
- Fixed with the same pattern as the existing wordlist recommendation
  system: new `checklist.NUCLEI_TAGS: dict[item_id -> tags]` (26
  entries — xss, sqli, ssrf, ssti, xxe, cors, csrf, lfi/rfi, rce,
  takeover, default-login, graphql, smuggling, ldapi, and others), and
  `backend/routers/tools.py`'s `preview_command()` swaps nuclei's
  `-tags` value when the current item has an override, same as it
  already does for ffuf/gobuster's `-w` wordlist flag. Items without an
  override keep nuclei's sensible built-in default.
- Also caught 2 more ffuf items during the audit that had no wordlist
  category despite a real dedicated bundled wordlist fitting (added to
  `WORDLIST_CATEGORY`): `WSTG-CONF-09` (File Permission → `backup`,
  same shape as backup-file exposure), `WSTG-IDNT-05` (Username Policy
  → `usernames`), `WSTG-ATHN-04` (Bypass Authentication Schema →
  `admin`, forced-browsing to protected paths), `WSTG-BUSL-08` (Upload
  of Unexpected File Types → `extensions`).
- Extended `_validate_tool_references()` (the import-time guard) to
  also catch a `NUCLEI_TAGS` entry referencing an unknown item ID, or
  an item whose `tools` list doesn't even include `nuclei` (so the
  override could never apply) — same "fail loudly at import" principle
  as the existing tool-registry check.
- Added a matching frontend hint: `RunToolDialog.tsx` shows a green
  "Using template tags scoped to this test — `<tags>`" alert when
  nuclei has an override for the current item, mirroring the existing
  wordlist-recommendation hint.

**Verified:**
- Curled the live backend for ~10 different nuclei-mapped items
  (SSRF, XSS, SSTI, GraphQL, CORS, default-login, SQLi, auth-bypass)
  and confirmed each returns the correct, distinct `-tags` value —
  previously every one of these would have returned the identical
  generic command.
- Confirmed an unmapped item (`WSTG-CONF-02`) still gets nuclei's
  plain default, unaffected.
- Confirmed the 4 new ffuf wordlist-category mappings resolve to the
  right bundled wordlist and label via the live backend.
- `_validate_tool_references()` passes with the new NUCLEI_TAGS checks
  active; checklist still loads all 97 items with zero errors.
- Full browser E2E (throwaway Playwright script, deleted after use):
  opened the SSRF checklist item, selected nuclei, confirmed the new
  green "template tags scoped to this test — ssrf" hint renders and
  the command field shows `-tags ssrf`. Zero console errors.
  `npx tsc --noEmit`, `eslint`, `next build` all clean.

**Next steps for the next agent:**
1. 9 nuclei-mapped items still use the plain default deliberately
   (WSTG-INFO-08/09 fingerprinting, WSTG-CONF-02/06/07 which the
   default genuinely suits, WSTG-INPV-03/04 which have no distinct real
   nuclei tag to target, WSTG-CLNT-09 clickjacking which the `headers`
   tag already covers). Worth a second look if any of these turn out
   to need their own override in practice.
2. The nuclei tag names in `NUCLEI_TAGS` are the community-standard
   ones as best recalled/reasoned (`xss`, `sqli`, `ssrf`, `ssti`,
   `xxe`, `takeover`, `default-login`, etc.) — nuclei's tag taxonomy is
   community-maintained and does drift; worth spot-checking against a
   real `nuclei -tag-list` output on a machine with nuclei's templates
   actually installed if a specific tag ever turns out to match zero
   templates.

---

## 2026-08-25 (10) — Wrap the whole project in Docker (web app included)

**Done (user request: "can you wrap all project by docker and update
script for run and ignore files not necessary" — the existing
Dockerfile only wrapped the CLI/TUI; the web app (backend + frontend)
had no Docker path at all):**
- `Dockerfile`: added `sqlmap`/`hydra` to the apt install list (both
  packaged directly for Debian, no build step) so the image now bundles
  all 18 tools, not 16. Switched `pip install .` to `pip install
  ".[web]"` so FastAPI/uvicorn/websockets ship in the same image. Added
  `COPY backend ./backend` and `ENV PYTHONPATH=/app` — `backend/` isn't
  a pip-installed package (pyproject.toml's `packages.find` only
  includes `oculus*`), so it needs to be on disk and importable via
  `python -m uvicorn backend.main:app` for the new `backend` compose
  service.
- New `frontend/Dockerfile`: 3-stage build (deps → build → runtime) for
  the Next.js app. `NEXT_PUBLIC_API_URL`/`NEXT_PUBLIC_WS_URL` build
  args default to `http://localhost:8000`/`ws://localhost:8000` —
  correct as-is for this compose setup, since those are inlined into
  the *client* bundle and the browser (not the Docker network) is what
  actually makes those calls, hitting the backend's published host port.
- `docker-compose.yml` rewritten: `backend` + `frontend` services (what
  a plain `docker compose up` starts by default) alongside the
  pre-existing `oculus` CLI/TUI service, now gated behind a `cli`
  profile specifically so a plain `up` doesn't try to start an
  interactive-TTY-only service. All three share the same `oculus-data`
  volume, so an engagement created via the web UI is visible to
  `docker compose run --rm oculus status` and vice versa.
- New `run-docker.sh` (mirrors the existing local-dev `run.sh`):
  `up`/`down`/`logs`/`build` subcommands wrapping `docker compose`.
- `.gitignore`/`.dockerignore` cleanup: removed 3 files that had no
  business being tracked — `.DS_Store` (macOS junk), a ~48KB stray
  terminal-session-log text file with a timestamp-only filename
  (clearly an accidental paste, not project content), and
  `demo_report.md` (a generated demo artifact). Kept on disk, just
  untracked; `.gitignore` updated so they don't come back. Root
  `.dockerignore` now also excludes `frontend/node_modules`,
  `frontend/.next`, and the SecLists download cache so the root
  Dockerfile's build context isn't needlessly bloated by directories it
  never even COPYs.

**Verified — this one got a real build, not just a static read:**
- Docker Desktop wasn't running at the start of this session; started
  it and did **actual builds**, not just `docker compose config`
  syntax validation. Backend/CLI image build took ~13 minutes (mostly
  compiling katana's large dependency tree — expected, matches the
  original Dockerfile's own build time before this session); frontend
  image built in under a minute.
- Confirmed `sqlmap`/`hydra`/`testssl.sh` all present and executable in
  the built image (`command -v` inside a running container).
- Ran the real stack: `docker compose up -d backend frontend`, hit
  `/api/health` (`{"status":"ok"}`), created a real engagement via the
  API and confirmed it got all 97 checklist items, previewed a real
  `sqlmap` command through the containerized backend.
- **Chased down a false alarm while verifying**: `sqlmap`'s
  `available` field read `false` when curled from the host but `true`
  when checked from inside the container — turned out to be this dev
  machine's own leftover local `uvicorn`/`next start` processes still
  bound to `127.0.0.1:8000`/`:3000` from earlier in this session; macOS
  routes a connection to `127.0.0.1:8000` to the more specific bind
  (the local process) over Docker's wildcard (`0.0.0.0:8000`) proxy, so
  every "verification" curl was silently hitting the old local process,
  not the container. Killed the stale local processes, re-verified
  clean against the actual container, confirmed all 18 tools report
  available.
- Full browser E2E against the real Docker stack (frontend container →
  backend container, not localhost dev servers): created an engagement,
  confirmed all 97 items rendered, opened the SQL Injection item,
  selected `sqlmap`, confirmed no "not installed" warning (proving the
  binary really is reachable inside the running container, not just
  present in a `docker exec` shell). Zero console errors.
- Restored the local dev environment afterward (stopped the Docker
  containers, restarted local `uvicorn`/`next start` so the real
  engagements — "Snoopbee Lab1/2/3" — created during this session by
  the user testing in parallel were reachable again).

**Next steps for the next agent:**
1. The backend/CLI image build is genuinely slow (~13 min, dominated by
   `go install`-ing katana and its headless-browser-adjacent dependency
   tree) — this was already true before this session, not introduced by
   it, but worth knowing if a future change to the Dockerfile seems to
   "hang": it's very likely just this, not a real problem.
2. `docker compose build` (no service name) builds all 3 services,
   including the `cli`-profile-gated `oculus` one — `build` ignores
   profile restrictions even though `up`/`run` respect them. Not a bug,
   just worth knowing `make docker`/`docker compose build` do build all
   three, not just the two the default `up` starts.
3. The Docker backend/CLI services use a *separate* `oculus-data`
   volume from this dev machine's local `~/.oculus/` — engagements
   created via the containerized web app (like the "Docker Final Check"/
   "Docker Stack Check" ones from this session's verification, deleted
   afterward) are invisible to the local dev servers and vice versa.
   Expected/correct (different persistence backing), just worth knowing
   if "my engagement disappeared" ever gets reported — it's almost
   certainly a local-vs-Docker split, not data loss.

---

## 2026-08-25 (9) — Full OWASP WSTG v4.2 coverage: 97 checklist items

**Done (user pasted the complete WSTG v4.2 table of contents — all 12
sections, 4.1 through 4.12 — and asked to "implement tools and script
for test these objectives"):**
- Rewrote `oculus/checklist.py`'s `build_checklist()` from 26 items
  (INFO, CONF, partial IDNT/ATHN/INPV) to the **full 97-item** WSTG v4.2
  TOC across all 12 sections: INFO(10), CONF(11), IDNT(5), ATHN(10),
  ATHZ(4), SESS(9), INPV(19), ERRH(2), CRYP(4), BUSL(9), CLNT(13),
  APIT(1). Every item's `owasp_ref` matches the exact numbering the user
  pasted; verified section-by-section counts against it exactly.
- **Corrected a numbering drift caught in the process**: the existing
  `WSTG-CONF-08`/`09`/`10` items didn't actually match the real official
  WSTG numbering (they'd been invented/misassigned earlier in this
  project's life, before this session had the authoritative TOC to check
  against) — real `CONF-08` is "Test RIA Cross Domain Policy", `CONF-09`
  is "Test File Permission", `CONF-10` is "Test for Subdomain Takeover"
  (was sitting at the made-up `CONF-09`), and there's an official
  `CONF-11` ("Test Cloud Storage") that didn't exist here at all. Fixed:
  - `CONF-08` is now really "Test RIA Cross Domain Policy" (new); the
    "Security Response Headers" content that used to squat on that ID
    got folded into `CONF-02`'s description instead (CSP/X-Frame-Options/
    etc. are genuinely part of "Test Application Platform Configuration",
    just not their own numbered WSTG item).
  - `CONF-09` is now really "Test File Permission" (new).
  - "Test for Subdomain Takeover" moved to its correct `CONF-10`.
  - `CONF-11` "Test Cloud Storage" added (new).
  - The old `CONF-10` "Test WAF Detection" wasn't an official WSTG-CONF
    item at all — removed as a standalone entry (`wafw00f` was already
    also mapped to `WSTG-INFO-10` "Map Application Architecture", which
    legitimately covers WAF/CDN mapping, so no coverage was lost).
- **No new tool wrappers added this round** — deliberate scope call
  given the size of the checklist expansion. `nuclei`'s template tag
  system alone covers the large majority of the new Input Validation,
  Authorization, and Client-side items (LFI/RFI, SSRF, SSTI, XXE, CORS,
  open redirect, clickjacking, HTTP smuggling, GraphQL, etc.) well
  enough to map directly; existing tools (`ffuf`, `httpx`, `katana`,
  `testssl`, `sqlmap`, `hydra`) cover most of the rest. Roughly a third
  of the new items (`tools=[]`) are honestly manual/business-logic
  tests no CLI tool can judge — documented as such in the new module
  docstring rather than forcing a tool mapping that wouldn't actually
  test the thing.
- README's "Checklist Coverage" and "Tool Wrappers" tables updated to
  match — the tool-mapping table is now explicitly a representative
  sample (checked against `checklist.py`'s `tools=[...]` per item, not
  hand-synced exhaustively for 97 items), and the stale `CONF-08/09/10`
  references in it fixed to the corrected numbering above.

**Verified:**
- `build_checklist()` returns exactly 97 items; confirmed zero duplicate
  `id`s and zero duplicate `owasp_ref`s.
- Per-section counts (`Counter(category_code)`) checked against the
  pasted TOC exactly: INFO 10, CONF 11, IDNT 5, ATHN 10, ATHZ 4, SESS 9,
  INPV 19, ERRH 2, CRYP 4, BUSL 9, CLNT 13, APIT 1 — all match.
- `_validate_tool_references()` (the import-time guard added earlier
  this session specifically to catch a dead/unregistered tool name)
  passes cleanly across all 97 items' `tools` lists.
- `./venv/bin/python -c "from backend.main import app"` and `from
  oculus.cli import build_checklist` both import clean.
- Curled the live backend's `POST /api/engagements` and confirmed a
  freshly created engagement gets all 97 items with the correct
  per-section breakdown.
- Full browser E2E (no frontend code changes needed — the UI already
  renders whatever checklist items the backend returns): confirmed
  `0/97` progress, all 12 section headers present including the very
  last one (`API TESTING 0/1` → `WSTG-APIT-01 — Testing GraphQL`),
  sidebar scrolls correctly through the much longer list, item detail
  panel renders correctly for both the first and last item. Zero
  console errors.

**Next steps for the next agent:**
1. Neither of the two pre-existing real engagements ("Snoopbee Lab1",
   "Snoopbee Lab2") retroactively gained the new items — same
   snapshot-at-creation behavior as every prior checklist change this
   session; only new engagements get the full 97.
2. `tools=[]` items (roughly a third of the new ones) have no "Run
   tool" button at all in the UI (`ItemDetail.tsx`'s `hasRunnableTools`
   already correctly hides it for an empty tools list) — they're
   tracked as pending/done/skipped like any item, just with no
   automation angle. That's an honest reflection of WSTG reality, not
   a gap to fill with a fake tool mapping.
3. Given the scale, some individual item descriptions are necessarily
   terser than earlier sessions' more elaborate ones — if a specific
   item's description turns out to be too thin in practice, it's a
   one-item edit in `checklist.py`, not a structural issue.

---

## 2026-08-25 (8) — Discovered-path tree view + run-a-tool-at-this-path

**Done (user request, clarified via AskUserQuestion into "show
ffuf/gobuster/katana's discovered paths as an expandable tree instead
of a flat log, and let me run a tool against a specific discovered
path"):**
- `frontend/src/lib/pathTree.ts`: `parseDiscoveredPaths(output, toolName)`
  extracts discovered directory/file paths from raw tool output, handling
  4 distinct formats in one pass — ffuf's own mock-output style
  (`| URL | https://target/admin`, including stripping a trailing
  ` -> https://target/admin/` redirect), gobuster's
  (`/admin (Status: 301) ...`), a bare absolute URL alone on a line
  (katana, or real ffuf `-v`), and real ffuf's `-s` (silent) bare-path-only
  lines (gated to `toolName === "ffuf"` specifically, since a bare line
  with no other marker is too ambiguous to assume for any other tool's
  output). `buildPathTree(paths)` turns the flat list into a nested tree.
- `frontend/src/components/DirectoryTree.tsx`: recursive collapsible tree
  (hand-rolled, no new dependency) — folder/file icons, click to
  expand/collapse, and a hover-revealed ▶ run icon per node.
- `ItemDetail.tsx`: a **Raw / Tree** `ToggleButtonGroup` appears above
  the Tool Output panel only when the active tab's output actually has
  parseable paths (computed via `useMemo`, falls back to Raw
  automatically if you switch to a tab that doesn't, e.g. an `nmap`
  result — a stale "Tree" selection doesn't leave the panel blank).
  Clicking a node's run icon opens the existing `RunToolDialog` with
  the *target* overridden to `${engagementTarget}${nodePath}` (e.g.
  `192.168.2.11/admin`), so ffuf/gobuster's own `-u .../FUZZ`
  construction naturally becomes a recursive fuzz under that discovered
  directory. `RunToolDialog` now also shows a `Target: ...` caption
  under its title so this is visible, not just implicit in the command
  preview.
- **Bug caught and fixed while building this**: `oculus/tools/base.py`'s
  `base_url()` isolated the hostname for its IPv4-vs-hostname scheme
  check via `target.split(":")[0]` — correct for a bare host or
  `host:port`, but a target with an appended path (`192.168.2.11/admin`,
  exactly what this feature produces) has no colon, so the *whole*
  `"192.168.2.11/admin"` string failed the IPv4 regex and incorrectly
  fell through to `https://`. Fixed to isolate the hostname via
  `target.split("/")[0].split(":")[0]` first. This would have silently
  broken every IP-target engagement's "run at this discovered path"
  clicks (connection refused on the wrong scheme) without ever
  surfacing as an error the tester could easily place.

**Verified:**
- Unit-style check of the parsing regexes (as plain JS, run directly in
  Node) against the *real* mock output text from `ffuf_tool.py`,
  `gobuster_tool.py`, and `katana_tool.py`: 9/16/27 paths respectively,
  all correct, no duplicates, no redirect-artifact paths.
- `base_url()` fix verified directly: `base_url("192.168.2.11/admin")`
  now returns `http://192.168.2.11/admin` (was `https://...`);
  `base_url("192.168.2.11:8080/admin")` and `base_url("example.com/
  admin")` also checked. Re-ran `build_command()` for `ffuf`, `gobuster`,
  `nikto`, `nuclei`, `katana`, `nmap` against an IP target to confirm no
  regression from the change.
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser E2E via throwaway Playwright scripts (deleted after use):
  injected real `FfufTool.mock_output()` text directly into a checklist
  item's `tool_outputs` (bypassing an actual scan for deterministic
  content), confirmed the Raw/Tree toggle appears, confirmed Tree view
  renders the correct nested structure (`.git` as an expandable folder
  containing `HEAD`, everything else as flat files, alphabetically
  sorted) via screenshot. Separately, against an **IP-target** ("192.168.
  2.11") engagement specifically to exercise the `base_url()` fix:
  clicked the `admin` node's run icon, confirmed the dialog's `Target:`
  caption read `192.168.2.11/admin` and the generated command was
  `ffuf -u http://192.168.2.11/admin/FUZZ ...` — correct `http://`, not
  the `https://` this would have produced pre-fix. Zero console errors
  in both runs.

**Next steps for the next agent:**
1. The tree is rebuilt from scratch on every render via `useMemo` keyed
   on `(activeOutput, item.tool_outputs)` — fine for the hundreds-of-paths
   scale ffuf/gobuster/katana actually produce, would need memoizing
   differently (or virtualizing the tree) if some future tool's output
   had tens of thousands of discovered paths.
2. The "run at this path" override only makes sense for URL-based tools
   (ffuf, gobuster, and to a lesser extent katana/nuclei/httpx) — nothing
   currently stops a tester from clicking a tree node's run icon and then
   picking `nmap` from the Tool dropdown, which would try to port-scan a
   hostname like `192.168.2.11/admin` (nonsensical). Not fixed here since
   the tester picks the tool explicitly in the same dialog and the
   `Target:` caption makes the override visible before they hit Run —
   worth revisiting if this causes real confusion in practice.

---

## 2026-08-25 (7) — New tools, new WSTG coverage, more wordlist categories

**Done (user request: "can you add other strategies or tools" —
clarified via AskUserQuestion into all three: more wordlist categories,
more tool wrappers, more checklist coverage):**

- **2 new tool wrappers** (`oculus/tools/`), registered in
  `TOOL_REGISTRY` (18 tools total, was 16):
  - `sqlmap_tool.py` — SQL injection detection/exploitation. Default
    command crawls the target and tests every form/link parameter found
    (`--crawl=2 --forms --batch --level=2 --risk=1`) rather than
    requiring a pre-known injectable URL, so it's actually runnable
    out of the box; description tells the tester to edit the command to
    a specific `-u "...?id=1"` for a faster, targeted run once they've
    found a real parameter to test.
  - `hydra_tool.py` — online brute-force login testing. Defaults to SSH
    (`ssh://target`, the single most commonly exposed brute-forceable
    service) using two new small bundled wordlists (below); description
    explains how to edit the command for `http-post-form` or another
    protocol instead, since that part is inherently site-specific.
    `uses_wordlist = False` — hydra needs *two* lists (`-L`/`-P`), which
    doesn't fit the picker's single-`-w` assumption, so its default
    wordlists are just hardcoded paths in `build_command()` rather than
    wired into the picker.
- **2 new bundled wordlists**: `oculus/data/wordlists/usernames.txt`
  (~30 common account names) and `passwords.txt` (~30 common/default
  passwords) — same small-curated-default pattern as the existing
  admin/api/backup/etc. bundles.
- **6 new checklist items**, 3 new WSTG sections beyond the existing
  INFO/CONF (26 items total, was 20):
  - `WSTG-IDNT-04` Test for Account Enumeration (`ffuf`)
  - `WSTG-ATHN-02` Test for Default Credentials (`hydra`, `nuclei`)
  - `WSTG-ATHN-03` Test for Weak Lock Out Mechanism (`hydra`)
  - `WSTG-INPV-01` Test for Reflected XSS (`nuclei`)
  - `WSTG-INPV-05` Test SQL Injection (`sqlmap`, `nuclei`)
  - `WSTG-INPV-12` Test Command Injection (`nuclei`)
- **2 new wordlist recommendation categories**
  (`oculus.wordlists.CATEGORY_KEYWORDS`, `checklist.WORDLIST_CATEGORY`):
  `"usernames"` (mapped to `WSTG-IDNT-04`) and `"passwords"` (not
  currently mapped to any picker-using item since hydra doesn't use the
  picker — added for consistency/future use). Keywords deliberately
  tight (`"username"`/`"usernames/"`, `"password"`/`"passwords/"`/
  `"rockyou"`) after an initial looser attempt (`"names"` as a
  usernames keyword) matched way too broadly against the real SecLists
  tree — service-name lists, variable-name lists, PHP filename lists all
  false-positived before narrowing it.

**Verified:**
- `_validate_tool_references()` (added last session specifically to
  catch a dead/unregistered tool reference) passes cleanly — confirms
  every new item's tools are real, registered names.
- `build_checklist()` returns 26 items; new tools' `build_command()`
  produce correct, runnable commands for both fast/full.
- `recommend_wordlist("usernames")`/`("passwords")` correctly fall back
  to the new bundled files when no local SecLists install exists.
- Curled the live backend's `/wordlists/remote/browse?item_id=
  WSTG-IDNT-04` against the real GitHub SecLists data: 17 genuinely
  username-relevant files recommended (`Usernames/CommonAdminBase64.txt`,
  `Usernames/top-usernames-shortlist.txt`, etc.) after the keyword
  narrowing above.
- `./venv/bin/python -c "from backend.main import app"` imports clean;
  live backend (already running with `--reload`) picked up both new
  tools and all 6 new items with no errors.
- Full browser E2E via a throwaway Playwright script (deleted after
  use): confirmed the 3 new section headers (Identity Management,
  Authentication, Input Validation) render in the sidebar, `sqlmap`
  appears as a tool option on the SQL Injection item, `hydra` appears
  on the Default Credentials item (with its install-hints alert showing
  correctly, since neither is installed on this dev machine), and the
  Account Enumeration item's Run Tool dialog shows the "username
  enumeration" recommendation hint. Zero console errors.
- `tool_installer.py`'s tester-facing tool list iterates `TOOL_REGISTRY`
  dynamically — confirmed `sqlmap`/`hydra` show up there with no
  additional code, correctly flagged as not installed on this machine.

**Next steps for the next agent:**
1. `sqlmap`/`hydra` aren't in `tool_installer.py`'s `RECOMMENDED` starter
   set — deliberate, since neither has `findings_extractor.py`
   auto-parsing wired up yet (that set specifically matches the 7 tools
   that do). Worth adding auto-extraction for at least `sqlmap` (its
   "identified the following injection point(s)" block is fairly
   parseable) if this becomes a commonly-used item.
2. The existing "Snoopbee Lab1" engagement (created before this
   session) won't retroactively gain the 6 new checklist items — its
   `checklist_items` were snapshotted from `build_checklist()` at
   creation time, same as any other engagement. This matches existing
   behavior (checklist items are per-engagement snapshots, not live
   references) and wasn't changed here; a tester who wants the new
   items on an old engagement would need to add them manually via the
   existing "+ add item" checklist UI.
3. Real OWASP WSTG has ~90 more items beyond what's covered now
   (Session Management, Authorization, Business Logic, Client-Side,
   Error Handling, Cryptography, API Testing, ...) — this pass added 6
   from 3 of those sections as a bounded, concrete slice per the user's
   request, not full coverage.

---

## 2026-08-25 (6) — Real per-file recommendations in the SecLists (GitHub) tab

**Done (user request: "recommend the wordlists in seclist at script
also" — the per-test wordlist recommendation feature from earlier this
session only ever applied to Local/bundled wordlists; the remote
GitHub-browse tab's own "recommended" flag existed but was checked
against whole SecLists folder names like `cat.lower() == "admin"`,
which never matches since SecLists' real top-level folders are broad
topics — `Discovery`, `Fuzzing`, `Passwords`, `Usernames`, ... — not
per-test categories, so the remote tab's recommendation never actually
fired for any real test):**
- `oculus/wordlists.py`: renamed the private `_CATEGORY_KEYWORDS` dict
  to public `CATEGORY_KEYWORDS` so it's importable elsewhere — same
  lookup `recommend_wordlist()` and the Local tab's grouping already
  use (e.g. `"admin": ("admin",)`, `"api": ("api", "swagger",
  "endpoint", "graphql")`).
- `backend/routers/tools.py`'s `/wordlists/remote/browse`: now checks
  each *individual file's path* against the category's keywords (not
  the folder name), and collects every match — regardless of which
  folder it actually lives in — into a synthetic `"Recommended"` group
  pinned first in the response, capped to 20. Also flags `recommended:
  true` on the matching file's entry within its normal folder group too
  (so browsing by folder still shows the star), and threads
  `RemoteWordlistInfo`'s new `recommended` field through.
- `WordlistPickerDialog.tsx`: renders a small green star next to a
  recommended file's name within its normal folder group (skipped
  inside the "Recommended" group itself, where it'd be redundant on
  every card); the synthetic group itself already got the star+green
  category-header treatment for free since it reuses the same
  `group.recommended` rendering as any other group.

**Verified:**
- Curled `/wordlists/remote/browse?item_id=WSTG-CONF-05` (admin
  interfaces) against the real GitHub data: got back 3 genuinely
  relevant files in a `"Recommended"` group —
  `Discovery/Web-Content/.../admin.txt`,
  `Discovery/Web-Content/Service-Specific/confluence-administration.txt`,
  `Usernames/CommonAdminBase64.txt` — pulled from 2 different top-level
  folders neither of which is named "admin". Repeated for
  `WSTG-CONF-04` (backup → `Common-DB-Backups.txt`), `WSTG-INFO-06`
  (api → `Swagger.txt`, `Docker-API.txt`, `strapi.txt`, ...), and
  `WSTG-INFO-03` (metafiles → `versioning_metafiles.txt`) — all
  correctly relevant, none of it possible under the old
  folder-name-only check.
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser E2E via a throwaway Playwright script (deleted after
  use): opened the SecLists (GitHub) tab for "Enumerate Admin
  Interfaces", confirmed a green-starred "Recommended" section with 3
  cards appeared pinned above the regular `Ai`/`Discovery`/... folder
  groups, screenshot-confirmed correct rendering. Zero console errors.

---

## 2026-08-25 (5) — Install SecLists wordlists into the project, not the home dir

**Done (user request: "can you implement at select wordlists and can
install the wordlists to own project" — a direct follow-up to the prior
entry, which had put picked-file downloads under `~/.oculus/wordlists/
seclists/`; the ask was for them to live inside the project itself):**
- `oculus/seclists_remote.py`: renamed the destination from
  `CACHE_DIR = ~/.oculus/wordlists/seclists` to
  `INSTALL_DIR = oculus/data/wordlists_downloaded/seclists` — inside
  this project's own package directory, a sibling of (not mixed into)
  the small hand-curated bundle at `oculus/data/wordlists/`. Kept
  `CACHE_DIR` as a backwards-compatible alias pointing at the same
  value. Added `install_wordlist` as an alias for `download_wordlist` —
  same function, a name that matches how it reads in the UI now
  ("Installs only the single file...").
  - The *tree-listing* cache (`seclists_tree_cache.json` — which files
    exist, not their content) deliberately stayed in `~/.oculus/` next
    to `config.json`/`engagements/` — it's request metadata, not a
    wordlist install, so home-dir persistence is still the right call
    for it specifically.
- `.gitignore`: added an explicit `oculus/data/wordlists_downloaded/`
  entry — these are per-checkout downloads, not meant to be committed.
  (There's also an unrelated pre-existing uncommitted `*.txt` rule in
  this file from before this session that would incidentally cover the
  same thing; added the explicit directory rule anyway so this doesn't
  depend on that other, unrelated change staying in place.)
- `oculus/wordlists.py`'s registered search root didn't need to change
  — it already referenced `seclists_remote.CACHE_DIR.parent` generically,
  which now just resolves to the project directory instead of the home
  directory automatically.
- Frontend (`WordlistPickerDialog.tsx`): updated the SecLists (GitHub)
  tab's caption and the Local tab's empty-state hint from "downloads"/
  "download" to "installs"/"install... into this project", naming the
  actual destination path (`oculus/data/wordlists_downloaded/`) so a
  tester knows where to look on disk.

**Verified:**
- Cleared any leftover files under the old `~/.oculus/wordlists/` path
  from the previous entry's testing first.
- `download_wordlist("Discovery/Web-Content/quickhits.txt")` against the
  real repo: confirmed the file lands at `<project>/oculus/data/
  wordlists_downloaded/seclists/Discovery/Web-Content/quickhits.txt`,
  confirmed nothing appears under `~/.oculus/` matching a wordlist file,
  confirmed `git status`/`git check-ignore -v` show it correctly ignored
  (matched by the new explicit rule, not the unrelated stray one), and
  confirmed it still surfaces under `discover_wordlists_grouped()`'s
  `SecLists/Discovery` group.
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser E2E via a throwaway Playwright script (deleted after
  use): opened the SecLists (GitHub) tab, confirmed the caption reads
  "Installs only the single file... into this project
  (oculus/data/wordlists_downloaded/)", searched "quickhits", installed
  the matching file, confirmed the Run Tool dialog's command field
  pointed at the new in-project path. Zero console errors. Deleted the
  test engagement and the installed test file afterward.

---

## 2026-08-25 (4) — Browse & selectively download individual SecLists wordlists

**Done (user request: "implement wordlists that won't download all
wordlists in seclist but user can select any wordlists at
https://github.com/danielmiessler/SecLists.git only target wordlists
file for run the script and create the structure wordlists in own
project" — i.e. no full `git clone` of the ~1GB SecLists repo; browse it
remotely and download only the one file actually picked):**
- New `oculus/seclists_remote.py`:
  - `list_remote_wordlists()` — one GitHub API call
    (`GET /repos/danielmiessler/SecLists/git/trees/master?recursive=1`)
    listing every file in the repo (6000+ `.txt` files as of this
    session), cached to disk for 24h at `~/.oculus/wordlists/
    seclists_tree_cache.json` — unauthenticated GitHub API calls are
    rate-limited to 60/hour, and the tree barely changes hour to hour,
    so there's no reason to refetch on every dialog open.
  - `download_wordlist(path)` — fetches exactly that one file's raw
    content (`raw.githubusercontent.com/.../master/<path>`) and saves it
    under `~/.oculus/wordlists/seclists/<path>`, mirroring the repo's
    own directory structure. No-ops (returns the existing path) if
    already downloaded. Rejects absolute paths / `..` segments — *path*
    ultimately comes from a request a tester could hand-edit.
  - No new Python dependency — uses stdlib `urllib.request` for both
    calls rather than adding `requests`.
  - Registered the download cache dir's *parent* as a
    `oculus/wordlists.py` search root (specifically the parent, not the
    `seclists/` dir itself, so `_category_for()`'s existing "seclists/
    <Discovery|Passwords|...>" special-case groups a downloaded file the
    same way a full local SecLists checkout would) — a file downloaded
    via the new remote-browse tab is then immediately visible under the
    existing **Local** tab too, no separate code path needed for that.
- Backend (`backend/routers/tools.py`): two new endpoints.
  - `GET /api/tools/wordlists/remote/browse?item_id=...&q=...` — grouped
    remote listing (same shape as the existing local `/wordlists/
    grouped`), *q* filters by substring, *item_id* flags the
    recommended-for-this-test category. Caps each category to 40 entries
    when unfiltered (SecLists' own `Fuzzing` folder alone has 4600+
    files — no reason to ship all of them over the wire before a tester
    has even searched) with a `truncated`/`total` flag so the UI can say
    "showing first 40 of 4642 — search to narrow" instead of silently
    cutting off; a committed search returns every match, uncapped.
  - `POST /api/tools/wordlists/remote/download` — downloads (or reuses
    the cache) and returns the local path.
  - Both wrap `seclists_remote`'s new `RemoteFetchError` into a clean
    HTTP 502 with a message, instead of a raw traceback, if GitHub is
    unreachable/rate-limited.
- Frontend: `WordlistPickerDialog.tsx` restructured into two `Tabs` —
  **Local** (the existing picker, unchanged behavior) and **SecLists
  (GitHub)** (new). The GitHub tab reuses the same card-grid/collapse/
  Enter-to-search UI patterns as Local for consistency, plus: a cloud
  icon per card (outline = not yet downloaded, filled/"done" = already
  cached) and a spinner in place of the icon while a download is in
  flight; clicking any card downloads-then-selects in one action
  (idempotent — clicking an already-downloaded card just selects
  immediately, no re-download); a `truncated` notice per category when
  the backend capped results. New types (`RemoteWordlistInfo`,
  `RemoteWordlistGroup`, `RemoteGroupedWordlists`) and `api.
  browseRemoteWordlists()`/`api.downloadRemoteWordlist()` added
  alongside the existing local-wordlist equivalents.

**Verified:**
- `list_remote_wordlists()` against the real GitHub API: 6042 real
  files, correctly grouped into the repo's actual top-level folders
  (`Fuzzing` 4642, `Passwords` 707, `Discovery` 415, `Miscellaneous` 241,
  `Usernames` 14, `Pattern-Matching` 9, `Ai` 8, `Payloads` 5,
  `Web-Shells` 1).
- `download_wordlist("Discovery/Web-Content/common.txt")` against the
  real repo: fetched exactly that one 38.5KB file (confirmed real
  wordlist content), confirmed `is_downloaded()` flips to `True`
  afterward, confirmed it then appears under `discover_wordlists_
  grouped()`'s `SecLists/Discovery` group alongside the bundled
  wordlists — proving the local-discovery integration works, not just
  the download itself.
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser E2E via a throwaway Playwright script (deleted after
  use): opened the Run Tool dialog for "Enumerate Admin Interfaces" →
  ffuf → Select wordlist → switched to the "SecLists (GitHub)" tab →
  confirmed the "downloads only the single file" caption and real
  category cards (`Discovery` 2 matches, `Passwords` 1 match) rendered
  → searched "common.txt", pressed Enter, confirmed it narrowed to the
  real matches (`OBEX_common.txt`, `Discovery/Web-Content/common.txt`)
  → clicked the `Discovery/Web-Content/common.txt` card → confirmed the
  Run Tool dialog's button updated to "Wordlist: common.txt" and the
  command field's `-w` flag now pointed at `~/.oculus/wordlists/
  seclists/Discovery/Web-Content/common.txt` → confirmed via `find` on
  disk that **only that one file** exists under the cache dir, nothing
  else. Zero console errors throughout.

**Next steps for the next agent:**
1. The 24h tree cache is a single flat file, not per-query — fine for
   one local user, would need real caching (Redis, etc.) if this app
   ever serves multiple concurrent users hitting GitHub's API
   independently.
2. No download-progress indication beyond a spinner — fine for the
   small (KB-to-low-MB) individual files SecLists actually has, would
   need a real progress bar if this pattern got reused for something
   with much larger individual files.
3. GitHub's unauthenticated rate limit (60 req/hour) applies to the
   tree-listing call only (raw file downloads via
   raw.githubusercontent.com aren't API-rate-limited the same way) — the
   24h cache keeps this comfortably under the limit for normal use, but
   there's no user-visible message distinguishing "rate limited" from
   "GitHub unreachable" if it ever does trip; both currently surface as
   the same generic 502 message.

---

## 2026-08-25 (3) — Fix: dnsx "command not found" (shell-wrapped tool, PATH not inherited)

**Done (user pasted a real failure): `/bin/sh: dnsx: command not found`
when running the `dnsx` checklist tool for real.**
- Root cause: `dnsx_tool.py`'s `build_command()` has to shell out —
  `["sh", "-c", "echo target | dnsx -a ... -silent"]` — since dnsx reads
  its target from stdin rather than a flag. `BaseTool.run()` already
  resolves `cmd[0]` to a full path via `resolve_binary()` before
  spawning (the fix for the earlier "subfinder installed but can't use
  it" bug, which checks Go's bin dir since `go install` binaries aren't
  on PATH by default) — but for dnsx, `cmd[0]` is `"sh"`, not `"dnsx"`.
  `sh` resolves fine via the ordinary PATH, so that resolution never
  reaches the *nested* `dnsx` invocation inside the shell string at all;
  the child shell just inherits the parent process's own PATH, which
  doesn't include the Go bin dir either.
- Fixed in `oculus/tools/base.py`: new `_subprocess_env()` builds the
  environment passed to every `run_tool()` subprocess with the same
  extra dirs `_extra_bin_dirs()`/`resolve_binary()` already know about
  (`$GOBIN`, `$GOPATH/bin`) prepended to `PATH`. Fixes this for dnsx and
  for any other shell-wrapped tool the same way, without parsing/
  rewriting each command string individually — the general architectural
  gap was "oculus's own binary search path never reaches a subprocess's
  own env," not "dnsx specifically is broken."

**Verified:**
- Reproduced the exact reported failure locally first: put a fake `dnsx`
  executable only in a directory pointed at by `$GOBIN` (not on plain
  `PATH`), ran `DnsxTool(target="example.com").run()` against the
  pre-fix code (via `git stash` on just `base.py`) — got the identical
  error, `/bin/sh: dnsx: command not found`, exit code 127.
- Same reproduction against the fixed code: `sh -c` now finds and runs
  the fake dnsx correctly (`simulated=False`, `exit_code=0`, real output
  parsed from the fake binary).
- Confirmed no regression for a normal (non-shell-wrapped) tool — `nmap`
  still runs for real, unaffected by the `PATH` change.
- Live backend (already running with `--reload`) picked up the change
  with no import/startup errors; curled `/api/tools` and confirmed
  `dnsx` still reports correctly.

**Also this session:** removed the `Co-Authored-By: Claude` trailer from
every commit message on `main` (8 commits had it) via `git filter-branch
--msg-filter` + `git push --force-with-lease`, per explicit user request
after confirming the scope (rewrite + force-push, not just "stop adding
it going forward"). File contents are unchanged — verified with `git
diff <old-head> <new-head> --stat` showing zero differences before
pushing. **Every commit hash on `main` changed as a result** — worth
knowing if anything anywhere references an old hash (there's nothing
tracked in this repo that does, as of this session).

---

## 2026-08-25 (2) — Audit: does each checklist item's tool list match its purpose?

**Done (user question: "each script tools it related with purpose each
engagements? if not can you adjust it" — asking whether the tools
assigned to each WSTG checklist item actually serve that item's stated
testing purpose):**
- Read every one of the 20 checklist items in `checklist.py` against its
  own `description` and cross-checked `tools` against `TOOL_REGISTRY`.
  Found and fixed:
  - **`WSTG-INFO-08` (Fingerprint Web Application Framework) listed
    `"wappalyzer-cli"`** — not a real tool anywhere in this project
    (`oculus/tools/__init__.py`'s `TOOL_REGISTRY` has no such entry).
    It's been a dead reference since this checklist item was written —
    the Run Tool dropdown for this item was silently missing that third
    option the whole time, no error, just fewer choices than intended.
    Replaced it with `nuclei`, which already has tech-detect templates
    (`-tags ...,tech`, used elsewhere in `nuclei_tool.py`) and genuinely
    fits "fingerprint the framework/CMS, match against known CVEs."
  - **`WSTG-INFO-01` (Search Engine Discovery & Recon)'s description
    promised Google/Bing/Shodan dorking**, but its actual tools
    (`subfinder`, `amass`) are subdomain enumeration, not search-engine
    dorking — no wrapped tool in this project does dorking at all.
    Reworded the description to honestly describe what the tools
    actually contribute (passive subdomain/asset discovery via
    aggregated sources) and explicitly call out that dorking/Shodan
    lookups are a manual supplement, rather than implying automated
    coverage that doesn't exist.
  - **3 items had a copy-pasted wrong `owasp_ref`**: `WSTG-CONF-08`
    (Security Response Headers) was stamped `WSTG-CONF-07` (duplicating
    the HSTS item's own ref), `WSTG-CONF-09` (Subdomain Takeover) was
    stamped `WSTG-CONF-10`, and `WSTG-CONF-10` (WAF Detection) was
    stamped `WSTG-CONF-01` (duplicating the network-config item's ref).
    All 3 now self-reference correctly.
  - Every other item's tools were already a good match for its stated
    purpose (e.g. `WSTG-CONF-01`'s open-port scan → `nmap` alone;
    `WSTG-CONF-03`/04/05's wordlist-brute-force tests →
    `ffuf`/`gobuster`, matching last session's per-test wordlist
    recommendations) — left unchanged.
- Added `_validate_tool_references()`, run once at `checklist.py` import
  time: asserts every tool name in every item's `tools` list exists in
  `TOOL_REGISTRY`, with a message naming the offending item. This is
  specifically to catch the `wappalyzer-cli` class of bug immediately
  (a crash on startup) instead of it silently sitting there as a
  missing dropdown option for however long, like this one did.
- Migrated the one existing real engagement (`~/.oculus/engagements/
  25f27157.json`, the user's actual "Snoopbee Lab1" lab work) to match:
  its checklist items were snapshotted from `build_checklist()` at
  creation time, so it had the stale `wappalyzer-cli` entry and the 3
  wrong `owasp_ref`s baked in. Patched only those 4 exact stale
  field values in place — left every other field (status, findings,
  tool_outputs, notes, timestamps) completely untouched. Confirmed via
  the live API afterward that the engagement's real progress (findings
  count, done/pending status per item) was unaffected by the patch.

**Verified:**
- `_validate_tool_references()` passes cleanly on the current checklist;
  confirmed it actually catches a regression by temporarily reintroducing
  a fake unregistered tool name and checking the `AssertionError` fires
  with a clear message.
- `./venv/bin/python -c "from backend.main import app"` and `from
  oculus.cli import build_checklist` both import without error.
- Curled the live (already-running, `--reload`) backend's `/api/tools`
  and confirmed `wappalyzer-cli` isn't there and `nuclei` is.
- Curled `/api/engagements/25f27157` after the data migration and
  confirmed the 4 fields now read correctly while findings count and
  per-item done/pending status matched what they were before the patch.

**Next steps for the next agent:**
1. `_validate_tool_references()` only checks that a listed tool *exists*
   — it doesn't (and can't, statically) verify the tool's actual
   `build_command()` genuinely performs the specific sub-test a
   checklist item describes (e.g. `WSTG-CONF-06`/Test HTTP Methods lists
   `httpx`, which probes headers but doesn't itself enumerate allowed
   HTTP methods the way `nmap`'s `http-methods` NSE script does — nmap
   already covers the item for real, httpx's presence there is just a
   generically-useful secondary probe, not wrong, just not load-bearing
   for that specific item). Worth a closer per-item pass if this
   becomes a recurring source of confusion.
2. If more engagements exist on other machines/other testers' setups,
   they'd have the same 4 stale fields baked in from before this fix —
   the migration here only touched the one engagement file present on
   this dev machine.

---

## 2026-08-25 — Fix: 7 more tools hardcoded https:// against a plain-HTTP target

**Done (user pasted a real failure): running `nikto` against this repo's
own lab target `192.168.2.11` (plain HTTP, no TLS on port 443) failed —
`nikto -h https://192.168.2.11 ...` → "Unable to connect to
192.168.2.11:443", because `nikto_tool.py` hardcoded `https://` instead
of using `base_url()`, the scheme-detection helper added a while back
specifically to fix this exact bug in ffuf/gobuster (bare IPv4 → http://,
bare hostname → https://, explicit scheme always respected).**
- Grepped every tool wrapper for the same `f"https://{self.target}"`
  pattern in `build_command()` (not just mock-output text, which doesn't
  matter) and found it wasn't just nikto — same bug in `gowitness`,
  `arjun`, `katana`, `nuclei`, `wafw00f`, and `wpscan`. Fixed all 7 to
  call `base_url(self.target)` instead.
- Deliberately left `testssl_tool.py`'s hardcoded `https://` alone —
  testing TLS/SSL configuration is testssl's entire purpose, so forcing
  https there is correct, not a bug (a target with no TLS at all
  genuinely has nothing for it to test).
- `httpx_tool.py` and `whatweb_tool.py` already passed the bare target
  through untouched (both tools auto-detect scheme themselves) — no
  change needed, confirmed by reading their `build_command()`.

**Verified:**
- `python3 -c` import + `build_command()` check across all 7 fixed
  wrappers against both `192.168.2.11` (→ `http://`) and `example.com`
  (→ `https://`) — correct in both directions for all of them.
- Ran the exact previously-failing command for real:
  `nikto -h http://192.168.2.11 -Tuning 1234567890 -nointeractive
  -Display 1` — connected successfully this time (`Target Port: 80`,
  real findings like "Apache/2.4.52 appears to be outdated").
- Curled the backend's own `/api/tools/nikto/command?target=
  192.168.2.11` preview endpoint — confirms it now returns
  `http://192.168.2.11`, matching what the Run Tool dialog would show.
- Dumped `build_command()` for every tool in `TOOL_REGISTRY` against
  `192.168.2.11` in one pass — every HTTP-based tool now agrees
  (`http://`), `testssl` is the one deliberate exception (`https://`),
  and non-HTTP tools (`amass`, `dnsx`, `nmap`, `subfinder`) are
  unaffected as expected.

**Next steps for the next agent:**
1. This class of bug (a wrapper re-deriving its own URL instead of
   calling `base_url()`) has now recurred 3 times across this project's
   life (ffuf/gobuster, then this batch of 7). If a new tool wrapper
   gets added, default to `base_url(self.target)` for anything that
   takes a URL rather than writing `f"https://{self.target}"` again.
2. Ran into this live: real `nikto` v2.6.1 (installed via brew) prints
   6-digit bracketed IDs like `[600050]`/`[013587]` instead of the
   `OSVDB-NNNN` format this repo's `nikto_tool.py` mock output still
   uses (nikto deprecated OSVDB IDs at some point). The output
   highlighter added last session only recognizes `OSVDB-\d+`, so a real
   nikto run's own finding IDs currently don't get the bold-magenta
   treatment CVEs/OSVDB IDs get. Not fixed this session (out of scope —
   this session was about the connection failure) but worth a follow-up:
   either update `HighlightedOutput.tsx` to also match nikto's newer
   `\[\d{6}\]` ID format, or update the bundled `nikto_tool.py` mock
   output to match the real tool's current ID scheme (or both).

---

## 2026-08-19 (9) — Highlight more "this matters" signal in tool output

**Done (user request: "can you highlight output each output for
necssary such as ports are opened especialy nmap or anything that maybe
important"):**
- `HighlightedOutput.tsx` (already highlighted URLs, HTTP status codes,
  `[severity]` tags, CVEs, `[+]`/`[-]`, and `⚠`) gets 4 new token types:
  - **nmap port/state lines** (`80/tcp   open  http`): the state word is
    colored by how interesting it is — `open` bold green, `open|filtered`
    yellow, `closed`/`filtered` dim gray — leaving the port/protocol and
    service name in the default color. Matched as one combined token
    (`\d{1,5}/(?:tcp|udp)\s+(?:open|filtered|...)`) rather than a bare
    "open"/"closed" word match, specifically to avoid false-positives on
    those common English words appearing elsewhere in unrelated output.
  - **`[!]`** (wpscan's own "notable finding" marker) — bold red, same
    weight as a bracket severity tag.
  - **`OSVDB-NNNN`** (nikto's per-finding IDs) — bold magenta, same
    treatment as a CVE ID.
  - **Risk keywords** — `vulnerable`, `outdated`, `exposed`,
    `misconfigured`, `risky`, `sensitive`, `weak`, `takeover` (whole-word,
    case-insensitive) — bold orange. Picked from words that actually
    appear in this repo's own tool wrappers' real/mock output (nikto's
    "OSVDB-877: ... vulnerable to XST", "nginx ... appears to be
    outdated", nikto's "Potentially risky methods") rather than an
    arbitrary keyword list.
  - **Bare IPv4 addresses** — cyan, same treatment as a URL (nmap/nikto
    both print the resolved IP early in their output; useful to have it
    pop visually next to the hostname).

**Verified:**
- Unit-style check via a standalone Node script exercising the raw
  regex against real strings pulled from `nmap_tool.py`'s and
  `nikto_tool.py`'s own `mock_output()` — confirmed `80/tcp   open`
  matches as one token, `53/tcp   open|filtered domain` matches
  `53/tcp   open|filtered`, `25/tcp   closed smtp` matches `25/tcp
  closed`, `OSVDB-6694` and `outdated` and `93.184.216.34` all matched
  as their own single tokens with nothing else in each line spuriously
  matching.
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser verification: created a throwaway engagement, wrote real
  `NmapTool`/`NiktoTool` `mock_output()` text directly into two checklist
  items' `tool_outputs` (bypassing an actual scan — deterministic,
  known-content output to check rendering against), reloaded each item
  in a real browser. Confirmed: `open` states render bold green,
  `open|filtered`/`closed` render dimmer, `93.184.216.34` and other IPs
  render cyan, `risky`/`outdated` render bold orange, `OSVDB-3092`
  renders bold magenta — all inside the same "Tool output" panel used by
  both the live WebSocket stream (`RunToolDialog`) and the persisted
  past-output view (`ItemDetail`), since both already shared this one
  highlighting component. Deleted the throwaway engagement after.

**Next steps for the next agent:**
1. The risk-keyword list is deliberately small and literal (no stemming,
   e.g. "vulnerability" won't match "vulnerable") — extend it if a real
   engagement surfaces another tool's own "this is bad" wording that
   isn't caught.
2. `gowitness`/screenshot-based tools and `wafw00f` weren't specifically
   considered here since their `mock_output()` didn't have an obvious
   "important line" shape to target — worth a look if their real output
   turns out to need it once used against a real target.

---

## 2026-08-19 (8) — Search wordlists on Enter, not per keystroke

**Done (user report: "when search implement wait for enter first because
it lag from when input each character then it search"):**
- `WordlistPickerDialog.tsx`: split the search box's live-typed text
  (`queryInput`) from the committed value that actually filters
  (`query`). Filtering (and its re-render across every category's cards)
  now only runs when the tester presses Enter or clicks the search icon
  — not on every keystroke. Clearing the box back to empty is the one
  exception: that's treated as "show everything again" and applies
  instantly, no Enter needed, since it's cheap (no filtering) and
  waiting on it would feel like a stuck search box.
- Placeholder text updated to "Search wordlists… (press Enter)" so the
  behavior is discoverable without a tooltip.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Browser E2E: typed "backup" character-by-character into the box and
  confirmed the list stayed unfiltered (all 6 bundled cards, including
  `admin.txt`, still visible) until Enter was pressed, at which point it
  correctly narrowed to just `backup.txt`; then cleared the box (no
  Enter) and confirmed `admin.txt` reappeared immediately. Zero console
  errors.

---

## 2026-08-19 (7) — Collapse categories with more than 6 wordlists

**Done (user request: "each category if there are more 6 wordlists
implement it can show samples and collapses"):**
- `WordlistPickerDialog.tsx`: each category now renders at most
  `SAMPLE_SIZE = 6` cards by default, with a "Show all N" / "Show less"
  toggle button (chevron icon, per-category expand state via a `Set` of
  expanded category names) when a group has more than 6. A search query
  bypasses the cap entirely for any group with matches — narrowing to
  "admin" and getting back 2 results shouldn't then hide one of them
  behind a second click.

**Verified:**
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Built a fake wordlist tree with a 9-file category (`/tmp/fake_wl2/
  seclists/Discovery/Web-Content/list1.txt`...`list9.txt`), rebuilt +
  restarted the frontend, browser E2E: opened the picker, confirmed
  "SecLists/Discovery" showed exactly 6 cards + a "Show all 9" button,
  clicked it, confirmed all 9 rendered + button changed to "Show less",
  clicked that, confirmed it collapsed back to 6. Zero console errors.
  Cleaned up the fake tree and reset the wordlist-dir config after.

---

## 2026-08-19 (6) — Wordlist picker dialog + full Kali/SecLists discovery

**Done (user report: "the wordlists still not all wordlists ... implement
the select wordlists button that show dialog popup can select card
wordlists, each category and recommendation by follow path default by
Kali linux wordlists and seclist" — pasted their real Kali
`/usr/share/wordlists` and `seclists/` layout):**
- `oculus/wordlists.py` discovery rewrite:
  - `_all_candidates()` walks every search root once (was 3x — one rglob
    per extension) matching both `*.txt` and `*.lst` (Kali's own
    `nmap.lst`/`john.lst` use `.lst`, previously invisible entirely).
  - `discover_wordlists()`'s old cap was 150 with a single flat priority
    sort — good for the "which wordlist should ffuf use by default"
    question, bad for "show me everything" since anything outside the
    directory-brute-force keywords could be squeezed out. Left this
    function for `default_wordlist()`'s use (raised limit to 500) but
    added a separate `discover_wordlists_grouped()` for browsing that
    is **not** capped or keyword-filtered — every password list, username
    list, fuzzing payload, etc. is reachable.
  - `_category_for()` groups the way the user's own `ls` output reads: a
    SecLists checkout (`.../seclists/<Discovery|Fuzzing|Passwords|
    Pattern-Matching|Payloads|Usernames|Web-Shells|Miscellaneous>`) is
    broken out by its own top-level folder; sibling Kali packages (dirb,
    dirbuster, wfuzz, legion, fern-wifi, metasploit, ...) group by their
    own directory name; the bundled bare files (rockyou.txt,
    fasttrack.txt, ...) land in "Other". oculus's own bundled wordlists
    (added last session) always appear too, under "Bundled (built-in)"
    — so the dialog is never empty on a machine with no system wordlists.
  - A group is flagged `recommended` if its category name matches the
    current test's category keywords, OR — since a category name alone
    like "SecLists/Discovery" is too broad to contain "admin" — if any
    wordlist *inside* it does (e.g. `.../Discovery/Web-Content/
    admin-panels.txt` correctly flags `SecLists/Discovery` as
    recommended for the admin-interfaces test).
- `backend/routers/tools.py`: new `GET /api/tools/wordlists/grouped
  ?item_id=...` returning `{recommended_category, recommended_category_
  label, groups: [{category, recommended, wordlists}]}`.
- New `frontend/src/components/WordlistPickerDialog.tsx`: a dialog with a
  search box and each category rendered as a labeled section of clickable
  cards (filename, full path, a ★ + green label on the recommended
  group(s)), plus a "Use tool default" card. Replaces the old
  `Autocomplete` dropdown in `RunToolDialog.tsx`, which is now a "Select
  wordlist" button (`Wordlist: <filename>`) that opens it.
- `applyWordlist()` in `RunToolDialog.tsx`: picking "Use tool default"
  now correctly reverts the command's `-w` flag to whatever path was in
  the original backend-recommended preview (`defaultCommand`), instead of
  leaving a previously-picked path stuck in the command with no way back
  short of the full "reset command" button.

**Verified:**
- Built a fake Kali-shaped tree at `/tmp/fake_wordlists`
  (`dirb/`, `dirbuster/`, `wfuzz/`, `seclists/Discovery/Web-Content/`,
  `seclists/Passwords/`, `seclists/Fuzzing/`, `seclists/Usernames/`,
  plus root-level `rockyou.txt`/`nmap.lst`) matching exactly the
  structure the user pasted, pointed `OCULUS_WORDLIST_DIR` at it via the
  config endpoint, and curled `/api/tools/wordlists/grouped` — confirmed
  9 groups exactly matching that layout (`SecLists/Discovery`,
  `SecLists/Fuzzing`, `SecLists/Passwords`, `SecLists/Usernames`, `dirb`,
  `dirbuster`, `wfuzz`, `Other`, `Bundled (built-in)`), with
  `SecLists/Discovery` and `Bundled (built-in)` both correctly flagged
  `recommended: true` for an admin-interfaces item (matching the nested
  `admin-panels.txt` file). Removed the fake tree and reset config after.
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser E2E via a throwaway Playwright script (deleted after use):
  rebuilt and restarted the production frontend (it was serving a stale
  build from before this session's changes), opened "Enumerate Admin
  Interfaces" → Run Tool → ffuf → clicked the new "Select wordlist"
  button → dialog showed "Bundled (built-in)" with 6 cards, `admin.txt`
  starred/green as recommended → typed "admin" in the search box →
  confirmed it filtered to just the one matching card → clicked it →
  confirmed the button now reads "Wordlist: admin.txt" and the command
  field's `-w` flag updated to the real `admin.txt` path. Zero console
  errors. Screenshots confirmed clean rendering (one screenshot taken
  mid dialog-open fade transition briefly showed overlapping text from
  both stacked dialogs — a screenshot-timing artifact, not a real bug;
  a second screenshot 300ms later, and every other checkpoint, rendered
  cleanly with no overlap).

**Next steps for the next agent:**
1. This was verified against a *simulated* Kali tree on macOS, not a
   real Kali box — the user should confirm the picker looks right
   against their actual `/usr/share/wordlists/seclists` once they pull
   this, since a real install's file count is much larger than the
   ~10-file fake tree used here (performance of `discover_wordlists_
   grouped()`'s full unbounded scan on a real multi-thousand-file
   SecLists install hasn't been measured — if it's noticeably slow,
   consider caching the scan result for the process lifetime, or lazily
   loading each category's file list only when a card section is
   expanded, rather than eagerly scanning everything up front).
2. Only `ffuf`/`gobuster` (`uses_wordlist = True`) surface this picker —
   confirmed no other tool wrapper (`wpscan`, `hydra`, etc. — hydra isn't
   wrapped at all yet) currently takes a `-w`/wordlist flag, so there's
   nothing else silently stuck on a bundled default; if a
   password-brute-force tool gets wrapped later, wire it through the same
   `uses_wordlist`/`recommend_wordlist()` path rather than inventing a
   separate mechanism.
3. `discover_wordlists()` (the older, capped/keyword-sorted function used
   by `default_wordlist()` for ffuf/gobuster's *default* preview command)
   and `discover_wordlists_grouped()` (used by the picker, uncapped) now
   both walk the filesystem independently on every call with no caching —
   fine for a single-user local tool but worth revisiting if this ever
   needs to serve concurrent requests against a huge wordlist directory.

---

## 2026-08-19 (5) — Per-test wordlist recommendations

**Done (user request: "each testing can you recommend wordlists for that
test, such as ffuf for search endpoint use that wordlist"):**
- Added 5 new bundled wordlists under `oculus/data/wordlists/`:
  `admin.txt` (~55 admin-panel paths), `api.txt` (~60 API/GraphQL/Swagger
  paths), `backup.txt` (~65 backup/dump file names), `extensions.txt`
  (~50 file-extension-handling probes like `index.php.bak`, `.git/config`),
  `metafiles.txt` (~30 well-known metafiles like `robots.txt`,
  `.well-known/security.txt`). `common.txt` (existing, general-purpose)
  is reused as the "common" category.
- `oculus/checklist.py`: new `WORDLIST_CATEGORY` dict mapping specific
  WSTG checklist item IDs to a category (e.g. `WSTG-CONF-05` "Enumerate
  Admin Interfaces" → `"admin"`, `WSTG-CONF-04` "Review Old Backup and
  Unreferenced Files" → `"backup"`, `WSTG-INFO-06` "Identify Application
  Entry Points" → `"api"`), plus `CATEGORY_LABELS` for the human-readable
  hint text. Only 6 items are mapped — everything else (including any
  tester-added custom item) falls through to the plain default wordlist,
  unchanged from before.
- `oculus/wordlists.py`: new `recommend_wordlist(category)` — tries a
  *discovered* wordlist whose path matches the category's keywords first
  (so a real SecLists install's own admin/API/backup lists win over the
  bundled ones), then falls back to the bundled `<category>.txt`, then to
  `default_wordlist()` if neither exists. `category=None` (unmapped item)
  goes straight to `default_wordlist()` — no behavior change for the
  other ~40 checklist items.
- `backend/routers/tools.py` `GET /api/tools/{tool}/command`: takes a new
  optional `item_id` query param. When the tool `uses_wordlist` and the
  item has a mapped category, swaps the `-w <path>` flag in the previewed
  command for the recommended wordlist and returns
  `recommended_category`/`recommended_category_label` in the response.
  Deliberately gated on `tool_cls.uses_wordlist` — caught in
  self-review that an earlier version leaked a `recommended_category` for
  `nmap` (which doesn't take a wordlist at all) when previewed against an
  admin-interfaces item; fixed before verifying further.
- Frontend (`RunToolDialog.tsx`, `lib/api.ts`): passes the current
  checklist item's ID through `previewCommand`, shows a green "Using a
  wordlist recommended for this test — **\<label\>**" hint above the
  command box when a recommendation applies and the tester hasn't
  manually picked a different wordlist from the picker.

**Verified:**
- Backend: curled `/api/tools/ffuf/command` for each of the 6 mapped
  item IDs — confirmed `admin.txt`, `backup.txt`, `api.txt`, etc. each
  appear in the returned command's `-w` flag, and `recommended_category`
  is `null` for an unmapped item and for `nmap` (non-wordlist tool)
  regardless of item.
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser E2E via a throwaway Playwright script (deleted after use,
  not committed): created a real engagement, opened "Enumerate Admin
  Interfaces" → Run Tool → selected `ffuf` → confirmed the green
  recommendation hint appeared and the previewed command contained
  `admin.txt`; repeated for "Review Old Backup and Unreferenced Files"
  (`backup.txt`) and "Enumerate Applications on Web Server" (`common`
  category, generic hint). Zero console errors across all three.
  Screenshots visually confirmed correct rendering (green outlined
  Alert, correct category label, no layout issues) before cleanup.

**Next steps for the next agent:**
1. Only 6 of ~46 checklist items have a wordlist category mapped —
   consider extending `WORDLIST_CATEGORY` to more items (e.g. a
   subdomain-takeover-focused list for `WSTG-CONF-09`) as more bundled
   wordlists get added.
2. The recommendation only kicks in for the *default* preview — if a
   tester has already picked a wordlist from the Autocomplete picker,
   their choice correctly takes precedence (hint is hidden), but there's
   no way to say "actually, use the recommended one" again short of
   clearing the picker manually.
3. Bundled wordlists are hand-curated and modest in size (30-65 entries
   each) — fine as a sane default, but a tester with a real SecLists
   install will usually get a bigger, better-matched discovered list
   automatically (see `recommend_wordlist`'s discovery-first order).

---

## 2026-08-19 (4) — Fix: wordlist discovery capped at 25 and alphabetical

**Done (user report on a real Kali box: "found only 25, not found
endpoint or directory wordlists"):**
- Root cause #1: `discover_wordlists(limit: int = 25)` — the number in
  the report matched the hardcoded default exactly.
- Root cause #2, the more important one: results were plain alphabetical
  (`sorted(root.rglob("*.txt"))`), and the function returned as soon as it
  hit the limit. A real SecLists install (what Kali's `seclists` apt
  package gives you) has 50+ categories; alphabetically "Discovery/DNS"
  and "Discovery/Infrastructure" sort ahead of "Discovery/Web-Content" —
  the one actually relevant to ffuf/gobuster's directory/file
  brute-forcing. A big DNS wordlist category alone could exhaust the
  entire limit before Web-Content was ever reached, matching exactly what
  was reported ("not found endpoint or directory wordlists").
- Fixed both: raised the default limit to 150, and added a
  `_DIR_BRUTEFORCE_KEYWORDS`-based priority sort (`web-content`,
  `discovery`, `dirb`, `dirbuster`, `raft`, `directory-list`, `common.txt`)
  so directory/file-relevant wordlists surface first regardless of where
  they fall alphabetically — applied to both `discover_wordlists()` (the
  picker's list) and `default_wordlist()`'s configured-directory case
  (previously also just alphabetically-first, could hand ffuf/gobuster a
  random unrelated wordlist as their "default").
- Upgraded the Run Tool dialog's wordlist picker from a plain `<Select>`
  to an `Autocomplete` (`RunToolDialog.tsx`) — with the cap now much
  higher, a searchable/type-to-filter control is what actually makes a
  larger result set usable rather than just scrollable.

**Verified:** built a fake SecLists-shaped tree (30 `Discovery/DNS/*.txt`
files sorted alphabetically ahead of 3 `Discovery/Web-Content/*.txt`
files) and confirmed: with the *old* `limit=25` explicitly passed, all 3
Web-Content wordlists now appear in the first 25 results (would have been
0 before this fix); `default_wordlist()` against that same tree resolves
to `Web-Content/common.txt`, not a DNS file. Then verified in a live
browser against the real running app (via the Settings dialog pointed at
the fake tree): the picker's initial dropdown shows Web-Content entries
immediately after "tool default" and before any DNS entries; typing
"raft" correctly filters to the one matching wordlist. `tsc`/`eslint`/
`next build` clean.

**Next steps for the next agent:**
1. The priority keyword list is a heuristic, not exhaustive — if another
   wordlist naming convention turns out to matter (e.g. a different
   pentesting distro's layout), extend `_DIR_BRUTEFORCE_KEYWORDS` in
   `oculus/wordlists.py` rather than reworking the sort mechanism.
2. `limit=150` is still a cap, chosen to keep the Autocomplete responsive
   — a truly enormous SecLists install could still have Web-Content
   entries beyond position 150 if there happen to be 150+ higher-priority
   matches ahead of them. Not expected in practice (real Web-Content
   directories have well under 150 files), but worth knowing if someone
   reports "still missing a specific wordlist" again.

---

## 2026-08-19 (3) — Settings dialog: configure wordlist dir from the web UI

**Done (user request: "ffuf can select wordlists and user can config
environment wordlists path" — the previous session's `OCULUS_WORDLIST_DIR`
env var required a backend restart to change, not something settable from
the running app):**
- New `oculus/config.py` — persisted app-wide settings
  (`~/.oculus/config.json`, separate from `~/.oculus/engagements/`).
  Currently just `wordlist_dir`; designed to hold more settings later.
- `wordlists.py`'s `_configured_root()` now checks the persisted config
  first, then `OCULUS_WORDLIST_DIR` — config wins if both are set, since
  it's the more explicit, most-recently-set value.
- New `GET /api/config` / `PUT /api/config/wordlist-dir` (backend/routers/
  config.py) — the PUT validates the path actually exists before
  persisting (400 with a real message if not) and returns the resulting
  effective default + wordlist count.
- New `SettingsDialog.tsx`, opened via a gear icon in `NavBar.tsx` (so
  it's reachable from every page) — set/clear the wordlist directory, see
  the effective default and how many wordlists were found, inline error
  on an invalid path.
- Improved `lib/api.ts`'s shared `request()` to surface FastAPI's actual
  `{"detail": "..."}` error message instead of dumping the raw response
  body — used by the Settings dialog's invalid-path error, but benefits
  every other API call's error handling too.
- The existing Run Tool dialog wordlist picker (`RunToolDialog.tsx`)
  needed no changes — it already calls `/api/tools/wordlists`, which now
  automatically reflects whatever's configured via Settings.

**Verified:** full browser flow — opened Settings, tried an invalid path
(rejected with the real "Path does not exist: ..." message, not a generic
500), saved a valid path (bundled wordlist dir), confirmed the wordlist
picker in the Run Tool dialog then showed a real, selectable wordlist
entry beyond just "tool default", confirmed the command preview picked up
the new default. Confirmed persistence survives independently of any
single request (backed by a file, not in-memory state) and reset cleanly
back to null after the test. `tsc`/`eslint`/`next build` clean; all 16
tools still `build_command()` without error; backend imports clean.

**Next steps for the next agent:**
1. If more app-wide settings get added later, extend `oculus/config.py`'s
   get/set functions the same way `wordlist_dir` was done — one JSON file,
   simple key access, no need for a heavier settings framework yet.
2. The Settings dialog only covers the wordlist directory right now —
   natural next candidates if the app grows: default engagement
   scope-notes template, tool timeout overrides (currently only
   per-tool-class `timeout_seconds`/`get_timeout()`, not user-configurable
   without editing code).

---

## 2026-08-19 (2) — Fix: unhandled backend-fetch rejections crashed pages

**Done (user report: Next.js dev error overlay, "Runtime TypeError:
Failed to fetch" at `api.ts:18` via `listTools` in the engagement detail
page's `useEffect`):**
- Backend was actually up and healthy when investigated (`curl` succeeded
  immediately) — this was transient (page loaded before the backend was
  ready, or hit uvicorn `--reload`'s brief restart window), not a
  standing outage.
- Real bug found and fixed: `api.getEngagement(id)` in that same
  `useEffect` has a `.catch()` and degrades gracefully ("Engagement not
  found."); the `api.listTools()` call two lines below it did not — any
  transient fetch failure there was an unhandled promise rejection, which
  Next's dev overlay turns into a full-page crash instead of a graceful
  degrade. Grepped for the same pattern elsewhere and found two more in
  `RunToolDialog.tsx` (`previewCommand`, `listWordlists`). All three now
  have `.catch()` — `listTools`/`previewCommand` show a toast error,
  `listWordlists` fails silently to an empty list (non-critical, it's
  just the wordlist picker).
- While adding the `listTools` catch, caught a second real bug before it
  shipped: `useToast()` returned a brand-new object (new function
  references) on every render, so adding `toast` to that `useEffect`'s
  dependency array — needed since the `.catch()` callback calls
  `toast.error(...)` — would have caused the effect to refire every
  render (an infinite-ish re-fetch loop). Fixed `useToast()` itself with
  `useMemo` keyed on the context value (which is already stable via the
  provider's `useCallback`), so `toast` is now safe to put in any
  dependency array. No other component currently does this, but it was a
  latent trap.

**Verified:** stopped the backend, loaded the engagement detail page
against the live dev server (Playwright, since a second `next dev`
instance can't run from the same project dir to test in isolation) —
confirmed zero uncaught page errors, no crash, and the exact intended
graceful degrade (an "Engagement not found." message plus two toast
errors, one per fixed call site). Restarted the backend and confirmed
recovery. `tsc`/`eslint`/`next build` all clean.

**Next steps for the next agent:**
1. If more `api.*().then(...)` call sites get added without a `.catch()`,
   the same crash class can recur — this is a "did I forget a catch"
   pattern to watch for in review, not something structurally prevented
   (the `request()` helper in `lib/api.ts` still just throws on failure,
   by design, so every call site is responsible for its own handling).
2. `useToast()` is now memoized/stable — safe to add to dependency arrays
   going forward without re-deriving this from scratch.

---

## 2026-08-19 — Configurable wordlist dir + make ffuf/gobuster actually work

**Done (user request: configurable wordlist folder + "implement ffuf for
real ffuf"):**
- New `OCULUS_WORDLIST_DIR` env var (`oculus/wordlists.py`) — point it
  at a directory (searched recursively for `*.txt`, also folded into the
  wordlist picker's search) or a specific file, and it's used first.
- New `default_wordlist()` resolver: `OCULUS_WORDLIST_DIR` → first
  discovered wordlist in the existing common-location scan → a wordlist
  now bundled with oculus itself (`oculus/data/wordlists/common.txt`,
  ~220 common paths, added to `package-data` in `pyproject.toml` so it
  survives a non-editable install too).
- **Root cause of "ffuf not really working" #1**: `ffuf_tool.py` and
  `gobuster_tool.py` hardcoded `-w /usr/share/wordlists/dirb/common.txt`
  — a Kali/Debian package path that doesn't exist on macOS or a bare
  Linux box. Every real run failed immediately with "no such file or
  directory". Both now call `default_wordlist()` instead.
- **Root cause #2, found while verifying the above**: both also hardcoded
  `https://{target}` regardless of what the target actually serves. Against
  an HTTP-only target (very common for internal/lab IPs — reproduced with
  this repo's own `192.168.2.11` test target) every single request failed
  to connect, and ffuf reported "success" with zero results — silently
  indistinguishable from a real empty scan. Added `base_url()` to
  `oculus/tools/base.py`: respects an explicit scheme if the tester typed
  one, defaults bare IPv4 targets to `http://` (internal targets are
  usually plain HTTP), bare hostnames to `https://` (still the common case
  for a real domain). Applied to `ffuf`/`gobuster` only, per the request's
  explicit scope — **9 other tools have the exact same hardcoded-https://
  pattern** (arjun, gowitness, katana, wafw00f, nikto, nuclei, wpscan,
  testssl — grep `f"https://{self.target}` across `oculus/tools/*.py`)
  and would benefit from the same `base_url()` fix; deliberately not
  touched this session to stay scoped to what was asked.

**Verified:** real `ffuf` and `gobuster` runs (via the wrapper classes
directly, then again through the actual backend WebSocket path) against
the same `192.168.2.11` target used in earlier bug reports — both now
return real results (`.htaccess`, `.htpasswd`, `assets`,
`server-status`, `vendor`) instead of silently succeeding with nothing.
Confirmed `OCULUS_WORDLIST_DIR` resolves correctly for both a directory
and a direct file path. All 16 tools still `build_command()` without
error; backend imports clean; CLI still works.

**Next steps for the next agent:**
1. Apply `base_url()` to the other 9 tools listed above if/when someone
   hits the same silent-empty-scan symptom with one of them against an
   HTTP-only target — same fix, just needs applying + verifying per tool.
2. If a config file (vs. just env vars) is ever wanted for wordlist dir
   or other settings, `default_wordlist()`/`_search_roots()` in
   `wordlists.py` is the place to extend — keep the env var as the
   override-of-first-resort either way, it's cheap and scriptable.

---

## 2026-08-18 (8) — ⚠ UNRESOLVED: amass v5.1.1 installed is architecturally incompatible

**Found while proactively auditing other tool wrappers' flags after the
httpx `-response-header` bug** (below) — checked every installed tool's
real `--help`/`-h` output against what each wrapper's `build_command()`
actually sends, on the theory that a hallucinated-flag bug might not be
unique to httpx. `nuclei`, `wpscan`, `subfinder`, `ffuf`, `gobuster`,
`nmap` all check out clean — every flag `oculus/tools/*_tool.py` uses for
those exists in the installed binary's real help output.

**`amass` does not check out, and it's bigger than a bad flag:**
- `amass -h` (top-level) shows this installed version is v5.1.1, with a
  completely restructured CLI: `amass [assoc|engine|enum|subs|track|viz]`.
  This is OWASP Amass's new "OAM" (Open Asset Model) architecture — a
  significant rewrite from the v3/v4-era single-shot CLI our wrapper
  (`oculus/tools/amass_tool.py`, still sending
  `amass enum -passive -d <target> -timeout <N>`) assumes.
- `amass enum -h` (and even `amass enum` with no arguments at all) **hangs
  indefinitely** — confirmed with `timeout 10s`, exit 124, zero output,
  even with stdin explicitly redirected from `/dev/null` to rule out a
  stdin-read block. It's not printing a usage error and exiting the way
  every other CLI tool here does; something in v5's `enum` subcommand
  blocks waiting on infrastructure that isn't there — almost certainly the
  new `engine` subcommand (a separate long-running backend/database
  process this architecture expects to already be running).
- **Practical effect:** the `-timeout` fix from entry (4) below is
  irrelevant here — even with a correct timeout value, a real `amass enum`
  invocation from this app will very likely just hang until our own
  subprocess timeout kills it (660s for a full scan), producing a
  `[TIMEOUT]` result with zero output every time, on top of tying up a
  backend worker for 11 minutes for nothing.

**Deliberately not fixed in this session** — reworking the amass
integration for v5's engine architecture needs actual research into how
`amass engine`/`enum` are meant to be used together now (does the engine
need to be started as a persistent sidecar service? per-scan? is there a
simpler one-shot mode this version still supports that I haven't found?),
which is a real investigation, not a quick patch, and not what was in
scope for the reported bug (httpx's flag).

**Next steps for the next agent:**
1. Read OWASP Amass v5's actual docs/changelog (not memory — this project
   has already been burned twice by hallucinated/stale flag names; verify
   against the real `amass --help` tree and github.com/owasp-amass/amass
   docs before writing any fix).
2. Options once the right invocation is known: (a) rewrite
   `amass_tool.py`'s `build_command()` for the new CLI if there's still a
   one-shot mode, (b) special-case amass to manage an `engine` sidecar
   process if that's required, or (c) if v5 fundamentally doesn't support
   a simple one-shot passive enum anymore, consider whether amass should
   stay in `TOOL_REGISTRY` at all vs. being documented as "install an
   older v3/v4 release for this to work."
3. Until fixed, expect any real (non-simulated) amass run through this app
   to hang for the full timeout and return nothing — this is a known
   issue, not a new bug report waiting to happen.

---

## 2026-08-18 (7) — Fix: httpx's `-response-header` flag doesn't exist

**Done (user report: `httpx ... -response-header ...` → "flag provided but
not defined: -response-header"):**
- Confirmed by checking real `httpx -h` output (v1.10.0): `-response-header`
  has never been a valid flag in any httpx release. It was a made-up name
  in `oculus/tools/httpx_tool.py`'s full-mode `build_command()` that
  happened to never get caught because the app's own simulated-fallback
  path never actually invokes the real binary's flag parser.
- The real flag for header info is `-include-response-header`/`-irh`, but
  it only works with `-json` output ("(-json only)" per httpx's own help)
  — switching to JSON would change the whole output shape and require
  updating `mock_output()` and `findings_extractor.py`'s `extract_httpx()`
  to match, which is a bigger change than this fix warrants. Used `-server`
  instead (real flag, works in the default plain-text mode, still
  surfaces something header-related — the Server header).
- Noted in passing, not fixed here: `extract_httpx()` parses patterns
  ("⚠ Missing headers:", "Set-Cookie: ... (missing Secure...)") that only
  ever appear in `mock_output()`'s simulated text — real httpx output
  (plain-text or JSON) never produces that shape, so finding extraction
  for httpx effectively only fires on simulated runs today, not real ones.
  Pre-existing, unrelated to this bug; flagging for whoever picks up
  "make finding extraction work on real tool output" next.

**Verified:** reproduced the exact reported error with the old flag
(`exit 2`, "flag provided but not defined"); confirmed the corrected
command runs cleanly against a real target (exit 0, real title/status/
server/tech-detect output); ran it through the actual app path end-to-end
(WebSocket `/ws/engagements/.../run`, real target `192.168.2.11`) —
`success: true`, real output streamed, no simulated fallback triggered.

**Next steps for the next agent:**
1. If httpx's finding extraction needs to work on real output (see the
   note above), that's a `findings_extractor.py` rewrite against actual
   httpx output shape (plain-text or `-json`), not a quick patch.
2. Worth doing eventually: audit every other tool wrapper's flags against
   its actually-installed binary's `-h` output the same way this was
   caught, rather than trusting flag names from memory — this exact class
   of bug (a flag that looks plausible but was never real) could exist
   elsewhere and would only surface when someone runs the tool for real.

---

## 2026-08-18 (6) — Warn before running domain-only tools against an IP target

**Done (user report: `subfinder -d 192.168.2.11 -silent -all` "shows no
response but success"):**
- Confirmed this is correct, expected behavior of subfinder itself, not a
  bug — subdomain enumeration is meaningless against a bare IP (especially
  a private one with no public DNS presence). It queries its sources,
  finds nothing to enumerate, and exits 0. Reproduced locally to confirm
  before concluding this.
- Real gap fixed: nothing told the tester *why* it would return nothing
  before they ran it. Added `BaseTool.domain_only: bool` (new attribute,
  `oculus/tools/base.py`), set `True` on `subfinder`, `amass`, `dnsx` —
  the three tools that structurally require a domain name. Exposed via
  `/api/tools` (`domain_only` field) and surfaced as a warning `Alert` in
  `RunToolDialog.tsx` when the selected tool is domain-only and the
  engagement's target looks like an IP address (new `lib/target.ts` ->
  `isIpAddress()`, a UI heuristic, not a strict validator — handles IPv4
  with an optional `:port` and a basic IPv6 check).
- Deliberately did *not* add this warning to `ChecklistItemDialog.tsx`'s
  tool picker — that dialog associates tools with a checklist item in the
  abstract and doesn't receive the engagement's `target` prop, so the
  warning wouldn't be actionable there. It only belongs in `RunToolDialog`,
  where an actual run against a specific target happens.

**Verified:** reproduced the exact reported command locally (real
`subfinder` binary, exit 0, empty output — confirms it's tool behavior,
not our bug). Backend: `/api/tools` correctly reports
`domain_only: true` for amass/dnsx/subfinder and `false` for nmap.
Browser: recreated the user's exact scenario (engagement target
`192.168.2.11`, WSTG-INFO-01 which offers amass + subfinder) — warning
renders correctly for both tools, zero console errors, `tsc`/`eslint`/
`next build` clean.

**Next steps for the next agent:**
1. If a domain-only tool ever gets added beyond these three, remember to
   set `domain_only = True` on it — there's no other enforcement.
2. `isIpAddress()` is intentionally a loose heuristic for a UI hint, not a
   real IP validator — don't repurpose it for anything that needs to be
   correct (e.g. backend validation).

---

## 2026-08-18 (5) — Full theme reskin: terminal/hacker-console, green accent

**Done (per explicit user request + a reference screenshot of
binaryjiujitsu.com — confirmed scope via AskUserQuestion first: whole app,
not just landing, and switch fully to green rather than keep red/blue):**
- `lib/theme.ts` — swapped the red/blue duotone for a single mint-green
  accent (`GREEN`/`GREEN_LIGHT`/`GREEN_DARK`/`GREEN_DIM`), switched the
  theme's default `fontFamily` to Geist Mono site-wide (was sans, mono only
  on `h1`), pill-shaped buttons (`borderRadius: 999`) with glow on
  hover/contained.
- `GridBackground.tsx` — green ambient glow (was two red/blue blobs) behind
  the hero; new `BinaryColumns.tsx` renders decorative binary-digit columns
  down the left/right edges (fixed content, not `Math.random()`-generated,
  to avoid an SSR/client hydration mismatch — see the comment in that file
  if tempted to make it "actually random").
- New `NavBar.tsx` — persistent `[ OCULUS ]` brand + Dashboard link, added
  globally via `ThemeRegistry.tsx`, which now wraps every page in a
  `height: 100dvh` flex column (nav + `flex:1, minHeight:0` content area).
- Landing page (`app/page.tsx`) rebuilt to match the reference layout:
  corner brackets, bracketed `[ OCULUS ]` tagline, huge glowing "OCULUS"
  title + "PENTESTING" subtitle, `SCAN · VERIFY · REPORT` strapline, pill
  CTA with a blinking cursor-block, feature cards restyled to match.
  Deliberately did NOT add a light/dark toggle despite the reference having
  one — this app is single-mode dark by prior explicit decision.
- Swept every hardcoded blue hex (`#3b82f6` etc.) across `Checklist.tsx`
  (selected-card glow) and `SeverityBar.tsx` (progress gradient) to use the
  new `GREEN`/`GREEN_DARK` exports instead — grep for `3b82f6`/`60a5fa` if
  a stray one turns up later.
- Severity/status colors (finding severity chips, checklist status dots,
  stat-card critical/high counts) were deliberately left alone — those are
  semantic (red=critical, amber=running, etc.), not brand color, and
  shouldn't shift with the theme.

**Non-obvious fix required by the NavBar addition:** the engagement detail
page previously used a hardcoded `height="100vh"` on its root layout Box
for its fixed-viewport/internal-scroll design (checklist sidebar + item
panel each scroll independently). Adding a persistent nav bar on top of
that would have pushed it past the actual viewport. Fixed by changing it
to `height="100%"` against the new `ThemeRegistry` flex-column parent
(`flex:1, minHeight:0` on the content wrapper is what makes the percentage
height resolve correctly — flex children need `minHeight:0` to not just
grow to their content's intrinsic size, a classic flexbox gotcha).

**Verified:** `tsc`/`eslint`/`next build` clean; full browser pass across
landing → engagements → detail → both create/run-tool dialogs, zero
console errors, screenshots confirmed visual parity with the reference
(corner brackets, glow, binary columns, pill buttons all render). Cleaned
up two stray test engagements ("Modes Check" ×2) left over from an earlier
session's verification that never got deleted.

**Next steps for the next agent:**
1. If a light mode ever gets requested, `theme.ts`'s green tokens need a
   light-surface variant — nothing here prepares for that, it's dark-only
   top to bottom (background.default, GridBackground, etc.).
2. `BinaryColumns.tsx`'s digit pattern is a fixed hardcoded array, not
   actually random — fine as pure decoration, but don't mistake it for a
   dynamic/animated matrix effect if asked to make it "more alive" later;
   that'd need a client-only `useEffect`-populated version to avoid the
   hydration mismatch a direct `Math.random()` in render would cause.

---

## 2026-08-18 (4) — Fix: amass timeout, subfinder PATH resolution, and a real timeout-enforcement bug

**Done (user-reported: "Amass engine did not respond" + "subfinder already
install but can't use it"):**
- **Subfinder (and every other `go install`-based tool: httpx, nuclei,
  dnsx, katana, gowitness)** installs to `~/go/bin` by default, which
  isn't on `PATH` for a lot of setups — `is_available()` couldn't find it,
  so the app silently used simulated output. Fixed: `resolve_binary()` in
  `oculus/tools/base.py` now also checks `$GOBIN`/`$GOPATH/bin` and
  resolves to the full path when found there.
- **Amass timeout mismatch**: amass's own `-timeout 10` flag means 10
  *minutes*, but the wrapper's subprocess kill timeout was a blanket 120
  seconds — amass was being killed 8+ minutes early. Added per-tool
  `get_timeout()` (amass: 90s fast / 660s full; also bumped `nikto`,
  `wpscan`, `testssl`, `nuclei`, `ffuf`, `gobuster`, which had the same
  problem to lesser degrees).
- **The bigger catch — timeout enforcement itself was broken**: the old
  `for line in proc.stdout: ...` then `proc.wait(timeout=...)` blocks on
  the read with no deadline, so `timeout` only ever took effect *after*
  the process had already exited on its own — i.e. it essentially never
  worked for any tool that runs long without producing output. Caught via
  a regression test (`sleep 5` with `timeout=1` ran the full 5s). Rewrote
  `run_tool()` to read in a background thread with `thread.join(timeout=)`
  enforcing a real wall-clock deadline, and kill the whole process group
  (`start_new_session=True` + `os.killpg(..., SIGKILL)`) rather than just
  the direct child — some tools here (`testssl.sh`) are shell scripts that
  spawn their own subprocesses, and killing only the parent leaves a
  grandchild holding the output pipe open, so the reader never sees EOF.

**Verified:** 4-case regression suite (silent hang, normal command,
output-then-hang, process-group kill) all pass with correct exit codes and
wall-clock timing; a real `nmap` scan over the WebSocket still completes
normally (no regression); `subfinder` now resolves to
`~/go/bin/subfinder` and reports `available: true` via `/api/tools`.

**Next steps for the next agent:**
1. `apt` install hints (Debian/Kali package names) still aren't verified
   against a real `apt-get` — this dev box is macOS only.
2. If a tool wrapper's `get_timeout()` default (180s) is too short for a
   real full scan against a large target, bump it per-tool the same way
   amass/nikto/etc. were — don't just raise the global default blindly.

---

## 2026-08-18 (3) — nmap scan-mode presets + checklist cards

**Done (user request: richer per-tool options like nmap UDP/all-ports
scans, and checklist items as cards instead of list rows):**
- `BaseTool.modes: dict[str,str]` + `build_command_for_mode()` — generic
  mechanism for tools to declare named scan-mode presets beyond Fast/Full.
  Only `nmap` uses it so far: quick, full, all-ports (`-p-`), UDP scan,
  OS/version detection (`-O`), aggressive (`-A`), ping sweep (`-sn`). Base
  implementation falls back to fast/full for every other tool, so nothing
  else changed behaviorally.
- `RunToolDialog.tsx` shows a "Scan mode" dropdown instead of the Fast
  switch when the selected tool declares modes; a mode-based run always
  executes for real (never the simulated fallback) since simulated output
  wouldn't actually reflect what e.g. a UDP scan looks like — that'd be
  actively misleading. Added a privilege warning for OS-detect/aggressive
  since `-O` needs root.
- `Checklist.tsx` — item rows are now MUI `Card`/`CardActionArea` with a
  status-colored left border strip and a glow on the selected card,
  Framer Motion hover/tap scale. Category collapse, filter, and ↑↓
  keyboard nav unchanged.

**Verified:** real end-to-end `nmap -sn` (ping sweep) executed over the
WebSocket via the new mode picker; all 7 nmap modes produce correct
commands via `/api/tools/nmap/command?mode=...`; invalid mode returns a
clean 400. `tsc`/`eslint`/`next build` clean.

---

## 2026-08-18 (2) — Landing page + interactive tool installer

**Done:**
- Split the frontend: `/` is now a landing page (hero, feature cards, "Open
  Dashboard" CTA), the engagement list moved from `/` to `/engagements`.
  Engagement detail's back-link updated accordingly.
- Added `oculus install-tools` — a new CLI command (backed by
  `oculus/tool_installer.py`) that interactively installs a *subset* of
  the 16 tool binaries rather than forcing all-or-nothing. The 7 tools
  `findings_extractor.py` auto-parses (`nmap`, `httpx`, `whatweb`,
  `nuclei`, `wafw00f`, `subfinder`, `nikto`) are pre-selected as the
  recommended starter set. Picks the best available package manager per
  tool (brew → apt → go → pip → gem, whichever the host actually has) and
  reports honestly when none apply, rather than guessing. `./install-tools.sh`
  wraps it (venv setup, matches the `run-*.sh` script family).
- Added `install_hints: dict[str, str]` to every tool wrapper
  (`oculus/tools/*_tool.py`, base attr on `BaseTool`) — single source of
  truth consumed by both the installer and the web UI (`/api/tools` now
  returns `available` + `install_hints` per tool; `RunToolDialog` shows a
  warning with copyable install commands when the selected tool isn't
  installed; `ChecklistItemDialog`'s tool picker dims uninstalled tools
  with a tooltip).

**Bugs caught and fixed during verification (source of these is worth
remembering — don't trust remembered package names without checking):**
- Guessed `brew install projectdiscovery/tap/httpx` (and the same pattern
  for `subfinder`/`nuclei`/`dnsx`/`katana`) — **that tap doesn't exist**
  (`brew tap projectdiscovery/tap` 404s on GitHub). Removed the brew hint
  for all 5; `go install .../cmd/<tool>@latest` is the only real install
  path for ProjectDiscovery tools on this host and is what's shipped now.
- Guessed `brew install whatweb` — **no such formula exists** (`brew
  search whatweb` only suggests an unrelated cask). WhatWeb has no clean
  one-line macOS install; only the `apt` hint is real. The installer now
  correctly reports "no automatic install method on this host" for it on
  macOS instead of running a command that 404s.
- Guessed `brew install wpscan` — wrong; the real formula is
  `wpscanteam/tap/wpscan` (a third-party tap, confirmed via `brew info`).
  Fixed to the fully-qualified path.
- Caught by actually running `brew search`/`brew info`/`pip3 index
  versions` for every hint rather than trusting training-data recall, then
  running a real end-to-end install (`pip install arjun` via the
  installer) and confirming `ArjunTool().is_available()` flips to `True`
  afterward. **Lesson for next time: verify install commands against the
  real package index before shipping them, every time — recalled package
  manager formula/tap names are frequently stale or outright wrong.**

**Verified:**
- `tsc --noEmit`, `eslint`, `next build` clean (new `/engagements` static
  route confirmed in build output).
- Browser pass: landing page renders (hero, feature cards, animations),
  "Open Dashboard" navigates to `/engagements`, "← oculus" navigates
  back — zero console errors.
- CLI: `oculus install-tools` tested end-to-end non-interactively (piped
  stdin) — table renders correctly with real `is_available()` status per
  tool, selection toggling (`n`/numbers/empty-line-confirm) works, EOF
  during the prompt aborts gracefully (click's `Aborted!`), and a real
  install (`arjun` via pip) succeeded and was reflected in a fresh
  availability check afterward.
- `install-tools.sh` wrapper tested standalone (creates venv if missing,
  execs into the CLI command).

**Next steps for the next agent:**
1. The `apt` hints (Debian/Kali package names) are *not* verified against
   a real `apt-get` — this dev box is macOS only. They're standard,
   well-known Kali package names (high confidence) but worth a real check
   on a Debian/Kali box before fully trusting them.
2. `gowitness`'s `go install github.com/sensepost/gowitness@latest` and
   the other bare `go install` paths weren't executed end-to-end (only
   `pip install arjun` was) — reasonably confident (stable, well-known
   module paths) but not empirically confirmed like the pip path was.
3. Landing page has no dark/light toggle or additional content sections
   by design (matches the single-mode dark theme decision from the
   previous session) — don't add a "light mode" landing variant without
   revisiting that decision first.

---

## 2026-08-18 — Frontend redesign: MUI + Framer Motion, dark red/blue theme

**Done:**
- Rebuilt the entire frontend UI layer on MUI v7 (`@mui/material`,
  `@mui/icons-material`, `@mui/material-nextjs` for App Router SSR/Emotion
  cache) and Framer Motion, per explicit user direction. Every page/component
  from the previous Tailwind-hand-rolled UI was rewritten: home page,
  engagement detail, `Checklist`, `ItemDetail`, `RunToolDialog`,
  `FindingsPanel`, `ChecklistItemDialog`, `Badge` (now MUI `Chip`),
  `SeverityBar`/`ProgressBar`, `toast.tsx` (MUI `Alert` + Framer Motion
  stack, same `useToast()` API as before).
- New visual identity, per user's explicit spec: black background, a faint
  grid pattern, and a slow-drifting red/blue ambient glow
  (`components/GridBackground.tsx`, animated via Framer Motion), plus a
  matching MUI dark theme (`lib/theme.ts` — primary blue, secondary red,
  glassy blurred `Paper`/`AppBar`/`Dialog` surfaces).
- Tailwind is still installed/imported (`globals.css`) but no longer the
  primary styling system — kept only for `HighlightedOutput.tsx`'s terminal
  color spans and a couple of small CSS bits (scrollbar, row hover) that
  don't need MUI's `sx`.

**Important pin — do not casually bump MUI:**
- Installing `@mui/material@latest` pulls **v9**, which removed the
  shorthand style props (`mb`, `p`, `display`, `flex`, `alignItems`,
  `justifyContent`, `fontWeight`, `color`, etc.) from `Box`/`Stack`/
  `Typography` — those components now type-check with `children`/`sx` only.
  Every component in this rewrite uses the classic shorthand-prop style
  extensively, so `package.json` pins `@mui/material`/`@mui/icons-material`/
  `@mui/material-nextjs` to `^7.3.11` deliberately (there is no v8; v7 is
  the last major with the classic API, v9 is next). Bumping past v7 means
  rewriting every shorthand prop usage to `sx={{...}}` across ~10 files —
  found this the hard way (full typecheck failure after `npm install
  @mui/material` with no version pin defaulted to v9).

**Verified:**
- `tsc --noEmit`, `eslint`, and `next build` all clean.
- Full browser pass via a throwaway Playwright script (not committed):
  home page stat cards/search/table, new-engagement dialog, engagement
  detail header (progress + severity bars), checklist sidebar (filter,
  collapse, add-item), item detail (edit/delete, run-tool dialog with
  colorized live WebSocket output, findings accordion with add form) —
  zero console errors, screenshots confirmed the grid+glow background and
  MUI theming render correctly together.
- Found and cleaned up two stray empty `package-lock.json` files (repo
  root and `backend/`) left over from earlier sessions running `npm
  install` from the wrong directory — not related to this change, just
  swept up during verification.

**Next steps for the next agent:**
1. If MUI ever needs to go past v7 (security fix, wanted v9 feature), budget
   time to convert every `mb`/`p`/`display`/etc. prop to `sx` — don't just
   bump the version and expect it to typecheck.
2. `HighlightedOutput.tsx` still uses Tailwind utility classes for terminal
   line coloring — intentionally left as-is since it's visually
   self-contained (always a black monospace box) and not worth converting;
   flag if Tailwind ever gets removed from the project entirely.
3. No dark/light mode toggle — the theme is deliberately single-mode (dark
   only, per the user's spec), so don't add `prefers-color-scheme` handling
   expecting a light variant to exist.
4. Same gaps as before still apply: no test suite for `frontend/` or
   `backend/`, no in-place finding-edit UI, no docker-compose entry for the
   web app.

---

## 2026-08-13 — Web app: FastAPI backend + Next.js frontend

**Done:**
- Added `backend/` — FastAPI app wrapping the existing `oculus` package
  (`state`, `orchestrator`, `models`, `report`, `tools`) with no changes
  to that package. Routes: engagements CRUD, checklist item actions
  (mark-done/skip/reset/notes), findings CRUD, tool registry + command
  preview + wordlist discovery, Markdown/.docx report download, and a
  WebSocket (`/ws/engagements/{id}/items/{item}/run`) that streams live
  tool stdout exactly like the TUI's Run Tool dialog (Fast/Full,
  editable command, wordlist picker).
- Added `frontend/` — Next.js 16 (App Router, TS, Tailwind) UI: engagement
  list/create page, engagement detail page with a category-grouped
  checklist sidebar, item detail panel, Run Tool dialog (WebSocket live
  output), findings panel (add/verify/delete), Markdown/Word report
  download buttons.
- Added `pyproject.toml` `web` extra (`fastapi`, `uvicorn[standard]`,
  `websockets`).
- Added README.md "Web app" section with setup instructions; added
  `frontend/README.md`, `frontend/.env.example`.
- Both backend and frontend read/write the same
  `~/.oculus/engagements/` JSON store as the CLI/TUI — no new storage
  layer, all three interfaces share state.
- No auth (matches the CLI's single-user/local trust model, per explicit
  user decision — see "Decisions" below).

**Verified:**
- Backend: imported cleanly, exercised via curl — created/listed/deleted
  engagements, ran `nmap` for real over the WebSocket, generated a
  Markdown report. `npx tsc --noEmit` and `next build` clean on the
  frontend.
- Full browser E2E via a throwaway Playwright script (not committed):
  home page → engagement detail → select checklist item → open Run Tool
  dialog → run `httpx` with Fast scan → confirmed output streamed into
  the terminal panel and findings were auto-extracted. Zero console
  errors after the CORS fix below.
- **Bug caught and fixed during verification:** `CORSMiddleware` was
  configured with `allow_credentials=True` and `allow_headers=["*"]`,
  which is invalid per the CORS spec (browsers reject wildcard headers
  when credentials are allowed) — the frontend's fetch calls were being
  silently blocked. Fixed by setting `allow_credentials=False` in
  `backend/main.py` (no auth/cookies are used, so this is correct, not
  a workaround).
- **Environment quirk, not a bug:** on this machine, plain
  `curl http://localhost:8000` resolves to IPv6 first and hits an
  unrelated Docker service also bound to port 8000, returning a
  confusing `{"error": "unauthorized"}`. `127.0.0.1:8000` (IPv4)
  reaches the actual FastAPI backend correctly. `frontend/.env.local`
  and `.env.example` already point at `127.0.0.1`, not `localhost`, to
  sidestep this. Worth knowing if a future agent sees mysterious 401s
  hitting "the backend" — check which process actually answered.

**Decisions made (asked via AskUserQuestion, not assumed):**
- Stack: FastAPI backend + Next.js frontend (user's explicit choice
  over HTMX/Jinja or API-only).
- Live tool output: WebSockets (over polling).
- Auth: none — local/single-user, matching the CLI today.

**State at end of session:**
- Backend running on `127.0.0.1:8000`, frontend dev server on
  `localhost:3000`, both started manually in this session (not a
  persistent service/systemd unit — a new agent will need to restart
  them; see README.md "Web app" section for the exact commands).
- No automated test suite for `backend/` or `frontend/` yet — the E2E
  verification was a throwaway script, deleted after use, not committed.
- Unrelated to this work: `.claude/` also got a statusline configured
  this session (model/cwd/git branch/context %) — irrelevant to the
  app itself, mentioned here only so it isn't mistaken for app config.

**Next steps for the next agent:**
1. No auth exists — if this ever needs to run somewhere other than
   localhost, add auth first (see README.md "Web app" note on this).
2. No test suite for `backend/` (pytest + `TestClient`/`httpx` would be
   natural) or `frontend/` (Playwright, given it's already proven out
   manually) — worth adding before this grows further.
3. Findings-panel editing is add/verify/delete only — there's no UI for
   editing an existing finding's title/description/severity in place
   (the backend `PATCH .../findings/{id}` endpoint supports it; the
   frontend just doesn't expose a form for it yet).
4. The frontend re-fetches the whole engagement on most mutations by
   updating local state from each endpoint's response rather than
   re-fetching — verify this stays correct if multiple browser tabs
   edit the same engagement concurrently (last-write-wins today, no
   conflict detection).
5. Consider a `docker-compose` service for the web app (backend +
   frontend containers) to match the existing CLI Docker setup in the
   root `docker-compose.yml` — not done this session, CLI Docker image
   is unchanged.
