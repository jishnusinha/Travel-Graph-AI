import { useEffect, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Loader2, Save } from 'lucide-react'
import { ErrorState } from '@/components/ui/EmptyState'
import { Field } from '@/components/ui/Field'
import { Skeleton } from '@/components/ui/Skeleton'
import { useToast } from '@/components/ui/Toast'
import { useTrip, useUpdateTrip } from '@/hooks/queries'
import { ApiError } from '@/lib/api'
import { validateTripDates } from '@/lib/validation'

const schema = z.object({
  title: z.string().trim().min(1, 'Title is required').max(200),
  destination: z.string().trim().max(200).optional(),
  origin: z.string().trim().max(200).optional(),
  start_date: z.string().optional(),
  end_date: z.string().optional(),
  travelers: z.number().int().min(1, 'At least 1 traveler').max(20, 'Max 20 travelers'),
  budget_inr: z.number().int().min(1000, 'Budget must be at least ₹1,000'),
  status: z.enum(['draft', 'in_progress', 'completed']),
  notes: z.string().max(5000).optional(),
})
type Form = z.infer<typeof schema>

export default function EditTripPage() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const trip = useTrip(tripId)
  const update = useUpdateTrip(tripId ?? '')
  const [dateError, setDateError] = useState<string | null>(null)

  const { register, control, handleSubmit, reset, formState: { errors, isDirty } } = useForm<Form>({ resolver: zodResolver(schema) })

  useEffect(() => {
    const t = trip.data
    if (!t) return
    reset({
      title: t.title,
      destination: t.destination,
      origin: t.origin,
      start_date: t.start_date ?? '',
      end_date: t.end_date ?? '',
      travelers: t.travelers,
      budget_inr: t.budget_inr,
      status: t.status,
      notes: t.notes ?? '',
    })
  }, [trip.data, reset])

  if (trip.isPending) return <div className="mx-auto max-w-2xl space-y-3"><Skeleton className="h-10 w-64" /><Skeleton className="h-96 w-full" /></div>
  if (trip.isError) return <div className="mx-auto max-w-xl pt-10"><ErrorState error={trip.error} onRetry={() => trip.refetch()} /></div>

  const onSubmit = handleSubmit(async (v) => {
    const err = validateTripDates(v.start_date, v.end_date)
    setDateError(err)
    if (err) return
    try {
      await update.mutateAsync({
        title: v.title,
        destination: v.destination,
        origin: v.origin,
        start_date: v.start_date || null,
        end_date: v.end_date || null,
        travelers: v.travelers,
        budget_inr: v.budget_inr,
        status: v.status,
        notes: v.notes ?? '',
      })
      toast.success('Trip updated')
      navigate(`/trips/${tripId}`)
    } catch (e) {
      toast.error('Could not save changes', e instanceof ApiError ? e.message : undefined)
    }
  })

  return (
    <div className="mx-auto max-w-3xl">
      <Link to={`/trips/${tripId}`} className="mb-3 inline-flex items-center gap-1.5 text-sm font-semibold text-primary-strong hover:underline"><ArrowLeft className="size-4" /> Back to trip</Link>
      <h1 className="mb-1 text-3xl font-extrabold">Edit trip</h1>
      <p className="mb-5 text-sm text-muted">Update the details. To regenerate the itinerary use <strong>Re-plan</strong> on the trip page.</p>
      <form onSubmit={onSubmit} noValidate className="tg-card space-y-4 p-5 sm:p-6">
        <Field label="Trip title" error={errors.title?.message} {...register('title')} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Destination" error={errors.destination?.message} {...register('destination')} />
          <Field label="Travelling from" error={errors.origin?.message} {...register('origin')} />
          <Field label="Start date" type="date" {...register('start_date')} />
          <div>
            <Field label="End date" type="date" {...register('end_date')} />
            {dateError && <p role="alert" className="tg-error-text">{dateError}</p>}
          </div>
          <Controller control={control} name="travelers" render={({ field }) => (
            <Field label="Travelers" type="number" min={1} max={20} error={errors.travelers?.message} value={Number.isNaN(field.value) ? '' : (field.value ?? '')} onChange={(e) => field.onChange(e.target.value === '' ? NaN : Number(e.target.value))} />
          )} />
          <Controller control={control} name="budget_inr" render={({ field }) => (
            <Field label="Budget (INR)" type="number" min={1000} step={500} error={errors.budget_inr?.message} value={Number.isNaN(field.value) ? '' : (field.value ?? '')} onChange={(e) => field.onChange(e.target.value === '' ? NaN : Number(e.target.value))} />
          )} />
        </div>
        <div>
          <label htmlFor="status" className="tg-label">Status</label>
          <select id="status" className="tg-input" {...register('status')}>
            <option value="draft">Draft</option>
            <option value="in_progress">In progress</option>
            <option value="completed">Completed</option>
          </select>
        </div>
        <div>
          <label htmlFor="notes" className="tg-label">Notes</label>
          <textarea id="notes" rows={4} className="tg-input" placeholder="Anything to remember about this trip…" {...register('notes')} />
        </div>
        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Link to={`/trips/${tripId}`} className="tg-btn tg-btn-secondary">Cancel</Link>
          <button type="submit" disabled={update.isPending || !isDirty} className="tg-btn tg-btn-primary">
            {update.isPending ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />} Save changes
          </button>
        </div>
      </form>
    </div>
  )
}
