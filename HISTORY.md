# surveil — project history

Running log of work sessions on this repo, kept for continuity across
agent sessions. Newest entry on top. Each entry: what was done, what
was verified, and what the next agent should pick up.

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
