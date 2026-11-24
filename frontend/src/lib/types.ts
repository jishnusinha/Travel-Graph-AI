/** Types mirror backend/app/schemas/*.py */

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Preferences {
  interests: string[]
  home_city: string
  currency: string
  budget_min: number
  budget_max: number
  accommodation_style: string
  transport_preference: string
  ai_mode_preference: string
  theme: string
  reduced_motion: boolean
  extra: Record<string, unknown>
}

export interface User {
  id: string
  email: string
  full_name: string
  phone: string | null
  timezone: string
  avatar_initials: string
  onboarding_completed: boolean
  is_demo: boolean
  created_at: string
  preferences: Preferences | null
  csrf_token: string | null
}

export type TripStatus = 'draft' | 'in_progress' | 'completed'

export interface TripListItem {
  id: string
  title: string
  plan_title: string
  destination: string
  travelers: number
  budget_inr: number
  estimated_cost_inr: number
  status: TripStatus
  is_favorite: boolean
  cover_image: string
  start_date: string | null
  end_date: string | null
  created_at: string
  day_count: number
}

export interface TripActivity {
  id: string
  time_label: string
  category: string
  title: string
  description: string
  image: string
  estimated_cost_inr: number
  sort_order: number
  citation_ids?: string[]
  verification_status?: string
}

export interface TripDay {
  id: string
  day_number: number
  title: string
  summary: string
  area: string
  image: string
  meta: Record<string, string>
  activities: TripActivity[]
}

export interface TripRecommendation {
  id: string
  kind: string
  title: string
  body: string
}

export interface Trip extends Omit<TripListItem, 'day_count'> {
  slug: string
  origin: string
  prompt: string
  interests: string[]
  notes: string
  budget_breakdown: Record<string, number | string | null>
  transport: Record<string, unknown>
  accommodation: Record<string, unknown>
  current_version: number
  public_code: string | null
  updated_at: string
  days: TripDay[]
  recommendations: TripRecommendation[]
}

export interface TripVersion {
  id: string
  version: number
  change_summary: string
  created_at: string
}

export interface TripCreateIn {
  prompt: string
  title?: string
  destination?: string
  origin?: string
  start_date?: string | null
  end_date?: string | null
  travelers?: number
  budget_inr?: number
  interests?: string[]
  mode?: string
  launch_run?: boolean
}

export interface TripCreateOut {
  trip: Trip
  run_id: string | null
  run_public_id: string | null
}

export interface RunLaunchOut {
  trip_id: string
  run_id: string
  run_public_id: string
  revision_number: number
}

export type RunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'needs_clarification'

export interface RunListItem {
  id: string
  public_id: string
  trip_id: string | null
  trip_title: string | null
  status: RunStatus
  prompt: string
  ai_mode: string
  model_name: string
  started_at: string | null
  completed_at: string | null
  wall_time_ms: number
  input_tokens: number
  output_tokens: number
  total_cost_usd: number
  cost_provenance: string
  revision_number: number
  created_at: string
}

export interface Run extends Omit<RunListItem, 'trip_title'> {
  thread_id: string
  request_payload: Record<string, unknown>
  final_plan: Record<string, unknown>
  model_cost_usd: number
  tool_cost_usd: number
  error_message: string | null
}

export interface AgentEvent {
  id: string
  run_id: string
  seq: number
  ts: string
  type: string
  node_id: string | null
  status: string | null
  payload: Record<string, unknown>
}

export type NodeStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped' | 'warning'

export interface GraphNode {
  id: string
  label: string
  status: NodeStatus
  duration_ms: number | null
  role: string
  invocations: number
  started_at: string | null
  completed_at: string | null
  input_tokens: number
  output_tokens: number
  cost_usd: number | null
  summary: string | null
}

export interface GraphEdge {
  id: string
  source: string
  target: string
}

export interface RunGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
  current_node: string | null
  run_status: string | null
  last_seq: number
}

export interface NodeDetail {
  node_id: string
  status: NodeStatus
  events: AgentEvent[]
  model_invocations: {
    provider: string
    model: string
    input_tokens: number
    output_tokens: number
    cached_tokens: number
    estimated_cost_usd: number
    cost_status: string
    duration_ms: number
  }[]
  tool_invocations: {
    tool_name: string
    status: string
    duration_ms: number
    fee_usd: number
    provenance: string
    input_summary: unknown
    output_summary: unknown
  }[]
  cost_items: {
    category: string
    model: string | null
    tool_name: string | null
    amount_usd: number
    tokens_in: number
    tokens_out: number
    provenance: string
  }[]
  errors: string[]
}

