# Mockup Inventory

> Reference folder in this workspace is `MOCK-UP/` (not `MOCKUP-UI/`). All files left read-only.

## Desktop / tablet references (~1536–1672 × 941–1024)

| Filename | Size | Route | Theme | Notes |
|---|---|---|---|---|
| `6e2f9110-4247-4b21-8f88-95f87d072b7c.png` | 1586×992 | `/login` | Light auth | Split scenic left / form right. OAuth buttons → label **Unavailable**. |
| `bc05551a-8c45-4313-91f4-f70051bbdca5.png` | 1586×992 | `/signup` | Light auth | Split beach hero + signup form. OAuth → Unavailable. |
| `travelgraph_batch_b_forgot_password.png` | 1536×960 | `/forgot-password` | Light auth | Centered split card. |
| `travelgraph_batch_b_reset_password.png` | 1536×960 | `/reset-password/:token` | Light auth | Strength meter + checklist. |
| `9035703f-5915-40f5-b351-0ddc5a429426.png` | 1586×992 | `/onboarding` | Light | **Primary** onboarding reference (Santorini + interest cards + budget slider). |
| `19f7715e-c404-4747-a030-2b812334ea45.png` | 1586×992 | `/onboarding` | Light | Alternate onboarding; inspirational only. Duplicate of `travelgraph_batch_b_onboarding.png`. |
| `0c92350e-a34b-4c7b-bbee-138dfa215e1c.png` | 1586×992 | `/onboarding` | Light | Alternate “Getting Started” variant; secondary. |
| `travelgraph_batch_b_onboarding.png` | 1586×992 | `/onboarding` | Light | Byte-identical twin of `19f7715e…`. |
| `65d19196-9748-4e33-9367-f88676793599.png` | 1586×992 | `/dashboard` | Light | Overview: hero prompt, metrics, recent trips, donut insights. |
| `4dfe9096-a6bb-4f11-a225-d8510d75d358.png` | 1672×941 | `/trips/new` | Light | Plan form; **omit Premium upsell**. |
| `723a150f-36d8-4f22-99ad-c867f10cc343.png` | 1586×992 | `/trips/:tripId` | Light | Goa Escape itinerary (days, timeline, AI summary). |
| `23d7ee47-4737-44c7-8911-7cfaadea3342.png` | 1672×941 | `/trips` | Light | My Journeys grid + filters; omit premium promo. |
| `6459a91d-fb54-408a-8200-8f83f949c527.png` | 1536×1024 | `/settings` | Light | Profile tabs; **2FA shown as Unavailable**. |
| `63314916-da97-436e-b260-c5223ff6fe63.png` | 1586×992 | `/studio` | Dark | Live Agent Studio graph + inspector + timeline. |
| `5194a6fd-7936-46ea-bfe6-c944567ca010.png` | 1586×992 | `/studio/runs/:runId/replay` | Dark | Replay controls + graph state. |
| `69c4d19e-8dd9-489c-958d-16f0275dbdbb.png` | 1586×992 | `/evaluations/compare` | Dark | Comparison lab (also informs `/evaluations`). |
| `7cae870d-4a38-4c73-a2f0-b44a0c04cb60.png` | 1586×992 | `/costs/runs/:runId` | Dark | Run cost detail (also informs `/costs` overview). |

## Mobile references (860×1864)

| Filename | Route | Theme |
|---|---|---|
| `travelgraph_batch_d_mobile_dashboard.png` | `/dashboard` | Light + bottom nav |
| `travelgraph_batch_d_mobile_trip_planner.png` | `/trips/:tripId` | Light itinerary |
| `travelgraph_batch_d_mobile_my_trips.png` | `/trips` | Light journeys |
| `travelgraph_batch_d_mobile_agent_studio.png` | `/studio` | Dark studio |

## Duplicates / conflicts

- Onboarding has 3 visual variants → use `9035703f…` as primary.
- Mockup metrics (e.g. 248 trips, $0.0032) conflict with coherent seed (`12` trips, `$0.237` for TG-1047). **Keep layout; use seed numbers.**
- Graph mockups omit Validator node; product requires Validator → include it in real graph.
- OAuth / Premium / 2FA in mockups → unavailable or omitted.
