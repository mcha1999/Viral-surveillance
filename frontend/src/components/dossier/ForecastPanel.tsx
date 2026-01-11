'use client';

import { useState } from 'react';
import { ForecastChart } from './ForecastChart';

interface ForecastPoint {
  date: string;
  risk_score: number;
  confidence_low: number;
  confidence_high: number;
}

interface ForecastPanelProps {
  locationId: string;
  currentScore: number;
  forecast: ForecastPoint[];
  trend: 'rising' | 'falling' | 'stable';
  audienceMode?: 'general' | 'expert';
}

const METHODOLOGY_TEXT = {
  general: {
    title: 'How we predict future risk',
    description:
      'This forecast shows where risk levels are headed based on recent trends. The shaded area shows our level of certainty — wider bands mean more uncertainty as we look further ahead.',
    bullets: [
      'Based on the past 7 days of viral activity',
      'Uncertainty grows the further we predict',
      'Updates daily as new data arrives',
    ],
  },
  expert: {
    title: 'Forecast Methodology',
    description:
      'Linear extrapolation of 14-day wastewater surveillance trend. Confidence intervals expand at ±5 points per forecast day, reflecting increased uncertainty.',
    bullets: [
      'Trend: Average daily change over available data points',
      'CI expansion: ±5 × √(days ahead) for error propagation',
      'Scores clamped to [0, 100] valid range',
      'Recomputed hourly with new surveillance data',
    ],
  },
};

export function ForecastPanel({
  currentScore,
  forecast,
  trend,
  audienceMode = 'general',
}: ForecastPanelProps) {
  const [showMethodology, setShowMethodology] = useState(false);

  const methodology = METHODOLOGY_TEXT[audienceMode];

  // Calculate projected change
  const projectedScore = forecast.length > 0 ? forecast[forecast.length - 1].risk_score : currentScore;
  const projectedChange = projectedScore - currentScore;
  const confidenceRange = forecast.length > 0
    ? forecast[forecast.length - 1].confidence_high - forecast[forecast.length - 1].confidence_low
    : 0;

  const getTrendColor = () => {
    switch (trend) {
      case 'rising':
        return 'text-red-400';
      case 'falling':
        return 'text-green-400';
      default:
        return 'text-yellow-400';
    }
  };

  const getTrendIcon = () => {
    switch (trend) {
      case 'rising':
        return '↑';
      case 'falling':
        return '↓';
      default:
        return '→';
    }
  };

  return (
    <div>
      <h3 className="text-sm font-semibold text-dark-muted uppercase mb-3 flex items-center justify-between">
        <span>7-Day Forecast</span>
        <button
          onClick={() => setShowMethodology(!showMethodology)}
          className="text-dark-muted hover:text-white transition-colors"
          aria-label="Show methodology"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </button>
      </h3>

      <div className="bg-dark-surface rounded-lg p-4 space-y-4">
        {/* Summary row */}
        <div className="flex items-center justify-between">
          <div>
            <span className="text-dark-muted text-sm">Trend: </span>
            <span className={`font-medium capitalize ${getTrendColor()}`}>
              {getTrendIcon()} {trend}
            </span>
          </div>
          <div className="text-right">
            <span className="text-dark-muted text-sm">Projected: </span>
            <span className="font-semibold text-white">
              {projectedScore.toFixed(0)}
            </span>
            <span className={`text-sm ml-1 ${projectedChange >= 0 ? 'text-red-400' : 'text-green-400'}`}>
              ({projectedChange >= 0 ? '+' : ''}{projectedChange.toFixed(0)})
            </span>
          </div>
        </div>

        {/* Chart */}
        <div className="flex justify-center">
          <ForecastChart
            forecast={forecast}
            currentScore={currentScore}
            height={120}
          />
        </div>

        {/* Legend */}
        <div className="flex items-center justify-center gap-4 text-xs text-dark-muted">
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-blue-500 rounded" />
            <span>Projected risk</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-blue-500/20 rounded" />
            <span>Confidence range</span>
          </div>
        </div>

        {/* Context message */}
        <p className="text-xs text-dark-muted italic text-center">
          {trend === 'rising' && 'If current trajectory continues, risk is expected to increase.'}
          {trend === 'falling' && 'If current trajectory continues, risk is expected to decrease.'}
          {trend === 'stable' && 'Risk levels are expected to remain relatively stable.'}
          {confidenceRange > 30 && ' (High uncertainty in this projection)'}
        </p>
      </div>

      {/* Methodology panel */}
      {showMethodology && (
        <div className="mt-3 bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 text-sm">
          <h4 className="font-medium text-blue-300 mb-2">{methodology.title}</h4>
          <p className="text-dark-muted text-xs mb-3">{methodology.description}</p>
          <ul className="space-y-1">
            {methodology.bullets.map((bullet, i) => (
              <li key={i} className="text-xs text-dark-muted flex items-start gap-2">
                <span className="text-blue-400 mt-1">•</span>
                <span>{bullet}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
