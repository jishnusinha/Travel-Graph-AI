import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { Coins, Link2, Loader2, PanelRightOpen, PlayCircle, Radio, RotateCcw, Sparkles, Workflow } from 'lucide-react'
import { AgentInspector } from '@/components/studio/AgentInspector'
import { EventLog } from '@/components/studio/EventLog'
import { RunSelector } from '@/components/studio/RunSelector'
import { RunTimeline } from '@/components/studio/RunTimeline'
import { StudioGraph } from '@/components/studio/StudioGraph'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { Skeleton } from '@/components/ui/Skeleton'
import { StatusPill } from '@/components/ui/StatusPill'
import { useToast } from '@/components/ui/Toast'
import { useRuns } from '@/hooks/queries'
import { useStudioRun } from '@/hooks/useStudioRun'
import { replayTimes } from '@/hooks/useReplay'
import { buildMilestones } from '@/lib/timeline'
import { cn, formatDuration } from '@/lib/utils'

export default function StudioPage() {
  const { runId } = useParams()
  const runs = useRuns({ page_size: 1 })

  // /studio → open the most recent run
  if (!runId) {
    if (runs.isPending) return <StudioSkeleton />
    if (runs.isError) return <ErrorState error={runs.error} onRetry={() => runs.refetch()} title="Could not load runs" />
    const first = runs.data?.items[0]
    if (first) return <Navigate to={`/studio/runs/${first.public_id}`} replace />
    return (
      <div className="mx-auto max-w-xl pt-10">
        <EmptyState icon={Workflow} title="No agent runs yet" description="Plan a trip and watch the supervisor, specialist agents and validator work in real time." action={<Link to="/trips/new" className="tg-btn tg-btn-primary"><Sparkles className="size-4" /> Plan a trip</Link>} />
      </div>
    )
  }
  return <RunStudio key={runId} runId={runId} />
}

