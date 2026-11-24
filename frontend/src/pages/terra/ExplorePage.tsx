import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Map as MapIcon } from 'lucide-react'
import { DestinationCard } from '@/components/terra/DestinationCard'
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

const FILTERS = [
  { id: 'all', label: 'All matches' },
  { id: 'waterfalls', label: 'Waterfalls' },
  { id: 'beaches', label: 'Beaches' },
  { id: 'culture', label: 'Culture' },
  { id: 'mountains', label: 'Mountains' },
]

export default function ExplorePage() {
  const location = useLocation()
  const navigate = useNavigate()
  const seeded = (location.state as { query?: string } | null)?.query || readPendingQuery() || readExploreQuery()
  const [query, setQuery] = useState(seeded)
  const [filter, setFilter] = useState('all')
  const [compare, setCompare] = useState<string[]>(readCompareIds())
  const [result, setResult] = useState<DiscoveryResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<Record<string, string>>({})
  const requestId = useRef(0)
  const bootstrapped = useRef(false)

  const search = useMutation({
    mutationFn: (text: string) => terraApi.search(text, 'hybrid_rerank'),
    onSuccess: (data, text) => {
      setResult(data)
      setError(null)
      rememberExploreQuery(text)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Search failed'),
  })

  useEffect(() => {
    if (readPendingQuery()) takePendingQuery()
    if (bootstrapped.current) return
    bootstrapped.current = true
    const text = query.trim()
    if (text.length >= 2) {
      const id = ++requestId.current
      search.mutate(text, {
        onSuccess: (data) => {
          if (id === requestId.current) {
            setResult(data)
            setError(null)
          }
        },
      })
    }
    // Seeded search once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    const text = query.trim()
    if (text.length < 2) return
    const id = ++requestId.current
    search.mutate(text, {
      onSuccess: (data) => {
        if (id === requestId.current) {
          setResult(data)
          setError(null)
          rememberExploreQuery(text)
        }
      },
    })
  }

  const onCompare = (id: string) => {
    const next = toggleCompareId(compare, id)
    setCompare(next)
    writeCompareIds(next)
  }

  const visible = (result?.results ?? []).filter((item) => {
    if (filter === 'all') return true
    const blob = `${item.matched_preferences.join(' ')} ${(item.themes ?? []).join(' ')} ${item.summary ?? ''}`.toLowerCase()
    return blob.includes(filter)
  })

  return (
    <div className="terra-scope -mx-4 -mt-5 min-h-full px-4 py-6 pb-28 lg:-mx-6 lg:px-6 lg:pb-6">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">Terra</p>
            <h1 className="terra-serif text-4xl">Explore</h1>
          </div>
          <Link to="/explore/map" className="terra-btn terra-btn-ghost text-sm">
            <MapIcon className="size-4" aria-hidden /> Map
          </Link>
        </div>

        <form onSubmit={submit} className="mt-5 flex flex-col gap-3 rounded-[1.5rem] border border-line bg-white p-3 sm:flex-row sm:items-center">
          <label className="sr-only" htmlFor="explore-query">Search</label>
          <input
            id="explore-query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="min-w-0 flex-1 rounded-2xl bg-surface-2 px-4 py-3 outline-none"
            placeholder="quiet hills, waterfalls, culture"
          />
          <button className="terra-btn terra-btn-primary shrink-0" type="submit" disabled={search.isPending}>
            {search.isPending ? 'Searching…' : 'Search'}
          </button>
        </form>

        <div className="mt-4 flex flex-wrap gap-2" aria-label="Preference filters">
          {FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${filter === item.id ? 'border-[color:var(--terra-forest)] bg-[color:var(--terra-forest)] text-white' : 'border-line bg-white text-muted'}`}
              aria-pressed={filter === item.id}
              onClick={() => setFilter(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>

        {error && <p className="mt-4 rounded-2xl border border-line bg-white p-4 text-sm" role="alert">{error}</p>}
        {result && (
          <p className="mt-4 text-xs text-muted">
            Snapshot {result.snapshot_id} · strategy {result.strategy_applied} · vectors {result.embedding_kind}
            {result.warnings?.length ? ` · ${result.warnings.join(', ')}` : ''}
          </p>
        )}
        {search.isPending && !result && (
          <ul className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-hidden>
            {Array.from({ length: 3 }).map((_, index) => (
              <li key={index} className="terra-card h-72 animate-pulse bg-surface-2" />
            ))}
          </ul>
        )}
        {result?.insufficient_evidence && <p className="mt-4 text-sm">No destination in the snapshot matched this query.</p>}
        {!search.isPending && result && !result.insufficient_evidence && !visible.length && (
          <p className="mt-4 text-sm text-muted">No results for that filter. Try All matches.</p>
        )}

        <ul className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((item) => (
            <li key={item.slug}>
              <DestinationCard
                item={item}
                compareSelected={compare.includes(item.destination_id)}
                onCompare={() => item.destination_id && onCompare(item.destination_id)}
                saveLabel={saved[item.destination_id] || 'Save'}
                onSave={async () => {
                  if (!item.destination_id) return
                  await terraApi.save(item.destination_id)
                  setSaved((prev) => ({ ...prev, [item.destination_id]: 'Saved' }))
                }}
              />
            </li>
          ))}
        </ul>

        {compare.length > 0 && (
          <div className="sticky bottom-20 z-20 mt-6 flex items-center justify-between rounded-2xl bg-[color:var(--terra-forest)] px-4 py-3 text-sm text-white lg:bottom-4">
            <span>{compare.length} selected (max 3)</span>
            <button
              type="button"
              className="rounded-full bg-white px-3 py-1 font-semibold text-[color:var(--terra-forest)]"
              onClick={() => navigate('/explore/compare')}
              disabled={compare.length < 2}
            >
              Compare
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
