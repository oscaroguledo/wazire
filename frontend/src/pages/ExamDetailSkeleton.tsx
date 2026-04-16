import React from 'react';
import { motion } from 'framer-motion';
import Skeleton from '@/components/Skeleton';

/**
 * ExamDetail page skeleton component
 * Matches the exact layout of the ExamDetail page
 */
export function ExamDetailSkeleton() {
  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <Skeleton width="250px" height="36px" className="mb-2" />
          <Skeleton width="350px" height="20px" />
        </div>
        <div className="flex space-x-3">
          <Skeleton width="100px" height="40px" className="rounded" />
          <Skeleton width="120px" height="40px" className="rounded" />
        </div>
      </div>

      {/* Exam Info Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-[var(--color-bg-card)] rounded-xl shadow-sm overflow-hidden mb-6"
      >
        <div className="p-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <Skeleton width="300px" height="28px" className="mb-4" />
              <Skeleton width="100%" height="16px" className="mb-2" />
              <Skeleton width="90%" height="16px" className="mb-2" />
              <Skeleton width="95%" height="16px" className="mb-6" />
              
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="flex items-center space-x-2">
                    <Skeleton width="16px" height="16px" className="rounded" />
                    <Skeleton width="70px" height="14px" />
                  </div>
                ))}
              </div>
            </div>
            
            <div className="space-y-4">
              <Skeleton width="150px" height="20px" className="mb-3" />
              <div className="space-y-3">
                <div className="flex justify-between">
                  <Skeleton width="80px" height="14px" />
                  <Skeleton width="60px" height="14px" />
                </div>
                <div className="flex justify-between">
                  <Skeleton width="70px" height="14px" />
                  <Skeleton width="50px" height="14px" />
                </div>
                <div className="flex justify-between">
                  <Skeleton width="90px" height="14px" />
                  <Skeleton width="70px" height="14px" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Stats Cards - 5 cards responsive grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4 lg:gap-6 mb-6">
        {Array.from({ length: 5 }).map((_, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.1 }}
            className="surface-card rounded-xl p-4 sm:p-5 border-l-4 border-l-[var(--color-bg-hover)]"
          >
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-[var(--color-bg-hover)] flex items-center justify-center">
                <Skeleton width="18px" height="18px" className="rounded" />
              </div>
              <Skeleton width="60px" height="12px" />
            </div>
            <Skeleton width="80px" height="28px" />
          </motion.div>
        ))}
      </div>

      {/* Tabs Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="bg-[var(--color-bg-card)] rounded-xl shadow-sm"
      >
        {/* Tab Headers */}
        <div className="border-b border-[var(--color-border-light)]">
          <div className="flex space-x-8 px-6">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} width="100px" height="48px" />
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {/* Questions Section */}
          <div>
            <div className="flex items-center justify-between mb-6">
              <Skeleton width="150px" height="20px" />
              <div className="flex space-x-2">
                <Skeleton width="100px" height="32px" className="rounded" />
                <Skeleton width="120px" height="32px" className="rounded" />
              </div>
            </div>
            
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="border border-[var(--color-border-light)] rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <Skeleton width="40px" height="24px" className="rounded" />
                      <Skeleton width="200px" height="18px" />
                    </div>
                    <div className="flex space-x-2">
                      <Skeleton width="80px" height="28px" className="rounded" />
                      <Skeleton width="60px" height="28px" className="rounded" />
                    </div>
                  </div>
                  
                  <Skeleton width="100%" height="14px" className="mb-2" />
                  <Skeleton width="95%" height="14px" className="mb-2" />
                  <Skeleton width="90%" height="14px" className="mb-4" />
                  
                  <div className="flex items-center space-x-4">
                    <Skeleton width="60px" height="14px" />
                    <Skeleton width="70px" height="14px" />
                    <Skeleton width="50px" height="14px" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Submissions Section */}
          <div className="mt-8">
            <div className="flex items-center justify-between mb-6">
              <Skeleton width="180px" height="20px" />
              <div className="flex space-x-2">
                <Skeleton width="100px" height="32px" className="rounded" />
                <Skeleton width="80px" height="32px" className="rounded" />
              </div>
            </div>
            
            <div className="border border-[var(--color-border-light)] rounded-lg overflow-hidden">
              <div className="grid grid-cols-5 gap-4 p-4 border-b border-[var(--color-border-light)]">
                <Skeleton width="80px" height="16px" />
                <Skeleton width="100px" height="16px" />
                <Skeleton width="80px" height="16px" />
                <Skeleton width="60px" height="16px" />
                <Skeleton width="80px" height="16px" />
              </div>
              
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="grid grid-cols-5 gap-4 p-4 border-b border-[var(--color-border-light)]">
                  <div className="flex items-center space-x-3">
                    <Skeleton width="32px" height="32px" className="rounded" />
                    <Skeleton width="120px" height="16px" />
                  </div>
                  <Skeleton width="100px" height="16px" />
                  <Skeleton width="80px" height="16px" />
                  <Skeleton width="60px" height="16px" />
                  <div className="flex space-x-2">
                    <Skeleton width="60px" height="24px" className="rounded" />
                    <Skeleton width="60px" height="24px" className="rounded" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default ExamDetailSkeleton;
