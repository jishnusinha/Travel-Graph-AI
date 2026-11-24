import { Layers } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { Logo } from '@/components/ui/Logo'
import { INTELLIGENCE_NAV, SETTINGS_NAV, WORKSPACE_NAV, isActive, type NavItem } from './nav'

function NavLink({ item, dark }: { item: NavItem; dark: boolean }) {
  const { pathname } = useLocation()
  const active = isActive(item, pathname)
  const Icon = item.icon
  return (
    <Link
      to={item.to}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'flex h-11 items-center gap-3 rounded-xl px-3.5 text-sm font-medium transition-colors',
        active
          ? dark
            ? 'bg-primary-strong text-white shadow-[0_0_22px_rgba(99,102,241,0.55)]'
            : 'bg-primary-soft font-semibold text-primary-ink'
          : 'text-ink/80 hover:bg-primary-soft hover:text-primary-ink',
      )}
    >
      <Icon className="size-[18px]" aria-hidden />
      {item.label}
    </Link>
  )
}

function SidebarBody({ dark }: { dark: boolean }) {
  return (
    <>
      <div className="px-5 pb-3 pt-5">
        <Link to="/dashboard" aria-label="TravelGraph AI home">
          <Logo />
        </Link>
        <span className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-line bg-surface-2 px-3 py-1 text-[11px] font-semibold text-muted">
          <Layers className="size-3.5" aria-hidden /> Dual Experience
        </span>
      </div>
      <nav aria-label="Primary" className="flex-1 space-y-1 overflow-y-auto px-3 pt-3">
        {WORKSPACE_NAV.map((i) => (
          <NavLink key={i.to} item={i} dark={dark} />
        ))}
        <p className="px-3.5 pb-1 pt-5 text-[11px] font-semibold uppercase tracking-wider text-muted">AI Intelligence</p>
        {INTELLIGENCE_NAV.map((i) => (
          <NavLink key={i.to} item={i} dark={dark} />
        ))}
      </nav>
      <div className="border-t border-line p-3">
        <NavLink item={SETTINGS_NAV} dark={dark} />
      </div>
    </>
  )
}

/** Travel Workspace navigation (light theme). */
export function LightSidebar() {
  return (
    <aside
      aria-label="Sidebar"
      className="hidden w-[248px] shrink-0 flex-col border-r border-line bg-surface lg:flex"
    >
      <SidebarBody dark={false} />
    </aside>
  )
}

/** Intelligence Workspace navigation (dark theme, glow). */
export function DarkSidebar() {
  return (
    <aside
      aria-label="Sidebar"
      className="hidden w-[248px] shrink-0 flex-col border-r border-line bg-surface/80 shadow-[inset_-1px_0_0_rgba(129,140,248,0.12)] lg:flex"
    >
      <SidebarBody dark />
    </aside>
  )
}
