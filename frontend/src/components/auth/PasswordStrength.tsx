import { Check, Circle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { passwordChecks, passwordStrength } from '@/lib/validation'

const BAR = ['bg-line', 'bg-danger', 'bg-warn', 'bg-primary', 'bg-mint']

export function PasswordStrength({ password }: { password: string }) {
  const { score, label } = passwordStrength(password)
  return (
    <div className="mt-2" aria-live="polite">
      <div className="flex items-center gap-2">
        <div className="flex flex-1 gap-1.5" aria-hidden>
          {[1, 2, 3, 4].map((i) => (
            <span key={i} className={cn('h-1.5 flex-1 rounded-full', i <= score ? BAR[score] : 'bg-line')} />
          ))}
        </div>
        <span className="w-12 text-right text-xs font-semibold text-muted">{label}</span>
      </div>
      <ul className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1">
        {passwordChecks(password).map((c) => (
          <li key={c.id} className={cn('flex items-center gap-1.5 text-xs', c.ok ? 'text-mint' : 'text-muted')}>
            {c.ok ? <Check className="size-3.5" /> : <Circle className="size-3" />}
            {c.label}
          </li>
        ))}
      </ul>
    </div>
  )
}
