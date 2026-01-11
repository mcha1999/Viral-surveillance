'use client';

import { useState } from 'react';
import { useOnboardingStore, useLocationStore } from '@/lib/store';

const STEPS = [
  {
    id: 'set_home',
    label: 'Set your home location',
    description: 'Get personalized updates',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    id: 'explore_globe',
    label: 'Explore the globe',
    description: 'Click a location to view details',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    id: 'add_watchlist',
    label: 'Add to watchlist',
    description: 'Track important locations',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
    ),
  },
  {
    id: 'view_history',
    label: 'View location history',
    description: 'Use the time scrubber',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    id: 'explore_routes',
    label: 'Explore flight routes',
    description: 'See transmission paths',
    icon: (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
      </svg>
    ),
  },
];

interface GettingStartedProps {
  onClose?: () => void;
}

export function GettingStarted({ onClose }: GettingStartedProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const { completedSteps, locationsViewed } = useOnboardingStore();
  const { homeLocation, watchlist } = useLocationStore();

  // Calculate which steps are actually completed based on state
  const actualCompletedSteps = [
    ...(homeLocation ? ['set_home'] : []),
    ...(locationsViewed > 0 ? ['explore_globe'] : []),
    ...(watchlist.length > 0 ? ['add_watchlist'] : []),
    ...completedSteps,
  ];

  const uniqueCompleted = Array.from(new Set(actualCompletedSteps));
  const progress = (uniqueCompleted.length / STEPS.length) * 100;

  // Hide if all steps complete
  if (uniqueCompleted.length >= STEPS.length) {
    return null;
  }

  return (
    <div className="fixed bottom-20 left-4 z-[100] w-72">
      <div className="bg-dark-surface/95 backdrop-blur-md border border-dark-border rounded-lg shadow-xl overflow-hidden">
        {/* Header */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors"
        >
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <span className="text-white font-medium text-sm">Getting Started</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-dark-muted">{uniqueCompleted.length}/{STEPS.length}</span>
            <svg
              className={`w-4 h-4 text-dark-muted transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </button>

        {/* Progress bar */}
        <div className="h-1 bg-dark-bg">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Steps */}
        {isExpanded && (
          <div className="p-3 space-y-1">
            {STEPS.map((step) => {
              const isComplete = uniqueCompleted.includes(step.id);
              return (
                <div
                  key={step.id}
                  className={`flex items-center gap-3 p-2 rounded-lg transition-colors ${
                    isComplete ? 'bg-green-500/10' : 'hover:bg-white/5'
                  }`}
                >
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                      isComplete
                        ? 'bg-green-500 text-white'
                        : 'bg-dark-bg text-dark-muted'
                    }`}
                  >
                    {isComplete ? (
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      step.icon
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className={`text-sm ${isComplete ? 'text-green-400 line-through' : 'text-white'}`}>
                      {step.label}
                    </div>
                    <div className="text-xs text-dark-muted truncate">
                      {step.description}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Close button when collapsed */}
        {!isExpanded && onClose && (
          <button
            onClick={onClose}
            className="absolute top-2 right-2 p-1 hover:bg-white/10 rounded transition-colors"
            aria-label="Close getting started"
          >
            <svg className="w-4 h-4 text-dark-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
