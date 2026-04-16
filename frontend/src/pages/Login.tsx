import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { GraduationCap, Mail, Lock, Eye, EyeOff, ArrowRight } from 'lucide-react'
import Icon from '@/components/Icon'
import Input from '@/components/Input'
import Button from '@/components/Button'
import { useAuth } from '@/contexts/AuthContext'

export function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw]     = useState(false)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!email || !password) return
    setLoading(true)
    try {
      const u = await login(email, password)
      navigate(u?.role === 'admin' && !u?.tenant_id ? '/institutions/create' : '/dashboard')
    } catch (err: any) {
      setError(err.message?.includes('Invalid') ? 'Invalid email or password.' : (err.message || 'Login failed.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left panel — branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-slate-900 via-slate-800 to-[#1a2634] flex-col items-center justify-center p-12 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")" }} />
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="relative z-10 text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-[var(--color-accent-coral-500)]/20 border border-[var(--color-accent-coral-400)]/30 mb-6">
            <Icon as={GraduationCap} size={40} className="text-[var(--color-accent-coral-400)]" />
          </div>
          <h1 className="text-4xl font-bold text-white mb-3 text-center">
            <span className="bg-gradient-to-r from-white via-white to-[var(--color-accent-coral-400)] bg-clip-text text-transparent inline-block">Wazire</span>
          </h1>
          <p className="text-[var(--color-text-secondary)] text-lg mx-auto text-center leading-relaxed">
            AI-powered exam platform for<br />
            <span className="text-[var(--color-accent-coral-400)] font-medium">modern institutions</span>
          </p>
          <div className="mt-10 grid grid-cols-3 gap-4 text-center">
            {[['Smart Grading', 'AI-assisted'], ['Multi-tenant', 'Isolated'], ['Real-time', 'Analytics']].map(([t, s], i) => (
              <div key={t} className="bg-[var(--color-bg-secondary)]/5 border border-[var(--color-bg-secondary)]/10 rounded-xl p-4 hover:border-[var(--color-accent-coral-500)]/50 hover:bg-[var(--color-accent-coral-500)]/10 transition-all group">
                <div className="w-8 h-8 rounded-lg bg-[var(--color-accent-coral-500)]/20 flex items-center justify-center mb-2 mx-auto group-hover:scale-110 transition-transform">
                  <span className="text-[var(--color-accent-coral-400)] text-xs font-bold">{i + 1}</span>
                </div>
                <p className="text-white font-semibold text-sm">{t}</p>
                <p className="text-white/90 text-xs mt-1">{s}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-6 bg-[var(--color-bg-main)]">
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-sm"
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <Icon as={GraduationCap} size={28} className="text-[var(--color-primary-600)]" />
            <span className="text-xl font-bold text-[var(--color-text-primary)]">Wazire</span>
          </div>

          <h2 className="text-2xl font-bold text-[var(--color-text-primary)] mb-1">Welcome back</h2>
          <p className="text-sm text-[var(--color-text-muted)] mb-8">Sign in to your account</p>

          {error && (
            <div className="mb-5 p-3 rounded-lg bg-[var(--color-error-100)] border border-[var(--color-error-100)] text-sm text-[var(--color-error-600)]">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">Email</label>
              <div className="relative">
                <Icon as={Mail} size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                <Input type="email" value={email} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)} placeholder="you@example.com" className="pl-9" required />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-sm font-medium text-[var(--color-text-secondary)]">Password</label>
                <button type="button" onClick={() => {}} className="text-xs text-[var(--color-primary-600)] hover:text-[var(--color-primary-700)]">Forgot password?</button>
              </div>
              <div className="relative">
                <Icon as={Lock} size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                <Input type={showPw ? 'text' : 'password'} value={password} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)} placeholder="••••••••" className="pl-9 pr-10" required />
                <button type="button" onClick={() => setShowPw(s => !s)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]">
                  <Icon as={showPw ? Eye : EyeOff} size={15} />
                </button>
              </div>
            </div>

            <Button type="submit" loading={loading} className="w-full mt-2 flex items-center justify-center gap-2">
              Sign in <Icon as={ArrowRight} size={15} className="text-white" />
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-[var(--color-text-muted)]">
            Don't have an account?{' '}
            <Link to="/register" className="text-[var(--color-accent-coral-500)] hover:text-[var(--color-accent-coral-600)] font-medium">Create one</Link>
          </p>
        </motion.div>
      </div>
    </div>
  )
}
