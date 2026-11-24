import {
  BedDouble,
  CalendarDays,
  Layers,
  MapPin,
  ShieldCheck,
  Sparkles,
  TrainFront,
  type LucideIcon,
} from 'lucide-react'
import type { AgentEvent, GraphEdge, GraphNode, NodeStatus } from './types'

export interface AgentMeta {
  id: string
  name: string
  subtitle: string
  icon: LucideIcon
  /** position in the React Flow canvas */
  x: number
  y: number
  /** short colour key for charts */
  color: string
}

/** Order matches backend GRAPH_NODES. */
export const AGENTS: AgentMeta[] = [
  { id: 'supervisor', name: 'Supervisor Agent', subtitle: 'Orchestrator', icon: Sparkles, x: 0, y: 0, color: '#818cf8' },
  { id: 'destination', name: 'Destination Research', subtitle: 'Parallel specialist', icon: MapPin, x: -300, y: 170, color: '#34d399' },
  { id: 'transport', name: 'Transport Planning', subtitle: 'Parallel specialist', icon: TrainFront, x: 0, y: 170, color: '#38bdf8' },
  { id: 'accommodation', name: 'Accommodation Agent', subtitle: 'Parallel specialist', icon: BedDouble, x: 300, y: 170, color: '#fbbf24' },
  { id: 'itinerary', name: 'Itinerary Planning', subtitle: 'Day-by-day planner', icon: CalendarDays, x: 0, y: 340, color: '#f472b6' },
  { id: 'validator', name: 'Validator', subtitle: 'Deterministic checks', icon: ShieldCheck, x: 0, y: 480, color: '#a78bfa' },
  { id: 'aggregator', name: 'Response Aggregator', subtitle: 'Final travel plan', icon: Layers, x: 0, y: 620, color: '#2dd4bf' },
]

export const AGENT_BY_ID: Record<string, AgentMeta> = Object.fromEntries(AGENTS.map((a) => [a.id, a]))

export function agentName(id: string | null | undefined): string {
  if (!id) return 'Run'
  return AGENT_BY_ID[id]?.name ?? id.replace(/_/g, ' ')
}

const SHORT: Record<string, string> = { supervisor: 'Supervisor', destination: 'Destination', transport: 'Transport', accommodation: 'Stays', itinerary: 'Itinerary', validator: 'Validator', aggregator: 'Aggregator' }
export const agentShort = (id: string) => SHORT[id] ?? agentName(id)

export function agentColor(id: string): string {
  return AGENT_BY_ID[id]?.color ?? '#94a3b8'
}

export const FALLBACK_EDGES: GraphEdge[] = [
  ['supervisor', 'destination'],
  ['supervisor', 'transport'],
  ['supervisor', 'accommodation'],
  ['destination', 'itinerary'],
  ['transport', 'itinerary'],
  ['accommodation', 'itinerary'],
  ['itinerary', 'validator'],
  ['validator', 'aggregator'],
  ['validator', 'itinerary'],
].map(([source, target]) => ({ id: `${source}-${target}`, source, target }))

export const TERMINAL_EVENTS = new Set(['run.completed', 'run.failed', 'run.needs_clarification'])
export const TERMINAL_STATUSES = new Set(['completed', 'failed', 'needs_clarification'])

function emptyNode(id: string): GraphNode {
  return {
    id,
    label: agentName(id),
    status: 'pending',
    duration_ms: null,
    role: id,
    invocations: 0,
    started_at: null,
    completed_at: null,
    input_tokens: 0,
    output_tokens: 0,
    cost_usd: null,
    summary: null,
  }
}

export interface DerivedGraph {
  nodes: GraphNode[]
  currentNode: string | null
  lastSeq: number
  runStatus: 'pending' | 'running' | 'completed' | 'failed' | 'needs_clarification'
}

/**
 * Rebuild node state from persisted events (mirrors backend `build_graph`).
 * Used both for live SSE updates and for replay — never calls a model.
 */
