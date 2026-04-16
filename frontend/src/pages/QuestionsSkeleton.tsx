import React from 'react';
import { motion } from 'framer-motion';
import Skeleton from '@/components/Skeleton';

/**
 * Questions page skeleton component
 * Matches the exact layout of the Questions page
 */
export function QuestionsSkeleton() {
  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <Skeleton width="180px" height="36px" className="mb-2" />
          <Skeleton width="320px" height="20px" />
        </div>
        <div className="flex space-x-3">
          <Skeleton width="120px" height="40px" className="rounded" />
          <Skeleton width="140px" height="40px" className="rounded" />
        </div>
      </div>

      {/* Filters and Search */}
      <div className="bg-[var(--color-bg-card)] rounded-xl p-4 shadow-sm mb-6">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1">
            <Skeleton width="100%" height="40px" className="rounded" />
          </div>
          <div className="flex space-x-3">
            <Skeleton width="120px" height="40px" className="rounded" />
            <Skeleton width="100px" height="40px" className="rounded" />
            <Skeleton width="80px" height="40px" className="rounded" />
          </div>
        </div>
      </div>

      {/* Questions List */}
      <div className="space-y-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.1 }}
            className="bg-[var(--color-bg-card)] rounded-xl shadow-sm overflow-hidden"
          >
            {/* Question Header */}
            <div className="p-6 border-b border-[var(--color-border-light)]">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <Skeleton width="40px" height="24px" className="rounded" />
                  <Skeleton width="200px" height="20px" />
                </div>
                <div className="flex items-center space-x-2">
                  <Skeleton width="80px" height="24px" className="rounded" />
                  <Skeleton width="80px" height="24px" className="rounded" />
                </div>
              </div>
              
              {/* Question Text */}
              <div className="mb-4">
                <Skeleton width="100%" height="18px" className="mb-3" />
                <Skeleton width="95%" height="16px" className="mb-2" />
                <Skeleton width="90%" height="16px" className="mb-2" />
                <Skeleton width="85%" height="16px" />
              </div>

              {/* Question Meta */}
              <div className="flex items-center space-x-6">
                <div className="flex items-center space-x-2">
                  <Skeleton width="16px" height="16px" className="rounded" />
                  <Skeleton width="80px" height="14px" />
                </div>
                <div className="flex items-center space-x-2">
                  <Skeleton width="16px" height="16px" className="rounded" />
                  <Skeleton width="70px" height="14px" />
                </div>
                <div className="flex items-center space-x-2">
                  <Skeleton width="16px" height="16px" className="rounded" />
                  <Skeleton width="90px" height="14px" />
                </div>
              </div>
            </div>

            {/* Options Section */}
            <div className="p-6">
              <Skeleton width="100px" height="16px" className="mb-4" />
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, j) => (
                  <div key={j} className="flex items-center space-x-3 p-3 border border-[var(--color-border-light)] rounded-lg">
                    <Skeleton width="24px" height="24px" className="rounded" />
                    <Skeleton width="20px" height="16px" />
                    <Skeleton width="300px" height="16px" />
                    <div className="flex items-center space-x-2 ml-auto">
                      <Skeleton width="60px" height="20px" className="rounded" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="border-t border-[var(--color-border-light)] p-4">
              <div className="flex items-center justify-between">
                <div className="flex space-x-2">
                  <Skeleton width="80px" height="32px" className="rounded" />
                  <Skeleton width="100px" height="32px" className="rounded" />
                </div>
                <div className="flex space-x-2">
                  <Skeleton width="60px" height="32px" className="rounded" />
                  <Skeleton width="60px" height="32px" className="rounded" />
                  <Skeleton width="80px" height="32px" className="rounded" />
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Pagination */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
        className="flex items-center justify-between mt-8"
      >
        <Skeleton width="200px" height="16px" />
        <div className="flex space-x-2">
          <Skeleton width="80px" height="32px" className="rounded" />
          <Skeleton width="80px" height="32px" className="rounded" />
          <Skeleton width="80px" height="32px" className="rounded" />
        </div>
      </motion.div>
    </div>
  );
}

export default QuestionsSkeleton;
