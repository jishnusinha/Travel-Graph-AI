import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

export function FullScreenLoader() {
  return (
    <div className="grid h-full min-h-screen place-items-center bg-canvas" role="status" aria-label="Loading">
      <div className="flex flex-col items-center gap-3">
        <div className="size-10 animate-spin rounded-full border-4 border-primary/20 border-t-primary" />
        <p className="text-sm text-muted">Loading your workspace…</p>
      </div>
    </div>
  )
}

/** Requires an authenticated session. Users who haven't finished onboarding are sent there first. */
export function ProtectedRoute({ allowUnboarded = false }: { allowUnboarded?: boolean }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <FullScreenLoader />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  if (!user.onboarding_completed && !allowUnboarded) return <Navigate to="/onboarding" replace />
  return <Outlet />
}

/** Auth screens bounce signed-in users to the dashboard. */
export function PublicOnlyRoute() {
  const { user, loading } = useAuth()
  if (loading) return <FullScreenLoader />
  if (user) return <Navigate to={user.onboarding_completed ? '/dashboard' : '/onboarding'} replace />
  return <Outlet />
}
