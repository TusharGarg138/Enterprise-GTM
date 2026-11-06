import React from 'react'
import { clsx } from 'clsx'

// ─── Loading Spinner ──────────────────────────────────────────────────────────
export function Spinner({ size = 'md', className = '' }) {
  const sizes = { sm: 'h-4 w-4', md: 'h-6 w-6', lg: 'h-8 w-8', xl: 'h-12 w-12' }
  return (
    <div className={clsx('animate-spin rounded-full border-2 border-gray-700 border-t-blue-500', sizes[size], className)} />
  )
}

// ─── Loading State ────────────────────────────────────────────────────────────
export function LoadingState({ message = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <Spinner size="lg" />
      <p className="text-gray-400 text-sm">{message}</p>
    </div>
  )
}

// ─── Error State ──────────────────────────────────────────────────────────────
export function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <div className="w-12 h-12 rounded-full bg-red-900/30 border border-red-800/50 flex items-center justify-center">
        <span className="text-red-400 text-xl">!</span>
      </div>
      <div className="text-center">
        <p className="text-gray-200 font-medium">Something went wrong</p>
        <p className="text-gray-400 text-sm mt-1">{message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary text-sm">
          Try Again
        </button>
      )}
    </div>
  )
}

// ─── Empty State ──────────────────────────────────────────────────────────────
export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      {Icon && (
        <div className="w-14 h-14 rounded-full bg-[#1e2535] border border-[#2a3348] flex items-center justify-center">
          <Icon className="w-6 h-6 text-gray-500" />
        </div>
      )}
      <div className="text-center">
        <p className="text-gray-200 font-medium">{title}</p>
        {description && <p className="text-gray-400 text-sm mt-1 max-w-sm">{description}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}

// ─── Score Badge ──────────────────────────────────────────────────────────────
export function ScoreBadge({ score, category }) {
  if (score == null) return <span className="text-gray-500 text-sm">Not scored</span>

  const colors = {
    'High Priority': 'text-green-400 bg-green-900/30 border-green-800/50',
    'Medium Priority': 'text-yellow-400 bg-yellow-900/30 border-yellow-800/50',
    'Low Priority': 'text-gray-400 bg-gray-800/30 border-gray-700/50',
  }

  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border',
      colors[category] || colors['Low Priority']
    )}>
      <span className="text-current font-bold">{Math.round(score)}</span>
      <span className="opacity-80">{category?.split(' ')[0] || 'Unknown'}</span>
    </span>
  )
}

// ─── Stat Card ────────────────────────────────────────────────────────────────
export function StatCard({ label, value, icon: Icon, trend, color = 'blue', onClick }) {
  const colors = {
    blue: 'text-blue-400 bg-blue-900/20',
    green: 'text-green-400 bg-green-900/20',
    yellow: 'text-yellow-400 bg-yellow-900/20',
    red: 'text-red-400 bg-red-900/20',
    purple: 'text-purple-400 bg-purple-900/20',
  }

  return (
    <div
      className={clsx('stat-card', onClick && 'cursor-pointer hover:border-blue-500/50 transition-colors')}
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <span className="text-gray-400 text-sm font-medium">{label}</span>
        {Icon && (
          <div className={clsx('p-2 rounded-lg', colors[color])}>
            <Icon className={clsx('w-4 h-4', colors[color].split(' ')[0])} />
          </div>
        )}
      </div>
      <div className="flex items-end gap-2">
        <span className="text-3xl font-bold text-gray-100">{value ?? '—'}</span>
        {trend && <span className={clsx('text-sm mb-1', trend > 0 ? 'text-green-400' : 'text-red-400')}>
          {trend > 0 ? '+' : ''}{trend}%
        </span>}
      </div>
    </div>
  )
}

// ─── Status Badge ─────────────────────────────────────────────────────────────
export function StatusBadge({ status }) {
  const configs = {
    complete: { label: 'Complete', cls: 'badge-high' },
    running: { label: 'Running', cls: 'badge-medium animate-pulse' },
    queued: { label: 'Queued', cls: 'badge-low' },
    failed: { label: 'Failed', cls: 'badge-risk' },
    pending: { label: 'Pending', cls: 'badge-low' },
    partial: { label: 'Partial', cls: 'badge-medium' },
  }
  const { label, cls } = configs[status] || { label: status, cls: 'badge-low' }
  return <span className={cls}>{label}</span>
}

// ─── Confidence Badge ─────────────────────────────────────────────────────────
export function ConfidenceBadge({ level }) {
  const configs = {
    high: 'badge-high',
    medium: 'badge-medium',
    low: 'badge-low',
  }
  return <span className={configs[level?.toLowerCase()] || 'badge-low'}>{level || 'Unknown'}</span>
}

// ─── Section Header ───────────────────────────────────────────────────────────
export function SectionHeader({ title, description, action }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-100">{title}</h2>
        {description && <p className="text-gray-400 text-sm mt-0.5">{description}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}

// ─── Info Row ─────────────────────────────────────────────────────────────────
export function InfoRow({ label, value }) {
  return (
    <div className="flex items-start gap-3 py-2 border-b border-[#2a3348] last:border-0">
      <span className="text-gray-500 text-sm w-32 shrink-0">{label}</span>
      <span className="text-gray-200 text-sm">{value || <span className="text-gray-600">—</span>}</span>
    </div>
  )
}

// ─── Pagination ───────────────────────────────────────────────────────────────
export function Pagination({ page, pages, onPage }) {
  if (pages <= 1) return null
  return (
    <div className="flex items-center gap-2 justify-center pt-4">
      <button
        className="btn-secondary text-sm px-3 py-1 disabled:opacity-40"
        onClick={() => onPage(page - 1)}
        disabled={page <= 1}
      >
        ← Prev
      </button>
      <span className="text-gray-400 text-sm">Page {page} of {pages}</span>
      <button
        className="btn-secondary text-sm px-3 py-1 disabled:opacity-40"
        onClick={() => onPage(page + 1)}
        disabled={page >= pages}
      >
        Next →
      </button>
    </div>
  )
}
