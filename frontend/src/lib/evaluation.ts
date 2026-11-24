import { titleCase } from './utils'
import type { CompareOut, CompareRun } from './types'

export const METRIC_LABELS: Record<string, string> = {
  budget_compliance: 'Budget Compliance',
  day_count_validity: 'Day Count Validity',
  itinerary_completeness: 'Itinerary Completeness',
  preference_coverage: 'Preference Coverage',
  tool_success_rate: 'Tool Success Rate',
  error_count: 'Error Count',
  latency_score: 'Latency Score',
  relevance: 'Relevance',
  coherence: 'Coherence',
  feasibility: 'Feasibility',
  recommendation_quality: 'Recommendation Quality',
  unsupported_claims: 'Unsupported Claims',
}
export const metricLabel = (n: string) => METRIC_LABELS[n] ?? titleCase(n)

/** Lower value is better only for counts (errors, unsupported claims). */
export function lowerIsBetter(unit: string): boolean {
  return unit === 'count'
}

/** Normalize any metric to a 0-100 "higher is better" scale (for bars and radar). */
export function normalizeMetric(value: number | null | undefined, unit: string): number | null {
  if (value == null) return null
  if (unit === '%') return Math.max(0, Math.min(100, value))
  if (unit === '/5') return Math.max(0, Math.min(100, value * 20))
  if (unit === 'count') return Math.max(0, 100 - value * 20)
  return Math.max(0, Math.min(100, value))
}

export function formatMetric(value: number | null | undefined, unit: string): string {
  if (value == null) return 'Not evaluated'
  if (unit === '%') return `${value.toFixed(value % 1 ? 1 : 0)}%`
  if (unit === '/5') return `${value.toFixed(2).replace(/0$/, '')} / 5`
  if (unit === 'count') return String(Math.round(value))
  return String(value)
}

export function formatDelta(delta: number | null | undefined, unit: string): string {
  if (delta == null) return '—'
  const sign = delta > 0 ? '+' : delta < 0 ? '−' : ''
  const abs = Math.abs(delta)
  if (unit === '%') return `${sign}${abs.toFixed(1)} pp`
  return `${sign}${abs.toFixed(2).replace(/\.?0+$/, '') || '0'}`
}

export type Winner = { runId: string; publicId: string } | 'tie' | 'n/a'

/** Winner among runs for a metric using a "higher-is-better" comparator. */
export function pickWinner(
  runs: { runId: string; publicId: string; value: number | null | undefined }[],
  lowerBetter: boolean,
): Winner {
  const valid = runs.filter((r) => r.value != null) as { runId: string; publicId: string; value: number }[]
  if (valid.length < 2) return 'n/a'
  const best = valid.reduce((a, b) => ((lowerBetter ? b.value < a.value : b.value > a.value) ? b : a))
  const tied = valid.filter((r) => Math.abs(r.value - best.value) < 1e-9)
  if (tied.length > 1) return 'tie'
  return { runId: best.runId, publicId: best.publicId }
}

export function overallOf(run: CompareRun): { value: number | null; kind: string } {
  const k = run.overall_by_kind
  if (k.deterministic != null) return { value: k.deterministic, kind: 'deterministic' }
  const first = Object.entries(k).find(([, v]) => v != null)
  return first ? { value: first[1] as number, kind: first[0] } : { value: null, kind: '' }
}

export interface CompareRow {
  key: string
  label: string
  unit: string
  lowerBetter: boolean
  values: Record<string, number | null | undefined>
  winner: Winner
  /** delta of each non-baseline run vs baseline (raw units) */
  deltas: Record<string, number | null>
}

