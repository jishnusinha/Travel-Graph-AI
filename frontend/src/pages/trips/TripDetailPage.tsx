import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  Bed,
  Bookmark,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Clock,
  Copy,
  History,
  IndianRupee,
  Info,
  Lightbulb,
  Loader2,
  Map as MapIcon,
  MapPin,
  Pencil,
  RefreshCw,
  Share2,
  Users,
  Wallet,
  Bus,
  Workflow,
  Trash2,
  type LucideIcon,
} from 'lucide-react'
import { DonutChart } from '@/components/charts/charts'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { CoverImage } from '@/components/ui/CoverImage'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { Skeleton } from '@/components/ui/Skeleton'
import { StatusPill } from '@/components/ui/StatusPill'
import { useToast } from '@/components/ui/Toast'
import { useRunGraph, useRuns, useTrip, useTripActions, useTripVersions } from '@/hooks/queries'
import { AGENTS } from '@/lib/agents'
import { ApiError } from '@/lib/api'
import type { Trip, TripActivity } from '@/lib/types'
import { cn, formatDate, formatDateRange, formatINR, titleCase } from '@/lib/utils'

type Tab = 'itinerary' | 'transport' | 'accommodation' | 'budget' | 'map'
const TABS: { id: Tab; label: string; icon: LucideIcon }[] = [
  { id: 'itinerary', label: 'Itinerary', icon: Calendar },
  { id: 'transport', label: 'Transport', icon: Bus },
  { id: 'accommodation', label: 'Accommodation', icon: Bed },
  { id: 'budget', label: 'Budget', icon: Wallet },
  { id: 'map', label: 'Map', icon: MapPin },
]

