import { useCallback, useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { TERMINAL_EVENTS } from '@/lib/agents'
import type { AgentEvent } from '@/lib/types'
import { qk } from './queries'

export type StreamState = 'idle' | 'loading' | 'live' | 'reconnecting' | 'ended' | 'error'

function mergeEvents(cur: AgentEvent[], incoming: AgentEvent[]): AgentEvent[] {
  if (!incoming.length) return cur
  const seen = new Set(cur.map((e) => e.seq))
  const add = incoming.filter((e) => !seen.has(e.seq))
  if (!add.length) return cur
  return [...cur, ...add].sort((a, b) => a.seq - b.seq)
}

/**
 * Loads a run's persisted events, then (if the run is still active) follows
 * GET /runs/:id/stream (SSE). Falls back to polling when SSE is unavailable.
 * The DB is the source of truth, so reconnects resume with `after_seq`.
 */
export function useRunStream(runId: string | undefined) {
  const qc = useQueryClient()
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [state, setState] = useState<StreamState>('idle')
  const [error, setError] = useState<unknown>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const lastSeq = useRef(0)

  const reload = useCallback(() => setReloadKey((k) => k + 1), [])

  useEffect(() => {
    if (!runId) return
    let cancelled = false
    let source: EventSource | null = null
    let poll: number | null = null
    setEvents([])
    setError(null)
    setState('loading')
    lastSeq.current = 0

    const push = (batch: AgentEvent[]) => {
      if (cancelled || !batch.length) return
      lastSeq.current = Math.max(lastSeq.current, ...batch.map((e) => e.seq))
      setEvents((cur) => mergeEvents(cur, batch))
    }

    const finish = () => {
      if (cancelled) return
      setState('ended')
      source?.close()
      if (poll) window.clearInterval(poll)
      void qc.invalidateQueries({ queryKey: qk.run(runId) })
      void qc.invalidateQueries({ queryKey: qk.graph(runId) })
      void qc.invalidateQueries({ queryKey: ['runs'] })
      void qc.invalidateQueries({ queryKey: ['trips'] })
      void qc.invalidateQueries({ queryKey: ['trip'] })
      void qc.invalidateQueries({ queryKey: ['costs'] })
      void qc.invalidateQueries({ queryKey: qk.dashboard })
    }

    const startPolling = () => {
      if (poll) return
      setState('reconnecting')
      poll = window.setInterval(async () => {
        try {
          const batch = await api.get<AgentEvent[]>(`/runs/${runId}/events`, { after_seq: lastSeq.current, limit: 1000 })
          push(batch)
          if (batch.some((e) => TERMINAL_EVENTS.has(e.type))) finish()
          else if (!cancelled) setState('live')
        } catch {
          /* keep trying */
        }
      }, 2000)
    }

    const startStream = () => {
      if (typeof EventSource === 'undefined') return startPolling()
      source = new EventSource(`/api/v1/runs/${runId}/stream?after_seq=${lastSeq.current}`, { withCredentials: true })
      source.onopen = () => !cancelled && setState('live')
      source.onmessage = (m) => {
        try {
          const ev = JSON.parse(m.data) as AgentEvent
          push([ev])
          if (TERMINAL_EVENTS.has(ev.type)) {
            // the server also sends an `end` event; finish after a tick so the last events render
            window.setTimeout(finish, 150)
          }
        } catch {
          /* ignore malformed frame */
        }
      }
      source.addEventListener('end', () => finish())
      source.onerror = () => {
        if (cancelled) return
        // EventSource retries by itself; if the connection is closed for good, fall back to polling.
        if (source?.readyState === EventSource.CLOSED) {
          source.close()
          startPolling()
        } else {
          setState('reconnecting')
        }
      }
    }

    api
      .get<AgentEvent[]>(`/runs/${runId}/events`, { limit: 10000 })
      .then((batch) => {
        if (cancelled) return
        push(batch)
        if (batch.some((e) => TERMINAL_EVENTS.has(e.type))) {
          setState('ended')
        } else {
          startStream()
        }
      })
      .catch((e) => {
        if (cancelled) return
        setError(e)
        setState('error')
      })

    return () => {
      cancelled = true
      source?.close()
      if (poll) window.clearInterval(poll)
    }
  }, [runId, reloadKey, qc])

  return { events, state, error, reload }
}
