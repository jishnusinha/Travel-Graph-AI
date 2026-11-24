import { Pause, Play, SkipBack, SkipForward, RotateCcw } from 'lucide-react'
import { SPEEDS } from '@/hooks/useReplay'
import { cn, formatDuration } from '@/lib/utils'

interface Props {
  playing: boolean
  speed: number
  t: number
  duration: number
  atEnd: boolean
  disabled?: boolean
  onToggle: () => void
  onStepPrev: () => void
  onStepNext: () => void
  onRestart: () => void
  onSpeed: (s: number) => void
}

export function ReplayToolbar({ playing, speed, t, duration, atEnd, disabled, onToggle, onStepPrev, onStepNext, onRestart, onSpeed }: Props) {
  const btn = 'grid size-10 place-items-center rounded-xl border border-line bg-surface-2 text-ink transition hover:border-primary disabled:opacity-40'
  return (
    <div role="toolbar" aria-label="Replay controls" className="flex flex-wrap items-center gap-2">
      <button type="button" className={btn} aria-label="Restart" onClick={onRestart} disabled={disabled}><RotateCcw className="size-4" /></button>
      <button type="button" className={btn} aria-label="Previous event" onClick={onStepPrev} disabled={disabled}><SkipBack className="size-4" /></button>
      <button
        type="button"
        aria-label={playing ? 'Pause replay' : atEnd ? 'Replay from start' : 'Play replay'}
        onClick={onToggle}
        disabled={disabled}
        className={cn(btn, 'size-11 border-primary bg-primary-strong text-white shadow-[0_0_20px_rgba(99,102,241,0.5)] hover:bg-primary-strong')}
      >
        {playing ? <Pause className="size-5" /> : <Play className="size-5" />}
      </button>
      <button type="button" className={btn} aria-label="Next event" onClick={onStepNext} disabled={disabled}><SkipForward className="size-4" /></button>
      <label className="ml-1 flex items-center gap-2 text-xs text-muted">
        <span className="sr-only sm:not-sr-only">Speed</span>
        <select aria-label="Playback speed" value={speed} onChange={(e) => onSpeed(Number(e.target.value))} className="tg-input h-10 w-auto rounded-xl bg-surface-2 pr-7 text-sm font-semibold">
          {SPEEDS.map((s) => <option key={s} value={s}>{s}x</option>)}
        </select>
      </label>
      <span className="tg-mono ml-1 text-xs text-muted" aria-live="off">{formatDuration(t)} / {formatDuration(duration)}</span>
    </div>
  )
}
