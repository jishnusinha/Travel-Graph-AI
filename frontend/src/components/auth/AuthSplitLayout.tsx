import type { ReactNode } from 'react'
import { Bot, Layers, LineChart, Sparkles } from 'lucide-react'
import { Logo } from '@/components/ui/Logo'

interface Props {
  children: ReactNode
  image?: string
  headline?: ReactNode
  tagline?: string
  features?: boolean
}

const FEATURES = [
  { icon: Bot, title: 'Multi-Agent AI Team', body: 'Research, plan, validate and optimize together' },
  { icon: Layers, title: 'Personalized Itineraries', body: 'Trips tailored to your style, budget, and pace' },
  { icon: LineChart, title: 'Smarter Travel Decisions', body: 'Real-time insight into cost, timing, and quality' },
]

export function AuthSplitLayout({
  children,
  image = '/assets/auth/mountains.svg',
  headline = (
    <>
      Go farther.
      <br />
      Plan <span className="relative inline-block">smarter.<span className="absolute -bottom-1 left-0 h-1.5 w-full rounded-full bg-mint/90" /></span>
    </>
  ),
  tagline = 'AI-powered travel planning with a multi-agent team that researches, creates, and optimizes your travel experience.',
  features = true,
}: Props) {
  return (
    <div className="min-h-screen bg-wash p-3 sm:p-5">
      <div className="mx-auto grid min-h-[calc(100vh-1.5rem)] max-w-[1400px] overflow-hidden rounded-3xl bg-surface shadow-soft sm:min-h-[calc(100vh-2.5rem)] lg:grid-cols-[1.08fr_1fr]">
        <section
          className="relative hidden flex-col justify-between overflow-hidden p-10 text-white lg:flex"
          style={{ backgroundImage: `url(${image})`, backgroundSize: 'cover', backgroundPosition: 'center' }}
          aria-label="TravelGraph AI overview"
        >
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-indigo-950/35 via-transparent to-indigo-950/45" aria-hidden />
          <div className="relative">
            <Sparkles className="mb-4 size-9 text-white/90" aria-hidden />
            <h2 className="text-[56px] font-extrabold leading-[1.05] tracking-tight drop-shadow-sm">{headline}</h2>
            <p className="mt-5 max-w-md text-[17px] leading-relaxed text-white/90">{tagline}</p>
          </div>
          {features && (
            <ul className="relative space-y-3">
              {FEATURES.map(({ icon: Icon, title, body }) => (
                <li key={title} className="flex items-center gap-3 rounded-2xl bg-white/15 p-3 backdrop-blur-md">
                  <span className="grid size-10 place-items-center rounded-xl bg-white/90 text-primary-strong">
                    <Icon className="size-5" />
                  </span>
                  <span>
                    <span className="block text-sm font-bold">{title}</span>
                    <span className="block text-xs text-white/85">{body}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="flex flex-col items-center justify-center px-5 py-10 sm:px-10">
          <div className="w-full max-w-[420px]">
            <div className="mb-8 flex justify-center">
              <Logo />
            </div>
            {children}
          </div>
        </section>
      </div>
    </div>
  )
}
