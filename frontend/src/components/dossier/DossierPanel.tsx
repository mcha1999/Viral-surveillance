'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getLocation, getRiskForecast, getRiskScore } from '@/lib/api';
import { useLocationStore, useOnboardingStore } from '@/lib/store';
import { RiskBadge } from './RiskBadge';
import { TrendIndicator } from './TrendIndicator';
import { IncomingThreats } from './IncomingThreats';
import { RiskScoreBreakdown } from './RiskScoreBreakdown';
import { ForecastPanel } from './ForecastPanel';
import { EvidenceChain } from './EvidenceChain';
import { DataFreshness } from '@/components/ui/DataFreshness';
import { ContextualTooltip } from '@/components/onboarding/ContextualTooltip';

interface DossierPanelProps {
  locationId: string;
}

export function DossierPanel({ locationId }: DossierPanelProps) {
  const { setSelectedLocation, watchlist, addToWatchlist, removeFromWatchlist, audienceMode } = useLocationStore();
  const {
    hasSeenDossierTooltip,
    setHasSeenDossierTooltip,
    hasSeenWatchlistTooltip,
    setHasSeenWatchlistTooltip,
    locationsViewed,
    incrementLocationsViewed,
    markStepComplete,
  } = useOnboardingStore();

  const [showDossierTooltip, setShowDossierTooltip] = useState(false);
  const [showWatchlistTooltip, setShowWatchlistTooltip] = useState(false);

  // Track location views and show tooltips
  useEffect(() => {
    incrementLocationsViewed();
    markStepComplete('explore_globe');

    // Show dossier tooltip on first view
    if (!hasSeenDossierTooltip) {
      const timer = setTimeout(() => setShowDossierTooltip(true), 500);
      return () => clearTimeout(timer);
    }
  }, []);

  // Show watchlist tooltip after viewing 3 locations
  useEffect(() => {
    if (locationsViewed >= 3 && !hasSeenWatchlistTooltip && hasSeenDossierTooltip) {
      const timer = setTimeout(() => setShowWatchlistTooltip(true), 1000);
      return () => clearTimeout(timer);
    }
  }, [locationsViewed, hasSeenWatchlistTooltip, hasSeenDossierTooltip]);

  // Fetch location data
  const { data: location, isLoading, error } = useQuery({
    queryKey: ['location', locationId],
    queryFn: () => getLocation(locationId),
    staleTime: 5 * 60 * 1000,
  });

  // Fetch forecast
  const { data: forecast } = useQuery({
    queryKey: ['forecast', locationId],
    queryFn: () => getRiskForecast(locationId, 7),
    staleTime: 15 * 60 * 1000,
    enabled: !!location,
  });

  // Fetch risk score with component breakdown
  const { data: riskScore } = useQuery({
    queryKey: ['riskScore', locationId],
    queryFn: () => getRiskScore(locationId),
    staleTime: 5 * 60 * 1000,
    enabled: !!location,
  });

  const isInWatchlist = watchlist.includes(locationId);

  if (isLoading) {
    return (
      <div className="dossier-panel p-6">
        <div className="space-y-4">
          <div className="skeleton h-8 w-3/4 rounded" />
          <div className="skeleton h-6 w-1/2 rounded" />
          <div className="skeleton h-24 w-full rounded" />
          <div className="skeleton h-32 w-full rounded" />
        </div>
      </div>
    );
  }

  if (error || !location) {
    return (
      <div className="dossier-panel p-6">
        <div className="text-red-400">Failed to load location data</div>
        <button
          onClick={() => setSelectedLocation(null)}
          className="mt-4 text-blue-400 hover:underline"
        >
          Close
        </button>
      </div>
    );
  }

  const handleDismissDossierTooltip = () => {
    setShowDossierTooltip(false);
    setHasSeenDossierTooltip(true);
  };

  const handleDismissWatchlistTooltip = () => {
    setShowWatchlistTooltip(false);
    setHasSeenWatchlistTooltip(true);
  };

  const handleAddToWatchlist = () => {
    if (!isInWatchlist) {
      addToWatchlist(locationId);
      markStepComplete('add_watchlist');
    } else {
      removeFromWatchlist(locationId);
    }
  };

  return (
    <div className="dossier-panel animate-in slide-in-from-right duration-300">
      {/* Dossier Tooltip */}
      <ContextualTooltip
        id="dossier-intro"
        title="This is the Dossier Panel"
        description="View detailed risk information, trends, and variants for any location. Explore the data to understand local viral activity."
        position="left"
        show={showDossierTooltip}
        onDismiss={handleDismissDossierTooltip}
      />

      {/* Header */}
      <div className="sticky top-0 bg-dark-surface/95 backdrop-blur-md border-b border-dark-border p-4 z-10">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">{location.name}</h2>
            <p className="text-dark-muted">{location.country}</p>
          </div>
          <button
            onClick={() => setSelectedLocation(null)}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            aria-label="Close panel"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Risk score */}
        <div className="mt-4 flex items-center gap-4">
          <RiskBadge score={location.risk_score || 0} />
          <TrendIndicator trend={location.risk_trend} change={location.weekly_change} />
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-6">
        {/* Quick stats */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-dark-surface rounded-lg p-3">
            <div className="text-xs text-dark-muted uppercase">Dominant Variant</div>
            <div className="text-lg font-semibold mt-1">
              {location.dominant_variant || 'Unknown'}
            </div>
          </div>
          <div className="bg-dark-surface rounded-lg p-3">
            <div className="text-xs text-dark-muted uppercase">Data Quality</div>
            <div className="text-lg font-semibold mt-1 capitalize">
              {location.data_quality}
            </div>
          </div>
        </div>

        {/* Risk score breakdown - progressive disclosure */}
        {riskScore && (
          <RiskScoreBreakdown
            riskScore={riskScore.risk_score}
            components={riskScore.components}
            confidence={riskScore.confidence}
            lastUpdated={riskScore.last_updated}
            audienceMode={audienceMode}
          />
        )}

        {/* Variants */}
        {location.variants.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-dark-muted uppercase mb-2">
              Detected Variants
            </h3>
            <div className="flex flex-wrap gap-2">
              {location.variants.map((variant) => (
                <span
                  key={variant}
                  className="px-2 py-1 bg-purple-500/20 text-purple-300 rounded text-sm"
                >
                  {variant}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Incoming threats */}
        {location.incoming_threats.length > 0 && (
          <IncomingThreats threats={location.incoming_threats} />
        )}

        {/* Early detection evidence chain */}
        <EvidenceChain locationId={locationId} />

        {/* Forecast with visualization */}
        {forecast && (
          <ForecastPanel
            locationId={locationId}
            currentScore={forecast.current_score}
            forecast={forecast.forecast}
            trend={forecast.trend}
            audienceMode={audienceMode}
          />
        )}

        {/* Actions */}
        <div className="flex gap-2 relative">
          <button
            onClick={handleAddToWatchlist}
            className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
              isInWatchlist
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-dark-surface text-white hover:bg-white/10'
            }`}
          >
            {isInWatchlist ? '★ In Watchlist' : '☆ Add to Watchlist'}
          </button>

          {/* Watchlist Tooltip */}
          <ContextualTooltip
            id="watchlist-intro"
            title="Add to your Watchlist"
            description="Track up to 5 locations and get notified when risk levels change significantly."
            position="top"
            show={showWatchlistTooltip}
            onDismiss={handleDismissWatchlistTooltip}
            showAction
            actionLabel="Add now"
            onAction={handleAddToWatchlist}
          />
        </div>

        {/* Data freshness indicator */}
        <div className="flex items-center justify-center">
          <DataFreshness lastUpdated={location.last_updated} />
        </div>
      </div>
    </div>
  );
}
