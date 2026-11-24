import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ApiError } from '@/lib/api'
import { terraApi, type TerraEvidence } from '@/lib/terra'

export default function DestinationPage() {
  const { slug = '' } = useParams()
  const navigate = useNavigate()
  const detail = useQuery({ queryKey: ['terra-dest', slug], queryFn: () => terraApi.destination(slug), enabled: !!slug })
  const [question, setQuestion] = useState('What is this place known for?')
  const [answer, setAnswer] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState<TerraEvidence | null>(null)

  const dest = (detail.data?.destination ?? null) as {
    destination_id?: string
    name?: string
    region?: string
    source_status?: string
    summary?: string
    lat?: number | null
    lon?: number | null
    coordinate_status?: string
  } | null
  const attractions = (detail.data?.attractions ?? []) as Array<Record<string, unknown>>
  const sources = (detail.data?.sources ?? []) as Array<Record<string, string>>
  const estimates = (detail.data?.estimates ?? []) as Array<Record<string, unknown>>
  const network = detail.data?.network_tools as { reason?: string } | undefined

  const ask = async (event: FormEvent) => {
    event.preventDefault()
    try {
      setAnswer(await terraApi.ask(slug, question))
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Question failed')
    }
  }

  if (detail.isLoading) return <p className="text-sm text-muted">Loading destination…</p>
  if (detail.isError || !dest) return <p role="alert">This destination is not in the active snapshot.</p>

  return (
    <div className="terra-scope -mx-4 -mt-5 px-4 py-6 lg:-mx-6 lg:px-6">
      <div className="mx-auto max-w-4xl">
        <p className="text-xs uppercase tracking-wide text-muted">{dest.region}</p>
        <h1 className="terra-serif text-5xl">{dest.name}</h1>
        <p className="mt-2 text-sm text-muted">
          {dest.source_status === 'synthetic_test' ? 'Synthetic test fixture. Not a published guide or photograph.' : dest.summary || 'No summary is stored.'}
        </p>
        <p className="mt-1 text-xs text-muted">Coordinates: {dest.coordinate_status || 'unknown'}{dest.lat != null ? ` · ${dest.lat}, ${dest.lon}` : ''}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-white"
            onClick={() => navigate('/trips/new', { state: { destination: dest.name, destination_id: dest.destination_id, prompt: `Plan a trip to ${dest.name}` } })}
          >
            Plan trip
          </button>
          <button type="button" className="rounded-full border border-line bg-white px-4 py-2 text-sm" onClick={() => dest.destination_id && terraApi.save(dest.destination_id)}>
            Save
          </button>
          <Link to="/explore" className="rounded-full border border-line bg-white px-4 py-2 text-sm">Back</Link>
        </div>
        <section className="mt-8">
          <h2 className="terra-serif text-3xl">Attractions in the snapshot</h2>
          {!attractions.length && <p className="mt-2 text-sm text-muted">No named attractions were ingested for this place.</p>}
          <ul className="mt-3 space-y-2">
            {attractions.map((item) => (
              <li key={String(item.id)} className="rounded-2xl border border-line bg-white px-4 py-3 text-sm">
                <span className="font-semibold">{String(item.name)}</span>
                <span className="text-muted"> · {String(item.category)}</span>
                {item.lat == null && <span className="text-muted"> · coordinates unknown</span>}
              </li>
            ))}
          </ul>
        </section>
        <section className="mt-8">
          <h2 className="terra-serif text-3xl">Cost estimates</h2>
          {!estimates.length && <p className="mt-2 text-sm">No stored cost estimate. Budget fit is unknown.</p>}
          <ul className="mt-3 space-y-2 text-sm">
            {estimates.map((est, index) => (
              <li key={index} className="rounded-2xl border border-line bg-white px-4 py-3">
                {String(est.category)} · {est.low_inr != null ? `₹${String(est.low_inr)}–₹${String(est.high_inr)}` : 'range unknown'} · {String(est.basis || 'basis unknown')}
                <p className="text-xs text-muted">{String(est.method || '')}</p>
              </li>
            ))}
          </ul>
        </section>
        <section className="mt-8">
          <h2 className="terra-serif text-3xl">Ask about this place</h2>
          <form onSubmit={ask} className="mt-3 flex flex-col gap-2 sm:flex-row">
            <input value={question} onChange={(e) => setQuestion(e.target.value)} className="flex-1 rounded-2xl border border-line bg-white px-4 py-3" />
            <button className="rounded-2xl bg-primary px-4 py-3 text-sm font-semibold text-white" type="submit">Ask</button>
          </form>
          {error && <p className="mt-2 text-sm" role="alert">{error}</p>}
          {answer && <AnswerBlock answer={answer} onOpen={setOpen} />}
        </section>
        <section className="mt-8">
          <h2 className="terra-serif text-3xl">Sources</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {sources.map((source) => (
              <li key={source.id} className="rounded-2xl border border-line bg-white px-4 py-3">
                <p className="font-semibold">{source.title}</p>
                <p className="text-xs text-muted">{source.license_name} · {source.source_type}</p>
                {source.permalink && <a className="text-xs underline" href={source.permalink} target="_blank" rel="noreferrer noopener">{source.permalink}</a>}
              </li>
            ))}
          </ul>
          {network?.reason && <p className="mt-3 text-xs text-muted">{network.reason}</p>}
        </section>
      </div>
      {open && (
        <div className="fixed inset-0 z-50 grid place-items-end bg-black/40 p-4 sm:place-items-center" role="dialog" aria-modal="true" aria-label="Citation">
          <div className="max-h-[80vh] w-full max-w-lg overflow-auto rounded-3xl bg-white p-5">
            <h3 className="terra-serif text-2xl">{open.title}</h3>
            <p className="mt-1 text-xs text-muted">{open.section_path} · {open.license}</p>
            <p className="mt-3 text-sm leading-relaxed">{open.excerpt}</p>
            {open.permalink && <a className="mt-3 block text-sm underline" href={open.permalink} target="_blank" rel="noreferrer noopener">Source revision</a>}
            <button type="button" className="mt-4 rounded-full border border-line px-3 py-1 text-sm" onClick={() => setOpen(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  )
}

function AnswerBlock({ answer, onOpen }: { answer: Record<string, unknown>; onOpen: (ev: TerraEvidence) => void }) {
  const claims = (answer.claims as Array<{ text: string; evidence_ids: string[] }> | undefined) ?? []
  const citations = (answer.citations as TerraEvidence[] | undefined) ?? []
  return (
    <div className="mt-4 rounded-3xl border border-line bg-white p-4 text-sm">
      <p className="text-xs uppercase tracking-wide text-muted">{String(answer.generation_mode || '')} · vectors {String(answer.embedding_kind || '')}</p>
      {answer.insufficient_evidence ? <p className="mt-2">The snapshot does not contain enough support to answer that.</p> : null}
      <ul className="mt-2 space-y-2">
        {claims.map((claim) => (
          <li key={claim.text}>
            {claim.text}{' '}
            {claim.evidence_ids.map((id) => (
              <button key={id} type="button" className="underline" onClick={() => {
                const found = citations.find((item) => item.id === id)
                if (found) onOpen(found)
              }}>source</button>
            ))}
          </li>
        ))}
      </ul>
    </div>
  )
}
