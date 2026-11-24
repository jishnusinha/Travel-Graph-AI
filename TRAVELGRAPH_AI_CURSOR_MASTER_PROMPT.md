# TRAVELGRAPH AI — CURSOR MASTER BUILD PROMPT

> Paste this entire prompt into **Cursor Agent** while the **root of the TravelGraph AI workspace** is open. The reference images are already inside `./MOCKUP-UI/`. This is a request to **implement, run, test, and visually refine a complete application** in this workspace — not merely create a plan or generate screenshots.

## 0. YOUR ROLE, PRIORITIES, AND NON-NEGOTIABLE RULES

You are the lead product engineer, frontend designer, backend engineer, LangGraph engineer, and QA engineer responsible for shipping **TravelGraph AI**, a premium, local-first, multi-user, multi-agent travel-planning application. Work autonomously in this workspace and write actual working source files.

PRIORITIES, IN ORDER:
1. Recreate the **provided `MOCKUP-UI/` images as closely as practical** at their target screen sizes. Carefully inspect the actual files, not guessed filenames or general design descriptions.
2. Deliver **complete working user journeys** with real state, persistence, functional controls, and clear UX.
3. Deliver a **genuine LangGraph multi-agent workflow**, with shared state, conditional routing, useful agents, saved events, and a graph driven by real execution state.
4. Ship an end-to-end **no-key demo mode**, with deterministic seeded travel data, repeatable events, evaluations, and costs, that works fully offline after dependencies are installed.
5. Include an **OpenAI-only live AI mode**, enabled later by the user explicitly, with a secure backend-only `OPENAI_API_KEY`.
6. Ensure the app runs on **Windows locally** with PowerShell setup scripts and excellent documentation.

DO NOT:
- Stop after creating a project plan, wireframe, component skeleton, or attractive static homepage.
- Ask me to purchase services or supply keys before finishing the local demo.
- Require other API keys, OAuth provider credentials, paid map APIs, Redis, Docker, PostgreSQL, hosted LangGraph, LangSmith, Supabase, Firebase, a payment provider, or a cloud server.
- Implement mockup screenshots as full-screen images or hide broken UIs beneath background images.
- Hardcode fake metrics in React UI. All metrics must come from stored data or deterministic calculations.
- Display demo travel prices or availability as current verified booking information.
- Claim Google/GitHub sign-in, billing, 2FA, reservations, or premium subscriptions work unless actually implemented. Remove or clearly label unsupported designs as unavailable.
- Expose the OpenAI API key to the browser, logs, repository, database, or seed files.
- Ignore Windows PowerShell compatibility; avoid Bash-only setup commands.
- Declare work finished if significant routes, primary buttons, tests, or UI comparisons are still failing.

Keep `MOCKUP-UI/` untouched. Implement application code in separate frontend/backend folders. If you find an existing codebase, inspect and extend it rather than deleting it.

## 1. FIRST: INSPECT THE WORKSPACE AND DESIGN REFERENCES

Before coding:
- List all files under `MOCKUP-UI/` recursively, including formats and pixel dimensions. Detect duplicates and collages.
- **Open/view each relevant mockup**, individually; group them logically into login, signup, onboarding, forgot/reset password, dashboard, create trip, itinerary, my trips, Agent Studio, replay, Evaluation Lab, evaluation comparison, Cost Explorer, cost run detail, Settings & Profile, and mobile variations.
- Create `docs/01-mockup-inventory.md` mapping **actual existing image filenames** to routes, design regions, desktop/mobile sizes, and expected interaction patterns. Do not guess image paths.
- Create `docs/02-design-system.md` from visual inspection: color tokens, typography, sidebar width, topbar height, surfaces, gradients, border radii, shadows, card gaps, controls, and breakpoint behavior. When uncertain, estimate, then confirm through screenshot comparison.
- Create `docs/03-implementation-plan.md` containing a dependency-ordered checklist; UPDATE it continuously as work is completed.
- Create `docs/04-screen-matrix.md` mapping all reference screens to implemented routes, states, tests, and screenshot results.
- If there are multiple versions of a screen, choose the highest-quality standalone reference, record why, and use others for state/responsiveness inspiration.
- Check local node, npm, Python, and browser-test tooling; install missing project dependencies only as necessary and compatible with Windows.

