import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Briefcase, Database, Layers, Loader2, Send, SlidersHorizontal, Sparkles, Star } from 'lucide-react'
import { ChartCard } from '@/components/charts/ChartCard'
import { DonutChart } from '@/components/charts/charts'
import { TripCard } from '@/components/trips/TripCard'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { CardGridSkeleton, Skeleton } from '@/components/ui/Skeleton'
import { StatCard } from '@/components/ui/StatCard'
import { StatusPill, ProvenanceBadge } from '@/components/ui/StatusPill'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/context/AuthContext'
import { useCosts, useCreateTrip, useDashboard } from '@/hooks/queries'
import { agentName, agentColor } from '@/lib/agents'
import { ApiError } from '@/lib/api'
import { formatDuration, formatUSD } from '@/lib/utils'

const DEFAULT_PROMPT = 'Plan a 5-day Goa trip for two under ₹35,000 with beaches and local food.'

export default function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const dash = useDashboard()
  const costs = useCosts({ days: 30 })
  const create = useCreateTrip()
  const [prompt, setPrompt] = useState('')

  const d = dash.data
  const generate = async (e: FormEvent) => {
    e.preventDefault()
    const text = prompt.trim() || DEFAULT_PROMPT
    if (text.length < 8) return toast.error('Describe your trip in a few more words')
    try {
      const res = await create.mutateAsync({ prompt: text, launch_run: true, origin: user?.preferences?.home_city })
      toast.success('Agents are planning your trip', 'Follow along live in Agent Studio.')
      navigate(res.run_public_id ? `/studio/runs/${res.run_public_id}` : `/trips/${res.trip.id}`)
    } catch (err) {
      toast.error('Could not start planning', err instanceof ApiError ? err.message : undefined)
    }
  }

  const agentSlices = (costs.data?.by_agent ?? []).filter((a) => a.cost_usd > 0).map((a) => ({
    name: agentName(a.agent),
    value: a.cost_usd,
    color: agentColor(a.agent),
  }))

  return (
    <div className="mx-auto max-w-[1280px] space-y-5">
      <section className="relative overflow-hidden rounded-3xl bg-cover bg-center p-6 sm:p-9" style={{ backgroundImage: 'url(/assets/hero/beach.svg)' }}>
        <div className="absolute inset-0 bg-gradient-to-r from-white/90 via-white/60 to-transparent" aria-hidden />
        <div className="relative max-w-2xl">
          <Sparkles className="mb-2 size-6 text-primary" aria-hidden />
          <h1 className="text-4xl font-extrabold text-slate-900 sm:text-5xl">
            Where to <span className="relative inline-block text-primary-strong">next?<span className="absolute -bottom-1 left-0 h-1.5 w-full rounded-full bg-mint" /></span>
          </h1>
          <p className="mt-3 max-w-lg text-slate-700">
            {d?.greeting_name ? `Hi ${d.greeting_name} — ` : ''}plan personalized journeys with a multi-agent AI system that researches, creates, and optimizes your travel experience.
          </p>
          <form onSubmit={generate} className="mt-6 flex flex-col gap-2 rounded-2xl bg-white p-2 shadow-lg sm:flex-row sm:items-center">
            <Sparkles className="ml-2 hidden size-5 shrink-0 text-primary sm:block" aria-hidden />
            <label htmlFor="hero-prompt" className="sr-only">Describe your trip</label>
            <input
              id="hero-prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={DEFAULT_PROMPT}
              maxLength={2000}
              className="h-11 min-w-0 flex-1 bg-transparent px-2 text-sm text-slate-900 placeholder:text-slate-500 focus:outline-none"
            />
            <Link to="/trips/new" state={{ prompt }} aria-label="Advanced trip options" className="hidden size-10 place-items-center rounded-xl text-slate-500 hover:bg-slate-100 sm:grid">
              <SlidersHorizontal className="size-4" />
            </Link>
            <button type="submit" disabled={create.isPending} className="tg-btn tg-btn-primary">
              {create.isPending ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
              Generate My Trip
            </button>
          </form>
        </div>
      </section>

      {dash.isError ? (
        <ErrorState error={dash.error} onRetry={() => dash.refetch()} title="Could not load your dashboard" />
      ) : (
        <>
          <section aria-label="Key metrics" className="grid grid-cols-2 gap-3 xl:grid-cols-4">
            <StatCard icon={Briefcase} label="Trips Planned" value={d?.trips_planned} loading={dash.isPending} tone="primary" hint={d ? `${d.trips_completed} completed · ${d.trips_in_progress} in progress` : undefined} />
            <StatCard icon={Layers} label="Agent Runs" value={d?.agent_runs} loading={dash.isPending} tone="mint" hint="All time" />
            <StatCard
              icon={Star}
              label="Avg. Plan Quality"
              tone="warn"
              loading={dash.isPending}
              value={d?.avg_plan_quality != null ? <>{d.avg_plan_quality.toFixed(1)} <span className="text-sm font-medium text-muted">/ 5</span></> : <span className="text-base">Not evaluated</span>}
              hint="Deterministic score"
            />
            <StatCard icon={Database} label="Total AI Cost" tone="primary" loading={dash.isPending} value={formatUSD(d?.total_ai_cost_usd)} hint="USD · demo estimate" />
          </section>

          <div className="grid gap-5 xl:grid-cols-[1.75fr_1fr]">
            <section className="tg-card p-5" aria-labelledby="recent-trips">
              <div className="mb-4 flex items-start justify-between">
                <div>
                  <h2 id="recent-trips" className="text-xl font-bold">Recent Trips</h2>
                  <p className="text-xs text-muted">Your latest travel plans, generated with TravelGraph AI.</p>
                </div>
                <Link to="/trips" className="flex items-center gap-1 text-sm font-semibold text-primary-strong hover:underline">
                  View All Trips <ArrowRight className="size-4" />
                </Link>
              </div>
              {dash.isPending ? (
                <CardGridSkeleton count={3} className="xl:grid-cols-3 sm:grid-cols-2" />
              ) : d && d.recent_trips.length > 0 ? (
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  {d.recent_trips.slice(0, 3).map((t) => <TripCard key={t.id} trip={t} />)}
                </div>
              ) : (
                <EmptyState
                  icon={Sparkles}
                  title="No trips yet"
                  description="Describe a destination above and the agent team will build your first itinerary."
                  action={<Link to="/trips/new" className="tg-btn tg-btn-primary">Plan a trip</Link>}
                />
              )}
            </section>

            <ChartCard title="Quick Insights" subtitle="AI cost by agent · last 30 days" className="min-h-[320px]">
              {costs.isPending ? (
                <Skeleton className="h-56 w-full" />
              ) : costs.isError ? (
                <ErrorState error={costs.error} onRetry={() => costs.refetch()} className="shadow-none" />
              ) : agentSlices.length === 0 ? (
                <p className="py-10 text-center text-sm text-muted">No agent usage recorded in the last 30 days.</p>
              ) : (
                <DonutChart
                  data={agentSlices}
                  format={(v) => formatUSD(v)}
                  center={
                    <div>
                      <p className="text-2xl font-extrabold">{d?.agent_runs ?? costs.data?.run_count}</p>
                      <p className="text-xs text-muted">Agent Runs</p>
                    </div>
                  }
                />
              )}
              {costs.data && <ProvenanceBadge value={costs.data.provenance} className="mt-3" />}
            </ChartCard>
          </div>

          <section className="tg-card p-5" aria-labelledby="activity">
            <div className="mb-3 flex items-center justify-between">
              <h2 id="activity" className="text-lg font-bold">Recent agent activity</h2>
              <Link to="/studio" className="text-sm font-semibold text-primary-strong hover:underline">Open Agent Studio</Link>
            </div>
            {dash.isPending ? (
              <Skeleton className="h-24 w-full" />
            ) : d && d.agent_activity.length > 0 ? (
              <ul className="divide-y divide-line">
                {d.agent_activity.map((a) => (
                  <li key={a.run_id}>
                    <Link to={`/studio/runs/${a.public_id}`} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-3 hover:bg-primary-soft/50 sm:px-2">
                      <span className="tg-mono w-20 text-xs font-semibold">{a.public_id}</span>
                      <span className="min-w-0 flex-1 truncate text-sm">{a.trip_title ?? 'Standalone run'}</span>
                      <StatusPill status={a.status} size="sm" />
                      <span className="text-xs text-muted">{formatDuration(a.wall_time_ms)}</span>
                      <span className="tg-mono text-xs font-semibold">{formatUSD(a.total_cost_usd)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="py-4 text-sm text-muted">No runs yet. Generate a trip to see agents at work.</p>
            )}
          </section>
        </>
      )}
    </div>
  )
}
