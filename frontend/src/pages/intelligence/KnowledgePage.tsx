import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { terraApi, type KnowledgeEdge, type KnowledgeEntity } from '@/lib/terra'

const TYPE_COLOR: Record<string, string> = {
  destination: '#818cf8',
  region: '#34d399',
  attraction: '#fbbf24',
}

const PREDICATES = [
  { id: '', label: 'All predicates' },
  { id: 'located_in', label: 'located_in' },
  { id: 'within_80km_straight_line', label: 'within_80km_straight_line' },
]

export default function KnowledgePage() {
  const [slug, setSlug] = useState('sohra')
  const [query, setQuery] = useState('')
  const [hops, setHops] = useState(1)
  const [predicate, setPredicate] = useState('')
  const [selectedNode, setSelectedNode] = useState<KnowledgeEntity | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<KnowledgeEdge | null>(null)

  const stats = useQuery({ queryKey: ['terra-stats'], queryFn: terraApi.stats })
  const destinations = useQuery({
    queryKey: ['terra-destinations', 'knowledge'],
    queryFn: () => terraApi.destinations({}),
  })
  const entities = useQuery({
    queryKey: ['terra-entities', query],
    queryFn: () => terraApi.entities(query.trim() ? { q: query.trim() } : undefined),
  })
  const graph = useQuery({
    queryKey: ['terra-graph', slug, hops, predicate],
    queryFn: () => terraApi.graph(slug, hops, predicate || undefined),
    retry: false,
    enabled: !!slug,
  })

  const body = stats.data
  const nodeById = useMemo(() => new Map((graph.data?.nodes ?? []).map((node) => [node.id, node])), [graph.data])
  const flowNodes = useMemo<Node[]>(() => layoutNodes(graph.data?.nodes ?? [], graph.data?.seed?.id), [graph.data])
  const flowEdges = useMemo<Edge[]>(
    () =>
      (graph.data?.edges ?? []).map((edge) => ({
        id: edge.id,
        source: edge.subject_id,
        target: edge.object_id,
        label: edge.predicate,
        markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
        style: {
          stroke: selectedEdge?.id === edge.id ? '#fbbf24' : 'rgba(129,140,248,0.55)',
          strokeWidth: selectedEdge?.id === edge.id ? 2.4 : 1.5,
        },
        labelStyle: { fill: 'var(--tg-muted)', fontSize: 10 },
        labelBgStyle: { fill: 'var(--tg-surface)' },
      })),
    [graph.data, selectedEdge],
  )

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div>
        <p className="text-xs uppercase tracking-wide text-muted">Intelligence</p>
        <h1 className="text-3xl font-extrabold">Knowledge explorer</h1>
        <p className="mt-1 text-sm text-muted">
          Travel entity graph from the active snapshot. This is not the LangGraph agent workflow.
        </p>
      </div>

      {stats.isLoading && <p>Loading corpus stats…</p>}
      {body && (
        <section className="tg-card grid gap-3 p-4 text-sm sm:grid-cols-3 lg:grid-cols-4">
          <Stat label="Status" value={body.status} />
          <Stat label="Snapshot" value={body.snapshot_id || 'none'} />
          <Stat label="Embedding" value={body.embedding_kind || 'unavailable'} />
          <Stat label="Destinations" value={String(body.destinations ?? 0)} />
          <Stat label="Documents" value={String(body.documents ?? 0)} />
          <Stat label="Chunks" value={String(body.chunks ?? 0)} />
          <Stat label="Entities" value={String(body.entities ?? 0)} />
          <Stat label="Relationships" value={String(body.relationships ?? 0)} />
          <Stat label="Images" value={String(body.images ?? 0)} />
          <div className="sm:col-span-3 lg:col-span-4">
            <p className="text-xs text-muted">Document licenses</p>
            <p className="font-semibold">
              {Object.entries(body.license_coverage ?? {}).map(([name, count]) => `${name}: ${count}`).join(' · ') || 'none'}
            </p>
            <p className="mt-2 text-xs text-muted">{body.source_status_note}</p>
          </div>
        </section>
      )}

      <section className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <div className="space-y-4">
          <div className="tg-card space-y-3 p-4">
            <label className="block text-sm font-semibold" htmlFor="knowledge-dest">
              Seed destination
            </label>
            <select
              id="knowledge-dest"
              className="tg-input"
              value={slug}
              onChange={(event) => {
                setSlug(event.target.value)
                setSelectedEdge(null)
                setSelectedNode(null)
              }}
            >
              {(destinations.data?.items ?? []).map((item) => (
                <option key={item.slug} value={item.slug}>
                  {item.name}
                </option>
              ))}
            </select>
            <label className="block text-sm font-semibold" htmlFor="knowledge-hops">
              Hops
            </label>
            <select id="knowledge-hops" className="tg-input" value={hops} onChange={(event) => setHops(Number(event.target.value))}>
              <option value={1}>1</option>
              <option value={2}>2</option>
            </select>
            <label className="block text-sm font-semibold" htmlFor="knowledge-predicate">
              Predicate filter
            </label>
            <select id="knowledge-predicate" className="tg-input" value={predicate} onChange={(event) => setPredicate(event.target.value)}>
              {PREDICATES.map((item) => (
                <option key={item.id || 'all'} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>

          <div className="tg-card space-y-3 p-4">
            <label className="block text-sm font-semibold" htmlFor="entity-search">
              Entity search
            </label>
            <input
              id="entity-search"
              className="tg-input"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Nohkalikai, Meghalaya…"
            />
            <ul className="max-h-64 space-y-1 overflow-auto text-sm" aria-label="Entity results">
              {(entities.data?.items ?? []).slice(0, 30).map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className="w-full rounded-lg px-2 py-1.5 text-left hover:bg-primary-soft"
                    onClick={() => {
                      setSelectedNode(item)
                      setSelectedEdge(null)
                      const destKey = item.external_key?.startsWith('destination:')
                        ? item.external_key.slice('destination:'.length)
                        : null
                      if (destKey) setSlug(destKey)
                    }}
                  >
                    <span className="font-semibold">{item.label}</span>
                    <span className="mt-0.5 block text-xs text-muted">{item.entity_type}</span>
                  </button>
                </li>
              ))}
              {!entities.isLoading && !(entities.data?.items?.length) && (
                <li className="px-2 text-xs text-muted">No entities matched.</li>
              )}
            </ul>
          </div>
        </div>

        <div className="space-y-4">
          <div className="tg-card overflow-hidden">
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <div>
                <h2 className="text-lg font-bold">Bounded subgraph</h2>
                <p className="text-xs text-muted">{graph.data?.note}</p>
              </div>
              {graph.data?.seed && (
                <Link className="text-sm font-semibold text-primary-strong underline" to={`/destinations/${graph.data.seed.slug}`}>
                  Open {graph.data.seed.name}
                </Link>
              )}
            </div>
            {graph.isError && <p className="p-4 text-sm text-muted">No graph is available for this destination.</p>}
            {graph.isLoading && <p className="p-4 text-sm text-muted">Loading subgraph…</p>}
            {graph.data && (
              <div className="h-[420px]">
                <ReactFlowProvider>
                  <ReactFlow
                    nodes={flowNodes}
                    edges={flowEdges}
                    fitView
                    minZoom={0.35}
                    maxZoom={1.6}
                    proOptions={{ hideAttribution: true }}
                    onNodeClick={(_, node) => {
                      setSelectedNode(nodeById.get(node.id) ?? null)
                      setSelectedEdge(null)
                    }}
                    onEdgeClick={(_, edge) => {
                      const found = (graph.data?.edges ?? []).find((item) => item.id === edge.id) ?? null
                      setSelectedEdge(found)
                      setSelectedNode(null)
                    }}
                  >
                    <Background variant={BackgroundVariant.Dots} gap={18} size={1} />
                    <Controls showInteractive={false} />
                    <MiniMap pannable zoomable />
                  </ReactFlow>
                </ReactFlowProvider>
              </div>
            )}
          </div>

          <div className="tg-card p-4">
            <h2 className="text-lg font-bold">Inspector</h2>
            {!selectedNode && !selectedEdge && (
              <p className="mt-2 text-sm text-muted">Select a node or edge. A list fallback is below the canvas.</p>
            )}
            {selectedNode && (
              <div className="mt-2 space-y-1 text-sm">
                <p className="font-semibold">{selectedNode.label}</p>
                <p className="text-muted">type {selectedNode.entity_type}</p>
                <p className="text-xs text-muted">{selectedNode.external_key}</p>
              </div>
            )}
            {selectedEdge && (
              <div className="mt-2 space-y-2 text-sm">
                <p className="font-semibold">{selectedEdge.predicate}</p>
                <p className="text-muted">
                  {nodeById.get(selectedEdge.subject_id)?.label || selectedEdge.subject_id}
                  {' → '}
                  {nodeById.get(selectedEdge.object_id)?.label || selectedEdge.object_id}
                </p>
                <p className="text-xs text-muted">
                  method {selectedEdge.method || 'unknown'}
                  {selectedEdge.hop != null ? ` · hop ${selectedEdge.hop}` : ''}
                </p>
                {selectedEdge.evidence?.excerpt ? (
                  <blockquote className="rounded-xl border border-line bg-surface-2 p-3 text-sm leading-relaxed">
                    {selectedEdge.evidence.excerpt}
                    {selectedEdge.evidence.section_path && (
                      <span className="mt-2 block text-xs text-muted">{selectedEdge.evidence.section_path}</span>
                    )}
                  </blockquote>
                ) : (
                  <p className="text-xs text-muted">No chunk evidence on this edge.</p>
                )}
              </div>
            )}
          </div>

          <div className="tg-card p-4">
            <h2 className="text-lg font-bold">Accessible edge list</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {(graph.data?.edges ?? []).map((edge) => (
                <li key={edge.id}>
                  <button
                    type="button"
                    className="w-full rounded-xl border border-line px-3 py-2 text-left hover:bg-primary-soft/40"
                    onClick={() => {
                      setSelectedEdge(edge)
                      setSelectedNode(null)
                    }}
                  >
                    <span className="font-semibold">{edge.predicate}</span>
                    <span className="mt-1 block text-xs text-muted">
                      {nodeById.get(edge.subject_id)?.label} → {nodeById.get(edge.object_id)?.label}
                      {edge.method ? ` · ${edge.method}` : ''}
                      {edge.evidence_chunk_id ? ' · has evidence' : ' · no chunk evidence'}
                    </span>
                  </button>
                </li>
              ))}
              {graph.data && !graph.data.edges.length && <li className="text-sm text-muted">No edges stored for this seed.</li>}
            </ul>
          </div>
        </div>
      </section>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted">{label}</p>
      <p className="font-semibold break-all">{value}</p>
    </div>
  )
}

function layoutNodes(nodes: KnowledgeEntity[], seedId?: string): Node[] {
  const destinations = nodes.filter((node) => node.entity_type === 'destination')
  const regions = nodes.filter((node) => node.entity_type === 'region')
  const attractions = nodes.filter((node) => node.entity_type === 'attraction')
  const other = nodes.filter((node) => !['destination', 'region', 'attraction'].includes(node.entity_type))
  const place = (list: KnowledgeEntity[], y: number, gap = 180) =>
    list.map((node, index) => ({
      id: node.id,
      position: { x: index * gap, y },
      data: { label: node.label },
      style: {
        border: `1px solid ${TYPE_COLOR[node.entity_type] || '#94a3b8'}`,
        background: node.id === seedId ? 'rgba(129,140,248,0.18)' : 'var(--tg-surface)',
        color: 'var(--tg-ink)',
        borderRadius: 12,
        padding: 8,
        fontSize: 12,
        width: 150,
      },
    }))
  return [...place(regions, 0), ...place(destinations, 120), ...place(attractions, 240, 160), ...place(other, 360)]
}
