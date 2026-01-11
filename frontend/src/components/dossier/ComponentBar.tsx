'use client';

interface ComponentBarProps {
  label: string;
  value: number; // 0-100
  weight: number; // e.g., 0.4 for 40%
  color?: string;
  showWeight?: boolean;
}

export function ComponentBar({
  label,
  value,
  weight,
  color = '#3b82f6',
  showWeight = true,
}: ComponentBarProps) {
  const percentage = Math.min(100, Math.max(0, value));
  const weightPercent = Math.round(weight * 100);

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-dark-muted">
          {label}
          {showWeight && (
            <span className="text-dark-muted/60 ml-1">({weightPercent}%)</span>
          )}
        </span>
        <span className="font-medium text-white">{Math.round(value)}</span>
      </div>
      <div className="h-2 bg-dark-border rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500 ease-out"
          style={{
            width: `${percentage}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}
