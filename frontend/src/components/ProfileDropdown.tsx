import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, LogOut, Settings, User, CreditCard } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Button from './Button';
import Icon from './Icon';
import { useAuth } from '@/contexts/AuthContext';

export function ProfileDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const toggleDropdown = () => setIsOpen(!isOpen);
  const closeDropdown = () => setIsOpen(false);

  const isAdmin = user?.role === 'admin';

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        closeDropdown();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      // Focus first menu item when opened
      const firstMenuItem = dropdownRef.current?.querySelector('button') as HTMLButtonElement;
      firstMenuItem?.focus();
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      closeDropdown();
    }
  };

  const handleLogout = () => {
    logout();
    closeDropdown();
  };

  return (
    <div ref={dropdownRef} className="relative" onKeyDown={handleKeyDown}>
      {/* Profile Button */}
      <Button
        variant="unstyled"
        noMotion
        noFocus
        onClick={toggleDropdown}
        aria-haspopup="true"
        aria-expanded={isOpen}
        aria-label={`${user?.name || 'User'} menu`}
        className="flex items-center gap-3 pl-4 border-l border-[var(--color-border-light)] rounded-lg transition-all duration-200 py-2 pr-3"
      >
        <div className="w-11 h-11 bg-[var(--color-primary-50)] rounded-full flex items-center justify-center transition-transform duration-200 hover:scale-105">
          <span className="text-primary-700 font-semibold text-base">
            {user?.name?.charAt(0) || 'U'}
          </span>
        </div>
        <div className="hidden md:block">
          <p className="text-base font-medium text-[var(--color-text-primary)] text-left">{user?.name}</p>
          <p className="text-sm text-[var(--color-text-muted)] capitalize text-left">{user?.role}</p>
        </div>
        <ChevronDown 
          className={`w-5 h-5 text-[var(--color-text-muted)] transition-all duration-200 ${
            isOpen ? 'rotate-180 text-[var(--color-accent-coral-500)]' : 'text-[var(--color-text-muted)]'
          }`} 
        />
      </Button>

      {/* Dropdown Menu */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ 
              duration: 0.2, 
              ease: [0.4, 0, 0.2, 1] // Custom cubic bezier
            }}
            role="menu"
            aria-label="User menu"
            className="absolute right-0 mt-2 w-56 bg-[var(--color-bg-card)] rounded-xl shadow-2xl border border-[var(--color-border-light)] py-2 z-50 overflow-hidden"
          >
            {/* User Info */}
            <div className="px-4 py-3 border-b border-[var(--color-border-light)]">
              <p className="text-sm font-medium text-[var(--color-text-primary)]">{user?.name}</p>
              <p className="text-xs text-[var(--color-text-muted)] capitalize">{user?.role}</p>
            </div>

            {/* Menu Items */}
            <div className="py-2" role="none">
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  navigate('/profile');
                  closeDropdown();
                }}
                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-subtle)] transition-colors duration-200 justify-start rounded-none"
              >
                <Icon as={User} size={16} className="text-[var(--color-text-muted)]" />
                View Profile
              </button>
              
              {isAdmin && (
                <>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      navigate('/settings');
                      closeDropdown();
                    }}
                    className="w-full flex items-center gap-3 px-4 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-subtle)] transition-colors duration-200 justify-start rounded-none"
                  >
                    <Icon as={Settings} size={16} className="text-[var(--color-text-muted)]" />
                    Settings
                  </button>

                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      navigate('/billing');
                      closeDropdown();
                    }}
                    className="w-full flex items-center gap-3 px-4 py-2 text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-subtle)] transition-colors duration-200 justify-start rounded-none"
                  >
                    <Icon as={CreditCard} size={16} className="text-[var(--color-text-muted)]" />
                    Billing
                  </button>
                </>
              )}
            </div>

            {/* Logout */}
            <div className="border-t border-[var(--color-border-light)] pt-2" role="none">
              <button
                type="button"
                role="menuitem"
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-4 py-2 text-sm rounded-lg mx-2 justify-start text-[var(--color-error-600)] hover:bg-[var(--color-error-100)]"
              >
                <Icon as={LogOut} size={16} className="text-red-500" />
                Logout
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
