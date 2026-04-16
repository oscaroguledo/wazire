import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import * as tenantApi from '@/apis/tenant'
import Input from '@/components/Input'
import Button from '@/components/Button'
import { AlertCircle, Building2, ArrowLeft } from 'lucide-react'
import Icon from '@/components/Icon'

export default function EditTenantPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()

  const [name, setName] = useState('')
  const [domain, setDomain] = useState('')
  const [logo, setLogo] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    tenantApi.getTenant(id)
      .then((t: any) => {
        setName(t.name ?? '')
        setDomain(t.domain ?? '')
        setLogo(t.logo_url ?? '')
        setIsActive(t.is_active ?? true)
      })
      .catch(() => setError('Failed to load institution data.'))
      .finally(() => setFetching(false))
  }, [id])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!name.trim()) return setError('Institution name is required')
    setLoading(true)
    try {
      const payload: Record<string, any> = { name, is_active: isActive }
      if (domain) payload.domain = domain
      if (logo) payload.logo_url = logo
      await tenantApi.updateTenant(id!, payload)
      navigate('/institutions')
    } catch (err: any) {
      if (err.response?.status === 409) {
        setError('An institution with this name or domain already exists.')
      } else if (err.response?.status === 404) {
        setError('Institution not found.')
      } else {
        setError(err.message || 'Failed to update institution. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  if (fetching) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-royal-600" />
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto py-10 px-4">
      <button
        onClick={() => navigate('/institutions')}
        className="flex items-center gap-2 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] mb-6 transition-colors"
      >
        <ArrowLeft size={16} />
        Back to Institutions
      </button>

      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded bg-[var(--color-bg-hover)] flex items-center justify-center">
          <Icon as={Building2} size={20} className="text-[var(--color-text-muted)]" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">Edit Institution</h1>
          <p className="text-sm text-[var(--color-text-muted)]">Update institution details</p>
        </div>
      </div>

      {error && (
        <div className="mb-5 p-4 bg-[var(--color-error-100)] border border-[var(--color-error-100)] rounded-lg flex items-center gap-2">
          <Icon as={AlertCircle} size={16} className="text-[var(--color-error-600)] shrink-0" />
          <p className="text-sm text-[var(--color-error-600)]">{error}</p>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-4 bg-[var(--color-bg-card)] rounded-2xl shadow-sm ring-1 ring-[var(--color-border-light)] p-6">
        <div>
          <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">Institution Name</label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Greenfield University"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">Domain (optional)</label>
          <Input
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="example.edu"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">Logo URL (optional)</label>
          <Input
            value={logo}
            onChange={(e) => setLogo(e.target.value)}
            placeholder="https://..."
          />
        </div>

        <div className="flex items-center gap-3 pt-1">
          <input
            id="is_active"
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="w-4 h-4 rounded border-[var(--color-border-medium)] text-[var(--color-primary-600)] focus:ring-royal-500"
          />
          <label htmlFor="is_active" className="text-sm font-medium text-[var(--color-text-secondary)]">
            Active
          </label>
        </div>

        <div className="flex gap-3 pt-2">
          <Button
            type="button"
            variant="secondary"
            onClick={() => navigate('/institutions')}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            loading={loading}
            disabled={!name.trim()}
            className="flex-1"
          >
            Save Changes
          </Button>
        </div>
      </form>
    </div>
  )
}
