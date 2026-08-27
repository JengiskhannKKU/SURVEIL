# surveil — project history

Running log of work sessions on this repo, kept for continuity across
agent sessions. Newest entry on top. Each entry: what was done, what
was verified, and what the next agent should pick up.

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
  - **naabu** (`surveil/tools/naabu_tool.py`) — ProjectDiscovery's fast
    SYN-based port scanner. Mapped alongside `nmap` on WSTG-CONF-01
    (Network Infrastructure Configuration) as a fast pre-scan pass;
    nmap remains the tool for banner/version detail on whatever naabu
    finds open. Fast mode: top 100 ports. Full: all 65535 (`-p -`).
  - **dalfox** (`surveil/tools/dalfox_tool.py`) — reflected/DOM XSS
    fuzzer that confirms each hit in a real browser context instead of
    just flagging a raw string reflection (fewer false positives than
    nuclei's generic XSS templates). Mapped alongside `nuclei` on
    WSTG-INPV-01 (Reflected XSS) only — deliberately **not** added to
    WSTG-INPV-02 (Stored XSS), since dalfox's URL-fuzzing approach
    can't do the submit-then-revisit workflow stored XSS actually needs.
  - **commix** (`surveil/tools/commix_tool.py`) — automated OS command
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
  --entrypoint sh surveil:tooltest -c "..."`) and confirmed `naabu
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
- `BaseTool` (`surveil/tools/base.py`) gained `help_flag` (default `-h`)
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
  `surveil/report.py::_deduplicate_findings()` groups by `(tool,
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
   (in `surveil/models.py`) untouched — those still return raw,
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
  matching `surveil/report.py`'s own structure exactly, no backend
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
  changes to `surveil/report.py` needed; it already returned the string
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
- 6 new extractors in `surveil/findings_extractor.py`, registered in
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
- `backend.main` and `surveil.cli` both import clean; `_validate_tool_
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
  includes `surveil*`), so it needs to be on disk and importable via
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
  pre-existing `surveil` CLI/TUI service, now gated behind a `cli`
  profile specifically so a plain `up` doesn't try to start an
  interactive-TTY-only service. All three share the same `surveil-data`
  volume, so an engagement created via the web UI is visible to
  `docker compose run --rm surveil status` and vice versa.
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
   including the `cli`-profile-gated `surveil` one — `build` ignores
   profile restrictions even though `up`/`run` respect them. Not a bug,
   just worth knowing `make docker`/`docker compose build` do build all
   three, not just the two the default `up` starts.
