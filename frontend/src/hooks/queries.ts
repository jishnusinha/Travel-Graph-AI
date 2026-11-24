import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type {
  AgentEvent,
  BenchmarkCase,
  BenchmarkOut,
  CompareOut,
  CostRunDetail,
  CostSummary,
  Dashboard,
  Evaluation,
  NodeDetail,
  Paginated,
  Run,
  RunGraph,
  RunLaunchOut,
  RunListItem,
  Trip,
  TripCreateIn,
  TripCreateOut,
  TripListItem,
  TripVersion,
} from '@/lib/types'

/* ------------------------------------------------------------------ keys */
export const qk = {
  dashboard: ['dashboard'] as const,
  trips: (params?: object) => ['trips', params ?? {}] as const,
  trip: (id: string) => ['trip', id] as const,
  versions: (id: string) => ['trip', id, 'versions'] as const,
  runs: (params?: object) => ['runs', params ?? {}] as const,
  run: (id: string) => ['run', id] as const,
  graph: (id: string) => ['run', id, 'graph'] as const,
  events: (id: string) => ['run', id, 'events'] as const,
  node: (id: string, node: string) => ['run', id, 'node', node] as const,
  evaluations: (params?: object) => ['evaluations', params ?? {}] as const,
  benchmarkCases: ['benchmark-cases'] as const,
  costs: (params?: object) => ['costs', params ?? {}] as const,
  runCost: (id: string) => ['costs', 'run', id] as const,
}

/* ------------------------------------------------------------- dashboard */
export const useDashboard = () =>
  useQuery({ queryKey: qk.dashboard, queryFn: () => api.get<Dashboard>('/analytics/dashboard') })

/* ----------------------------------------------------------------- trips */
/** Loads up to 100 trips; filtering/sorting/counts happen client-side (see lib/tripFilters). */
export const useTrips = () =>
  useQuery({
    queryKey: qk.trips({ all: true }),
    queryFn: async () => {
      const first = await api.get<Paginated<TripListItem>>('/trips', { page_size: 100, sort: 'recent' })
      return first
    },
  })

export const useTrip = (id: string | undefined, refetchInterval?: number | false) =>
  useQuery({
    queryKey: qk.trip(id ?? ''),
    queryFn: () => api.get<Trip>(`/trips/${id}`),
    enabled: !!id,
    refetchInterval,
  })

export const useTripVersions = (id: string | undefined) =>
  useQuery({
    queryKey: qk.versions(id ?? ''),
    queryFn: () => api.get<TripVersion[]>(`/trips/${id}/versions`),
    enabled: !!id,
  })

export function useCreateTrip() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: TripCreateIn) => api.post<TripCreateOut>('/trips', body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['trips'] })
      void qc.invalidateQueries({ queryKey: qk.dashboard })
      void qc.invalidateQueries({ queryKey: ['runs'] })
    },
  })
}

export function useUpdateTrip(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<Pick<Trip, 'title' | 'notes' | 'status' | 'destination' | 'origin' | 'travelers' | 'budget_inr' | 'start_date' | 'end_date' | 'prompt' | 'interests'>>) =>
      api.patch<Trip>(`/trips/${id}`, body),
    onSuccess: (trip) => {
      qc.setQueryData(qk.trip(id), trip)
      void qc.invalidateQueries({ queryKey: ['trips'] })
      void qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useTripActions() {
  const qc = useQueryClient()
  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ['trips'] })
    void qc.invalidateQueries({ queryKey: qk.dashboard })
  }
  return {
    favorite: useMutation({
      mutationFn: ({ id, value }: { id: string; value?: boolean }) =>
        api.post<TripListItem>(`/trips/${id}/favorite`, value === undefined ? undefined : { is_favorite: value }),
      onSuccess: (t) => {
        invalidate()
        void qc.invalidateQueries({ queryKey: qk.trip(t.id) })
      },
    }),
    duplicate: useMutation({
      mutationFn: (id: string) => api.post<Trip>(`/trips/${id}/duplicate`),
      onSuccess: invalidate,
    }),
    remove: useMutation({
      mutationFn: (id: string) => api.delete<{ message: string }>(`/trips/${id}`),
      onSuccess: invalidate,
    }),
    replan: useMutation({
      mutationFn: ({ id, prompt }: { id: string; prompt?: string }) =>
        api.post<RunLaunchOut>(`/trips/${id}/replan`, prompt ? { prompt } : undefined),
      onSuccess: () => {
        invalidate()
        void qc.invalidateQueries({ queryKey: ['runs'] })
      },
    }),
    restore: useMutation({
      mutationFn: ({ id, version }: { id: string; version: number }) =>
        api.post<Trip>(`/trips/${id}/versions/${version}/restore`),
      onSuccess: (t) => {
        qc.setQueryData(qk.trip(t.id), t)
        void qc.invalidateQueries({ queryKey: qk.versions(t.id) })
        invalidate()
      },
    }),
  }
}

