import React from 'react';
import { motion } from 'framer-motion';
import Skeleton from '@/components/Skeleton';

/**
 * CourseDetail page skeleton component
 * Matches the exact layout of the CourseDetail page
 */
export function CourseDetailSkeleton() {
  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <Skeleton width="200px" height="36px" className="mb-2" />
          <Skeleton width="300px" height="20px" />
        </div>
        <div className="flex space-x-3">
          <Skeleton width="100px" height="40px" className="rounded" />
          <Skeleton width="120px" height="40px" className="rounded" />
        </div>
      </div>

      {/* Course Info Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-[var(--color-bg-card)] rounded-xl shadow-sm overflow-hidden mb-6"
      >
        <div className="p-6">
          <div className="flex items-start space-x-6">
            <Skeleton width="120px" height="120px" className="rounded-xl" />
            
            <div className="flex-1">
              <Skeleton width="300px" height="28px" className="mb-3" />
              <Skeleton width="150px" height="16px" className="mb-4" />
              
              <Skeleton width="100%" height="14px" className="mb-2" />
              <Skeleton width="90%" height="14px" className="mb-2" />
              <Skeleton width="95%" height="14px" className="mb-4" />
              
              <div className="flex items-center space-x-6">
                <div className="flex items-center space-x-2">
                  <Skeleton width="16px" height="16px" className="rounded" />
                  <Skeleton width="80px" height="12px" />
                </div>
                <div className="flex items-center space-x-2">
                  <Skeleton width="16px" height="16px" className="rounded" />
                  <Skeleton width="70px" height="12px" />
                </div>
                <div className="flex items-center space-x-2">
                  <Skeleton width="16px" height="16px" className="rounded" />
                  <Skeleton width="60px" height="12px" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Stats Grid - 2 stats */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {Array.from({ length: 2 }).map((_, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.1 }}
            className="bg-[var(--color-bg-card)] p-4 rounded-lg shadow-sm"
          >
            <Skeleton width="100px" height="16px" className="mb-2" />
            <Skeleton width="60px" height="24px" />
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
        {/* Tab Headers - 2 tabs */}
        <div className="border-b border-[var(--color-border-light)]">
          <div className="flex space-x-8 px-6">
            {Array.from({ length: 2 }).map((_, i) => (
              <Skeleton key={i} width="80px" height="48px" />
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {/* Overview/Exams Section */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <Skeleton width="120px" height="20px" />
              <Skeleton width="100px" height="32px" className="rounded" />
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Array.from({ length: 2 }).map((_, i) => (
                <div key={i} className="border border-[var(--color-border-light)] rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <Skeleton width="150px" height="18px" />
                    <Skeleton width="80px" height="24px" className="rounded" />
                  </div>
                  <Skeleton width="100%" height="14px" className="mb-2" />
                  <Skeleton width="80%" height="14px" className="mb-3" />
                  <div className="flex items-center justify-between">
                    <div className="flex space-x-4">
                      <Skeleton width="60px" height="12px" />
                      <Skeleton width="70px" height="12px" />
                    </div>
                    <Skeleton width="80px" height="28px" className="rounded" />
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

export default CourseDetailSkeleton;
