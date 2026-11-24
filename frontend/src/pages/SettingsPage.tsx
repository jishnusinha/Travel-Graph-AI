import { useEffect, useState, type ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { Brain, Download, KeyRound, Loader2, Mail, Monitor, Phone, Plane, Save, ShieldCheck, ShieldOff, Trash2, User as UserIcon, type LucideIcon } from 'lucide-react'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { DualRange } from '@/components/ui/DualRange'
import { Field, PasswordField } from '@/components/ui/Field'
import { PageHeader } from '@/components/ui/PageHeader'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/context/AuthContext'
import { api, ApiError } from '@/lib/api'
import type { Preferences, User } from '@/lib/types'
import { changePasswordSchema, type ChangePasswordForm } from '@/lib/validation'
import { cn, downloadText, formatDate, formatINR } from '@/lib/utils'

type TabId = 'profile' | 'travel' | 'ai' | 'privacy' | 'appearance'
const TABS: { id: TabId; label: string; hint: string; icon: LucideIcon }[] = [
  { id: 'profile', label: 'Profile & Account', hint: 'Your personal information and security', icon: UserIcon },
  { id: 'travel', label: 'Travel Preferences', hint: 'Default travel and trip planning options', icon: Plane },
  { id: 'ai', label: 'AI Preferences', hint: 'Model, reasoning and agent behavior', icon: Brain },
  { id: 'privacy', label: 'Privacy & Data', hint: 'Data export, usage and account controls', icon: ShieldCheck },
  { id: 'appearance', label: 'Appearance & Accessibility', hint: 'Theme, motion and notifications', icon: Monitor },
]
const INTERESTS = ['beaches', 'mountains', 'food', 'nature', 'culture', 'adventure', 'nightlife', 'wellness']
const STAYS = ['budget', 'mid-range', 'comfort', 'luxury']
const TRANSPORT = ['flights', 'trains', 'road', 'flexible']
const TIMEZONES = ['Asia/Kolkata', 'Asia/Dubai', 'Asia/Singapore', 'Europe/London', 'America/New_York', 'America/Los_Angeles', 'UTC']

export default function SettingsPage() {
  const [tab, setTab] = useState<TabId>('profile')
  return (
    <div className="mx-auto max-w-[1100px]">
      <PageHeader title="Settings & Profile" subtitle="Manage your account, travel preferences, AI configuration, privacy and experience." />
      <div className="grid gap-5 lg:grid-cols-[290px_1fr]">
        <nav aria-label="Settings sections" className="tg-card h-fit p-2">
          <ul className="flex gap-1 overflow-x-auto lg:flex-col">
            {TABS.map(({ id, label, hint, icon: Icon }) => (
              <li key={id} className="shrink-0 lg:shrink">
                <button type="button" aria-current={tab === id} onClick={() => setTab(id)} className={cn('flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left', tab === id ? 'bg-primary-soft' : 'hover:bg-primary-soft/50')}>
                  <Icon className={cn('mt-0.5 size-5 shrink-0', tab === id ? 'text-primary' : 'text-muted')} />
                  <span><span className="block whitespace-nowrap text-sm font-bold lg:whitespace-normal">{label}</span><span className="hidden text-xs text-muted lg:block">{hint}</span></span>
                </button>
              </li>
            ))}
          </ul>
        </nav>
        <div className="min-w-0">
          {tab === 'profile' && <ProfileTab />}
          {tab === 'travel' && <TravelTab />}
          {tab === 'ai' && <AiTab />}
          {tab === 'privacy' && <PrivacyTab />}
          {tab === 'appearance' && <AppearanceTab />}
        </div>
      </div>
    </div>
  )
}

function Section({ title, subtitle, icon: Icon, children }: { title: string; subtitle?: string; icon: LucideIcon; children: ReactNode }) {
  return (
    <section className="tg-card p-5 sm:p-6">
      <header className="mb-5 flex items-center gap-3 border-b border-line pb-4">
        <span className="grid size-11 place-items-center rounded-xl bg-primary-soft text-primary"><Icon className="size-5" /></span>
        <div><h2 className="text-lg font-bold">{title}</h2>{subtitle && <p className="text-sm text-muted">{subtitle}</p>}</div>
      </header>
      {children}
    </section>
  )
}

/* ---------------------------------------------------------------- profile */
const profileSchema = z.object({
  full_name: z.string().trim().min(2, 'Name must be at least 2 characters').max(200),
  phone: z.string().trim().max(40).optional(),
  timezone: z.string().min(1),
})
type ProfileForm = z.infer<typeof profileSchema>

function ProfileTab() {
  const { user, setUser, logout } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [showPw, setShowPw] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deletePw, setDeletePw] = useState('')
  const [busy, setBusy] = useState(false)

  const { register, handleSubmit, reset, formState: { errors, isSubmitting, isDirty } } = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: { full_name: user?.full_name ?? '', phone: user?.phone ?? '', timezone: user?.timezone ?? 'Asia/Kolkata' },
  })
  useEffect(() => {
    if (user) reset({ full_name: user.full_name, phone: user.phone ?? '', timezone: user.timezone })
  }, [user, reset])

  if (!user) return null
  const save = handleSubmit(async (v) => {
    try {
      const updated = await api.patch<User>('/me/profile', { full_name: v.full_name, phone: v.phone ?? '', timezone: v.timezone })
      setUser(updated)
      toast.success('Profile saved')
    } catch (e) {
      toast.error('Could not save profile', e instanceof ApiError ? e.message : undefined)
    }
  })

  const exportData = async () => {
    try {
      const data = await api.get<unknown>('/me/export')
      downloadText('travelgraph-export.json', JSON.stringify(data, null, 2), 'application/json')
      toast.success('Export ready', 'Your data was downloaded as JSON.')
    } catch (e) {
      toast.error('Export failed', e instanceof ApiError ? e.message : undefined)
    }
  }

  const deleteAccount = async () => {
    setBusy(true)
    try {
      await api.delete('/me', { password: deletePw })
      await logout()
      navigate('/login', { replace: true })
    } catch (e) {
      toast.error('Could not delete account', e instanceof ApiError ? e.message : undefined)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <Section title="Profile & Account" subtitle="Update your personal details and manage account security." icon={UserIcon}>
        <div className="mb-6 flex items-center gap-4">
          <span className="grid size-20 place-items-center rounded-full bg-gradient-to-br from-primary to-primary-strong text-2xl font-extrabold text-white">{user.avatar_initials}</span>
          <div>
            <p className="text-xl font-extrabold">{user.full_name}</p>
            <p className="text-sm text-muted">{user.email}</p>
            <p className="text-xs text-muted">Member since {formatDate(user.created_at)}{user.is_demo && ' · Local demo account'}</p>
          </div>
        </div>
        <form onSubmit={save} noValidate>
          <h3 className="mb-3 text-sm font-bold">Profile Information</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Full name" icon={UserIcon} error={errors.full_name?.message} {...register('full_name')} />
            <Field label="Email address" icon={Mail} value={user.email} readOnly hint="Email cannot be changed in the local demo." />
            <Field label="Phone number (optional)" icon={Phone} placeholder="+91 98765 43210" error={errors.phone?.message} {...register('phone')} />
            <div>
              <label htmlFor="tz" className="tg-label">Time zone</label>
              <select id="tz" className="tg-input" {...register('timezone')}>
                {[...new Set([user.timezone, ...TIMEZONES])].map((z) => <option key={z}>{z}</option>)}
              </select>
            </div>
          </div>
          <div className="mt-5 flex justify-end gap-2">
            <button type="button" className="tg-btn tg-btn-secondary" disabled={!isDirty} onClick={() => reset()}>Reset</button>
            <button type="submit" className="tg-btn tg-btn-primary" disabled={isSubmitting || !isDirty}>{isSubmitting ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />} Save Changes</button>
          </div>
        </form>

        <div className="mt-6 space-y-4 border-t border-line pt-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3"><KeyRound className="size-5 text-primary" /><div><p className="text-sm font-bold">Password & Security</p><p className="text-xs text-muted">Changing your password signs out your other devices.</p></div></div>
            <button type="button" className="tg-btn tg-btn-secondary tg-btn-sm" onClick={() => setShowPw((s) => !s)}><KeyRound className="size-4" /> Change Password</button>
          </div>
          {showPw && <ChangePasswordForm onDone={() => setShowPw(false)} />}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-surface-2 p-3">
            <div className="flex items-center gap-3"><ShieldOff className="size-5 text-muted" /><div><p className="text-sm font-bold">Two-Factor Authentication (2FA)</p><p className="text-xs text-muted">Not available in the local demo.</p></div></div>
            <div className="flex items-center gap-2"><span className="rounded-full border border-line px-2.5 py-1 text-xs font-semibold text-muted">Unavailable</span><button type="button" role="switch" aria-checked="false" aria-label="Two-factor authentication (unavailable)" disabled className="relative h-6 w-11 rounded-full bg-line opacity-60"><span className="absolute left-0.5 top-0.5 size-5 rounded-full bg-white shadow" /></button></div>
          </div>
        </div>

        <div className="mt-6 border-t border-line pt-5">
          <p className="mb-3 text-sm font-bold">Account Actions</p>
          <div className="flex flex-wrap gap-3">
            <button type="button" className="tg-btn tg-btn-secondary" onClick={exportData}><Download className="size-4" /> Export My Data</button>
            <button type="button" className="tg-btn tg-btn-danger" onClick={() => setConfirmDelete(true)}><Trash2 className="size-4" /> Delete Account</button>
          </div>
        </div>
      </Section>

      <ConfirmDialog open={confirmDelete} destructive title="Delete your account?" description="All trips, runs, evaluations and costs are removed permanently. This cannot be undone." confirmLabel="Delete account" busy={busy}
        onCancel={() => { setConfirmDelete(false); setDeletePw('') }} onConfirm={deleteAccount}>
        {user.is_demo ? (
          <p className="rounded-xl bg-warn-soft px-3 py-2 text-xs text-warn">Demo accounts cannot be deleted. Create your own account to try this.</p>
        ) : (
          <PasswordField label="Confirm with your password" value={deletePw} onChange={(e) => setDeletePw(e.target.value)} autoComplete="current-password" />
        )}
      </ConfirmDialog>
    </div>
  )
}

