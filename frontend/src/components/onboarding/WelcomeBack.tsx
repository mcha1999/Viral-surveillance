'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useLocationStore, useOnboardingStore } from '@/lib/store';
import { getLocation } from '@/lib/api';

interface WelcomeBackProps {
  onDismiss: () => void;
}

export function WelcomeBack({ onDismiss }: WelcomeBackProps) {
  const [isVisible, setIsVisible] = useState(false);
  const { homeLocation, watchlist, setSelectedLocation } = useLocationStore();
  const { setLastVisit } = useOnboardingStore();

  // Fetch home location data
  const { data: homeData } = useQuery({
    queryKey: ['location', homeLocation],
    queryFn: () => getLocation(homeLocation!),
    enabled: !!homeLocation,
    staleTime: 5 * 60 * 1000,
  });

  // Fetch watchlist data
  const watchlistQueries = useQuery({
    queryKey: ['watchlist-summary', watchlist],
    queryFn: async () => {
      if (watchlist.length === 0) return [];
      const results = await Promise.all(
        watchlist.slice(0, 3).map((id) => getLocation(id).catch(() => null))
      );
      return results.filter(Boolean);
    },
    enabled: watchlist.length > 0,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const handleViewDetails = () => {
    if (homeLocation) {
      setSelectedLocation(homeLocation);
    }
    setLastVisit(new Date().toISOString());
    onDismiss();
  };

  const handleDismiss = () => {
    setLastVisit(new Date().toISOString());
    onDismiss();
  };

  const getRiskColor = (score: number | null) => {
    if (score === null) return 'text-dark-muted';
    if (score >= 70) return 'text-red-400';
    if (score >= 50) return 'text-orange-400';
    if (score >= 30) return 'text-amber-400';
    return 'text-green-400';
  };

  const getRiskLabel = (score: number | null) => {
    if (score === null) return 'Unknown';
    if (score >= 70) return 'HIGH';
    if (score >= 50) return 'ELEVATED';
    if (score >= 30) return 'MODERATE';
    return 'LOW';
  };

  const getTrendIcon = (trend: string | undefined) => {
    if (trend === 'rising') return '↑';
    if (trend === 'falling') return '↓';
    return '→';
  };

  const getTrendColor = (trend: string | undefined) => {
    if (trend === 'rising') return 'text-red-400';
    if (trend === 'falling') return 'text-green-400';
    return 'text-amber-400';
  };

  return (
    <div
      className={`fixed top-20 left-1/2 -translate-x-1/2 z-[150] transition-all duration-300 ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-4'
      }`}
    >
      <div className="bg-dark-surface border border-dark-border rounded-xl shadow-2xl p-5 max-w-sm w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Welcome back!</h3>
          <button
            onClick={handleDismiss}
            className="p-1 hover:bg-white/10 rounded transition-colors"
            aria-label="Dismiss"
          >
            <svg className="w-4 h-4 text-dark-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Home location summary */}
        {homeData && (
          <div className="bg-dark-bg rounded-lg p-3 mb-3">
            <div className="flex items-center gap-2 mb-1">
              <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span className="text-white font-medium text-sm">{homeData.name}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className={`text-sm font-semibold ${getRiskColor(homeData.risk_score)}`}>
                {getRiskLabel(homeData.risk_score)} ({homeData.risk_score?.toFixed(0) || 'N/A'})
              </span>
              {homeData.weekly_change !== undefined && (
                <span className={`text-xs ${getTrendColor(homeData.risk_trend)}`}>
                  {getTrendIcon(homeData.risk_trend)} {homeData.weekly_change > 0 ? '+' : ''}{homeData.weekly_change?.toFixed(0)}%
                </span>
              )}
            </div>
          </div>
        )}

        {/* Watchlist preview */}
        {watchlistQueries.data && watchlistQueries.data.length > 0 && (
          <div className="mb-4">
            <h4 className="text-xs text-dark-muted uppercase font-medium mb-2">Your Watchlist</h4>
            <div className="space-y-2">
              {watchlistQueries.data.map((loc: any) => (
                <div
                  key={loc.location_id}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-white truncate flex-1">{loc.name}</span>
                  <div className="flex items-center gap-2">
                    <span className={`font-semibold ${getRiskColor(loc.risk_score)}`}>
                      {loc.risk_score?.toFixed(0) || 'N/A'}
                    </span>
                    <span className={`text-xs ${getTrendColor(loc.risk_trend)}`}>
                      {getTrendIcon(loc.risk_trend)}
                    </span>
                  </div>
                </div>
              ))}
              {watchlist.length > 3 && (
                <div className="text-xs text-dark-muted">
                  +{watchlist.length - 3} more locations
                </div>
              )}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          {homeLocation && (
            <button
              onClick={handleViewDetails}
              className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
            >
              View Details
            </button>
          )}
          <button
            onClick={handleDismiss}
            className={`${homeLocation ? '' : 'flex-1'} py-2 px-4 bg-dark-bg hover:bg-white/10 text-white text-sm font-medium rounded-lg transition-colors`}
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
