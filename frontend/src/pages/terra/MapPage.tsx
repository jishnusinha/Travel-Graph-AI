import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { readExploreQuery, terraApi, type TerraDestination } from '@/lib/terra'

function project(lat: number, lon: number) {
  const x = ((lon - 68) / (98 - 68)) * 100
  const y = ((36 - lat) / (36 - 6)) * 100
  return { x: Math.min(100, Math.max(0, x)), y: Math.min(100, Math.max(0, y)) }
}

export default function MapPage() {
  const destinations = useQuery({ queryKey: ['terra-destinations'], queryFn: () => terraApi.destinations() })
  const items = (destinations.data?.items ?? []).filter((item) => item.lat != null && item.lon != null) as Array<TerraDestination & { lat: number; lon: number }>
  const missing = (destinations.data?.items ?? []).filter((item) => item.lat == null || item.lon == null)
  return (
    <div className="terra-scope -mx-4 -mt-5 px-4 py-6 lg:-mx-6 lg:px-6">
      <div className="mx-auto max-w-5xl">
        <div className="flex items-end justify-between gap-3">
          <div>
            <h1 className="terra-serif text-4xl">Map</h1>
            <p className="mt-1 text-sm text-muted">Schematic positions from stored coordinates. Not a road map and not a driving route. {readExploreQuery() ? `Last search kept off the URL.` : ''}</p>
          </div>
          <Link to="/explore" className="text-sm underline">List</Link>
        </div>
        {destinations.isError && <p className="mt-4" role="alert">The snapshot is not available, so there is nothing to plot.</p>}
        <div className="relative mt-5 h-[480px] overflow-hidden rounded-[2rem] border border-line bg-[#e7efe9]">
          <svg viewBox="0 0 100 100" className="size-full" role="img" aria-label="Schematic map of stored destination coordinates">
            <rect width="100" height="100" fill="#e7efe9" />
            {items.map((item) => {
              const point = project(item.lat, item.lon)
              return (
                <a key={item.slug} href={`/destinations/${item.slug}`}>
                  <circle cx={point.x} cy={point.y} r="1.6" fill="#243E36" />
                  <text x={point.x + 2} y={point.y} fontSize="2.4" fill="#222722">{item.name}</text>
                </a>
              )
            })}
          </svg>
        </div>
        {!!missing.length && <p className="mt-3 text-xs text-muted">Not plotted because coordinates are unknown: {missing.map((item) => item.name).join(', ')}.</p>}
      </div>
    </div>
  )
}
