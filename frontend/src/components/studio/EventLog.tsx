import { useEffect, useMemo, useRef, useState } from 'react'
import { CheckCircle2, ListFilter, Play, Search, TriangleAlert, Wrench, XCircle, Circle } from 'lucide-react'
import { eventDetail, eventLabel, eventMatches, type EventFilter } from '@/lib/agents'
import type { AgentEvent } from '@/lib/types'
import { cn, formatDuration } from '@/lib/utils'

function iconFor(ev: AgentEvent) {
  if (ev.type.endsWith('failed')) return <XCircle className="size-4 text-danger" />
  if (ev.type === 'validation.warning') return <TriangleAlert className="size-4 text-warn" />
  if (ev.type.startsWith('tool.')) return <Wrench className="size-4 text-primary" />
  if (ev.type.endsWith('completed') || ev.type.endsWith('succeeded')) return <CheckCircle2 className="size-4 text-mint" />
  if (ev.type.endsWith('started')) return <Play className="size-4 text-primary" />
  return <Circle className="size-3.5 text-muted" />
}

interface Props {
  events: AgentEvent[]
  times?: number[]
  /** seq of the event to highlight (replay cursor) */
  activeSeq?: number
  onSelect?: (ev: AgentEvent) => void
  runLabel?: string
  followTail?: boolean
}

export function EventLog({ events, times, activeSeq, onSelect, runLabel, followTail }: Props) {
  const [filter, setFilter] = useState<EventFilter>('all')
  const [q, setQ] = useState('')
  const listRef = useRef<HTMLOListElement>(null)

  const rows = useMemo(
    () =>
      events
        .map((ev, i) => ({ ev, t: times?.[i] }))
        .filter(({ ev }) => eventMatches(ev, filter))
        .filter(({ ev }) => {
          const needle = q.trim().toLowerCase()
          if (!needle) return true
          return `${eventLabel(ev)} ${eventDetail(ev)} ${ev.type}`.toLowerCase().includes(needle)
        }),
    [events, times, filter, q],
  )

  useEffect(() => {
    const el = listRef.current
    if (!el) return
    if (followTail) el.scrollTop = el.scrollHeight
    else if (activeSeq != null) {
      const item = el.querySelector<HTMLElement>(`[data-seq="${activeSeq}"]`)
      if (item) el.scrollTop = item.offsetTop - el.clientHeight / 2 + item.clientHeight / 2
    }
  }, [rows.length, activeSeq, followTail])

  return (
    <section className="tg-card flex min-h-0 flex-col p-4" aria-label="Event log">
      <header className="mb-3 flex flex-wrap items-center gap-2">
        <h2 className="text-sm font-bold">Event Log {runLabel && <span className="font-normal text-muted">({runLabel})</span>}</h2>
        <span className="text-xs text-muted">{rows.length} of {events.length} events</span>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <label className="relative">
            <span className="sr-only">Search events</span>
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search events…" className="tg-input h-9 w-44 rounded-lg pl-8 text-xs" />
          </label>
          <label className="flex items-center gap-1.5">
            <ListFilter className="size-4 text-muted" aria-hidden />
            <span className="sr-only">Filter events</span>
            <select value={filter} onChange={(e) => setFilter(e.target.value as EventFilter)} className="tg-input h-9 w-auto rounded-lg pr-7 text-xs">
              <option value="all">All events</option>
              <option value="agents">Agents & run</option>
              <option value="tools">Tool calls</option>
              <option value="warnings">Warnings & failures</option>
            </select>
          </label>
        </div>
      </header>
      {rows.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted">{events.length === 0 ? 'Waiting for events…' : 'No events match.'}</p>
      ) : (
        <ol ref={listRef} className="relative grid max-h-64 gap-2 overflow-y-auto pr-1 sm:grid-cols-2 xl:grid-cols-3">
          {rows.map(({ ev, t }) => {
            const active = activeSeq === ev.seq
            const Wrapper = onSelect ? 'button' : 'div'
            return (
              <li key={ev.id} data-seq={ev.seq}>
                <Wrapper
                  {...(onSelect ? { type: 'button' as const, onClick: () => onSelect(ev) } : {})}
                  className={cn('block w-full rounded-xl border p-2.5 text-left text-xs', active ? 'border-primary bg-primary-soft shadow-[0_0_16px_rgba(129,140,248,0.35)]' : 'border-line bg-surface', onSelect && 'hover:border-primary/60')}
                >
                  <div className="flex items-center gap-2">
                    {iconFor(ev)}
                    <span className="min-w-0 flex-1 truncate font-semibold">{eventLabel(ev)}</span>
                    <span className="tg-mono text-[10px] text-muted">{t != null ? formatDuration(t) : `#${ev.seq}`}</span>
                  </div>
                  <p className="tg-mono mt-1 text-[10px] text-muted">{new Date(ev.ts).toLocaleTimeString('en-IN', { hour12: false })}.{String(new Date(ev.ts).getMilliseconds()).padStart(3, '0')}</p>
                  {eventDetail(ev) && <p className="mt-1 line-clamp-2 text-muted">{eventDetail(ev)}</p>}
                </Wrapper>
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}
