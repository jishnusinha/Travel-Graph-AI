import { useEffect, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, Calendar, Home, IndianRupee, Lightbulb, Loader2, MapPin, Sparkles, Users, Workflow, Zap, SlidersHorizontal, LayoutList, Plane } from 'lucide-react'
import { CoverImage } from '@/components/ui/CoverImage'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/context/AuthContext'
import { useCreateTrip } from '@/hooks/queries'
import { AGENTS } from '@/lib/agents'
import { ApiError } from '@/lib/api'
import { tripPromptSchema, validateTripDates, type TripPromptForm } from '@/lib/validation'
import { cn } from '@/lib/utils'

const DESTINATIONS = ['Goa', 'Manali', 'Jaipur', 'Udaipur', 'Munnar', 'Kerala', 'Darjeeling', 'Rishikesh']
const INTERESTS = ['beaches', 'mountains', 'food', 'nature', 'culture', 'adventure', 'nightlife', 'wellness']

const IDEAS = [
  { title: 'Goa Beach Retreat', body: 'A 5-day beach vacation in Goa with food, nightlife and relaxation.', img: '/assets/destinations/goa.svg', destination: 'Goa', prompt: 'Plan a relaxing 5-day Goa trip from Kolkata for two people, with beaches, local food and a budget of ₹35,000.', travelers: 2, budget: 35000 },
  { title: 'Manali Adventure', body: 'A 6-day trip to Manali with nature, adventure and scenic stays.', img: '/assets/destinations/manali.svg', destination: 'Manali', prompt: 'Plan a 6-day Manali adventure from Delhi for four travelers with scenic stays and a budget of ₹52,000.', travelers: 4, budget: 52000 },
  { title: 'Udaipur Heritage', body: 'A 4-day cultural trip to Udaipur with palaces, lakes and local eats.', img: '/assets/destinations/udaipur.svg', destination: 'Udaipur', prompt: 'Plan a 4-day Udaipur heritage trip for two with palaces, lake views and local food under ₹38,000.', travelers: 2, budget: 38000 },
]

