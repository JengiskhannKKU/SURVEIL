# surveil — web frontend

Next.js (App Router, TypeScript, Tailwind) UI for `surveil`, talking to
the FastAPI backend in `../backend/`. See the repo root `README.md`
("Web app" section) for the full setup — backend install/run, env vars,
and how this fits with the CLI/TUI.

Quick start (backend must already be running on `:8000`):

```bash
npm install
cp .env.example .env.local   # points at http://127.0.0.1:8000 by default
npm run dev
```

Open http://localhost:3000.

## Layout

- `src/app/page.tsx` — engagement list + create form
- `src/app/engagements/[id]/page.tsx` — engagement detail (checklist + item panel)
- `src/components/` — `Checklist`, `ItemDetail`, `RunToolDialog` (WebSocket live output), `FindingsPanel`, `Badge`
- `src/lib/api.ts` — typed fetch client for the backend REST API
- `src/lib/types.ts` — TypeScript types mirroring `surveil/models.py`
