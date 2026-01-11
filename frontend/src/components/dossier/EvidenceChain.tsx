'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAllEvidenceChains } from '@/lib/api';
import { format, parseISO } from 'date-fns';

interface EvidenceEvent {
  event_id: string;
  event_type: string;
  date: string;
  variant_id: string;
  description: string;
  source_location?: string;
  count?: number;
  confidence: number;
  icon: string;
}

interface EvidenceChainData {
  location_id: string;
  location_name: string;
  variant_id: string;
  events: EvidenceEvent[];
  lead_time_days: number | null;
  chain_confidence: number;
  summary: string;
}

interface EvidenceChainProps {
  locationId: string;
}

const EVENT_TYPE_COLORS: Record<string, string> = {
  traveler_detection: 'border-red-500 bg-red-500/10',
  genomic_detection: 'border-purple-500 bg-purple-500/10',
  wastewater_spike: 'border-amber-500 bg-amber-500/10',
  clinical_cases: 'border-blue-500 bg-blue-500/10',
};

const EVENT_TYPE_LABELS: Record<string, string> = {
  traveler_detection: 'Traveler Screening',
  genomic_detection: 'Genomic Detection',
  wastewater_spike: 'Wastewater Spike',
  clinical_cases: 'Clinical Cases',
};

export function EvidenceChain({ locationId }: EvidenceChainProps) {
  const [expandedChain, setExpandedChain] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['evidenceChains', locationId],
    queryFn: () => getAllEvidenceChains(locationId, 60),
    staleTime: 10 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="bg-dark-surface rounded-lg p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-dark-border rounded w-1/3" />
          <div className="h-20 bg-dark-border rounded" />
        </div>
      </div>
    );
  }

  if (error || !data || data.chains.length === 0) {
    return null; // Don't show if no evidence chains
  }

  const { chains } = data;
  const topChain = chains[0]; // Best lead time

  return (
    <div>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between text-sm font-semibold text-dark-muted uppercase mb-3 hover:text-white transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
            />
          </svg>
          <span>Early Detection Evidence</span>
          {topChain.lead_time_days && (
            <span className="px-2 py-0.5 bg-green-500/20 text-green-400 rounded text-xs font-normal normal-case">
              {topChain.lead_time_days}d lead time
            </span>
          )}
        </div>
        <svg
          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="space-y-3">
          {chains.map((chain) => (
            <div
              key={chain.variant_id}
              className="bg-dark-surface rounded-lg border border-dark-border overflow-hidden"
            >
              {/* Chain header */}
              <button
                onClick={() =>
                  setExpandedChain(expandedChain === chain.variant_id ? null : chain.variant_id)
                }
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="px-2 py-1 bg-purple-500/20 text-purple-300 rounded text-sm font-medium">
                    {chain.variant_id}
                  </span>
                  {chain.lead_time_days && (
                    <span className="text-xs text-green-400">
                      {chain.lead_time_days} days early warning
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-dark-muted">
                    {chain.events.length} events
                  </span>
                  <svg
                    className={`w-4 h-4 text-dark-muted transition-transform ${
                      expandedChain === chain.variant_id ? 'rotate-180' : ''
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
                </div>
              </button>

              {/* Expanded chain details */}
              {expandedChain === chain.variant_id && (
                <div className="px-4 pb-4 border-t border-dark-border pt-4">
                  {/* Summary */}
                  <p className="text-xs text-dark-muted mb-4 italic">{chain.summary}</p>

                  {/* Timeline */}
                  <div className="relative pl-6">
                    {/* Vertical line */}
                    <div className="absolute left-2 top-2 bottom-2 w-px bg-dark-border" />

                    {chain.events.map((event, idx) => (
                      <div key={event.event_id} className="relative pb-4 last:pb-0">
                        {/* Timeline dot */}
                        <div
                          className={`absolute left-0 -translate-x-1/2 w-4 h-4 rounded-full border-2 ${
                            EVENT_TYPE_COLORS[event.event_type] || 'border-gray-500 bg-gray-500/10'
                          }`}
                          style={{ left: '8px' }}
                        >
                          {idx === 0 && (
                            <div className="absolute inset-0 rounded-full animate-ping bg-current opacity-25" />
                          )}
                        </div>

                        {/* Event content */}
                        <div className="ml-4">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-lg">{event.icon}</span>
                            <span className="text-xs font-medium text-white">
                              {EVENT_TYPE_LABELS[event.event_type] || event.event_type}
                            </span>
                            <span className="text-xs text-dark-muted">
                              {format(parseISO(event.date), 'MMM d, yyyy')}
                            </span>
                          </div>
                          <p className="text-xs text-dark-muted">{event.description}</p>
                          <div className="mt-1 flex items-center gap-2">
                            <span className="text-[10px] text-dark-muted">
                              Confidence: {Math.round(event.confidence * 100)}%
                            </span>
                            {event.source_location && (
                              <span className="text-[10px] text-blue-400">
                                Origin: {event.source_location}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Connector arrow to next event */}
                        {idx < chain.events.length - 1 && (
                          <div className="absolute left-[7px] bottom-0 translate-y-1/2">
                            <svg
                              className="w-2 h-2 text-dark-border"
                              fill="currentColor"
                              viewBox="0 0 8 8"
                            >
                              <path d="M0 0L4 4L0 8V0Z" />
                            </svg>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Chain confidence */}
                  <div className="mt-4 pt-3 border-t border-dark-border/50 flex items-center justify-between text-xs">
                    <span className="text-dark-muted">Chain confidence:</span>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-dark-border rounded-full overflow-hidden">
                        <div
                          className="h-full bg-green-500 rounded-full"
                          style={{ width: `${chain.chain_confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-green-400">
                        {Math.round(chain.chain_confidence * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Explanation footer */}
          <div className="text-[10px] text-dark-muted text-center px-4 py-2 bg-blue-500/5 rounded-lg">
            Evidence chains show how variants were detected through traveler screening before
            appearing in local surveillance, providing early warning.
          </div>
        </div>
      )}
    </div>
  );
}
