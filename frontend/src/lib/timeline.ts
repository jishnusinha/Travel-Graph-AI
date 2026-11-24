import { TERMINAL_EVENTS, agentName } from './agents'
import type { AgentEvent } from './types'

export interface Milestone {
  key: string
  label: string
  /** event seq when this milestone is reached; undefined = not reached yet */
  seq?: number
  /** ms from the first event */
  t?: number
  failed?: boolean
  active?: boolean
}

const PARALLEL = ['destination', 'transport', 'accommodation']

function lastCompletion(events: AgentEvent[], node: string): AgentEvent | undefined {
  return [...events].reverse().find((e) => e.node_id === node && e.type === 'agent.completed')
}

/** Condensed run timeline: start → supervisor → parallel specialists → itinerary → validator → aggregator → end. */
export function buildMilestones(events: AgentEvent[], times: number[]): Milestone[] {
  const timeOf = (ev?: AgentEvent) => (ev ? times[events.indexOf(ev)] : undefined)
  const out: Milestone[] = []

  const start = events.find((e) => e.type === 'run.started')
  out.push({ key: 'start', label: 'Run started', seq: start?.seq, t: timeOf(start) })

  const sup = lastCompletion(events, 'supervisor')
  out.push({ key: 'supervisor', label: agentName('supervisor'), seq: sup?.seq, t: timeOf(sup), active: !sup && events.some((e) => e.node_id === 'supervisor') })

  const par = PARALLEL.map((n) => lastCompletion(events, n))
  const parDone = par.filter(Boolean) as AgentEvent[]
  const allPar = parDone.length === PARALLEL.length
  const lastPar = allPar ? parDone.reduce((a, b) => (a.seq > b.seq ? a : b)) : undefined
  out.push({
    key: 'parallel',
    label: `${PARALLEL.length} agents (parallel)`,
    seq: lastPar?.seq,
    t: timeOf(lastPar),
    active: !allPar && events.some((e) => PARALLEL.includes(e.node_id ?? '') && e.type === 'agent.started'),
  })

  for (const node of ['itinerary', 'validator', 'aggregator']) {
    const c = lastCompletion(events, node)
    const failed = events.some((e) => e.node_id === node && e.type === 'agent.failed')
    out.push({ key: node, label: agentName(node), seq: c?.seq, t: timeOf(c), failed, active: !c && !failed && events.some((e) => e.node_id === node && e.type === 'agent.started') })
  }

  const end = events.find((e) => TERMINAL_EVENTS.has(e.type))
  out.push({
    key: 'end',
    label: end?.type === 'run.failed' ? 'Run failed' : end?.type === 'run.needs_clarification' ? 'Needs clarification' : 'Run completed',
    seq: end?.seq,
    t: timeOf(end),
    failed: end?.type === 'run.failed',
  })
  return out
}
