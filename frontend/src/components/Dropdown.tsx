import React, { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ChevronDown, Search } from 'lucide-react'
import Icon from './Icon'

type Option = { value: string; label: string; subtitle?: string }

export default function Dropdown({
  options,
  value,
  onChange,
  className = '',
  searchable = false,
  showClearButton = true,
  placeholder = 'Select...',
  'aria-label': ariaLabel = 'Dropdown',
}: {
  options: Option[]
  value?: string
  onChange?: (v: string) => void
  className?: string
  searchable?: boolean
  showClearButton?: boolean
  placeholder?: string
  'aria-label'?: string
}) {
  const [open, setOpen]           = useState(false)
  const [highlight, setHighlight] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [position, setPosition]   = useState<'below' | 'above'>('below')
  const rootRef   = useRef<HTMLDivElement>(null)
  const btnRef    = useRef<HTMLButtonElement>(null)
  const menuRef   = useRef<HTMLDivElement>(null)

  const filteredOptions = searchable
    ? options.filter(o =>
        o.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (o.subtitle && o.subtitle.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : options

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  useEffect(() => {
    if (!open) { setHighlight(null); if (searchable) setSearchQuery('') }
  }, [open, searchable])

  useEffect(() => {
    if (open && btnRef.current && menuRef.current) {
      const { bottom, top } = btnRef.current.getBoundingClientRect()
      const menuH = menuRef.current.scrollHeight
      setPosition(window.innerHeight - bottom < menuH && top > window.innerHeight - bottom ? 'above' : 'below')
    }
  }, [open, filteredOptions.length])

  const onKeyDown: React.KeyboardEventHandler = (e) => {
    if (!open) {
      if (['ArrowDown', 'Enter', ' '].includes(e.key)) { e.preventDefault(); setOpen(true); setHighlight(0) }
      return
    }
    if (e.key === 'Escape') { setOpen(false); btnRef.current?.focus() }
    else if (e.key === 'ArrowDown') { e.preventDefault(); setHighlight(h => h === null ? 0 : Math.min(filteredOptions.length - 1, h + 1)) }
    else if (e.key === 'ArrowUp')   { e.preventDefault(); setHighlight(h => h === null ? filteredOptions.length - 1 : Math.max(0, h - 1)) }
    else if (e.key === 'Enter' && highlight !== null) {
      e.preventDefault()
      onChange?.(filteredOptions[highlight].value)
      setOpen(false)
      btnRef.current?.focus()
    }
  }

  const selectedOption = options.find(o => o.value === value)

  return (
    <div className={`relative inline-block ${className}`} ref={rootRef}>
      <button
        ref={btnRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        onClick={() => setOpen(s => !s)}
        onKeyDown={onKeyDown}
        className="flex items-center gap-2 w-full h-[38px] px-3 text-sm rounded-lg border border-[var(--color-border-light)] bg-[var(--color-bg-card)] text-[var(--color-text-primary)] hover:border-[var(--color-border-medium)] transition-colors"
      >
        <span className="truncate flex-1 text-left">
          {selectedOption ? selectedOption.label : <span className="text-[var(--color-text-muted)]">{placeholder}</span>}
        </span>
        {searchable && value && showClearButton && (
          <span
            role="button"
            tabIndex={0}
            onClick={e => { e.stopPropagation(); onChange?.('') }}
            onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); onChange?.(''); } }}
            className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] cursor-pointer"
          >
            <Icon as={X} size={13} />
          </span>
        )}
        <Icon as={ChevronDown} size={14} className={`text-[var(--color-text-muted)] transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            ref={menuRef}
            initial={{ opacity: 0, y: position === 'below' ? -4 : 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: position === 'below' ? -4 : 4 }}
            transition={{ duration: 0.12 }}
            role="listbox"
            className={`absolute ${position === 'below' ? 'top-full mt-1' : 'bottom-full mb-1'} z-20 min-w-full max-h-60 overflow-y-auto bg-[var(--color-bg-card)] border border-[var(--color-border-light)] rounded-lg shadow-[var(--shadow-md)]`}
          >
            {searchable && (
              <div className="p-2 border-b border-[var(--color-border-light)]">
                <div className="relative">
                  <Icon
                    as={Search}
                    size={14}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] pointer-events-none"
                  />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search options..."
                    className="w-full pl-9 pr-3 py-1.5 text-sm rounded-lg border border-[var(--color-border-light)] bg-[var(--color-bg-card)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent-coral-400)] focus:ring-1 focus:ring-[var(--color-accent-coral-400)]"
                  />
                </div>
              </div>
            )}
            {filteredOptions.length === 0 ? (
              <div className="p-3 text-sm text-[var(--color-text-muted)] text-center">No options</div>
            ) : (
              filteredOptions.map((o, i) => (
                <div
                  key={o.value}
                  role="option"
                  aria-selected={value === o.value}
                  onClick={() => { onChange?.(o.value); setOpen(false); btnRef.current?.focus() }}
                  onMouseEnter={() => setHighlight(i)}
                  className={`px-3 py-2 text-sm cursor-pointer transition-colors ${
                    value === o.value
                      ? 'bg-[var(--color-primary-50)] text-[var(--color-primary-700)] font-medium'
                      : highlight === i
                        ? 'bg-[var(--color-bg-hover)]'
                        : 'text-[var(--color-text-primary)]'
                  }`}
                >
                  <div>{o.label}</div>
                  {o.subtitle && <div className="text-xs text-[var(--color-text-muted)]">{o.subtitle}</div>}
                </div>
              ))
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