export default function TripDetailPage() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [tab, setTab] = useState<Tab>('itinerary')
  const [dayIdx, setDayIdx] = useState(0)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [confirmReplan, setConfirmReplan] = useState(false)

  const tripQ = useTrip(tripId, undefined)
  const trip = tripQ.data
  const planning = trip?.status === 'in_progress'
  // poll while agents are still working on this trip
  useTrip(planning ? tripId : undefined, planning ? 3000 : false)
  const runs = useRuns({ trip_id: tripId, page_size: 5 })
  const latestRun = runs.data?.items[0]
  const graph = useRunGraph(latestRun?.id)
  const versions = useTripVersions(tripId)
  const actions = useTripActions()

  const fail = (title: string) => (e: unknown) => toast.error(title, e instanceof ApiError ? e.message : undefined)

  if (tripQ.isPending) return <DetailSkeleton />
  if (tripQ.isError)
    return (
      <div className="mx-auto max-w-xl pt-10">
        <ErrorState error={tripQ.error} title="Trip unavailable" onRetry={() => tripQ.refetch()} />
        <p className="mt-4 text-center"><Link to="/trips" className="font-semibold text-primary-strong hover:underline">Back to My Trips</Link></p>
      </div>
    )
  if (!trip) return null

  const day = trip.days[Math.min(dayIdx, Math.max(trip.days.length - 1, 0))]
  const title = trip.plan_title || trip.title
  const remaining = trip.budget_inr - trip.estimated_cost_inr
  const withinBudget = trip.estimated_cost_inr > 0 && remaining >= 0
  const aiRec = trip.recommendations.find((r) => r.kind === 'ai')
  const advisories = trip.recommendations.filter((r) => r.kind === 'advisory')

  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href)
      toast.success('Link copied', 'Anyone signed in to your local workspace with access can open it.')
    } catch {
      toast.error('Could not copy link')
    }
  }

  return (
    <div className="mx-auto max-w-[1280px] space-y-5">
      <section className="relative overflow-hidden rounded-3xl">
        <CoverImage src={trip.cover_image} className="absolute inset-0 size-full" />
        <div className="absolute inset-0 bg-gradient-to-r from-white/92 via-white/70 to-white/10" aria-hidden />
        <div className="relative p-5 sm:p-8">
          <nav aria-label="Breadcrumb" className="mb-3 flex items-center gap-1.5 text-xs text-slate-600">
            <Link to="/trips" className="hover:underline">My Trips</Link> <ChevronRight className="size-3" /> <span className="font-semibold text-primary-strong">{trip.title}</span>
          </nav>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-2xl">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-3xl font-extrabold text-slate-900 sm:text-4xl">{title}</h1>
                <StatusPill status={trip.status} />
              </div>
              <p className="mt-2 line-clamp-2 text-sm text-slate-700">{trip.prompt}</p>
              <ul className="mt-4 flex flex-wrap gap-2 text-xs font-semibold text-slate-700">
                {[
                  [Calendar, `${trip.days.length || '—'} Days`],
                  [Users, `${trip.travelers} Travelers`],
                  [IndianRupee, `${formatINR(trip.budget_inr)} Budget`],
                  [Clock, formatDateRange(trip.start_date, trip.end_date)],
                ].map(([I, label]) => {
                  const Icon = I as LucideIcon
                  return <li key={label as string} className="flex items-center gap-1.5 rounded-xl bg-white/90 px-3 py-1.5 shadow-sm"><Icon className="size-3.5 text-primary" /> {label as string}</li>
                })}
              </ul>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link to={`/trips/${trip.id}/edit`} className="tg-btn tg-btn-secondary tg-btn-sm bg-white text-slate-900"><Pencil className="size-4" /> Edit Plan</Link>
              <button type="button" onClick={() => actions.favorite.mutate({ id: trip.id }, { onError: fail('Could not save') })} aria-pressed={trip.is_favorite} className="tg-btn tg-btn-secondary tg-btn-sm bg-white text-slate-900">
                <Bookmark className={cn('size-4', trip.is_favorite && 'fill-primary text-primary')} /> {trip.is_favorite ? 'Saved' : 'Save'}
              </button>
              <button type="button" onClick={share} className="tg-btn tg-btn-primary tg-btn-sm"><Share2 className="size-4" /> Share</button>
            </div>
          </div>
        </div>
      </section>

      {planning && (
        <div role="status" className="flex flex-wrap items-center gap-3 rounded-2xl border border-primary/30 bg-primary-soft px-4 py-3 text-sm">
          <Loader2 className="size-4 animate-spin text-primary" />
          <span className="flex-1 font-medium">Agents are still planning this trip. This page updates automatically.</span>
          {latestRun && <Link to={`/studio/runs/${latestRun.public_id}`} className="font-semibold text-primary-strong hover:underline">Watch live in Agent Studio</Link>}
        </div>
      )}
      {trip.status === 'draft' && trip.days.length === 0 && !planning && (
        <div role="status" className="flex flex-wrap items-center gap-3 rounded-2xl border border-warn/30 bg-warn-soft px-4 py-3 text-sm">
          <Info className="size-4 text-warn" />
          <span className="flex-1">This trip has no itinerary yet{latestRun?.status === 'failed' ? ' — the last run failed.' : '.'}</span>
          <button type="button" className="tg-btn tg-btn-primary tg-btn-sm" disabled={actions.replan.isPending} onClick={() => actions.replan.mutate({ id: trip.id }, { onSuccess: (r) => navigate(`/studio/runs/${r.run_public_id}`), onError: fail('Could not start planning') })}>
            <RefreshCw className="size-4" /> Generate plan
          </button>
        </div>
      )}

      <div role="tablist" aria-label="Trip sections" className="flex gap-1 overflow-x-auto">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} role="tab" aria-selected={tab === id} type="button" onClick={() => setTab(id)} className={cn('flex h-11 shrink-0 items-center gap-2 rounded-xl px-4 text-sm font-semibold', tab === id ? 'bg-primary-soft text-primary-ink' : 'text-muted hover:bg-primary-soft/60')}>
            <Icon className="size-4" /> {label}
          </button>
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_320px]">
        <div className="min-w-0">
          {tab === 'itinerary' && (trip.days.length === 0 ? (
            <EmptyState icon={Calendar} title="No itinerary yet" description="Once the agents finish, your day-by-day plan will appear here." />
          ) : (
            <div className="grid gap-4 lg:grid-cols-[210px_1fr]">
              <div className="tg-card p-3">
                <h2 className="mb-2 px-1 text-sm font-bold">Trip Days</h2>
                <ul className="flex gap-2 overflow-x-auto lg:flex-col lg:overflow-visible">
                  {trip.days.map((d, i) => (
                    <li key={d.id} className="shrink-0 lg:shrink">
                      <button type="button" aria-current={i === dayIdx} onClick={() => setDayIdx(i)} className={cn('flex w-44 items-center gap-2.5 rounded-xl border p-1.5 text-left lg:w-full', i === dayIdx ? 'border-primary-strong bg-primary-soft' : 'border-line hover:border-primary/50')}>
                        <CoverImage src={d.image} className="size-12 shrink-0 rounded-lg" />
                        <span className="min-w-0"><span className="block text-sm font-bold">Day {d.day_number}</span><span className="block truncate text-xs text-muted">{d.title}</span></span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
              {day && <DayPanel day={day} />}
            </div>
          ))}

          {tab === 'transport' && <KeyValueCard title="Transport" icon={Bus} data={trip.transport} emptyHint="No transport recommendation was produced." />}
          {tab === 'accommodation' && <KeyValueCard title="Accommodation" icon={Bed} data={trip.accommodation} emptyHint="No accommodation recommendation was produced." />}
          {tab === 'budget' && <BudgetPanel trip={trip} />}
          {tab === 'map' && <MapPanel trip={trip} />}
        </div>

        <aside className="space-y-4">
          <section className="tg-card p-4" aria-labelledby="ai-planning">
            <h2 id="ai-planning" className="flex items-center gap-2 text-base font-bold"><Workflow className="size-4 text-primary" /> AI Planning by Multi-Agents</h2>
            <p className="mb-3 text-xs text-muted">A coordinated agent system that plans, verifies and optimizes your trip.</p>
            {!latestRun ? (
              <p className="text-sm text-muted">No agent run is linked to this trip.</p>
            ) : graph.isPending ? (
              <Skeleton className="h-40 w-full" />
            ) : (
              <ul className="space-y-2.5">
                {AGENTS.map((a) => {
                  const node = graph.data?.nodes.find((n) => n.id === a.id)
                  const Icon = a.icon
                  return (
                    <li key={a.id} className="flex items-center gap-2.5">
                      <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary-soft text-primary"><Icon className="size-4" /></span>
                      <span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold">{a.name}</span></span>
                      <StatusPill status={node?.status ?? 'pending'} size="sm" />
                    </li>
                  )
                })}
              </ul>
            )}
            {latestRun && <Link to={`/studio/runs/${latestRun.public_id}`} className="mt-3 inline-block text-xs font-semibold text-primary-strong hover:underline">Open run {latestRun.public_id} in Agent Studio →</Link>}
          </section>

          <section className="tg-card p-4" aria-labelledby="summary">
            <h2 id="summary" className="mb-3 text-base font-bold">Trip Summary</h2>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex items-center gap-2"><span className="grid size-10 place-items-center rounded-xl bg-primary-soft text-primary"><Wallet className="size-5" /></span><div><p className="text-[11px] text-muted">Estimated Cost</p><p className="text-lg font-extrabold">{trip.estimated_cost_inr ? formatINR(trip.estimated_cost_inr) : '—'}</p></div></div>
              <div className="flex items-center gap-2"><span className={cn('grid size-10 place-items-center rounded-xl', withinBudget ? 'bg-mint-soft text-mint' : 'bg-warn-soft text-warn')}><CheckCircle2 className="size-5" /></span><div><p className="text-[11px] text-muted">Budget Fit</p><p className={cn('text-xs font-bold', withinBudget ? 'text-mint' : 'text-warn')}>{trip.estimated_cost_inr ? (withinBudget ? `Within ${formatINR(trip.budget_inr)}` : `Over by ${formatINR(-remaining)}`) : 'Not planned'}</p></div></div>
            </div>
            {aiRec && (
              <div className="mt-3 rounded-xl bg-mint-soft p-3 text-xs">
                <p className="mb-1 flex items-center gap-1.5 font-bold text-mint"><Lightbulb className="size-3.5" /> AI Recommendation</p>
                <p className="text-ink/80">{aiRec.body}</p>
              </div>
            )}
            <p className="mt-3 text-[11px] text-muted">Prices are sample estimates from a local catalog, not live inventory.</p>
          </section>

          {advisories.length > 0 && (
            <section className="tg-card p-4"><h2 className="mb-2 text-sm font-bold">Travel notes</h2><ul className="list-disc space-y-1 pl-4 text-xs text-muted">{advisories.map((a) => <li key={a.id}>{a.body}</li>)}</ul></section>
          )}

          <section className="tg-card p-4" aria-labelledby="versions">
            <h2 id="versions" className="mb-2 flex items-center gap-2 text-sm font-bold"><History className="size-4 text-primary" /> Version history</h2>
            {versions.isPending ? <Skeleton className="h-12 w-full" /> : versions.data && versions.data.length > 0 ? (
              <ul className="space-y-2">
                {versions.data.slice(0, 5).map((v) => (
                  <li key={v.id} className="flex items-center justify-between gap-2 text-xs">
                    <span className="min-w-0"><span className="font-semibold">v{v.version}{v.version === trip.current_version && ' (current)'}</span><span className="block truncate text-muted">{v.change_summary} · {formatDate(v.created_at)}</span></span>
                    {v.version !== trip.current_version && (
                      <button type="button" className="tg-btn tg-btn-ghost tg-btn-sm" disabled={actions.restore.isPending} onClick={() => actions.restore.mutate({ id: trip.id, version: v.version }, { onSuccess: () => toast.success(`Restored v${v.version} as a new version`), onError: fail('Could not restore') })}>Restore</button>
                    )}
                  </li>
                ))}
              </ul>
            ) : <p className="text-xs text-muted">No versions yet.</p>}
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" className="tg-btn tg-btn-secondary tg-btn-sm" disabled={planning || actions.replan.isPending} onClick={() => setConfirmReplan(true)}><RefreshCw className="size-4" /> Re-plan</button>
              <button type="button" className="tg-btn tg-btn-secondary tg-btn-sm" onClick={() => actions.duplicate.mutate(trip.id, { onSuccess: (t) => { toast.success('Trip duplicated'); navigate(`/trips/${t.id}`) }, onError: fail('Could not duplicate') })}><Copy className="size-4" /> Duplicate</button>
              <button type="button" className="tg-btn tg-btn-danger tg-btn-sm" onClick={() => setConfirmDelete(true)}><Trash2 className="size-4" /> Delete</button>
            </div>
          </section>
        </aside>
      </div>

      <ConfirmDialog open={confirmDelete} destructive title="Delete this trip?" description="The itinerary and versions are removed permanently. Agent runs stay in analytics." confirmLabel="Delete trip" busy={actions.remove.isPending}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => actions.remove.mutate(trip.id, { onSuccess: () => { toast.success('Trip deleted'); navigate('/trips', { replace: true }) }, onError: fail('Could not delete') })} />
      <ConfirmDialog open={confirmReplan} title="Re-plan with agents?" description="A new agent run will generate a fresh itinerary and save it as a new version. Earlier versions stay restorable." confirmLabel="Start re-plan" busy={actions.replan.isPending}
        onCancel={() => setConfirmReplan(false)}
        onConfirm={() => actions.replan.mutate({ id: trip.id }, { onSuccess: (r) => { setConfirmReplan(false); navigate(`/studio/runs/${r.run_public_id}`) }, onError: fail('Could not start re-plan') })} />
    </div>
  )
}

