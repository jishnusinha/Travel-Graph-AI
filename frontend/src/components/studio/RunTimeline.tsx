import { Activity, AlertCircle, CheckCircle2, Circle, Loader2 } from 'lucide-react'
import { cn, formatDuration } from '@/lib/utils'
import type { Milestone } from '@/lib/timeline'

interface Props {
  milestones: Milestone[]
  /** highest seq reached (live: last seq; replay: cursor seq) */
  reachedSeq: number
  eventCount: number
  totalMs?: number
  onSelect?: (m: Milestone) => void
  title?: string
}

export function RunTimeline({ milestones, reachedSeq, eventCount, totalMs, onSelect, title = 'Run timeline' }: Props) {
  return (
    <section className="tg-card p-4" aria-label={title}>
      <header className="mb-3 flex items-center gap-2">
        <Activity className="size-4 text-primary" aria-hidden />
        <h2 className="text-sm font-bold">{title}</h2>
        <span className="text-xs text-muted">{eventCount} events{totalMs != null ? ` · ${formatDuration(totalMs)} total` : ''}</span>
      </header>
      <ol className="flex items-start gap-0 overflow-x-auto pb-1">
        {milestones.map((m, i) => {
          const reached = m.seq != null && m.seq <= reachedSeq
          const Icon = m.failed && reached ? AlertCircle : reached ? CheckCircle2 : m.active ? Loader2 : Circle
          return (
            <li key={m.key} className="flex min-w-[112px] flex-1 items-start">
              <button
                type="button"
                disabled={!onSelect || m.seq == null}
                onClick={() => onSelect?.(m)}
                className="group flex w-full flex-col items-center gap-1 px-1 text-center disabled:cursor-default"
              >
                <span className="flex w-full items-center">
                  <span className={cn('h-px flex-1', i === 0 ? 'bg-transparent' : reached ? 'bg-mint/60' : 'bg-line')} />
                  <Icon className={cn('size-5 shrink-0', m.failed && reached ? 'text-danger' : reached ? 'text-mint' : m.active ? 'animate-spin text-primary' : 'text-muted')} aria-hidden />
                  <span className={cn('h-px flex-1', i === milestones.length - 1 ? 'bg-transparent' : reached ? 'bg-mint/60' : 'bg-line')} />
                </span>
                <span className={cn('text-xs font-semibold leading-tight group-enabled:group-hover:text-primary', !reached && 'text-muted')}>{m.label}</span>
                <span className="tg-mono text-[10px] text-muted">{m.t != null && reached ? formatDuration(m.t) : '—'}</span>
              </button>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
