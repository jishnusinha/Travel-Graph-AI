import { useState, type ReactNode } from 'react'
import { Box, Clock, Coins, Copy, FileText, Wrench, X, Cpu, TriangleAlert, ListChecks } from 'lucide-react'
import { StatusPill } from '@/components/ui/StatusPill'
import { Skeleton } from '@/components/ui/Skeleton'
import { useToast } from '@/components/ui/Toast'
import { useNodeDetail } from '@/hooks/queries'
import { AGENT_BY_ID, eventDetail, eventLabel } from '@/lib/agents'
import type { AgentEvent, GraphNode, Run } from '@/lib/types'
import { cn, formatDate, formatDuration, formatINR, formatNumber, formatUSD } from '@/lib/utils'

type Tab = 'details' | 'logs' | 'state' | 'artifacts'

interface Props {
  runId: string | undefined
  run: Run | undefined
  node: GraphNode | null
  /** events visible at the current moment (live: all so far; replay: up to cursor) */
  events: AgentEvent[]
  replay?: boolean
  onClose?: () => void
  className?: string
}

function Section({ icon: Icon, title, children }: { icon: typeof Box; title: string; children: ReactNode }) {
  return (
    <section className="mt-4">
      <h3 className="mb-1.5 flex items-center gap-2 text-sm font-bold"><Icon className="size-4 text-muted" aria-hidden /> {title}</h3>
      {children}
    </section>
  )
}

