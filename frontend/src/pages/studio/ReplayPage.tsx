import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Download, Link2, Loader2, Radio, Sparkles, History, Info } from 'lucide-react'
import { AgentInspector } from '@/components/studio/AgentInspector'
import { EventLog } from '@/components/studio/EventLog'
import { ReplayToolbar } from '@/components/studio/ReplayToolbar'
import { RunSelector } from '@/components/studio/RunSelector'
import { RunTimeline } from '@/components/studio/RunTimeline'
import { StudioGraph } from '@/components/studio/StudioGraph'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { useToast } from '@/components/ui/Toast'
import { useStudioRun } from '@/hooks/useStudioRun'
import { useReplay } from '@/hooks/useReplay'
import { deriveGraph } from '@/lib/agents'
import { buildMilestones } from '@/lib/timeline'
import { cn, downloadText, formatDuration } from '@/lib/utils'

export default function ReplayPage() {
  const { runId = '' } = useParams()
  return <Replay key={runId} runId={runId} />
}

function Replay({ runId }: { runId: string }) {
  const navigate = useNavigate()
  const toast = useToast()
  const { run, stream, edges, terminal } = useStudioRun(runId)
  const events = stream.events
  const rp = useReplay(events)
  const cursorSeq = rp.cursor >= 0 ? events[rp.cursor].seq : 0
  const derived = useMemo(() => deriveGraph(events, cursorSeq), [events, cursorSeq])
  const milestones = useMemo(() => buildMilestones(events, rp.times), [events, rp.times])

  const [selected, setSelected] = useState<string | null>('supervisor')
  const [drawer, setDrawer] = useState(false)
  const picked = useRef(false)
  useEffect(() => {
    if (picked.current) return
    setSelected(derived.currentNode ?? selected ?? 'supervisor')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [derived.currentNode])
  const pick = (id: string | null) => {
    picked.current = id !== null
    setSelected(id)
    if (id) setDrawer(true)
  }
  const node = derived.nodes.find((n) => n.id === selected) ?? null
  const pct = rp.duration ? Math.round((rp.t / rp.duration) * 100) : 0

  if (run.isError) {
    return <div className="mx-auto max-w-xl pt-10"><ErrorState error={run.error} title="Run unavailable" onRetry={() => run.refetch()} /></div>
  }

  return (
    <div className="mx-auto max-w-[1400px] space-y-4">
      <header className="flex flex-wrap items-center gap-3">
        <span className="grid size-11 place-items-center rounded-2xl bg-primary-soft text-primary"><Sparkles className="size-5" /></span>
        <div className="mr-2">
          <h1 className="text-2xl font-bold leading-tight">Agent Execution Replay</h1>
          <p className="text-xs text-muted">Step-by-step replay of an agent run</p>
        </div>
        <RunSelector value={runId} currentFallback={run.data ? { id: run.data.id, public_id: run.data.public_id } : null} onChange={(r) => navigate(`/studio/runs/${r.public_id}/replay`)} />
        <div role="group" aria-label="View mode" className="flex rounded-xl border border-line bg-surface-2 p-1 text-sm font-semibold">
          <Link to={`/studio/runs/${runId}`} className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-muted hover:text-ink"><Radio className="size-3.5" /> Live</Link>
          <span aria-current="page" className="flex items-center gap-1.5 rounded-lg bg-primary-strong px-3 py-1.5 text-white"><History className="size-3.5" /> Replay</span>
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <ReplayToolbar playing={rp.playing} speed={rp.speed} t={rp.t} duration={rp.duration} atEnd={rp.atEnd} disabled={events.length === 0}
            onToggle={rp.toggle} onStepPrev={rp.stepPrev} onStepNext={rp.stepNext} onRestart={rp.restart} onSpeed={rp.setSpeed} />
          <button type="button" className="tg-btn tg-btn-secondary tg-btn-sm" disabled={!events.length} onClick={() => downloadText(`${run.data?.public_id ?? runId}-events.json`, JSON.stringify(events, null, 2), 'application/json')}><Download className="size-4" /> Export</button>
          <button type="button" className="tg-btn tg-btn-secondary tg-btn-sm" onClick={() => navigator.clipboard.writeText(window.location.href).then(() => toast.success('Link copied'))}><Link2 className="size-4" /> Share</button>
        </div>
      </header>

      {!terminal && stream.state !== 'loading' && events.length > 0 && (
        <div role="status" className="flex items-center gap-2 rounded-xl border border-primary/30 bg-primary-soft px-4 py-2.5 text-sm"><Info className="size-4 text-primary" /> This run is still in progress; new events are appended as they arrive. <Link className="font-semibold text-primary-ink underline" to={`/studio/runs/${runId}`}>Switch to Live</Link></div>
      )}
      <p className="flex items-center gap-2 text-xs text-muted"><Info className="size-3.5" /> Replay re-plays stored events only — no new AI calls are made and no cost is incurred.</p>

      {stream.state === 'error' && <ErrorState error={stream.error} title="Could not load run events" onRetry={stream.reload} />}
      {stream.state === 'loading' && <div className="grid h-40 place-items-center"><Loader2 className="size-6 animate-spin text-primary" /></div>}
      {stream.state !== 'loading' && stream.state !== 'error' && events.length === 0 && (
        <EmptyState icon={History} title="No events stored for this run" description="There is nothing to replay yet." action={<Link to="/studio" className="tg-btn tg-btn-secondary">Back to Agent Studio</Link>} />
      )}

      {events.length > 0 && (
        <>
          <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
            <section className="tg-card tg-dotgrid relative h-[min(60vh,560px)] min-h-[400px] overflow-hidden p-0 lg:h-[560px]" aria-label="Replay graph">
              <StudioGraph nodes={derived.nodes} edges={edges} selected={selected} onSelect={pick} replaying={rp.playing} className="relative size-full" />
            </section>
            <div className={cn('lg:static lg:block lg:h-[560px]', drawer ? 'fixed inset-x-2 bottom-[72px] z-50 block h-[68vh] shadow-2xl' : 'hidden')}>
              <AgentInspector runId={runId} run={run.data} node={node} events={rp.visibleEvents} replay onClose={() => setDrawer(false)} className="size-full bg-surface" />
            </div>
          </div>

          <section className="tg-card p-4" aria-label="Replay timeline">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <h2 className="flex items-center gap-2 text-sm font-bold"><Sparkles className="size-4 text-primary" /> Replay Timeline <span className="font-normal text-muted">Run #{run.data?.public_id ?? runId} · Total {formatDuration(rp.duration)}</span></h2>
              <span className="tg-mono rounded-lg border border-line bg-surface-2 px-2.5 py-1 text-xs">t = {formatDuration(rp.t)} / {formatDuration(rp.duration)} ({pct}%)</span>
            </div>
            <input
              type="range"
              aria-label="Seek replay"
              aria-valuetext={`${formatDuration(rp.t)} of ${formatDuration(rp.duration)}`}
              min={0}
              max={rp.duration}
              step={10}
              value={rp.t}
              onChange={(e) => { rp.pause(); rp.seek(Number(e.target.value)) }}
              className="h-2 w-full cursor-pointer appearance-none rounded-full bg-line accent-primary"
              style={{ background: `linear-gradient(90deg, var(--tg-primary) ${pct}%, var(--tg-line) ${pct}%)` }}
            />
          </section>

          <RunTimeline
            title="Milestones"
            milestones={milestones}
            reachedSeq={cursorSeq}
            eventCount={events.length}
            onSelect={(m) => { const i = events.findIndex((e) => e.seq === m.seq); if (i >= 0) rp.seekIndex(i) }}
          />

          <EventLog events={events} times={rp.times} activeSeq={cursorSeq} runLabel={run.data?.public_id} onSelect={(ev) => rp.seekIndex(events.findIndex((e) => e.seq === ev.seq))} />
        </>
      )}
    </div>
  )
}
