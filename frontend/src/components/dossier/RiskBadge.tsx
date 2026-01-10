'use client';

interface RiskBadgeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
}

export function RiskBadge({ score, size = 'md' }: RiskBadgeProps) {
  const level = score >= 70 ? 'critical' : score >= 50 ? 'high' : score >= 30 ? 'medium' : 'low';

  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1.5',
    lg: 'text-base px-4 py-2',
  };

  const levelClasses = {
    low: 'bg-green-500/20 text-green-400 border-green-500/30',
    medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  };

  const levelLabels = {
    low: 'Low',
    medium: 'Medium',
    high: 'High',
    critical: 'Critical',
  };

  return (
    <div className={`inline-flex items-center gap-2 rounded-full border ${sizeClasses[size]} ${levelClasses[level]}`}>
      <span className="font-bold">{score.toFixed(0)}</span>
      <span className="opacity-80">{levelLabels[level]}</span>
    </div>
  );
}