export interface ActivityItem {
  run_id: string
  public_id: string
  trip_id: string | null
  trip_title: string | null
  status: RunStatus
  model_name: string
  wall_time_ms: number
  total_cost_usd: number
  completed_at: string | null
  cost_provenance: string
}

export interface Dashboard {
  greeting_name: string
  trips_planned: number
  trips_completed: number
  trips_in_progress: number
  trips_draft: number
  agent_runs: number
  avg_plan_quality: number | null
  total_ai_cost_usd: number
  recent_trips: TripListItem[]
  agent_activity: ActivityItem[]
  provenance: string
}

export interface EvaluationMetric {
  name: string
  value: number | null
  unit: string
  weight: number
  provenance: string
  status: string
  details: Record<string, unknown>
}

export interface Evaluation {
  id: string
  run_id: string
  run_public_id: string | null
  kind: string
  label: string
  overall_score: number | null
  status: string
  rubric_version: string
  is_demo_fixture: boolean
  summary: string
  judge_model: string | null
  judge_prompt_version: string | null
  metrics: EvaluationMetric[]
  evidence: { metric_name: string; snippet: string; source_ref: string }[]
  created_at: string
  run: Run | null
}

export interface CompareRun {
  run_id: string
  public_id: string
  status: string
  model_name: string
  ai_mode: string
  wall_time_ms: number
  total_cost_usd: number
  input_tokens: number
  output_tokens: number
  evaluations: Evaluation[]
  metrics: Record<string, number | null>
  overall_by_kind: Record<string, number | null>
  is_demo_fixture: boolean
}

export interface CompareOut {
  baseline_run_id: string
  runs: CompareRun[]
  metric_names: string[]
  metric_units: Record<string, string>
  metric_provenance: Record<string, string>
  deltas: Record<string, Record<string, number | null>>
  missing: { run_id: string; public_id: string; metric: string }[]
  notes: string[]
}

export interface BenchmarkCase {
  slug: string
  title: string
  prompt: string
  expected: Record<string, unknown>
  tags: string[]
}

export interface BenchmarkOut {
  total: number
  passed: number
  failed: number
  provenance: string
  results: {
    slug: string
    title: string
    run_id: string | null
    run_public_id: string | null
    run_status: string
    evaluation_id: string | null
    overall_score: number | null
    passed: boolean
    checks: Record<string, unknown>[]
    flags: string[]
  }[]
}

export interface CostAgentRow {
  agent: string
  cost_usd: number
  model_cost_usd: number
  tool_cost_usd: number
  tokens_in: number
  tokens_out: number
  share_pct: number
}

export interface CostModelRow {
  model: string
  cost_usd: number
  tokens_in: number
  tokens_out: number
  calls: number
  share_pct: number
  is_tool?: boolean
}

export interface CostSummary {
  total_cost_usd: number
  total_tokens: number
  input_tokens: number
  output_tokens: number
  avg_cost_per_run_usd: number
  by_agent: CostAgentRow[]
  by_model: CostModelRow[]
  trend: {
    date: string
    cost_usd: number
    model_cost_usd: number
    tool_cost_usd: number
    tokens: number
    runs: number
  }[]
  provenance: string
  currency: string
  model_cost_usd: number
  tool_cost_usd: number
  run_count: number
  unpriced_run_count: number
  filters: Record<string, unknown>
  note: string
}

export interface CostLineItem {
  category: string
  agent_role: string | null
  model: string | null
  tool_name: string | null
  amount_usd: number
  tokens_in: number
  tokens_out: number
  provenance: string
  occurred_at: string
}

export interface CostRunDetail {
  run: Run
  line_items: CostLineItem[]
  by_agent: CostAgentRow[]
  by_model: CostModelRow[]
  tools: {
    tool_name: string
    node_id: string
    calls: number
    fee_usd: number
    duration_ms: number
    provenance: string
    failed: number
  }[]
  waterfall: {
    node: string
    start_ms: number | null
    end_ms: number | null
    duration_ms: number | null
    attempts: number
    cost_usd: number
    cumulative_cost_usd: number
  }[]
  provenance: string
  currency: string
  reconciliation: {
    line_items_total_usd: number
    run_total_usd: number
    difference_usd: number
    reconciled: boolean
    tokens_in_items: number
    tokens_out_items: number
    tokens_reconciled: boolean
  }
  wall_time_ms: number
  note: string
}
