import { Link } from 'react-router-dom'
import { Bookmark, Scale } from 'lucide-react'
import { DestinationPhoto } from '@/components/terra/DestinationPhoto'
import type { TerraDestination, TerraEvidence, TerraPhoto } from '@/lib/terra'

export type DestinationCardItem = TerraDestination & {
  photo?: TerraPhoto | null
  matched_preferences?: string[]
  unknown_preferences?: string[]
  evidence?: TerraEvidence[]
  evidence_count?: number
}

type Props = {
  item: DestinationCardItem
  compareSelected?: boolean
  onCompare?: () => void
  onSave?: () => void
  saveLabel?: string
}

export function DestinationCard({ item, compareSelected, onCompare, onSave, saveLabel = 'Save' }: Props) {
  const excerpt = item.evidence?.[0]?.excerpt
  return (
    <article className="terra-card flex flex-col overflow-hidden">
      <Link to={`/destinations/${item.slug}`} className="block focus-visible:outline-offset-[-4px]">
        <DestinationPhoto photo={item.photo} className="aspect-[4/3] w-full" sizes="(max-width:768px) 100vw, 33vw" />
      </Link>
      <div className="flex flex-1 flex-col p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">{item.region}</p>
        <h2 className="terra-serif mt-1 text-2xl leading-tight">
          <Link to={`/destinations/${item.slug}`} className="hover:underline">{item.name}</Link>
        </h2>
        <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-muted">
          {item.source_status === 'synthetic_test' ? 'Synthetic fixture — not a published guide.' : item.summary || 'No stored summary.'}
        </p>
        {!!item.matched_preferences?.length && (
          <p className="mt-3 text-xs text-ink">Matched: {item.matched_preferences.join(', ')}</p>
        )}
        {!!item.unknown_preferences?.length && (
          <p className="mt-1 text-xs text-muted">Unknown: {item.unknown_preferences.join(', ')}</p>
        )}
        {typeof item.evidence_count === 'number' && (
          <p className="mt-1 text-xs text-muted">{item.evidence_count} cited excerpts</p>
        )}
        {excerpt && <blockquote className="mt-3 line-clamp-3 border-l-2 border-[color:var(--terra-clay)] pl-3 text-sm text-muted">{excerpt}</blockquote>}
        <div className="mt-4 flex flex-wrap gap-2">
          <Link to={`/destinations/${item.slug}`} className="terra-btn terra-btn-primary text-xs">Open</Link>
          {onCompare && (
            <button type="button" className="terra-btn terra-btn-ghost text-xs" onClick={onCompare} aria-pressed={compareSelected}>
              <Scale className="size-3.5" aria-hidden /> {compareSelected ? 'Selected' : 'Compare'}
            </button>
          )}
          {onSave && (
            <button type="button" className="terra-btn terra-btn-ghost text-xs" onClick={onSave}>
              <Bookmark className="size-3.5" aria-hidden /> {saveLabel}
            </button>
          )}
        </div>
      </div>
    </article>
  )
}
