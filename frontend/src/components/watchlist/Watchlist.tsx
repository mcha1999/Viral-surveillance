'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useLocationStore } from '@/lib/store';
import { getLocation, getRiskScore } from '@/lib/api';

interface WatchlistItemProps {
  locationId: string;
  onSelect: (id: string) => void;
  onRemove: (id: string) => void;
}

function WatchlistItem({ locationId, onSelect, onRemove }: WatchlistItemProps) {
  const { data: location, isLoading } = useQuery({
    queryKey: ['location', locationId],
    queryFn: () => getLocation(locationId),
    staleTime: 5 * 60 * 1000,
  });

  const { data: risk } = useQuery({
    queryKey: ['risk', locationId],
    queryFn: () => getRiskScore(locationId),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading || !location) {
    return (
      <div className="animate-pulse bg-gray-800 rounded p-2 h-16" />
    );
  }

  const riskScore = risk?.risk_score ?? location.risk_score;
  const riskColor = riskScore >= 70
    ? 'text-red-500'
    : riskScore >= 30
    ? 'text-amber-500'
    : 'text-green-500';

  const trendIcon = location.risk_trend === 'rising'
    ? '↑'
    : location.risk_trend === 'falling'
    ? '↓'
    : '→';

  return (
    <div
      className="bg-gray-800/50 rounded-lg p-3 cursor-pointer hover:bg-gray-700/50 transition-colors group"
      onClick={() => onSelect(locationId)}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-white truncate">{location.name}</h4>
          <p className="text-xs text-gray-400 truncate">{location.country}</p>
        </div>
        <div className="flex items-center gap-2 ml-2">
          <div className={`text-lg font-bold ${riskColor}`}>
            {riskScore?.toFixed(0) ?? 'N/A'}
          </div>
          <span className={`text-sm ${riskColor}`}>{trendIcon}</span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRemove(locationId);
            }}
            className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-500 transition-opacity p-1"
            aria-label="Remove from watchlist"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Alert indicator */}
      {location.weekly_change && Math.abs(location.weekly_change) > 50 && (
        <div className="mt-2 text-xs bg-red-500/20 text-red-400 px-2 py-1 rounded">
          ⚠ {location.weekly_change > 0 ? '+' : ''}{location.weekly_change.toFixed(0)}% this week
        </div>
      )}
    </div>
  );
}

export function Watchlist() {
  const [isExpanded, setIsExpanded] = useState(true);
  const { watchlist, removeFromWatchlist, setSelectedLocation } = useLocationStore();

  if (watchlist.length === 0) {
    return null;
  }

  return (
    <div className="bg-gray-900/90 backdrop-blur-sm rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
          </svg>
          <span className="font-medium text-white">Watchlist</span>
          <span className="text-xs text-gray-400">({watchlist.length}/5)</span>
        </div>
        <svg
          className={`w-5 h-5 text-gray-400 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Items */}
      {isExpanded && (
        <div className="px-3 pb-3 space-y-2">
          {watchlist.map((locationId) => (
            <WatchlistItem
              key={locationId}
              locationId={locationId}
              onSelect={setSelectedLocation}
              onRemove={removeFromWatchlist}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Button to add current location to watchlist
interface AddToWatchlistButtonProps {
  locationId: string;
}

export function AddToWatchlistButton({ locationId }: AddToWatchlistButtonProps) {
  const { watchlist, addToWatchlist, removeFromWatchlist, isInWatchlist } = useLocationStore();
  const isWatched = isInWatchlist(locationId);
  const isFull = watchlist.length >= 5;

  const handleClick = () => {
    if (isWatched) {
      removeFromWatchlist(locationId);
    } else if (!isFull) {
      addToWatchlist(locationId);
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={!isWatched && isFull}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
        isWatched
          ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
          : isFull
          ? 'bg-gray-700/50 text-gray-500 cursor-not-allowed'
          : 'bg-gray-700/50 text-gray-300 hover:bg-gray-600/50'
      }`}
      title={isFull && !isWatched ? 'Watchlist is full (max 5)' : ''}
    >
      <svg
        className="w-5 h-5"
        fill={isWatched ? 'currentColor' : 'none'}
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
        />
      </svg>
      <span className="text-sm">
        {isWatched ? 'Watching' : 'Watch'}
      </span>
    </button>
  );
}
