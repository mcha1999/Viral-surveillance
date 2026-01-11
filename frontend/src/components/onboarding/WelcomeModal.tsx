'use client';

import { useState, useCallback } from 'react';
import { useLocationStore, useOnboardingStore } from '@/lib/store';
import { useQuery } from '@tanstack/react-query';
import { autocomplete } from '@/lib/api';

interface WelcomeModalProps {
  onComplete: () => void;
}

export function WelcomeModal({ onComplete }: WelcomeModalProps) {
  const [step, setStep] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const { setHomeLocation, setSelectedLocation } = useLocationStore();
  const { setHasSeenWelcome, markStepComplete } = useOnboardingStore();

  // Autocomplete for location search
  const { data: suggestions = [] } = useQuery({
    queryKey: ['autocomplete', searchQuery],
    queryFn: () => autocomplete(searchQuery, 5),
    enabled: searchQuery.length >= 2,
    staleTime: 60 * 1000,
  });

  const handleLocationSelect = useCallback((id: string, name: string) => {
    setHomeLocation(id);
    setSelectedLocation(id);
    markStepComplete('set_home');
    setStep(3);
  }, [setHomeLocation, setSelectedLocation, markStepComplete]);

  const handleSkip = useCallback(() => {
    setStep(3);
  }, []);

  const handleComplete = useCallback(() => {
    setHasSeenWelcome(true);
    markStepComplete('completed_welcome');
    onComplete();
  }, [setHasSeenWelcome, markStepComplete, onComplete]);

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-dark-surface border border-dark-border rounded-2xl shadow-2xl max-w-md w-full mx-4 overflow-hidden animate-in fade-in zoom-in duration-300">
        {/* Progress indicator */}
        <div className="flex gap-1 p-4 pb-0">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={`h-1 flex-1 rounded-full transition-colors ${
                s <= step ? 'bg-blue-500' : 'bg-dark-border'
              }`}
            />
          ))}
        </div>

        {/* Step 1: Welcome */}
        {step === 1 && (
          <div className="p-6 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">
              Welcome to Viral Weather
            </h2>
            <p className="text-dark-muted mb-6">
              Track viral activity worldwide with real-time wastewater surveillance, genomic data, and flight transmission routes.
            </p>
            <div className="space-y-3">
              <div className="flex items-center gap-3 text-left p-3 bg-dark-bg rounded-lg">
                <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                  </svg>
                </div>
                <div>
                  <div className="text-white text-sm font-medium">Explore the Globe</div>
                  <div className="text-dark-muted text-xs">Click any location to see risk details</div>
                </div>
              </div>
              <div className="flex items-center gap-3 text-left p-3 bg-dark-bg rounded-lg">
                <div className="w-8 h-8 rounded-full bg-amber-500/20 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                  </svg>
                </div>
                <div>
                  <div className="text-white text-sm font-medium">Build Your Watchlist</div>
                  <div className="text-dark-muted text-xs">Track up to 5 locations you care about</div>
                </div>
              </div>
              <div className="flex items-center gap-3 text-left p-3 bg-dark-bg rounded-lg">
                <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <div className="text-white text-sm font-medium">Travel Through Time</div>
                  <div className="text-dark-muted text-xs">See 30 days of history and 7-day forecasts</div>
                </div>
              </div>
            </div>
            <button
              onClick={() => setStep(2)}
              className="w-full mt-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
            >
              Get Started
            </button>
          </div>
        )}

        {/* Step 2: Set Home Location */}
        {step === 2 && (
          <div className="p-6">
            <div className="text-center mb-6">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-blue-500/20 flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h2 className="text-xl font-bold text-white mb-1">
                Set Your Home Location
              </h2>
              <p className="text-dark-muted text-sm">
                Get personalized risk updates for your area
              </p>
            </div>

            {/* Search input */}
            <div className="relative mb-4">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search for a city..."
                className="w-full px-4 py-3 pl-10 bg-dark-bg border border-dark-border rounded-lg text-white placeholder-dark-muted focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500"
                autoFocus
              />
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-muted"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>

            {/* Suggestions */}
            {suggestions.length > 0 && (
              <div className="bg-dark-bg border border-dark-border rounded-lg overflow-hidden mb-4 max-h-48 overflow-y-auto">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion.id}
                    onClick={() => handleLocationSelect(suggestion.id, suggestion.label)}
                    className="w-full px-4 py-3 text-left hover:bg-white/5 transition-colors border-b border-dark-border last:border-0 flex items-center gap-3"
                  >
                    <svg className="w-4 h-4 text-dark-muted flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    </svg>
                    <span className="text-white">{suggestion.label}</span>
                  </button>
                ))}
              </div>
            )}

            {searchQuery.length >= 2 && suggestions.length === 0 && (
              <div className="text-center text-dark-muted py-4 mb-4">
                No locations found
              </div>
            )}

            <button
              onClick={handleSkip}
              className="w-full py-2 text-dark-muted hover:text-white transition-colors text-sm"
            >
              Skip for now
            </button>
          </div>
        )}

        {/* Step 3: Ready to Go */}
        {step === 3 && (
          <div className="p-6 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">
              You&apos;re All Set!
            </h2>
            <p className="text-dark-muted mb-6">
              Start exploring viral activity around the world. Click any location on the globe to see detailed risk information.
            </p>
            <div className="bg-dark-bg rounded-lg p-4 mb-6 text-left">
              <h3 className="text-sm font-medium text-white mb-2">Quick Tips</h3>
              <ul className="space-y-2 text-sm text-dark-muted">
                <li className="flex items-center gap-2">
                  <kbd className="px-1.5 py-0.5 bg-dark-surface rounded text-xs font-mono">/</kbd>
                  <span>Quick search</span>
                </li>
                <li className="flex items-center gap-2">
                  <kbd className="px-1.5 py-0.5 bg-dark-surface rounded text-xs font-mono">?</kbd>
                  <span>View all shortcuts</span>
                </li>
                <li className="flex items-center gap-2">
                  <kbd className="px-1.5 py-0.5 bg-dark-surface rounded text-xs font-mono">Space</kbd>
                  <span>Play/pause timeline</span>
                </li>
              </ul>
            </div>
            <button
              onClick={handleComplete}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
            >
              Start Exploring
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
