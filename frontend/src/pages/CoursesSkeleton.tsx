import React from 'react';
import { motion } from 'framer-motion';
import Skeleton from '@/components/Skeleton';

/**
 * Courses page skeleton component
 * Matches the exact layout of the Courses page
 */
export function CoursesSkeleton() {
  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <Skeleton width="200px" height="36px" className="mb-2" />
          <Skeleton width="350px" height="20px" />
        </div>
        <div className="flex space-x-3">
          <Skeleton width="100px" height="40px" className="rounded" />
          <Skeleton width="120px" height="40px" className="rounded" />
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

      {/* Course Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="bg-[var(--color-bg-card)] p-4 rounded-lg shadow-sm"
          >
            <Skeleton width="80px" height="16px" className="mb-2" />
            <Skeleton width="60px" height="24px" />
          </motion.div>
        ))}
      </div>

      {/* Courses Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 + i * 0.1 }}
            className="bg-[var(--color-bg-card)] rounded-xl shadow-sm overflow-hidden"
          >
            {/* Course Header */}
            <div className="p-6 border-b border-[var(--color-border-light)]">
              <div className="flex items-start justify-between mb-4">
                <Skeleton width="48px" height="48px" className="rounded-lg" />
                <Skeleton width="80px" height="24px" className="rounded" />
              </div>
              
              <Skeleton width="200px" height="20px" className="mb-2" />
              <Skeleton width="150px" height="16px" className="mb-4" />
              
              <Skeleton width="100%" height="12px" className="mb-2" />
              <Skeleton width="80%" height="12px" className="mb-4" />
              
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <Skeleton width="16px" height="16px" className="rounded" />
                  <Skeleton width="60px" height="12px" />
                </div>
                <div className="flex items-center space-x-2">
                  <Skeleton width="16px" height="16px" className="rounded" />
                  <Skeleton width="50px" height="12px" />
                </div>
              </div>
            </div>

            {/* Course Body */}
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <Skeleton width="80px" height="14px" className="mb-1" />
                  <Skeleton width="60px" height="16px" />
                </div>
                <Skeleton width="100px" height="32px" className="rounded" />
              </div>
              
              {/* Progress Bar */}
              <div className="mb-4">
                <div className="flex justify-between mb-2">
                  <Skeleton width="60px" height="12px" />
                  <Skeleton width="40px" height="12px" />
                </div>
                <Skeleton width="100%" height="8px" className="rounded" />
              </div>
              
              {/* Action Buttons */}
              <div className="flex space-x-2">
                <Skeleton width="100%" height="36px" className="rounded" />
                <Skeleton width="60px" height="36px" className="rounded" />
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Pagination */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
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

export default CoursesSkeleton;
