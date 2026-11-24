import { useEffect, useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowLeftRight, Award, Download, FlaskConical, GitCompare, Lightbulb, Plus, Trophy, X, Clock, Coins, Gauge, Layers, Target, Wrench } from 'lucide-react'
import { ChartCard } from '@/components/charts/ChartCard'
import { RadarCompare } from '@/components/charts/charts'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { LoadingSkeleton } from '@/components/ui/Skeleton'
import { MetricCard } from '@/components/ui/StatCard'
import { ProvenanceBadge } from '@/components/ui/StatusPill'
import { useCompareRuns, useEvaluations, useRuns } from '@/hooks/queries'
import { buildCompareRows, deriveInsights, formatDelta, formatMetric, metricLabel, normalizeMetric, overallOf, type CompareRow } from '@/lib/evaluation'
import type { CompareRun } from '@/lib/types'
import { cn, downloadText, formatDate, formatDuration, formatUSD } from '@/lib/utils'

const COLORS = ['#818cf8', '#34d399', '#fbbf24', '#f472b6']
const LETTERS = ['A', 'B', 'C', 'D']

function fmtRow(row: CompareRow, v: number | null | undefined): string {
  if (v == null) return 'Not evaluated'
  if (row.unit === 's') return `${v.toFixed(1)}s`
  if (row.unit === 'usd') return formatUSD(v)
  return formatMetric(v, row.unit)
}
function fmtDelta(row: CompareRow, d: number | null | undefined): string {
  if (d == null) return '—'
  if (row.unit === 's') return `${d > 0 ? '+' : d < 0 ? '−' : ''}${Math.abs(d).toFixed(1)}s`
  if (row.unit === 'usd') return `${d > 0 ? '+' : d < 0 ? '−' : ''}${formatUSD(Math.abs(d))}`
  return formatDelta(d, row.unit)
}
function barPct(row: CompareRow, v: number | null | undefined, all: (number | null | undefined)[]): number {
  if (v == null) return 0
  if (row.unit === 's' || row.unit === 'usd') {
    const max = Math.max(...all.filter((x): x is number => x != null), 1e-9)
    return Math.max(4, (v / max) * 100)
  }
  return normalizeMetric(v, row.unit) ?? 0
}

