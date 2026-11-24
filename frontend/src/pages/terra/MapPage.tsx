import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { DestinationMap } from '@/components/terra/DestinationMap'
import { readExploreQuery, terraApi, type TerraDestination } from '@/lib/terra'

export default function MapPage() {
  const navigate = useNavigate()
  const destinations = useQuery({ queryKey: ['terra-destinations'], queryFn: () => terraApi.destinations({ }) })
  const [selected, setSelected] = useState<string | null>(null)
  const items = useMemo(
    () => (destinations.data?.items ?? []).filter((item): item is TerraDestination & { lat: number; lon: number } => item.lat != null && item.lon != null),
    [destinations.data],
  )
  const missing = (destinations.data?.items ?? []).filter((item) => item.lat == null || item.lon == null)
  const selectedItem = items.find((item) => item.slug === selected) ?? null

  return (
    <div className="terra-scope -mx-4 -mt-5 px-4 py-6 pb-28 lg:-mx-6 lg:px-6 lg:pb-6">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="terra-serif text-4xl">Map</h1>
            <p className="mt-1 max-w-2xl text-sm text-muted">
              Offline MapLibre basemap with a simplified India outline and stored destination pins. Not a road map and not a driving route.
              {readExploreQuery() ? ' Last search stays in session storage, not the URL.' : ''}
            </p>
          </div>
          <Link to="/explore" className="terra-btn terra-btn-ghost text-sm">List</Link>
        </div>

        {destinations.isError && (
          <p className="mt-4" role="alert">The snapshot is not available, so there is nothing to plot.</p>
        )}

        <div className="mt-5 grid gap-4 lg:grid-cols-[1.4fr_0.8fr]">
          <DestinationMap
            className="h-[520px] w-full"
            items={items}
            selectedSlug={selected}
            onSelect={(slug) => {
              setSelected(slug)
            }}
          />
          <aside className="rounded-[1.5rem] border border-line bg-white p-4">
            <h2 className="terra-serif text-2xl">Places with coordinates</h2>
            <p className="mt-1 text-xs text-muted">{items.length} plotted · {missing.length} omitted</p>
            <ul className="mt-4 max-h-[420px] space-y-2 overflow-auto">
              {items.map((item) => (
                <li key={item.slug}>
                  <button
                    type="button"
                    className={`w-full rounded-xl px-3 py-2 text-left text-sm ${selected === item.slug ? 'bg-[color:var(--terra-forest)] text-white' : 'hover:bg-surface-2'}`}
                    onClick={() => setSelected(item.slug)}
                  >
                    <span className="font-semibold">{item.name}</span>
                    <span className={`mt-0.5 block text-xs ${selected === item.slug ? 'text-white/80' : 'text-muted'}`}>{item.region}</span>
                  </button>
                </li>
              ))}
            </ul>
            {selectedItem && (
              <button
                type="button"
                className="terra-btn terra-btn-primary mt-4 w-full text-sm"
                onClick={() => navigate(`/destinations/${selectedItem.slug}`)}
              >
                Open {selectedItem.name}
              </button>
            )}
          </aside>
        </div>

        {!!missing.length && (
          <p className="mt-3 text-xs text-muted">
            Not plotted because coordinates are unknown: {missing.map((item) => item.name).join(', ')}.
          </p>
        )}
      </div>
    </div>
  )
}
