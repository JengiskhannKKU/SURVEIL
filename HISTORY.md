# surveil — project history

Running log of work sessions on this repo, kept for continuity across
agent sessions. Newest entry on top. Each entry: what was done, what
was verified, and what the next agent should pick up.

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
