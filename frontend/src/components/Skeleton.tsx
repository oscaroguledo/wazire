import React from 'react';
import { motion } from 'framer-motion';

/**
 * Shimmer helper component for inline skeletons
 */
export function Shimmer({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse bg-[var(--color-bg-hover)] rounded-lg ${className}`} />;
}

interface SkeletonProps {
  className?: string;
  variant?: 'default' | 'card' | 'table' | 'text' | 'avatar' | 'button';
  width?: string | number;
  height?: string | number;
  lines?: number;
  animate?: boolean;
}

/**
 * Reusable skeleton loading component for various UI patterns
 */
export function Skeleton({ 
  className = '', 
  variant = 'default',
  width,
  height,
  lines = 1,
  animate = true 
}: SkeletonProps) {
  const baseClasses = 'bg-[var(--color-bg-hover)] rounded-lg';
  const animationClasses = animate ? 'animate-pulse' : '';
  const combinedClasses = `${baseClasses} ${animationClasses} ${className}`;

  const renderSkeleton = () => {
    switch (variant) {
      case 'card':
        return (
          <div className={`${combinedClasses} p-6 space-y-4`}>
            <div className="h-4 bg-[var(--color-bg-hover)] rounded w-3/4"></div>
            <div className="h-3 bg-[var(--color-bg-hover)] rounded w-1/2"></div>
            <div className="h-3 bg-[var(--color-bg-hover)] rounded w-2/3"></div>
          </div>
        );

      case 'table':
        return (
          <div className={`${combinedClasses} space-y-2`}>
            <div className="flex space-x-4">
              <div className="h-4 bg-[var(--color-bg-hover)] rounded flex-1"></div>
              <div className="h-4 bg-[var(--color-bg-hover)] rounded flex-1"></div>
              <div className="h-4 bg-[var(--color-bg-hover)] rounded flex-1"></div>
              <div className="h-4 bg-[var(--color-bg-hover)] rounded flex-1"></div>
            </div>
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex space-x-4">
                <div className="h-3 bg-[var(--color-bg-hover)] rounded flex-1"></div>
                <div className="h-3 bg-[var(--color-bg-hover)] rounded flex-1"></div>
                <div className="h-3 bg-[var(--color-bg-hover)] rounded flex-1"></div>
                <div className="h-3 bg-[var(--color-bg-hover)] rounded flex-1"></div>
              </div>
            ))}
          </div>
        );

      case 'text':
        return (
          <div className={`${combinedClasses} space-y-2`}>
            {Array.from({ length: lines }).map((_, i) => (
              <div
                key={i}
                className="h-3 bg-[var(--color-bg-hover)] rounded"
                style={{
                  width: i === lines - 1 ? '60%' : '100%'
                }}
              ></div>
            ))}
          </div>
        );

      case 'avatar':
        return (
          <div className={`${combinedClasses} w-12 h-12 rounded-full`}></div>
        );

      case 'button':
        return (
          <div className={`${combinedClasses} h-10 w-24 rounded-md`}></div>
        );

      default:
        return (
          <div 
            className={`${combinedClasses}`}
            style={{
              width: width || '100%',
              height: height || '1rem'
            }}
          ></div>
        );
    }
  };

  if (animate) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        {renderSkeleton()}
      </motion.div>
    );
  }

  return <>{renderSkeleton()}</>;
}

/**
 * Page skeleton wrapper for full page loading states
 */
interface PageSkeletonProps {
  children?: React.ReactNode;
  className?: string;
  header?: boolean;
  sidebar?: boolean;
  footer?: boolean;
}

export function PageSkeleton({ 
  children, 
  className = '',
  header = true,
  sidebar = false,
  footer = false 
}: PageSkeletonProps) {
  return (
    <div className={`min-h-screen bg-[var(--color-bg-subtle)] ${className}`}>
      {/* Header Skeleton */}
      {header && (
        <div className="bg-[var(--color-bg-card)] border-b border-[var(--color-border-light)]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4">
              <Skeleton variant="text" lines={1} width="200px" />
              <div className="flex space-x-4">
                <Skeleton variant="avatar" />
                <Skeleton variant="button" />
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex">
        {/* Sidebar Skeleton */}
        {sidebar && (
          <div className="w-64 bg-[var(--color-bg-card)] border-r border-[var(--color-border-light)] min-h-screen">
            <div className="p-4 space-y-4">
              <Skeleton variant="text" lines={1} width="150px" />
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} variant="text" lines={1} width="120px" />
              ))}
            </div>
          </div>
        )}

        {/* Main Content */}
        <main className="flex-1 p-6">
          {children || (
            <div className="max-w-7xl mx-auto space-y-6">
              {/* Page Title Skeleton */}
              <div className="space-y-2">
                <Skeleton variant="text" lines={1} width="300px" height="32px" />
                <Skeleton variant="text" lines={1} width="500px" height="20px" />
              </div>

              {/* Stats Cards Skeleton */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} variant="card" />
                ))}
              </div>

              {/* Table Skeleton */}
              <Skeleton variant="table" />

              {/* Action Buttons Skeleton */}
              <div className="flex justify-end space-x-4">
                <Skeleton variant="button" />
                <Skeleton variant="button" />
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Footer Skeleton */}
      {footer && (
        <div className="bg-[var(--color-bg-card)] border-t border-[var(--color-border-light)] mt-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <Skeleton variant="text" lines={1} width="200px" />
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Card skeleton for content cards
 */
export function CardSkeleton({ className = '' }: { className?: string }) {
  return (
    <div className={`bg-[var(--color-bg-card)] rounded-xl shadow-sm p-6 space-y-4 ${className}`}>
      <div className="flex items-center space-x-4">
        <Skeleton variant="avatar" />
        <div className="flex-1 space-y-2">
          <Skeleton variant="text" lines={1} width="150px" />
          <Skeleton variant="text" lines={1} width="100px" />
        </div>
      </div>
      <Skeleton variant="text" lines={3} />
      <div className="flex justify-between items-center">
        <Skeleton variant="button" />
        <Skeleton variant="button" />
      </div>
    </div>
  );
}

/**
 * Table skeleton for data tables
 */
export function TableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="bg-[var(--color-bg-card)] rounded-xl shadow-sm overflow-hidden">
      {/* Header */}
      <div className="border-b border-[var(--color-border-light)] p-4">
        <div className="flex space-x-4">
          {Array.from({ length: columns }).map((_, i) => (
            <Skeleton key={i} variant="text" lines={1} width="120px" height="20px" />
          ))}
        </div>
      </div>
      
      {/* Rows */}
      <div className="divide-y divide-[var(--color-border-light)]">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="p-4">
            <div className="flex space-x-4">
              {Array.from({ length: columns }).map((_, colIndex) => (
                <Skeleton key={colIndex} variant="text" lines={1} height="16px" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * List skeleton for lists of items
 */
export function ListSkeleton({ items = 5 }: { items?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: items }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

export default Skeleton;