function ChangePasswordForm({ onDone }: { onDone: () => void }) {
  const toast = useToast()
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<ChangePasswordForm>({ resolver: zodResolver(changePasswordSchema) })
  const submit = handleSubmit(async (v) => {
    try {
      await api.post('/me/change-password', v)
      toast.success('Password changed', 'Other devices were signed out.')
      onDone()
    } catch (e) {
      toast.error('Could not change password', e instanceof ApiError ? e.message : undefined)
    }
  })
  return (
    <form onSubmit={submit} noValidate className="grid gap-3 rounded-xl border border-line p-4 sm:grid-cols-3">
      <PasswordField label="Current password" autoComplete="current-password" error={errors.current_password?.message} {...register('current_password')} />
      <PasswordField label="New password" autoComplete="new-password" error={errors.new_password?.message} {...register('new_password')} />
      <PasswordField label="Confirm new password" autoComplete="new-password" error={errors.confirm_password?.message} {...register('confirm_password')} />
      <div className="flex justify-end gap-2 sm:col-span-3">
        <button type="button" className="tg-btn tg-btn-ghost tg-btn-sm" onClick={onDone}>Cancel</button>
        <button type="submit" className="tg-btn tg-btn-primary tg-btn-sm" disabled={isSubmitting}>{isSubmitting && <Loader2 className="size-4 animate-spin" />} Update password</button>
      </div>
    </form>
  )
}

