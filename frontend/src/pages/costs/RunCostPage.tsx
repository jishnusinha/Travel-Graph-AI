import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowDownToLine, ArrowUpFromLine, CheckCircle2, ChevronRight, Clock, Coins, Download, Hash, Layers, Lightbulb, Loader2, PlayCircle, Timer, TriangleAlert, Wrench } from 'lucide-react'
import { ChartCard } from '@/components/charts/ChartCard'
import { DonutChart, WaterfallChart } from '@/components/charts/charts'
import { ErrorState } from '@/components/ui/EmptyState'
import { LoadingSkeleton, Skeleton } from '@/components/ui/Skeleton'
import { MetricCard } from '@/components/ui/StatCard'
import { ProvenanceBadge, StatusPill } from '@/components/ui/StatusPill'
import { useToast } from '@/components/ui/Toast'
import { RunSelector } from '@/components/studio/RunSelector'
import { useRunCost } from '@/hooks/queries'
import { AGENT_BY_ID, agentColor, agentName, agentShort } from '@/lib/agents'
import { api, ApiError } from '@/lib/api'
import { downloadText, formatDate, formatDuration, formatNumber, formatUSD } from '@/lib/utils'

export default function RunCostPage() {
  const { runId = '' } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const q = useRunCost(runId)
  const [exporting, setExporting] = useState(false)
  const d = q.data
  const run = d?.run

  const exportCsv = async () => {
    setExporting(true)
    try {
      const text = await api.text(`/analytics/costs/runs/${runId}/export`)
      downloadText(`travelgraph-${run?.public_id ?? runId}-costs.csv`, text, 'text/csv')
      toast.success('CSV exported', 'Line items for this run were downloaded.')
    } catch (e) {
      toast.error('Export failed', e instanceof ApiError ? e.message : undefined)
    } finally {
      setExporting(false)
    }
  }

  if (q.isError) return <div className="mx-auto max-w-xl pt-10"><ErrorState error={q.error} title="Run cost unavailable" onRetry={() => q.refetch()} /><p className="mt-4 text-center"><Link to="/costs" className="font-semibold text-primary hover:underline">Back to Cost Explorer</Link></p></div>

  const total = run?.total_cost_usd ?? 0
  const toolShare = total ? ((run?.tool_cost_usd ?? 0) / total) * 100 : 0
  const waterfall = (d?.waterfall ?? []).filter((w) => w.cost_usd > 0)
  const steps = waterfall.map((w) => ({ name: agentShort(w.node), value: w.cost_usd }))
  const top = [...(d?.by_agent ?? [])].sort((a, b) => b.cost_usd - a.cost_usd)[0]
  const biggestModelAgent = [...(d?.by_agent ?? [])].filter((a) => a.model_cost_usd > 0).sort((a, b) => b.model_cost_usd - a.model_cost_usd)[0]
  const suggestions: { title: string; body: string }[] = []
  if (top && top.share_pct >= 20) suggestions.push({ title: `Review ${agentName(top.agent)}`, body: `${top.share_pct.toFixed(1)}% of this run's cost (${formatUSD(top.cost_usd)}). The largest single lever for reducing spend.` })
  if (biggestModelAgent && biggestModelAgent !== top) suggestions.push({ title: `Smaller model for ${agentName(biggestModelAgent.agent)}?`, body: `Model spend ${formatUSD(biggestModelAgent.model_cost_usd)}. Compare quality in the Evaluation Lab before switching.` })
  if (toolShare >= 10) suggestions.push({ title: 'Cache or batch tool calls', body: `Tools are ${toolShare.toFixed(1)}% of cost. Reusing catalog lookups for similar trips could reduce this.` })
  if (d && d.tools.some((t) => t.failed > 0)) suggestions.push({ title: 'Failed tool calls', body: 'Some tool calls failed; retries may be adding cost and latency.' })

  return (
    <div className="mx-auto max-w-[1400px] space-y-4">
      <header className="flex flex-wrap items-center gap-3">
        <div className="mr-auto">
          <nav aria-label="Breadcrumb" className="mb-1 flex items-center gap-1 text-xs text-muted"><Link to="/costs" className="hover:text-primary">Cost Explorer</Link><ChevronRight className="size-3" /><span>Run {run?.public_id ?? runId}</span></nav>
          <h1 className="text-2xl font-bold leading-tight">Detailed Run Cost Analysis</h1>
          <p className="text-xs text-muted">Deep cost breakdown, agent performance and optimization insights for a single run.</p>
        </div>
        <RunSelector value={runId} onChange={(r) => navigate(`/costs/runs/${r.public_id}`)} currentFallback={run ? { id: run.id, public_id: run.public_id } : null} />
        <button type="button" onClick={exportCsv} disabled={!d || exporting} className="tg-btn tg-btn-secondary h-10">{exporting ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />} Export CSV</button>
      </header>

      <section className="tg-card flex flex-wrap items-center gap-5 p-4" aria-label="Run summary">
        {q.isPending ? <Skeleton className="h-16 w-full" /> : run && d && (
          <>
            <div className="min-w-[240px] flex-1">
              <div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-bold">{run.public_id}</h2><StatusPill status={run.status} size="sm" /><span className="tg-mono rounded-md bg-surface-2 px-1.5 py-0.5 text-xs">{run.model_name}</span><ProvenanceBadge value={d.provenance} /></div>
              <p className="mt-1 line-clamp-2 text-sm text-muted">{run.prompt}</p>
              <p className="mt-1 text-xs text-muted">{formatDate(run.started_at ?? run.created_at, true)} · revision {run.revision_number}</p>
              <div className="mt-2 flex gap-3 text-xs font-semibold"><Link to={`/studio/runs/${run.public_id}`} className="text-primary hover:underline">Agent Studio</Link><Link to={`/studio/runs/${run.public_id}/replay`} className="inline-flex items-center gap-1 text-primary hover:underline"><PlayCircle className="size-3.5" /> Replay</Link>{run.trip_id && <Link to={`/trips/${run.trip_id}`} className="text-primary hover:underline">Open trip</Link>}</div>
            </div>
            <div className="flex items-center gap-3 border-l border-line pl-5"><Hash className="size-5 text-muted" /><div><p className="text-xs text-muted">Total tokens</p><p className="text-xl font-bold">{formatNumber(run.input_tokens + run.output_tokens)}</p><p className="text-[11px] text-muted">{formatNumber(run.output_tokens)} out / {formatNumber(run.input_tokens)} in</p></div></div>
            <div className="flex items-center gap-3 border-l border-line pl-5"><Timer className="size-5 text-muted" /><div><p className="text-xs text-muted">Wall time</p><p className="text-xl font-bold">{formatDuration(d.wall_time_ms)}</p></div></div>
            <div className="rounded-2xl border border-primary bg-primary-soft px-5 py-3 shadow-[0_0_28px_rgba(99,102,241,0.3)]"><p className="text-xs text-muted">Total cost</p><p className="text-3xl font-extrabold text-mint">{formatUSD(run.total_cost_usd)}</p></div>
          </>
        )}
      </section>

      <section className="grid grid-cols-2 gap-3 xl:grid-cols-4" aria-label="Cost metrics">
        <MetricCard icon={ArrowDownToLine} label="Input tokens" value={q.isPending ? '…' : formatNumber(run?.input_tokens)} />
        <MetricCard icon={ArrowUpFromLine} label="Output tokens" value={q.isPending ? '…' : formatNumber(run?.output_tokens)} />
        <MetricCard icon={Wrench} label="Tool / API costs" value={q.isPending ? '…' : formatUSD(run?.tool_cost_usd)} sub={total ? `${toolShare.toFixed(1)}% of total cost` : undefined} />
        <MetricCard icon={Coins} label="Total AI cost" highlight value={q.isPending ? '…' : formatUSD(run?.total_cost_usd)} sub={`model ${formatUSD(run?.model_cost_usd)}`} />
      </section>

      {d && (
        <div className={d.reconciliation.reconciled && d.reconciliation.tokens_reconciled ? 'flex items-center gap-2 text-xs text-mint' : 'flex items-center gap-2 rounded-xl border border-warn/30 bg-warn-soft px-3 py-2 text-xs text-warn'} role="status">
          {d.reconciliation.reconciled && d.reconciliation.tokens_reconciled ? <CheckCircle2 className="size-4" /> : <TriangleAlert className="size-4" />}
          {d.reconciliation.reconciled && d.reconciliation.tokens_reconciled
            ? `Reconciled: ${d.line_items.length} line items sum to ${formatUSD(d.reconciliation.line_items_total_usd)} (run total ${formatUSD(d.reconciliation.run_total_usd)}).`
            : `Line items total ${formatUSD(d.reconciliation.line_items_total_usd)} vs run total ${formatUSD(d.reconciliation.run_total_usd)} (difference ${formatUSD(d.reconciliation.difference_usd)}).`}
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr_1fr]">
        <ChartCard title="Cost breakdown by agent (waterfall)" subtitle="Cumulative cost by execution stage" icon={<Layers className="size-4" />}>
          {q.isPending ? <LoadingSkeleton rows={4} /> : steps.length === 0 ? <p className="py-10 text-center text-sm text-muted">No priced agent steps for this run.</p> : <WaterfallChart steps={steps} format={(v) => formatUSD(v, { max: 4 })} />}
        </ChartCard>
        <ChartCard title="Cost distribution" subtitle="Share of total cost by agent" icon={<Coins className="size-4" />}>
          {q.isPending ? <LoadingSkeleton rows={4} /> : <DonutChart data={(d?.by_agent ?? []).filter((a) => a.cost_usd > 0).map((a) => ({ name: agentName(a.agent), value: a.cost_usd, color: agentColor(a.agent) }))} format={(v) => formatUSD(v)} center={<div><p className="text-lg font-extrabold">{formatUSD(total)}</p><p className="text-xs text-muted">Total cost</p></div>} />}
        </ChartCard>
        <ChartCard title="Suggestions" subtitle="Heuristic ideas based on this run's numbers" icon={<Lightbulb className="size-4" />}>
          {q.isPending ? <LoadingSkeleton rows={3} /> : suggestions.length === 0 ? <p className="text-sm text-muted">Nothing stands out: cost is spread evenly across agents.</p> : (
            <ul className="space-y-2">{suggestions.map((s) => <li key={s.title} className="rounded-xl border border-line bg-surface p-3"><p className="text-sm font-bold">{s.title}</p><p className="text-xs text-muted">{s.body}</p></li>)}</ul>
          )}
        </ChartCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartCard title="Per-agent cost analysis" subtitle="Token usage and cost for each agent" icon={<Layers className="size-4" />}>
          <div className="overflow-x-auto"><table className="w-full min-w-[460px] text-sm">
            <thead className="text-xs text-muted"><tr><th className="py-1.5 text-left">#</th><th className="text-left">Agent (role)</th><th className="text-right">Input</th><th className="text-right">Output</th><th className="text-right">Cost</th><th className="text-right">% total</th></tr></thead>
            <tbody className="divide-y divide-line">
              {(d?.by_agent ?? []).map((a, i) => { const Icon = AGENT_BY_ID[a.agent]?.icon; return (
                <tr key={a.agent}><td className="py-2 text-muted">{i + 1}</td><td className="font-medium"><span className="inline-flex items-center gap-2">{Icon && <Icon className="size-4" style={{ color: agentColor(a.agent) }} />}{agentName(a.agent)}</span></td><td className="tg-mono text-right text-xs">{formatNumber(a.tokens_in)}</td><td className="tg-mono text-right text-xs">{formatNumber(a.tokens_out)}</td><td className="tg-mono text-right text-xs font-semibold">{formatUSD(a.cost_usd, { max: 4 })}</td><td className="text-right text-xs">{a.share_pct.toFixed(1)}%</td></tr>
              ) })}
              {d && (
                <tr className="font-bold"><td /><td className="py-2">Total</td><td className="tg-mono text-right text-xs">{formatNumber(run?.input_tokens)}</td><td className="tg-mono text-right text-xs">{formatNumber(run?.output_tokens)}</td><td className="tg-mono text-right text-xs">{formatUSD(total, { max: 4 })}</td><td className="text-right text-xs">100%</td></tr>
              )}
            </tbody>
          </table></div>
          {d && <p className="mt-2 text-[11px] text-muted">{d.note}</p>}
        </ChartCard>

        <ChartCard title="Model & tool breakdown" subtitle="Cost by model and external tool / API" icon={<Wrench className="size-4" />}>
          <table className="mb-4 w-full text-sm">
            <thead className="text-xs text-muted"><tr><th className="py-1.5 text-left">Model</th><th className="text-right">Input</th><th className="text-right">Output</th><th className="text-right">Cost</th><th className="text-right">% total</th></tr></thead>
            <tbody className="divide-y divide-line">{(d?.by_model ?? []).map((m) => <tr key={m.model}><td className="tg-mono py-2 text-xs">{m.model}</td><td className="tg-mono text-right text-xs">{formatNumber(m.tokens_in)}</td><td className="tg-mono text-right text-xs">{formatNumber(m.tokens_out)}</td><td className="tg-mono text-right text-xs font-semibold">{formatUSD(m.cost_usd, { max: 4 })}</td><td className="text-right text-xs">{m.share_pct.toFixed(1)}%</td></tr>)}</tbody>
          </table>
          <table className="w-full text-sm">
            <thead className="text-xs text-muted"><tr><th className="py-1.5 text-left">Tool / API</th><th className="text-right">Calls</th><th className="text-right">Latency</th><th className="text-right">Fee</th></tr></thead>
            <tbody className="divide-y divide-line">
              {(d?.tools ?? []).map((t) => <tr key={`${t.node_id}-${t.tool_name}`}><td className="tg-mono py-2 text-xs">{t.tool_name}{t.failed > 0 && <span className="ml-2 text-danger">({t.failed} failed)</span>}</td><td className="text-right text-xs">{t.calls}</td><td className="text-right text-xs">{formatDuration(t.duration_ms)}</td><td className="tg-mono text-right text-xs font-semibold">{formatUSD(t.fee_usd, { max: 4 })}</td></tr>)}
              {d && d.tools.length === 0 && <tr><td colSpan={4} className="py-3 text-center text-xs text-muted">No tool calls recorded.</td></tr>}
            </tbody>
          </table>
        </ChartCard>
      </div>

      <ChartCard title="Run timeline — cost events" subtitle="Chronological execution with cost incurred at each stage" icon={<Clock className="size-4" />}>
        {q.isPending ? <LoadingSkeleton rows={2} /> : (d?.waterfall.length ?? 0) === 0 ? <p className="py-4 text-sm text-muted">No timeline events recorded.</p> : (
          <ol className="flex items-stretch gap-2 overflow-x-auto pb-1">
            {d!.waterfall.map((w, i) => (
              <li key={w.node} className="flex items-center gap-2">
                <div className="min-w-[132px] rounded-xl border border-primary/40 bg-surface p-2.5 shadow-[0_0_16px_rgba(99,102,241,0.18)]">
                  <p className="text-xs font-bold">{agentName(w.node)}</p>
                  <p className="tg-mono text-[10px] text-muted">{w.start_ms != null ? formatDuration(w.start_ms) : '—'} → {w.end_ms != null ? formatDuration(w.end_ms) : '—'}</p>
                  <p className="mt-1 inline-flex rounded-md bg-mint-soft px-1.5 py-0.5 text-[11px] font-semibold text-mint">{formatUSD(w.cost_usd, { max: 4 })}</p>
                  {w.attempts > 1 && <p className="mt-1 text-[10px] text-warn">{w.attempts} attempts</p>}
                </div>
                {i < d!.waterfall.length - 1 && <ChevronRight className="size-4 shrink-0 text-muted" aria-hidden />}
              </li>
            ))}
          </ol>
        )}
      </ChartCard>
    </div>
  )
}