export function AgentInspector({ runId, run, node, events, replay, onClose, className }: Props) {
  const [tab, setTab] = useState<Tab>('details')
  const toast = useToast()
  const nodeEvents = events.filter((e) => e.node_id === node?.id)
  const settled = node?.status === 'completed' || node?.status === 'failed'
  const detail = useNodeDetail(runId, node?.id ?? null, !replay || settled)
  const meta = node ? AGENT_BY_ID[node.id] : undefined
  const Icon = meta?.icon
  const tabs: Tab[] = replay ? ['details', 'logs', 'state', 'artifacts'] : ['details', 'logs', 'state']

  const started = nodeEvents.find((e) => e.type === 'agent.started')
  const inputKeys = (started?.payload?.input_keys as string[] | undefined) ?? []
  const completions = nodeEvents.filter((e) => e.type === 'agent.completed')
  const warnings = nodeEvents.filter((e) => e.type === 'validation.warning')
  const d = detail.data
  const model = d?.model_invocations[0]
  const done = events.some((e) => e.type === 'run.completed')

  return (
    <aside aria-label="Agent inspector" className={cn('tg-card flex min-h-0 flex-col', className)}>
      <div className="flex items-center justify-between gap-2 border-b border-line px-3 pt-3">
        <div role="tablist" aria-label="Inspector sections" className="flex gap-1">
          {tabs.map((t) => (
            <button key={t} role="tab" aria-selected={tab === t} type="button" onClick={() => setTab(t)}
              className={cn('rounded-t-lg border-b-2 px-3 py-2 text-sm font-semibold capitalize', tab === t ? 'border-primary text-primary-ink' : 'border-transparent text-muted hover:text-ink')}>
              {t}
            </button>
          ))}
        </div>
        {onClose && <button type="button" aria-label="Close inspector" onClick={onClose} className="mb-1 rounded-lg p-1.5 text-muted hover:bg-primary-soft lg:hidden"><X className="size-4" /></button>}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {!node || !meta || !Icon ? (
          <p className="py-10 text-center text-sm text-muted">Select an agent node to inspect its input, output, tool calls and cost.</p>
        ) : (
          <>
            <div className="flex items-start gap-3">
              <span className="grid size-12 shrink-0 place-items-center rounded-xl" style={{ background: `${meta.color}26`, color: meta.color }}><Icon className="size-6" /></span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="text-base font-bold">{meta.name}</h2>
                  <StatusPill status={replay && node.status === 'running' ? 'replaying' : node.status} size="sm" />
                </div>
                <p className="text-xs text-muted">({meta.subtitle})</p>
                <p className="mt-1 flex items-center gap-1 text-xs text-muted"><Clock className="size-3.5" /> {node.duration_ms != null ? `${formatDuration(node.duration_ms)} total execution time` : 'Not finished yet'}</p>
              </div>
            </div>

            {tab === 'details' && (
              <>
                <Section icon={Box} title="Input">
                  <div className="flex items-start justify-between gap-2 rounded-xl border border-line bg-surface p-3 text-sm">
                    <p className="min-w-0 break-words">
                      {node.id === 'supervisor' ? (run?.prompt ?? '…') : inputKeys.length ? <>State inputs: <span className="tg-mono text-xs">{inputKeys.join(', ')}</span></> : <span className="text-muted">Not started yet.</span>}
                    </p>
                    {node.id === 'supervisor' && run?.prompt && (
                      <button type="button" aria-label="Copy prompt" className="shrink-0 text-muted hover:text-primary" onClick={() => navigator.clipboard.writeText(run.prompt).then(() => toast.info('Prompt copied'))}><Copy className="size-4" /></button>
                    )}
                  </div>
                </Section>
                <Section icon={FileText} title="Output">
                  {completions.length === 0 ? <p className="text-sm text-muted">{node.status === 'running' ? 'Working…' : 'No output yet.'}</p> : (
                    <ul className="list-disc space-y-1 pl-5 text-sm marker:text-mint">
                      {completions.map((c) => <li key={c.id}>{(c.payload.summary as string) || 'Completed'}{completions.length > 1 && <span className="text-xs text-muted"> (attempt {String(c.payload.attempt ?? '?')})</span>}</li>)}
                    </ul>
                  )}
                </Section>

                {warnings.length > 0 && (
                  <Section icon={TriangleAlert} title="Validation warnings">
                    <ul className="space-y-1 text-sm text-warn">{warnings.map((w) => <li key={w.id}>• {(w.payload.message as string) ?? (w.payload.code as string)}</li>)}</ul>
                  </Section>
                )}
                {(d?.errors.length ?? 0) > 0 && (
                  <Section icon={TriangleAlert} title="Errors"><ul className="space-y-1 text-sm text-danger">{d!.errors.map((e, i) => <li key={i}>• {e}</li>)}</ul></Section>
                )}

                <dl className="mt-4 divide-y divide-line rounded-xl border border-line text-sm">
                  <div className="flex items-center justify-between px-3 py-2"><dt className="flex items-center gap-2 text-muted"><Cpu className="size-4" /> Model</dt><dd className="tg-mono text-xs font-semibold">{detail.isPending && !!runId && settled ? '…' : (model?.model ?? (node.input_tokens || node.output_tokens ? run?.model_name : '—') ?? '—')}</dd></div>
                  <div className="flex items-center justify-between px-3 py-2"><dt className="flex items-center gap-2 text-muted"><ListChecks className="size-4" /> Tokens</dt><dd className="font-semibold">{node.input_tokens || node.output_tokens ? `${formatNumber(node.input_tokens)} in / ${formatNumber(node.output_tokens)} out` : '—'}</dd></div>
                  <div className="flex items-center justify-between px-3 py-2"><dt className="flex items-center gap-2 text-muted"><Coins className="size-4" /> Cost (USD)</dt><dd className="tg-mono font-semibold">{node.cost_usd != null ? formatUSD(node.cost_usd) : '—'}</dd></div>
                </dl>

                <Section icon={Wrench} title={`Tool calls (${d?.tool_invocations.length ?? 0})`}>
                  {detail.isPending && settled ? <Skeleton className="h-10 w-full" /> : (d?.tool_invocations.length ?? 0) === 0 ? <p className="text-sm text-muted">No tools used by this agent.</p> : (
                    <ul className="divide-y divide-line rounded-xl border border-line">
                      {d!.tool_invocations.map((t, i) => (
                        <li key={i} className="flex items-center justify-between gap-2 px-3 py-2 text-sm">
                          <span className="min-w-0"><span className="tg-mono block truncate text-xs">{t.tool_name}</span><span className="text-[11px] text-muted">{formatDuration(t.duration_ms)} · {t.provenance}{t.fee_usd > 0 && ` · ${formatUSD(t.fee_usd)}`}</span></span>
                          <StatusPill status={t.status} size="sm" />
                        </li>
                      ))}
                    </ul>
                  )}
                </Section>
              </>
            )}

            {tab === 'logs' && (
              <Section icon={FileText} title={`Event log (${nodeEvents.length})`}>
                {nodeEvents.length === 0 ? <p className="text-sm text-muted">No events for this agent yet.</p> : (
                  <ol className="space-y-2">
                    {nodeEvents.map((e) => (
                      <li key={e.id} className="rounded-xl border border-line bg-surface p-2.5 text-xs">
                        <div className="flex items-center justify-between gap-2"><span className="font-semibold">{eventLabel(e)}</span><span className="tg-mono text-muted">#{e.seq}</span></div>
                        <p className="tg-mono mt-0.5 text-[11px] text-muted">{formatDate(e.ts, true)}</p>
                        {eventDetail(e) && <p className="mt-1 text-muted">{eventDetail(e)}</p>}
                      </li>
                    ))}
                  </ol>
                )}
              </Section>
            )}

            {tab === 'state' && (
              <Section icon={Box} title="State updates">
                <p className="mb-2 text-xs text-muted">Keys this agent read and wrote on the shared graph state.</p>
                <pre className="tg-mono max-h-80 overflow-auto rounded-xl border border-line bg-surface p-3 text-[11px] leading-relaxed">
{JSON.stringify(
  {
    node: node.id,
    status: node.status,
    invocations: node.invocations,
    read: inputKeys,
    wrote: nodeEvents.filter((e) => e.type === 'state.updated').flatMap((e) => (e.payload.keys as string[]) ?? []),
    tokens: { in: node.input_tokens, out: node.output_tokens },
    cost_usd: node.cost_usd,
    summary: node.summary,
  },
  null,
  2,
)}
                </pre>
              </Section>
            )}

            {tab === 'artifacts' && (
              <Section icon={FileText} title="Artifacts">
                {!done || !run ? <p className="text-sm text-muted">The final plan appears once the replay reaches the end of the run.</p> : (
                  <dl className="space-y-2 text-sm">
                    {[
                      ['Plan', run.final_plan.title as string],
                      ['Destination', run.final_plan.destination as string],
                      ['Days', Array.isArray(run.final_plan.days) ? String((run.final_plan.days as unknown[]).length) : undefined],
                      ['Estimated cost', typeof run.final_plan.estimated_cost_inr === 'number' ? formatINR(run.final_plan.estimated_cost_inr) : undefined],
                      ['Recommendation', run.final_plan.recommendation as string],
                    ].filter(([, v]) => v).map(([k, v]) => <div key={k as string} className="rounded-xl border border-line bg-surface p-2.5"><dt className="text-xs text-muted">{k}</dt><dd className="font-medium">{v}</dd></div>)}
                  </dl>
                )}
              </Section>
            )}
          </>
        )}
      </div>
    </aside>
  )
}
