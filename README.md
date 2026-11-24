# TravelGraph AI

Local-first multi-agent travel planning app with a **Dual Experience** UI:

- **Light Travel Workspace** — auth, dashboard, trip planning, itineraries, settings  
- **Dark Intelligence Workspace** — Agent Studio, replay, Evaluation Lab, Cost Explorer  

Orchestration is a real **LangGraph** graph (Supervisor → Destination / Transport / Accommodation → Itinerary → Validator → Aggregator) with persisted events, SSE streaming, and replay.

## Quick start (Windows)

```powershell
# From repo root
.\scripts\setup.ps1
.\scripts\dev.ps1
```

- Frontend: http://localhost:5173  
- Backend API docs: http://127.0.0.1:8000/docs  

### Demo accounts (local only)

| Email | Password |
|---|---|
| `demo@travelgraph.local` | `TravelGraphDemo!2026` |
| `reviewer@travelgraph.local` | `TravelGraphDemo!2026` |

Demo mode needs **no API keys**. Seeded data is labeled as catalog estimates / demo costs — not live bookings or invoice prices.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/setup.ps1` | venv, deps, `.env`, migrate, seed (+ models unless `-SkipModels` / `-CatalogOnly`) |
| `scripts/doctor.ps1` | Offline-demo health check (venv, models, snapshot, ports) |
| `scripts/prepare-knowledge.ps1` | Download local models and rebuild `india-v1` from cache |
| `scripts/evaluate-rag.ps1` | Score reviewed retrieval cases |
| `scripts/start-backend.ps1` | Uvicorn on :8000 |
| `scripts/start-frontend.ps1` | Vite on :5173 |
| `scripts/dev.ps1` | Both in separate windows |
| `scripts/seed.ps1` | Idempotent seed |
| `scripts/reset-demo.ps1` | Wipe local DB + reseed (type `RESET`) |
| `scripts/test.ps1` | Backend pytest + frontend vitest + build |

## Terra

The travel workspace at `/` is **Terra**. Agent Studio stays the dark TravelGraph workspace. `KNOWLEDGE_MODE=catalog` (the default when unset) keeps the original demo planner. `KNOWLEDGE_MODE=rag` uses a local snapshot. See `docs/TERRA.md`, `docs/DATA_SOURCES.md`, and `docs/EVALUATION_REPORT.md`.

```powershell
.\scripts\setup.ps1                  # full offline-ready setup
.\scripts\doctor.ps1                 # verify models + india-v1
.\scripts\prepare-knowledge.ps1      # rebuild snapshot if needed
.\scripts\evaluate-rag.ps1           # measured retrieval table
```

Clean-machine catalog-only fallback (no dense models):

```powershell
.\scripts\setup.ps1 -CatalogOnly
```

## AI modes

`.env` (from `.env.example`):

```
AI_MODE=demo          # default — fully offline after install
OPENAI_API_KEY=       # leave blank for demo
OPENAI_MODEL=
```

To enable live OpenAI later (optional):

1. Put `OPENAI_API_KEY` in the **root** `.env` (backend-only; never in frontend).  
2. Set `OPENAI_MODEL` to a model available on your account.  
3. Set `AI_MODE=openai`.  
4. Restart the backend. Demo remains the default until you do this deliberately.

## Architecture

```
frontend/   React + TypeScript + Vite + Tailwind + React Flow + Recharts
backend/    FastAPI + SQLAlchemy/SQLite + LangGraph + Argon2 sessions
MOCK-UP/    Visual design references (read-only)
data/       Local SQLite databases (gitignored)
```

## Coherent demo scenario

- Trip: **Goa Escape Plan** · Kolkata → Goa · Jan 12–16, 2027 · 2 travelers · ₹35,000  
- Sample estimate: ₹34,850 (₹150 remaining) — labeled estimates only  
- Run **TG-1047**: 14.2s wall · 36,420 tokens · **$0.237** demo AI cost (USD)

## Security notes

- Opaque HttpOnly session cookies + CSRF header for mutations  
- Passwords hashed with Argon2  
- Per-user ownership on trips, runs, evaluations, costs  
- Password reset in local mode writes a one-time link to the backend console and `data/dev_reset_inbox.jsonl`  
- OAuth / Premium / 2FA shown in mockups are **not implemented** and are labeled unavailable  

## Tests

```powershell
.\scripts\test.ps1
```

## Docs

- `docs/TERRA.md` — Terra product surface  
- `docs/DATA_SOURCES.md` / `docs/DATA_LICENSES.md` — corpus provenance  
- `docs/EVALUATION_REPORT.md` — measured retrieval numbers  
- `docs/screenshots/` — Terra desktop/mobile smoke captures  
- `docs/01-mockup-inventory.md` — mockup → route map  
- `docs/02-design-system.md` — tokens  
- `docs/03-implementation-plan.md` — checklist  
- `docs/04-screen-matrix.md` — screen status  
- `docs/visual-deviations.md` — intentional differences from mockups  
- `docs/AGENT-HANDOFF.md` — resume status  

Reference images live in **`MOCK-UP/`** (workspace name; master prompt’s `MOCKUP-UI/` refers to the same role).

## Limitations (honest)

- OpenStreetMap Overpass did not yield POIs in this snapshot (0 OSM ids).  
- Nongriat, Dooars, and Mawlynnong have unknown page coordinates.  
- Visual search and live weather/routing stay unavailable offline.  
- Cost bands are editorial planning envelopes, not quotes.  
- Live OpenAI is optional and off unless you configure a key.
