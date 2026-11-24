import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BadgeCheck, CheckCircle2, FlaskConical, GitCompare, Loader2, Play, ShieldAlert, Sigma, XCircle, ClipboardList, Star } from 'lucide-react'
import { ChartCard } from '@/components/charts/ChartCard'
import { ScoreBars } from '@/components/charts/charts'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { LoadingSkeleton } from '@/components/ui/Skeleton'
import { MetricCard } from '@/components/ui/StatCard'
import { StatusPill } from '@/components/ui/StatusPill'
import { useToast } from '@/components/ui/Toast'
import { useBenchmarkCases, useEvaluations, useRunBenchmark, useRunEvaluation, useRuns } from '@/hooks/queries'
import { ApiError } from '@/lib/api'
import type { BenchmarkOut } from '@/lib/types'
import { cn, formatDate } from '@/lib/utils'

export default function EvaluationsPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const evals = useEvaluations()
  const runs = useRuns({ status: 'completed', page_size: 100 })
  const cases = useBenchmarkCases()
  const evaluate = useRunEvaluation()
  const bench = useRunBenchmark()
  const [picked, setPicked] = useState<string[]>([])
  const [runToEval, setRunToEval] = useState('')
  const [benchResult, setBenchResult] = useState<BenchmarkOut | null>(null)

  const items = useMemo(() => evals.data?.items ?? [], [evals.data])
  const deterministic = items.filter((e) => e.kind === 'deterministic' && e.overall_score != null)
  const avg = deterministic.length ? deterministic.reduce((s, e) => s + (e.overall_score ?? 0), 0) / deterministic.length : null
  const evaluatedRuns = new Set(items.map((e) => e.run_id)).size
  const fixtures = items.filter((e) => e.is_demo_fixture).length

  const chart = useMemo(() => {
    const byRun = new Map<string, { name: string; deterministic?: number; sample?: number; t: string }>()
    ;[...items].reverse().forEach((e) => {
      const key = e.run_public_id ?? e.run_id
      const row = byRun.get(key) ?? { name: key, t: e.created_at }
      if (e.overall_score != null) {
        if (e.is_demo_fixture) row.sample = e.overall_score
        else if (e.kind === 'deterministic') row.deterministic = e.overall_score
        else row.sample = row.sample ?? e.overall_score
      }
      byRun.set(key, row)
    })
    return [...byRun.values()].slice(-14)
  }, [items])

  const togglePick = (runId: string) => setPicked((cur) => (cur.includes(runId) ? cur.filter((x) => x !== runId) : cur.length >= 4 ? cur : [...cur, runId]))

  const runEval = () => {
    if (!runToEval) return
    evaluate.mutate(runToEval, {
      onSuccess: (e) => toast.success('Evaluation complete', `${e.run_public_id}: overall ${e.overall_score?.toFixed(2)} / 5`),
      onError: (e) => toast.error('Could not evaluate run', e instanceof ApiError ? e.message : undefined),
    })
  }
  const runBench = () =>
    bench.mutate(undefined, {
      onSuccess: (r) => { setBenchResult(r); toast.success('Benchmark finished', `${r.passed} of ${r.total} cases passed`) },
      onError: (e) => toast.error('Benchmark unavailable', e instanceof ApiError ? e.message : undefined),
    })

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <PageHeader
        icon={<FlaskConical className="size-6" />}
        title="Evaluation Lab"
        subtitle="Score agent runs with deterministic rubrics and compare configurations side by side."
        actions={
          <button type="button" disabled={picked.length < 2} onClick={() => navigate(`/evaluations/compare?runs=${picked.join(',')}`)} className="tg-btn tg-btn-primary">
            <GitCompare className="size-4" /> Compare selected ({picked.length})
          </button>
        }
      />

      {evals.isError ? <ErrorState error={evals.error} onRetry={() => evals.refetch()} title="Could not load evaluations" /> : (
        <>
          <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Evaluation summary">
            <MetricCard icon={ClipboardList} label="Evaluations" value={evals.isPending ? '…' : evals.data?.total ?? 0} sub="stored in database" />
            <MetricCard icon={Star} label="Avg deterministic score" value={avg != null ? `${avg.toFixed(2)} / 5` : 'Not evaluated'} sub={`${deterministic.length} evaluations${fixtures > 0 ? " (incl. sample fixtures)" : ""}`} />
            <MetricCard icon={Sigma} label="Runs evaluated" value={evals.isPending ? '…' : evaluatedRuns} sub={`${runs.data?.total ?? '…'} completed runs`} />
            <MetricCard icon={ShieldAlert} label="Sample fixtures" value={evals.isPending ? '…' : fixtures} sub="Sample evaluation (demo)" />
          </section>

          <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
            <ChartCard title="Overall score by run" subtitle="0–5 scale. Sample evaluation (demo) fixtures are seeded history, not live judgements." icon={<BadgeCheck className="size-4" />}>
              {evals.isPending ? <LoadingSkeleton rows={4} /> : chart.length === 0 ? <p className="py-10 text-center text-sm text-muted">No evaluations yet. Evaluate a completed run to see scores.</p> : (
                <ScoreBars data={chart} yDomain={[0, 5]} series={[{ key: 'deterministic', label: 'Deterministic', color: '#34d399' }, { key: 'sample', label: 'Sample evaluation (demo)', color: '#818cf8' }]} />
              )}
            </ChartCard>

            <div className="space-y-5">
              <ChartCard title="Evaluate a run" subtitle="Deterministic rubric (rule-based, no AI call)" icon={<Play className="size-4" />}>
                <div className="flex flex-wrap gap-2">
                  <select aria-label="Run to evaluate" value={runToEval} onChange={(e) => setRunToEval(e.target.value)} className="tg-input h-10 min-w-0 flex-1 rounded-xl bg-surface-2 text-sm">
                    <option value="">Select a completed run…</option>
                    {runs.data?.items.map((r) => <option key={r.id} value={r.id}>{r.public_id}{r.trip_title ? ` · ${r.trip_title}` : ''}</option>)}
                  </select>
                  <button type="button" className="tg-btn tg-btn-primary h-10" disabled={!runToEval || evaluate.isPending} onClick={runEval}>
                    {evaluate.isPending ? <Loader2 className="size-4 animate-spin" /> : <BadgeCheck className="size-4" />} Evaluate
                  </button>
                </div>
              </ChartCard>

              <ChartCard title="Benchmark suite" subtitle={`${cases.data?.length ?? '…'} curated prompts, run locally in demo mode`} icon={<ClipboardList className="size-4" />}
                actions={<button type="button" className="tg-btn tg-btn-secondary tg-btn-sm" disabled={bench.isPending} onClick={runBench}>{bench.isPending ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />} Run benchmark</button>}>
                {benchResult ? (
                  <div>
                    <p className="mb-2 text-sm font-semibold"><span className="text-mint">{benchResult.passed} passed</span> · <span className="text-danger">{benchResult.failed} failed</span> of {benchResult.total}</p>
                    <ul className="max-h-48 space-y-1.5 overflow-y-auto text-sm">
                      {benchResult.results.map((r) => (
                        <li key={r.slug} className="flex items-center gap-2 rounded-lg border border-line px-2.5 py-1.5">
                          {r.passed ? <CheckCircle2 className="size-4 shrink-0 text-mint" /> : <XCircle className="size-4 shrink-0 text-danger" />}
                          <span className="min-w-0 flex-1 truncate">{r.title}</span>
                          <span className="tg-mono text-xs text-muted">{r.overall_score != null ? r.overall_score.toFixed(2) : r.run_status}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : cases.isPending ? <LoadingSkeleton rows={2} /> : (
                  <ul className="max-h-48 space-y-1.5 overflow-y-auto text-sm">
                    {cases.data?.map((c) => <li key={c.slug} className="rounded-lg border border-line px-2.5 py-1.5"><span className="font-semibold">{c.title}</span> <span className="text-xs text-muted">· {c.tags.join(', ')}</span></li>)}
                  </ul>
                )}
              </ChartCard>
            </div>
          </div>

          <section className="tg-card overflow-hidden" aria-label="Evaluations">
            <header className="flex items-center justify-between border-b border-line px-4 py-3">
              <h2 className="text-sm font-bold">All evaluations</h2>
              <span className="text-xs text-muted">Select 2–4 runs to compare</span>
            </header>
            {evals.isPending ? <div className="p-4"><LoadingSkeleton rows={4} /></div> : items.length === 0 ? (
              <EmptyState icon={FlaskConical} title="No evaluations yet" description="Evaluate a completed run above, or run the benchmark suite." className="border-0 shadow-none" />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead className="bg-surface-2 text-xs text-muted"><tr>
                    <th className="w-10 px-4 py-2"><span className="sr-only">Select</span></th>
                    <th className="px-2 py-2">Run</th><th className="px-2 py-2">Evaluation</th><th className="px-2 py-2">Kind</th><th className="px-2 py-2 text-right">Overall</th><th className="px-2 py-2">Rubric</th><th className="px-2 py-2">Date</th><th className="px-4 py-2" />
                  </tr></thead>
                  <tbody className="divide-y divide-line">
                    {items.map((e) => (
                      <tr key={e.id} className={cn(picked.includes(e.run_public_id ?? e.run_id) && 'bg-primary-soft/60')}>
                        <td className="px-4 py-2.5"><input type="checkbox" aria-label={`Select ${e.run_public_id}`} checked={picked.includes(e.run_public_id ?? e.run_id)} onChange={() => togglePick(e.run_public_id ?? e.run_id)} className="size-4 accent-primary-strong" /></td>
                        <td className="px-2 py-2.5"><Link to={`/studio/runs/${e.run_public_id ?? e.run_id}`} className="tg-mono text-xs font-semibold text-primary hover:underline">{e.run_public_id}</Link></td>
                        <td className="px-2 py-2.5"><span className="block max-w-[260px] truncate">{e.label}</span>{e.is_demo_fixture && <span className="text-[10px] font-semibold text-warn">Sample evaluation (demo)</span>}</td>
                        <td className="px-2 py-2.5 capitalize">{e.kind}</td>
                        <td className="px-2 py-2.5 text-right font-bold">{e.overall_score != null ? e.overall_score.toFixed(2) : <span className="text-xs font-normal text-muted">Not evaluated</span>}</td>
                        <td className="px-2 py-2.5 text-xs text-muted">{e.rubric_version}</td>
                        <td className="px-2 py-2.5 text-xs text-muted">{formatDate(e.created_at)}</td>
                        <td className="px-4 py-2.5 text-right"><StatusPill status={e.status} size="sm" /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
