import { motion } from 'framer-motion'

type Props = React.InputHTMLAttributes<HTMLInputElement> & { 
  label?: string
  error?: string
}

export default function Checkbox({ label, error, className = '', ...rest }: Props) {
  return (
    <div className={`space-y-2 ${className}`}>
      <label className="inline-flex items-center gap-3 cursor-pointer group">
        <motion.div
          className="relative"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        >
          <input 
            type="checkbox" 
            {...rest} 
            className={`
              w-4 h-4 rounded border-[var(--color-border-medium)]
              accent-[var(--color-accent-coral-500)]
              focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-coral-100)]
              transition-colors duration-200
              ${error ? 'border-[var(--color-error-500)]' : ''}
            `} 
          />
        </motion.div>
        <motion.span 
          className="text-sm text-[var(--color-text-secondary)] group-hover:text-[var(--color-accent-coral-600)] transition-colors"
          whileHover={{ x: 2 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        >
          {label}
        </motion.span>
      </label>
      {error && (
        <motion.p 
          className="text-xs text-[var(--color-error-600)] mt-1"
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {error}
        </motion.p>
      )}
    </div>
  )
}
