import React from 'react';
import { motion } from 'framer-motion';
import { Shimmer } from '@/components/Skeleton';

export function ProfileSkeleton() {
  return (
    <div className="max-w-6xl">
      {/* Breadcrumb + header */}
      <div className="mb-8">
        <Shimmer className="h-5 w-40 mb-4" />
        <Shimmer className="h-10 w-56 mb-2" />
      </div>

      {/* Stats skeleton */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        {[1, 2, 3].map((i) => (
          <div key={i} className="surface-card p-6">
            <div className="flex items-center justify-between">
              <div>
                <Shimmer className="h-4 w-24 mb-2" />
                <Shimmer className="h-8 w-16" />
              </div>
              <Shimmer className="h-12 w-12 rounded-xl" />
            </div>
          </div>
        ))}
      </div>

      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main form card */}
        <div className="lg:col-span-2 surface-card p-8">
          {/* Avatar + identity */}
          <div className="flex items-center gap-6 mb-8 pb-6 border-b border-[var(--color-border-light)]">
            <Shimmer className="h-24 w-24 rounded-full flex-shrink-0" />
            <div className="flex-1">
              <Shimmer className="h-8 w-48 mb-2" />
              <Shimmer className="h-4 w-32 mb-4" />
              <Shimmer className="h-6 w-20 rounded-full" />
            </div>
          </div>

          {/* Personal info section */}
          <div className="mb-8">
            <Shimmer className="h-5 w-32 mb-4" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[1, 2, 3, 4].map((_, i) => (
                <div key={i}>
                  <Shimmer className="h-4 w-20 mb-2" />
                  <Shimmer className="h-12 w-full rounded-lg" />
                </div>
              ))}
            </div>
          </div>

          {/* Password section */}
          <div className="pt-6 border-t border-[var(--color-border-light)]">
            <Shimmer className="h-5 w-36 mb-4" />
            <Shimmer className="h-4 w-48 mb-4" />
            <Shimmer className="h-12 w-full rounded-lg" />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-6">
            <Shimmer className="h-10 flex-1 rounded-lg" />
            <Shimmer className="h-10 w-28 rounded-lg" />
          </div>
        </div>

        {/* Sidebar cards */}
        <div className="space-y-6">
          {/* Account Info */}
          <div className="surface-card p-6">
            <Shimmer className="h-5 w-28 mb-4" />
            <div className="space-y-4">
              {[1, 2, 3].map((_, i) => (
                <div key={i} className="flex items-center gap-3">
                  <Shimmer className="h-9 w-9 rounded-lg" />
                  <div className="flex-1">
                    <Shimmer className="h-3 w-24 mb-1" />
                    <Shimmer className="h-4 w-32" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="surface-card p-6">
            <Shimmer className="h-5 w-28 mb-4" />
            <Shimmer className="h-10 w-full rounded-lg" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProfileSkeleton;