/* ----------------------------------------------------------- preferences */
function usePrefsForm() {
  const { user, setUser } = useAuth()
  const toast = useToast()
  const [saving, setSaving] = useState(false)
  const base = user?.preferences
  const [draft, setDraft] = useState<Preferences | null>(base ?? null)
  useEffect(() => setDraft(base ?? null), [base])
  const dirty = JSON.stringify(draft) !== JSON.stringify(base ?? null)
  const save = async () => {
    if (!draft) return
    setSaving(true)
    try {
      const { extra: _extra, ...rest } = draft
      void _extra
      const prefs = await api.patch<Preferences>('/me/preferences', rest)
      if (user) setUser({ ...user, preferences: prefs })
      toast.success('Preferences saved')
    } catch (e) {
      toast.error('Could not save preferences', e instanceof ApiError ? e.message : undefined)
    } finally {
      setSaving(false)
    }
  }
  return { draft, setDraft, dirty, save, saving, reset: () => setDraft(base ?? null) }
}

function PrefsFooter({ f }: { f: ReturnType<typeof usePrefsForm> }) {
  return (
    <div className="mt-6 flex justify-end gap-2 border-t border-line pt-4">
      <button type="button" className="tg-btn tg-btn-secondary" disabled={!f.dirty} onClick={f.reset}>Reset</button>
      <button type="button" className="tg-btn tg-btn-primary" disabled={!f.dirty || f.saving} onClick={f.save}>{f.saving ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />} Save Changes</button>
    </div>
  )
}

