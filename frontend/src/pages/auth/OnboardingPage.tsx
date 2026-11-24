import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  Coins,
  Compass,
  Heart,
  Landmark,
  Loader2,
  MapPin,
  Mountain,
  Music,
  Sailboat,
  Sparkles,
  Sprout,
  Target,
  Umbrella,
  Utensils,
  Wallet,
  type LucideIcon,
} from 'lucide-react'
import { Logo } from '@/components/ui/Logo'
import { DualRange } from '@/components/ui/DualRange'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/context/AuthContext'
import { api, ApiError } from '@/lib/api'
import type { User } from '@/lib/types'
import { cn, formatINR } from '@/lib/utils'

const INTERESTS: { id: string; label: string; hint: string; icon: LucideIcon; grad: string }[] = [
  { id: 'beaches', label: 'Beaches', hint: 'Sun, sand and coastal escapes', icon: Umbrella, grad: 'from-sky-400 to-cyan-300' },
  { id: 'mountains', label: 'Mountains', hint: 'Hills, treks and scenic views', icon: Mountain, grad: 'from-indigo-400 to-sky-300' },
  { id: 'food', label: 'Food', hint: 'Local cuisines and food trails', icon: Utensils, grad: 'from-orange-400 to-amber-300' },
  { id: 'nature', label: 'Nature', hint: 'Forests, wildlife and serene places', icon: Sprout, grad: 'from-emerald-400 to-teal-300' },
  { id: 'culture', label: 'Culture', hint: 'Heritage, forts and history', icon: Landmark, grad: 'from-rose-400 to-orange-300' },
  { id: 'adventure', label: 'Adventure', hint: 'Rafting, trekking and thrills', icon: Compass, grad: 'from-violet-400 to-fuchsia-300' },
  { id: 'nightlife', label: 'Nightlife', hint: 'Music, bars and late evenings', icon: Music, grad: 'from-fuchsia-500 to-indigo-400' },
  { id: 'wellness', label: 'Wellness', hint: 'Yoga, spas and slow travel', icon: Sailboat, grad: 'from-teal-400 to-lime-300' },
]
const STAYS = ['budget', 'mid-range', 'comfort', 'luxury']
const TRANSPORT = ['flights', 'trains', 'road', 'flexible']
const CITIES = ['Kolkata, India', 'Delhi, India', 'Mumbai, India', 'Bengaluru, India', 'Chennai, India', 'Hyderabad, India', 'Pune, India']

