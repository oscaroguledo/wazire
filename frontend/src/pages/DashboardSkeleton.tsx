import React from 'react';
import { motion } from 'framer-motion';
import { Shimmer } from '@/components/Skeleton';

export function DashboardSkeleton() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="mb-8">
        <Shimmer className="h-4 w-32 mb-3 rounded" />
        <Shimmer className="h-8 w-64 mb-2" />
        <Shimmer className="h-4 w-48" />
      </div>

      {/* 6 stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="surface-card p-6">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <Shimmer className="h-4 w-28 mb-3" />
                <Shimmer className="h-9 w-16 mb-2" />
                <Shimmer className="h-3 w-24" />
              </div>
              <Shimmer className="h-12 w-12 rounded-xl flex-shrink-0" />
            </div>
          </div>
        ))}
      </div>

      {/* Quick actions card */}
      <div className="surface-card p-6">
        <Shimmer className="h-6 w-36 mb-6" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Shimmer key={i} className="h-10 rounded-lg" />
          ))}
        </div>
      </div>
    </div>
  );
}

export default DashboardSkeleton;
