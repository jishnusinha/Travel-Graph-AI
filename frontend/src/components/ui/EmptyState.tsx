import type { ReactNode } from 'react'
import { AlertCircle, Inbox, RefreshCw, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ApiError } from '@/lib/api'

interface EmptyProps {
  icon?: LucideIcon
  title: string
  description?: ReactNode
  action?: ReactNode
  className?: string
}

export function EmptyState({ icon: Icon = Inbox, title, description, action, className }: EmptyProps) {
  return (
    <div className={cn('tg-card flex flex-col items-center gap-3 px-6 py-12 text-center', className)}>
      <span className="grid size-14 place-items-center rounded-2xl bg-primary-soft text-primary">
        <Icon className="size-7" aria-hidden />
      </span>
      <h3 className="text-lg font-bold">{title}</h3>
      {description && <p className="max-w-md text-sm text-muted">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

interface ErrorProps {
  error?: unknown
  title?: string
  onRetry?: () => void
  className?: string
}

export function ErrorState({ error, title = 'Something went wrong', onRetry, className }: ErrorProps) {
  const message =
    error instanceof ApiError
      ? error.status === 404
        ? 'We could not find that. It may have been removed or you may not have access.'
        : error.message
      : error instanceof Error
        ? error.message
        : 'Please try again.'
  return (
    <div role="alert" className={cn('tg-card flex flex-col items-center gap-3 px-6 py-10 text-center', className)}>
      <span className="grid size-14 place-items-center rounded-2xl bg-danger-soft text-danger">
        <AlertCircle className="size-7" aria-hidden />
      </span>
      <h3 className="text-lg font-bold">{title}</h3>
      <p className="max-w-md text-sm text-muted">{message}</p>
      {onRetry && (
        <button type="button" className="tg-btn tg-btn-secondary tg-btn-sm mt-1" onClick={onRetry}>
          <RefreshCw className="size-4" /> Try again
        </button>
      )}
    </div>
  )
}