The established brand is **TravelGraph AI**, a **Dual Experience hybrid** product:
- LIGHT TRAVEL WORKSPACE: light lavender/white backgrounds, dark navy typography, indigo-purple CTAs, mint progress indicators, travel imagery, rounded premium cards; includes authentication, onboarding, dashboard, planning, trips, settings.
- DARK INTELLIGENCE WORKSPACE: midnight navy backgrounds, glowing restrained indigo borders, mint/teal success markers, sophisticated charts, dense but legible technical controls; includes Agent Studio, Replay, Evaluation Lab, Comparison, Cost Explorer, detailed run analysis.
- Keep branding, icon language, spacing, type scale, and navigation consistent between both themes. Do not swap to a generic dashboard template.
- Preserve the visual hierarchy of the mockups even if image-generative mockups contain text inconsistencies. Correct obvious copy or math errors and log differences in `docs/visual-deviations.md`.

## 2. STACK — LOCAL WINDOWS FIRST

FRONTEND:
- React + TypeScript + Vite
- Tailwind CSS (current supported Vite setup) + shadcn/ui components
- React Router
- TanStack Query for backend data, state caching, mutations
- React Hook Form + Zod for forms
- `@xyflow/react` (React Flow) for the REAL interactive agent graph
- Recharts for analytics charts
- Lucide icons
- Motion for React only for restrained purposeful animations
- Playwright for E2E and screenshot comparison; Vitest + React Testing Library for unit/component tests

BACKEND:
- Python 3.11+ (choose an installed compatible Python version)
- FastAPI + Pydantic v2
- LangGraph for orchestration and checkpointed state
- OpenAI Python SDK / supported LangChain OpenAI wrapper where appropriate (prefer the supported OpenAI Responses API for new direct calls)
- SQLAlchemy + SQLite + Alembic migrations (aiosqlite where needed)
- LangGraph SQLite checkpointer, stored locally, separate DB file if helpful
- Secure password hashing with a modern supported library (e.g., Argon2)
- Session auth with opaque revocable server-side sessions and HttpOnly SameSite cookies, with appropriate local-development safeguards
- pytest + httpx for backend tests

ARCHITECTURE:
```
workspace/
  MOCKUP-UI/                 # READ-ONLY reference images
  frontend/
    src/
      app/ routes/ pages/ layouts/
      components/ui/ components/travel/ components/analytics/
      features/auth/ features/trips/ features/agents/ features/evaluations/ features/costs/
      hooks/ lib/ services/ styles/ assets/
    tests/ e2e/ public/
  backend/
    app/
      main.py config.py
      api/ auth/ db/ models/ schemas/ services/
      graph/ agents/ tools/ providers/ observability/ evaluation/ seed/
    tests/ alembic/
    requirements.txt or pyproject.toml
  scripts/
    setup.ps1  start-backend.ps1  start-frontend.ps1
    dev.ps1  seed.ps1  test.ps1  reset-demo.ps1
  docs/
  .env.example  .gitignore  README.md
```
Adapt as needed to avoid meaningless nesting. Keep domain logic out of React components and route handlers.

Run at `http://localhost:5173` (frontend) and `http://localhost:8000` (backend); FastAPI docs at `http://localhost:8000/docs`. Use a Vite proxy or explicit CORS that works with local cookie authentication. No Docker required.

## 3. REQUIRED FRONTEND ROUTES AND SCREENS

Implement ALL of these, using the actual mockups as visual source of truth. All listed pages need proper loading, empty, error, and success states, responsive behavior, keyboard focus, and useful controls.

PUBLIC AUTHENTICATION (LIGHT):
- `/login`: scenic split-screen image, logo, heading, email/password fields, password visibility, remember-me, sign-in, reset link, navigation to signup. Validate forms and errors.
- `/signup`: scenic split-screen, full name, email, password, confirmation, validation and account creation.
- `/forgot-password`: email entry, submit, generic confirmation that does not leak account existence. No mail API requirement: local development mode writes a single-use reset link to the backend terminal and a clearly gated developer-only local reset inbox. Never expose recovery links publicly.
- `/reset-password/:token`: valid/expired token UX; new password + confirmation; secure one-time reset; success screen with Login button.
- `/onboarding`: welcome, optional interests/preferences, home city, currency, budget range, accommodation and transport preferences, completion/skip behavior. Persist per user.

