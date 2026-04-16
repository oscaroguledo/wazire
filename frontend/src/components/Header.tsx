import React from 'react'
import { Menu, Cloud, CloudOff } from 'lucide-react'
import Icon from './Icon'
import { motion } from 'framer-motion'
import Button from './Button'
import { ProfileDropdown } from './ProfileDropdown'
import { useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'

interface HeaderProps {
  onToggleMobileSidebar?: () => void
}

const ROUTE_TITLES: Record<string, { title: string; subtitle?: string }> = {
  '/dashboard':    { title: 'Dashboard' },
  '/courses':      { title: 'Courses',         subtitle: 'Manage and browse courses' },
  '/exams':        { title: 'Exams',           subtitle: 'Manage and schedule exams' },
  '/submissions':  { title: 'Submissions',     subtitle: 'Review and grade submissions' },
  '/users':        { title: 'User Management', subtitle: 'Manage users, roles and permissions' },
  '/institutions': { title: 'Institution',     subtitle: 'Your institution profile' },
}

function getPageMeta(pathname: string) {
  if (ROUTE_TITLES[pathname]) return ROUTE_TITLES[pathname]
  const key = Object.keys(ROUTE_TITLES).find(k => k !== '/dashboard' && pathname.startsWith(k))
  return key ? ROUTE_TITLES[key] : null
}

function HeaderComponent({ onToggleMobileSidebar }: HeaderProps) {
  const { pathname } = useLocation()
  const meta = getPageMeta(pathname)

  // Network status
  const [isOnline, setIsOnline] = useState(true)

  useEffect(() => {
    // Check initial status
    setIsOnline(navigator.onLine)

    const handleOnline = () => {
      setIsOnline(true)
    }

    const handleOffline = () => {
      setIsOnline(false)
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  return (
    <motion.header
      className="bg-[var(--color-bg-card)] border-b border-[var(--color-border-light)] px-6 py-4 flex items-center justify-between"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
      <motion.div className="md:hidden" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
        <Button variant="secondary" onClick={onToggleMobileSidebar} className="p-2 w-10 h-10 flex items-center justify-center">
          <Icon as={Menu} size={18} className="text-[var(--color-text-muted)]" />
        </Button>
      </motion.div>

      {meta && (
        <motion.div className="hidden md:block" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.15 }}>
          <h1 className="text-xl font-bold text-[var(--color-text-primary)] leading-tight">{meta.title}</h1>
          {meta.subtitle && <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{meta.subtitle}</p>}
        </motion.div>
      )}

      <motion.div className="flex items-center gap-4 ml-auto" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }}>
        {/* Network Status Indicator */}
        {!isOnline ? (
          <motion.div
            className="flex items-center gap-2 px-3 py-1.5 bg-[var(--color-error-50)] border border-[var(--color-error-200)] rounded-lg"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
          >
            <Icon as={CloudOff} size={16} className="text-[var(--color-error-600)]" />
            <span className="text-xs font-medium text-[var(--color-error-700)] hidden sm:inline">Offline</span>
          </motion.div>
        ) : (
          <motion.div
            className="flex items-center gap-2 px-3 py-1.5 bg-[var(--color-success-50)] border border-[var(--color-success-200)] rounded-lg"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <Icon as={Cloud} size={16} className="text-[var(--color-success-600)]" />
            <span className="text-xs font-medium text-[var(--color-success-700)] hidden sm:inline">Online</span>
          </motion.div>
        )}

        <ProfileDropdown />
      </motion.div>
    </motion.header>
  )
}

export const Header = React.memo(HeaderComponent)
