import React from 'react';
import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  BookOpen,
  FileText,
  ClipboardList,
  Users,
  LogOut,
  ChevronLeft,
  GraduationCap,
  Building2 } from
'lucide-react';
import Icon from './Icon';
import Button from './Button';
import { useAuth } from '@/contexts/AuthContext';
import { abbreviateTenantName } from '@/utils/tenantAbbreviations';

interface SidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
  isMobile?: boolean;
}

function SidebarComponent({ isCollapsed, onToggle, isMobile = false }: SidebarProps) {
  const { user, logout } = useAuth();
  const rawTenantName = user?.tenant_name || 'Wazire';
  const tenantName = abbreviateTenantName(rawTenantName);
  const logoUrl = user?.logo_url;
  const navItems = [
  {
    icon: LayoutDashboard,
    label: 'Dashboard',
    path: '/dashboard',
    roles: ['admin', 'lecturer', 'student']
  },
  {
    icon: BookOpen,
    label: 'Courses',
    path: '/courses',
    roles: ['admin', 'lecturer', 'student'] // Students can view enrolled courses
  },
  {
    icon: FileText,
    label: 'Exams',
    path: '/exams',
    roles: ['admin', 'lecturer', 'student'] // Students can view available exams
  },
  {
    icon: ClipboardList,
    label: 'Submissions',
    path: '/submissions',
    roles: ['admin', 'lecturer', 'student'] // All roles can view submissions
  },
  {
    icon: Users,
    label: 'Users',
    path: '/users',
    roles: ['admin'] // Only admins can manage users
  },
  {
    icon: Building2,
    label: 'Institution',
    path: '/institutions',
    roles: ['admin']
  }];

  const filteredNavItems = navItems.filter((item) =>
  item.roles.includes(user?.role || 'student')
  );
  return (
    <motion.aside
      initial={false}
      animate={{
        width: isMobile ? 256 : (isCollapsed ? 80 : 256)
      }}
      aria-label="Main navigation"
      className="bg-[var(--color-bg-sidebar)] text-[var(--color-text-sidebar)] h-screen fixed left-0 top-0 z-30 flex flex-col shadow-xl">
      
      <div className="p-6 flex items-center justify-between border-b border-[var(--color-border-dark)] dark:border-[var(--color-border-light)]/30">
        {(!isCollapsed || isMobile) &&
        <motion.div
          initial={{
            opacity: 0
          }}
          animate={{
            opacity: 1
          }}
          className="flex items-center gap-2">
          
            {logoUrl ? (
              <img src={logoUrl} alt={tenantName} className="h-8 w-8 object-contain rounded" />
            ) : (
              <Icon as={GraduationCap} size={32} className="text-[var(--color-accent-coral-500)] dark:text-[var(--color-accent-coral-400)]" />
            )}
            <span className="text-xl font-bold truncate max-w-[140px] text-[var(--color-text-sidebar)] dark:text-[var(--color-text-sidebar)]/90">{tenantName}</span>
          </motion.div>
        }
        {!isMobile && (
          <Button
            variant="secondary"
            onClick={onToggle}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className="p-2 hover:bg-black/10 dark:hover:bg-white/10 rounded-lg transition-colors"
          >
            <Icon as={ChevronLeft} size={18} className={`transition-transform ${isCollapsed ? 'rotate-180' : ''} text-[var(--color-text-sidebar)] dark:text-[var(--color-text-sidebar)]/80`} />
          </Button>
        )}
        {isMobile && (
          <Button variant="secondary" onClick={onToggle} aria-label="Close sidebar" className="p-2 hover:bg-black/10 dark:hover:bg-white/10 rounded-lg transition-colors">
            <span className="text-2xl text-[var(--color-text-sidebar)] dark:text-[var(--color-text-sidebar)]/80">&times;</span>
          </Button>
        )}
      </div>

      <nav className="flex-1 p-4 space-y-2" aria-label="Main navigation">
        {filteredNavItems.map((item) =>
        <NavLink
          key={item.path}
          to={item.path}
          aria-label={item.label}
          className={({ isActive }) =>
          `flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${isActive ? 'bg-[var(--color-accent-coral-500)] text-white shadow-lg' : 'text-[var(--color-text-sidebar)] dark:text-[var(--color-text-sidebar)]/80 hover:bg-black/10 dark:hover:bg-white/10 hover:text-[var(--color-text-sidebar)]'}`}
        >
          
            <Icon as={item.icon} size={18} className="flex-shrink-0 text-[var(--color-text-sidebar)] dark:text-[var(--color-text-sidebar)]/80" />
            {(!isCollapsed || isMobile) &&
          <motion.span
            initial={{
              opacity: 0
            }}
            animate={{
              opacity: 1
            }}
            className="font-medium">
            
                {item.label}
              </motion.span>
          }
          </NavLink>
        )}
      </nav>

      <div className="p-4 border-t border-[var(--color-border-dark)] dark:border-[var(--color-border-light)]/30">
        <Button onClick={logout} aria-label="Logout" className="flex items-center gap-3 px-4 py-3 rounded-lg text-[var(--color-text-sidebar)] dark:text-[var(--color-text-sidebar)]/80 hover:bg-black/15 dark:hover:bg-white/15 hover:border-[var(--color-border-medium)] dark:hover:border-[var(--color-border-light)] transition-all w-full bg-transparent border border-[var(--color-border-medium)] dark:border-[var(--color-border-light)]">
          <Icon as={LogOut} size={18} className="flex-shrink-0 text-[var(--color-text-sidebar)] dark:text-[var(--color-text-sidebar)]/80" />
          {(!isCollapsed || isMobile) &&
          <motion.span
            initial={{
              opacity: 0
            }}
            animate={{
              opacity: 1
            }}
            className="font-medium">
              Logout
            </motion.span>
          }
        </Button>
      </div>
    </motion.aside>);
}

export const Sidebar = React.memo(SidebarComponent);