export function deriveGraph(events: AgentEvent[], upToSeq: number = Infinity): DerivedGraph {
  const nodes = new Map<string, GraphNode>(AGENTS.map((a) => [a.id, emptyNode(a.id)]))
  const running: string[] = []
  let lastSeq = 0
  let runStatus: DerivedGraph['runStatus'] = 'pending'
  const sorted = [...events].sort((a, b) => a.seq - b.seq)
  for (const ev of sorted) {
    if (ev.seq > upToSeq) break
    lastSeq = ev.seq
    if (ev.type === 'run.started') runStatus = 'running'
    if (ev.type === 'run.completed') runStatus = 'completed'
    if (ev.type === 'run.failed') runStatus = 'failed'
    if (ev.type === 'run.needs_clarification') runStatus = 'needs_clarification'
    const n = ev.node_id ? nodes.get(ev.node_id) : undefined
    if (!n || !ev.node_id) continue
    const p = ev.payload ?? {}
    const drop = () => {
      const i = running.indexOf(n.id)
      if (i >= 0) running.splice(i, 1)
    }
    if (ev.type === 'agent.started') {
      n.status = 'running'
      n.invocations += 1
      n.started_at = n.started_at ?? ev.ts
      n.completed_at = null
      drop()
      running.push(n.id)
    } else if (ev.type === 'agent.completed') {
      n.status = 'completed'
      n.completed_at = ev.ts
      n.duration_ms = (p.duration_ms as number | undefined) ?? n.duration_ms
      n.summary = (p.summary as string | undefined) ?? n.summary
      n.input_tokens += Number(p.tokens_in ?? 0)
      n.output_tokens += Number(p.tokens_out ?? 0)
      if (p.cost_usd != null) n.cost_usd = Math.round(((n.cost_usd ?? 0) + Number(p.cost_usd)) * 1e6) / 1e6
      drop()
    } else if (ev.type === 'agent.failed') {
      n.status = 'failed'
      n.completed_at = ev.ts
      drop()
    }
  }
  const terminal = runStatus === 'completed' || runStatus === 'failed' || runStatus === 'needs_clarification'
  const out = [...nodes.values()].map((n) =>
    n.status === 'pending' && terminal ? { ...n, status: 'skipped' as NodeStatus } : n,
  )
  return {
    nodes: out,
    currentNode: terminal ? null : (running[running.length - 1] ?? null),
    lastSeq,
    runStatus,
  }
}

/** Relative ms of each event from the first event. */
export function relativeTimes(events: AgentEvent[]): number[] {
  if (!events.length) return []
  const t0 = new Date(events[0].ts).getTime()
  return events.map((e) => Math.max(0, new Date(e.ts).getTime() - t0))
}

export function eventLabel(ev: AgentEvent): string {
  const name = agentName(ev.node_id)
  switch (ev.type) {
    case 'run.created':
      return 'Run created'
    case 'run.started':
      return 'Run started'
    case 'run.completed':
      return 'Run completed'
    case 'run.failed':
      return 'Run failed'
    case 'run.needs_clarification':
      return 'Clarification needed'
    case 'agent.started':
      return `${name} started`
    case 'agent.completed':
      return `${name} completed`
    case 'agent.failed':
      return `${name} failed`
    case 'tool.called':
      return `${name} · tool call`
    case 'tool.succeeded':
      return `${name} · tool succeeded`
    case 'validation.warning':
      return 'Validation warning'
    case 'state.updated':
      return `${name} · state updated`
    default:
      return ev.type
  }
}

export function eventDetail(ev: AgentEvent): string {
  const p = ev.payload ?? {}
  if (typeof p.summary === 'string') return p.summary
  if (typeof p.message === 'string') return p.message
  if (typeof p.error === 'string') return p.error
  if (typeof p.tool === 'string') return `Tool: ${p.tool}`
  if (typeof p.clarification === 'string') return p.clarification
  if (Array.isArray(p.keys)) return `Updated: ${(p.keys as string[]).join(', ')}`
  if (p.wall_time_ms != null) return `Wall time ${(Number(p.wall_time_ms) / 1000).toFixed(1)}s`
  return ''
}

export type EventFilter = 'all' | 'agents' | 'tools' | 'warnings'
export function eventMatches(ev: AgentEvent, f: EventFilter): boolean {
  switch (f) {
    case 'agents':
      return ev.type.startsWith('agent.') || ev.type.startsWith('run.')
    case 'tools':
      return ev.type.startsWith('tool.')
    case 'warnings':
      return ev.type === 'validation.warning' || ev.type.endsWith('failed')
    default:
      return true
  }
}