function RunStudio({ runId }: { runId: string }) {
  const navigate = useNavigate()
  const toast = useToast()
  const { run, stream, derived, status, terminal, nodes, edges } = useStudioRun(runId)
  const [selected, setSelected] = useState<string | null>(null)
  const [drawer, setDrawer] = useState(false)
  const userPicked = useRef(false)

  // follow the running agent until the user picks a node themselves
  useEffect(() => {
    if (userPicked.current) return
    setSelected(derived.currentNode ?? (terminal ? 'supervisor' : (selected ?? 'supervisor')))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [derived.currentNode, terminal])

  const pick = (id: string | null) => {
    userPicked.current = id !== null
    setSelected(id)
    if (id) setDrawer(true)
  }

  const { times } = useMemo(() => replayTimes(stream.events), [stream.events])
  const milestones = useMemo(() => buildMilestones(stream.events, times), [stream.events, times])
  const node = nodes.find((n) => n.id === selected) ?? null
  const live = stream.state === 'live' || stream.state === 'reconnecting'
  const wall = run.data?.wall_time_ms || (times.length ? times[times.length - 1] : 0)
  const runData = run.data

  if (run.isError) {
    return (
      <div className="mx-auto max-w-xl pt-10">
        <ErrorState error={run.error} title="Run unavailable" onRetry={() => run.refetch()} />
        <p className="mt-4 text-center"><Link to="/studio" className="font-semibold text-primary-strong hover:underline">Back to Agent Studio</Link></p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-[1400px] space-y-4">
      <header className="flex flex-wrap items-center gap-3">
        <span className="grid size-11 place-items-center rounded-2xl bg-primary-soft text-primary"><Sparkles className="size-5" /></span>
        <div className="mr-2">
          <h1 className="text-2xl font-bold leading-tight">Agent Studio</h1>
          <p className="text-xs text-muted">{live ? 'Live orchestration' : 'Run orchestration'}</p>
        </div>
        <RunSelector value={runId} currentFallback={runData ? { id: runData.id, public_id: runData.public_id } : null} onChange={(r) => navigate(`/studio/runs/${r.public_id}`)} />
        <StatusPill status={status} />
        {live && <span className="inline-flex items-center gap-1.5 rounded-full border border-mint/30 bg-mint-soft px-2.5 py-1 text-xs font-semibold text-mint"><Radio className="size-3.5 animate-pulse" /> {stream.state === 'reconnecting' ? 'Reconnecting…' : 'Live'}</span>}
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Link to={`/studio/runs/${runId}/replay`} className="tg-btn tg-btn-secondary tg-btn-sm"><PlayCircle className="size-4" /> Replay</Link>
          <Link to={`/costs/runs/${runId}`} className="tg-btn tg-btn-secondary tg-btn-sm"><Coins className="size-4" /> Cost</Link>
          <button type="button" className="tg-btn tg-btn-secondary tg-btn-sm" onClick={() => navigator.clipboard.writeText(window.location.href).then(() => toast.success('Link copied'))}><Link2 className="size-4" /> Share</button>
        </div>
      </header>

      {status === 'failed' && (
        <div role="alert" className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger"><strong>Run failed.</strong> {runData?.error_message ?? 'An agent reported an error. Open the failed node for details.'}</div>
      )}
      {status === 'needs_clarification' && (
        <div role="status" className="rounded-xl border border-warn/30 bg-warn-soft px-4 py-3 text-sm text-warn"><strong>Clarification needed.</strong> {runData?.error_message ?? 'The supervisor needs more detail about the trip.'} <Link to="/trips/new" className="font-semibold underline">Start a new plan</Link></div>
      )}
      {stream.state === 'error' && <ErrorState error={stream.error} title="Could not load run events" onRetry={stream.reload} />}

      <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
        <section className="tg-card tg-dotgrid relative h-[min(62vh,620px)] min-h-[420px] overflow-hidden p-0 lg:h-[640px]" aria-label="Agent graph">
          {stream.state === 'loading' && nodes.every((n) => n.status === 'pending') && (
            <div className="absolute inset-0 z-10 grid place-items-center bg-canvas/50"><Loader2 className="size-6 animate-spin text-primary" /></div>
          )}
          <StudioGraph nodes={nodes} edges={edges} selected={selected} onSelect={pick} className="relative size-full" />
          <button type="button" onClick={() => setDrawer(true)} className="tg-btn tg-btn-secondary tg-btn-sm absolute bottom-3 right-3 z-10 lg:hidden"><PanelRightOpen className="size-4" /> Inspector</button>
        </section>

        <div className={cn('lg:static lg:block lg:h-[640px]', drawer ? 'fixed inset-x-2 bottom-[72px] z-50 block h-[68vh] shadow-2xl' : 'hidden')}>
          <AgentInspector runId={runId} run={runData} node={node} events={stream.events} onClose={() => setDrawer(false)} className="size-full bg-surface" />
        </div>
      </div>

      <RunTimeline milestones={milestones} reachedSeq={derived.lastSeq} eventCount={stream.events.length} totalMs={terminal ? wall : undefined} title={`Run timeline${terminal ? '' : ' (live)'}`} />

      <EventLog events={stream.events} times={times} runLabel={runData?.public_id} followTail={live} onSelect={(ev) => ev.node_id && pick(ev.node_id)} />

      {terminal && runData && (
        <p className="flex flex-wrap items-center gap-2 text-xs text-muted"><RotateCcw className="size-3.5" /> Stored run · {formatDuration(runData.wall_time_ms)} wall time. Use Replay to step through events without calling any AI.</p>
      )}
    </div>
  )
}

function StudioSkeleton() {
  return <div className="mx-auto max-w-[1400px] space-y-4" role="status" aria-label="Loading"><Skeleton className="h-12 w-96" /><Skeleton className="h-[560px] w-full" /></div>
}
