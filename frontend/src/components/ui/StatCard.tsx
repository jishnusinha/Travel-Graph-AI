import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Skeleton } from './Skeleton'

const TONES = {
  primary: 'bg-primary-soft text-primary',
  mint: 'bg-mint-soft text-mint',
  warn: 'bg-warn-soft text-warn',
  danger: 'bg-danger-soft text-danger',
} as const

interface Props {
  icon: LucideIcon
  label: string
  value: ReactNode
  hint?: ReactNode
  tone?: keyof typeof TONES
  loading?: boolean
  className?: string
  active?: boolean
}

/** Light-theme stat tile (dashboard / trips). */
export function StatCard({ icon: Icon, label, value, hint, tone = 'primary', loading, className, active }: Props) {
  return (
    <div className={cn('tg-card flex items-center gap-3 p-4', active && 'ring-2 ring-primary/50', className)}>
      <span className={cn('grid size-11 shrink-0 place-items-center rounded-xl', TONES[tone])}>
        <Icon className="size-5" aria-hidden />
      </span>
      <div className="min-w-0">
        <p className="truncate text-xs font-medium text-muted">{label}</p>
        {loading ? (
          <Skeleton className="mt-1 h-7 w-16" />
        ) : (
          <p className="truncate text-2xl font-bold leading-tight">{value}</p>
        )}
        {hint && !loading && <p className="truncate text-[11px] text-muted">{hint}</p>}
      </div>
    </div>
  )
}

interface MetricProps {
  icon?: LucideIcon
  label: string
  value: ReactNode
  sub?: ReactNode
  delta?: { text: string; good?: boolean | null }
  highlight?: boolean
  className?: string
}

/** Dark-theme metric tile (evaluation / cost). */
export function MetricCard({ icon: Icon, label, value, sub, delta, highlight, className }: MetricProps) {
  return (
    <div
      className={cn(
        'tg-card flex min-w-0 flex-col gap-1 p-3.5',
        highlight && 'ring-1 ring-primary shadow-[0_0_28px_rgba(99,102,241,0.35)]',
        className,
      )}
    >
      <div className="flex items-center gap-2 text-xs font-medium text-muted">
        {Icon && (
          <span className="grid size-7 place-items-center rounded-lg bg-primary-soft text-primary">
            <Icon className="size-4" aria-hidden />
          </span>
        )}
        <span className="truncate">{label}</span>
      </div>
      <div className="truncate text-2xl font-bold leading-tight">{value}</div>
      {sub && <div className="truncate text-[11px] text-muted">{sub}</div>}
      {delta && (
        <div
          className={cn(
            'w-fit rounded-md px-1.5 py-0.5 text-[11px] font-semibold',
            delta.good == null ? 'bg-surface-2 text-muted' : delta.good ? 'bg-mint-soft text-mint' : 'bg-danger-soft text-danger',
          )}
        >
          {delta.text}
        </div>
      )}
    </div>
  )
}
