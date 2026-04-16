import React from 'react';
import { motion } from 'framer-motion';
import { Shimmer } from '@/components/Skeleton';

export function ExamsSkeleton() {
  return (
    <div>
      {/* Header row */}
      <div className="flex items-center justify-between mb-6">
        <Shimmer className="h-5 w-40" />
        <Shimmer className="h-9 w-32 rounded-lg" />
      </div>

      {/* Search + filter row */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <Shimmer className="h-10 flex-1 max-w-md" />
        <Shimmer className="h-10 w-64 rounded-lg" />
        <Shimmer className="h-10 w-40 rounded-lg" />
      </div>

      {/* Grid of exam card skeletons */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="surface-card overflow-hidden">
            <div className="p-6 pb-4">
              {/* Icon + badge row */}
              <div className="flex items-start justify-between mb-4">
                <Shimmer className="h-12 w-12 rounded-xl" />
                <Shimmer className="h-6 w-20 rounded-full" />
              </div>
              {/* Title */}
              <Shimmer className="h-5 w-3/4 mb-2" />
              <Shimmer className="h-4 w-1/2 mb-4" />
              {/* Meta row */}
              <div className="flex items-center gap-4">
                <Shimmer className="h-4 w-16" />
                <Shimmer className="h-4 w-20" />
              </div>
            </div>
            {/* Footer */}
            <div className="px-4 py-3 bg-[var(--color-bg-hover)] border-t border-[var(--color-border-light)] flex justify-end gap-2">
              <Shimmer className="h-7 w-14 rounded-lg" />
              <Shimmer className="h-7 w-16 rounded-lg" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ExamsSkeleton;
