# surveil — web frontend

Next.js (App Router, TypeScript) UI for `surveil`, talking to the FastAPI
backend in `../backend/`. See the repo root `README.md` ("Web app" section)
for the full setup — backend install/run, env vars, and how this fits with
the CLI/TUI.

Built on MUI v7 (Material UI) for components and Framer Motion for
animation, themed as a terminal/hacker-console: near-black background,
monospace type everywhere, a faint grid, decorative binary-digit side
columns, and a single mint-green glow accent (`src/components/
GridBackground.tsx`, `BinaryColumns.tsx`, `NavBar.tsx`, `src/lib/theme.ts`
— see `GREEN`/`GREEN_LIGHT`/`GREEN_DARK` there for the palette). Buttons
are pill-shaped (`shape.borderRadius: 999` via `MuiButton` overrides).
Theme note: MUI v9 dropped the classic shorthand style props (`mb`, `p`,
`display`, …) from `Box`/`Stack`/`Typography` in favor of `sx`-only — this
project is pinned to `^7.3.11` deliberately; don't bump past v7 without
rewriting every such prop usage to `sx`.

Layout note: `ThemeRegistry.tsx` wraps every page in a `height: 100dvh`
flex column (`NavBar` + a `flex: 1, minHeight: 0` content area) so the
engagement detail page's fixed-viewport, internally-scrolling layout
(checklist sidebar + item panel each scroll independently) resolves
correctly — its root `Box` uses `height: "100%"` against that flex
parent, not a hardcoded `100vh`. Keep that in mind if you add a page that
needs the full viewport height.

Quick start (backend must already be running on `:8000`):

```bash
npm install
cp .env.example .env.local   # points at http://127.0.0.1:8000 by default
npm run dev
```

Open http://localhost:3000.

## Layout

- `src/app/page.tsx` — landing page (`/`)
- `src/app/engagements/page.tsx` — engagement list + create dialog (`/engagements`)
- `src/app/engagements/[id]/page.tsx` — engagement detail (checklist + item panel)
- `src/components/` — `Checklist` (card-based items), `ItemDetail`, `RunToolDialog` (WebSocket
  live output, per-tool scan-mode presets), `FindingsPanel`, `ChecklistItemDialog` (add/edit
  checklist items), `InstallHints` (copyable install commands for missing tool binaries),
  `Badge` (status/severity chips), `SeverityBar` (progress + severity overview),
  `HighlightedOutput` (terminal-style line coloring for tool output), `GridBackground`,
  `BinaryColumns` (decorative side columns), `NavBar`, `ThemeRegistry`
- `src/lib/api.ts` — typed fetch client for the backend REST API
- `src/lib/types.ts` — TypeScript types mirroring `surveil/models.py`
- `src/lib/theme.ts` — MUI theme (palette, component overrides)
- `src/lib/toast.tsx` — toast notifications (MUI `Alert` + Framer Motion), `useToast()` hook