AUTHENTICATED LIGHT TRAVEL WORKSPACE:
- `/dashboard`: branded shell, real user greeting, search, header actions, travel hero, prominent prompt input / Generate Trip CTA, seeded metrics calculated from DB, recent trip cards, quick agent insights; new-user empty state.
- `/trips/new`: beautiful pre-generation trip request form with free-form prompt, simple/advanced mode, destination, origin, dates, traveler count, max trip budget, interests, optional preferences, seeded inspiration prompts. Validated submission launches a run.
- `/trips`: My Journeys library with working search, filters (all/completed/in-progress/draft/favorite), sort, grid/list toggle, trip cards, favorite/unfavorite, duplicate, delete with confirm, and continue/open.
- `/trips/:tripId`: full itinerary view from mockup: hero, 5-day selector, timeline, attractions, hotel and transport sections, budget breakdown, optional map panel, saved notes, AI-agent progress summary, save, edit, share/export (share can mean a local printable/shareable read-only view; never fabricate cloud sharing).
- `/trips/:tripId/edit`: alter preferences/request, invoke intelligent or deterministic replanning, retain version history; allow compare versions or recover earlier version if feasible.
- `/settings`: Profile & Account, Travel Preferences, AI Preferences, Privacy & Data, Appearance & Accessibility. Profile edit, change password, exports and account deletion confirmation should work. Don't claim 2FA works unless implemented; omit disabled premium upsell/OAuth placeholders.

AUTHENTICATED DARK AI INTELLIGENCE WORKSPACE:
- `/studio`: list latest runs, select run, live interactive directed graph (Supervisor, Destination, Transport, Accommodation, Itinerary, Validation, Aggregator), status indicators, current node, event timeline, side inspector with input/output/tool calls/duration/tokens/model/cost/errors. Nodes and edges must be real React Flow components, not SVG screenshot backgrounds.
- `/studio/runs/:runId`: same interactive graph scoped to actual run. Poll/subscribe to live events. Support pan, zoom, fit-to-view, keyboard and touch control, node selection, logs/state tabs, and truthful status.
- `/studio/runs/:runId/replay`: persisted timestamped event replay with play/pause, speed, seek, step forward/back, events and selected node state. A replay must reconstruct UI from saved historical events, not pretend to re-run paid LLM calls.
- `/evaluations`: one-run quality evaluation summary with calculation method, metric provenance, honest status if no judge scores; test history, errors, source/evidence links where available.
- `/evaluations/compare`: compare two or more runs/configurations on a common evaluation dataset and rubric; comparison table/charts with meaningful deltas, model names, prompt versions, latency, cost, deterministic versus judge metrics.
- `/costs`: filters by date/user-owned run/model/agent; measured and estimated totals, trends, tokens, per-model and per-agent costs; data from DB.
- `/costs/runs/:runId`: detailed single-run cost analytics with per-agent event breakdown, model usage, token inputs/outputs, tool/API costs, duration, pricing-source flags, exports; totals must reconcile.

MOBILE:
- Match the mobile reference mockups for dashboard, trip planner, My Trips, Agent Studio. Hide desktop sidebar and use compact header/bottom navigation where appropriate. Agent graph stays pannable/zoomable; inspector becomes a bottom drawer. Ensure no overflow or microscopic tables.
- Tablets should work naturally between desktop and mobile.

EVERY visible navigational item, primary action, dropdown, tab, search input, pagination control, replay control, and core chart drilldown must either WORK or be clearly disabled with an honest label and explanation. No decorative buttons suggesting unsupported functionality.

## 4. REUSABLE UI SYSTEM AND PIXEL-ACCURACY PROCESS

Build a reusable design system: AppShell, LightSidebar, DarkSidebar, TopBar, PageHeader, StatCard, TripCard, DataTable, FilterBar, MetricCard, ChartCard, EmptyState, ErrorState, LoadingSkeleton, ConfirmDialog, Toast, StatusPill, AgentNode, AgentInspector, ReplayToolbar, Timeline, CostLegend, QualityMetric.

Create centralized CSS design tokens for:
- canvas and card colors in light/dark themes; indigo CTA and mint success; accessible warning/error colors
- font family, font weight, heading scale, body scale, table text; consistent font rendering
- 4/8px spacing grid, margins, sidebar/topbar dimensions, radii, borders, shadow and glow intensity
- form sizes, focus ring, hover states, disabled/loading states
- responsive breakpoints and safe-area handling

Visual acceptance workflow, **for each route**:
1. Open its corresponding source image from `MOCKUP-UI/`.
2. Determine the reference image's aspect ratio and likely viewport. Match reference screenshot size when possible (desktop around 1440–1600px width and matching height; portrait mobile about 390–430 CSS px; verify rather than assuming).
3. Implement with real semantic HTML, reusable components, and local image assets.
4. Seed and open the route in a browser at matched dimensions.
5. Capture a Playwright screenshot and compare side by side with the mockup (if available, generate a diff/overlay artifact). Compare screenshot geometries, sidebar/hero heights, typography, card positioning, gaps, radii, image placement, shadows, charts, and visual density. Different dynamic demo figures are acceptable if the layout matches.
6. Refine until major mismatches are fixed. Record unresolved differences in `docs/visual-deviations.md`; NEVER claim measured pixel perfection if it was not verified.
7. Add visual-regression snapshots for the local app itself. Do not use generated mockups as Playwright's functional expected screenshots blindly; mockups contain non-renderable/imagined details.

