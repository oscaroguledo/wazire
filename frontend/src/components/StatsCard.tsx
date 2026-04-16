import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';

interface StatsCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  delay?: number;
}

export function StatsCard({
  title,
  value,
  icon: Icon,
  trend,
  delay = 0
}: StatsCardProps) {
  return (
    <motion.div
      initial={{
        opacity: 0,
        y: 20,
        scale: 0.95
      }}
      animate={{
        opacity: 1,
        y: 0,
        scale: 1
      }}
      whileHover={{
        y: -4,
        scale: 1.02,
        boxShadow: '0 20px 25px -5px rgba(13, 148, 136, 0.1), 0 10px 10px -5px rgba(13, 148, 136, 0.04)'
      }}
      transition={{
        delay,
        type: 'spring',
        stiffness: 300,
        damping: 30
      }}
      className="bg-[var(--color-bg-card)] rounded-xl p-6 shadow-card hover:shadow-lg transition-all duration-300"
    >
      <div className="flex items-center justify-between">
        <div>
          <motion.p 
            className="text-sm font-medium text-[var(--color-text-secondary)]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: delay + 0.1 }}
          >
            {title}
          </motion.p>
          <motion.p 
            className="text-3xl font-bold text-[var(--color-text-primary)] mt-2"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: delay + 0.2 }}
          >
            {value}
          </motion.p>
          {trend && (
            <motion.p
              className={`text-sm mt-2 ${trend.isPositive ? 'text-[var(--color-success-600)]' : 'text-[var(--color-error-600)]'}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: delay + 0.3 }}
            >
              {trend.isPositive ? '+' : ''}
              {trend.value}% from last month
            </motion.p>
          )}
        </div>
        <motion.div 
          className="bg-[var(--color-primary-50)] p-3 rounded-lg"
          whileHover={{ 
            scale: 1.1, 
            rotate: [0, -5, 5, 0],
            backgroundColor: '#ccfbf1'
          }}
          transition={{ 
            type: 'spring', 
            stiffness: 400, 
            damping: 25 
          }}
        >
          <Icon className="w-8 h-8 text-[var(--color-primary-600)]" />
        </motion.div>
      </div>
    </motion.div>
  );
}