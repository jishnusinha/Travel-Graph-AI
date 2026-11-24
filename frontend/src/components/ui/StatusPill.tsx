import { CheckCircle2, CircleDashed, FileText, Loader2, XCircle, HelpCircle, AlertTriangle, MinusCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

type Tone = 'mint' | 'primary' | 'warn' | 'danger' | 'muted'

const TONE: Record<Tone, string> = {
  mint: 'bg-mint-soft text-mint border-mint/30',
  primary: 'bg-primary-soft text-primary-ink border-primary/30',
  warn: 'bg-warn-soft text-warn border-warn/30',
  danger: 'bg-danger-soft text-danger border-danger/30',
  muted: 'bg-surface-2 text-muted border-line',
}

const MAP: Record<string, { label: string; tone: Tone; icon: typeof CheckCircle2; spin?: boolean }> = {
  completed: { label: 'Completed', tone: 'mint', icon: CheckCircle2 },
  succeeded: { label: 'Succeeded', tone: 'mint', icon: CheckCircle2 },
  in_progress: { label: 'In Progress', tone: 'primary', icon: Loader2, spin: true },
  running: { label: 'Running', tone: 'primary', icon: Loader2, spin: true },
  pending: { label: 'Pending', tone: 'muted', icon: CircleDashed },
  draft: { label: 'Draft', tone: 'warn', icon: FileText },
  failed: { label: 'Failed', tone: 'danger', icon: XCircle },
  skipped: { label: 'Skipped', tone: 'muted', icon: MinusCircle },
  warning: { label: 'Warning', tone: 'warn', icon: AlertTriangle },
  needs_clarification: { label: 'Needs clarification', tone: 'warn', icon: HelpCircle },
  replaying: { label: 'Replaying', tone: 'primary', icon: Loader2, spin: true },
}

interface Props {
  status: string
  label?: string
  className?: string
  size?: 'sm' | 'md'
}

export function StatusPill({ status, label, className, size = 'md' }: Props) {
  const cfg = MAP[status] ?? { label: status, tone: 'muted' as Tone, icon: CircleDashed }
  const Icon = cfg.icon
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border font-semibold',
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs',
        TONE[cfg.tone],
        className,
      )}
    >
      <Icon className={cn(size === 'sm' ? 'size-3' : 'size-3.5', cfg.spin && 'animate-spin')} aria-hidden />
      {label ?? cfg.label}
    </span>
  )
}

export function ProvenanceBadge({ value, className }: { value: string | undefined | null; className?: string }) {
  if (!value) return null
  const label =
    value === 'demo' ? 'Demo estimate' : value === 'estimated' ? 'Estimated' : value === 'mixed' ? 'Mixed sources' : value
  return (
    <span
      title="Where these numbers come from. Seeded demo charges are illustrative, not an invoice."
      className={cn(
        'inline-flex items-center rounded-full border border-line bg-surface-2 px-2 py-0.5 text-[11px] font-semibold text-muted',
        className,
      )}
    >
      {label}
    </span>
  )
}
