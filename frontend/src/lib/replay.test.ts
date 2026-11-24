import { describe, expect, it } from 'vitest'
import { deriveGraph } from './agents'
import { cursorAt, replayTimes } from '@/hooks/useReplay'
import { buildMilestones } from './timeline'
import type { AgentEvent } from './types'

let seq = 0
const ev = (type: string, node: string | null, offsetMs: number, payload: Record<string, unknown> = {}): AgentEvent => ({
  id: `e${++seq}`, run_id: 'r1', seq, ts: new Date(Date.UTC(2026, 0, 1, 0, 0, 0) + offsetMs).toISOString(), type, node_id: node, status: null, payload,
})

const events: AgentEvent[] = (() => {
  seq = 0
  return [
  ev('run.created', null, 0),
  ev('run.started', null, 100),
  ev('agent.started', 'supervisor', 200),
  ev('agent.completed', 'supervisor', 2000, { duration_ms: 1800, summary: 'Parsed Goa', tokens_in: 10, tokens_out: 5, cost_usd: 0.01 }),
  ev('agent.started', 'destination', 2100),
  ev('agent.started', 'transport', 2100),
  ev('agent.started', 'accommodation', 2100),
  ev('agent.completed', 'destination', 4000, { duration_ms: 1900 }),
  ev('agent.completed', 'transport', 4200, { duration_ms: 2100 }),
  ev('agent.completed', 'accommodation', 4500, { duration_ms: 2400 }),
  ev('agent.started', 'itinerary', 4600),
  ev('agent.completed', 'itinerary', 7000),
  ev('agent.started', 'validator', 7100),
  ev('agent.completed', 'validator', 7300),
  ev('agent.started', 'aggregator', 7400),
  ev('agent.completed', 'aggregator', 9000),
  ev('run.completed', null, 9100),
  ]
})()

describe('deriveGraph (replay state)', () => {
  it('shows only supervisor running part-way through', () => {
    const g = deriveGraph(events, 3)
    expect(g.nodes.find((n) => n.id === 'supervisor')?.status).toBe('running')
    expect(g.nodes.find((n) => n.id === 'destination')?.status).toBe('pending')
    expect(g.currentNode).toBe('supervisor')
    expect(g.runStatus).toBe('running')
  })

  it('runs specialists in parallel', () => {
    const g = deriveGraph(events, 7)
    const running = g.nodes.filter((n) => n.status === 'running').map((n) => n.id).sort()
    expect(running).toEqual(['accommodation', 'destination', 'transport'])
  })

  it('completes everything at the end and aggregates tokens/cost', () => {
    const g = deriveGraph(events)
    expect(g.runStatus).toBe('completed')
    expect(g.nodes.every((n) => n.status === 'completed')).toBe(true)
    const sup = g.nodes.find((n) => n.id === 'supervisor')!
    expect(sup.input_tokens).toBe(10)
    expect(sup.cost_usd).toBe(0.01)
    expect(sup.summary).toBe('Parsed Goa')
    expect(g.currentNode).toBeNull()
  })

  it('marks never-started nodes as skipped once the run is terminal', () => {
    const failedRun = [ev('run.started', null, 0), ev('agent.started', 'supervisor', 10), ev('agent.failed', 'supervisor', 20), ev('run.failed', null, 30)]
    const g = deriveGraph(failedRun)
    expect(g.nodes.find((n) => n.id === 'supervisor')?.status).toBe('failed')
    expect(g.nodes.find((n) => n.id === 'itinerary')?.status).toBe('skipped')
  })

  it('counts validator retries as extra itinerary attempts', () => {
    const retry = [...events.slice(0, 13), ev('agent.started', 'itinerary', 7200)]
    expect(deriveGraph(retry).nodes.find((n) => n.id === 'itinerary')?.invocations).toBe(2)
  })
})

describe('replay timing', () => {
  it('uses real offsets when the run took a while', () => {
    const { times, duration } = replayTimes(events)
    expect(times[0]).toBe(0)
    expect(duration).toBe(9100)
  })

  it('spreads near-instant runs synthetically so replay is watchable', () => {
    const instant = [ev('run.started', null, 0), ev('agent.started', 'supervisor', 5), ev('run.completed', null, 10)]
    const { times, duration } = replayTimes(instant)
    expect(times).toEqual([0, 350, 700])
    expect(duration).toBe(700)
  })

  it('finds the cursor event for a time', () => {
    const times = [0, 100, 200, 500]
    expect(cursorAt(times, -1)).toBe(-1)
    expect(cursorAt(times, 0)).toBe(0)
    expect(cursorAt(times, 150)).toBe(1)
    expect(cursorAt(times, 9999)).toBe(3)
  })
})

describe('milestones', () => {
  it('builds the condensed timeline and reflects progress', () => {
    const { times } = replayTimes(events)
    const m = buildMilestones(events, times)
    expect(m.map((x) => x.key)).toEqual(['start', 'supervisor', 'parallel', 'itinerary', 'validator', 'aggregator', 'end'])
    expect(m.every((x) => x.seq != null)).toBe(true)
    const partial = events.slice(0, 7)
    const pm = buildMilestones(partial, replayTimes(partial).times)
    expect(pm.find((x) => x.key === 'parallel')?.seq).toBeUndefined()
    expect(pm.find((x) => x.key === 'parallel')?.active).toBe(true)
    expect(pm.find((x) => x.key === 'end')?.seq).toBeUndefined()
  })
})
