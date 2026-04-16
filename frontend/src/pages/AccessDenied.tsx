import React from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ShieldX, ArrowLeft, Home } from 'lucide-react'
import Icon from '@/components/Icon'
import Button from '@/components/Button'

export function AccessDenied() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[var(--color-bg-main)]">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-sm text-center"
      >
        <div className="w-20 h-20 rounded-2xl bg-[var(--color-error-100)] flex items-center justify-center mx-auto mb-6">
          <Icon as={ShieldX} size={36} className="text-[var(--color-error-600)]" />
        </div>

        <h1 className="text-2xl font-bold text-[var(--color-text-primary)] mb-2">Access Denied</h1>
        <p className="text-[var(--color-text-muted)] mb-8">
          You don't have permission to view this page. Contact your administrator if you think this is a mistake.
        </p>

        <div className="flex gap-3 justify-center">
          <Button variant="secondary" onClick={() => navigate(-1)} className="flex items-center gap-2">
            <Icon as={ArrowLeft} size={15} />
            Go back
          </Button>
          <Button onClick={() => navigate('/dashboard')} className="flex items-center gap-2">
            <Icon as={Home} size={15} />
            Dashboard
          </Button>
        </div>
      </motion.div>
    </div>
  )
}
