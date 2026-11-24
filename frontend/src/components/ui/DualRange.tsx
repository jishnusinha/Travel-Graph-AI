import { cn } from '@/lib/utils'

interface Props {
  min: number
  max: number
  step?: number
  low: number
  high: number
  onChange: (low: number, high: number) => void
  className?: string
  labelLow?: string
  labelHigh?: string
}

/** Two-thumb range slider built from two native range inputs (keyboard + screen-reader friendly). */
export function DualRange({ min, max, step = 1000, low, high, onChange, className, labelLow = 'Minimum', labelHigh = 'Maximum' }: Props) {
  const pct = (v: number) => ((v - min) / (max - min)) * 100
  const thumb =
    'pointer-events-none absolute inset-0 h-6 w-full appearance-none bg-transparent [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:size-5 [&::-webkit-slider-thumb]:cursor-grab [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-primary-strong [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:shadow [&::-moz-range-thumb]:pointer-events-auto [&::-moz-range-thumb]:size-5 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-primary-strong [&::-moz-range-thumb]:bg-white'
  return (
    <div className={cn('relative h-6', className)}>
      <div className="absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-line" />
      <div
        className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-primary-strong"
        style={{ left: `${pct(low)}%`, width: `${pct(high) - pct(low)}%` }}
      />
      <input
        type="range"
        aria-label={labelLow}
        min={min}
        max={max}
        step={step}
        value={low}
        onChange={(e) => onChange(Math.min(Number(e.target.value), high - step), high)}
        className={thumb}
      />
      <input
        type="range"
        aria-label={labelHigh}
        min={min}
        max={max}
        step={step}
        value={high}
        onChange={(e) => onChange(low, Math.max(Number(e.target.value), low + step))}
        className={thumb}
      />
    </div>
  )
}
