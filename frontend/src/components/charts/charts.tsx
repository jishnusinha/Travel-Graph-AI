import type { ReactNode } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export const CHART_COLORS = ['#818cf8', '#34d399', '#fbbf24', '#f472b6', '#38bdf8', '#a78bfa', '#2dd4bf', '#fb923c']

const axis = { stroke: 'var(--tg-muted)', fontSize: 11 }
const tooltipStyle = {
  background: 'var(--tg-surface)',
  border: '1px solid var(--tg-line)',
  borderRadius: 12,
  color: 'var(--tg-ink)',
  fontSize: 12,
  boxShadow: 'var(--tg-shadow)',
}

export interface Slice {
  name: string
  value: number
  color?: string
}

export function DonutChart({
  data,
  center,
  format = (v: number) => String(v),
  height = 220,
}: {
  data: Slice[]
  center?: ReactNode
  format?: (v: number) => string
  height?: number
}) {
  const total = data.reduce((s, d) => s + d.value, 0)
  return (
    <div className="flex flex-wrap items-center gap-4">
      <div className="relative mx-auto w-full max-w-[220px] flex-1" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius="62%"
              outerRadius="92%"
              paddingAngle={2}
              stroke="none"
              isAnimationActive={false}
            >
              {data.map((d, i) => (
                <Cell key={d.name} fill={d.color ?? CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} formatter={(v) => format(Number(v))} />
          </PieChart>
        </ResponsiveContainer>
        {center && <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">{center}</div>}
      </div>
      <ul className="min-w-[150px] flex-1 space-y-2 text-sm">
        {data.map((d, i) => (
          <li key={d.name} className="flex items-center gap-2">
            <span className="size-2.5 shrink-0 rounded-full" style={{ background: d.color ?? CHART_COLORS[i % CHART_COLORS.length] }} />
            <span className="min-w-0 flex-1 truncate">{d.name}</span>
            <span className="tg-mono text-xs font-semibold">{total ? `${((d.value / total) * 100).toFixed(1)}%` : '—'}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function TrendAreaChart({
  data,
  xKey,
  series,
  height = 240,
  yFormat,
}: {
  data: Record<string, unknown>[]
  xKey: string
  series: { key: string; label: string; color: string }[]
  height?: number
  yFormat?: (v: number) => string
}) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            {series.map((s) => (
              <linearGradient key={s.key} id={`grad-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={s.color} stopOpacity={0.45} />
                <stop offset="100%" stopColor={s.color} stopOpacity={0.02} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid stroke="var(--tg-line)" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey={xKey} {...axis} tickLine={false} axisLine={false} minTickGap={24} />
          <YAxis {...axis} tickLine={false} axisLine={false} width={56} tickFormatter={yFormat} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v) => (yFormat ? yFormat(Number(v)) : String(v))} />
          {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
          {series.map((s) => (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={s.color}
              strokeWidth={2}
              fill={`url(#grad-${s.key})`}
              stackId={series.length > 1 ? 'a' : undefined}
              isAnimationActive={false}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export function HorizontalBars({
  data,
  format,
  height,
}: {
  data: { name: string; value: number; color?: string }[]
  format?: (v: number) => string
  height?: number
}) {
  return (
    <div style={{ height: height ?? Math.max(160, data.length * 38) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--tg-line)" strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" {...axis} tickLine={false} axisLine={false} tickFormatter={format} />
          <YAxis type="category" dataKey="name" {...axis} tickLine={false} axisLine={false} width={120} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'var(--tg-primary-soft)' }} formatter={(v) => (format ? format(Number(v)) : String(v))} />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={d.name} fill={d.color ?? CHART_COLORS[i % CHART_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export interface WaterfallStep {
  name: string
  value: number
}

/** Cumulative waterfall: each agent floats on top of the running total; final bar is the total. */
export function WaterfallChart({
  steps,
  format,
  height = 260,
  totalLabel = 'Total',
}: {
  steps: WaterfallStep[]
  format: (v: number) => string
  height?: number
  totalLabel?: string
}) {
  let run = 0
  const rows = steps.map((s) => {
    const base = run
    run += s.value
    return { name: s.name, base, value: s.value, total: false }
  })
  rows.push({ name: totalLabel, base: 0, value: run, total: true })
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--tg-line)" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" {...axis} tickLine={false} axisLine={false} interval={0} tickFormatter={(v: string) => (v.length > 11 ? v.slice(0, 10) + '…' : v)} />
          <YAxis {...axis} tickLine={false} axisLine={false} width={60} tickFormatter={format} />
          <Tooltip
            contentStyle={tooltipStyle}
            cursor={{ fill: 'var(--tg-primary-soft)' }}
            formatter={(v, n) => (n === 'base' ? [null, null] : [format(Number(v)), 'Cost']) as never}
          />
          <Bar dataKey="base" stackId="w" fill="transparent" isAnimationActive={false} />
          <Bar dataKey="value" stackId="w" radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {rows.map((r) => (
              <Cell key={r.name} fill={r.total ? '#6366f1' : '#34d399'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function RadarCompare({
  data,
  series,
  height = 280,
}: {
  data: Record<string, number | string>[]
  series: { key: string; label: string; color: string }[]
  height?: number
}) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="60%">
          <PolarGrid stroke="var(--tg-line)" />
          <PolarAngleAxis dataKey="metric" tick={{ fill: 'var(--tg-muted)', fontSize: 10 }} />
          <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
          {series.map((s) => (
            <Radar key={s.key} name={s.label} dataKey={s.key} stroke={s.color} fill={s.color} fillOpacity={0.22} strokeWidth={2} isAnimationActive={false} />
          ))}
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Tooltip contentStyle={tooltipStyle} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ScoreBars({
  data,
  series,
  height = 260,
  yDomain,
}: {
  data: Record<string, number | string | null>[]
  series: { key: string; label: string; color: string }[]
  height?: number
  yDomain?: [number, number]
}) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--tg-line)" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" {...axis} tickLine={false} axisLine={false} />
          <YAxis {...axis} tickLine={false} axisLine={false} width={36} domain={yDomain} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'var(--tg-primary-soft)' }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {series.map((s) => (
            <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
