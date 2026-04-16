import React from 'react';
import { PageSkeleton, Skeleton, CardSkeleton, TableSkeleton, ListSkeleton } from './Skeleton';

/**
 * Example component showing how to use skeleton components
 * This demonstrates various patterns for implementing loading states
 */
export function SkeletonExample() {
  return (
    <div className="space-y-8 p-6">
      <h1 className="text-2xl font-bold text-[var(--color-text-primary)] mb-6">Skeleton Component Examples</h1>
      
      {/* Basic Skeleton Usage */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">Basic Skeleton</h2>
        <div className="space-y-2">
          <Skeleton width="200px" height="20px" />
          <Skeleton width="100%" height="16px" />
          <Skeleton width="80%" height="16px" />
        </div>
      </section>

      {/* Text Skeleton */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">Text Skeleton</h2>
        <Skeleton variant="text" lines={3} />
      </section>

      {/* Card Skeleton */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">Card Skeleton</h2>
        <CardSkeleton />
      </section>

      {/* Table Skeleton */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">Table Skeleton</h2>
        <TableSkeleton rows={3} columns={4} />
      </section>

      {/* List Skeleton */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">List Skeleton</h2>
        <ListSkeleton items={3} />
      </section>

      {/* Avatar and Button Skeletons */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">UI Element Skeletons</h2>
        <div className="flex items-center space-x-4">
          <Skeleton variant="avatar" />
          <div className="flex-1">
            <Skeleton variant="text" lines={1} width="150px" />
            <Skeleton variant="text" lines={1} width="100px" />
          </div>
          <Skeleton variant="button" />
        </div>
      </section>
    </div>
  );
}

/**
 * Example of how to implement loading states in a typical page component
 */
export function ExamplePageWithLoading() {
  const [loading, setLoading] = React.useState(true);
  const [data, setData] = React.useState<any[]>([]);

  // Simulate data loading - immediate execution
  React.useEffect(() => {
    setData([
      { id: 1, name: 'Item 1', description: 'Description for item 1' },
      { id: 2, name: 'Item 2', description: 'Description for item 2' },
      { id: 3, name: 'Item 3', description: 'Description for item 3' },
      { id: 4, name: 'Item 4', description: 'Description for item 4' },
      { id: 5, name: 'Item 5', description: 'Description for item 5' },
    ]);
  }, []);

  if (loading) {
    return (
      <PageSkeleton>
        {/* Custom loading content for this page */}
        <div className="space-y-6">
          {/* Page header skeleton */}
          <div className="space-y-2">
            <Skeleton width="300px" height="32px" />
            <Skeleton width="500px" height="20px" />
          </div>

          {/* Stats cards skeleton */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>

          {/* Data table skeleton */}
          <TableSkeleton rows={5} columns={4} />
        </div>
      </PageSkeleton>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-[var(--color-text-primary)]">Example Page</h1>
      <p className="text-[var(--color-text-secondary)]">This page demonstrates skeleton loading states.</p>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {data.map((item) => (
          <div key={item.id} className="bg-[var(--color-bg-card)] p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold">{item.name}</h3>
            <p className="text-[var(--color-text-secondary)]">{item.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Quick usage patterns for different scenarios
 */
export const SkeletonUsagePatterns = {
  // For pages with complex layouts
  fullPage: (children: React.ReactNode) => (
    <PageSkeleton>{children}</PageSkeleton>
  ),

  // For card grids
  cardGrid: (count: number) => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  ),

  // For data tables
  dataTable: (rows: number, columns: number) => (
    <TableSkeleton rows={rows} columns={columns} />
  ),

  // For lists of items
  itemList: (items: number) => (
    <ListSkeleton items={items} />
  ),

  // For forms
  form: () => (
    <div className="space-y-4">
      <Skeleton variant="text" lines={1} width="150px" />
      <Skeleton height="40px" />
      <Skeleton variant="text" lines={1} width="120px" />
      <Skeleton height="40px" />
      <Skeleton variant="button" />
    </div>
  ),
};

export default SkeletonExample;
