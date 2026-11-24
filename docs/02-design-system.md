# Design System — TravelGraph AI

## Dual Experience

| Token group | Light Travel Workspace | Dark Intelligence Workspace |
|---|---|---|
| Canvas | `#F5F7FB` / soft lavender wash | `#0B0E17` midnight navy |
| Surface | `#FFFFFF` cards | `#141827` / `#1A1F33` glass cards |
| Text | `#0F172A` navy | `#E8ECF8` |
| Muted | `#64748B` | `#94A3B8` |
| Primary CTA | Indigo `#6366F1` → `#4F46E5` | Indigo glow `#818CF8` |
| Success / mint | `#10B981` / `#2DD4BF` | Neon mint `#34D399` |
| Warning | `#F59E0B` | `#FBBF24` |
| Danger | `#EF4444` | `#F87171` |
| Borders | `#E2E8F0` | `rgba(129,140,248,0.25)` glow |

## Typography

- Display / UI: **Plus Jakarta Sans** (not Inter/Roboto/system)
- Mono metadata: **IBM Plex Mono**
- Scale: 12 / 13 / 14 / 16 / 18 / 24 / 32 / 40
- Weights: 500 medium UI, 600 semibold headings, 700 bold hero

## Layout

- Sidebar width: **248px** desktop; hidden `<1024px`
- Topbar height: **64px**
- Content max: fluid inside shell; page padding `24px` desktop / `16px` mobile
- Radius: cards `16px`, inputs `12px`, pills `999px`, buttons `12px`
- Spacing grid: 4 / 8
- Soft shadow light: `0 8px 24px rgba(15,23,42,0.06)`
- Dark glow: `0 0 0 1px rgba(129,140,248,0.35), 0 0 24px rgba(99,102,241,0.15)`

## Breakpoints

- `sm` 640 · `md` 768 · `lg` 1024 · `xl` 1280 · `2xl` 1536
- Mobile: bottom nav (Home / Plan / My Trips / Studio); studio inspector → bottom drawer

## Components (required)

AppShell, LightSidebar, DarkSidebar, TopBar, MobileBottomNav, PageHeader, StatCard, TripCard, DataTable, FilterBar, MetricCard, ChartCard, EmptyState, ErrorState, LoadingSkeleton, ConfirmDialog, Toast, StatusPill, AgentNode, AgentInspector, ReplayToolbar, Timeline, CostLegend, QualityMetric, AuthSplitLayout.