/** Build metric rows incl. wall time and AI cost (lower is better). */
export function buildCompareRows(cmp: CompareOut): CompareRow[] {
  const base = cmp.baseline_run_id
  const rows: CompareRow[] = []
  const overallValues: Record<string, number | null> = {}
  cmp.runs.forEach((r) => (overallValues[r.run_id] = overallOf(r).value))
  rows.push(mk('overall', 'Overall Score', '/5', false, overallValues, cmp, base))
  for (const name of cmp.metric_names) {
    const unit = cmp.metric_units[name] ?? ''
    const values: Record<string, number | null | undefined> = {}
    cmp.runs.forEach((r) => (values[r.run_id] = r.metrics[name]))
    rows.push(mk(name, metricLabel(name), unit, lowerIsBetter(unit), values, cmp, base))
  }
  const lat: Record<string, number | null> = {}
  const cost: Record<string, number | null> = {}
  cmp.runs.forEach((r) => {
    lat[r.run_id] = r.wall_time_ms ? r.wall_time_ms / 1000 : null
    cost[r.run_id] = r.total_cost_usd
  })
  rows.push(mk('wall_time', 'Latency (s)', 's', true, lat, cmp, base))
  rows.push(mk('cost', 'AI Cost (USD)', 'usd', true, cost, cmp, base))
  return rows
}

function mk(key: string, label: string, unit: string, lowerBetter: boolean, values: Record<string, number | null | undefined>, cmp: CompareOut, base: string): CompareRow {
  const deltas: Record<string, number | null> = {}
  cmp.runs.forEach((r) => {
    if (r.run_id === base) return
    const a = values[base]
    const b = values[r.run_id]
    deltas[r.run_id] = a != null && b != null ? Math.round((b - a) * 10000) / 10000 : null
  })
  return {
    key,
    label,
    unit,
    lowerBetter,
    values,
    deltas,
    winner: pickWinner(cmp.runs.map((r) => ({ runId: r.run_id, publicId: r.public_id, value: values[r.run_id] })), lowerBetter),
  }
}

/** Plain-language findings derived only from the returned numbers. */
export function deriveInsights(cmp: CompareOut, rows: CompareRow[]): { headline: string; findings: string[]; leader: string | null } {
  const tally: Record<string, number> = {}
  let counted = 0
  rows.forEach((r) => {
    if (typeof r.winner === 'object') {
      tally[r.winner.publicId] = (tally[r.winner.publicId] ?? 0) + 1
      counted += 1
    }
  })
  const leaderEntry = Object.entries(tally).sort((a, b) => b[1] - a[1])
  const leader = leaderEntry.length && (leaderEntry.length === 1 || leaderEntry[0][1] > leaderEntry[1][1]) ? leaderEntry[0][0] : null
  const findings: string[] = []
  const [a, b] = cmp.runs
  const overall = rows.find((r) => r.key === 'overall')
  if (b && overall && overall.values[a.run_id] != null && overall.values[b.run_id] != null) {
    const d = (overall.values[b.run_id] as number) - (overall.values[a.run_id] as number)
    findings.push(`Overall score: ${b.public_id} is ${d >= 0 ? '+' : '−'}${Math.abs(d).toFixed(2)} vs ${a.public_id}.`)
  }
  const lat = rows.find((r) => r.key === 'wall_time')
  if (b && lat && lat.values[a.run_id] && lat.values[b.run_id]) {
    const pct = (((lat.values[b.run_id] as number) - (lat.values[a.run_id] as number)) / (lat.values[a.run_id] as number)) * 100
    findings.push(`Latency: ${b.public_id} is ${Math.abs(pct).toFixed(0)}% ${pct <= 0 ? 'faster' : 'slower'} (${(lat.values[b.run_id] as number).toFixed(1)}s vs ${(lat.values[a.run_id] as number).toFixed(1)}s).`)
  }
  const cost = rows.find((r) => r.key === 'cost')
  if (b && cost && cost.values[a.run_id] && cost.values[b.run_id]) {
    const pct = (((cost.values[b.run_id] as number) - (cost.values[a.run_id] as number)) / (cost.values[a.run_id] as number)) * 100
    findings.push(`AI cost: ${b.public_id} is ${Math.abs(pct).toFixed(0)}% ${pct <= 0 ? 'cheaper' : 'more expensive'} ($${(cost.values[b.run_id] as number).toFixed(4)} vs $${(cost.values[a.run_id] as number).toFixed(4)}).`)
  }
  if (cmp.missing.length) findings.push(`${cmp.missing.length} metric value(s) are Not evaluated and excluded from winners.`)
  return {
    leader,
    headline: leader ? `${leader} leads on ${tally[leader]} of ${counted} comparable metrics` : counted ? 'No clear overall winner: metrics are split or tied' : 'Not enough evaluated metrics to pick a winner',
    findings,
  }
}