export default function NewTripPage() {
  const { user } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const create = useCreateTrip()
  const [mode, setMode] = useState<'simple' | 'advanced'>('simple')
  const [interests, setInterests] = useState<string[]>([])
  const [dateError, setDateError] = useState<string | null>(null)

  const {
    register,
    control,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<TripPromptForm>({
    resolver: zodResolver(tripPromptSchema),
    defaultValues: {
      prompt: (location.state as { prompt?: string } | null)?.prompt ?? '',
      destination: '',
      origin: user?.preferences?.home_city ?? 'Kolkata, India',
      start_date: '',
      end_date: '',
      travelers: 2,
      budget_inr: 35000,
    },
  })
  const prompt = watch('prompt') ?? ''

  useEffect(() => {
    if (user?.preferences?.interests?.length) setInterests(user.preferences.interests.map(String))
  }, [user?.preferences?.interests])

  const onSubmit = handleSubmit(async (v) => {
    const err = validateTripDates(v.start_date, v.end_date)
    setDateError(err)
    if (err) return
    try {
      const res = await create.mutateAsync({
        prompt: v.prompt,
        destination: v.destination || undefined,
        origin: v.origin || undefined,
        start_date: v.start_date || null,
        end_date: v.end_date || null,
        travelers: v.travelers,
        budget_inr: v.budget_inr,
        interests: mode === 'advanced' || interests.length ? interests : [],
        mode,
        launch_run: true,
      })
      toast.success('Agents are planning your trip', 'Watching live in Agent Studio.')
      navigate(res.run_public_id ? `/studio/runs/${res.run_public_id}` : `/trips/${res.trip.id}`)
    } catch (e) {
      toast.error('Could not start planning', e instanceof ApiError ? e.message : 'Is the backend running?')
    }
  })

  return (
    <div className="mx-auto max-w-[1280px]">
      <nav aria-label="Breadcrumb" className="mb-3 flex items-center gap-2 text-xs text-muted">
        <Home className="size-3.5" /> <Link to="/dashboard" className="hover:underline">My Workspace</Link> <span>›</span> <span className="font-semibold text-primary-strong">Plan a New Trip</span>
      </nav>
      <div className="grid gap-5 xl:grid-cols-[1fr_300px]">
        <div>
          <section className="relative overflow-hidden rounded-3xl p-6 sm:p-9" style={{ backgroundImage: 'url(/assets/hero/beach.svg)', backgroundSize: 'cover', backgroundPosition: 'center' }}>
            <div className="absolute inset-0 bg-gradient-to-r from-white/90 via-white/55 to-transparent" aria-hidden />
            <div className="relative">
              <h1 className="text-3xl font-extrabold text-slate-900 sm:text-[42px]">
                Where will your <em className="font-serif text-primary-strong">story</em> take you?
              </h1>
              <p className="mt-2 text-slate-700">Tell your AI travel team about your dream journey.</p>
              <ul className="mt-4 flex flex-wrap gap-2">
                {[['Multi-Agent Planning', Workflow], ['Personalized Itineraries', LayoutList], ['Real-time Insights', Zap], ['Budget Optimized', IndianRupee]].map(([l, I]) => {
                  const Icon = I as typeof Zap
                  return <li key={l as string} className="flex items-center gap-1.5 rounded-xl border border-white/80 bg-white/80 px-3 py-1.5 text-xs font-semibold text-slate-700 backdrop-blur"><Icon className="size-3.5 text-primary" /> {l as string}</li>
                })}
              </ul>
            </div>
          </section>

          <form onSubmit={onSubmit} noValidate className="tg-card -mt-6 relative space-y-5 p-5 sm:mx-4 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="flex items-center gap-2 text-lg font-bold"><Sparkles className="size-5 text-primary" /> Describe Your Trip</h2>
              <div className="flex rounded-xl border border-line p-1" role="tablist" aria-label="Planning mode">
                {([['simple', 'Simple Planning', Zap], ['advanced', 'Advanced Planning', SlidersHorizontal]] as const).map(([id, label, Icon]) => (
                  <button key={id} type="button" role="tab" aria-selected={mode === id} onClick={() => setMode(id)} className={cn('flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold', mode === id ? 'bg-primary-soft text-primary-ink' : 'text-muted')}>
                    <Icon className="size-4" /> {label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="prompt" className="sr-only">Trip description</label>
              <textarea
                id="prompt"
                rows={4}
                maxLength={2000}
                aria-invalid={errors.prompt ? true : undefined}
                placeholder="Plan a relaxing 5-day Goa trip from Kolkata for two people, with beaches, local food, and a budget of ₹35,000."
                className="tg-input"
                {...register('prompt')}
              />
              <div className="mt-1 flex justify-between text-xs">
                {errors.prompt ? <p role="alert" className="tg-error-text mt-0">{errors.prompt.message}</p> : <span className="text-muted">The supervisor agent parses destination, days, party size and budget from this text.</span>}
                <span className="text-muted">{prompt.length} / 2000</span>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_1.7fr_0.8fr_1fr]">
              <div>
                <label htmlFor="destination" className="tg-label flex items-center gap-1.5"><MapPin className="size-4 text-primary" /> Destination</label>
                <input id="destination" list="dest-list" placeholder="Goa" className="tg-input" {...register('destination')} />
                <datalist id="dest-list">{DESTINATIONS.map((d) => <option key={d} value={d} />)}</datalist>
              </div>
              <div>
                <label htmlFor="start" className="tg-label flex items-center gap-1.5"><Calendar className="size-4 text-primary" /> Travel dates</label>
                <div className="flex gap-1.5">
                  <input id="start" type="date" aria-label="Start date" className="tg-input px-2 text-xs" {...register('start_date')} />
                  <input type="date" aria-label="End date" className="tg-input px-2 text-xs" {...register('end_date')} />
                </div>
                {dateError && <p role="alert" className="tg-error-text">{dateError}</p>}
              </div>
              <div>
                <label htmlFor="travelers" className="tg-label flex items-center gap-1.5"><Users className="size-4 text-primary" /> Travelers</label>
                <Controller control={control} name="travelers" render={({ field }) => (
                  <input id="travelers" type="number" min={1} max={20} className="tg-input" aria-invalid={errors.travelers ? true : undefined} value={Number.isNaN(field.value) ? '' : field.value} onChange={(e) => field.onChange(e.target.value === '' ? NaN : Number(e.target.value))} />
                )} />
                {errors.travelers && <p role="alert" className="tg-error-text">{errors.travelers.message ?? 'Enter travelers'}</p>}
              </div>
              <div>
                <label htmlFor="budget" className="tg-label flex items-center gap-1.5"><IndianRupee className="size-4 text-primary" /> Budget (total, INR)</label>
                <Controller control={control} name="budget_inr" render={({ field }) => (
                  <input id="budget" type="number" min={1000} step={500} className="tg-input" aria-invalid={errors.budget_inr ? true : undefined} value={Number.isNaN(field.value) ? '' : field.value} onChange={(e) => field.onChange(e.target.value === '' ? NaN : Number(e.target.value))} />
                )} />
                {errors.budget_inr && <p role="alert" className="tg-error-text">{errors.budget_inr.message ?? 'Enter a budget'}</p>}
              </div>
            </div>

            {mode === 'advanced' && (
              <div className="grid gap-3 border-t border-line pt-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="origin" className="tg-label flex items-center gap-1.5"><Plane className="size-4 text-primary" /> Travelling from</label>
                  <input id="origin" className="tg-input" {...register('origin')} />
                </div>
                <fieldset>
                  <legend className="tg-label">Interests</legend>
                  <div className="flex flex-wrap gap-1.5">
                    {INTERESTS.map((i) => (
                      <button key={i} type="button" aria-pressed={interests.includes(i)} onClick={() => setInterests((c) => c.includes(i) ? c.filter((x) => x !== i) : [...c, i])}
                        className={cn('rounded-full border px-3 py-1 text-xs font-semibold capitalize', interests.includes(i) ? 'border-primary-strong bg-primary-soft text-primary-ink' : 'border-line text-muted')}>
                        {i}
                      </button>
                    ))}
                  </div>
                </fieldset>
              </div>
            )}

            <div className="flex justify-end">
              <button type="submit" disabled={create.isPending} className="tg-btn tg-btn-primary h-12 min-w-44">
                {create.isPending ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                {create.isPending ? 'Starting agents…' : 'Generate Trip'} {!create.isPending && <ArrowRight className="size-4" />}
              </button>
            </div>
          </form>

          <section className="mt-6" aria-labelledby="ideas">
            <h2 id="ideas" className="mb-3 flex items-center gap-2 text-base font-bold"><Lightbulb className="size-5 text-warn" /> Need Inspiration? <span className="text-xs font-normal text-muted">Try one of these ready-to-use prompts.</span></h2>
            <div className="grid gap-3 md:grid-cols-3">
              {IDEAS.map((idea) => (
                <button key={idea.title} type="button" onClick={() => { setValue('prompt', idea.prompt, { shouldValidate: true }); setValue('destination', idea.destination); setValue('travelers', idea.travelers); setValue('budget_inr', idea.budget) }}
                  className="tg-card flex items-center gap-3 p-3 text-left transition hover:border-primary/60">
                  <CoverImage src={idea.img} className="size-16 shrink-0 rounded-xl" />
                  <span className="min-w-0 flex-1"><span className="block text-sm font-bold">{idea.title}</span><span className="block text-xs text-muted">{idea.body}</span></span>
                  <ArrowRight className="size-4 shrink-0 text-primary" />
                </button>
              ))}
            </div>
          </section>
        </div>

        <aside className="tg-card h-fit p-5" aria-labelledby="how">
          <h2 id="how" className="text-base font-bold">How TravelGraph AI Works</h2>
          <p className="mb-4 text-xs text-muted">A team of AI agents collaborates to create your perfect travel plan.</p>
          <ol className="space-y-3">
            {AGENTS.map((a) => {
              const Icon = a.icon
              return (
                <li key={a.id} className="flex items-start gap-3">
                  <span className="grid size-9 shrink-0 place-items-center rounded-xl" style={{ background: `${a.color}22`, color: a.color }}><Icon className="size-[18px]" /></span>
                  <span><span className="block text-sm font-bold">{a.name}</span><span className="block text-xs text-muted">{a.subtitle}</span></span>
                </li>
              )
            })}
          </ol>
          <Link to="/studio" className="tg-btn tg-btn-secondary mt-5 w-full"><Workflow className="size-4 text-primary" /> View Agent Flow</Link>
        </aside>
      </div>
    </div>
  )
}