Do not crop mockups to use as the entire page. If scenic photo regions can be extracted cleanly from user-provided mockups, place cropped/optimized assets in `frontend/public/assets/` with provenance documentation, ensuring no UI chrome or embedded fake labels remain. If clean crops aren't possible, use local gradients/vector illustrations and document the visual limitation; do not hotlink unreliable stock image sites or require an image API.

## 5. AUTHENTICATION, DATA OWNERSHIP, AND DATABASE

Use SQLite as the sole required database, with Alembic migrations and persistent application tables. Suggested schema:
- `users`, `sessions`, `password_reset_tokens`, `user_preferences`
- `trips`, `trip_versions`, `trip_days`, `trip_activities`, `trip_recommendations`
- `conversations`, `messages`
- `agent_runs`, `agent_events`, `tool_invocations`, `model_invocations`
- `evaluation_runs`, `evaluation_metrics`, `evaluation_evidence`, `benchmark_cases`
- `model_pricing_snapshots`, `cost_line_items`

Define documented PKs/FKs, indices, user_id ownership, created_at/updated_at UTC timestamps, and cascade/archive behavior. JSON fields are fine for structured payloads if validated by Pydantic models. Keep a separate checkpoint DB file if using the LangGraph SQLite checkpointer to avoid concurrent schema collisions.

Use secure salted hashing (Argon2 or comparable), revocable opaque session tokens stored hashed, HttpOnly cookies, local dev SameSite settings, server-enforced session checking, rate-limiting/basic throttling for auth, CSRF mitigation appropriate to cookie auth, and redaction of sensitive inputs. Restrict every trip, run, event, evaluation, and cost query to the authenticated owner; verify cross-user isolation in tests.

Only seed demo accounts in local/demo mode. Offer local reset/seed script. Never ship the demo password as a production credential.

## 6. REAL MULTI-AGENT LANGGRAPH ENGINE

Build a genuine **LangGraph StateGraph**. Do not fake multi-agent calls using one monolithic model response or sequential React timers.

SHARED STATE (typed): `user_id`, `trip_id`, `thread_id`, `run_id`, `trip_request`, `normalized_request`, `constraints`, `research`, `transport_options`, `accommodation_options`, `itinerary_days`, `budget_breakdown`, `travel_advisories`, `validation_findings`, `messages`, `agent_errors`, `tool_results`, `final_plan`, `revision_number`, `replan_requests`, and event metadata. Parallel writes must be isolated or use defined reducers.

NODES:
- `supervisor`: parses requirements, identifies missing constraints, selects needed agents and safe bounded actions. Missing essential fields must produce a user clarification state instead of guessed bookings.
- `destination_research`: researches destinations and activities using the LOCAL curated travel catalog/tool adapter; in OpenAI mode reasons about returned catalog data without claiming a live web search.
- `transport`: retrieves deterministic sample transport options from local provider adapter; never advertises them as live inventory or verified prices.
- `accommodation`: retrieves local sample stays from an adapter; returns price ranges and evidence provenance.
- `itinerary`: generates coherent day-by-day schedules based on agent findings and times/distances estimated from local data; OpenAI mode can use the model here.
- `validator`: **deterministic Python**, verifies itinerary completeness, date count, estimated budget totals, conflicting activities, required preferences, field types, duplicate items, missing evidence, and source freshness. This is not an LLM agent.
- `aggregator`: compiles validated results into a structured final plan and concise user-friendly explanation. In OpenAI mode may call the LLM for narrative/justification, preserving deterministic numbers.

WORKFLOW:
`START -> supervisor -> parallel(destination, transport, accommodation) -> itinerary -> validator -> aggregator -> END`.
The exact parallel fan-out/fan-in must follow LangGraph's supported primitives and state reducer semantics. Allow bounded loop(s) back to an affected specialist/itinerary when validator finds correctable problems; cap retries (e.g., 2) and fail gracefully. A revision request should reuse results where still valid and re-run only affected nodes when safe. Tests must prove actual graph branching, parallelism, state updates, and loop termination.

Create tool interfaces with a provider pattern:
- `TravelCatalogProvider` deterministic offline local datasets (destinations, attractions, sample hotel/transport options, seasonal notes, estimated routes/coordinates, image asset references).
- `LLMProvider` has `DemoLLMProvider` and `OpenAILLMProvider` implementations.
- Weather, maps, hotels, airlines **must not require external keys**. No live weather claims; show seasonal guidance as such. Use a static/local schematic route view if necessary.
- Trip budgets, times, currencies, and metadata are stored as structured types, not scraped from text.

