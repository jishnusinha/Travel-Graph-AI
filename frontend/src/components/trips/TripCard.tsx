import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Calendar, Copy, Heart, MapPin, MoreHorizontal, PlayCircle, Trash2, Users, Wallet, ExternalLink } from 'lucide-react'
import { CoverImage } from '@/components/ui/CoverImage'
import { StatusPill } from '@/components/ui/StatusPill'
import type { TripListItem } from '@/lib/types'
import { cn, formatINR } from '@/lib/utils'

export interface TripCardActions {
  onFavorite?: (t: TripListItem) => void
  onDuplicate?: (t: TripListItem) => void
  onDelete?: (t: TripListItem) => void
}

interface Props extends TripCardActions {
  trip: TripListItem
  /** compact = dashboard tile, full = My Journeys card with action row */
  variant?: 'compact' | 'full'
  list?: boolean
}

export function TripCard({ trip, variant = 'compact', list, onFavorite, onDuplicate, onDelete }: Props) {
  const [menu, setMenu] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!menu) return
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setMenu(false)
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setMenu(false)
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', esc)
    }
  }, [menu])

  const href = `/trips/${trip.id}`
  const draft = trip.status === 'draft'
  const hasActions = !!(onFavorite || onDuplicate || onDelete)

  return (
    <article className={cn('tg-card group overflow-hidden', list && 'flex flex-col sm:flex-row')}>
      <div className={cn('relative', list ? 'h-40 sm:h-auto sm:w-56 sm:shrink-0' : 'h-40')}>
        <Link to={href} tabIndex={-1} aria-hidden>
          <CoverImage src={trip.cover_image} className="size-full transition-transform duration-300 group-hover:scale-105" />
        </Link>
        <div className="absolute left-3 top-3">
          <StatusPill status={trip.status} className="bg-surface/95 backdrop-blur" />
        </div>
        {onFavorite ? (
          <button
            type="button"
            aria-label={trip.is_favorite ? `Remove ${trip.title} from favorites` : `Add ${trip.title} to favorites`}
            aria-pressed={trip.is_favorite}
            onClick={() => onFavorite(trip)}
            className="absolute right-3 top-3 grid size-8 place-items-center rounded-full bg-surface/95 shadow"
          >
            <Heart className={cn('size-4', trip.is_favorite ? 'fill-danger text-danger' : 'text-muted')} />
          </button>
        ) : (
          hasActions && null
        )}
      </div>
      <div className="flex min-w-0 flex-1 flex-col p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="truncate text-base font-bold">
              <Link to={href} className="hover:text-primary-strong">
                {trip.title}
              </Link>
            </h3>
            {trip.destination && (
              <p className="mt-0.5 flex items-center gap-1 truncate text-xs text-muted">
                <MapPin className="size-3.5" /> {trip.destination}
              </p>
            )}
          </div>
          {hasActions && (
            <div ref={ref} className="relative">
              <button type="button" aria-label={`More actions for ${trip.title}`} aria-expanded={menu} onClick={() => setMenu((m) => !m)} className="grid size-8 place-items-center rounded-lg text-muted hover:bg-primary-soft">
                <MoreHorizontal className="size-4" />
              </button>
              {menu && (
                <div role="menu" className="tg-card absolute right-0 top-9 z-20 w-48 bg-surface p-1.5 text-sm">
                  <Link role="menuitem" to={href} className="flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-primary-soft">
                    <ExternalLink className="size-4" /> {draft ? 'Continue / Edit' : 'Open trip'}
                  </Link>
                  {onDuplicate && (
                    <button role="menuitem" type="button" onClick={() => { setMenu(false); onDuplicate(trip) }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 hover:bg-primary-soft">
                      <Copy className="size-4" /> Duplicate trip
                    </button>
                  )}
                  {onFavorite && (
                    <button role="menuitem" type="button" onClick={() => { setMenu(false); onFavorite(trip) }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 hover:bg-primary-soft">
                      <Heart className="size-4" /> {trip.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
                    </button>
                  )}
                  {onDelete && (
                    <button role="menuitem" type="button" onClick={() => { setMenu(false); onDelete(trip) }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-danger hover:bg-danger-soft">
                      <Trash2 className="size-4" /> Delete trip
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <dl className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted">
          <div className="flex items-center gap-1.5"><Calendar className="size-3.5" /><dt className="sr-only">Duration</dt><dd>{trip.day_count ? `${trip.day_count} ${trip.day_count === 1 ? 'day' : 'days'}` : 'Not planned'}</dd></div>
          <div className="flex items-center gap-1.5"><Users className="size-3.5" /><dt className="sr-only">Travelers</dt><dd>{trip.travelers} {trip.travelers === 1 ? 'traveler' : 'travelers'}</dd></div>
          <div className="flex items-center gap-1.5"><Wallet className="size-3.5" /><dt className="sr-only">Cost</dt><dd className="font-semibold text-ink">{formatINR(trip.estimated_cost_inr || trip.budget_inr)}</dd></div>
        </dl>

        {variant === 'full' && (
          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Link to={href} className="tg-btn tg-btn-primary tg-btn-sm col-span-2 sm:col-span-1">
              {draft || trip.status === 'in_progress' ? <PlayCircle className="size-4" /> : <ExternalLink className="size-4" />}
              {draft || trip.status === 'in_progress' ? 'Continue' : 'Open Trip'}
            </Link>
            {onDuplicate && (
              <button type="button" className="tg-btn tg-btn-secondary tg-btn-sm" onClick={() => onDuplicate(trip)}>
                <Copy className="size-4" /> Duplicate
              </button>
            )}
            {onFavorite && (
              <button type="button" className="tg-btn tg-btn-secondary tg-btn-sm" onClick={() => onFavorite(trip)}>
                <Heart className={cn('size-4', trip.is_favorite && 'fill-danger text-danger')} /> Favorite
              </button>
            )}
            {onDelete && (
              <button type="button" className="tg-btn tg-btn-danger tg-btn-sm" onClick={() => onDelete(trip)}>
                <Trash2 className="size-4" /> Delete
              </button>
            )}
          </div>
        )}
      </div>
    </article>
  )
}
