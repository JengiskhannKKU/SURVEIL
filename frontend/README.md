# surveil — web frontend

Next.js (App Router, TypeScript) UI for `surveil`, talking to the FastAPI
backend in `../backend/`. See the repo root `README.md` ("Web app" section)
for the full setup — backend install/run, env vars, and how this fits with
the CLI/TUI.

Built on MUI v7 (Material UI) for components and Framer Motion for
animation, themed as a dark "red team / blue team" console: black
background, a faint grid, and a slow-drifting red/blue ambient glow
(`src/components/GridBackground.tsx`, `src/lib/theme.ts`). Theme note:
MUI v9 dropped the classic shorthand style props (`mb`, `p`, `display`, …)
from `Box`/`Stack`/`Typography` in favor of `sx`-only — this project is
pinned to `^7.3.11` deliberately; don't bump past v7 without rewriting
every such prop usage to `sx`.

Quick start (backend must already be running on `:8000`):

```bash
npm install
cp .env.example .env.local   # points at http://127.0.0.1:8000 by default
npm run dev
```

Open http://localhost:3000.

## Layout

- `src/app/page.tsx` — engagement list + create dialog
- `src/app/engagements/[id]/page.tsx` — engagement detail (checklist + item panel)
- `src/components/` — `Checklist`, `ItemDetail`, `RunToolDialog` (WebSocket live output),
  `FindingsPanel`, `ChecklistItemDialog` (add/edit checklist items), `Badge` (status/severity
  chips), `SeverityBar` (progress + severity overview), `HighlightedOutput` (terminal-style
  line coloring for tool output), `GridBackground`, `ThemeRegistry`
- `src/lib/api.ts` — typed fetch client for the backend REST API
- `src/lib/types.ts` — TypeScript types mirroring `surveil/models.py`
- `src/lib/theme.ts` — MUI theme (palette, component overrides)
- `src/lib/toast.tsx` — toast notifications (MUI `Alert` + Framer Motion), `useToast()` hook