export default function OnboardingPage() {
  const { user, setUser } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const prefs = user?.preferences
  const [step, setStep] = useState(1)
  const [busy, setBusy] = useState(false)
  const [interests, setInterests] = useState<string[]>(prefs?.interests?.map(String) ?? ['beaches', 'mountains'])
  const [home, setHome] = useState(prefs?.home_city ?? 'Kolkata, India')
  const [lo, setLo] = useState(prefs?.budget_min ?? 20000)
  const [hi, setHi] = useState(prefs?.budget_max ?? 50000)
  const [stay, setStay] = useState(prefs?.accommodation_style ?? 'mid-range')
  const [transport, setTransport] = useState(prefs?.transport_preference ?? 'flights')

  const finish = async (skipped: boolean) => {
    setBusy(true)
    try {
      const updated = await api.post<User>('/me/onboarding/complete', {
        skipped,
        preferences: skipped
          ? undefined
          : {
              interests,
              home_city: home,
              currency: 'INR',
              budget_min: lo,
              budget_max: hi,
              accommodation_style: stay,
              transport_preference: transport,
            },
      })
      setUser(updated)
      toast.success(skipped ? 'Skipped for now' : 'Preferences saved', 'You can change these anytime in Settings.')
      navigate('/dashboard', { replace: true })
    } catch (e) {
      toast.error('Could not save preferences', e instanceof ApiError ? e.message : undefined)
    } finally {
      setBusy(false)
    }
  }

  const toggle = (id: string) => setInterests((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]))

  return (
    <div className="min-h-screen bg-wash p-3 sm:p-5">
      <header className="mx-auto mb-3 flex max-w-[1400px] items-center justify-between px-2">
        <Logo />
        <span className="hidden items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 text-sm font-semibold text-primary-ink sm:inline-flex">
          <Sparkles className="size-4" /> Personalize your travel experience
        </span>
      </header>
      <div className="mx-auto grid max-w-[1400px] overflow-hidden rounded-3xl bg-surface shadow-soft lg:min-h-[calc(100vh-7rem)] lg:grid-cols-[0.62fr_1fr]">
        <aside
          className="relative hidden flex-col p-10 text-white lg:flex"
          style={{ backgroundImage: 'url(/assets/auth/santorini.svg)', backgroundSize: 'cover', backgroundPosition: 'center' }}
        >
          <h2 className="font-serif text-5xl font-semibold leading-tight">
            Welcome to
            <br />
            TravelGraph AI
          </h2>
          <span className="my-6 h-1 w-14 rounded-full bg-mint" />
          <p className="max-w-xs text-lg text-white/90">
            Your multi-agent AI travel partner for planning, optimizing and personalizing unforgettable trips.
          </p>
        </aside>

        <section className="flex flex-col p-6 sm:p-10">
          <div className="flex items-center justify-between border-b border-line pb-4 text-sm text-muted">
            <span>
              <strong className="text-ink">Step {step} of 3</strong> · Tell us about your travel preferences
            </span>
            <ol className="flex items-center gap-1" aria-label="Progress">
              {[1, 2, 3].map((n) => (
                <li key={n} className="flex items-center gap-1">
                  <span
                    className={cn(
                      'grid size-7 place-items-center rounded-full border text-xs font-bold',
                      n <= step ? 'border-primary-strong bg-primary-strong text-white' : 'border-line bg-surface text-muted',
                    )}
                  >
                    {n < step ? <Check className="size-3.5" /> : n}
                  </span>
                  {n < 3 && <span className={cn('h-px w-5', n < step ? 'bg-primary-strong' : 'bg-line')} />}
                </li>
              ))}
            </ol>
          </div>

          <div className="flex-1 pt-6">
            {step === 1 && (
              <div className="space-y-6">
                <div>
                  <h1 className="flex items-center gap-2 text-[26px] font-extrabold sm:text-3xl">
                    Let&apos;s personalize your travel experience <Sparkles className="size-6 text-primary" />
                  </h1>
                  <p className="mt-1 text-muted">A few quick preferences help our AI agents plan trips that you&apos;ll love.</p>
                </div>
                <div>
                  <h2 className="mb-1 flex items-center gap-2 text-base font-bold">
                    <Heart className="size-4 text-primary" /> What do you enjoy the most while traveling?
                  </h2>
                  <p className="mb-3 text-sm text-muted">Select one or more travel interests.</p>
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-4" role="group" aria-label="Travel interests">
                    {INTERESTS.map((it) => {
                      const on = interests.includes(it.id)
                      const Icon = it.icon
                      return (
                        <button
                          key={it.id}
                          type="button"
                          aria-pressed={on}
                          onClick={() => toggle(it.id)}
                          className={cn(
                            'overflow-hidden rounded-2xl border bg-surface text-left transition',
                            on ? 'border-primary-strong ring-2 ring-primary/30' : 'border-line hover:border-primary/50',
                          )}
                        >
                          <div className={cn('relative grid h-20 place-items-center bg-gradient-to-br text-white', it.grad)}>
                            <Icon className="size-9" aria-hidden />
                            <span
                              className={cn(
                                'absolute right-2 top-2 grid size-5 place-items-center rounded-md border',
                                on ? 'border-primary-strong bg-primary-strong text-white' : 'border-white/80 bg-white/30',
                              )}
                            >
                              {on && <Check className="size-3.5" />}
                            </span>
                          </div>
                          <div className="p-2.5">
                            <p className="text-sm font-bold">{it.label}</p>
                            <p className="text-[11px] leading-snug text-muted">{it.hint}</p>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="flex gap-3">
                    <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary-soft text-primary"><MapPin className="size-5" /></span>
                    <div className="flex-1">
                      <label htmlFor="home" className="text-sm font-bold">Your Home City</label>
                      <p className="mb-1.5 text-xs text-muted">Where do you usually travel from?</p>
                      <select id="home" value={home} onChange={(e) => setHome(e.target.value)} className="tg-input">
                        {[...new Set([home, ...CITIES])].map((c) => <option key={c}>{c}</option>)}
                      </select>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary-soft text-primary"><Coins className="size-5" /></span>
                    <div className="flex-1">
                      <label htmlFor="cur" className="text-sm font-bold">Preferred Currency</label>
                      <p className="mb-1.5 text-xs text-muted">For trip budgets and cost estimates</p>
                      <select id="cur" className="tg-input" defaultValue="INR" disabled aria-describedby="cur-note">
                        <option value="INR">INR – Indian Rupee (₹)</option>
                      </select>
                      <p id="cur-note" className="mt-1 text-[11px] text-muted">Trip budgets are in INR. AI usage costs are shown in USD.</p>
                    </div>
                  </div>
                </div>
                <div className="grid items-center gap-4 md:grid-cols-[1fr_220px]">
                  <div className="flex gap-3">
                    <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary-soft text-primary"><Wallet className="size-5" /></span>
                    <div className="flex-1">
                      <p className="text-sm font-bold">Your Typical Budget per Trip</p>
                      <p className="mb-5 text-xs text-muted">Select a comfortable budget range for your trips.</p>
                      <DualRange min={10000} max={100000} step={1000} low={lo} high={hi} onChange={(a, b) => { setLo(a); setHi(b) }} labelLow="Minimum budget" labelHigh="Maximum budget" />
                      <div className="mt-2 flex justify-between text-[11px] text-muted"><span>₹10,000</span><span>₹1,00,000+</span></div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 rounded-2xl bg-mint-soft p-4">
                    <Target className="size-6 shrink-0 text-mint" />
                    <div>
                      <p className="text-[11px] text-muted">Selected Range</p>
                      <p className="text-base font-extrabold">{formatINR(lo)} – {formatINR(hi)}</p>
                      <p className="text-[11px] text-muted">per trip</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-7">
                <div>
                  <h1 className="text-[26px] font-extrabold sm:text-3xl">How do you like to travel?</h1>
                  <p className="mt-1 text-muted">These defaults pre-fill every new trip plan.</p>
                </div>
                <fieldset>
                  <legend className="mb-2 flex items-center gap-2 text-base font-bold"><Building2 className="size-4 text-primary" /> Accommodation style</legend>
                  <div className="flex flex-wrap gap-2">
                    {STAYS.map((s) => (
                      <button key={s} type="button" aria-pressed={stay === s} onClick={() => setStay(s)}
                        className={cn('rounded-full border px-4 py-2 text-sm font-semibold capitalize', stay === s ? 'border-primary-strong bg-primary-soft text-primary-ink' : 'border-line hover:border-primary/50')}>
                        {s}
                      </button>
                    ))}
                  </div>
                </fieldset>
                <fieldset>
                  <legend className="mb-2 flex items-center gap-2 text-base font-bold"><Compass className="size-4 text-primary" /> Preferred transport</legend>
                  <div className="flex flex-wrap gap-2">
                    {TRANSPORT.map((s) => (
                      <button key={s} type="button" aria-pressed={transport === s} onClick={() => setTransport(s)}
                        className={cn('rounded-full border px-4 py-2 text-sm font-semibold capitalize', transport === s ? 'border-primary-strong bg-primary-soft text-primary-ink' : 'border-line hover:border-primary/50')}>
                        {s}
                      </button>
                    ))}
                  </div>
                </fieldset>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-5">
                <div>
                  <h1 className="text-[26px] font-extrabold sm:text-3xl">You&apos;re all set</h1>
                  <p className="mt-1 text-muted">Review your preferences, then start planning.</p>
                </div>
                <dl className="tg-card divide-y divide-line">
                  {[
                    ['Interests', interests.length ? interests.map((i) => INTERESTS.find((x) => x.id === i)?.label ?? i).join(', ') : 'None selected'],
                    ['Home city', home],
                    ['Budget range', `${formatINR(lo)} – ${formatINR(hi)} per trip`],
                    ['Accommodation', stay],
                    ['Transport', transport],
                    ['AI mode', 'Local demo (no API key needed)'],
                  ].map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-4 px-4 py-3 text-sm">
                      <dt className="text-muted">{k}</dt>
                      <dd className="text-right font-semibold capitalize">{v}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
          </div>

          <div className="mt-8 flex items-center justify-between gap-3">
            {step > 1 ? (
              <button type="button" className="tg-btn tg-btn-ghost" onClick={() => setStep((s) => s - 1)} disabled={busy}>
                <ArrowLeft className="size-4" /> Back
              </button>
            ) : <span />}
            <div className="flex gap-3">
              <button type="button" className="tg-btn tg-btn-secondary" onClick={() => finish(true)} disabled={busy}>
                Skip for now
              </button>
              {step < 3 ? (
                <button type="button" className="tg-btn tg-btn-primary min-w-36" onClick={() => setStep((s) => s + 1)}>
                  Continue <ArrowRight className="size-4" />
                </button>
              ) : (
                <button type="button" className="tg-btn tg-btn-primary min-w-36" onClick={() => finish(false)} disabled={busy}>
                  {busy ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />} Finish
                </button>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