/* ------------------------------------------------------------------ runs */
export const useRuns = (params: { status?: string; q?: string; page_size?: number; trip_id?: string } = {}) =>
  useQuery({
    queryKey: qk.runs(params),
    queryFn: () => api.get<Paginated<RunListItem>>('/runs', { page_size: 50, ...params }),
    placeholderData: keepPreviousData,
  })

export const useRun = (id: string | undefined, refetchInterval?: number | false) =>
  useQuery({
    queryKey: qk.run(id ?? ''),
    queryFn: () => api.get<Run>(`/runs/${id}`),
    enabled: !!id,
    refetchInterval,
  })

export const useRunGraph = (id: string | undefined) =>
  useQuery({
    queryKey: qk.graph(id ?? ''),
    queryFn: () => api.get<RunGraph>(`/runs/${id}/graph`),
    enabled: !!id,
  })

export const useRunEvents = (id: string | undefined) =>
  useQuery({
    queryKey: qk.events(id ?? ''),
    queryFn: () => api.get<AgentEvent[]>(`/runs/${id}/events`, { limit: 10000 }),
    enabled: !!id,
  })

export const useNodeDetail = (runId: string | undefined, nodeId: string | null, enabledExtra = true) =>
  useQuery({
    queryKey: qk.node(runId ?? '', nodeId ?? ''),
    queryFn: () => api.get<NodeDetail>(`/runs/${runId}/nodes/${nodeId}`),
    enabled: !!runId && !!nodeId && enabledExtra,
  })

/* ----------------------------------------------------------- evaluations */
export const useEvaluations = (params: { run_id?: string; kind?: string; page_size?: number } = {}) =>
  useQuery({
    queryKey: qk.evaluations(params),
    queryFn: () => api.get<Paginated<Evaluation>>('/evaluations', { page_size: 100, ...params }),
  })

export const useBenchmarkCases = () =>
  useQuery({ queryKey: qk.benchmarkCases, queryFn: () => api.get<BenchmarkCase[]>('/evaluations/benchmark/cases') })

export function useRunEvaluation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) => api.post<Evaluation>('/evaluations', { run_id: runId, kind: 'deterministic' }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['evaluations'] }),
  })
}

export function useRunBenchmark() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (slugs?: string[]) => api.post<BenchmarkOut>('/evaluations/benchmark', slugs ? { case_slugs: slugs } : {}),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['evaluations'] })
      void qc.invalidateQueries({ queryKey: ['runs'] })
      void qc.invalidateQueries({ queryKey: ['costs'] })
    },
  })
}

/** POST /evaluations/compare is read-only, so it is cached like a query. */
export const useCompareRuns = (runIds: string[]) => {
  const ids = [...new Set(runIds.filter(Boolean))]
  return useQuery({
    queryKey: ['compare', ids],
    queryFn: () => api.post<CompareOut>('/evaluations/compare', { run_ids: ids }),
    enabled: ids.length >= 2,
    placeholderData: keepPreviousData,
  })
}

/* ----------------------------------------------------------------- costs */
export interface CostFilters {
  days?: number
  model?: string
  agent?: string
  run_id?: string
}
export const useCosts = (filters: CostFilters) =>
  useQuery({
    queryKey: qk.costs(filters),
    queryFn: () => api.get<CostSummary>('/analytics/costs', { ...filters }),
    placeholderData: keepPreviousData,
  })

export const useRunCost = (id: string | undefined) =>
  useQuery({
    queryKey: qk.runCost(id ?? ''),
    queryFn: () => api.get<CostRunDetail>(`/analytics/costs/runs/${id}`),
    enabled: !!id,
  })
