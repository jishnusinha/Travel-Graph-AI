# Visual QA Checklist

Screenshots captured 2026-11-18 via Playwright against local demo (AI_MODE=demo).

| Route | Screenshot | Mockup ref | Layout match | Notes |
|---|---|---|---|---|
| `/login` | `docs/screenshots/login-desktop.png` | `6e2f9110…` | High | Split layout + demo helper; OAuth disabled labeled |
| `/dashboard` | `docs/screenshots/dashboard-desktop.png` | `65d19196…` | High | Seed metrics 12/7/2/3; AI cost USD; SVG hero placeholders |
| `/dashboard` mobile | `docs/screenshots/dashboard-mobile.png` | `batch_d_mobile_dashboard` | Medium–High | Bottom nav present |
| `/trips` | `docs/screenshots/trips-desktop.png` | `23d7ee47…` | High | Filters/counts from DB |
| `/studio` | `docs/screenshots/studio-desktop.png` | `63314916…` | High | React Flow graph + Validator node; TG-1047 $0.237 / 14.2s |
| `/costs` | `docs/screenshots/costs-desktop.png` | derived from `7cae870d…` | Medium–High | Dark analytics; demo provenance |

## Intentional deviations

See `docs/visual-deviations.md`. Scenic photos replaced with local SVG/gradient assets (no stock hotlinking). Mockup metric numbers overridden by coherent seed.

## Not claiming pixel perfection

Side-by-side inspection shows strong structural fidelity (shell, hierarchy, dual themes). Exact photo assets and some mockup decorative flourishes differ by design.
