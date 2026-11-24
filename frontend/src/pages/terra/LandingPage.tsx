import { useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/context/AuthContext'
import { DestinationPhoto } from '@/components/terra/DestinationPhoto'
import { stashPendingQuery, terraApi, type TerraDestination } from '@/lib/terra'

const EXAMPLES = [
  'quiet hills and waterfalls for five days',
  'coastal towns with beaches',
  'a culture-focused long weekend',
]

const COLLECTIONS = [
  { id: 'mountains', label: 'Mountains', theme: 'mountains', query: 'quiet hills and mountains' },
  { id: 'culture', label: 'Culture', theme: 'culture', query: 'culture heritage temples' },
  { id: 'coastal', label: 'Coastal', theme: 'beaches', query: 'coastal towns with beaches' },
  { id: 'nature', label: 'Nature', theme: 'nature', query: 'forests waterfalls nature' },
]

export default function LandingPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const highlights = useQuery({ queryKey: ['terra-highlights'], queryFn: terraApi.highlights })
  const items = highlights.data?.items ?? []
  const hero = useMemo(() => items.find((item) => item.photo?.url) ?? items[0] ?? null, [items])

  const submit = (event: FormEvent, next = query) => {
    event.preventDefault()
    const text = next.trim()
    if (text.length < 2) return
    if (!user) {
      stashPendingQuery(text)
      navigate('/login', { state: { from: '/explore' } })
      return
    }
    if (!user.onboarding_completed) {
      stashPendingQuery(text)
      navigate('/onboarding')
      return
    }
    navigate('/explore', { state: { query: text } })
  }

  return (
    <div className="terra-scope min-h-screen">
      <section className="relative min-h-[100svh] overflow-hidden">
        {hero?.photo?.url ? (
          <img
            src={hero.photo.url}
            alt=""
            aria-hidden
            className="absolute inset-0 size-full object-cover terra-fade"
            fetchPriority="high"
          />
        ) : (
          <div className="absolute inset-0 bg-[color:var(--terra-forest)]" aria-hidden />
        )}
        <div className="terra-hero-scrim absolute inset-0" aria-hidden />
        <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-5 py-5 text-white">
          <Link to="/" className="terra-serif text-3xl tracking-tight">
            terra<span className="text-[color:var(--terra-clay)]">.</span>
          </Link>
          <nav className="flex items-center gap-2 text-sm">
            <a href="#how" className="rounded-full px-3 py-2 text-white/80 hover:text-white">How it works</a>
            {user ? (
              <Link to="/explore" className="terra-btn terra-btn-accent">Explore</Link>
            ) : (
              <Link to="/login" className="terra-btn terra-btn-accent">Sign in</Link>
            )}
          </nav>
        </header>
        <div className="relative z-10 mx-auto flex min-h-[calc(100svh-5.5rem)] max-w-6xl flex-col justify-end px-5 pb-14 pt-10 text-white">
          <p className="terra-rise text-xs font-semibold uppercase tracking-[0.2em] text-white/70">terra · TravelGraph AI</p>
          <h1 className="terra-serif terra-rise mt-3 max-w-3xl text-5xl leading-[1.05] sm:text-6xl lg:text-7xl" style={{ animationDelay: '80ms' }}>
            Somewhere new. Something unforgettable.
          </h1>
          <p className="terra-rise mt-4 max-w-xl text-base leading-relaxed text-white/85" style={{ animationDelay: '140ms' }}>
            Describe the trip you want. Terra retrieves licensed source text, shows the evidence, then hands a place to TravelGraph to plan.
          </p>
          <form onSubmit={submit} className="terra-rise mt-7 max-w-3xl rounded-[1.5rem] border border-white/20 bg-white/95 p-3 text-ink shadow-soft" style={{ animationDelay: '200ms' }}>
            <label htmlFor="terra-query" className="sr-only">Trip idea</label>
            <textarea
              id="terra-query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={2}
              placeholder="quiet mountains, waterfalls and culture, five days"
              className="w-full resize-none bg-transparent px-3 py-2 text-base outline-none"
            />
            <div className="flex flex-wrap items-center justify-between gap-3 px-2 pb-1">
              <div className="flex flex-wrap gap-2">
                {EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    className="rounded-full border border-line px-3 py-1 text-xs text-muted hover:border-[color:var(--terra-forest)] hover:text-ink"
                    onClick={() => setQuery(example)}
                  >
                    {example}
                  </button>
                ))}
              </div>
              <button type="submit" className="terra-btn terra-btn-primary">Discover</button>
            </div>
          </form>
          {hero?.photo && (
            <p className="mt-4 max-w-2xl text-[11px] text-white/70">
              Hero photograph: {hero.name}
              {hero.photo.author ? ` · ${hero.photo.author}` : ''}
              {hero.photo.license_name ? ` · ${hero.photo.license_name}` : ''}
            </p>
          )}
        </div>
      </section>

      <main className="mx-auto max-w-6xl px-5 py-16">
        <section id="how" className="grid gap-8 md:grid-cols-3">
          {[
            ['Discover', 'Search by meaning. If no place is named, Terra shows candidates instead of guessing.'],
            ['Read the source', 'Every recommendation carries an excerpt, license and snapshot id.'],
            ['Plan', 'Hand the destination to the existing TravelGraph agents when you are ready.'],
          ].map(([title, body]) => (
            <article key={title}>
              <h2 className="terra-serif text-3xl">{title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>
            </article>
          ))}
        </section>

        <section className="mt-16">
          <h2 className="terra-serif text-4xl">Collections</h2>
          <p className="mt-2 text-sm text-muted">Themes from the active snapshot registry. Opening one starts a real discovery search after sign-in.</p>
          <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {COLLECTIONS.map((collection) => {
              const count = items.filter((item) => (item.themes ?? []).includes(collection.theme)).length
              return (
                <li key={collection.id}>
                  <button
                    type="button"
                    className="w-full rounded-[1.25rem] border border-line bg-white px-4 py-5 text-left transition hover:border-[color:var(--terra-forest)]"
                    onClick={(event) => submit(event, collection.query)}
                  >
                    <span className="terra-serif text-2xl">{collection.label}</span>
                    <span className="mt-1 block text-xs text-muted">
                      {count ? `${count} highlighted places mention this theme` : 'Search the full snapshot'}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </section>

        <section className="mt-16">
          <div className="flex items-end justify-between gap-3">
            <div>
              <h2 className="terra-serif text-4xl">From the active snapshot</h2>
              <p className="mt-2 text-sm text-muted">
                {highlights.data?.snapshot_id ? `Snapshot ${highlights.data.snapshot_id}` : 'No snapshot id yet'}
              </p>
            </div>
            {user && <Link to="/explore" className="terra-btn terra-btn-ghost text-sm">Open Explore</Link>}
          </div>
          <HighlightGrid items={items} status={highlights.data?.status} />
        </section>
      </main>

      <footer className="border-t border-line px-5 py-8 text-center text-xs text-muted">
        Terra does not book travel. Photographs appear only when a snapshot includes a licensed Commons file. Sources and licenses are shown on each destination.
      </footer>
    </div>
  )
}

function HighlightGrid({ items, status }: { items: TerraDestination[]; status?: string }) {
  if (!items.length) {
    return (
      <p className="mt-4 rounded-[1.25rem] border border-dashed border-line bg-white p-6 text-sm text-muted">
        {status === 'ready'
          ? 'The snapshot has destinations, but none were returned.'
          : 'No knowledge snapshot is active yet. After sign-in you can still use the legacy catalog planner.'}
      </p>
    )
  }
  return (
    <ul className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
      {items.map((item) => (
        <li key={item.slug} className="terra-card overflow-hidden">
          <DestinationPhoto photo={item.photo} className="aspect-[4/3] w-full" />
          <div className="p-4">
            <p className="text-[11px] uppercase tracking-[0.14em] text-muted">{item.region}</p>
            <h3 className="terra-serif mt-1 text-2xl">{item.name}</h3>
            <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-muted">
              {item.source_status === 'synthetic_test' ? 'Synthetic test text, not a guide.' : item.summary || 'No summary stored.'}
            </p>
          </div>
        </li>
      ))}
    </ul>
  )
}
