import { lazy, Suspense } from 'react'
import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import { Compass } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { FullScreenLoader, ProtectedRoute, PublicOnlyRoute } from '@/components/routing/ProtectedRoute'

const LoginPage = lazy(() => import('@/pages/auth/LoginPage'))
const SignupPage = lazy(() => import('@/pages/auth/SignupPage'))
const ForgotPasswordPage = lazy(() => import('@/pages/auth/ForgotPasswordPage'))
const ResetPasswordPage = lazy(() => import('@/pages/auth/ResetPasswordPage'))
const OnboardingPage = lazy(() => import('@/pages/auth/OnboardingPage'))
const DashboardPage = lazy(() => import('@/pages/DashboardPage'))
const NewTripPage = lazy(() => import('@/pages/trips/NewTripPage'))
const TripsPage = lazy(() => import('@/pages/trips/TripsPage'))
const TripDetailPage = lazy(() => import('@/pages/trips/TripDetailPage'))
const EditTripPage = lazy(() => import('@/pages/trips/EditTripPage'))
const SettingsPage = lazy(() => import('@/pages/SettingsPage'))
const StudioPage = lazy(() => import('@/pages/studio/StudioPage'))
const ReplayPage = lazy(() => import('@/pages/studio/ReplayPage'))
const EvaluationsPage = lazy(() => import('@/pages/evaluations/EvaluationsPage'))
const ComparePage = lazy(() => import('@/pages/evaluations/ComparePage'))
const CostsPage = lazy(() => import('@/pages/costs/CostsPage'))
const RunCostPage = lazy(() => import('@/pages/costs/RunCostPage'))

function NotFound() {
  return (
    <div className="grid min-h-[60vh] place-items-center p-6 text-center">
      <div>
        <span className="mx-auto grid size-16 place-items-center rounded-2xl bg-primary-soft text-primary"><Compass className="size-8" /></span>
        <h1 className="mt-4 text-3xl font-extrabold">Page not found</h1>
        <p className="mt-1 text-muted">The page you are looking for does not exist.</p>
        <Link to="/dashboard" className="tg-btn tg-btn-primary mt-5">Go to dashboard</Link>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<FullScreenLoader />}>
        <Routes>
          {/* Public */}
          <Route element={<PublicOnlyRoute />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          </Route>
          <Route path="/reset-password/:token" element={<ResetPasswordPage />} />

          {/* Onboarding needs a session but not a completed profile */}
          <Route element={<ProtectedRoute allowUnboarded />}>
            <Route path="/onboarding" element={<OnboardingPage />} />
          </Route>

          {/* Authenticated shell: light workspace + dark intelligence workspace */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/trips/new" element={<NewTripPage />} />
              <Route path="/trips" element={<TripsPage />} />
              <Route path="/trips/:tripId" element={<TripDetailPage />} />
              <Route path="/trips/:tripId/edit" element={<EditTripPage />} />
              <Route path="/settings" element={<SettingsPage />} />

              <Route path="/studio" element={<StudioPage />} />
              <Route path="/studio/runs/:runId" element={<StudioPage />} />
              <Route path="/studio/runs/:runId/replay" element={<ReplayPage />} />
              <Route path="/evaluations" element={<EvaluationsPage />} />
              <Route path="/evaluations/compare" element={<ComparePage />} />
              <Route path="/costs" element={<CostsPage />} />
              <Route path="/costs/runs/:runId" element={<RunCostPage />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Route>

          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
