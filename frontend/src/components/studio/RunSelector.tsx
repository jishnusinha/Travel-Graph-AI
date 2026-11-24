import { PlayCircle } from 'lucide-react'
import { useRuns } from '@/hooks/queries'
import type { RunListItem } from '@/lib/types'

interface Props {
  value: string | undefined
  onChange: (run: RunListItem) => void
  /** make sure the currently open run appears even if it is not in the first page */
  currentFallback?: { id: string; public_id: string } | null
}

export function RunSelector({ value, onChange, currentFallback }: Props) {
  const runs = useRuns({ page_size: 100 })
  const items = runs.data?.items ?? []
  const current = items.find((r) => r.public_id === value || r.id === value)
  return (
    <label className="relative inline-flex items-center">
      <span className="sr-only">Select run</span>
      <PlayCircle className="pointer-events-none absolute left-3 size-4 text-primary" aria-hidden />
      <select
        value={current?.public_id ?? value ?? ''}
        onChange={(e) => {
          const r = items.find((x) => x.public_id === e.target.value)
          if (r) onChange(r)
        }}
        className="tg-input h-10 w-auto min-w-[190px] max-w-[300px] rounded-xl bg-surface-2 pl-9 pr-8 text-sm font-semibold"
        disabled={runs.isPending}
      >
        {!current && value && <option value={value}>Run #{currentFallback?.public_id ?? value}</option>}
        {items.map((r) => (
          <option key={r.id} value={r.public_id}>
            Run #{r.public_id}{r.trip_title ? ` · ${r.trip_title}` : ''}
          </option>
        ))}
      </select>
    </label>
  )
}
