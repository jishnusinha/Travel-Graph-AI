# 07 — Terra UI, routes and frontend implementation

## Design direction

Preserve the existing TravelGraph dark Intelligence Workspace and read-only `MOCK-UP/` images. Introduce a refined editorial light theme in the travel workspace; use scoped CSS tokens rather than rewriting dark styles. Audit current `index.css`, Logo, AppShell, Sidebars, TopBar, mobile nav, CoverImage and UI components first.

Terra palette: forest `#243E36`, ivory `#F6F3EB`, clay `#BB7955`, sage `#A5B4A0`, ink `#222722`, muted `#59665E`, white `#FFFFFF`. Dark studio retains existing navy/indigo/mint tokens. Choose licensed local fonts (editorial serif e.g. Playfair Display, sans e.g. Manrope/Inter) or system fallback, no runtime CDN. Use high-contrast accessible text and focus rings; clay is accent, not low-contrast small text. Desktop 1440, tablet 768, mobile 390 CSS pixels. Use generous whitespace, restrained motion, image-rich editorial cards, soft borders, no excessive glass/gradients. Follow reduced-motion preference. Every photo has alt and attribution. Never use mockup screenshots as full-page backgrounds.

## Route map and integration

| Route | Implementation |
|---|---|
| `/` | public Terra landing; replace current unconditional dashboard redirect, authenticated CTA goes to explore or dashboard |
| `/login`, `/signup`, `/forgot-password`, `/reset-password/:token`, `/onboarding` | existing flows; brand and photos updated carefully, preserve routing/security |
| `/dashboard` | upgrade existing overview; discovery search, curated collection, recent trips, genuine user counts |
| `/explore` | new search, filter, results and collection browser |
| `/explore/map` | map/list view sharing search state |
| `/explore/compare` | compare selected 2–3 canonical destinations |
| `/destinations/:slug` | guide, photos, attraction list, contextual Q&A, citation drawer and Plan trip CTA |
| `/saved` | saved destinations, compare and unsave |
| `/trips/new` | existing planner prefilled from selection, no duplicate trip form |
| `/trips`, `/trips/:tripId`, `/trips/:tripId/edit` | existing journeys, enhanced cited itinerary and budget controls |
| `/studio`, `/studio/runs/:runId`, `/studio/runs/:runId/replay` | preserve and enhance |
| `/intelligence/retrieval` | retrieval playground, dark shell |
| `/intelligence/knowledge` | corpus stats and entity graph, dark shell |
| `/evaluations`, `/evaluations/compare`, `/costs`, `/costs/runs/:runId`, `/settings` | preserve, extend according to plan 10 |

Update lazy route imports, protected routes, nav.ts `WORKSPACE_NAV`, `INTELLIGENCE_NAV`, `DARK_PREFIXES`, mobile nav, active route matching, breadcrumbs. Public search redirect preserves pending query through login/onboarding; verify existing auth redirect logic. Do not expose protected data on landing. Existing routes must remain directly accessible.

## Screen specifications

**Landing:** responsive header brand + Explore + How it works + Sign in; panoramic actual destination photo with readable overlay, editorial H1 “Somewhere new. Something unforgettable.”, natural-language search composer, chips that populate meaningful examples, curated collections (mountains, culture, coastal, nature) derived from snapshot tags, destination grid, simple Discover→Plan→Explore narrative, footer with sources and privacy. CTA routes to real discovery, not fake chat. Local images optimized with responsive sizes and lazy loading below fold.

**Explore:** search composer top, active filter chips, responsive two/three-column cards, list/map toggle, sort by relevant/name only unless data supports cost/season. Each card: cover, region, destination, short sourced description, match reasons, evidence count, unknown indicators, save, compare, open details. Selecting a card never starts a paid run. Use loading skeleton, retry, no-results suggestions and missing-index state. Search explicit submit or debounced with cancellation; URL stores non-sensitive filter state, not full private query. Avoid stale response overriding new search. Keep accessible compare tray for up to 3 IDs.

**Details:** cinematic gallery, breadcrumb, name/region, save and Plan trip buttons, cited overview, attractions with map pins, local culture/food, seasonality (historical vs forecast), estimated cost ranges, source cards, nearby places if supported. “Ask Terra about this place” returns structured cited claims and uncertainty, not raw uncontrolled Markdown. Citation drawer displays exact excerpt, section, source URL, revision date, license, highlight where possible and related claims. Escape all text. Gallery includes author credit. Handle missing images, price, coords and text honestly.

**Dashboard:** preserve user's recent trips, status, existing metrics, navigation; add discovery hero and curated destinations backed by actual corpus, meaningful empty state for new user. Use real user counts from backend, not generated demo values.

**Planner:** preserve existing form and trip creation; destination canonical selection and handoff through router state or draft, editable confirmed constraints, clear budget basis, source/estimate labels, run status, candidate-selection screen if ambiguous. Existing offline fixtures remain accessible.

**Trip details:** timeline and map toggle, cite chips per activity, estimate breakdown, unknown flags, version history, save, export/print, reorder/regenerate controls as plan 08. Mobile bottom drawer instead of cramped third panel. Keep existing agent status and run link.

## Components and state

Create small reusable `TerraSearchComposer`, `DestinationCard`, `DestinationGallery`, `MatchReasons`, `FilterChips`, `CompareTray`, `CitationChip`, `CitationDrawer`, `SourceAttribution`, `TravelEstimate`, `DestinationMap`, `EmptyEvidenceState`, `KnowledgeStatus`, `GroundedAnswer`, `TripHandoff`. Use existing `lib/api.ts` auth/CSRF client and TanStack Query if already configured (otherwise extend existing query conventions). Typed contracts from plan 04; stable cache keys include snapshot ID and user scope. Clear user cache on logout. No browser-side provider secrets or raw vector access. All visible controls functional or explicitly unavailable, no dead interactions.

## Visual QA

Capture Playwright desktop/mobile screenshots for landing, explore/results, details, comparison, map, saved, planner and existing dark pages. Evaluate overflow, typography, image cropping, contrast, keyboard tab order, modal focus trap, screen reader names, mobile nav, reduced motion, touch targets and offline assets. Compare existing mockup-driven screens with original reference where applicable; Terra changes intentional and documented in `docs/visual-deviations.md`. Use local screenshots as regression artifacts, not generated mockups as exact baselines. No fabricated pixel-perfect claims. New pages must use real backend data; mock fixtures only in isolated component tests/stories.

## Exit gate

A new user signs up, finishes/skips onboarding, searches, inspects source, saves and compares, opens destination, prefills planner, generates a real offline cited trip, reloads it and navigates to its trace. Desktop/mobile E2E and accessibility smoke pass; no major console errors, broken images, dead links or inaccessible dialogs. Existing auth and studio smoke pass.
