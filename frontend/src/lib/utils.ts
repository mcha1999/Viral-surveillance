import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Utility for merging Tailwind CSS classes with proper conflict resolution
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a number with locale-aware formatting
 */
export function formatNumber(num: number, decimals = 0): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num);
}

/**
 * Format a number in compact notation (e.g., 1.2K, 3.4M)
 */
export function formatCompactNumber(num: number): string {
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(num);
}

/**
 * Format a number as a percentage
 */
export function formatPercentage(num: number, showSign = false): string {
  const sign = showSign && num > 0 ? '+' : '';
  return `${sign}${num.toFixed(0)}%`;
}

/**
 * Format a date as relative time (e.g., "5 minutes ago")
 */
export function formatRelativeTime(date: Date | string): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - dateObj.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

  return dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Risk level type based on score thresholds
 */
export type RiskLevel = 'low' | 'moderate' | 'elevated' | 'high' | 'very-high';

/**
 * Get risk level from a numeric score (0-100)
 */
export function getRiskLevel(score: number | null): RiskLevel {
  if (score === null) return 'low';
  if (score <= 20) return 'low';
  if (score <= 40) return 'moderate';
  if (score <= 60) return 'elevated';
  if (score <= 80) return 'high';
  return 'very-high';
}

/**
 * Get human-readable risk label
 */
export function getRiskLabel(score: number | null): string {
  const level = getRiskLevel(score);
  const labels: Record<RiskLevel, string> = {
    low: 'Low',
    moderate: 'Moderate',
    elevated: 'Elevated',
    high: 'High',
    'very-high': 'Very High',
  };
  return labels[level];
}

/**
 * Get risk description for tooltips/explanations
 */
export function getRiskDescription(score: number | null): string {
  const level = getRiskLevel(score);
  const descriptions: Record<RiskLevel, string> = {
    low: 'Minimal viral activity detected',
    moderate: 'Moderate levels, normal caution advised',
    elevated: 'Above average activity',
    high: 'Significant viral activity',
    'very-high': 'Extreme levels detected',
  };
  return descriptions[level];
}

/**
 * Data freshness status type
 */
export type FreshnessStatus = 'current' | 'stale' | 'old' | 'expired';

/**
 * Get freshness status based on last update time
 */
export function getFreshnessStatus(lastUpdated: Date | string | null): FreshnessStatus {
  if (!lastUpdated) return 'expired';
  const dateObj = typeof lastUpdated === 'string' ? new Date(lastUpdated) : lastUpdated;
  const diffDays = Math.floor((new Date().getTime() - dateObj.getTime()) / 86400000);

  if (diffDays <= 2) return 'current';
  if (diffDays <= 14) return 'stale';
  if (diffDays <= 30) return 'old';
  return 'expired';
}

/**
 * Get freshness label for display
 */
export function getFreshnessLabel(status: FreshnessStatus): string {
  const labels: Record<FreshnessStatus, string> = {
    current: 'Current',
    stale: 'Data may be outdated',
    old: 'Limited data',
    expired: 'Data expired',
  };
  return labels[status];
}

/**
 * Get trend indicator from weekly change
 */
export function getTrendFromChange(change: number | null): 'rising' | 'falling' | 'stable' {
  if (change === null) return 'stable';
  if (change > 5) return 'rising';
  if (change < -5) return 'falling';
  return 'stable';
}
