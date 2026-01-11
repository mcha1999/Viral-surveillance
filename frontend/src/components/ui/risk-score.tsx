'use client';

import * as React from 'react';
import { cn, getRiskLevel, getRiskLabel, getRiskDescription, type RiskLevel } from '@/lib/utils';
import { Badge } from './badge';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface RiskScoreProps {
  score: number | null;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  showTrend?: boolean;
  trend?: 'rising' | 'falling' | 'stable';
  weeklyChange?: number | null;
  className?: string;
}

const riskColors: Record<RiskLevel, string> = {
  low: 'text-risk-low',
  moderate: 'text-risk-moderate',
  elevated: 'text-risk-elevated',
  high: 'text-risk-high',
  'very-high': 'text-risk-very-high',
};

const riskBgColors: Record<RiskLevel, string> = {
  low: 'bg-risk-low/20',
  moderate: 'bg-risk-moderate/20',
  elevated: 'bg-risk-elevated/20',
  high: 'bg-risk-high/20',
  'very-high': 'bg-risk-very-high/20',
};

const riskRingColors: Record<RiskLevel, string> = {
  low: 'ring-risk-low',
  moderate: 'ring-risk-moderate',
  elevated: 'ring-risk-elevated',
  high: 'ring-risk-high',
  'very-high': 'ring-risk-very-high',
};

function RiskScore({
  score,
  size = 'md',
  showLabel = true,
  showTrend = false,
  trend,
  weeklyChange,
  className,
}: RiskScoreProps) {
  const level = getRiskLevel(score);
  const label = getRiskLabel(score);
  const description = getRiskDescription(score);

  const sizeClasses = {
    sm: 'h-12 w-12 text-lg',
    md: 'h-16 w-16 text-2xl',
    lg: 'h-24 w-24 text-4xl',
  };

  const TrendIcon = trend === 'rising' ? TrendingUp : trend === 'falling' ? TrendingDown : Minus;
  const trendColor = trend === 'rising' ? 'text-risk-high' : trend === 'falling' ? 'text-risk-low' : 'text-foreground-muted';

  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div
        className={cn(
          'relative flex items-center justify-center rounded-full font-bold ring-2',
          sizeClasses[size],
          riskColors[level],
          riskBgColors[level],
          riskRingColors[level]
        )}
        title={description}
      >
        {score !== null ? Math.round(score) : '—'}
      </div>
      {showLabel && (
        <div className="flex flex-col">
          <span className={cn('font-semibold', riskColors[level])}>{label}</span>
          {showTrend && trend && (
            <div className={cn('flex items-center gap-1 text-sm', trendColor)}>
              <TrendIcon className="h-3 w-3" />
              {weeklyChange !== null && weeklyChange !== undefined && (
                <span>{weeklyChange > 0 ? '+' : ''}{weeklyChange.toFixed(0)}%</span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RiskScoreBadge({ score, className }: { score: number | null; className?: string }) {
  const level = getRiskLevel(score);
  const label = getRiskLabel(score);

  return (
    <Badge variant={level} className={className}>
      {score !== null ? `${Math.round(score)} - ${label}` : 'Unknown'}
    </Badge>
  );
}

function RiskScoreCompact({ score, className }: { score: number | null; className?: string }) {
  const level = getRiskLevel(score);

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center h-6 w-8 rounded text-xs font-bold',
        riskColors[level],
        riskBgColors[level],
        className
      )}
    >
      {score !== null ? Math.round(score) : '—'}
    </span>
  );
}

export { RiskScore, RiskScoreBadge, RiskScoreCompact };
