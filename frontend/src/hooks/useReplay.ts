import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { AgentEvent } from '@/lib/types'
import { relativeTimes } from '@/lib/agents'

export const SPEEDS = [0.5, 1, 2, 4] as const

/** Replay timing: real offsets from stored timestamps; synthetic spacing when a run was effectively instant. */
export function replayTimes(events: AgentEvent[]): { times: number[]; duration: number } {
  const rel = relativeTimes(events)
  const max = rel.length ? rel[rel.length - 1] : 0
  if (events.length > 1 && max < 1500) {
    const times = events.map((_, i) => i * 350)
    return { times, duration: times[times.length - 1] || 1000 }
  }
  return { times: rel, duration: Math.max(max, 1000) }
}

/** Index of the last event whose time <= t (or -1). */
export function cursorAt(times: number[], t: number): number {
  let lo = 0
  let hi = times.length - 1
  let ans = -1
  while (lo <= hi) {
    const mid = (lo + hi) >> 1
    if (times[mid] <= t) {
      ans = mid
      lo = mid + 1
    } else hi = mid - 1
  }
  return ans
}

/**
 * Client-side replay of persisted events (no network, no AI calls).
 * play / pause / seek / speed / step are all derived from the stored event list.
 */
export function useReplay(events: AgentEvent[]) {
  const { times, duration } = useMemo(() => replayTimes(events), [events])
  const [t, setT] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState<number>(1)
  const raf = useRef<number | null>(null)
  const last = useRef(0)

  // restart when the underlying run changes
  useEffect(() => {
    setT(0)
    setPlaying(false)
  }, [events[0]?.run_id])

  useEffect(() => {
    if (!playing) return
    last.current = performance.now()
    const tick = (now: number) => {
      const dt = now - last.current
      last.current = now
      setT((cur) => {
        const next = cur + dt * speed
        if (next >= duration) {
          setPlaying(false)
          return duration
        }
        return next
      })
      raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current)
    }
  }, [playing, speed, duration])

  const cursor = cursorAt(times, t)
  const atEnd = t >= duration

  const play = useCallback(() => {
    setT((cur) => (cur >= duration ? 0 : cur))
    setPlaying(true)
  }, [duration])
  const pause = useCallback(() => setPlaying(false), [])
  const toggle = useCallback(() => (playing ? pause() : play()), [playing, play, pause])
  const seek = useCallback((ms: number) => setT(Math.min(duration, Math.max(0, ms))), [duration])
  const seekIndex = useCallback((i: number) => {
    setPlaying(false)
    setT(times[Math.min(times.length - 1, Math.max(0, i))] ?? 0)
  }, [times])
  const stepNext = useCallback(() => {
    setPlaying(false)
    const i = cursorAt(times, t)
    const next = Math.min(times.length - 1, i + 1)
    setT(times[next] ?? duration)
  }, [times, t, duration])
  const stepPrev = useCallback(() => {
    setPlaying(false)
    const i = cursorAt(times, t)
    if (i < 0) return setT(0)
    // between events: snap back to the current event; on an event: go to the previous one
    const target = times[i] < t ? i : i - 1
    setT(target < 0 ? 0 : times[target])
  }, [times, t])
  const restart = useCallback(() => {
    setPlaying(false)
    setT(0)
  }, [])

  const visibleEvents = useMemo(() => events.slice(0, cursor + 1), [events, cursor])

  return { t, duration, times, playing, speed, setSpeed, cursor, atEnd, play, pause, toggle, seek, seekIndex, stepNext, stepPrev, restart, visibleEvents }
}