function DayPanel({ day }: { day: Trip['days'][number] }) {
  const meta = Object.entries(day.meta ?? {}).filter(([, v]) => typeof v === 'string' && v)
  const total = day.activities.reduce((s, a) => s + a.estimated_cost_inr, 0)
  return (
    <article className="tg-card overflow-hidden">
      <div className="relative h-44 sm:h-52">
        <CoverImage src={day.image} className="size-full" />
        {day.area && <span className="absolute right-3 top-3 flex items-center gap-1 rounded-full bg-surface/95 px-3 py-1 text-xs font-semibold shadow"><MapPin className="size-3.5 text-primary" /> {day.area}</span>}
      </div>
      <div className="p-5">
        <h2 className="text-2xl font-extrabold">Day {day.day_number}: {day.title}</h2>
        {day.summary && <p className="mt-1 text-sm text-muted">{day.summary}</p>}
        {meta.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2">
            {meta.map(([k, v]) => <li key={k} className="rounded-full border border-line bg-surface-2 px-3 py-1 text-xs font-medium"><span className="text-muted">{titleCase(k)}:</span> {v}</li>)}
          </ul>
        )}
        <div className="mt-5 flex items-center justify-between"><h3 className="text-sm font-bold">Day Plan</h3><span className="text-xs text-muted">{day.activities.length} activities · {formatINR(total)}</span></div>
        <ol className="mt-3 space-y-2.5">
          {day.activities.map((a) => <ActivityRow key={a.id} a={a} />)}
        </ol>
      </div>
    </article>
  )
}

