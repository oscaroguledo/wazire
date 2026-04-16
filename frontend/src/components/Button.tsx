import React from 'react'
import { motion } from 'framer-motion'
import { Spinner } from './Spinner'

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'coral' | 'danger' | 'ghost' | 'unstyled'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  noMotion?: boolean
  noFocus?: boolean
}

const buttonVariants: Record<string, string> = {
  primary:   'bg-[var(--color-accent-coral-500)] text-white hover:bg-[var(--color-accent-coral-600)] shadow-sm',
  secondary: 'bg-[var(--color-bg-card)] text-[var(--color-primary-600)] border border-[var(--color-border-light)] hover:bg-[var(--color-bg-hover)] shadow-sm',
  coral:     'bg-[var(--color-accent-coral-500)] text-white hover:bg-[var(--color-accent-coral-600)] shadow-sm',
  danger:    'bg-[var(--color-error-600)] text-[var(--color-text-inverse)] hover:bg-[var(--color-error-600)] shadow-sm',
  ghost:     'bg-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]',
  unstyled:  'bg-transparent text-inherit',
}

export default function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  loading = false,
  disabled,
  noMotion = false,
  noFocus = false,
  ...rest
}: Props) {
  const base = 'text-sm font-semibold inline-flex items-center justify-center transition-colors duration-200'
  const rounded = 'rounded-lg'
  const focus = 'focus-visible:ring-2 focus-visible:ring-[var(--color-accent-coral-500)] focus-visible:ring-offset-2'
  const disabledStyle = 'disabled:opacity-60 disabled:cursor-not-allowed'

  const isIconOnly = React.Children.count(children) === 1 &&
    React.Children.toArray(children).every(c => typeof c === 'object')
  
  const sizeClasses = {
    sm: isIconOnly ? 'p-1.5' : 'px-3 py-1.5 text-xs',
    md: isIconOnly ? 'p-2' : 'px-4 py-2',
    lg: isIconOnly ? 'p-3' : 'px-6 py-3 text-base',
  }
  const sizes = sizeClasses[size]

  const { onAnimationStart, onAnimationComplete, ...buttonProps } = rest as any

  const useFocusClass = !noFocus && variant !== 'unstyled'
  const motionEnabled = !noMotion && variant !== 'unstyled'
  const finalBase = variant === 'unstyled' ? 'inline-flex items-center' : `${rounded} ${base}`

  const motionProps: any = motionEnabled ? {
    whileHover: !loading && !disabled ? { scale: 1.02, y: -1 } : {},
    whileTap:   !loading && !disabled ? { scale: 0.98, y: 0 } : {},
    transition: { type: 'spring', stiffness: 400, damping: 25, mass: 0.5 },
  } : {}

  const MotionComponent = motionEnabled ? motion.button : 'button'

  return (
    <MotionComponent
      className={`${finalBase} ${useFocusClass ? focus : ''} ${disabledStyle} ${sizes} ${buttonVariants[variant]} ${className}`}
      {...motionProps}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...buttonProps}
    >
      {loading && (
        <>
          <Spinner size={16} className="mr-2" />
          <span className="sr-only">Loading</span>
        </>
      )}
      {children}
    </MotionComponent>
  )
}
