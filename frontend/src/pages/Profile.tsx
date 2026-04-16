import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ProfileSkeleton } from './ProfileSkeleton'
import { motion } from 'framer-motion'
import {
  User,
  Mail,
  Lock,
  LogOut,
  Save,
  ShieldCheck,
  Calendar,
  BookOpen,
  Award,
  Clock,
  Edit3,
  Camera,
  CheckCircle2,
  AlertCircle,
  Settings,
  Users,
  Building2
} from 'lucide-react'
import Input from '@/components/Input'
import Button from '@/components/Button'
import Breadcrumbs from '@/components/Breadcrumbs'
import Icon from '@/components/Icon'
import Card from '@/components/Card'
import * as authApi from '@/apis/auth'
import * as courseApi from '@/apis/course'
import { errorTracker } from '@/utils/errorTracking'
import * as enrollmentApi from '@/apis/enrollment'
import * as examApi from '@/apis/exam'
import { useAuth } from '@/contexts/AuthContext'

const Shimmer = ({ className = '' }: { className?: string }) => (
  <div className={`animate-pulse bg-[var(--color-bg-hover)] rounded-lg ${className}`} />
)

interface UserStats {
  icon: any
  label: string
  value: string
  color: string
}

const StatCard = ({ icon: IconComponent, label, value, color }: { icon: any, label: string, value: string, color: string }) => {
  const colorClasses: Record<string, string> = {
    blue: 'bg-[var(--color-primary-50)] text-[var(--color-primary-600)] border-[var(--color-primary-100)]',
    green: 'bg-[var(--color-success-50)] text-[var(--color-success-600)] border-[var(--color-success-100)]',
    purple: 'bg-[var(--color-premium-50)] text-[var(--color-premium-600)] border-[var(--color-premium-100)]',
    amber: 'bg-[var(--color-warning-50)] text-[var(--color-warning-600)] border-[var(--color-warning-100)]',
  }

  return (
    <Card className="p-4 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${colorClasses[color]}`}>
        <Icon as={IconComponent} size={22} />
      </div>
      <div>
        <p className="text-2xl font-bold text-[var(--color-text-primary)]">{value}</p>
        <p className="text-sm text-[var(--color-text-muted)]">{label}</p>
      </div>
    </Card>
  )
}

