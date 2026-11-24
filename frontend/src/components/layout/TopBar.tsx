import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Bell, ChevronDown, LogOut, Search, Settings, User as UserIcon } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { useRuns } from '@/hooks/queries'
import { LogoMark } from '@/components/ui/Logo'
import { StatusPill } from '@/components/ui/StatusPill'
import { formatDate, cn } from '@/lib/utils'

function useOutsideClose(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) close()
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close()
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, close])
  return ref
}

export function TopBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [menu, setMenu] = useState(false)
  const [bell, setBell] = useState(false)
  const searchRef = useRef<HTMLInputElement>(null)
  const menuRef = useOutsideClose(menu, () => setMenu(false))
  const bellRef = useOutsideClose(bell, () => setBell(false))
  const runs = useRuns({ page_size: 5 })

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        searchRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const onSearch = (e: FormEvent) => {
    e.preventDefault()
    navigate(q.trim() ? `/trips?q=${encodeURIComponent(q.trim())}` : '/trips')
  }

  const activeRuns = runs.data?.items.filter((r) => r.status === 'running' || r.status === 'pending').length ?? 0

  return (
    <header className="z-30 flex h-16 shrink-0 items-center gap-3 border-b border-line bg-surface/80 px-4 backdrop-blur lg:px-6">
      <Link to="/dashboard" className="shrink-0 lg:hidden" aria-label="TravelGraph AI home">
        <LogoMark />
      </Link>
      <form onSubmit={onSearch} role="search" className="relative max-w-xl flex-1">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden />
        <input
          ref={searchRef}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Search trips"
          placeholder="Search trips, destinations…"
          className="tg-input h-10 rounded-full pl-10 pr-16 text-[13px]"
        />
        <kbd className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 rounded-md border border-line bg-surface-2 px-1.5 py-0.5 text-[10px] font-semibold text-muted sm:block">
          Ctrl K
        </kbd>
      </form>
      <div className="ml-auto flex items-center gap-1">
        <div ref={bellRef} className="relative">
          <button
            type="button"
            aria-label="Recent agent activity"
            aria-expanded={bell}
            onClick={() => setBell((b) => !b)}
            className="relative grid size-10 place-items-center rounded-full text-muted hover:bg-primary-soft hover:text-primary-ink"
          >
            <Bell className="size-5" />
            {activeRuns > 0 && <span className="absolute right-2 top-2 size-2 rounded-full bg-primary ring-2 ring-surface" />}
          </button>
          {bell && (
            <div className="tg-card absolute right-0 top-12 z-50 w-80 bg-surface p-2">
              <p className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted">Recent agent runs</p>
              {runs.isPending && <p className="px-3 py-4 text-sm text-muted">Loading…</p>}
              {runs.data?.items.length === 0 && <p className="px-3 py-4 text-sm text-muted">No runs yet.</p>}
              {runs.data?.items.map((r) => (
                <Link
                  key={r.id}
                  to={`/studio/runs/${r.public_id}`}
                  onClick={() => setBell(false)}
                  className="flex items-center justify-between gap-2 rounded-xl px-3 py-2 hover:bg-primary-soft"
                >
                  <span className="min-w-0">
                    <span className="tg-mono block text-xs font-medium">{r.public_id}</span>
                    <span className="block truncate text-xs text-muted">
                      {r.trip_title ?? r.prompt.slice(0, 32)} · {formatDate(r.created_at)}
                    </span>
                  </span>
                  <StatusPill status={r.status} size="sm" />
                </Link>
              ))}
            </div>
          )}
        </div>
        <div ref={menuRef} className="relative">
          <button
            type="button"
            aria-label="Account menu"
            aria-expanded={menu}
            onClick={() => setMenu((m) => !m)}
            className="flex items-center gap-1.5 rounded-full p-1 pr-2 hover:bg-primary-soft"
          >
            <span className="grid size-9 place-items-center rounded-full bg-primary text-xs font-bold text-white">
              {user?.avatar_initials ?? '?'}
            </span>
            <ChevronDown className={cn('size-4 text-muted transition-transform', menu && 'rotate-180')} />
          </button>
          {menu && (
            <div className="tg-card absolute right-0 top-12 z-50 w-60 bg-surface p-2">
              <div className="px-3 py-2">
                <p className="truncate text-sm font-semibold">{user?.full_name}</p>
                <p className="truncate text-xs text-muted">{user?.email}</p>
              </div>
              <Link to="/settings" onClick={() => setMenu(false)} className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-primary-soft">
                <UserIcon className="size-4" /> Profile
              </Link>
              <Link to="/settings" onClick={() => setMenu(false)} className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm hover:bg-primary-soft">
                <Settings className="size-4" /> Settings
              </Link>
              <button
                type="button"
                onClick={async () => {
                  setMenu(false)
                  await logout()
                  navigate('/login', { replace: true })
                }}
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-danger hover:bg-danger-soft"
              >
                <LogOut className="size-4" /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
