import { memo } from 'react'
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { Clock, RefreshCw } from 'lucide-react'
import { AGENT_BY_ID } from '@/lib/agents'
import type { NodeStatus } from '@/lib/types'
import { cn, formatDuration, formatUSD } from '@/lib/utils'
import { StatusPill } from '@/components/ui/StatusPill'

export interface AgentNodeData extends Record<string, unknown> {
  agentId: string
  status: NodeStatus
  durationMs: number | null
  invocations: number
  costUsd: number | null
  selected: boolean
  /** replay: show "Replaying…" for the running node */
  replaying?: boolean
}

export type AgentFlowNode = Node<AgentNodeData, 'agent'>

const BORDER: Record<NodeStatus, string> = {
  pending: 'border-line opacity-70',
  running: 'border-primary shadow-[0_0_28px_rgba(129,140,248,0.55)] tg-node-running',
  completed: 'border-mint/70 shadow-[0_0_18px_rgba(52,211,153,0.22)]',
  warning: 'border-warn/70',
  failed: 'border-danger shadow-[0_0_18px_rgba(248,113,113,0.3)]',
  skipped: 'border-dashed border-line opacity-50',
}

function AgentNodeImpl({ data }: NodeProps<AgentFlowNode>) {
  const meta = AGENT_BY_ID[data.agentId]
  const Icon = meta.icon
  const pillStatus = data.replaying && data.status === 'running' ? 'replaying' : data.status
  return (
    <div
      role="button"
      aria-label={`${meta.name}: ${data.status}`}
      className={cn(
        'w-[236px] rounded-2xl border-2 bg-surface-2/95 p-3 backdrop-blur transition-all',
        BORDER[data.status],
        data.selected && 'ring-2 ring-primary ring-offset-2 ring-offset-canvas',
      )}
    >
      <Handle id="t" type="target" position={Position.Top} className="!size-2 !border-0 !bg-primary" />
      <Handle id="s" type="source" position={Position.Bottom} className="!size-2 !border-0 !bg-primary" />
      <Handle id="loop-out" type="source" position={Position.Right} className="!size-1.5 !border-0 !bg-transparent" />
      <Handle id="loop-in" type="target" position={Position.Right} className="!size-1.5 !border-0 !bg-transparent" />
      <div className="flex items-center gap-2.5">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl" style={{ background: `${meta.color}26`, color: meta.color }}>
          <Icon className="size-5" aria-hidden />
        </span>
        <div className="min-w-0">
          <p className="truncate text-[13px] font-bold leading-tight">{meta.name}</p>
          <p className="truncate text-[11px] text-muted">{meta.subtitle}</p>
        </div>
      </div>
      <div className="mt-2.5 flex items-center justify-between gap-2">
        <StatusPill status={pillStatus} size="sm" />
        <span className="flex items-center gap-1 text-[11px] text-muted">
          <Clock className="size-3" aria-hidden />
          {data.durationMs != null ? formatDuration(data.durationMs) : '—'}
        </span>
      </div>
      {(data.invocations > 1 || data.costUsd != null) && (
        <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted">
          {data.invocations > 1 ? (
            <span className="flex items-center gap-1 text-warn"><RefreshCw className="size-3" /> {data.invocations} attempts</span>
          ) : <span />}
          {data.costUsd != null && <span className="tg-mono">{formatUSD(data.costUsd)}</span>}
        </div>
      )}
    </div>
  )
}

export const AgentNode = memo(AgentNodeImpl)
