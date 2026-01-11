'use client';

import { useState } from 'react';
import { ComponentBar } from './ComponentBar';
import { ConfidenceIndicator } from './ConfidenceIndicator';

interface RiskComponents {
  wastewater_load: number;
  growth_velocity: number;
  import_pressure: number;
}

interface RiskScoreBreakdownProps {
  riskScore: number;
  components: RiskComponents;
  confidence: number;
  lastUpdated?: string | null;
  audienceMode?: 'general' | 'expert';
}

const COMPONENT_CONFIG = {
  wastewater_load: {
    label: 'Wastewater Surveillance',
    labelGeneral: 'Local viral detection',
    weight: 0.4,
    color: '#8b5cf6', // purple
    description: 'Viral concentration detected in wastewater samples',
    descriptionGeneral: 'How much virus is being detected locally',
  },
  growth_velocity: {
    label: 'Growth Velocity',
    labelGeneral: 'Spread rate',
    weight: 0.3,
    color: '#f59e0b', // amber
    description: 'Week-over-week change in viral load',
    descriptionGeneral: 'How fast the virus is spreading',
  },
  import_pressure: {
    label: 'Import Pressure',
    labelGeneral: 'Travel risk',
    weight: 0.3,
    color: '#06b6d4', // cyan
    description: 'Risk from incoming travelers from high-risk areas',
    descriptionGeneral: 'Risk from travelers arriving from affected areas',
  },
};

export function RiskScoreBreakdown({
  riskScore,
  components,
  confidence,
  lastUpdated,
  audienceMode = 'general',
}: RiskScoreBreakdownProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showMethodology, setShowMethodology] = useState(false);

  const isExpert = audienceMode === 'expert';

  return (
    <div className="bg-dark-surface rounded-lg border border-dark-border overflow-hidden">
      {/* Collapsed header - always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2 text-sm text-dark-muted">
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          <span>How is this score calculated?</span>
        </div>
        <svg
          className={`w-5 h-5 text-dark-muted transition-transform duration-200 ${
            isExpanded ? 'rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-dark-border pt-4">
          {/* Component breakdown */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-dark-muted uppercase tracking-wider">
              Component Breakdown
            </h4>
            {Object.entries(components).map(([key, value]) => {
              const config = COMPONENT_CONFIG[key as keyof RiskComponents];
              return (
                <div key={key} className="group">
                  <ComponentBar
                    label={isExpert ? config.label : config.labelGeneral}
                    value={value}
                    weight={config.weight}
                    color={config.color}
                    showWeight={isExpert}
                  />
                  {isExpert && (
                    <p className="text-xs text-dark-muted/60 mt-1 pl-1">
                      {config.description}
                    </p>
                  )}
                </div>
              );
            })}
          </div>

          {/* Weighted calculation preview (expert only) */}
          {isExpert && (
            <div className="bg-dark-bg/50 rounded-lg p-3 text-xs font-mono text-dark-muted">
              <div className="mb-1 text-dark-muted/60">Weighted calculation:</div>
              <div>
                ({components.wastewater_load.toFixed(1)} × 0.4) + (
                {components.growth_velocity.toFixed(1)} × 0.3) + (
                {components.import_pressure.toFixed(1)} × 0.3) ={' '}
                <span className="text-white font-semibold">
                  {riskScore.toFixed(1)}
                </span>
              </div>
            </div>
          )}

          {/* Confidence indicator */}
          <div className="pt-2 border-t border-dark-border/50">
            <ConfidenceIndicator
              confidence={confidence}
              lastUpdated={lastUpdated}
              showDetails={isExpert}
            />
          </div>

          {/* Learn more button */}
          <button
            onClick={() => setShowMethodology(!showMethodology)}
            className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
          >
            <svg
              className="w-3 h-3"
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
            {showMethodology ? 'Hide methodology' : 'Learn more about methodology'}
          </button>

          {/* Methodology explanation */}
          {showMethodology && (
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-xs space-y-2">
              <h5 className="font-medium text-blue-300">Risk Score Methodology</h5>
              <p className="text-dark-muted">
                The risk score combines three data sources to provide a comprehensive
                view of viral activity:
              </p>
              <ul className="space-y-2 text-dark-muted">
                <li>
                  <span className="text-purple-400 font-medium">
                    Wastewater Surveillance (40%):
                  </span>{' '}
                  {isExpert
                    ? 'Normalized viral concentration from wastewater treatment facilities, using copies/L measurements compared to historical baselines.'
                    : 'Measures virus levels in sewage to detect community spread early.'}
                </li>
                <li>
                  <span className="text-amber-400 font-medium">
                    Growth Velocity (30%):
                  </span>{' '}
                  {isExpert
                    ? '7-day rolling average comparison of viral load, normalized to ±50% weekly change range. Values above 50 indicate growth.'
                    : 'Tracks whether the virus is spreading faster or slower than last week.'}
                </li>
                <li>
                  <span className="text-cyan-400 font-medium">
                    Import Pressure (30%):
                  </span>{' '}
                  {isExpert
                    ? 'Passenger-weighted average of origin location risk scores, scaled by volume (baseline: 10,000 pax/day).'
                    : 'Estimates risk from travelers arriving from areas with high viral activity.'}
                </li>
              </ul>
              {isExpert && (
                <p className="text-dark-muted/60 text-[10px] mt-2">
                  Confidence score reflects data availability (target: 10+ data points)
                  and recency (penalized if {'>'} 7 days old).
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
