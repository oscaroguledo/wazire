import { motion } from 'framer-motion'

type Option = { value: string; label: string }

type Props = {
  name: string
  options: Option[]
  value?: string
  onChange?: (v: string) => void
  className?: string
  error?: string
  orientation?: 'horizontal' | 'vertical'
}

export default function Radio({ 
  name, 
  options, 
  value, 
  onChange, 
  className = '', 
  error,
  orientation = 'horizontal'
}: Props) {
  const orientationClasses = orientation === 'vertical' ? 'space-y-3' : 'flex gap-4'
  
  return (
    <div className={`space-y-2 ${className}`}>
      <div className={`${orientationClasses}`} role="radiogroup">
        {options.map((o, index) => (
          <motion.label 
            key={o.value} 
            className="inline-flex items-center gap-3 cursor-pointer group"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ 
              delay: index * 0.1,
              type: 'spring', 
              stiffness: 300, 
              damping: 30 
            }}
          >
            <motion.div
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            >
              <input
                type="radio"
                name={name}
                value={o.value}
                checked={value === o.value}
                onChange={() => onChange && onChange(o.value)}
                className={`
                  w-4 h-4 text-[var(--color-accent-coral-500)] border-[var(--color-border-medium)] 
                  focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-coral-100)] focus:border-[var(--color-accent-coral-400)]
                  hover:border-[var(--color-accent-coral-400)]
                  transition-colors duration-200
                  ${error ? 'border-red-500' : ''}
                `}
                aria-checked={value === o.value}
              />
            </motion.div>
            <motion.span 
              className="text-sm text-[var(--color-text-secondary)] group-hover:text-[var(--color-accent-coral-600)] transition-colors"
              whileHover={{ x: 2 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            >
              {o.label}
            </motion.span>
          </motion.label>
        ))}
      </div>
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
