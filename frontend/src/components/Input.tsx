import { motion } from 'framer-motion'
import { useState } from 'react'

type InputProps    = React.InputHTMLAttributes<HTMLInputElement>
type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>
type Props = (InputProps | TextareaProps) & {
  as?: 'input' | 'textarea'
  /** Force light appearance — use on dark-background pages like auth */
  light?: boolean
}

export default function Input(props: Props) {
  const [focused, setFocused] = useState(false)
  const { as, light, className = '', onFocus, onBlur, ...rest } = props as any

  const base = light
    ? `w-full rounded-lg px-3 py-2 text-sm transition-all duration-200
       bg-[var(--color-bg-card)] text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)]
       border ${focused ? 'border-[var(--color-accent-coral-500)] ring-2 ring-[var(--color-accent-coral-400)]/30' : 'border-[var(--color-border-light)]'}
       focus:outline-none`
    : `w-full rounded-lg px-3 py-2 text-sm transition-all duration-200
       bg-[var(--color-bg-card)] text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)]
       border ${focused ? 'border-[var(--color-accent-coral-500)] ring-2 ring-[var(--color-accent-coral-400)]/30' : 'border-[var(--color-border-light)]'}
       focus:outline-none`

  const MotionEl = motion[as === 'textarea' ? 'textarea' : 'input']

  return (
    <MotionEl
      className={`${base} ${className}`}
      onFocus={(e: any) => { setFocused(true); onFocus?.(e) }}
      onBlur={(e: any)  => { setFocused(false); onBlur?.(e) }}
      whileFocus={{ scale: 1.005 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      {...(rest as any)}
    />
  )
}