A run must create persisted unique IDs and capture every node's lifecycle, with start/end timestamps, status, inputs (sanitized), output summaries, tool calls, errors, retries, model usage and cost. Use LangGraph stream/event projection APIs available in the installed release; follow current official patterns, not outdated guessed event shapes. Use the SQLite LangGraph checkpointer keyed by an authorized scoped thread ID. Resume state across local app restarts and preserve previous versions.

## 7. TWO AI MODES — KEY WILL BE ADDED LATER

DEFAULT `.env.example`:
```
APP_ENV=local
AI_MODE=demo
OPENAI_API_KEY=
OPENAI_MODEL=
DATABASE_URL=sqlite+aiosqlite:///./data/travelgraph.sqlite
CHECKPOINT_DB_PATH=./data/checkpoints.sqlite
FRONTEND_ORIGIN=http://localhost:5173
SESSION_SECRET=replace-in-local-env-with-a-random-long-value
SEED_DEMO_DATA=true
```

- `AI_MODE=demo`: **must be fully functional with NO OpenAI key**, and must make no external AI calls. Deterministic local mock/tool agents should actually execute inside a LangGraph graph; seeded fixtures should produce coherent plans, events, evaluations, costs, and historical replay.
- `AI_MODE=openai`: only available if `OPENAI_API_KEY` and a compatible `OPENAI_MODEL` are set; otherwise fail with a useful configuration error, never a broken UI or a secret leak. Default remains demo even if a key is present: **do not silently trigger paid usage**. An API usage confirmation or visible 'Live AI' mode badge is desirable.
- Use the official OpenAI backend SDK and supported structured-output pattern; validate JSON using Pydantic; handle refusal, missing output, malformed business content, timeout, rate limit, and provider failure. Keep OpenAI calls only in backend services.
- `OPENAI_MODEL` is configurable: do not bake in a model name that might be retired or unsupported on the user's account. Document a tested example once verified. Avoid fabricating support for inaccessible models.
- Preserve conversation/trip context and user's preferences within authorized graph sessions. Bound LLM recursion, tokens, retries, concurrency, and per-run maximum estimated spend.
- No tool/web travel searches unless explicitly integrated later. OpenAI model knowledge does not equal real-time travel availability.

## 8. LIVE EXECUTION, EVENT STREAMING, AND REPLAY

Use FastAPI + same-origin/proxied **Server-Sent Events (SSE)** for run updates. Design a typed event model (`id`, `run_id`, `seq`, `ts`, `type`, `node_id`, `status`, `payload`) and persist events in the database BEFORE or reliably alongside publishing them. Support reconnection using persisted sequence/cursor and client refresh, rather than losing the stream when navigation changes. Ensure auth-scoped streams and no secret/raw private leakage.

Emit `run.created`, `run.started`, `agent.started`, `agent.progress`, `tool.called`, `tool.succeeded`/`tool.failed`, `agent.completed`/`agent.failed`, `state.updated`, `validation.warning`, `run.completed`/`run.failed`. Persist event timestamps, node transitions and summaries.

React Flow should show **actual execution graph and statuses**, including parallel agents and repeated invocations. Each node opens a real inspector with input, output, timing, costs, tokens and errors when available. Running nodes animate subtly. In replay mode, read stored events, reconstruct statuses at selected timestamp, render timeline, and support pause/play/speed/seek/step. Replaying a run must NOT call OpenAI again.

## 9. EVALUATION LAB — NO FICTIONAL SCORES

Support two kinds of evaluation:
A. Deterministic: budget compliance, required day count, date validity, missing fields, preference coverage, itinerary completeness, scheduling conflicts detected by rules, tool success rate, error count, latency. Define thresholds and rubrics; use actual trip/run data.
B. Optional model-as-judge in `AI_MODE=openai`: structured rubric for relevance, coherence, feasibility, recommendation quality, supported/unsupported claims; store exact judge model/prompt version, sampled evidence, rubric version, tokens/cost, and uncertainty. Avoid pretending judgment equals objective truth. Make this opt-in because it incurs cost.

In `AI_MODE=demo`, seed historical judge outputs clearly marked `Sample evaluation (demo)`. New demo runs get real deterministic metric scores; unavailable subjective judge metrics should show `Not evaluated` unless a deterministic demo fixture is explicitly assigned and labeled as a fixture. Never use random 92% as a universal default. Overall score must only appear when its component weights are meaningful and provenance is displayed. Comparison screen must compare the same metric definitions/benchmarks and display missing data honestly.

Provide local benchmark fixtures (at least 8 scenarios: Goa budget trip, Manali family, Udaipur heritage, Kerala nature, solo city break, budget conflict, missing destination, unrealistic dates). Add a 'Run Benchmark' action in demo mode and persist results. Show errors, flags, metric evidence, and click-through to run/trip.

