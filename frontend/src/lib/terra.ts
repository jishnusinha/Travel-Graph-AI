import { api } from './api'

export const PENDING_QUERY_KEY = 'terra.pendingQuery'
export const EXPLORE_QUERY_KEY = 'terra.exploreQuery'
const COMPARE_KEY = 'terra.compareIds'

export function stashPendingQuery(query: string): void {
  sessionStorage.setItem(PENDING_QUERY_KEY, query.trim().slice(0, 1000))
}

export function readPendingQuery(): string | null {
  return sessionStorage.getItem(PENDING_QUERY_KEY)
}

export function takePendingQuery(): string | null {
  const value = readPendingQuery()
  if (value) sessionStorage.removeItem(PENDING_QUERY_KEY)
  return value
}

export function rememberExploreQuery(query: string): void {
  sessionStorage.setItem(EXPLORE_QUERY_KEY, query)
}

export function readExploreQuery(): string {
  return sessionStorage.getItem(EXPLORE_QUERY_KEY) ?? ''
}

export function readCompareIds(): string[] {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(COMPARE_KEY) || '[]')
    return Array.isArray(parsed) ? parsed.slice(0, 3) : []
  } catch {
    return []
  }
}

export function toggleCompareId(current: string[], id: string): string[] {
  if (current.includes(id)) return current.filter((item) => item !== id)
  if (current.length >= 3) return current
  return [...current, id]
}

export function writeCompareIds(ids: string[]): void {
  sessionStorage.setItem(COMPARE_KEY, JSON.stringify(ids.slice(0, 3)))
}

export interface TerraEvidence {
  id: string
  chunk_id?: string
  title?: string
  section_path?: string
  excerpt?: string
  permalink?: string
  license?: string
  source_type?: string
  rank?: number
}

export interface TerraDestination {
  destination_id: string
  slug: string
  name: string
  region?: string
  summary?: string
  themes?: string[]
  source_status?: string
  coordinate_status?: string
  lat?: number | null
  lon?: number | null
  kind?: string
}

export interface DiscoveryResult {
  snapshot_id: string | null
  retrieval_run_id: string | null
  strategy_applied?: string
  embedding_kind?: string
  embedding_model?: string
  warnings?: string[]
  generation_mode?: string
  insufficient_evidence?: boolean
  results: Array<TerraDestination & {
    rank: number
    matched_preferences: string[]
    unknown_preferences: string[]
    evidence: TerraEvidence[]
    evidence_count: number
  }>
}

export interface KnowledgeStats {
  status: string
  snapshot_id: string | null
  destinations?: number
  documents?: number
  chunks?: number
  attractions?: number
  images?: number
  embedding_kind?: string
  embedding_model?: string
  capabilities?: Record<string, unknown>
  source_status_note?: string
}

export const terraApi = {
  stats: () => api.get<KnowledgeStats>('/knowledge/stats'),
  highlights: () => api.get<{ items: TerraDestination[]; status: string; snapshot_id: string | null }>('/knowledge/highlights'),
  destinations: (query?: { q?: string; region?: string }) =>
    api.get<{ items: TerraDestination[]; snapshot_id: string }>('/destinations', query),
  destination: (slug: string) => api.get<Record<string, unknown>>(`/destinations/${slug}`),
  search: (query: string, strategy?: string, filters?: Record<string, unknown>) =>
    api.post<DiscoveryResult>('/discovery/search', { query, strategy, filters: filters ?? {} }),
  ask: (slug: string, query: string) => api.post<Record<string, unknown>>(`/destinations/${slug}/ask`, { query }),
  compare: (destination_ids: string[]) => api.post<{ results: Array<Record<string, unknown>>; note: string }>('/destinations/compare', { destination_ids }),
  graph: (slug: string) => api.get<{ nodes: Array<Record<string, string>>; edges: Array<Record<string, unknown>>; note?: string }>(`/destinations/${slug}/graph`),
  save: (destination_id: string) => api.post<{ id: string; destination_id: string }>('/saved-destinations', { destination_id }),
  saved: () => api.get<{ items: Array<Record<string, string>> }>('/saved-destinations'),
  unsave: (id: string) => api.delete<{ deleted: boolean }>(`/saved-destinations/${id}`),
  retrieval: (query: string, strategy: string) => api.post<Record<string, unknown>>('/retrieval/search', { query, strategy }),
  benchmark: (strategies: string[]) => api.post<Record<string, unknown>>('/evaluations/retrieval', { strategies }),
  personalize: (consent: boolean, interests: string[]) => api.post('/me/personalization', { consent, interests }),
  forYou: () => api.get<DiscoveryResult>('/discovery/for-you'),
}
