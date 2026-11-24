import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError, setCsrfToken, setUnauthorizedHandler } from '@/lib/api'
import type { User } from '@/lib/types'

export const ME_KEY = ['me'] as const

interface AuthValue {
  user: User | null
  /** true only on the very first session probe */
  loading: boolean
  login: (input: { email: string; password: string; remember_me: boolean }) => Promise<User>
  signup: (input: { full_name: string; email: string; password: string; confirm_password: string }) => Promise<User>
  logout: () => Promise<void>
  setUser: (u: User) => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthValue | null>(null)

async function fetchMe(): Promise<User | null> {
  try {
    const me = await api.get<User>('/auth/me', undefined, { silent401: true })
    setCsrfToken(me.csrf_token)
    return me
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      setCsrfToken(null)
      return null
    }
    throw e
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const { data, isPending } = useQuery({
    queryKey: ME_KEY,
    queryFn: fetchMe,
    staleTime: 5 * 60_000,
    retry: false,
  })

  const setUser = useCallback(
    (u: User | null) => {
      if (u) setCsrfToken(u.csrf_token)
      qc.setQueryData(ME_KEY, u)
    },
    [qc],
  )

  // A 401 anywhere (expired session) drops us back to the login screen.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setCsrfToken(null)
      qc.setQueryData(ME_KEY, null)
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== 'me' })
    })
    return () => setUnauthorizedHandler(null)
  }, [qc])

  const login = useCallback<AuthValue['login']>(
    async (input) => {
      const u = await api.post<User>('/auth/login', input, { silent401: true })
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== 'me' })
      setUser(u)
      return u
    },
    [qc, setUser],
  )

  const signup = useCallback<AuthValue['signup']>(
    async (input) => {
      const u = await api.post<User>('/auth/signup', input, { silent401: true })
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== 'me' })
      setUser(u)
      return u
    },
    [qc, setUser],
  )

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout', {}, { silent401: true })
    } catch {
      /* cookie is cleared server-side regardless; fall through */
    }
    setCsrfToken(null)
    qc.setQueryData(ME_KEY, null)
    qc.removeQueries({ predicate: (q) => q.queryKey[0] !== 'me' })
  }, [qc])

  const refresh = useCallback(async () => {
    await qc.invalidateQueries({ queryKey: ME_KEY })
  }, [qc])

  const value = useMemo<AuthValue>(
    () => ({ user: data ?? null, loading: isPending, login, signup, logout, setUser, refresh }),
    [data, isPending, login, signup, logout, setUser, refresh],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