## 10. COST EXPLORER — RECONCILED, EXPLAINABLE METRICS

Create a cost accounting model:
- Per model invocation: model, provider, timestamp, input tokens, output tokens, optional cached/reasoning token subfields, pricing snapshot ID, estimated amount and status of completeness.
- Per tool invocation: tool name, call count, optional known fee, timing, provenance, status.
- Per run: sum of known model + known tool charges, plus explicit unknown components. Do not report unknown as zero.
- Per agent: aggregate by node invocation and tool ownership. Re-run events must be counted correctly. Show displayed currency and conversion provenance (do not invent FX rates).
- The travel **vacation budget is INR**, while provider **AI cost should default to USD**; do not mix them on one chart.
- Pricing must be configurable/versioned in a local pricing catalog with source date and support for model-specific input/output/cached pricing. If rates have not been configured/verified, show token usage and 'Cost unavailable' rather than a made-up price.
- In demo mode store internally consistent sample costs, clearly labeled Demo.

Charts: total cost, total tokens, avg cost per completed planning run, cost trend, cost by agent, cost by model, per-node cost waterfall, token split, run detail and export CSV. All filters must apply to real stored records. Include no-data and partially-priced states.

## 11. COHERENT DETERMINISTIC SEED DATA (DO THIS BEFORE BUILDING UI)

Write idempotent seed logic (`python -m app.seed` or equivalent) with safe reset, per-user ownership and migrations. Seed two local-only demo accounts:
- `demo@travelgraph.local` / `TravelGraphDemo!2026`
- `reviewer@travelgraph.local` / `TravelGraphDemo!2026`
Display the local demo credentials in README and (only in demo mode) in a clearly labeled login helper. Give the second account separate data to verify isolation.

Seed at least 12 varied trips: Goa, Manali, Jaipur, Udaipur, Munnar, Kerala backwaters and other realistic sample destinations; cover completed, in-progress, draft and favorited states. Example dashboard count for primary account: 12 trips, 7 completed, 2 in progress, 3 drafts. Derive these numbers from DB, and seed coherent agent runs, events, evaluations and costs for selected trips. Seed time series spanning at least 30 days for meaningful chart filters.

The MAIN demonstration scenario MUST be consistent across all screens:
- Trip: `Goa Getaway` / `Goa Escape Plan`
- Origin: Kolkata, India; destination: Goa, India
- Dates: Jan 12–16, 2027 (five calendar days / four hotel nights)
- Travelers: 2
- Trip budget: INR 35,000 total, not per person
- Interests: beaches, local Goan food, relaxed sightseeing
- Example itinerary: arrival & North Goa; beaches & forts; Old Goa/Panaji culture & food; South Goa; checkout/departure
- SAMPLE TRAVEL COSTS (not live prices): round-trip intercity travel ₹12,500 + accommodation ₹9,200 + meals ₹5,400 + local travel ₹3,650 + attractions ₹2,600 + contingency ₹1,500 = **₹34,850**, leaving **₹150** against ₹35,000. Show labeled estimates only.
- Demo example historical run ID: `TG-1047` (preserve unique IDs internally; can have public formatted ID)
- Demo run wall time example: 14.2 s. Agent tasks may overlap in parallel; do not sum individual durations to get wall time.
- Demo token totals example: **28,960 input + 7,460 output = 36,420 total**. For 6 LLM-node roles, use input/output: Supervisor 2,900/740, Destination 5,600/1,250, Transport 4,300/1,100, Accommodation 4,600/1,250, Itinerary 7,600/2,400, Aggregator 3,960/720. Sum and validate these in automated tests.
- Demo historical AI run cost example: **$0.237 total** = **$0.217 model costs + $0.020 tool costs**. Attribute total by role including tools: Supervisor $0.018; Destination $0.043; Transport $0.038; Accommodation $0.041; Itinerary $0.074; Aggregator $0.023. Sum MUST equal $0.237. These numbers are **seeded illustrative example charges**, not current OpenAI invoice prices. If necessary, mark costs simulated in every demo analytics view.
- Build historical event timestamps, transitions and simulated task overlaps compatible with the above totals and durations.
- Seed named models and comparison evaluations as DEMO historical scenarios only. Their score cards, tables, and charts must be mathematically consistent.
- Seed consistent local catalog data for each destination, e.g., attractions, seasonal guidance and sample transport/hotels with valid references and realistic location labels. No claims of real-time inventory.
- Provide local demo data provenance labels in UI and README.

