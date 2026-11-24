import { useEffect, useMemo, useState } from 'react'
import {
  Background,
  BackgroundVariant,
  MarkerType,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Maximize2, Minus, Plus } from 'lucide-react'
import { AGENT_BY_ID, AGENTS, FALLBACK_EDGES } from '@/lib/agents'
import type { GraphEdge, GraphNode } from '@/lib/types'
import { AgentNode, type AgentFlowNode } from './AgentNode'

const nodeTypes = { agent: AgentNode }

interface Props {
  nodes: GraphNode[]
  edges?: GraphEdge[]
  selected: string | null
  onSelect: (id: string | null) => void
  replaying?: boolean
  className?: string
}

function Inner({ nodes, edges, selected, onSelect, replaying }: Props) {
  const rf = useReactFlow()
  const [zoom, setZoom] = useState(100)
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes])

  const flowNodes = useMemo<AgentFlowNode[]>(
    () =>
      AGENTS.map((a) => {
        const n = byId.get(a.id)
        return {
          id: a.id,
          type: 'agent',
          position: { x: a.x, y: a.y },
          draggable: false,
          selectable: true,
          data: {
            agentId: a.id,
            status: n?.status ?? 'pending',
            durationMs: n?.duration_ms ?? null,
            invocations: n?.invocations ?? 0,
            costUsd: n?.cost_usd ?? null,
            selected: selected === a.id,
            replaying,
          },
        }
      }),
    [byId, selected, replaying],
  )

  const flowEdges = useMemo<Edge[]>(() => {
    const src = edges && edges.length ? edges : FALLBACK_EDGES
    return src
      .filter((e) => AGENT_BY_ID[e.source] && AGENT_BY_ID[e.target])
      .map((e) => {
        const s = byId.get(e.source)
        const t = byId.get(e.target)
        const isLoop = e.source === 'validator' && e.target === 'itinerary'
        const retried = (byId.get('itinerary')?.invocations ?? 0) > 1
        const active = !isLoop && s?.status === 'completed' && t?.status === 'running'
        const done = !isLoop && s?.status === 'completed' && (t?.status === 'completed' || t?.status === 'running')
        const stroke = isLoop ? (retried ? '#fbbf24' : 'rgba(148,163,184,0.35)') : done ? '#34d399' : 'rgba(129,140,248,0.45)'
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          ...(isLoop ? { sourceHandle: 'loop-out', targetHandle: 'loop-in' } : { sourceHandle: 's', targetHandle: 't' }),
          type: 'smoothstep',
          animated: false,
          className: active ? 'tg-edge-active' : undefined,
          label: isLoop ? 'retry' : undefined,
          labelStyle: { fill: 'var(--tg-muted)', fontSize: 10 },
          labelBgStyle: { fill: 'var(--tg-surface)' },
          style: { stroke, strokeWidth: 2, strokeDasharray: isLoop ? '5 5' : undefined },
          markerEnd: { type: MarkerType.ArrowClosed, color: stroke, width: 16, height: 16 },
        } satisfies Edge
      })
  }, [edges, byId])

  useEffect(() => {
    const t = window.setTimeout(() => rf.fitView({ padding: 0.2, duration: 200 }), 50)
    return () => window.clearTimeout(t)
  }, [rf])

  return (
    <>
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, n) => onSelect(n.id)}
        onPaneClick={() => onSelect(null)}
        onMove={(_, vp) => setZoom(Math.round(vp.zoom * 100))}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={1.6}
        proOptions={{ hideAttribution: true }}
        aria-label="Agent execution graph"
      >
        <Background variant={BackgroundVariant.Dots} gap={22} size={1.2} color="var(--tg-grid-dot)" />
      </ReactFlow>
      <div className="absolute right-3 top-3 z-10 flex items-center gap-1 rounded-xl border border-line bg-surface/90 p-1 backdrop-blur" role="toolbar" aria-label="Graph zoom">
        <button type="button" aria-label="Zoom out" className="tg-btn tg-btn-ghost tg-btn-sm !px-2" onClick={() => rf.zoomOut({ duration: 150 })}><Minus className="size-4" /></button>
        <span className="w-12 text-center text-xs font-semibold" aria-live="polite">{zoom}%</span>
        <button type="button" aria-label="Zoom in" className="tg-btn tg-btn-ghost tg-btn-sm !px-2" onClick={() => rf.zoomIn({ duration: 150 })}><Plus className="size-4" /></button>
        <button type="button" aria-label="Fit view" className="tg-btn tg-btn-ghost tg-btn-sm !px-2" onClick={() => rf.fitView({ padding: 0.2, duration: 200 })}><Maximize2 className="size-4" /></button>
      </div>
    </>
  )
}

export function StudioGraph(props: Props) {
  return (
    <div className={props.className ?? 'relative h-full min-h-[420px] w-full'}>
      <ReactFlowProvider>
        <Inner {...props} />
      </ReactFlowProvider>
    </div>
  )
}
