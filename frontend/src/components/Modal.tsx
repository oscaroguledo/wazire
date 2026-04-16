import React, { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import Icon from './Icon'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const sizes = { sm: 'max-w-md', md: 'max-w-lg', lg: 'max-w-2xl', xl: 'max-w-4xl' }

export function Modal({ isOpen, onClose, title, children, size = 'md' }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const hasFocusedRef = useRef(false)

  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : ''
    if (isOpen && !hasFocusedRef.current) {
      const el = dialogRef.current
      if (!el) return
      const focusable = el.querySelectorAll<HTMLElement>('button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])')
      focusable[0]?.focus()
      hasFocusedRef.current = true
    }
    if (!isOpen) {
      hasFocusedRef.current = false
    }
    const onEsc = (e: KeyboardEvent) => { if (e.key === 'Escape' && isOpen) onClose() }
    document.addEventListener('keydown', onEsc)
    return () => {
      document.body.style.overflow = ''
      document.removeEventListener('keydown', onEsc)
    }
  }, [isOpen, onClose])

  const trapKey: React.KeyboardEventHandler = (e) => {
    if (e.key !== 'Tab') return
    const el = dialogRef.current
    if (!el) return
    const focusable = Array.from(el.querySelectorAll<HTMLElement>('a[href],button:not([disabled]),textarea,input,select,[tabindex]:not([tabindex="-1"])'))
    if (!focusable.length) return
    if (!e.shiftKey && document.activeElement === focusable[focusable.length - 1]) { e.preventDefault(); focusable[0].focus() }
    if (e.shiftKey && document.activeElement === focusable[0]) { e.preventDefault(); focusable[focusable.length - 1].focus() }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="fixed inset-0 bg-[var(--color-overlay-strong)] backdrop-blur-sm z-40"
          />
          <div className="fixed inset-0 z-50 overflow-y-auto" onClick={onClose}>
            <div className="flex min-h-full items-center justify-center p-4">
              <motion.div
                ref={dialogRef}
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                role="dialog" aria-modal="true" aria-label={title}
                onKeyDown={trapKey}
                onClick={e => e.stopPropagation()}
                className={`relative bg-[var(--color-bg-card)] border border-[var(--color-border-light)] rounded-xl shadow-[var(--shadow-lg)] w-full ${sizes[size]} p-6`}
              >
                <div className="flex items-center justify-between mb-5">
                  <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">{title}</h2>
                  <button
                    onClick={onClose}
                    className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-hover)] transition-colors"
                    aria-label="Close"
                  >
                    <Icon as={X} size={16} />
                  </button>
                </div>
                {children}
              </motion.div>
            </div>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}
