import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate } from 'react-router-dom'
import { Loader2, Lock, Mail, User, UserPlus } from 'lucide-react'
import { AuthSplitLayout } from '@/components/auth/AuthSplitLayout'
import { OAuthButtons } from '@/components/auth/OAuthButtons'
import { PasswordStrength } from '@/components/auth/PasswordStrength'
import { Field, PasswordField } from '@/components/ui/Field'
import { useAuth } from '@/context/AuthContext'
import { ApiError } from '@/lib/api'
import { signupSchema, type SignupForm } from '@/lib/validation'

export default function SignupPage() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
    defaultValues: { full_name: '', email: '', password: '', confirm_password: '', terms: false },
  })
  const password = watch('password')

  const onSubmit = handleSubmit(async ({ full_name, email, password, confirm_password }) => {
    setServerError(null)
    try {
      await signup({ full_name, email, password, confirm_password })
      navigate('/onboarding', { replace: true })
    } catch (e) {
      setServerError(e instanceof ApiError ? e.message : 'Could not reach the server. Is the backend running?')
    }
  })

  return (
    <AuthSplitLayout
      image="/assets/auth/beach.svg"
      headline={<>Your next story starts here.</>}
      tagline="Create your free local workspace and let a team of AI agents plan, validate and cost your next trip."
    >
      <h1 className="text-center text-[30px] font-extrabold lg:text-left">Create your account</h1>
      <p className="mt-1 text-center text-muted lg:text-left">Start planning smarter in a minute</p>

      <form onSubmit={onSubmit} noValidate className="mt-6 space-y-3.5">
        {serverError && (
          <div role="alert" className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">
            {serverError}
          </div>
        )}
        <Field label="Full name" autoComplete="name" placeholder="Your full name" icon={User} error={errors.full_name?.message} {...register('full_name')} />
        <Field label="Email" type="email" autoComplete="email" placeholder="Enter your email" icon={Mail} error={errors.email?.message} {...register('email')} />
        <div>
          <PasswordField label="Password" autoComplete="new-password" placeholder="Create a password" icon={Lock} error={errors.password?.message} {...register('password')} />
          <PasswordStrength password={password ?? ''} />
        </div>
        <PasswordField label="Confirm password" autoComplete="new-password" placeholder="Re-enter your password" icon={Lock} error={errors.confirm_password?.message} {...register('confirm_password')} />
        <div>
          <label className="flex cursor-pointer items-start gap-2 text-sm">
            <input type="checkbox" className="mt-0.5 size-4 accent-primary-strong" {...register('terms')} />
            <span>I agree to the Terms of Service and Privacy Policy (local demo).</span>
          </label>
          {errors.terms && <p className="tg-error-text">{errors.terms.message}</p>}
        </div>
        <button type="submit" disabled={isSubmitting} className="tg-btn tg-btn-primary h-12 w-full">
          {isSubmitting ? <Loader2 className="size-4 animate-spin" /> : <UserPlus className="size-4" />}
          {isSubmitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <OAuthButtons />

      <p className="mt-5 text-center text-sm text-muted">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-primary-strong hover:underline">
          Sign in
        </Link>
      </p>
    </AuthSplitLayout>
  )
}
