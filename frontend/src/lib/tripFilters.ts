import type { TripListItem } from './types'

export type TripFilter = 'all' | 'completed' | 'in_progress' | 'draft' | 'favorite'
export type TripSort = 'recent' | 'oldest' | 'title' | 'budget' | 'start_date'

export interface TripFilterState {
  q: string
  filter: TripFilter
  sort: TripSort
}

export function matchesFilter(trip: TripListItem, filter: TripFilter): boolean {
  if (filter === 'all') return true
  if (filter === 'favorite') return trip.is_favorite
  return trip.status === filter
}

export function matchesQuery(trip: TripListItem, q: string): boolean {
  const needle = q.trim().toLowerCase()
  if (!needle) return true
  return [trip.title, trip.destination, trip.plan_title].some((f) => (f ?? '').toLowerCase().includes(needle))
}

export function sortTrips(trips: TripListItem[], sort: TripSort): TripListItem[] {
  const copy = [...trips]
  switch (sort) {
    case 'oldest':
      return copy.sort((a, b) => a.created_at.localeCompare(b.created_at))
    case 'title':
      return copy.sort((a, b) => a.title.toLowerCase().localeCompare(b.title.toLowerCase()))
    case 'budget':
      return copy.sort((a, b) => b.budget_inr - a.budget_inr)
    case 'start_date':
      // undated trips last
      return copy.sort((a, b) => {
        if (!a.start_date && !b.start_date) return 0
        if (!a.start_date) return 1
        if (!b.start_date) return -1
        return a.start_date.localeCompare(b.start_date)
      })
    case 'recent':
    default:
      return copy.sort((a, b) => b.created_at.localeCompare(a.created_at))
  }
}

export function filterTrips(trips: TripListItem[], state: TripFilterState): TripListItem[] {
  return sortTrips(
    trips.filter((t) => matchesFilter(t, state.filter) && matchesQuery(t, state.q)),
    state.sort,
  )
}

export function countTrips(trips: TripListItem[]): Record<TripFilter, number> {
  return {
    all: trips.length,
    completed: trips.filter((t) => t.status === 'completed').length,
    in_progress: trips.filter((t) => t.status === 'in_progress').length,
    draft: trips.filter((t) => t.status === 'draft').length,
    favorite: trips.filter((t) => t.is_favorite).length,
  }
}
