import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { GraduationCap, Mail, Lock, Eye, EyeOff, ArrowRight, AlertCircle } from 'lucide-react'
import Icon from '@/components/Icon'
import Input from '@/components/Input'
import Button from '@/components/Button'
import Checkbox from '@/components/Checkbox'
import { useAuth } from '@/contexts/AuthContext'
import { UserRole } from '@/lib/types'

export function Register() {
  const navigate = useNavigate()
  const { register: authRegister } = useAuth()
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', password: '', confirm: '' })
  const [showPw, setShowPw]       = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [agree, setAgree]         = useState(false)
  const [loading, setLoading]     = useState(false)
  const [errors, setErrors]       = useState<Record<string, string>>({})

  const set = (k: string, v: string) => {
    setForm(p => ({ ...p, [k]: v }))
    setErrors(p => ({ ...p, [k]: '' }))
  }

  const validate = () => {
    const e: Record<string, string> = {}
    if (form.first_name.trim().length < 2) e.first_name = 'Required'
    if (form.last_name.trim().length < 2)  e.last_name  = 'Required'
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = 'Enter a valid email'
    if (form.password.length < 8) e.password = 'Min 8 characters'
    if (form.password !== form.confirm) e.confirm = 'Passwords do not match'
    if (!agree) e.agree = 'You must agree to the terms'
    return e
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) { setErrors(errs); return }
    setLoading(true)
    try {
      await authRegister(`${form.first_name} ${form.last_name}`, form.email, form.password, 'admin' as UserRole)
      navigate('/institutions/create')
    } catch (err: any) {
      setErrors({ general: err.message?.includes('Email already') ? 'Email already registered.' : (err.message || 'Registration failed.') })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left branding panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-slate-900 via-slate-800 to-[#1a2634] flex-col items-center justify-center p-12 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")" }} />
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="relative z-10 text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-[var(--color-accent-coral-500)]/20 border border-[var(--color-accent-coral-400)]/30 mb-6">
            <Icon as={GraduationCap} size={40} className="text-[var(--color-accent-coral-400)]" />
          </div>
          <h1 className="text-4xl font-bold text-white mb-3">
            <span className="bg-gradient-to-r from-white via-white to-[var(--color-accent-coral-400)] bg-clip-text">Wazire</span>
          </h1>
          <p className="text-slate-300 text-lg max-w-xs">Set up your institution in <span className="text-[var(--color-accent-coral-400)] font-medium">minutes</span></p>
          <div className="mt-10 space-y-3 text-left">
            {['Create your admin account', 'Set up your institution', 'Add lecturers and students', 'Start creating exams'].map((s, i) => (
              <div key={i} className="flex items-center gap-3 text-slate-300 text-sm group">
                <div className="w-6 h-6 rounded-full bg-[var(--color-accent-coral-500)]/30 border border-[var(--color-accent-coral-400)]/40 flex items-center justify-center text-[var(--color-accent-coral-400)] text-xs font-bold group-hover:scale-110 transition-transform">{i + 1}</div>
                <span className="group-hover:text-[var(--color-accent-coral-400)] transition-colors">{s}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center p-6 bg-[var(--color-bg-main)] overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-sm py-8"
        >
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <Icon as={GraduationCap} size={28} className="text-[var(--color-accent-coral-500)]" />
            <span className="text-xl font-bold text-[var(--color-text-primary)]">Wazire</span>
          </div>

          <h2 className="text-2xl font-bold text-[var(--color-text-primary)] mb-1">Create admin account</h2>
          <p className="text-sm text-[var(--color-text-muted)] mb-8">Register to manage your institution</p>

          {errors.general && (
            <div className="mb-5 p-3 rounded-lg bg-[var(--color-error-100)] border border-[var(--color-error-100)] flex items-center gap-2 text-sm text-[var(--color-error-600)]">
              <Icon as={AlertCircle} size={15} className="shrink-0" />
              {errors.general}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">First name</label>
                <Input value={form.first_name} onChange={e => set('first_name', (e.target as HTMLInputElement).value)} placeholder="John" />
                {errors.first_name && <p className="text-xs text-[var(--color-error-600)] mt-1">{errors.first_name}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">Last name</label>
                <Input value={form.last_name} onChange={e => set('last_name', (e.target as HTMLInputElement).value)} placeholder="Doe" />
                {errors.last_name && <p className="text-xs text-[var(--color-error-600)] mt-1">{errors.last_name}</p>}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">Email</label>
              <div className="relative">
                <Icon as={Mail} size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                <Input type="email" value={form.email} onChange={e => set('email', (e.target as HTMLInputElement).value)} placeholder="you@example.com" className="pl-9" />
              </div>
              {errors.email && <p className="text-xs text-[var(--color-error-600)] mt-1">{errors.email}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">Password</label>
              <div className="relative">
                <Icon as={Lock} size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                <Input type={showPw ? 'text' : 'password'} value={form.password} onChange={e => set('password', (e.target as HTMLInputElement).value)} placeholder="Min 8 characters" className="pl-9 pr-10" />
                <button type="button" onClick={() => setShowPw(s => !s)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]">
                  <Icon as={showPw ? Eye : EyeOff} size={15} />
                </button>
              </div>
              {errors.password && <p className="text-xs text-[var(--color-error-600)] mt-1">{errors.password}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5">Confirm password</label>
              <div className="relative">
                <Icon as={Lock} size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                <Input type={showConfirm ? 'text' : 'password'} value={form.confirm} onChange={e => set('confirm', (e.target as HTMLInputElement).value)} placeholder="••••••••" className="pl-9 pr-10" />
                <button type="button" onClick={() => setShowConfirm(s => !s)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]">
                  <Icon as={showConfirm ? Eye : EyeOff} size={15} />
                </button>
              </div>
              {errors.confirm && <p className="text-xs text-[var(--color-error-600)] mt-1">{errors.confirm}</p>}
            </div>

            <div>
              <Checkbox checked={agree} onChange={e => setAgree((e.target as HTMLInputElement).checked)} label="I agree to the Terms & Conditions" />
              {errors.agree && <p className="text-xs text-[var(--color-error-600)] mt-1">{errors.agree}</p>}
            </div>

            <Button type="submit" loading={loading} disabled={!agree} className="w-full flex items-center justify-center gap-2 mt-2">
              Create account <Icon as={ArrowRight} size={15} className="text-white" />
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-[var(--color-text-muted)]">
            Already have an account?{' '}
            <Link to="/login" className="text-[var(--color-accent-coral-500)] hover:text-[var(--color-accent-coral-600)] font-medium">Sign in</Link>
          </p>
        </motion.div>
      </div>
    </div>
  )
}
