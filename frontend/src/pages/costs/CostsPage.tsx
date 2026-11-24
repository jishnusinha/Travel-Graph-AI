import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, Calculator, Coins, Cpu, Database, Download, Hash, Loader2, TriangleAlert, Wrench } from 'lucide-react'
import { ChartCard } from '@/components/charts/ChartCard'
import { DonutChart, HorizontalBars, TrendAreaChart } from '@/components/charts/charts'
import { EmptyState, ErrorState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { LoadingSkeleton } from '@/components/ui/Skeleton'
import { MetricCard } from '@/components/ui/StatCard'
import { ProvenanceBadge, StatusPill } from '@/components/ui/StatusPill'
import { useToast } from '@/components/ui/Toast'
import { useCosts, useRuns } from '@/hooks/queries'
import { AGENTS, agentColor, agentName } from '@/lib/agents'
import { api, ApiError } from '@/lib/api'
import { downloadText, formatDate, formatDuration, formatNumber, formatUSD } from '@/lib/utils'

const RANGES = [
  { v: 7, l: 'Last 7 days' },
  { v: 30, l: 'Last 30 days' },
  { v: 90, l: 'Last 90 days' },
  { v: 0, l: 'All time' },
]

export default function CostsPage() {
  const toast = useToast()
  const [days, setDays] = useState(30)
  const [model, setModel] = useState('')
  const [agent, setAgent] = useState('')
  const [exporting, setExporting] = useState(false)
  const filters = useMemo(() => ({ days, model: model || undefined, agent: agent || undefined }), [days, model, agent])
  const costs = useCosts(filters)
  const runs = useRuns({ page_size: 100 })
  const models = useMemo(() => [...new Set(runs.data?.items.map((r) => r.model_name) ?? [])], [runs.data])
  const c = costs.data

  const exportCsv = async () => {
    setExporting(true)
    try {
      const text = await api.text('/analytics/costs/export', { days, model: model || undefined, agent: agent || undefined })
      downloadText('travelgraph-costs.csv', text, 'text/csv')
      toast.success('CSV exported')
    } catch (e) {
      toast.error('Export failed', e instanceof ApiError ? e.message : undefined)
    } finally {
      setExporting(false)
    }
  }

  const trend = useMemo(() => c?.trend.map((t) => ({ ...t, label: t.date.slice(5) })) ?? [], [c])
  const agentRows = c?.by_agent ?? []
  const modelRows = c?.by_model ?? []
  const visibleRuns = (runs.data?.items ?? []).filter((r) => (days === 0 ? true : Date.now() - new Date(r.created_at).getTime() <= days * 86400000) && (!model || r.model_name === model))

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <PageHeader
        icon={<Database className="size-6" />}
        title="Cost Explorer"
        subtitle="AI usage cost across all agent runs (USD)."
        actions={
          <>
            <select aria-label="Date range" value={days} onChange={(e) => setDays(Number(e.target.value))} className="tg-input h-10 w-auto rounded-xl bg-surface-2 text-sm font-semibold">
              {RANGES.map((r) => <option key={r.v} value={r.v}>{r.l}</option>)}
            </select>
            <select aria-label="Model" value={model} onChange={(e) => setModel(e.target.value)} className="tg-input h-10 w-auto rounded-xl bg-surface-2 text-sm font-semibold">
              <option value="">All models</option>
              {models.map((m) => <option key={m}>{m}</option>)}
            </select>
            <select aria-label="Agent" value={agent} onChange={(e) => setAgent(e.target.value)} className="tg-input h-10 w-auto rounded-xl bg-surface-2 text-sm font-semibold">
              <option value="">All agents</option>
              {AGENTS.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
            <button type="button" onClick={exportCsv} disabled={exporting} className="tg-btn tg-btn-secondary h-10">{exporting ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />} Export</button>
          </>
        }
      />

      {costs.isError ? <ErrorState error={costs.error} onRetry={() => costs.refetch()} title="Could not load costs" /> : (
        <>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
            {c && <ProvenanceBadge value={c.provenance} />}
            <span>{c?.note ?? 'Seeded demo charges are illustrative, not an invoice.'}</span>
          </div>
          {c && c.unpriced_run_count > 0 && (
            <div role="status" className="flex items-center gap-2 rounded-xl border border-warn/30 bg-warn-soft px-4 py-2.5 text-sm text-warn"><TriangleAlert className="size-4" /> {c.unpriced_run_count} run(s) used tokens but have no price recorded and are not included in totals.</div>
          )}

          <section className="grid grid-cols-2 gap-3 xl:grid-cols-5" aria-label="Cost summary">
            <MetricCard icon={Coins} label="Total AI cost" highlight value={costs.isPending ? '…' : formatUSD(c?.total_cost_usd)} sub={`${c?.run_count ?? 0} runs in range`} />
            <MetricCard icon={Hash} label="Total tokens" value={costs.isPending ? '…' : formatNumber(c?.total_tokens)} sub={`${formatNumber(c?.input_tokens)} in / ${formatNumber(c?.output_tokens)} out`} />
            <MetricCard icon={Calculator} label="Avg cost / completed run" value={costs.isPending ? '…' : formatUSD(c?.avg_cost_per_run_usd)} />
            <MetricCard icon={Cpu} label="Model cost" value={costs.isPending ? '…' : formatUSD(c?.model_cost_usd)} sub={c && c.total_cost_usd ? `${((c.model_cost_usd / c.total_cost_usd) * 100).toFixed(1)}% of total` : undefined} />
            <MetricCard icon={Wrench} label="Tool / API cost" value={costs.isPending ? '…' : formatUSD(c?.tool_cost_usd)} sub={c && c.total_cost_usd ? `${((c.tool_cost_usd / c.total_cost_usd) * 100).toFixed(1)}% of total` : undefined} />
          </section>

          {!costs.isPending && c && c.run_count === 0 ? (
            <EmptyState icon={Database} title="No costs in this range" description="Try a wider date range or clear the model and agent filters." />
          ) : (
            <>
              <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
                <ChartCard title="Cost trend" subtitle="Daily cost, stacked model vs tool (USD)" icon={<Activity className="size-4" />}>
                  {costs.isPending ? <LoadingSkeleton rows={4} /> : (
                    <TrendAreaChart data={trend} xKey="label" yFormat={(v) => formatUSD(v)} series={[{ key: 'model_cost_usd', label: 'Model', color: '#818cf8' }, { key: 'tool_cost_usd', label: 'Tools', color: '#34d399' }]} />
                  )}
                </ChartCard>
                <ChartCard title="Cost by agent" subtitle="Share of total cost" icon={<Cpu className="size-4" />}>
                  {costs.isPending ? <LoadingSkeleton rows={4} /> : (
                    <DonutChart data={agentRows.filter((a) => a.cost_usd > 0).map((a) => ({ name: agentName(a.agent), value: a.cost_usd, color: agentColor(a.agent) }))} format={(v) => formatUSD(v)} center={<div><p className="text-lg font-extrabold">{formatUSD(c?.total_cost_usd)}</p><p className="text-xs text-muted">Total</p></div>} />
                  )}
                </ChartCard>
              </div>

              <div className="grid gap-5 xl:grid-cols-2">
                <ChartCard title="Cost by model" subtitle="Tools are listed separately (no model)" icon={<Cpu className="size-4" />}>
                  {costs.isPending ? <LoadingSkeleton rows={3} /> : <HorizontalBars data={modelRows.map((m) => ({ name: m.model, value: m.cost_usd }))} format={(v) => formatUSD(v)} />}
                </ChartCard>
                <ChartCard title="Per-agent analysis" subtitle="Tokens and cost per agent role" icon={<Database className="size-4" />}>
                  <div className="overflow-x-auto"><table className="w-full min-w-[460px] text-sm">
                    <thead className="text-xs text-muted"><tr><th className="py-1.5 text-left">Agent</th><th className="text-right">In</th><th className="text-right">Out</th><th className="text-right">Cost</th><th className="text-right">Share</th></tr></thead>
                    <tbody className="divide-y divide-line">
                      {agentRows.map((a) => <tr key={a.agent}><td className="py-2 font-medium">{agentName(a.agent)}</td><td className="text-right tg-mono text-xs">{formatNumber(a.tokens_in)}</td><td className="text-right tg-mono text-xs">{formatNumber(a.tokens_out)}</td><td className="text-right tg-mono text-xs font-semibold">{formatUSD(a.cost_usd)}</td><td className="text-right text-xs">{a.share_pct.toFixed(1)}%</td></tr>)}
                      {agentRows.length === 0 && <tr><td colSpan={5} className="py-6 text-center text-muted">No data</td></tr>}
                    </tbody>
                  </table></div>
                </ChartCard>
              </div>

              <section className="tg-card overflow-hidden" aria-label="Runs">
                <header className="border-b border-line px-4 py-3"><h2 className="text-sm font-bold">Runs</h2><p className="text-xs text-muted">Open a run for its full cost breakdown and CSV export.</p></header>
                {runs.isPending ? <div className="p-4"><LoadingSkeleton rows={3} /></div> : visibleRuns.length === 0 ? <p className="p-6 text-center text-sm text-muted">No runs in this range.</p> : (
                  <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm">
                    <thead className="bg-surface-2 text-xs text-muted"><tr><th className="px-4 py-2">Run</th><th className="px-2 py-2">Trip</th><th className="px-2 py-2">Model</th><th className="px-2 py-2">Status</th><th className="px-2 py-2 text-right">Tokens</th><th className="px-2 py-2 text-right">Runtime</th><th className="px-2 py-2 text-right">Cost</th><th className="px-4 py-2">Date</th></tr></thead>
                    <tbody className="divide-y divide-line">
                      {visibleRuns.slice(0, 25).map((r) => (
                        <tr key={r.id} className="hover:bg-primary-soft/40">
                          <td className="px-4 py-2"><Link to={`/costs/runs/${r.public_id}`} className="tg-mono text-xs font-semibold text-primary hover:underline">{r.public_id}</Link></td>
                          <td className="max-w-[200px] truncate px-2 py-2">{r.trip_title ?? <span className="text-muted">—</span>}</td>
                          <td className="tg-mono px-2 py-2 text-xs">{r.model_name}</td>
                          <td className="px-2 py-2"><StatusPill status={r.status} size="sm" /></td>
                          <td className="tg-mono px-2 py-2 text-right text-xs">{formatNumber(r.input_tokens + r.output_tokens)}</td>
                          <td className="px-2 py-2 text-right text-xs">{formatDuration(r.wall_time_ms)}</td>
                          <td className="tg-mono px-2 py-2 text-right text-xs font-semibold">{formatUSD(r.total_cost_usd)}</td>
                          <td className="px-4 py-2 text-xs text-muted">{formatDate(r.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table></div>
                )}
              </section>
            </>
          )}
        </>
      )}
    </div>
  )
}
