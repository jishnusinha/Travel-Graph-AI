import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

const inr = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

/** Trip budgets are always INR. */
export function formatINR(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  return inr.format(value)
}

/** AI costs are always USD; small amounts need more precision. */
export function formatUSD(value: number | null | undefined, opts?: { max?: number }): string {
  if (value == null || Number.isNaN(value)) return '—'
  const abs = Math.abs(value)
  const digits = opts?.max ?? (abs === 0 ? 2 : abs < 0.01 ? 5 : abs < 1 ? 4 : 2)
  return `$${value.toFixed(digits)}`
}

export function formatNumber(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  return new Intl.NumberFormat('en-IN').format(value)
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null || Number.isNaN(ms)) return '—'
  if (ms < 1000) return `${Math.round(ms)}ms`
  const s = ms / 1000
  if (s < 60) return `${s.toFixed(1)}s`
  const m = Math.floor(s / 60)
  return `${m}m ${Math.round(s - m * 60)}s`
}

export function formatPct(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

export function formatDate(value: string | Date | null | undefined, withTime = false): string {
  if (!value) return '—'
  const d = typeof value === 'string' ? new Date(value) : value
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {}),
  })
}

export function formatDateRange(start?: string | null, end?: string | null): string {
  if (!start && !end) return 'Dates flexible'
  const fmt = (s: string) =>
    new Date(s + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
  if (start && end) return `${fmt(start)} – ${fmt(end)}`
  return fmt((start ?? end) as string)
}

export function titleCase(s: string): string {
  return s
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export function clamp(n: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, n))
}

/** Trigger a browser download for in-memory text. */
export function downloadText(filename: string, text: string, mime = 'text/plain'): void {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
