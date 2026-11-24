import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { readCompareIds, terraApi } from '@/lib/terra'

export default function ComparePage() {
  const ids = readCompareIds()
  const query = useQuery({
    queryKey: ['terra-compare', ids.join('|')],
    queryFn: () => terraApi.compare(ids),
    enabled: ids.length >= 2,
  })
  if (ids.length < 2) {
    return <p className="text-sm">Select two or three destinations from Explore first. <Link className="underline" to="/explore">Back to Explore</Link></p>
  }
  if (query.isLoading) return <p className="text-sm text-muted">Comparing stored fields…</p>
  if (query.isError) return <p role="alert">Comparison failed.</p>
  const results = query.data?.results ?? []
  return (
    <div className="terra-scope -mx-4 -mt-5 px-4 py-6 lg:-mx-6 lg:px-6">
      <div className="mx-auto max-w-6xl">
        <h1 className="terra-serif text-4xl">Compare</h1>
        <p className="mt-2 text-sm text-muted">{query.data?.note}</p>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          {results.map((item) => (
            <article key={String(item.slug)} className="rounded-3xl border border-line bg-white p-5">
              <h2 className="terra-serif text-3xl">{String(item.name)}</h2>
              <p className="text-xs uppercase text-muted">{String(item.region)} · {String(item.source_status)}</p>
              <p className="mt-3 text-sm">Attractions stored: {String(item.attraction_count)}</p>
              <p className="mt-1 text-sm">Missing: {((item.missing as string[]) || []).join(', ') || 'none flagged'}</p>
              <Link className="mt-4 inline-block text-sm underline" to={`/destinations/${String(item.slug)}`}>Open guide</Link>
            </article>
          ))}
        </div>
      </div>
    </div>
  )
}
