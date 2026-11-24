/**
 * Fetch wrapper for the TravelGraph API.
 * - cookie session (credentials: include) through the Vite /api proxy
 * - CSRF token from GET /auth/me (also returned by login/signup) sent as X-CSRF-Token on writes
 * - one transparent CSRF refresh + retry; 401 notifies the auth layer
 */
export const API_BASE = '/api/v1'

export class ApiError extends Error {
  status: number
  code?: string
  constructor(status: number, message: string, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

let csrfToken: string | null = null
export function setCsrfToken(token: string | null | undefined): void {
  csrfToken = token ?? null
}
export function getCsrfToken(): string | null {
  return csrfToken
}

type UnauthorizedHandler = () => void
let onUnauthorized: UnauthorizedHandler | null = null
export function setUnauthorizedHandler(fn: UnauthorizedHandler | null): void {
  onUnauthorized = fn
}

type Query = Record<string, string | number | boolean | null | undefined>

export function buildQuery(params?: Query): string {
  if (!params) return ''
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue
    sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

interface RequestOptions {
  method?: string
  body?: unknown
  query?: Query
  /** skip the global 401 handler (used by login / me probes) */
  silent401?: boolean
  signal?: AbortSignal
  raw?: boolean
}

async function parseError(res: Response): Promise<ApiError> {
  let message = `Request failed (${res.status})`
  let code: string | undefined
  try {
    const data = await res.json()
    if (typeof data?.detail === 'string') message = data.detail
    else if (Array.isArray(data?.detail) && data.detail[0]?.msg) message = String(data.detail[0].msg)
    code = data?.code
  } catch {
    /* non-JSON body */
  }
  return new ApiError(res.status, message, code)
}

async function refreshCsrf(): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/me`, { credentials: 'include' })
  if (res.ok) {
    const me = await res.json()
    setCsrfToken(me.csrf_token)
  }
}

async function doFetch(path: string, opts: RequestOptions): Promise<Response> {
  const method = (opts.method ?? 'GET').toUpperCase()
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
  if (method !== 'GET' && method !== 'HEAD' && csrfToken) headers['X-CSRF-Token'] = csrfToken
  return fetch(`${API_BASE}${path}${buildQuery(opts.query)}`, {
    method,
    headers,
    credentials: 'include',
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    signal: opts.signal,
  })
}

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const method = (opts.method ?? 'GET').toUpperCase()
  let res = await doFetch(path, opts)

  if (res.status === 403 && method !== 'GET' && !path.startsWith('/auth/login')) {
    // CSRF token may be stale (new session / server restart): refresh once and retry.
    await refreshCsrf()
    res = await doFetch(path, opts)
  }
  if (!res.ok) {
    if (res.status === 401 && !opts.silent401) onUnauthorized?.()
    throw await parseError(res)
  }
  if (opts.raw) return res as unknown as T
  if (res.status === 204) return undefined as T
  const text = await res.text()
  return (text ? JSON.parse(text) : undefined) as T
}

export const api = {
  get: <T>(path: string, query?: Query, o?: Pick<RequestOptions, 'signal' | 'silent401'>) =>
    request<T>(path, { query, ...o }),
  post: <T>(path: string, body?: unknown, o?: Pick<RequestOptions, 'silent401' | 'query'>) =>
    request<T>(path, { method: 'POST', body: body ?? {}, ...o }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body: body ?? {} }),
  delete: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'DELETE', body }),
  /** Download a text/CSV endpoint; returns the body text. */
  text: async (path: string, query?: Query): Promise<string> => {
    const res = await request<Response>(path, { query, raw: true })
    return res.text()
  },
}
