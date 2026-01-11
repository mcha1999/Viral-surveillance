'use client';

import { useState } from 'react';

interface ConfidenceIndicatorProps {
  confidence: number; // 0-1
  dataPointCount?: number;
  lastUpdated?: string | null;
  showDetails?: boolean;
}

export function ConfidenceIndicator({
  confidence,
  dataPointCount,
  lastUpdated,
  showDetails = false,
}: ConfidenceIndicatorProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const percentage = Math.round(confidence * 100);

  // Determine confidence level
  const getConfidenceLevel = () => {
    if (confidence >= 0.8) return { label: 'High', color: '#22c55e' };
    if (confidence >= 0.5) return { label: 'Medium', color: '#eab308' };
    return { label: 'Low', color: '#ef4444' };
  };

  const { label, color } = getConfidenceLevel();

  const getConfidenceExplanation = () => {
    const factors = [];
    if (dataPointCount !== undefined) {
      if (dataPointCount >= 10) {
        factors.push('Abundant data points');
      } else if (dataPointCount >= 5) {
        factors.push('Moderate data coverage');
      } else {
        factors.push('Limited data points');
      }
    }
    if (lastUpdated) {
      const daysAgo = Math.floor(
        (Date.now() - new Date(lastUpdated).getTime()) / (1000 * 60 * 60 * 24)
      );
      if (daysAgo <= 1) {
        factors.push('Data is current');
      } else if (daysAgo <= 7) {
        factors.push(`Data is ${daysAgo} days old`);
      } else {
        factors.push(`Data is ${daysAgo} days old (stale)`);
      }
    }
    return factors;
  };

  return (
    <div className="relative">
      <div
        className="flex items-center gap-2 cursor-help"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <span className="text-sm text-dark-muted">Confidence:</span>
        <div className="flex items-center gap-2">
          <div className="w-16 h-1.5 bg-dark-border rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{ width: `${percentage}%`, backgroundColor: color }}
            />
          </div>
          <span className="text-sm font-medium" style={{ color }}>
            {percentage}%
          </span>
        </div>
        <svg
          className="w-4 h-4 text-dark-muted"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </div>

      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute bottom-full left-0 mb-2 p-3 bg-dark-surface border border-dark-border rounded-lg shadow-lg z-50 w-64">
          <div className="text-sm">
            <div className="font-medium text-white mb-2">
              {label} Confidence Score
            </div>
            <p className="text-dark-muted text-xs mb-2">
              Indicates how reliable this risk assessment is based on data
              availability and recency.
            </p>
            {showDetails && (
              <ul className="text-xs text-dark-muted space-y-1">
                {getConfidenceExplanation().map((factor, i) => (
                  <li key={i} className="flex items-center gap-1">
                    <span className="w-1 h-1 rounded-full bg-dark-muted" />
                    {factor}
                  </li>
                ))}
              </ul>
            )}
          </div>
          {/* Tooltip arrow */}
          <div className="absolute top-full left-4 w-2 h-2 bg-dark-surface border-b border-r border-dark-border transform rotate-45 -mt-1" />
        </div>
      )}
    </div>
  );
}