NOTE: Mockup images may show conflicting costs, dates, names, model labels, or run counts. Keep the **design**, but prioritize this coherent seed dataset for values. Record changes from mockups.

## 12. REQUIRED API CONTRACTS

Create OpenAPI-documented APIs with consistent errors, pagination, Pydantic response models, ownership enforcement and versioning. Reasonable endpoints include:
- `POST /api/v1/auth/signup`, `/login`, `/logout`, `/forgot-password`, `/reset-password`; `GET /api/v1/auth/me`
- `GET/PATCH /api/v1/me/preferences`, `PATCH /api/v1/me/profile`, `POST /api/v1/me/change-password`, `GET /api/v1/me/export`, `DELETE /api/v1/me`
- `GET/POST /api/v1/trips`, `GET/PATCH/DELETE /api/v1/trips/{id}`, `/favorite`, `/duplicate`, `/versions`, `/replan`
- `POST /api/v1/runs`, `GET /api/v1/runs`, `GET /api/v1/runs/{runId}`, `GET /api/v1/runs/{runId}/events`, `GET /api/v1/runs/{runId}/stream` (SSE), `/graph`
- `POST/GET /api/v1/evaluations`, `GET /api/v1/evaluations/{id}`, `POST /api/v1/evaluations/compare`, `POST /api/v1/evaluations/benchmark`
- `GET /api/v1/analytics/dashboard`, `GET /api/v1/analytics/costs`, `GET /api/v1/analytics/costs/runs/{runId}`
- `GET /api/v1/health` with non-sensitive readiness status, AI mode and database connectivity

Adjust endpoint names if warranted, but fully wire all frontend features to actual API methods. Build typed TS API interfaces from Pydantic/OpenAPI schema, or maintain matching Zod contracts and tests.

## 13. USER JOURNEYS AND BEHAVIOR

At minimum, a seeded demo user can:
1. Open the site, login using seed credentials, see personalized dashboard cards/counts.
2. Start new trip from a natural-language request, optionally edit structured details, and run a REAL LangGraph demo workflow with progress events.
3. Enter Agent Studio while the run is executing; watch actual node status updates, inspect details and logs, then finish without a reload.
4. Open the generated five-day itinerary, change day tabs, see trip budgets/hotel/transport suggestions, save it, favorite it, duplicate it and edit the plan.
5. Reload or restart backend and retrieve the trip and its run history.
6. Replay persisted run events with play/pause/seek/speed and inspect event-specific node state without calling AI.
7. Run deterministic evaluation, see method/evidence, run local benchmark, and compare two evaluated runs.
8. Explore costs/usage by agent/model/run/date; click into a detailed run and export CSV. All totals reconcile.
9. Update their preferences, sign out/in, and verify the second account cannot access the first account's runs or trips.
10. Complete a password reset locally with development-only recovery flow.
11. Use main journeys comfortably at mobile viewport widths and keyboard navigation.

No user-visible feature should be a permanently spinning loader, fake progress animation disconnected from graph state, or route that renders an empty stub.

## 14. TESTING, VALIDATION AND VISUAL QA

MANDATORY:
- Backend unit tests for graph routing, state reducers, idempotent seeds, budget math, travel date logic, validation, model accounting, role/user isolation, SSE event ordering, event replay, evaluator rubric, password reset, and OpenAI-key-missing behavior.
- Integration tests for Auth -> Trip -> Run -> Events -> Itinerary -> Evaluation -> Cost across demo mode.
- Frontend tests for key forms, routing, trip filters, favorites, graph-node selection, replay controls, API loading/error states, chart data aggregation.
- Playwright E2E tests in Chromium for demo account login, generate trip, reopen trip, replay, evaluation, cost explorer, settings, logout, and responsive screens.
- Desktop screenshots at reference-aligned viewports and mobile screenshots around 390x844 (match actual references). Save results in `docs/screenshots/` and a `docs/visual-qa.md` checklist; use Playwright screenshot comparisons to create stable internal regression baselines.
- TypeScript `tsc` no errors, frontend production build successful, backend imports clean, migrations apply, seeds run twice without duplicates, tests pass.
- Confirm all routes accessible, no broken images, no browser console errors, no unhandled promises, no permanent UI placeholders.
- Confirm app runs in demo without OPENAI_API_KEY and that enabling OpenAI mode is a configuration switch, not a rewrite.
- If API calls can't be tested without a user key, use mocked SDK calls in automated tests and honestly mark live-provider smoke test pending.

Do not fabricate passing tests or claim visual matching without running screenshot comparison. If runtime limitations block a check, report exactly which command failed and why, and continue with feasible verification.

## 15. WINDOWS COMMANDS AND LOCAL DEVELOPER EXPERIENCE