3. The Docker backend/CLI services use a *separate* `surveil-data`
   volume from this dev machine's local `~/.surveil/` — engagements
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
- Rewrote `surveil/checklist.py`'s `build_checklist()` from 26 items
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
  surveil.cli import build_checklist` both import clean.
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
- **Bug caught and fixed while building this**: `surveil/tools/base.py`'s
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

- **2 new tool wrappers** (`surveil/tools/`), registered in
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
- **2 new bundled wordlists**: `surveil/data/wordlists/usernames.txt`
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
  (`surveil.wordlists.CATEGORY_KEYWORDS`, `checklist.WORDLIST_CATEGORY`):
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
- `surveil/wordlists.py`: renamed the private `_CATEGORY_KEYWORDS` dict
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
entry, which had put picked-file downloads under `~/.surveil/wordlists/
seclists/`; the ask was for them to live inside the project itself):**
- `surveil/seclists_remote.py`: renamed the destination from
  `CACHE_DIR = ~/.surveil/wordlists/seclists` to
  `INSTALL_DIR = surveil/data/wordlists_downloaded/seclists` — inside
  this project's own package directory, a sibling of (not mixed into)
  the small hand-curated bundle at `surveil/data/wordlists/`. Kept
  `CACHE_DIR` as a backwards-compatible alias pointing at the same
  value. Added `install_wordlist` as an alias for `download_wordlist` —
  same function, a name that matches how it reads in the UI now
  ("Installs only the single file...").
  - The *tree-listing* cache (`seclists_tree_cache.json` — which files
    exist, not their content) deliberately stayed in `~/.surveil/` next
    to `config.json`/`engagements/` — it's request metadata, not a
    wordlist install, so home-dir persistence is still the right call
    for it specifically.
- `.gitignore`: added an explicit `surveil/data/wordlists_downloaded/`
  entry — these are per-checkout downloads, not meant to be committed.
  (There's also an unrelated pre-existing uncommitted `*.txt` rule in
  this file from before this session that would incidentally cover the
  same thing; added the explicit directory rule anyway so this doesn't
  depend on that other, unrelated change staying in place.)
- `surveil/wordlists.py`'s registered search root didn't need to change
  — it already referenced `seclists_remote.CACHE_DIR.parent` generically,
  which now just resolves to the project directory instead of the home
  directory automatically.
- Frontend (`WordlistPickerDialog.tsx`): updated the SecLists (GitHub)
  tab's caption and the Local tab's empty-state hint from "downloads"/
  "download" to "installs"/"install... into this project", naming the
  actual destination path (`surveil/data/wordlists_downloaded/`) so a
  tester knows where to look on disk.

**Verified:**
- Cleared any leftover files under the old `~/.surveil/wordlists/` path
  from the previous entry's testing first.
- `download_wordlist("Discovery/Web-Content/quickhits.txt")` against the
  real repo: confirmed the file lands at `<project>/surveil/data/
  wordlists_downloaded/seclists/Discovery/Web-Content/quickhits.txt`,
  confirmed nothing appears under `~/.surveil/` matching a wordlist file,
  confirmed `git status`/`git check-ignore -v` show it correctly ignored
  (matched by the new explicit rule, not the unrelated stray one), and
  confirmed it still surfaces under `discover_wordlists_grouped()`'s
  `SecLists/Discovery` group.
- `npx tsc --noEmit`, `eslint`, `next build` all clean.
- Full browser E2E via a throwaway Playwright script (deleted after
  use): opened the SecLists (GitHub) tab, confirmed the caption reads
  "Installs only the single file... into this project
  (surveil/data/wordlists_downloaded/)", searched "quickhits", installed
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
- New `surveil/seclists_remote.py`:
  - `list_remote_wordlists()` — one GitHub API call
    (`GET /repos/danielmiessler/SecLists/git/trees/master?recursive=1`)
    listing every file in the repo (6000+ `.txt` files as of this
    session), cached to disk for 24h at `~/.surveil/wordlists/
    seclists_tree_cache.json` — unauthenticated GitHub API calls are
    rate-limited to 60/hour, and the tree barely changes hour to hour,
    so there's no reason to refetch on every dialog open.
  - `download_wordlist(path)` — fetches exactly that one file's raw
    content (`raw.githubusercontent.com/.../master/<path>`) and saves it
    under `~/.surveil/wordlists/seclists/<path>`, mirroring the repo's
    own directory structure. No-ops (returns the existing path) if
    already downloaded. Rejects absolute paths / `..` segments — *path*
    ultimately comes from a request a tester could hand-edit.
  - No new Python dependency — uses stdlib `urllib.request` for both
    calls rather than adding `requests`.
  - Registered the download cache dir's *parent* as a
    `surveil/wordlists.py` search root (specifically the parent, not the
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
  command field's `-w` flag now pointed at `~/.surveil/wordlists/
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
- Fixed in `surveil/tools/base.py`: new `_subprocess_env()` builds the
  environment passed to every `run_tool()` subprocess with the same
  extra dirs `_extra_bin_dirs()`/`resolve_binary()` already know about
  (`$GOBIN`, `$GOPATH/bin`) prepended to `PATH`. Fixes this for dnsx and
  for any other shell-wrapped tool the same way, without parsing/
  rewriting each command string individually — the general architectural
  gap was "surveil's own binary search path never reaches a subprocess's
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
    (`surveil/tools/__init__.py`'s `TOOL_REGISTRY` has no such entry).
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
- Migrated the one existing real engagement (`~/.surveil/engagements/
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
  surveil.cli import build_checklist` both import without error.
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
- `surveil/wordlists.py` discovery rewrite:
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
    fasttrack.txt, ...) land in "Other". surveil's own bundled wordlists
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
  structure the user pasted, pointed `SURVEIL_WORDLIST_DIR` at it via the
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
- Added 5 new bundled wordlists under `surveil/data/wordlists/`:
  `admin.txt` (~55 admin-panel paths), `api.txt` (~60 API/GraphQL/Swagger
  paths), `backup.txt` (~65 backup/dump file names), `extensions.txt`
  (~50 file-extension-handling probes like `index.php.bak`, `.git/config`),
  `metafiles.txt` (~30 well-known metafiles like `robots.txt`,
  `.well-known/security.txt`). `common.txt` (existing, general-purpose)
  is reused as the "common" category.
- `surveil/checklist.py`: new `WORDLIST_CATEGORY` dict mapping specific
  WSTG checklist item IDs to a category (e.g. `WSTG-CONF-05` "Enumerate
  Admin Interfaces" → `"admin"`, `WSTG-CONF-04` "Review Old Backup and
  Unreferenced Files" → `"backup"`, `WSTG-INFO-06` "Identify Application
  Entry Points" → `"api"`), plus `CATEGORY_LABELS` for the human-readable
  hint text. Only 6 items are mapped — everything else (including any
  tester-added custom item) falls through to the plain default wordlist,
  unchanged from before.
- `surveil/wordlists.py`: new `recommend_wordlist(category)` — tries a
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
   `surveil/wordlists.py` rather than reworking the sort mechanism.
2. `limit=150` is still a cap, chosen to keep the Autocomplete responsive
   — a truly enormous SecLists install could still have Web-Content
   entries beyond position 150 if there happen to be 150+ higher-priority
   matches ahead of them. Not expected in practice (real Web-Content
   directories have well under 150 files), but worth knowing if someone
   reports "still missing a specific wordlist" again.

---

## 2026-08-19 (3) — Settings dialog: configure wordlist dir from the web UI

**Done (user request: "ffuf can select wordlists and user can config
environment wordlists path" — the previous session's `SURVEIL_WORDLIST_DIR`
env var required a backend restart to change, not something settable from
the running app):**
- New `surveil/config.py` — persisted app-wide settings
  (`~/.surveil/config.json`, separate from `~/.surveil/engagements/`).
  Currently just `wordlist_dir`; designed to hold more settings later.
- `wordlists.py`'s `_configured_root()` now checks the persisted config
  first, then `SURVEIL_WORDLIST_DIR` — config wins if both are set, since
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
1. If more app-wide settings get added later, extend `surveil/config.py`'s
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
- New `SURVEIL_WORDLIST_DIR` env var (`surveil/wordlists.py`) — point it
  at a directory (searched recursively for `*.txt`, also folded into the
  wordlist picker's search) or a specific file, and it's used first.
- New `default_wordlist()` resolver: `SURVEIL_WORDLIST_DIR` → first
  discovered wordlist in the existing common-location scan → a wordlist
  now bundled with surveil itself (`surveil/data/wordlists/common.txt`,
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
  `surveil/tools/base.py`: respects an explicit scheme if the tester typed
  one, defaults bare IPv4 targets to `http://` (internal targets are
  usually plain HTTP), bare hostnames to `https://` (still the common case
  for a real domain). Applied to `ffuf`/`gobuster` only, per the request's
  explicit scope — **9 other tools have the exact same hardcoded-https://
  pattern** (arjun, gowitness, katana, wafw00f, nikto, nuclei, wpscan,
  testssl — grep `f"https://{self.target}` across `surveil/tools/*.py`)
  and would benefit from the same `base_url()` fix; deliberately not
  touched this session to stay scoped to what was asked.

**Verified:** real `ffuf` and `gobuster` runs (via the wrapper classes
directly, then again through the actual backend WebSocket path) against
the same `192.168.2.11` target used in earlier bug reports — both now
return real results (`.htaccess`, `.htpasswd`, `assets`,
`server-status`, `vendor`) instead of silently succeeding with nothing.
Confirmed `SURVEIL_WORDLIST_DIR` resolves correctly for both a directory
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
`nmap` all check out clean — every flag `surveil/tools/*_tool.py` uses for
those exists in the installed binary's real help output.

**`amass` does not check out, and it's bigger than a bad flag:**
- `amass -h` (top-level) shows this installed version is v5.1.1, with a
  completely restructured CLI: `amass [assoc|engine|enum|subs|track|viz]`.
  This is OWASP Amass's new "OAM" (Open Asset Model) architecture — a
  significant rewrite from the v3/v4-era single-shot CLI our wrapper
  (`surveil/tools/amass_tool.py`, still sending
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
  in `surveil/tools/httpx_tool.py`'s full-mode `build_command()` that
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
  `surveil/tools/base.py`), set `True` on `subfinder`, `amass`, `dnsx` —
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
- New `NavBar.tsx` — persistent `[ SURVEIL ]` brand + Dashboard link, added
  globally via `ThemeRegistry.tsx`, which now wraps every page in a
  `height: 100dvh` flex column (nav + `flex:1, minHeight:0` content area).
- Landing page (`app/page.tsx`) rebuilt to match the reference layout:
  corner brackets, bracketed `[ SURVEIL ]` tagline, huge glowing "SURVEIL"
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
  `surveil/tools/base.py` now also checks `$GOBIN`/`$GOPATH/bin` and
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
- Added `surveil install-tools` — a new CLI command (backed by
  `surveil/tool_installer.py`) that interactively installs a *subset* of
  the 16 tool binaries rather than forcing all-or-nothing. The 7 tools
  `findings_extractor.py` auto-parses (`nmap`, `httpx`, `whatweb`,
  `nuclei`, `wafw00f`, `subfinder`, `nikto`) are pre-selected as the
  recommended starter set. Picks the best available package manager per
  tool (brew → apt → go → pip → gem, whichever the host actually has) and
  reports honestly when none apply, rather than guessing. `./install-tools.sh`
  wraps it (venv setup, matches the `run-*.sh` script family).
- Added `install_hints: dict[str, str]` to every tool wrapper
  (`surveil/tools/*_tool.py`, base attr on `BaseTool`) — single source of
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
  "Open Dashboard" navigates to `/engagements`, "← surveil" navigates
  back — zero console errors.
- CLI: `surveil install-tools` tested end-to-end non-interactively (piped
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
- Added `backend/` — FastAPI app wrapping the existing `surveil` package
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
  `~/.surveil/engagements/` JSON store as the CLI/TUI — no new storage
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
