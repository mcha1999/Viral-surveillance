'use client';

import { useMemo } from 'react';
import { differenceInHours, differenceInDays, format } from 'date-fns';

interface DataFreshnessProps {
  lastUpdated: string | null | undefined;
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

type FreshnessLevel = 'current' | 'recent' | 'stale' | 'old' | 'expired';

interface FreshnessInfo {
  level: FreshnessLevel;
  label: string;
  color: string;
  bgColor: string;
  description: string;
}

export function DataFreshness({ lastUpdated, showLabel = true, size = 'md' }: DataFreshnessProps) {
  const freshness = useMemo((): FreshnessInfo => {
    if (!lastUpdated) {
      return {
        level: 'expired',
        label: 'Unknown',
        color: 'text-dark-muted',
        bgColor: 'bg-dark-muted/20',
        description: 'Update time unknown',
      };
    }

    const date = new Date(lastUpdated);
    const now = new Date();
    const hoursAgo = differenceInHours(now, date);
    const daysAgo = differenceInDays(now, date);

    if (hoursAgo < 24) {
      return {
        level: 'current',
        label: 'Current',
        color: 'text-green-400',
        bgColor: 'bg-green-500/20',
        description: hoursAgo < 1 ? 'Just updated' : `${hoursAgo}h ago`,
      };
    }

    if (daysAgo < 3) {
      return {
        level: 'recent',
        label: 'Recent',
        color: 'text-blue-400',
        bgColor: 'bg-blue-500/20',
        description: `${daysAgo} day${daysAgo > 1 ? 's' : ''} ago`,
      };
    }

    if (daysAgo < 7) {
      return {
        level: 'stale',
        label: 'Stale',
        color: 'text-amber-400',
        bgColor: 'bg-amber-500/20',
        description: `${daysAgo} days ago`,
      };
    }

    if (daysAgo < 30) {
      return {
        level: 'old',
        label: 'Old',
        color: 'text-orange-400',
        bgColor: 'bg-orange-500/20',
        description: format(date, 'MMM d'),
      };
    }

    return {
      level: 'expired',
      label: 'Outdated',
      color: 'text-red-400',
      bgColor: 'bg-red-500/20',
      description: format(date, 'MMM d, yyyy'),
    };
  }, [lastUpdated]);

  const sizeClasses = {
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-xs px-2 py-1',
  };

  return (
    <div className="flex items-center gap-2">
      {/* Indicator dot */}
      <span className={`inline-flex items-center gap-1.5 ${sizeClasses[size]} rounded-full ${freshness.bgColor}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${freshness.color.replace('text-', 'bg-')}`} />
        {showLabel && (
          <span className={freshness.color}>{freshness.label}</span>
        )}
      </span>

      {/* Description */}
      <span className="text-dark-muted text-xs">
        {freshness.description}
      </span>
    </div>
  );
}

// Compact version for inline use
export function DataFreshnessDot({ lastUpdated }: { lastUpdated: string | null | undefined }) {
  const freshness = useMemo(() => {
    if (!lastUpdated) return 'bg-dark-muted';

    const date = new Date(lastUpdated);
    const daysAgo = differenceInDays(new Date(), date);

    if (daysAgo < 1) return 'bg-green-400';
    if (daysAgo < 3) return 'bg-blue-400';
    if (daysAgo < 7) return 'bg-amber-400';
    if (daysAgo < 30) return 'bg-orange-400';
    return 'bg-red-400';
  }, [lastUpdated]);

  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${freshness}`}
      title={lastUpdated ? `Last updated: ${new Date(lastUpdated).toLocaleString()}` : 'Unknown'}
    />
  );
}
