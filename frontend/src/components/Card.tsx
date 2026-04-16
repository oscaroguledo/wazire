import React from 'react'
import { motion } from 'framer-motion'

function CardComponent({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.div
      className={`surface-card p-6 ${className}`}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    >
      {children}
    </motion.div>
  )
}

export default React.memo(CardComponent)
