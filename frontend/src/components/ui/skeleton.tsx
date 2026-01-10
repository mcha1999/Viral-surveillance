"use client";

import { cn } from "@/lib/utils";

type SkeletonProps = React.HTMLAttributes<HTMLDivElement>;

function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-background-elevated", className)}
      {...props}
    />
  );
}

// Skeleton compositions for common use cases
function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn("space-y-3", className)}>
      <Skeleton className="h-32 w-full rounded-lg" />
      <div className="space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    </div>
  );
}

function SkeletonRiskScore({ className }: { className?: string }) {
  return (
    <div className={cn("p-4 rounded-lg border border-border space-y-3", className)}>
      <div className="flex justify-between items-start">
        <div className="space-y-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-10 w-16" />
        </div>
        <Skeleton className="h-6 w-24" />
      </div>
      <Skeleton className="h-2 w-full" />
    </div>
  );
}

function SkeletonDossierPanel({ className }: { className?: string }) {
  return (
    <div className={cn("p-4 space-y-4", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-24" />
        </div>
        <Skeleton className="h-8 w-8 rounded-full" />
      </div>

      {/* Risk Score */}
      <SkeletonRiskScore />

      {/* Chart */}
      <div className="space-y-2">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-40 w-full rounded-lg" />
      </div>

      {/* Variants */}
      <div className="space-y-2">
        <Skeleton className="h-4 w-24" />
        <div className="flex gap-2">
          <Skeleton className="h-20 w-28 rounded-lg" />
          <Skeleton className="h-20 w-28 rounded-lg" />
        </div>
      </div>

      {/* Flight routes */}
      <div className="space-y-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-12 w-full rounded-lg" />
        <Skeleton className="h-12 w-full rounded-lg" />
        <Skeleton className="h-12 w-full rounded-lg" />
      </div>
    </div>
  );
}

function SkeletonGlobe({ className }: { className?: string }) {
  return (
    <div className={cn("relative w-full h-full", className)}>
      {/* Globe circle */}
      <div className="absolute inset-0 flex items-center justify-center">
        <Skeleton className="w-[60%] aspect-square rounded-full" />
      </div>

      {/* Loading overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-background/50">
        <div className="flex gap-2">
          <div className="w-2 h-2 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
          <div className="w-2 h-2 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
          <div className="w-2 h-2 rounded-full bg-primary animate-bounce" />
        </div>
        <p className="text-foreground-secondary text-sm">Loading global viral data...</p>
      </div>
    </div>
  );
}

function SkeletonList({ count = 3, className }: { count?: number; className?: string }) {
  return (
    <div className={cn("space-y-3", className)}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

export {
  Skeleton,
  SkeletonCard,
  SkeletonRiskScore,
  SkeletonDossierPanel,
  SkeletonGlobe,
  SkeletonList,
};
