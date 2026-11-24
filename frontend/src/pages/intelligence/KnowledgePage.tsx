import { useQuery } from '@tanstack/react-query'
import { terraApi } from '@/lib/terra'

export default function KnowledgePage() {
  const stats = useQuery({ queryKey: ['terra-stats'], queryFn: terraApi.stats })
  const graph = useQuery({
    queryKey: ['terra-graph', 'sohra'],
    queryFn: () => terraApi.graph('sohra'),
    retry: false,
  })
  const body = stats.data
  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div>
        <p className="text-xs uppercase tracking-wide text-muted">Intelligence</p>
        <h1 className="text-3xl font-extrabold">Knowledge explorer</h1>
        <p className="mt-1 text-sm text-muted">This is the travel entity graph. It is separate from the LangGraph agent workflow.</p>
      </div>
      {stats.isLoading && <p>Loading corpus stats…</p>}
      {body && (
        <section className="tg-card grid gap-3 p-4 sm:grid-cols-3 text-sm">
          <Stat label="Status" value={body.status} />
          <Stat label="Snapshot" value={body.snapshot_id || 'none'} />
          <Stat label="Embedding" value={body.embedding_kind || 'unavailable'} />
          <Stat label="Destinations" value={String(body.destinations ?? 0)} />
          <Stat label="Documents" value={String(body.documents ?? 0)} />
          <Stat label="Chunks" value={String(body.chunks ?? 0)} />
          <p className="sm:col-span-3 text-xs text-muted">{body.source_status_note}</p>
        </section>
      )}
      <section className="tg-card p-4">
        <h2 className="text-lg font-bold">Sohra neighborhood</h2>
        {graph.isError && <p className="mt-2 text-sm text-muted">No Sohra graph is in the active snapshot.</p>}
        {graph.data && (
          <>
            <p className="mt-1 text-xs text-muted">{graph.data.note}</p>
            <ul className="mt-3 space-y-2 text-sm">
              {graph.data.edges.map((edge, index) => (
                <li key={index} className="rounded-xl border border-line px-3 py-2">
                  {String(edge.predicate)} · {String(edge.method)}
                  {edge.evidence_chunk_id ? ` · evidence ${String(edge.evidence_chunk_id).slice(0, 8)}` : ' · no chunk evidence'}
                </li>
              ))}
            </ul>
            {!graph.data.edges.length && <p className="mt-2 text-sm">No edges stored.</p>}
          </>
        )}
      </section>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted">{label}</p>
      <p className="font-semibold">{value}</p>
    </div>
  )
}
