import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CalendarClock, CheckCircle2, FileText, Heart, LayoutGrid, List, Loader2, Luggage, Map, Plus, Search, Briefcase, Layers, Database, FolderOpen } from 'lucide-react'
import { TripCard } from '@/components/trips/TripCard'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { CardGridSkeleton } from '@/components/ui/Skeleton'
import { StatCard } from '@/components/ui/StatCard'
import { useToast } from '@/components/ui/Toast'
import { useDashboard, useTripActions, useTrips } from '@/hooks/queries'
import { ApiError } from '@/lib/api'
import { countTrips, filterTrips, type TripFilter, type TripSort } from '@/lib/tripFilters'
import type { TripListItem } from '@/lib/types'
import { cn, formatUSD } from '@/lib/utils'

const FILTERS: { id: TripFilter; label: string; icon: typeof Map }[] = [
  { id: 'all', label: 'All Trips', icon: LayoutGrid },
  { id: 'completed', label: 'Completed', icon: CheckCircle2 },
  { id: 'in_progress', label: 'In Progress', icon: Loader2 },
  { id: 'draft', label: 'Drafts', icon: FileText },
  { id: 'favorite', label: 'Favorites', icon: Heart },
]

export default function TripsPage() {
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const [filter, setFilter] = useState<TripFilter>('all')
  const [sort, setSort] = useState<TripSort>('recent')
  const [view, setView] = useState<'grid' | 'list'>('grid')
  const [toDelete, setToDelete] = useState<TripListItem | null>(null)

  const trips = useTrips()
  const dash = useDashboard()
  const actions = useTripActions()

  const all = useMemo(() => trips.data?.items ?? [], [trips.data])
  const counts = useMemo(() => countTrips(all), [all])
  const visible = useMemo(() => filterTrips(all, { q, filter, sort }), [all, q, filter, sort])

  const setQ = (v: string) => {
    const next = new URLSearchParams(params)
    if (v) next.set('q', v)
    else next.delete('q')
    setParams(next, { replace: true })
  }

  const onFavorite = (t: TripListItem) =>
    actions.favorite.mutate(
      { id: t.id },
      {
        onSuccess: (r) => toast.success(r.is_favorite ? 'Added to favorites' : 'Removed from favorites'),
        onError: (e) => toast.error('Could not update favorite', e instanceof ApiError ? e.message : undefined),
      },
    )
  const onDuplicate = (t: TripListItem) =>
    actions.duplicate.mutate(t.id, {
      onSuccess: () => toast.success('Trip duplicated', 'The copy is saved as a draft.'),
      onError: (e) => toast.error('Could not duplicate', e instanceof ApiError ? e.message : undefined),
    })
  const confirmDelete = () => {
    if (!toDelete) return
    actions.remove.mutate(toDelete.id, {
      onSuccess: () => {
        toast.success('Trip deleted', toDelete.title)
        setToDelete(null)
      },
      onError: (e) => toast.error('Could not delete trip', e instanceof ApiError ? e.message : undefined),
    })
  }

  return (
    <div className="mx-auto max-w-[1280px]">
      <PageHeader
        icon={<Map className="size-6" />}
        title="My Journeys"
        subtitle="Every adventure, beautifully organized."
        actions={
          <div className="hidden gap-2 md:flex">
            <StatCard icon={Briefcase} label="Total Trips" value={counts.all} loading={trips.isPending} className="px-3 py-2" />
            <StatCard icon={CheckCircle2} label="Completed" value={counts.completed} tone="mint" loading={trips.isPending} className="px-3 py-2" />
            <StatCard icon={Loader2} label="In Progress" value={counts.in_progress} tone="primary" loading={trips.isPending} className="px-3 py-2" />
            <StatCard icon={FileText} label="Drafts" value={counts.draft} tone="warn" loading={trips.isPending} className="px-3 py-2" />
          </div>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative min-w-[220px] flex-1 sm:max-w-sm">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden />
          <input value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search trips" placeholder="Search destinations, trips…" className="tg-input pl-10" />
        </div>
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter trips">
          {FILTERS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              role="tab"
              aria-selected={filter === id}
              type="button"
              onClick={() => setFilter(id)}
              className={cn(
                'inline-flex h-10 items-center gap-1.5 rounded-full border px-3.5 text-sm font-semibold transition',
                filter === id ? 'border-primary-strong bg-primary-strong text-white' : 'border-line bg-surface hover:border-primary/50',
              )}
            >
              <Icon className="size-4" /> {label} ({counts[id]})
            </button>
          ))}
        </div>
        <Link to="/trips/new" className="tg-btn tg-btn-primary ml-auto">
          <Plus className="size-4" /> New Trip
        </Link>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_300px]">
        <section aria-label="Trips">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-sm">
            <p className="text-muted" aria-live="polite">Showing {visible.length} {visible.length === 1 ? 'trip' : 'trips'}</p>
            <div className="flex items-center gap-2">
              <label htmlFor="sort" className="text-muted">Sort by:</label>
              <select id="sort" value={sort} onChange={(e) => setSort(e.target.value as TripSort)} className="tg-input h-9 w-auto pr-8 text-[13px]">
                <option value="recent">Most Recent</option>
                <option value="oldest">Oldest</option>
                <option value="title">Title (A–Z)</option>
                <option value="budget">Budget (high → low)</option>
                <option value="start_date">Start date</option>
              </select>
              <div className="flex overflow-hidden rounded-lg border border-line">
                {([['grid', LayoutGrid], ['list', List]] as const).map(([v, Icon]) => (
                  <button key={v} type="button" aria-label={`${v} view`} aria-pressed={view === v} onClick={() => setView(v)} className={cn('grid size-9 place-items-center', view === v ? 'bg-primary-soft text-primary' : 'text-muted')}>
                    <Icon className="size-4" />
                  </button>
                ))}
              </div>
            </div>
          </div>

          {trips.isPending ? (
            <CardGridSkeleton count={4} className="xl:grid-cols-2" />
          ) : trips.isError ? (
            <ErrorState error={trips.error} onRetry={() => trips.refetch()} title="Could not load your trips" />
          ) : all.length === 0 ? (
            <EmptyState
              icon={Luggage}
              title="No journeys yet"
              description="Your planned trips will show up here. Describe a destination and let the agent team do the legwork."
              action={<Link to="/trips/new" className="tg-btn tg-btn-primary"><Plus className="size-4" /> Plan your first trip</Link>}
            />
          ) : visible.length === 0 ? (
            <EmptyState
              icon={FolderOpen}
              title="No trips match"
              description="Try a different search or filter."
              action={<button type="button" className="tg-btn tg-btn-secondary" onClick={() => { setFilter('all'); setQ('') }}>Clear filters</button>}
            />
          ) : (
            <div className={cn('grid gap-4', view === 'grid' ? 'sm:grid-cols-2' : 'grid-cols-1')}>
              {visible.map((t) => (
                <TripCard key={t.id} trip={t} variant="full" list={view === 'list'} onFavorite={onFavorite} onDuplicate={onDuplicate} onDelete={setToDelete} />
              ))}
            </div>
          )}
        </section>

        <aside className="space-y-4" aria-label="Travel summary">
          <div className="tg-card p-4">
            <div className="flex items-center gap-3">
              <span className="grid size-11 place-items-center rounded-xl bg-primary-soft text-primary"><CalendarClock className="size-5" /></span>
              <div>
                <p className="text-sm font-bold">Upcoming Trip</p>
                {(() => {
                  const next = [...all].filter((t) => t.start_date && t.start_date >= new Date().toISOString().slice(0, 10)).sort((a, b) => (a.start_date ?? '').localeCompare(b.start_date ?? ''))[0]
                  return next ? (
                    <Link to={`/trips/${next.id}`} className="text-xs font-semibold text-primary-strong hover:underline">{next.title} · {next.start_date}</Link>
                  ) : (
                    <p className="text-xs text-muted">No upcoming trips. Plan your next adventure!</p>
                  )
                })()}
              </div>
            </div>
            <Link to="/trips/new" className="tg-btn tg-btn-secondary tg-btn-sm mt-3">New Trip</Link>
          </div>
          <div className="tg-card p-4">
            <h2 className="mb-3 text-sm font-bold">Your Travel Activity</h2>
            <ul className="space-y-3 text-sm">
              <li className="flex items-center gap-3"><Briefcase className="size-4 text-primary" /> <span className="flex-1">Trips Planned</span> <strong>{dash.data?.trips_planned ?? '—'}</strong></li>
              <li className="flex items-center gap-3"><Layers className="size-4 text-primary" /> <span className="flex-1">Agent Runs</span> <strong>{dash.data?.agent_runs ?? '—'}</strong></li>
              <li className="flex items-center gap-3"><Database className="size-4 text-primary" /> <span className="flex-1">AI Cost</span> <strong>{dash.data ? formatUSD(dash.data.total_ai_cost_usd) : '—'}</strong></li>
            </ul>
            <p className="mt-3 text-[11px] text-muted">Costs are USD demo estimates, not an invoice.</p>
          </div>
        </aside>
      </div>

      <ConfirmDialog
        open={!!toDelete}
        destructive
        title="Delete this trip?"
        description={<>“{toDelete?.title}” and its itinerary will be permanently removed. Agent runs and their costs are kept for analytics.</>}
        confirmLabel="Delete trip"
        busy={actions.remove.isPending}
        onConfirm={confirmDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  )
}
