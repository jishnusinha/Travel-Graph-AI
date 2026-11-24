import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { LogIn, Lock, Mail, Loader2 } from 'lucide-react'
import { AuthSplitLayout } from '@/components/auth/AuthSplitLayout'
import { OAuthButtons } from '@/components/auth/OAuthButtons'
import { Field, PasswordField } from '@/components/ui/Field'
import { useAuth } from '@/context/AuthContext'
import { ApiError } from '@/lib/api'
import { loginSchema, type LoginForm } from '@/lib/validation'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '', remember_me: true },
  })

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null)
    try {
      const user = await login(values)
      navigate(user.onboarding_completed ? (from ?? '/dashboard') : '/onboarding', { replace: true })
    } catch (e) {
      setServerError(
        e instanceof ApiError
          ? e.status === 429
            ? 'Too many attempts. Please wait a moment and try again.'
            : e.message
          : 'Could not reach the server. Is the backend running?',
      )
    }
  })

  return (
    <AuthSplitLayout>
      <h1 className="text-center text-[32px] font-extrabold lg:text-left">Welcome back</h1>
      <p className="mt-1 text-center text-muted lg:text-left">Sign in to your travel workspace</p>

      <form onSubmit={onSubmit} noValidate className="mt-7 space-y-4">
        {serverError && (
          <div role="alert" className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">
            {serverError}
          </div>
        )}
        <Field
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="Enter your email"
          icon={Mail}
          error={errors.email?.message}
          {...register('email')}
        />
        <PasswordField
          label="Password"
          autoComplete="current-password"
          placeholder="Enter your password"
          icon={Lock}
          error={errors.password?.message}
          {...register('password')}
        />
        <div className="flex items-center justify-between text-sm">
          <label className="flex cursor-pointer items-center gap-2">
            <input type="checkbox" className="size-4 accent-primary-strong" {...register('remember_me')} />
            Remember me
          </label>
          <Link to="/forgot-password" className="font-semibold text-primary-strong hover:underline">
            Forgot password?
          </Link>
        </div>
        <button type="submit" disabled={isSubmitting} className="tg-btn tg-btn-primary h-12 w-full">
          {isSubmitting ? <Loader2 className="size-4 animate-spin" /> : <LogIn className="size-4" />}
          {isSubmitting ? 'Signing in…' : 'Sign In'}
        </button>
        <button
          type="button"
          className="w-full text-center text-xs text-muted hover:text-primary-strong"
          onClick={() => {
            setValue('email', 'demo@travelgraph.local')
            setValue('password', 'TravelGraphDemo!2026')
          }}
        >
          Local demo: fill demo credentials
        </button>
      </form>

      <OAuthButtons />

      <p className="mt-6 text-center text-sm text-muted">
        New to TravelGraph AI?{' '}
        <Link to="/signup" className="font-semibold text-primary-strong hover:underline">
          Create an account
        </Link>
      </p>
    </AuthSplitLayout>
  )
}
