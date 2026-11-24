import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, Loader2, Mail, Send } from 'lucide-react'
import { AuthSplitLayout } from '@/components/auth/AuthSplitLayout'
import { Field } from '@/components/ui/Field'
import { api, ApiError } from '@/lib/api'
import { forgotSchema, type ForgotForm } from '@/lib/validation'

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState<string | null>(null)
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotForm>({ resolver: zodResolver(forgotSchema), defaultValues: { email: '' } })

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null)
    try {
      const res = await api.post<{ message: string }>('/auth/forgot-password', values, { silent401: true })
      setSent(res.message)
    } catch (e) {
      setServerError(e instanceof ApiError ? e.message : 'Could not reach the server.')
    }
  })

  return (
    <AuthSplitLayout
      image="/assets/auth/lake.svg"
      headline={<>Locked out? No worries.</>}
      tagline="We will send a single-use link to reset your password."
      features={false}
    >
      {sent ? (
        <div className="text-center" role="status">
          <span className="mx-auto grid size-16 place-items-center rounded-full bg-mint-soft text-mint">
            <CheckCircle2 className="size-8" />
          </span>
          <h1 className="mt-5 text-2xl font-extrabold">Check your inbox</h1>
          <p className="mt-2 text-sm text-muted">{sent}</p>
          <p className="mt-4 rounded-xl border border-line bg-surface-2 px-4 py-3 text-left text-xs text-muted">
            <strong className="text-ink">Local demo:</strong> no email is sent. The reset link is printed in the backend
            terminal and saved to <code className="tg-mono">data/dev_reset_inbox.jsonl</code>.
          </p>
          <Link to="/login" className="tg-btn tg-btn-secondary mt-6 w-full">
            <ArrowLeft className="size-4" /> Back to sign in
          </Link>
        </div>
      ) : (
        <>
          <h1 className="text-center text-[30px] font-extrabold lg:text-left">Forgot password?</h1>
          <p className="mt-1 text-center text-muted lg:text-left">Enter your email and we will send a reset link.</p>
          <form onSubmit={onSubmit} noValidate className="mt-7 space-y-4">
            {serverError && (
              <div role="alert" className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">
                {serverError}
              </div>
            )}
            <Field label="Email" type="email" autoComplete="email" placeholder="Enter your email" icon={Mail} error={errors.email?.message} {...register('email')} />
            <button type="submit" disabled={isSubmitting} className="tg-btn tg-btn-primary h-12 w-full">
              {isSubmitting ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
              Send reset link
            </button>
          </form>
          <Link to="/login" className="mt-6 flex items-center justify-center gap-1.5 text-sm font-semibold text-primary-strong hover:underline">
            <ArrowLeft className="size-4" /> Back to sign in
          </Link>
        </>
      )}
    </AuthSplitLayout>
  )
}
