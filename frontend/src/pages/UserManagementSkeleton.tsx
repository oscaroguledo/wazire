import React from 'react';
import { motion } from 'framer-motion';
import { Shimmer } from '@/components/Skeleton';

export function UserManagementSkeleton() {
  return (
    <div>
      {/* Breadcrumb row + Add User button */}
      <div className="flex items-center justify-between mb-5">
        <Shimmer className="h-5 w-48" />
        <Shimmer className="h-9 w-28 rounded-lg" />
      </div>

      {/* Search + filters row */}
      <div className="flex gap-3 mb-5">
        <Shimmer className="h-10 flex-1 max-w-sm" />
        <Shimmer className="h-10 w-36 rounded-lg" />
        <Shimmer className="h-10 w-36 rounded-lg" />
      </div>

      {/* Table */}
      <div className="surface-card overflow-hidden">
        {/* Table header */}
        <div className="bg-[var(--color-bg-hover)] border-b border-[var(--color-border-light)] px-6 py-3 hidden md:grid grid-cols-5 gap-4">
          {['User', 'Role', 'Status', 'Created', 'Actions'].map((col) => (
            <Shimmer key={col} className="h-4 w-16" />
          ))}
        </div>

        {/* Table rows */}
        <div className="divide-y divide-[var(--color-border-light)]">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="px-6 py-4 hidden md:grid grid-cols-5 gap-4 items-center">
              <div className="flex items-center gap-3">
                <Shimmer className="h-9 w-9 rounded-lg flex-shrink-0" />
                <div>
                  <Shimmer className="h-4 w-28 mb-1.5" />
                  <Shimmer className="h-3 w-36" />
                </div>
              </div>
              <Shimmer className="h-6 w-20 rounded-full" />
              <Shimmer className="h-6 w-16 rounded-full" />
              <Shimmer className="h-4 w-20" />
              <div className="flex gap-2">
                <Shimmer className="h-7 w-14 rounded-lg" />
                <Shimmer className="h-7 w-18 rounded-lg" />
              </div>
            </div>
          ))}

          {/* Mobile rows */}
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={`m-${i}`} className="p-4 md:hidden space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Shimmer className="h-9 w-9 rounded-lg flex-shrink-0" />
                  <div>
                    <Shimmer className="h-4 w-28 mb-1.5" />
                    <Shimmer className="h-3 w-36" />
                  </div>
                </div>
                <Shimmer className="h-6 w-16 rounded-full" />
              </div>
              <div className="flex gap-2 pt-2 border-t border-[var(--color-border-light)]">
                <Shimmer className="h-8 flex-1 rounded-lg" />
                <Shimmer className="h-8 flex-1 rounded-lg" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between mt-4">
        <Shimmer className="h-4 w-32" />
        <div className="flex gap-2">
          <Shimmer className="h-8 w-20 rounded-lg" />
          <Shimmer className="h-8 w-8 rounded-lg" />
          <Shimmer className="h-8 w-20 rounded-lg" />
        </div>
      </div>
    </div>
  );
}

export default UserManagementSkeleton;
