import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Compass, Mountain, Palmtree, Landmark } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { terraApi, stashPendingQuery, type TerraDestination } from '@/lib/terra'

const EXAMPLES = [
  'quiet hills and waterfalls for five days',
  'coastal towns with beaches',
  'a culture-focused long weekend',
]

export default function LandingPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const highlights = useQuery({ queryKey: ['terra-highlights'], queryFn: terraApi.highlights })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const text = query.trim()
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
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <Link to="/" className="terra-serif text-2xl font-semibold tracking-tight">terra<span className="text-primary">.</span></Link>
        <nav className="flex items-center gap-2 text-sm">
          <a href="#how" className="rounded-full px-3 py-2 text-muted hover:text-ink">How it works</a>
          {user ? (
            <Link to="/explore" className="rounded-full bg-primary px-4 py-2 font-semibold text-white">Explore</Link>
          ) : (
            <Link to="/login" className="rounded-full bg-primary px-4 py-2 font-semibold text-white">Sign in</Link>
          )}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-5 pb-16">
        <section className="grid items-center gap-10 py-8 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Powered by TravelGraph AI</p>
            <h1 className="terra-serif mt-3 text-5xl leading-tight text-ink sm:text-6xl">Somewhere new. Something unforgettable.</h1>
            <p className="mt-4 max-w-xl text-base leading-relaxed text-muted">
              Describe the kind of trip you want. Terra retrieves licensed or fixture source text, shows the evidence, and only then asks TravelGraph to plan.
            </p>
            <form onSubmit={submit} className="mt-6 rounded-3xl border border-line bg-white p-3 shadow-sm">
              <label htmlFor="terra-query" className="sr-only">Trip idea</label>
              <textarea
                id="terra-query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={3}
                placeholder="quiet mountains, waterfalls and culture, five days from Kolkata"
                className="w-full resize-none bg-transparent px-3 py-2 text-base outline-none"
              />
              <div className="flex flex-wrap items-center justify-between gap-3 px-2 pb-1">
                <div className="flex flex-wrap gap-2">
                  {EXAMPLES.map((example) => (
                    <button key={example} type="button" className="rounded-full border border-line px-3 py-1 text-xs text-muted" onClick={() => setQuery(example)}>
                      {example}
                    </button>
                  ))}
                </div>
                <button type="submit" className="rounded-full bg-primary px-5 py-2 text-sm font-semibold text-white">Discover</button>
              </div>
            </form>
          </div>
          <Landscape />
        </section>
        <section id="how" className="mt-8 grid gap-4 md:grid-cols-3">
          {[
            ['Discover', 'Search by meaning. If no place is named, Terra shows candidates instead of guessing.'],
            ['Read the source', 'Every recommendation carries an excerpt, license and snapshot id.'],
            ['Plan', 'Hand the destination to the existing TravelGraph agents when you are ready.'],
          ].map(([title, body]) => (
            <article key={title} className="rounded-3xl border border-line bg-white p-5">
              <h2 className="terra-serif text-2xl">{title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>
            </article>
          ))}
        </section>
        <section className="mt-12">
          <h2 className="terra-serif text-3xl">From the active snapshot</h2>
          <HighlightGrid items={highlights.data?.items ?? []} status={highlights.data?.status} />
        </section>
      </main>
      <footer className="border-t border-line px-5 py-8 text-center text-xs text-muted">
        Terra does not book travel. Photographs appear only when a snapshot includes a licensed file. Sources and licenses are shown on each destination.
      </footer>
    </div>
  )
}

function HighlightGrid({ items, status }: { items: TerraDestination[]; status?: string }) {
  if (!items.length) {
    return (
      <p className="mt-4 rounded-3xl border border-dashed border-line bg-white p-6 text-sm text-muted">
        {status === 'ready'
          ? 'The snapshot has destinations, but none were returned.'
          : 'No knowledge snapshot is active yet. After sign-in you can still use the legacy catalog planner. Build a snapshot with scripts/ingest.ps1 when a network fetch is available.'}
      </p>
    )
  }
  return (
    <ul className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {items.map((item) => (
        <li key={item.slug} className="rounded-3xl border border-line bg-white p-4">
          <p className="text-xs uppercase tracking-wide text-muted">{item.region}</p>
          <h3 className="terra-serif mt-1 text-2xl">{item.name}</h3>
          <p className="mt-2 text-xs text-muted">{item.source_status === 'synthetic_test' ? 'Synthetic test text, not a guide.' : item.summary || 'No summary stored.'}</p>
        </li>
      ))}
    </ul>
  )
}

function Landscape() {
  return (
    <div className="relative h-80 overflow-hidden rounded-[2rem] bg-[#243E36] text-[#F6F3EB]" aria-hidden>
      <svg viewBox="0 0 640 420" className="absolute inset-0 size-full">
        <rect width="640" height="420" fill="#243E36" />
        <path d="M0 280 C120 220 180 300 280 250 C380 200 430 260 520 210 C580 180 620 200 640 190 V420 H0 Z" fill="#A5B4A0" />
        <path d="M0 330 C140 300 200 360 320 320 C450 280 500 340 640 300 V420 H0 Z" fill="#BB7955" opacity="0.85" />
        <circle cx="480" cy="90" r="36" fill="#F6F3EB" opacity="0.9" />
      </svg>
      <p className="absolute bottom-4 left-4 text-xs">Original illustration. Not a photograph of a place.</p>
      <span className="sr-only">Illustrated hills</span>
      <div className="absolute right-4 top-4 flex gap-2 opacity-80">
        <Mountain className="size-5" />
        <Palmtree className="size-5" />
        <Landmark className="size-5" />
        <Compass className="size-5" />
      </div>
    </div>
  )
}
