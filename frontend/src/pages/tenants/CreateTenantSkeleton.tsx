import React from 'react';
import { motion } from 'framer-motion';
import Skeleton from '@/components/Skeleton';

/**
 * CreateTenant page skeleton component
 * Matches the exact layout of the CreateTenant page
 */
export function CreateTenantSkeleton() {
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

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-4xl"
      >
        <div className="bg-[var(--color-bg-card)] rounded-xl shadow-sm overflow-hidden">
          {/* Form Header */}
          <div className="border-b border-[var(--color-border-light)] p-6">
            <Skeleton width="180px" height="24px" className="mb-2" />
            <Skeleton width="400px" height="16px" />
          </div>

          {/* Form Content */}
          <div className="p-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left Column */}
              <div className="space-y-6">
                {/* Basic Information */}
                <div>
                  <Skeleton width="150px" height="18px" className="mb-4" />
                  <div className="space-y-4">
                    <div>
                      <Skeleton width="80px" height="14px" className="mb-2" />
                      <Skeleton width="100%" height="40px" className="rounded" />
                    </div>
                    <div>
                      <Skeleton width="100px" height="14px" className="mb-2" />
                      <Skeleton width="100%" height="40px" className="rounded" />
                    </div>
                    <div>
                      <Skeleton width="60px" height="14px" className="mb-2" />
                      <Skeleton width="100%" height="40px" className="rounded" />
                    </div>
                  </div>
                </div>

                {/* Contact Information */}
                <div>
                  <Skeleton width="140px" height="18px" className="mb-4" />
                  <div className="space-y-4">
                    <div>
                      <Skeleton width="80px" height="14px" className="mb-2" />
                      <Skeleton width="100%" height="40px" className="rounded" />
                    </div>
                    <div>
                      <Skeleton width="70px" height="14px" className="mb-2" />
                      <Skeleton width="100%" height="40px" className="rounded" />
                    </div>
                    <div>
                      <Skeleton width="90px" height="14px" className="mb-2" />
                      <Skeleton width="100%" height="40px" className="rounded" />
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column */}
              <div className="space-y-6">
                {/* Configuration */}
                <div>
                  <Skeleton width="120px" height="18px" className="mb-4" />
                  <div className="space-y-4">
                    <div>
                      <Skeleton width="100px" height="14px" className="mb-2" />
                      <Skeleton width="100%" height="40px" className="rounded" />
                    </div>
                    <div>
                      <Skeleton width="80px" height="14px" className="mb-2" />
                      <Skeleton width="100%" height="40px" className="rounded" />
                    </div>
                    <div>
                      <Skeleton width="110px" height="14px" className="mb-2" />
                      <Skeleton width="100%" height="40px" className="rounded" />
                    </div>
                  </div>
                </div>

                {/* Settings */}
                <div>
                  <Skeleton width="80px" height="18px" className="mb-4" />
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 border border-[var(--color-border-light)] rounded-lg">
                      <div>
                        <Skeleton width="120px" height="16px" className="mb-1" />
                        <Skeleton width="180px" height="12px" />
                      </div>
                      <Skeleton width="48px" height="24px" className="rounded" />
                    </div>
                    <div className="flex items-center justify-between p-3 border border-[var(--color-border-light)] rounded-lg">
                      <div>
                        <Skeleton width="100px" height="16px" className="mb-1" />
                        <Skeleton width="160px" height="12px" />
                      </div>
                      <Skeleton width="48px" height="24px" className="rounded" />
                    </div>
                    <div className="flex items-center justify-between p-3 border border-[var(--color-border-light)] rounded-lg">
                      <div>
                        <Skeleton width="110px" height="16px" className="mb-1" />
                        <Skeleton width="170px" height="12px" />
                      </div>
                      <Skeleton width="48px" height="24px" className="rounded" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Admin User Section */}
            <div className="mt-8 pt-6 border-t border-[var(--color-border-light)]">
              <Skeleton width="140px" height="18px" className="mb-4" />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Skeleton width="80px" height="14px" className="mb-2" />
                  <Skeleton width="100%" height="40px" className="rounded" />
                </div>
                <div>
                  <Skeleton width="90px" height="14px" className="mb-2" />
                  <Skeleton width="100%" height="40px" className="rounded" />
                </div>
                <div>
                  <Skeleton width="70px" height="14px" className="mb-2" />
                  <Skeleton width="100%" height="40px" className="rounded" />
                </div>
              </div>
            </div>
          </div>

          {/* Form Actions */}
          <div className="border-t border-[var(--color-border-light)] p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Skeleton width="20px" height="20px" className="rounded" />
                <Skeleton width="200px" height="14px" />
              </div>
              <div className="flex space-x-3">
                <Skeleton width="100px" height="40px" className="rounded" />
                <Skeleton width="120px" height="40px" className="rounded" />
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default CreateTenantSkeleton;
