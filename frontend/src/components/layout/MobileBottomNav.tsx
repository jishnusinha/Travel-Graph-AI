import { Compass, Home, Luggage, Workflow } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'

const ITEMS = [
  { to: '/dashboard', label: 'Home', icon: Home, active: (p: string) => p === '/dashboard' },
  { to: '/explore', label: 'Explore', icon: Compass, active: (p: string) => p === '/explore' || p.startsWith('/explore/') || p.startsWith('/destinations/') || p === '/saved' },
  {
    to: '/trips',
    label: 'My Trips',
    icon: Luggage,
    active: (p: string) => p === '/trips' || (p.startsWith('/trips/') && p !== '/trips/new'),
  },
  {
    to: '/studio',
    label: 'Studio',
    icon: Workflow,
    active: (p: string) => ['/studio', '/evaluations', '/costs'].some((s) => p === s || p.startsWith(s + '/')),
  },
]

export function MobileBottomNav() {
  const { pathname } = useLocation()
  return (
    <nav
      aria-label="Mobile"
      className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-4 border-t border-line bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden"
    >
      {ITEMS.map(({ to, label, icon: Icon, active }) => {
        const on = active(pathname)
        return (
          <Link
            key={to}
            to={to}
            aria-current={on ? 'page' : undefined}
            className={cn(
              'flex h-16 flex-col items-center justify-center gap-1 text-[11px] font-semibold transition-colors',
              on ? 'text-primary' : 'text-muted',
            )}
          >
            <span className={cn('grid h-7 w-12 place-items-center rounded-full', on && 'bg-primary-soft')}>
              <Icon className="size-5" aria-hidden />
            </span>
            {label}
          </Link>
        )
      })}
    </nav>
  )
}