function TravelTab() {
  const f = usePrefsForm()
  const { draft, setDraft } = f
  if (!draft) return <Section title="Travel Preferences" icon={Plane}><p className="text-sm text-muted">Preferences are not available.</p></Section>
  const set = (patch: Partial<Preferences>) => setDraft({ ...draft, ...patch })
  const chip = (on: boolean) => cn('rounded-full border px-3.5 py-1.5 text-sm font-semibold capitalize', on ? 'border-primary-strong bg-primary-soft text-primary-ink' : 'border-line text-muted hover:border-primary/50')
  return (
    <Section title="Travel Preferences" subtitle="Defaults used to pre-fill every new trip." icon={Plane}>
      <div className="space-y-6">
        <fieldset><legend className="tg-label">Interests</legend><div className="flex flex-wrap gap-2">{INTERESTS.map((i) => <button key={i} type="button" aria-pressed={draft.interests.includes(i)} className={chip(draft.interests.includes(i))} onClick={() => set({ interests: draft.interests.includes(i) ? draft.interests.filter((x) => x !== i) : [...draft.interests, i] })}>{i}</button>)}</div></fieldset>
        <Field label="Home city" value={draft.home_city} onChange={(e) => set({ home_city: e.target.value })} />
        <div>
          <p className="tg-label">Typical budget per trip: <span className="text-primary-strong">{formatINR(draft.budget_min)} – {formatINR(draft.budget_max)}</span></p>
          <DualRange min={10000} max={150000} step={1000} low={draft.budget_min} high={draft.budget_max} onChange={(a, b) => set({ budget_min: a, budget_max: b })} labelLow="Minimum budget" labelHigh="Maximum budget" />
        </div>
        <fieldset><legend className="tg-label">Accommodation style</legend><div className="flex flex-wrap gap-2">{STAYS.map((s) => <button key={s} type="button" aria-pressed={draft.accommodation_style === s} className={chip(draft.accommodation_style === s)} onClick={() => set({ accommodation_style: s })}>{s}</button>)}</div></fieldset>
        <fieldset><legend className="tg-label">Preferred transport</legend><div className="flex flex-wrap gap-2">{TRANSPORT.map((s) => <button key={s} type="button" aria-pressed={draft.transport_preference === s} className={chip(draft.transport_preference === s)} onClick={() => set({ transport_preference: s })}>{s}</button>)}</div></fieldset>
      </div>
      <PrefsFooter f={f} />
    </Section>
  )
}

