import { NavLink, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard,
  Building2,
  Telescope,
  TrendingUp,
  FileText,
  MessageSquare,
  Upload,
  Activity,
  Zap,
} from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/accounts', label: 'Accounts', icon: Building2 },
  { to: '/research', label: 'Research', icon: Telescope },
  { to: '/opportunities', label: 'Opportunities', icon: TrendingUp },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/chat', label: 'Ask Intelligence', icon: MessageSquare },
  { to: '/ingest', label: 'Data Ingestion', icon: Upload },
]

export function Sidebar() {
  return (
    <aside className="w-60 shrink-0 bg-[#161b27] border-r border-[#2a3348] flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-[#2a3348]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-gray-100 leading-tight">GTM Intelligence</p>
            <p className="text-xs text-gray-500">Enterprise Platform</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto">
        <div className="space-y-0.5">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-blue-600/15 text-blue-400 font-medium'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-[#1e2535]'
                )
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-[#2a3348]">
        <p className="text-xs text-gray-600">v1.0.0 · Zero Paid Cost</p>
        <p className="text-xs text-gray-600 mt-0.5">Powered by Gemini Free Tier</p>
      </div>
    </aside>
  )
}

export function TopBar({ title, subtitle }) {
  return (
    <header className="h-14 border-b border-[#2a3348] flex items-center px-6 gap-3 sticky top-0 bg-[#0f1117]/95 backdrop-blur z-10">
      <div className="flex-1">
        <h1 className="text-base font-semibold text-gray-100">{title}</h1>
        {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2">
        <Activity className="w-4 h-4 text-green-400" />
        <span className="text-xs text-gray-500">System Active</span>
      </div>
    </header>
  )
}

export function Layout({ children, title, subtitle }) {
  return (
    <div className="flex min-h-screen bg-[#0f1117]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar title={title} subtitle={subtitle} />
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