export default function ProfilePage() {
  const navigate = useNavigate()
  const { logout, user: authUser } = useAuth()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  const [email, setEmail] = useState('')
  const [firstName, setFirstName] = useState('')
  const [middleName, setMiddleName] = useState('')
  const [lastName, setLastName] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('')
  const [joinedDate, setJoinedDate] = useState<string | null>(null)
  const [stats, setStats] = useState<UserStats[]>([])
  const [statsLoading, setStatsLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    authApi.me()
      .then((res) => {
        const data = (res as any)?.user || res
        if (!mounted) return
        setEmail(data?.email || '')
        setFirstName(data?.first_name || data?.firstName || '')
        setMiddleName(data?.middle_name || '')
        setLastName(data?.last_name || data?.lastName || '')
        setRole(data?.role || '')
        setJoinedDate(data?.created_at || data?.joined_at || null)
      })
      .catch((e: unknown) => {
        if (e instanceof Error) {
          errorTracker.track(e, { action: 'load_profile', component: 'Profile' });
        }
      })
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      const payload: Record<string, string | undefined> = {
        first_name: firstName || undefined,
        middle_name: middleName || undefined,
        last_name: lastName || undefined,
      }
      if (password) payload.password = password
      const res = await authApi.updateMe(payload)
      const data = (res as any)?.user || res
      try { localStorage.setItem('wazire_user', JSON.stringify(data)) } catch (err) {
        console.warn('Failed to save user to localStorage:', err)
      }
      setPassword('')
      setMessage({ text: 'Profile updated successfully', type: 'success' })
      setIsEditing(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update profile'
      setMessage({ text: msg, type: 'error' })
    } finally {
      setSaving(false)
    }
  }

  // Fetch user stats based on role
  useEffect(() => {
    if (!role || !authUser?.id) return
    
    const fetchStats = async () => {
      setStatsLoading(true)
      try {
        if (role === 'student') {
          // Fetch student enrollments
          const enrollmentsRes = await enrollmentApi.getStudentEnrollment(authUser.id, { per_page: 100 })
          const totalCourses = enrollmentsRes.pagination.total
          const completedCourses = enrollmentsRes.items.filter(e => e.status === 'completed').length
          
          setStats([
            { icon: BookOpen, label: 'Enrolled', value: totalCourses.toString(), color: 'blue' },
            { icon: Award, label: 'Completed', value: completedCourses.toString(), color: 'green' },
            { icon: Clock, label: 'In Progress', value: (totalCourses - completedCourses).toString(), color: 'purple' },
          ])
        } else if (role === 'lecturer') {
          // Fetch lecturer courses, students, and exams
          const [coursesRes, enrollmentsRes, examsRes] = await Promise.all([
            courseApi.listCourses({ lecturer_id: authUser.id, per_page: 1 }),
            enrollmentApi.getLecturerEnrollment(authUser.id, { per_page: 1 }),
            examApi.listExams({ lecturer_id: authUser.id, per_page: 1 }),
          ])
          
          setStats([
            { icon: BookOpen, label: 'My Courses', value: coursesRes.pagination.total.toString(), color: 'blue' },
            { icon: Users, label: 'My Students', value: enrollmentsRes.pagination.total.toString(), color: 'green' },
            { icon: Award, label: 'Exams', value: examsRes.pagination.total.toString(), color: 'purple' },
          ])
        } else if (role === 'admin') {
          // Fetch admin stats
          const [coursesRes, usersRes] = await Promise.all([
            courseApi.listCourses({ per_page: 1 }),
            authApi.listUsers({ per_page: 100 }),
          ])
          
          const students = usersRes.items.filter(u => u.role === 'student').length
          const lecturers = usersRes.items.filter(u => u.role === 'lecturer').length
          
          setStats([
            { icon: BookOpen, label: 'Courses', value: coursesRes.pagination.total.toString(), color: 'blue' },
            { icon: Users, label: 'Students', value: students.toString(), color: 'green' },
            { icon: ShieldCheck, label: 'Lecturers', value: lecturers.toString(), color: 'purple' },
          ])
        }
      } catch (err: unknown) {
        if (err instanceof Error) {
          errorTracker.track(err, { action: 'fetch_stats', component: 'Profile' });
        }
        setStats([])
      } finally {
        setStatsLoading(false)
      }
    }
    
    fetchStats()
  }, [role, authUser?.id])

  const fullName = [firstName, middleName, lastName].filter(Boolean).join(' ') || 'Your Name'
  const initials = [firstName, lastName].filter(Boolean).map(n => n[0]).join('').toUpperCase() || '?'

  // Format joined date
  const formattedJoinedDate = joinedDate
    ? new Date(joinedDate).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
    : 'N/A'

  if (loading) {
    return <ProfileSkeleton />
  }

  return (
    <div className="max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <Breadcrumbs />
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mt-4"
        >
          <div>
            <h1 className="text-3xl font-bold text-[var(--color-text-primary)]">My Profile</h1>
            <p className="text-[var(--color-text-muted)] mt-1">Manage your personal information and account settings</p>
          </div>
          <Button
            variant="coral"
            onClick={() => setIsEditing(!isEditing)}
            className="flex items-center gap-2"
          >
            <Icon as={isEditing ? CheckCircle2 : Edit3} size={16} />
            {isEditing ? 'Done' : 'Edit Profile'}
          </Button>
        </motion.div>
      </div>

      {/* Stats Row */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8"
      >
        {stats.map((stat, idx) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + idx * 0.05 }}
          >
            <StatCard {...stat} />
          </motion.div>
        ))}
      </motion.div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Form - Left Column */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="lg:col-span-2"
        >
          <Card className="overflow-hidden">
            {/* Profile Header with Avatar */}
            <div className="relative bg-gradient-to-r from-[var(--color-primary-600)] to-[var(--color-primary-500)] p-8">
              <div className="absolute inset-0 bg-black/10" />
              <div className="relative flex items-center gap-6">
                <div className="relative">
                  <div className="w-24 h-24 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center border-4 border-white/30">
                    <span className="text-3xl font-bold text-white">{initials}</span>
                  </div>
                  {isEditing && (
                    <button className="absolute -bottom-1 -right-1 w-8 h-8 bg-white rounded-full shadow-lg flex items-center justify-center text-[var(--color-primary-600)] hover:bg-[var(--color-bg-hover)] transition-colors">
                      <Icon as={Camera} size={14} />
                    </button>
                  )}
                </div>
                <div className="text-white">
                  <h2 className="text-2xl font-bold">{fullName}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <Icon as={Mail} size={14} className="text-white/80" />
                    <span className="text-white/90">{email}</span>
                  </div>
                  {role && (
                    <span className="inline-flex items-center gap-1.5 mt-3 px-3 py-1 rounded-full text-xs font-medium bg-white/20 text-white border border-white/30">
                      <Icon as={ShieldCheck} size={11} />
                      {role.charAt(0).toUpperCase() + role.slice(1)}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Form Content */}
            <form onSubmit={handleSave} className="p-8 space-y-8">
              {/* Personal Information */}
              <div>
                <div className="flex items-center gap-2 mb-6">
                  <div className="w-10 h-10 rounded-lg bg-[var(--color-primary-50)] flex items-center justify-center">
                    <Icon as={User} size={18} className="text-[var(--color-primary-600)]" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-[var(--color-text-primary)]">Personal Information</h3>
                    <p className="text-sm text-[var(--color-text-muted)]">Update your name and contact details</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                      First Name
                    </label>
                    <Input
                      value={firstName}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFirstName(e.target.value)}
                      placeholder="Enter first name"
                      disabled={!isEditing}
                      className={!isEditing ? 'bg-[var(--color-bg-subtle)]' : ''}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                      Middle Name <span className="text-[var(--color-text-muted)]">(Optional)</span>
                    </label>
                    <Input
                      value={middleName}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setMiddleName(e.target.value)}
                      placeholder="Enter middle name"
                      disabled={!isEditing}
                      className={!isEditing ? 'bg-[var(--color-bg-subtle)]' : ''}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                      Last Name
                    </label>
                    <Input
                      value={lastName}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => setLastName(e.target.value)}
                      placeholder="Enter last name"
                      disabled={!isEditing}
                      className={!isEditing ? 'bg-[var(--color-bg-subtle)]' : ''}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                      Email Address
                    </label>
                    <div className="relative">
                      <Icon as={Mail} size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
                      <Input
                        value={email}
                        disabled
                        className="pl-10 bg-[var(--color-bg-subtle)] opacity-70 cursor-not-allowed"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Security Section - Only visible when editing */}
              {isEditing && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="pt-6 border-t border-[var(--color-border-light)]"
                >
                  <div className="flex items-center gap-2 mb-6">
                    <div className="w-10 h-10 rounded-lg bg-[var(--color-warning-50)] flex items-center justify-center">
                      <Icon as={Lock} size={18} className="text-[var(--color-warning-600)]" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-[var(--color-text-primary)]">Security</h3>
                      <p className="text-sm text-[var(--color-text-muted)]">Update your password</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                      <label className="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
                        New Password
                      </label>
                      <Input
                        type="password"
                        value={password}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                        placeholder="Leave blank to keep current password"
                      />
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Feedback message */}
              {message && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex items-center gap-2 p-4 rounded-lg text-sm ${
                    message.type === 'success'
                      ? 'bg-[var(--color-success-50)] text-[var(--color-success-700)] border border-[var(--color-success-200)]'
                      : 'bg-[var(--color-error-50)] text-[var(--color-error-700)] border border-[var(--color-error-200)]'
                  }`}
                >
                  <Icon as={message.type === 'success' ? CheckCircle2 : AlertCircle} size={18} />
                  {message.text}
                </motion.div>
              )}

              {/* Action Buttons */}
              {isEditing && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex gap-3 pt-4"
                >
                  <Button
                    type="submit"
                    variant="coral"
                    className="flex-1 flex items-center justify-center gap-2"
                    loading={saving}
                  >
                    <Icon as={Save} size={16} />
                    Save Changes
                  </Button>
                  <Button
                    variant="ghost"
                    type="button"
                    onClick={() => setIsEditing(false)}
                  >
                    Cancel
                  </Button>
                </motion.div>
              )}
            </form>
          </Card>
        </motion.div>

        {/* Sidebar - Right Column */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="space-y-6"
        >
          {/* Account Info Card */}
          <Card className="p-6">
            <h3 className="font-semibold text-[var(--color-text-primary)] mb-4">Account Info</h3>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-[var(--color-primary-50)] flex items-center justify-center">
                  <Icon as={Calendar} size={16} className="text-[var(--color-primary-600)]" />
                </div>
                <div>
                  <p className="text-sm text-[var(--color-text-muted)]">Member Since</p>
                  <p className="font-medium text-[var(--color-text-primary)]">{formattedJoinedDate}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-[var(--color-premium-50)] flex items-center justify-center">
                  <Icon as={ShieldCheck} size={16} className="text-[var(--color-premium-600)]" />
                </div>
                <div>
                  <p className="text-sm text-[var(--color-text-muted)]">Account Type</p>
                  <p className="font-medium text-[var(--color-text-primary)] capitalize">{role || 'User'}</p>
                </div>
              </div>
              {authUser?.tenant_name && (
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-[var(--color-accent-coral-100)] flex items-center justify-center">
                    <Icon as={Building2} size={16} className="text-[var(--color-accent-coral-600)]" />
                  </div>
                  <div>
                    <p className="text-sm text-[var(--color-text-muted)]">Institution</p>
                    <p className="font-medium text-[var(--color-text-primary)]">{authUser.tenant_name}</p>
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Quick Actions */}
          <Card className="p-6">
            <h3 className="font-semibold text-[var(--color-text-primary)] mb-4">Quick Actions</h3>
            <div className="space-y-2">
              {/* <button
                onClick={() => navigate('/settings')}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-subtle)] transition-colors text-left"
              >
                <Icon as={Settings} size={16} className="text-[var(--color-text-muted)]" />
                Settings
              </button> */}
              <button
                onClick={() => { logout(); navigate('/login') }}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-[var(--color-error-600)] hover:bg-[var(--color-error-50)] transition-colors text-left"
              >
                <Icon as={LogOut} size={16} />
                Sign Out
              </button>
            </div>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}
