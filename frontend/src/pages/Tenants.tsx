import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Building2, Globe, Pencil, Calendar,
  Users, BookOpen, FileText, CheckCircle, XCircle, AlertCircle
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import Button from '@/components/Button'
import Breadcrumbs from '@/components/Breadcrumbs'
import { EmptyState } from '@/components/EmptyState'
import TenantsSkeleton from './TenantsSkeleton'
import * as tenantApi from '@/apis/tenant'
import { getCompactAbbreviation } from '@/utils/tenantAbbreviations'

interface Tenant {
  id: string
  name: string
  domain?: string
  logo_url?: string
  is_active: boolean
  created_at?: string
}

interface TenantStats {
  total_students?: number
  total_lecturers?: number
  total_courses?: number
  total_exams?: number
}

function StatCard({ label, value, icon: Icon, delay }: { label: string; value: number | string; icon: React.ElementType; delay: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, type: 'spring', stiffness: 300, damping: 30 }}
      className="surface-card p-5"
    >
      <div className="w-10 h-10 rounded-xl bg-[var(--color-primary-50)] flex items-center justify-center mb-3">
        <Icon size={20} className="text-[var(--color-primary-600)]" />
      </div>
      <p className="text-2xl font-bold text-[var(--color-text-primary)]">{value}</p>
      <p className="text-sm text-[var(--color-text-muted)] mt-0.5">{label}</p>
    </motion.div>
  )
}

export default function TenantsPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [tenant, setTenant] = useState<Tenant | null>(null)
  const [stats, setStats] = useState<TenantStats>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user?.tenant_id) { setLoading(false); return }
    setError(null)
    Promise.all([
      tenantApi.getTenant(user.tenant_id),
      tenantApi.getTenantStats(user.tenant_id).catch((err) => {
        console.warn('Failed to load tenant stats:', err)
        return {}
      }),
    ])
      .then(([t, s]) => { setTenant(t); setStats(s || {}) })
      .catch(() => setError('Failed to load institution data.'))
      .finally(() => setLoading(false))
  }, [user?.tenant_id])

  if (loading) return <TenantsSkeleton />

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="w-14 h-14 rounded-2xl bg-[var(--color-error-100)] flex items-center justify-center mb-4">
          <AlertCircle size={28} className="text-[var(--color-error-600)]" />
        </div>
        <p className="text-[var(--color-text-primary)] font-semibold mb-1">Something went wrong</p>
        <p className="text-[var(--color-text-muted)] text-sm mb-4">{error}</p>
        <Button variant="secondary" onClick={() => window.location.reload()}>Try again</Button>
      </div>
    )
  }

  if (!tenant) {
    return (
      <EmptyState
        icon={Building2}
        title="No institution found"
        description="Your account is not linked to an institution."
      />
    )
  }

  const statCards = [
    { label: 'Students',  value: stats.total_students  ?? '—', icon: Users },
    { label: 'Lecturers', value: stats.total_lecturers ?? '—', icon: Users },
    { label: 'Courses',   value: stats.total_courses   ?? '—', icon: BookOpen },
    { label: 'Exams',     value: stats.total_exams     ?? '—', icon: FileText },
  ]

  return (
    <div className="max-w-4xl">
      {/* Breadcrumb + action */}
      <div className="flex items-center justify-between mb-5">
        <Breadcrumbs />
        <Button
          variant="coral"
          onClick={() => navigate(`/institutions/${tenant.id}/edit`)}
          className="flex items-center gap-2"
        >
          <Pencil size={14} />
          Edit
        </Button>
      </div>

      {/* Profile card */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 280, damping: 28 }}
        className="surface-card overflow-hidden mb-5 !p-0"
      >
        {/* Cover */}
        <div className="h-32 bg-gradient-to-r from-[var(--color-primary-800)] via-[var(--color-primary-700)] to-[var(--color-primary-800)] relative">
          <div
            className="absolute inset-0 opacity-10"
            style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23ffffff' fill-opacity='1' fill-rule='evenodd'%3E%3Ccircle cx='3' cy='3' r='1.5'/%3E%3Ccircle cx='23' cy='23' r='1.5'/%3E%3C/g%3E%3C/svg%3E\")" }}
          />
          {/* Status badge on cover */}
          <div className="absolute top-4 right-4">
            {tenant.is_active ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-green-500/30 text-white border border-green-500/30 backdrop-blur-sm">
                <CheckCircle size={12} /> Active
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-[var(--color-error-500)]/30 text-white border border-[var(--color-error-500)]/30 backdrop-blur-sm">
                <XCircle size={12} /> Inactive
              </span>
            )}
          </div>
        </div>

        {/* Content section */}
        <div className="px-6 py-6">
          <div className="flex items-start gap-5">
            {/* Logo - clean square design */}
            <div className="shrink-0">
              <div className="w-24 h-24 rounded-2xl shadow-lg overflow-hidden bg-[var(--color-bg-card)] border-2 border-[var(--color-border-light)]">
                {tenant.logo_url ? (
                  <img src={tenant.logo_url} alt={tenant.name} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full bg-gradient-to-br from-[var(--color-accent-coral-500)] to-[var(--color-accent-coral-600)] flex items-center justify-center">
                    <span className="text-2xl font-bold text-white">
                      {getCompactAbbreviation(tenant.name)}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0 pt-1">
              <h2 className="text-2xl font-bold text-[var(--color-text-primary)] truncate">{tenant.name}</h2>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mt-2">
                {tenant.domain && (
                  <div className="flex items-center gap-1.5 text-sm text-[var(--color-text-muted)]">
                    <Globe size={14} className="text-[var(--color-accent-coral-500)]" />
                    <span className="hover:text-[var(--color-text-secondary)] transition-colors">{tenant.domain}</span>
                  </div>
                )}
                {tenant.created_at && (
                  <div className="flex items-center gap-1.5 text-sm text-[var(--color-text-muted)]">
                    <Calendar size={14} className="text-[var(--color-accent-coral-500)]" />
                    Since {new Date(tenant.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statCards.map((s, i) => (
          <StatCard key={s.label} {...s} delay={i * 0.07} />
        ))}
      </div>
    </div>
  )
}
