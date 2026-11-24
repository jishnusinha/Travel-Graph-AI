import { useEffect, useRef } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { cn } from '@/lib/utils'
import { DarkSidebar, LightSidebar } from './Sidebars'
import { TopBar } from './TopBar'
import { MobileBottomNav } from './MobileBottomNav'
import { isDarkRoute } from './nav'

/**
 * Authenticated shell. Studio / evaluation / cost routes render in the dark
 * "Intelligence Workspace"; everything else is the light "Travel Workspace".
 */
export function AppShell() {
  const { pathname } = useLocation()
  const { user } = useAuth()
  const dark = isDarkRoute(pathname)
  const reduce = !!user?.preferences?.reduced_motion
  const mainRef = useRef<HTMLElement>(null)
  useEffect(() => {
    mainRef.current?.scrollTo({ top: 0 })
  }, [pathname])
  useEffect(() => {
    document.documentElement.dataset.reduceMotion = String(reduce)
    return () => {
      delete document.documentElement.dataset.reduceMotion
    }
  }, [reduce])
  return (
    <div
      className={cn(
        'flex h-full min-h-screen bg-canvas text-ink',
        dark && 'theme-dark',
        dark
          ? 'bg-[radial-gradient(900px_500px_at_70%_-10%,rgba(99,102,241,0.14),transparent),radial-gradient(700px_400px_at_0%_100%,rgba(45,212,191,0.07),transparent)]'
          : 'bg-[linear-gradient(180deg,var(--tg-canvas-wash),var(--tg-canvas)_320px)]',
      )}
    >
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[200] focus:rounded-lg focus:bg-primary focus:px-3 focus:py-2 focus:text-white"
      >
        Skip to content
      </a>
      {dark ? <DarkSidebar /> : <LightSidebar />}
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main ref={mainRef} id="main" className="min-h-0 flex-1 overflow-y-auto px-4 pb-24 pt-5 lg:px-6 lg:pb-8">
          <Outlet />
        </main>
      </div>
      <MobileBottomNav />
    </div>
  )
}