function AiTab() {
  const f = usePrefsForm()
  const health = useQuery({ queryKey: ['health'], queryFn: () => api.get<{ ai_mode: string; openai_configured: boolean; version: string }>('/health', undefined, { silent401: true }) })
  return (
    <Section title="AI Preferences" subtitle="How the agent team runs on this server." icon={Brain}>
      <dl className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-line bg-surface-2 p-4"><dt className="text-xs text-muted">Server AI mode</dt><dd className="text-lg font-bold capitalize">{health.isPending ? '…' : (health.data?.ai_mode ?? 'unknown')}</dd><dd className="text-xs text-muted">{health.data?.ai_mode === 'demo' ? 'Deterministic local agents. No API key and no paid usage.' : health.data?.openai_configured ? 'OpenAI configured on the server.' : 'OpenAI mode selected but not configured.'}</dd></div>
        <div className="rounded-xl border border-line bg-surface-2 p-4"><dt className="text-xs text-muted">Cost currency</dt><dd className="text-lg font-bold">USD</dd><dd className="text-xs text-muted">AI usage is shown in USD; trip budgets are INR.</dd></div>
      </dl>
      {f.draft && (
        <div className="mt-5">
          <label htmlFor="aipref" className="tg-label">Preferred mode</label>
          <select id="aipref" className="tg-input" value={f.draft.ai_mode_preference} onChange={(e) => f.setDraft({ ...f.draft!, ai_mode_preference: e.target.value })}>
            <option value="demo">Demo (local, free)</option>
            <option value="openai" disabled={!health.data?.openai_configured}>OpenAI (requires server key)</option>
          </select>
          <p className="mt-1 text-xs text-muted">The server&apos;s AI mode is configured by the administrator; this is stored as your preference.</p>
        </div>
      )}
      <PrefsFooter f={f} />
    </Section>
  )
}

function PrivacyTab() {
  const toast = useToast()
  const exportData = async () => {
    try {
      downloadText('travelgraph-export.json', JSON.stringify(await api.get<unknown>('/me/export'), null, 2), 'application/json')
      toast.success('Export ready')
    } catch (e) {
      toast.error('Export failed', e instanceof ApiError ? e.message : undefined)
    }
  }
  return (
    <Section title="Privacy & Data" subtitle="You own your data. Everything stays in your local database." icon={ShieldCheck}>
      <ul className="space-y-3 text-sm">
        <li className="rounded-xl border border-line p-4">Trips, agent runs, evaluations and costs are stored locally and are only visible to your account.</li>
        <li className="rounded-xl border border-line p-4">Sessions use an HTTP-only cookie plus a CSRF token. Changing your password signs out other devices.</li>
        <li className="rounded-xl border border-line p-4">Seeded demo charges and sample evaluations are illustrative and labelled as such.</li>
      </ul>
      <button type="button" className="tg-btn tg-btn-secondary mt-5" onClick={exportData}><Download className="size-4" /> Export My Data (JSON)</button>
    </Section>
  )
}

function AppearanceTab() {
  const f = usePrefsForm()
  return (
    <Section title="Appearance & Accessibility" subtitle="Theme, motion and notifications." icon={Monitor}>
      <div className="space-y-4">
        <div className="rounded-xl border border-line bg-surface-2 p-4 text-sm">
          <p className="font-bold">Dual Experience theme</p>
          <p className="text-muted">Travel pages use the light workspace; Agent Studio, Evaluation Lab and Cost Explorer use the dark intelligence workspace automatically.</p>
        </div>
        {f.draft && (
          <label className="flex cursor-pointer items-center justify-between gap-4 rounded-xl border border-line p-4">
            <span><span className="block text-sm font-bold">Reduce motion</span><span className="text-xs text-muted">Minimizes animations such as pulsing agent nodes.</span></span>
            <input type="checkbox" role="switch" className="size-5 accent-primary-strong" checked={f.draft.reduced_motion} onChange={(e) => f.setDraft({ ...f.draft!, reduced_motion: e.target.checked })} />
          </label>
        )}
      </div>
      <PrefsFooter f={f} />
    </Section>
  )
}
