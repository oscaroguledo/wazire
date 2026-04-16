import React from 'react';
import { motion } from 'framer-motion';
import { Shimmer } from '@/components/Skeleton';

export function SubmissionsSkeleton() {
  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-6">
        <Shimmer className="h-5 w-40" />
      </div>

      {/* 4 stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 mb-8">
        {[
          'bg-[var(--color-primary-50)]',
          'bg-[var(--color-primary-50)]',
          'bg-[var(--color-success-100)]',
          'bg-[var(--color-warning-100)]',
        ].map((iconBg, i) => (
          <div key={i} className="surface-card p-6">
            <div className="flex items-center justify-between">
              <div>
                <Shimmer className="h-4 w-24 mb-3" />
                <Shimmer className="h-9 w-14" />
              </div>
              <div className={`${iconBg} p-3 rounded-lg`}>
                <Shimmer className="h-8 w-8 rounded" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="surface-card overflow-hidden">
        {/* Table header */}
        <div className="bg-[var(--color-bg-hover)] border-b border-[var(--color-border-light)] px-6 py-4 hidden lg:grid grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Shimmer key={i} className="h-4 w-20" />
          ))}
        </div>

        {/* Table rows */}
        <div className="divide-y divide-[var(--color-border-light)]">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="px-6 py-4 hidden lg:grid grid-cols-5 gap-4 items-center">
              <div className="flex items-center gap-3">
                <Shimmer className="h-9 w-9 rounded-lg flex-shrink-0" />
                <div>
                  <Shimmer className="h-4 w-28 mb-1.5" />
                  <Shimmer className="h-3 w-16" />
                </div>
              </div>
              <Shimmer className="h-4 w-20" />
              <Shimmer className="h-4 w-16" />
              <Shimmer className="h-6 w-20 rounded-full" />
              <Shimmer className="h-7 w-20 rounded-lg" />
            </div>
          ))}

          {/* Mobile rows */}
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={`m-${i}`} className="p-4 lg:hidden">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <Shimmer className="h-9 w-9 rounded-lg flex-shrink-0" />
                  <div>
                    <Shimmer className="h-4 w-28 mb-1.5" />
                    <Shimmer className="h-3 w-16" />
                  </div>
                </div>
                <Shimmer className="h-6 w-20 rounded-full" />
              </div>
              <div className="flex items-center justify-between">
                <Shimmer className="h-3 w-20" />
                <Shimmer className="h-4 w-16" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default SubmissionsSkeleton;
