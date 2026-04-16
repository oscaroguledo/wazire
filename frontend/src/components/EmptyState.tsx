import React from 'react'
import { motion } from 'framer-motion'
import { LucideIcon } from 'lucide-react'
import Button from './Button'

interface EmptyStateProps {
  icon: LucideIcon | React.ElementType
  title: string
  description: string
  action?: { label: string; onClick: () => void }
}

function EmptyStateComponent({ icon: IconComp, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.85 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.05 }}
        className="w-16 h-16 rounded-2xl bg-[var(--color-bg-hover)] flex items-center justify-center mb-4"
      >
        <IconComp size={28} className="text-[var(--color-text-muted)]" />
      </motion.div>
      <motion.h3
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="text-base font-semibold text-[var(--color-text-primary)] mb-1"
      >
        {title}
      </motion.h3>
      <motion.p
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
        className="text-sm text-[var(--color-text-muted)] max-w-xs mb-6"
      >
        {description}
      </motion.p>
      {action && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Button onClick={action.onClick}>{action.label}</Button>
        </motion.div>
      )}
    </div>
  )
}

export const EmptyState = React.memo(EmptyStateComponent)
