import React from 'react'
import { Link, useLocation } from 'react-router-dom'

export default function Breadcrumbs() {
  const loc = useLocation()
  const parts = loc.pathname.split('/').filter(Boolean)
  if (parts.length === 0) return null
  
  // Helper to truncate long IDs (UUIDs)
  const truncateLabel = (label: string) => {
    // If it looks like a UUID or is longer than 12 chars, truncate it
    if (label.length > 12 || /\w{8}-\w{4}-\w{4}/.test(label)) {
      return label.slice(0, 8) + '...'
    }
    return label
  }
  
  const crumbs = parts.map((p, i) => ({
    label: truncateLabel(decodeURIComponent(p.replace(/-/g, ' '))),
    to: '/' + parts.slice(0, i + 1).join('/')
  }))
  return (
    <nav className="text-sm text-[var(--color-text-secondary)] mb-4" aria-label="Breadcrumb">
      <ol className="flex items-center gap-2">
        <li>
          <Link to="/" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:underline transition-colors">Home</Link>
        </li>
        {crumbs.map((c, i) => (
          <li key={c.to} className="flex items-center">
            <span className="mx-2">/</span>
            {i === crumbs.length - 1 ? (
              <span className="text-[var(--color-text-secondary)] font-medium">{c.label}</span>
            ) : (
              <Link to={c.to} className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:underline transition-colors">{c.label}</Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  )
}
