import {
  Home,
  Sparkles,
  Luggage,
  Workflow,
  FlaskConical,
  Database,
  Settings,
  Compass,
  Bookmark,
  Search,
  Share2,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  /** path prefixes that mark this item active */
  match: string[]
  end?: boolean
}

export const WORKSPACE_NAV: NavItem[] = [
  { to: '/dashboard', label: 'Overview', icon: Home, match: ['/dashboard'] },
  { to: '/explore', label: 'Explore', icon: Compass, match: ['/explore', '/destinations'] },
  { to: '/saved', label: 'Saved', icon: Bookmark, match: ['/saved'] },
  { to: '/trips/new', label: 'Plan a Trip', icon: Sparkles, match: ['/trips/new'] },
  { to: '/trips', label: 'My Trips', icon: Luggage, match: ['/trips'], end: false },
]

export const INTELLIGENCE_NAV: NavItem[] = [
  { to: '/studio', label: 'Agent Studio', icon: Workflow, match: ['/studio'] },
  { to: '/intelligence/retrieval', label: 'Retrieval', icon: Search, match: ['/intelligence/retrieval'] },
  { to: '/intelligence/knowledge', label: 'Knowledge', icon: Share2, match: ['/intelligence/knowledge'] },
  { to: '/evaluations', label: 'Evaluation Lab', icon: FlaskConical, match: ['/evaluations'] },
  { to: '/costs', label: 'Cost Explorer', icon: Database, match: ['/costs'] },
]

export const SETTINGS_NAV: NavItem = {
  to: '/settings',
  label: 'Settings & Profile',
  icon: Settings,
  match: ['/settings'],
}

export const DARK_PREFIXES = ['/studio', '/evaluations', '/costs', '/intelligence']

export function isDarkRoute(pathname: string): boolean {
  return DARK_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + '/'))
}

export function isActive(item: NavItem, pathname: string): boolean {
  // "My Trips" must not light up for /trips/new
  if (item.to === '/trips') return pathname === '/trips' || (pathname.startsWith('/trips/') && !pathname.startsWith('/trips/new'))
  return item.match.some((p) => pathname === p || pathname.startsWith(p + '/'))
}
