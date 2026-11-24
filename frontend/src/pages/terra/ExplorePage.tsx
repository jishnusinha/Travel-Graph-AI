import { useEffect, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Bookmark, Map as MapIcon, Scale } from 'lucide-react'
import { ApiError } from '@/lib/api'
import {
  readCompareIds,
  readExploreQuery,
  readPendingQuery,
  rememberExploreQuery,
  takePendingQuery,
  terraApi,
  toggleCompareId,
  writeCompareIds,
  type DiscoveryResult,
} from '@/lib/terra'

export default function ExplorePage() {
  const location = useLocation()
  const navigate = useNavigate()
  const seeded = (location.state as { query?: string } | null)?.query || readPendingQuery() || readExploreQuery()
  const [query, setQuery] = useState(seeded)
  useEffect(() => {
    if (readPendingQuery()) takePendingQuery()
  }, [])
  const [compare, setCompare] = useState<string[]>(readCompareIds())
  const [result, setResult] = useState<DiscoveryResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const search = useMutation({
    mutationFn: (text: string) => terraApi.search(text, 'hybrid_rerank'),
    onSuccess: (data) => {
      setResult(data)
      setError(null)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Search failed'),
  })

  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    const text = query.trim()
    if (text.length < 2) return
    rememberExploreQuery(text)
    search.mutate(text)
  }

  const onCompare = (id: string) => {
    const next = toggleCompareId(compare, id)
    setCompare(next)
    writeCompareIds(next)
  }

  return (
    <div className="terra-scope -mx-4 -mt-5 min-h-full px-4 py-6 pb-28 lg:-mx-6 lg:px-6 lg:pb-6">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Terra</p>
            <h1 className="terra-serif text-4xl">Explore</h1>
          </div>
          <Link to="/explore/map" className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-4 py-2 text-sm font-semibold">
            <MapIcon className="size-4" /> Map
          </Link>
        </div>
        <form onSubmit={submit} className="mt-5 flex flex-col gap-3 rounded-3xl border border-line bg-white p-3 sm:flex-row">
          <label className="sr-only" htmlFor="explore-query">Search</label>
          <input id="explore-query" value={query} onChange={(e) => setQuery(e.target.value)} className="min-w-0 flex-1 rounded-2xl bg-surface-2 px-4 py-3 outline-none" placeholder="quiet hills, waterfalls, culture" />
          <button className="rounded-2xl bg-primary px-5 py-3 text-sm font-semibold text-white" type="submit" disabled={search.isPending}>
            {search.isPending ? 'Searching…' : 'Search'}
          </button>
        </form>
        {error && <p className="mt-4 rounded-2xl border border-line bg-white p-4 text-sm" role="alert">{error}</p>}
        {result && (
          <p className="mt-4 text-xs text-muted">
            Snapshot {result.snapshot_id} · strategy {result.strategy_applied} · vectors {result.embedding_kind}
            {result.warnings?.length ? ` · ${result.warnings.join(', ')}` : ''}
          </p>
        )}
        {result?.insufficient_evidence && <p className="mt-4 text-sm">No destination in the snapshot matched this query.</p>}
        <ul className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {(result?.results ?? []).map((item) => (
            <li key={item.slug} className="flex flex-col rounded-3xl border border-line bg-white p-5">
              <p className="text-xs uppercase tracking-wide text-muted">{item.region}</p>
              <h2 className="terra-serif text-3xl">{item.name}</h2>
              <p className="mt-2 text-xs text-muted">{item.source_status === 'synthetic_test' ? 'Synthetic fixture — not a published guide.' : item.summary || 'No stored summary.'}</p>
              <p className="mt-3 text-sm">Matched: {item.matched_preferences.join(', ') || 'none labeled'}</p>
              <p className="text-sm text-muted">Unknown: {item.unknown_preferences.join(', ')}</p>
              <p className="mt-2 text-xs text-muted">{item.evidence_count} cited excerpts</p>
              {item.evidence[0] && (
                <blockquote className="mt-3 border-l-2 border-primary pl-3 text-sm text-muted">{item.evidence[0].excerpt}</blockquote>
              )}
              <div className="mt-4 flex flex-wrap gap-2">
                <Link to={`/destinations/${item.slug}`} className="rounded-full bg-primary px-3 py-1.5 text-xs font-semibold text-white">Open</Link>
                <button type="button" className="inline-flex items-center gap-1 rounded-full border border-line px-3 py-1.5 text-xs" onClick={() => item.destination_id && onCompare(item.destination_id)}>
                  <Scale className="size-3" /> {compare.includes(item.destination_id) ? 'Selected' : 'Compare'}
                </button>
                <SaveButton id={item.destination_id} />
              </div>
            </li>
          ))}
        </ul>
        {compare.length > 0 && (
          <div className="sticky bottom-20 mt-6 flex items-center justify-between rounded-2xl bg-primary px-4 py-3 text-sm text-white lg:bottom-4">
            <span>{compare.length} selected (max 3)</span>
            <button type="button" className="rounded-full bg-white px-3 py-1 font-semibold text-primary" onClick={() => navigate('/explore/compare')} disabled={compare.length < 2}>
              Compare
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function SaveButton({ id }: { id: string }) {
  const [label, setLabel] = useState('Save')
  return (
    <button
      type="button"
      className="inline-flex items-center gap-1 rounded-full border border-line px-3 py-1.5 text-xs"
      onClick={async () => {
        await terraApi.save(id)
        setLabel('Saved')
      }}
    >
      <Bookmark className="size-3" /> {label}
    </button>
  )
}
