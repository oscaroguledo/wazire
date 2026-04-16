import React from 'react'
import { motion } from 'framer-motion'

function Pulse({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse bg-[var(--color-bg-hover)] rounded-lg ${className}`} />
}

export function TenantsSkeleton() {
  return (
    <div className="max-w-4xl">
      {/* Breadcrumb + button row */}
      <div className="flex items-center justify-between mb-4">
        <Pulse className="h-4 w-32" />
        <Pulse className="h-9 w-20 rounded-lg" />
      </div>

      {/* Profile card skeleton */}
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        className="bg-[var(--color-bg-card)] rounded-2xl ring-1 ring-[var(--color-border-light)] overflow-hidden mb-5"
      >
        {/* Cover */}
        <Pulse className="h-28 rounded-none" />
        <div className="px-6 pb-6">
          <div className="flex items-end justify-between -mt-10 mb-4">
            <Pulse className="w-20 h-20 rounded-xl ring-4 ring-[var(--color-bg-card)]" />
            <Pulse className="h-6 w-20 rounded-full" />
          </div>
          <Pulse className="h-7 w-56 mb-3" />
          <div className="flex gap-4">
            <Pulse className="h-4 w-32" />
            <Pulse className="h-4 w-40" />
          </div>
        </div>
      </motion.div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[0, 1, 2, 3].map(i => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            className="bg-[var(--color-bg-card)] rounded-xl ring-1 ring-[var(--color-border-light)] p-5"
          >
            <Pulse className="w-9 h-9 rounded-lg mb-3" />
            <Pulse className="h-7 w-12 mb-1" />
            <Pulse className="h-3 w-16" />
          </motion.div>
        ))}
      </div>
    </div>
  )
}

export default TenantsSkeleton
