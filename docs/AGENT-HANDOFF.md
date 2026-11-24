# AGENT-HANDOFF

## Status

**Usable end-to-end local demo complete** (AI_MODE=demo, no OpenAI key).

## Reference path

`MOCK-UP/` holds 21 design PNGs (master prompt’s `MOCKUP-UI/` role).

## How to run

```powershell
.\scripts\setup.ps1   # first time
.\scripts\dev.ps1
```

Demo: `demo@travelgraph.local` / `TravelGraphDemo!2026`

## Verified

- Backend: 62 pytest passed
- Frontend: 26 vitest + production build
- Seed counts 12/7/2/3; TG-1047 = $0.237 / 14.2s
- Playwright screenshots under `docs/screenshots/`
- Servers were exercised on :8000 / :5173

## Enabling OpenAI later

1. Edit root `.env`: set `OPENAI_API_KEY`, `OPENAI_MODEL`, `AI_MODE=openai`
2. Restart backend only
3. Never put the key in frontend env files

## Remaining polish (optional)

- Deeper pixel-diff automation vs every mockup
- Broader Playwright E2E coverage beyond smoke screenshots
- Replace SVG destination placeholders with licensed photos if desired
- Eval Lab landing + CSV download were implemented; CSV download not re-verified in last smoke pass

## Blockers

None for demo delivery.
