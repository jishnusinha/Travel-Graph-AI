import { describe, expect, it } from 'vitest'
import { countTrips, filterTrips, matchesFilter, matchesQuery, sortTrips } from './tripFilters'
import type { TripListItem } from './types'

const base: TripListItem = {
  id: '1', title: 'Goa Getaway', plan_title: 'Goa Escape Plan', destination: 'Goa', travelers: 2, budget_inr: 35000,
  estimated_cost_inr: 34850, status: 'completed', is_favorite: false, cover_image: '', start_date: '2027-01-12',
  end_date: '2027-01-16', created_at: '2026-10-01T00:00:00Z', day_count: 5,
}
const trips: TripListItem[] = [
  base,
  { ...base, id: '2', title: 'Manali Break', plan_title: '', destination: 'Manali', status: 'draft', is_favorite: true, budget_inr: 52000, start_date: null, created_at: '2026-11-01T00:00:00Z' },
  { ...base, id: '3', title: 'Jaipur Weekend', plan_title: '', destination: 'Jaipur', status: 'in_progress', budget_inr: 20000, start_date: '2026-12-05', created_at: '2026-09-01T00:00:00Z' },
]

describe('trip filter helpers', () => {
  it('filters by status and favorites', () => {
    expect(matchesFilter(trips[0], 'completed')).toBe(true)
    expect(matchesFilter(trips[0], 'draft')).toBe(false)
    expect(matchesFilter(trips[1], 'favorite')).toBe(true)
    expect(filterTrips(trips, { q: '', filter: 'in_progress', sort: 'recent' }).map((t) => t.id)).toEqual(['3'])
  })

  it('searches title, destination and plan title case-insensitively', () => {
    expect(matchesQuery(trips[0], 'goa')).toBe(true)
    expect(matchesQuery(trips[0], 'ESCAPE')).toBe(true)
    expect(matchesQuery(trips[1], 'jaipur')).toBe(false)
    expect(matchesQuery(trips[1], '  ')).toBe(true)
  })

  it('sorts by recency, title, budget and puts undated trips last by start date', () => {
    expect(sortTrips(trips, 'recent').map((t) => t.id)).toEqual(['2', '1', '3'])
    expect(sortTrips(trips, 'oldest').map((t) => t.id)).toEqual(['3', '1', '2'])
    expect(sortTrips(trips, 'title').map((t) => t.id)).toEqual(['1', '3', '2'].sort((a, b) => trips.find((t) => t.id === a)!.title.localeCompare(trips.find((t) => t.id === b)!.title)))
    expect(sortTrips(trips, 'budget').map((t) => t.id)).toEqual(['2', '1', '3'])
    expect(sortTrips(trips, 'start_date').map((t) => t.id)).toEqual(['3', '1', '2'])
  })

  it('does not mutate the input array', () => {
    const copy = [...trips]
    sortTrips(trips, 'budget')
    expect(trips).toEqual(copy)
  })

  it('counts per filter', () => {
    expect(countTrips(trips)).toEqual({ all: 3, completed: 1, in_progress: 1, draft: 1, favorite: 1 })
  })
})
