'use client';

interface TrendIndicatorProps {
  trend: 'rising' | 'falling' | 'stable';
  change: number | null;
}

export function TrendIndicator({ trend, change }: TrendIndicatorProps) {
  const trendConfig = {
    rising: {
      icon: '↑',
      color: 'text-red-400',
      label: 'Rising',
    },
    falling: {
      icon: '↓',
      color: 'text-green-400',
      label: 'Falling',
    },
    stable: {
      icon: '→',
      color: 'text-yellow-400',
      label: 'Stable',
    },
  };

  const config = trendConfig[trend];

  return (
    <div className={`flex items-center gap-1 ${config.color}`}>
      <span className="text-lg">{config.icon}</span>
      <span className="text-sm">
        {config.label}
        {change !== null && (
          <span className="ml-1 opacity-80">
            ({change >= 0 ? '+' : ''}{change.toFixed(0)}%)
          </span>
        )}
      </span>
    </div>
  );
}
