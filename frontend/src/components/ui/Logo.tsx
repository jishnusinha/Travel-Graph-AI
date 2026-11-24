import { cn } from '@/lib/utils'

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={cn('size-8', className)} aria-hidden>
      <defs>
        <linearGradient id="tg-logo" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#818cf8" />
          <stop offset="1" stopColor="#4f46e5" />
        </linearGradient>
      </defs>
      <path d="M4 17.5 36 4 25.5 36 19 22.5 4 17.5Z" fill="url(#tg-logo)" />
      <path d="M19 22.5 36 4 21.5 24.5Z" fill="#fff" opacity=".28" />
      <path d="M32 2.5l1 2.6 2.6 1-2.6 1-1 2.6-1-2.6-2.6-1 2.6-1Z" fill="#f59e0b" />
    </svg>
  )
}

export function Logo({ className, compact }: { className?: string; compact?: boolean }) {
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <LogoMark />
      {!compact && (
        <span className="text-[19px] font-extrabold tracking-tight">
          TravelGraph <span className="text-primary">AI</span>
        </span>
      )}
    </span>
  )
}
