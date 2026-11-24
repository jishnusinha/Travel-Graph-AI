import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2, KeyRound, Loader2, Lock, XCircle } from 'lucide-react'
import { AuthSplitLayout } from '@/components/auth/AuthSplitLayout'
import { PasswordStrength } from '@/components/auth/PasswordStrength'
import { PasswordField } from '@/components/ui/Field'
import { api, ApiError } from '@/lib/api'
import { resetSchema, type ResetForm } from '@/lib/validation'

type TokenState = 'checking' | 'valid' | 'invalid'

export default function ResetPasswordPage() {
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const [tokenState, setTokenState] = useState<TokenState>('checking')
  const [done, setDone] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ResetForm>({ resolver: zodResolver(resetSchema), defaultValues: { password: '', confirm_password: '' } })
  const password = watch('password')

  useEffect(() => {
    let alive = true
    api
      .post<{ valid: boolean }>('/auth/reset-password/validate', { token }, { silent401: true })
      .then((r) => alive && setTokenState(r.valid ? 'valid' : 'invalid'))
      .catch(() => alive && setTokenState('invalid'))
    return () => {
      alive = false
    }
  }, [token])

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null)
    try {
      await api.post('/auth/reset-password', { token, ...values }, { silent401: true })
      setDone(true)
      window.setTimeout(() => navigate('/login', { replace: true }), 2500)
    } catch (e) {
      setServerError(e instanceof ApiError ? e.message : 'Could not reach the server.')
    }
  })

  return (
    <AuthSplitLayout
      image="/assets/auth/lake.svg"
      headline={<>Choose a new password.</>}
      tagline="Use a strong password you do not use anywhere else."
      features={false}
    >
      {tokenState === 'checking' && (
        <div className="py-16 text-center" role="status">
          <Loader2 className="mx-auto size-8 animate-spin text-primary" />
          <p className="mt-3 text-sm text-muted">Verifying your reset link…</p>
        </div>
      )}
      {tokenState === 'invalid' && (
        <div className="text-center" role="alert">
          <span className="mx-auto grid size-16 place-items-center rounded-full bg-danger-soft text-danger">
            <XCircle className="size-8" />
          </span>
          <h1 className="mt-5 text-2xl font-extrabold">Link expired or invalid</h1>
          <p className="mt-2 text-sm text-muted">Reset links work once and expire after 30 minutes.</p>
          <Link to="/forgot-password" className="tg-btn tg-btn-primary mt-6 w-full">
            Request a new link
          </Link>
        </div>
      )}
      {tokenState === 'valid' && !done && (
        <>
          <h1 className="text-center text-[30px] font-extrabold lg:text-left">Reset password</h1>
          <p className="mt-1 text-center text-muted lg:text-left">Create a new password for your account.</p>
          <form onSubmit={onSubmit} noValidate className="mt-6 space-y-4">
            {serverError && (
              <div role="alert" className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">
                {serverError}
              </div>
            )}
            <div>
              <PasswordField label="New password" autoComplete="new-password" placeholder="Create a password" icon={Lock} error={errors.password?.message} {...register('password')} />
              <PasswordStrength password={password ?? ''} />
            </div>
            <PasswordField label="Confirm new password" autoComplete="new-password" placeholder="Re-enter your password" icon={Lock} error={errors.confirm_password?.message} {...register('confirm_password')} />
            <button type="submit" disabled={isSubmitting} className="tg-btn tg-btn-primary h-12 w-full">
              {isSubmitting ? <Loader2 className="size-4 animate-spin" /> : <KeyRound className="size-4" />}
              Update password
            </button>
          </form>
        </>
      )}
      {done && (
        <div className="text-center" role="status">
          <span className="mx-auto grid size-16 place-items-center rounded-full bg-mint-soft text-mint">
            <CheckCircle2 className="size-8" />
          </span>
          <h1 className="mt-5 text-2xl font-extrabold">Password updated</h1>
          <p className="mt-2 text-sm text-muted">All other sessions were signed out. Redirecting to sign in…</p>
          <Link to="/login" className="tg-btn tg-btn-primary mt-6 w-full">
            Sign in now
          </Link>
        </div>
      )}
    </AuthSplitLayout>
  )
}
