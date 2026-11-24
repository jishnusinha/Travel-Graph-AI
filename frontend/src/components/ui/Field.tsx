import { forwardRef, useState, type InputHTMLAttributes, type ReactNode } from 'react'
import { Eye, EyeOff, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  icon?: LucideIcon
  hint?: ReactNode
  rightSlot?: ReactNode
  wrapperClassName?: string
}

export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, error, icon: Icon, hint, rightSlot, className, id, wrapperClassName, ...rest },
  ref,
) {
  const inputId = id ?? rest.name
  return (
    <div className={wrapperClassName}>
      {label && (
        <label htmlFor={inputId} className="tg-label">
          {label}
        </label>
      )}
      <div className="relative">
        {Icon && <Icon className="pointer-events-none absolute left-3.5 top-1/2 size-[18px] -translate-y-1/2 text-muted" aria-hidden />}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${inputId}-err` : undefined}
          className={cn('tg-input', Icon && 'pl-11', rightSlot && 'pr-11', className)}
          {...rest}
        />
        {rightSlot && <div className="absolute right-2 top-1/2 -translate-y-1/2">{rightSlot}</div>}
      </div>
      {hint && !error && <p className="mt-1 text-xs text-muted">{hint}</p>}
      {error && (
        <p id={`${inputId}-err`} role="alert" className="tg-error-text">
          {error}
        </p>
      )}
    </div>
  )
})

export const PasswordField = forwardRef<HTMLInputElement, Omit<FieldProps, 'type' | 'rightSlot'>>(
  function PasswordField(props, ref) {
    const [show, setShow] = useState(false)
    return (
      <Field
        ref={ref}
        {...props}
        type={show ? 'text' : 'password'}
        rightSlot={
          <button
            type="button"
            aria-label={show ? 'Hide password' : 'Show password'}
            onClick={() => setShow((s) => !s)}
            className="grid size-8 place-items-center rounded-lg text-muted hover:bg-primary-soft"
          >
            {show ? <EyeOff className="size-[18px]" /> : <Eye className="size-[18px]" />}
          </button>
        }
      />
    )
  },
)