function ActivityRow({ a }: { a: TripActivity }) {
  return (
    <li className="flex gap-3">
      <span className="tg-mono w-[70px] shrink-0 rounded-lg bg-primary-soft py-1.5 text-center text-[11px] font-medium text-primary-ink">{a.time_label}</span>
      <div className="flex min-w-0 flex-1 items-center gap-3 rounded-xl border border-line p-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold">{a.title}</p>
          {a.description && <p className="text-xs text-muted">{a.description}</p>}
          <p className="mt-1 flex items-center gap-2 text-[11px]"><span className="rounded-md bg-surface-2 px-1.5 py-0.5 capitalize text-muted">{a.category}</span>{a.estimated_cost_inr > 0 && <span className="font-semibold">{formatINR(a.estimated_cost_inr)}</span>}</p>
        </div>
        {a.image && <CoverImage src={a.image} className="hidden size-14 shrink-0 rounded-lg sm:block" />}
      </div>
    </li>
  )
}

function KeyValueCard({ title, icon: Icon, data, emptyHint }: { title: string; icon: LucideIcon; data: Record<string, unknown>; emptyHint: string }) {
  const entries = Object.entries(data ?? {}).filter(([, v]) => v !== null && typeof v !== 'object')
  if (!entries.length) return <EmptyState icon={Icon} title={`No ${title.toLowerCase()} details`} description={emptyHint} />
  return (
    <section className="tg-card p-5">
      <h2 className="mb-3 flex items-center gap-2 text-lg font-bold"><Icon className="size-5 text-primary" /> {title}</h2>
      <dl className="grid gap-3 sm:grid-cols-2">
        {entries.map(([k, v]) => (
          <div key={k} className="rounded-xl border border-line bg-surface-2 p-3">
            <dt className="text-xs text-muted">{titleCase(k)}</dt>
            <dd className="text-sm font-semibold">{/_inr$/.test(k) && typeof v === 'number' ? formatINR(v) : String(v)}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 text-xs text-muted">Sample estimates from a local catalog — not live availability or pricing.</p>
    </section>
  )
}

function BudgetPanel({ trip }: { trip: Trip }) {
  const rows = Object.entries(trip.budget_breakdown ?? {}).filter(([k, v]) => !['total', 'remaining'].includes(k) && typeof v === 'number')
  const slices = rows.map(([k, v]) => ({ name: titleCase(k), value: v as number }))
  if (!slices.length) return <EmptyState icon={Wallet} title="No budget breakdown" description="A breakdown appears once the agents finish planning." />
  return (
    <section className="tg-card p-5">
      <h2 className="mb-4 flex items-center gap-2 text-lg font-bold"><Wallet className="size-5 text-primary" /> Budget breakdown</h2>
      <DonutChart data={slices} format={(v) => formatINR(v)} center={<div><p className="text-xl font-extrabold">{formatINR(trip.estimated_cost_inr)}</p><p className="text-xs text-muted">estimated</p></div>} />
      <table className="mt-5 w-full text-sm">
        <caption className="sr-only">Budget lines</caption>
        <tbody className="divide-y divide-line">
          {slices.map((s) => <tr key={s.name}><th scope="row" className="py-2 text-left font-medium">{s.name}</th><td className="py-2 text-right font-semibold">{formatINR(s.value)}</td></tr>)}
          <tr><th scope="row" className="py-2 text-left font-bold">Total</th><td className="py-2 text-right font-extrabold">{formatINR(trip.estimated_cost_inr)}</td></tr>
          <tr><th scope="row" className="py-2 text-left text-muted">Remaining of {formatINR(trip.budget_inr)}</th><td className={cn('py-2 text-right font-semibold', trip.budget_inr - trip.estimated_cost_inr >= 0 ? 'text-mint' : 'text-danger')}>{formatINR(trip.budget_inr - trip.estimated_cost_inr)}</td></tr>
        </tbody>
      </table>
    </section>
  )
}

function MapPanel({ trip }: { trip: Trip }) {
  const areas = useMemo(() => {
    const m = new Map<string, number[]>()
    trip.days.forEach((d) => d.area && m.set(d.area, [...(m.get(d.area) ?? []), d.day_number]))
    return [...m.entries()]
  }, [trip.days])
  return (
    <section className="tg-card p-5">
      <h2 className="mb-1 flex items-center gap-2 text-lg font-bold"><MapIcon className="size-5 text-primary" /> Areas to explore</h2>
      <p className="mb-4 text-xs text-muted">Interactive maps are not available in the local demo. Here are the areas covered by day.</p>
      {areas.length === 0 ? <p className="text-sm text-muted">No areas yet.</p> : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {areas.map(([area, ds]) => <li key={area} className="flex items-center gap-3 rounded-xl border border-line p-3"><MapPin className="size-5 text-primary" /><span><span className="block text-sm font-bold">{area}</span><span className="text-xs text-muted">Day {ds.join(', ')}</span></span></li>)}
        </ul>
      )}
    </section>
  )
}

function DetailSkeleton() {
  return (
    <div className="mx-auto max-w-[1280px] space-y-5" role="status" aria-label="Loading trip">
      <Skeleton className="h-44 w-full rounded-3xl" />
      <Skeleton className="h-11 w-96 max-w-full" />
      <div className="grid gap-5 xl:grid-cols-[1fr_320px]"><Skeleton className="h-96" /><Skeleton className="h-96" /></div>
    </div>
  )
}
