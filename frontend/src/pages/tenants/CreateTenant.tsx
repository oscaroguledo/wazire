import React, { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Building2, Globe, Image, AlertCircle, ArrowRight } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import * as tenantApi from '@/apis/tenant'
import { me } from '@/apis/auth'
import Input from '@/components/Input'
import Button from '@/components/Button'
import Icon from '@/components/Icon'

export default function CreateTenantPage() {
  const navigate = useNavigate()
  const { user, setUser, authLoading } = useAuth()
  const [name, setName]   = useState('')
  const [domain, setDomain] = useState('')
  const [logo, setLogo]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!authLoading && user?.tenant_id) return <Navigate to="/dashboard" replace />

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!name.trim()) return setError('Institution name is required')
    setLoading(true)
    try {
      const payload: Record<string, string> = { name }
      if (domain) payload.domain = domain
      if (logo)   payload.logo_url = logo
      await tenantApi.createTenant(payload)
      const freshUser = await me()
      setUser(freshUser as any)
      localStorage.setItem('wazire_user', JSON.stringify(freshUser))
      navigate('/dashboard')
    } catch (err: any) {
      setError(
        err.response?.status === 409 ? 'An institution with this name or domain already exists.' :
        err.response?.status === 401 ? 'Session expired. Please log in again.' :
        err.message || 'Failed to create institution.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-slate-900 via-slate-800 to-[#1a2634] flex-col items-center justify-center p-12 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")" }} />
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="relative z-10 text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-[var(--color-accent-coral-500)]/20 border border-[var(--color-accent-coral-400)]/30 mb-6">
            <Icon as={Building2} size={40} className="text-[var(--color-accent-coral-400)]" />
          </div>
          <h1 className="text-4xl font-bold text-white mb-3">
            <span className="bg-gradient-to-r from-white via-white to-[var(--color-accent-coral-400)] bg-clip-text">One last step</span>
          </h1>
          <p className="text-slate-300 text-lg max-w-xs">Set up your institution to start <span className="text-[var(--color-accent-coral-400)] font-medium">managing courses and exams</span></p>
        </motion.div>
      </div>

      {/* Right form */}
      <div className="flex-1 flex items-center justify-center p-6 bg-[var(--color-bg-main)]">
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-sm"
        >
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <Icon as={Building2} size={28} className="text-[var(--color-accent-coral-500)]" />
            <span className="text-xl font-bold text-[var(--color-text-primary)]">Wazire</span>
          </div>

          <h2 className="text-2xl font-bold text-[var(--color-text-primary)] mb-1">Create your institution</h2>
          <p className="text-sm text-[var(--color-text-muted)] mb-8">You can update these details later from your settings.</p>

          {error && (
            <div className="mb-5 p-3 rounded-lg bg-[var(--color-error-100)] border border-[var(--color-error-100)] flex items-center gap-2 text-sm text-[var(--color-error-600)]">
              <Icon as={AlertCircle} size={15} className="shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">Institution name</label>
              <div className="relative">
                <Icon as={Building2} size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                <Input value={name} onChange={e => setName((e.target as HTMLInputElement).value)} placeholder="Greenfield University" className="pl-9" required />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">Domain <span className="text-[var(--color-text-muted)] font-normal">(optional)</span></label>
              <div className="relative">
                <Icon as={Globe} size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                <Input value={domain} onChange={e => setDomain((e.target as HTMLInputElement).value)} placeholder="example.edu" className="pl-9" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">Logo URL <span className="text-[var(--color-text-muted)] font-normal">(optional)</span></label>
              <div className="relative">
                <Icon as={Image} size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                <Input value={logo} onChange={e => setLogo((e.target as HTMLInputElement).value)} placeholder="https://..." className="pl-9" />
              </div>
            </div>

            <Button type="submit" loading={loading} disabled={!name.trim()} className="w-full flex items-center justify-center gap-2 mt-2">
              Create institution <Icon as={ArrowRight} size={15} className="text-white" />
            </Button>
          </form>
        </motion.div>
      </div>
    </div>
  )
}
