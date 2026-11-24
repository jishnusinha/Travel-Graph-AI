import { useState, type FormEvent } from 'react'
import { ApiError } from '@/lib/api'
import { terraApi } from '@/lib/terra'

const STRATEGIES = ['keyword', 'dense', 'hybrid', 'hybrid_rerank', 'graph_hybrid']

export default function RetrievalPage() {
  const [query, setQuery] = useState('quiet hills and waterfalls')
  const [strategy, setStrategy] = useState('hybrid_rerank')
  const [trace, setTrace] = useState<Record<string, unknown> | null>(null)
  const [bench, setBench] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  const run = async (event: FormEvent) => {
    event.preventDefault()
    try {
      setTrace(await terraApi.retrieval(query, strategy))
      setError(null)
    } catch (err) {
      setTrace(null)
      setError(err instanceof ApiError ? err.message : 'Retrieval failed')
    }
  }

  const evidence = (trace?.evidence as Array<Record<string, unknown>> | undefined) ?? []
  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div>
        <p className="text-xs uppercase tracking-wide text-muted">Intelligence</p>
        <h1 className="text-3xl font-extrabold">Retrieval playground</h1>
        <p className="mt-1 text-sm text-muted">Scores and timings come from this request. A missing model is reported, not replaced with fake similarity.</p>
      </div>
      <form onSubmit={run} className="tg-card grid gap-3 p-4 md:grid-cols-[1fr_220px_auto]">
        <input value={query} onChange={(e) => setQuery(e.target.value)} className="rounded-xl border border-line bg-surface-2 px-3 py-2" aria-label="Query" />
        <select value={strategy} onChange={(e) => setStrategy(e.target.value)} className="rounded-xl border border-line bg-surface-2 px-3 py-2" aria-label="Strategy">
          {STRATEGIES.map((item) => <option key={item}>{item}</option>)}
        </select>
        <button className="tg-btn tg-btn-primary" type="submit">Run</button>
      </form>
      {error && <p role="alert" className="text-sm">{error}</p>}
      {trace && (
        <section className="tg-card space-y-2 p-4 text-sm">
          <p>Applied strategy: <strong>{String(trace.strategy_applied)}</strong></p>
          <p>Requested: {String(trace.strategy_requested)} · embedding {String(trace.embedding_kind)} · {String(trace.embedding_model || 'none')}</p>
          <p>Warnings: {(trace.warnings as string[] | undefined)?.join(', ') || 'none'}</p>
          <p>Timings ms: {JSON.stringify(trace.timings_ms)}</p>
          <p className="text-xs text-muted">Run {String(trace.retrieval_run_id)}</p>
          <ol className="space-y-2">
            {evidence.map((item) => (
              <li key={String(item.chunk_id)} className="rounded-xl border border-line p-3">
                <p className="font-semibold">{String(item.name)} · {String(item.title)}</p>
                <p className="text-xs text-muted">{String(item.license_name)} · {String(item.source_type)}</p>
                <p className="mt-1">{String(item.excerpt)}</p>
              </li>
            ))}
          </ol>
        </section>
      )}
      <section className="tg-card p-4">
        <h2 className="text-lg font-bold">Reviewed cases</h2>
        <p className="mt-1 text-sm text-muted">Cases whose expected destination is not in the snapshot are skipped. They are not counted as hits.</p>
        <button
          type="button"
          className="tg-btn tg-btn-primary mt-3"
          onClick={async () => {
            try {
              setBench(await terraApi.benchmark(['keyword', 'dense', 'hybrid', 'hybrid_rerank', 'graph_hybrid']))
              setError(null)
            } catch (err) {
              setError(err instanceof ApiError ? err.message : 'Benchmark failed')
            }
          }}
        >
          Measure strategies
        </button>
        {bench && <pre className="mt-3 overflow-auto text-xs">{JSON.stringify(bench, null, 2)}</pre>}
      </section>
    </div>
  )
}