Provide PowerShell scripts that:
- `scripts/setup.ps1`: check Python/npm, create `.venv`, install backend and frontend deps, copy `.env.example` to `.env` only if missing, create local data directories, run migrations, idempotently seed.
- `scripts/start-backend.ps1`: start FastAPI/Uvicorn in local environment.
- `scripts/start-frontend.ps1`: start Vite.
- `scripts/dev.ps1`: optionally start both with clear windows/tabs or well-managed PowerShell processes.
- `scripts/seed.ps1`: safe idempotent demo seed.
- `scripts/reset-demo.ps1`: require explicit confirmation before removing local demo DB, then migrate and reseed.
- `scripts/test.ps1`: run backend/frontend/E2E checks with clear error reporting.

Write an excellent `README.md` with exact Windows commands, ports, troubleshooting, demo account, feature matrix, screenshots, graph explanation, API docs, architecture, security boundaries, offline limitations, evaluation definitions, cost provenance and later OpenAI setup. No mandatory `make`, Bash, Docker, or paid services.

`OPENAI_API_KEY` must remain blank for the initial build. When the user is ready, tell them to put it in **backend local `.env`** (or root `.env` loaded by backend), set `AI_MODE=openai`, set a valid accessible `OPENAI_MODEL`, restart the backend, and run an explicit live smoke test. **Do not request or invent the key now**. Never paste an API key into a chat response or frontend env file.

## 16. WORK EXECUTION PLAN — IMPLEMENT EVERYTHING, NOT JUST PLANNING

Execute sequentially in coherent vertical slices, and update docs after each:
1. **Inspect mockups** and create inventory + screen mapping + design tokens.
2. **Initialize backend/frontend** with correct package versions and Windows scripts; verify clean starts.
3. **Schema, migrations, auth and seed data**; verify dashboard endpoints and user isolation.
4. **Implement the actual demo LangGraph graph** and deterministic tools, checkpointing, event store, SSE, trip creation.
5. **Implement OpenAI provider adapter** as backend-only optional mode; test with mocks and no secret.
6. **Build shared visual components**, then high-fidelity light auth, onboarding, dashboard, create-trip, itinerary, trips, settings.
7. **Build high-fidelity dark views**: live graph, inspector, replay, Evaluation Lab/comparison, Cost Explorer/run breakdown.
8. **Connect all UI actions and data**; implement all mobile layouts from reference.
9. **Evaluate and cost accounting**, real benchmark/test data, chart consistency and exports.
10. **Run E2E and screenshot visual QA**, iterate until high-priority mismatches and failures are fixed.
11. **Deliver setup docs and tested commands**, report what actually passed and what remains dependent on a real OpenAI key.

If you must work over multiple Agent context windows, write/maintain `docs/AGENT-HANDOFF.md` with exact current status, files changed, commands run, blockers, next unchecked task, so you can resume without losing context. Continue implementing instead of repeatedly asking the user to approve each routine phase. Ask the user only for choices or permissions that are strictly necessary, destructive, or materially consequential.

## 17. STRICT DEFINITION OF DONE

The work is finished only if ALL of the following are true:
- The reference mockups were actually inspected and a filename-to-route mapping exists.
- Every major light and dark page is implemented with meaningful responsive design, and both desktop/mobile mockups were compared to actual screenshots.
- The user can locally register/login, manage profile, recover password, create/edit/favorite/delete trips and see persisted state.
- Demo travel generation runs through the REAL LangGraph graph and returns coherent, budget-checked itinerary data.
- SSE status events drive a real interactive orchestration graph, and persisted events power replay.
- Evaluation Lab works with honest deterministic scoring, seeded history, comparisons and optional AI judge capability.
- Cost Explorer works with reconciled model/tool costs, token usage, filters, breakdowns and provenance.
- All data is per-user; seed fixtures are consistent and demo-only.
- No paid API credentials are required for demo. Only the backend `OPENAI_API_KEY` is needed to enable OpenAI later.
- Windows PowerShell scripts and README work; frontend builds; backend tests and browser E2E tests pass (or blockers reported exactly).
- Primary UI routes/actions do not contain fake, dead or misleading interactive elements.
- `docs/visual-qa.md` and `docs/AGENT-HANDOFF.md` accurately reflect tested status.

### IMMEDIATE ACTION

Start NOW with workspace inspection. First list and visually inspect every image in `./MOCKUP-UI/`, create the design inventory/mapping and implementation checklist, then continue directly into actual code creation in the order above. Do not stop after writing a plan. Implement, run, debug, visually compare, test, and iterate until the complete local demo is usable. Leave `OPENAI_API_KEY` blank and finish with explicit instructions for enabling it later.
