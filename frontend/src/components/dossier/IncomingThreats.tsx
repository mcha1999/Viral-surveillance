'use client';

import type { IncomingThreat } from '@/types';
import { RiskBadge } from './RiskBadge';

interface IncomingThreatsProps {
  threats: IncomingThreat[];
}

export function IncomingThreats({ threats }: IncomingThreatsProps) {
  if (threats.length === 0) return null;

  return (
    <div>
      <h3 className="text-sm font-semibold text-dark-muted uppercase mb-2">
        Incoming Vectors (Next 48h)
      </h3>
      <div className="space-y-2">
        {threats.map((threat, index) => (
          <div
            key={index}
            className="bg-dark-surface rounded-lg p-3 border border-dark-border"
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium text-white">
                  {threat.origin_name}
                </div>
                <div className="text-sm text-dark-muted">
                  {threat.origin_country}
                </div>
              </div>
              <RiskBadge score={threat.source_risk_score} size="sm" />
            </div>
            <div className="mt-2 flex items-center gap-4 text-sm text-dark-muted">
              <span>✈️ {threat.flight_count} flights</span>
              <span>👥 ~{threat.pax_estimate.toLocaleString()} pax</span>
              {threat.primary_variant && (
                <span className="text-purple-400">{threat.primary_variant}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
