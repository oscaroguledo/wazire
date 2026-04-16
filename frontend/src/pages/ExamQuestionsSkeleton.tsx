import React from 'react';
import { motion } from 'framer-motion';

export function ExamQuestionsSkeleton() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <div className="animate-pulse space-y-6">
        {/* Header skeleton */}
        <div className="flex items-center justify-between mb-8">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 bg-[var(--color-bg-hover)] rounded"></div>
              <div className="h-8 w-64 bg-[var(--color-bg-hover)] rounded"></div>
            </div>
            <div className="h-4 w-96 bg-[var(--color-bg-hover)] rounded"></div>
          </div>
        </div>
        
        {/* Stats cards skeleton */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-[var(--color-bg-card)] rounded-lg p-4 shadow-sm">
              <div className="flex items-center gap-2 mb-2">
                <div className="h-4 w-4 bg-[var(--color-bg-hover)] rounded"></div>
                <div className="h-4 w-20 bg-[var(--color-bg-hover)] rounded"></div>
              </div>
              <div className="h-8 w-16 bg-[var(--color-bg-hover)] rounded"></div>
            </div>
          ))}
        </div>
        
        {/* Tabs skeleton */}
        <div className="bg-[var(--color-bg-card)] rounded-xl shadow-sm">
          <div className="border-b border-[var(--color-border-light)] px-6">
            <div className="flex space-x-8">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-12 w-24 bg-[var(--color-bg-hover)] rounded-t"></div>
              ))}
            </div>
          </div>
          
          {/* Questions list skeleton */}
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="h-6 w-32 bg-[var(--color-bg-hover)] rounded"></div>
              <div className="flex gap-2">
                <div className="h-8 w-24 bg-[var(--color-bg-hover)] rounded"></div>
                <div className="h-8 w-28 bg-[var(--color-bg-hover)] rounded"></div>
              </div>
            </div>
            
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="border border-[var(--color-border-light)] rounded-lg p-4"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="h-6 w-10 bg-[var(--color-bg-hover)] rounded-full"></div>
                      <div className="h-5 w-48 bg-[var(--color-bg-hover)] rounded"></div>
                    </div>
                    <div className="flex gap-2">
                      <div className="h-6 w-16 bg-[var(--color-bg-hover)] rounded"></div>
                      <div className="h-6 w-14 bg-[var(--color-bg-hover)] rounded"></div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="h-4 w-full bg-[var(--color-bg-hover)] rounded"></div>
                    <div className="h-4 w-3/4 bg-[var(--color-bg-hover)] rounded"></div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ExamQuestionsSkeleton;
