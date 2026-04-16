import React from 'react'

interface StatusBadgeProps {
  status?: string
  size?: 'sm' | 'md'
}

const STATUS_STYLES: Record<string, string> = {
  active:    'bg-[var(--color-success-100)] text-[var(--color-success-600)] border-[var(--color-success-100)]',
  inactive:  'bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] border-[var(--color-border-medium)]',
  not_started:     'bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] border-[var(--color-border-medium)]',
  in_progress: 'bg-[var(--color-warning-100)] text-[var(--color-warning-600)] border-[var(--color-warning-100)]',
  finished: 'bg-[var(--color-info-100)] text-[var(--color-info-600)] border-[var(--color-info-100)]',
  graded:    'bg-[var(--color-success-100)] text-[var(--color-success-600)] border-[var(--color-success-100)]',
  pending:   'bg-[var(--color-warning-100)] text-[var(--color-warning-600)] border-[var(--color-warning-100)]',
  submitted: 'bg-[var(--color-info-100)] text-[var(--color-info-600)] border-[var(--color-info-100)]',
}

export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const statusStr = (status || 'not_started') as string
  const key = statusStr.toLowerCase()
  const style = STATUS_STYLES[key] ?? STATUS_STYLES.not_started
  const sz = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs'
  const label = statusStr.length > 0 ? (statusStr.charAt(0).toUpperCase() + statusStr.slice(1)) : 'Unknown'
  return (
    <span className={`inline-flex items-center rounded-full font-medium border ${style} ${sz}`}>
      {label}
    </span>
  )
}