export default function ComparePage() {
  const [params, setParams] = useSearchParams()
  const picked = useMemo(() => (params.get('runs') ?? '').split(',').map((s) => s.trim()).filter(Boolean).slice(0, 4), [params])
  const runs = useRuns({ status: 'completed', page_size: 100 })
  const evals = useEvaluations({ page_size: 12 })

  // default to the two most recent completed runs that already have evaluations
  useEffect(() => {
    if (picked.length >= 2 || !runs.data || !evals.data) return
    const evaluated = new Set(evals.data.items.map((e) => e.run_public_id))
    const candidates = runs.data.items.filter((r) => evaluated.has(r.public_id))
    const pool = (candidates.length >= 2 ? candidates : runs.data.items).slice(0, 2).map((r) => r.public_id)
    if (pool.length >= 2) setParams({ runs: pool.reverse().join(',') }, { replace: true })
  }, [picked.length, runs.data, evals.data, setParams])

  const cmp = useCompareRuns(picked)
  const data = cmp.data
  const rows = useMemo(() => (data ? buildCompareRows(data) : []), [data])
  const insights = useMemo(() => (data ? deriveInsights(data, rows) : null), [data, rows])

  const setRun = (idx: number, id: string) => {
    const next = [...picked]
    next[idx] = id
    setParams({ runs: next.join(',') })
  }
  const swap = () => picked.length >= 2 && setParams({ runs: [picked[1], picked[0], ...picked.slice(2)].join(',') })
  const addRun = () => {
    const free = runs.data?.items.find((r) => !picked.includes(r.public_id))
    if (free && picked.length < 4) setParams({ runs: [...picked, free.public_id].join(',') })
  }
  const removeRun = (idx: number) => picked.length > 2 && setParams({ runs: picked.filter((_, i) => i !== idx).join(',') })

  const focus: CompareRun | undefined = data?.runs[data.runs.length - 1]
  const base: CompareRun | undefined = data?.runs[0]
  const rowOf = (k: string) => rows.find((r) => r.key === k)

  const tiles = useMemo(() => {
    if (!data || !focus || !base) return []
    const wanted = ['overall', 'budget_compliance', 'preference_coverage', 'tool_success_rate', 'itinerary_completeness', 'latency_score', 'wall_time', 'cost']
    const icons: Record<string, typeof Gauge> = { overall: Award, budget_compliance: Coins, preference_coverage: Target, tool_success_rate: Wrench, itinerary_completeness: Layers, latency_score: Gauge, wall_time: Clock, cost: Coins }
    return wanted.map((k) => rowOf(k)).filter((r): r is CompareRow => !!r).slice(0, 7).map((r) => ({ r, icon: icons[r.key] ?? Gauge }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, rows])

  const radar = useMemo(() => {
    if (!data) return { data: [] as Record<string, number | string>[], dropped: 0 }
    const usable = data.metric_names.filter((n) => data.runs.every((r) => r.metrics[n] != null))
    return {
      dropped: data.metric_names.length - usable.length,
      data: usable.map((n) => {
        const row: Record<string, number | string> = { metric: metricLabel(n) }
        data.runs.forEach((r) => (row[r.public_id] = Math.round(normalizeMetric(r.metrics[n], data.metric_units[n] ?? '') ?? 0)))
        return row
      }),
    }
  }, [data])

  const exportCsv = () => {
    if (!data) return
    const head = ['metric', 'unit', ...data.runs.map((r) => r.public_id), 'winner']
    const lines = [head.join(',')]
    rows.forEach((r) => lines.push([r.label, r.unit, ...data.runs.map((x) => r.values[x.run_id] ?? ''), typeof r.winner === 'object' ? r.winner.publicId : r.winner].map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')))
    downloadText(`travelgraph-compare-${picked.join('-')}.csv`, lines.join('\n'), 'text/csv')
  }

  const runOptions = runs.data?.items ?? []
  const notEnough = runs.data && runOptions.length < 2

  return (
    <div className="mx-auto max-w-[1500px] space-y-4">
      <header className="flex flex-wrap items-center gap-3">
        <span className="grid size-11 place-items-center rounded-2xl bg-primary-soft text-primary"><GitCompare className="size-5" /></span>
        <div className="mr-auto">
          <h1 className="text-2xl font-bold leading-tight">Evaluation Comparison</h1>
          <p className="text-xs text-muted">Compare trip-planning runs across quality, fidelity and efficiency metrics.</p>
        </div>
        <Link to="/evaluations" className="tg-btn tg-btn-secondary tg-btn-sm"><FlaskConical className="size-4" /> Evaluation Lab</Link>
        <button type="button" className="tg-btn tg-btn-secondary tg-btn-sm" onClick={exportCsv} disabled={!data}><Download className="size-4" /> Export CSV</button>
      </header>

      {notEnough ? (
        <EmptyState icon={GitCompare} title="Need at least two completed runs" description="Plan a couple of trips (or run the benchmark) to compare runs here." action={<Link to="/trips/new" className="tg-btn tg-btn-primary">Plan a trip</Link>} />
      ) : (
        <>
          <section className="tg-card flex flex-wrap items-center gap-3 p-3" aria-label="Choose runs to compare">
            {picked.map((id, i) => (
              <div key={i} className="flex items-center gap-2">
                {i === 1 && <button type="button" aria-label="Swap runs A and B" onClick={swap} className="grid size-10 place-items-center rounded-xl border border-line bg-surface-2 hover:border-primary"><ArrowLeftRight className="size-4" /></button>}
                <label className="flex items-center gap-2 rounded-xl border bg-surface-2 py-1 pl-2 pr-1" style={{ borderColor: COLORS[i] }}>
                  <span className="rounded-md px-2 py-1 text-xs font-bold text-slate-900" style={{ background: COLORS[i] }}>Run {LETTERS[i]}</span>
                  <select aria-label={`Run ${LETTERS[i]}`} value={id} onChange={(e) => setRun(i, e.target.value)} className="h-9 min-w-[170px] rounded-lg border-0 bg-transparent text-sm font-semibold focus:outline-none">
                    {!runOptions.some((r) => r.public_id === id) && <option value={id}>{id}</option>}
                    {runOptions.map((r) => <option key={r.id} value={r.public_id}>#{r.public_id} · {r.model_name}</option>)}
                  </select>
                  {picked.length > 2 && i >= 2 && <button type="button" aria-label={`Remove run ${LETTERS[i]}`} onClick={() => removeRun(i)} className="rounded-lg p-1.5 text-muted hover:bg-danger-soft hover:text-danger"><X className="size-4" /></button>}
                </label>
              </div>
            ))}
            {picked.length < 4 && picked.length >= 2 && <button type="button" onClick={addRun} className="tg-btn tg-btn-ghost tg-btn-sm"><Plus className="size-4" /> Add run</button>}
            {data && (
              <p className="ml-auto flex flex-wrap items-center gap-2 text-xs text-muted">
                <span>Rubric: {[...new Set(data.runs.flatMap((r) => r.evaluations.map((e) => e.rubric_version)))].join(', ') || 'none'}</span>
                {data.runs.some((r) => r.is_demo_fixture) && <span className="rounded-full border border-warn/40 bg-warn-soft px-2 py-0.5 font-semibold text-warn">Includes Sample evaluation (demo)</span>}
              </p>
            )}
          </section>

          {picked.length < 2 || (cmp.isPending && cmp.fetchStatus !== 'idle') ? <LoadingSkeleton rows={5} /> : cmp.isError ? <ErrorState error={cmp.error} onRetry={() => cmp.refetch()} title="Could not compare these runs" /> : data && base && focus ? (
            <>
              <section className="grid grid-cols-2 gap-3 md:grid-cols-4 2xl:grid-cols-7 xl:grid-cols-4" aria-label="Headline metrics">
                {tiles.map(({ r, icon }, i) => {
                  const v = r.values[focus.run_id]
                  const d = r.deltas[focus.run_id]
                  const good = d == null || d === 0 ? null : r.lowerBetter ? d < 0 : d > 0
                  return (
                    <MetricCard key={r.key} icon={icon} highlight={i === 0} label={r.label}
                      value={r.key === 'overall' ? (v != null ? <>{v.toFixed(1)} <span className="text-sm text-muted">/ 5</span></> : <span className="text-base">Not evaluated</span>) : fmtRow(r, v)}
                      sub={`${focus.public_id}${data.runs.length > 2 ? ` (Run ${LETTERS[data.runs.length - 1]})` : ''}`}
                      delta={data.runs.length > 1 && focus.run_id !== base.run_id && d != null ? { text: `${fmtDelta(r, d)} vs ${base.public_id}`, good } : undefined} />
                  )
                })}
              </section>

              <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr_1fr]">
                <ChartCard title="Run Comparison" subtitle="Side-by-side results, metrics and key differences" icon={<GitCompare className="size-4" />} className="xl:col-span-1">
                  <div className="mb-3 grid gap-2" style={{ gridTemplateColumns: `repeat(${data.runs.length}, minmax(0, 1fr))` }}>
                    {data.runs.map((r, i) => {
                      const o = overallOf(r)
                      return (
                        <div key={r.run_id} className="rounded-xl border p-2.5" style={{ borderColor: COLORS[i] }}>
                          <p className="flex items-center justify-between text-xs font-bold"><span style={{ color: COLORS[i] }}>Run {LETTERS[i]} — {r.model_name}</span><span className="rounded-md bg-surface-2 px-1.5 py-0.5">{o.value != null ? `${o.value.toFixed(1)}/5` : 'N/E'}</span></p>
                          <Link to={`/studio/runs/${r.public_id}`} className="tg-mono text-[11px] text-muted hover:text-primary">#{r.public_id} · {r.status}</Link>
                          <p className="mt-0.5 text-[11px] text-muted">{formatDuration(r.wall_time_ms)} · {formatUSD(r.total_cost_usd)}</p>
                        </div>
                      )
                    })}
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[520px] text-xs">
                      <thead className="text-muted"><tr><th className="py-1.5 text-left font-semibold">Metric</th>{data.runs.map((r, i) => <th key={r.run_id} className="px-1 py-1.5 text-left font-semibold" style={{ color: COLORS[i] }}>Run {LETTERS[i]}</th>)}<th className="px-1 py-1.5 text-right font-semibold">Δ vs A</th><th className="py-1.5 text-right font-semibold">Winner</th></tr></thead>
                      <tbody className="divide-y divide-line">
                        {rows.map((r) => {
                          const all = data.runs.map((x) => r.values[x.run_id])
                          const d = r.deltas[focus.run_id]
                          return (
                            <tr key={r.key}>
                              <th scope="row" className="py-2 pr-2 text-left font-medium">{r.label}</th>
                              {data.runs.map((x, i) => (
                                <td key={x.run_id} className="px-1 py-2">
                                  <div className={cn('mb-1 font-semibold', r.values[x.run_id] == null && 'font-normal text-muted')}>{fmtRow(r, r.values[x.run_id])}</div>
                                  <div className="h-1.5 w-full max-w-[110px] overflow-hidden rounded-full bg-line"><div className="h-full rounded-full" style={{ width: `${barPct(r, r.values[x.run_id], all)}%`, background: COLORS[i] }} /></div>
                                </td>
                              ))}
                              <td className={cn('px-1 py-2 text-right font-semibold', d == null || d === 0 ? 'text-muted' : (r.lowerBetter ? d < 0 : d > 0) ? 'text-mint' : 'text-danger')}>{focus.run_id === base.run_id ? '—' : fmtDelta(r, d)}</td>
                              <td className="py-2 text-right">
                                {typeof r.winner === 'object' ? <span className="inline-flex items-center gap-1 rounded-md border border-mint/40 bg-mint-soft px-1.5 py-0.5 font-semibold text-mint"><Trophy className="size-3" />{r.winner.publicId}</span> : <span className="text-muted">{r.winner === 'tie' ? 'Tie' : '—'}</span>}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </ChartCard>

                <div className="space-y-4">
                  <ChartCard title="Metric Radar Comparison" subtitle="Normalized 0–100, higher is better" icon={<Target className="size-4" />}>
                    {radar.data.length < 3 ? <p className="py-10 text-center text-sm text-muted">Not enough evaluated metrics shared by all runs to draw a radar.</p> : (
                      <RadarCompare data={radar.data} series={data.runs.map((r, i) => ({ key: r.public_id, label: `Run ${LETTERS[i]} (${r.public_id})`, color: COLORS[i] }))} />
                    )}
                    {radar.dropped > 0 && <p className="mt-1 text-[11px] text-muted">{radar.dropped} metric(s) omitted because at least one run is Not evaluated.</p>}
                  </ChartCard>
                </div>

                <ChartCard title="Insights & Recommendations" subtitle="Derived from the numbers shown" icon={<Lightbulb className="size-4" />}>
                  {insights && (
                    <div className="space-y-3 text-sm">
                      <div className={cn('rounded-xl border p-3', insights.leader ? 'border-mint/40 bg-mint-soft' : 'border-line bg-surface-2')}>
                        <p className="flex items-center gap-2 font-bold"><Trophy className={cn('size-4', insights.leader ? 'text-mint' : 'text-muted')} /> {insights.headline}</p>
                      </div>
                      <ul className="list-disc space-y-1.5 pl-5 text-muted marker:text-primary">{insights.findings.map((f, i) => <li key={i}>{f}</li>)}</ul>
                      {data.notes.length > 0 && <div className="rounded-xl border border-line bg-surface-2 p-3 text-xs text-muted"><p className="mb-1 font-semibold text-ink">Notes</p><ul className="list-disc space-y-1 pl-4">{data.notes.map((n, i) => <li key={i}>{n}</li>)}</ul></div>}
                      {Object.keys(data.metric_provenance).length > 0 && <ProvenanceBadge value={[...new Set(Object.values(data.metric_provenance))].join(' + ')} />}
                    </div>
                  )}
                </ChartCard>
              </div>
            </>
          ) : null}

          <section className="tg-card overflow-hidden" aria-label="Recent evaluations">
            <header className="border-b border-line px-4 py-3"><h2 className="text-sm font-bold">Evaluation history</h2><p className="text-xs text-muted">Most recent stored evaluations. Click a row to load that run as Run B.</p></header>
            {evals.isPending ? <div className="p-4"><LoadingSkeleton rows={3} /></div> : (evals.data?.items.length ?? 0) === 0 ? <p className="p-6 text-center text-sm text-muted">No evaluations stored yet.</p> : (
              <div className="overflow-x-auto"><table className="w-full min-w-[640px] text-left text-sm">
                <thead className="bg-surface-2 text-xs text-muted"><tr><th className="px-4 py-2">Date & time</th><th className="px-2 py-2">Run</th><th className="px-2 py-2">Evaluation</th><th className="px-2 py-2 text-right">Overall</th><th className="px-4 py-2" /></tr></thead>
                <tbody className="divide-y divide-line">
                  {evals.data?.items.map((e) => (
                    <tr key={e.id} className="hover:bg-primary-soft/40">
                      <td className="px-4 py-2 text-xs text-muted">{formatDate(e.created_at, true)}</td>
                      <td className="tg-mono px-2 py-2 text-xs font-semibold">{e.run_public_id}</td>
                      <td className="px-2 py-2"><span className="block max-w-[320px] truncate">{e.label}</span>{e.is_demo_fixture && <span className="text-[10px] font-semibold text-warn">Sample evaluation (demo)</span>}</td>
                      <td className="px-2 py-2 text-right font-bold">{e.overall_score != null ? e.overall_score.toFixed(2) : 'N/E'}</td>
                      <td className="px-4 py-2 text-right"><button type="button" className="tg-btn tg-btn-ghost tg-btn-sm" onClick={() => e.run_public_id && setRun(1, e.run_public_id)}>Use as Run B</button></td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
