import React from 'react';
import { motion } from 'framer-motion';
import Skeleton from '@/components/Skeleton';

/**
 * TakeExam page skeleton component
 * Matches the exact layout of the TakeExam page
 */
export function TakeExamSkeleton() {
  return (
    <div>
      {/* Header with Timer */}
      <div className="bg-[var(--color-bg-card)] border-b border-[var(--color-border-light)] mb-6">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <Skeleton width="300px" height="24px" className="mb-2" />
              <Skeleton width="200px" height="16px" />
            </div>
            <div className="flex items-center space-x-4">
              <Skeleton width="120px" height="20px" />
              <Skeleton width="80px" height="36px" className="rounded" />
            </div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-4xl mx-auto mb-6"
      >
        <div className="bg-[var(--color-bg-card)] rounded-lg p-4 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <Skeleton width="100px" height="14px" />
            <Skeleton width="60px" height="14px" />
          </div>
          <Skeleton width="100%" height="8px" className="rounded" />
        </div>
      </motion.div>

      {/* Question Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="max-w-4xl mx-auto"
      >
        <div className="bg-[var(--color-bg-card)] rounded-xl shadow-sm overflow-hidden">
          {/* Question Header */}
          <div className="border-b border-[var(--color-border-light)] p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <Skeleton width="40px" height="24px" className="rounded" />
                <Skeleton width="200px" height="20px" />
              </div>
              <div className="flex items-center space-x-2">
                <Skeleton width="60px" height="16px" />
                <Skeleton width="80px" height="16px" />
              </div>
            </div>
            
            {/* Question Text */}
            <div className="mb-6">
              <Skeleton width="100%" height="18px" className="mb-3" />
              <Skeleton width="95%" height="16px" className="mb-2" />
              <Skeleton width="90%" height="16px" className="mb-2" />
              <Skeleton width="85%" height="16px" />
            </div>

            {/* Multiple Choice Options */}
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center space-x-3 p-3 border border-[var(--color-border-light)] rounded-lg">
                  <Skeleton width="24px" height="24px" className="rounded" />
                  <Skeleton width="20px" height="16px" />
                  <Skeleton width="300px" height="16px" />
                </div>
              ))}
            </div>
          </div>

          {/* Question Actions */}
          <div className="border-t border-[var(--color-border-light)] p-6">
            <div className="flex items-center justify-between">
              <div className="flex space-x-3">
                <Skeleton width="100px" height="36px" className="rounded" />
                <Skeleton width="80px" height="36px" className="rounded" />
              </div>
              <div className="flex space-x-3">
                <Skeleton width="80px" height="36px" className="rounded" />
                <Skeleton width="100px" height="36px" className="rounded" />
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Question Navigation Sidebar */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.2 }}
        className="fixed right-6 top-24 w-64"
      >
        <div className="bg-[var(--color-bg-card)] rounded-xl shadow-sm p-4">
          <Skeleton width="120px" height="18px" className="mb-4" />
          
          <div className="grid grid-cols-5 gap-2 mb-4">
            {Array.from({ length: 20 }).map((_, i) => (
              <Skeleton
                key={i}
                width="40px"
                height="40px"
                className="rounded"
              />
            ))}
          </div>
          
          <div className="space-y-3">
            <div className="flex justify-between">
              <Skeleton width="60px" height="14px" />
              <Skeleton width="40px" height="14px" />
            </div>
            <div className="flex justify-between">
              <Skeleton width="70px" height="14px" />
              <Skeleton width="40px" height="14px" />
            </div>
            <div className="flex justify-between">
              <Skeleton width="80px" height="14px" />
              <Skeleton width="40px" height="14px" />
            </div>
          </div>
          
          <Skeleton width="100%" height="36px" className="rounded mt-4" />
        </div>
      </motion.div>
    </div>
  );
}

export default TakeExamSkeleton;
