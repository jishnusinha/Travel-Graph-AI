import { useMemo } from 'react'
import { useRun, useRunGraph } from './queries'
import { useRunStream } from './useRunStream'
import { deriveGraph, TERMINAL_STATUSES } from '@/lib/agents'
import type { GraphNode } from '@/lib/types'

/** Everything the Studio / Replay pages need for one run. */
export function useStudioRun(runId: string | undefined) {
  const run = useRun(runId)
  const graph = useRunGraph(runId)
  const stream = useRunStream(runId)

  const derived = useMemo(() => deriveGraph(stream.events), [stream.events])
  const status = derived.runStatus !== 'pending' ? derived.runStatus : (run.data?.status ?? 'pending')
  const terminal = TERMINAL_STATUSES.has(status)

  const nodes: GraphNode[] = useMemo(() => {
    const server = graph.data
    if (terminal && server && server.last_seq >= derived.lastSeq) return server.nodes
    if (stream.events.length) return derived.nodes
    return server?.nodes ?? derived.nodes
  }, [graph.data, derived, terminal, stream.events.length])

  return { run, graph, stream, derived, status, terminal, nodes, edges: graph.data?.edges }
}
