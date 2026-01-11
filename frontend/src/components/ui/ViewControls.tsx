'use client';

import { useLocationStore, useUIStore } from '@/lib/store';

export function ViewControls() {
  const { showFlightArcs, setShowFlightArcs } = useLocationStore();
  const { setShortcutsOpen } = useUIStore();

  return (
    <div className="fixed top-20 right-4 z-[90] flex flex-col gap-2">
      {/* Flight arcs toggle */}
      <button
        onClick={() => setShowFlightArcs(!showFlightArcs)}
        className={`flex items-center gap-2 px-3 py-2 rounded-lg backdrop-blur-md border transition-all ${
          showFlightArcs
            ? 'bg-blue-600/20 border-blue-500/50 text-blue-400'
            : 'bg-dark-surface/90 border-dark-border text-dark-muted hover:text-white hover:border-dark-muted'
        }`}
        title={showFlightArcs ? 'Hide flight routes' : 'Show flight routes'}
      >
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
          />
        </svg>
        <span className="text-xs font-medium">
          {showFlightArcs ? 'Routes On' : 'Routes Off'}
        </span>
      </button>

      {/* Keyboard shortcuts button */}
      <button
        onClick={() => setShortcutsOpen(true)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg backdrop-blur-md bg-dark-surface/90 border border-dark-border text-dark-muted hover:text-white hover:border-dark-muted transition-all"
        title="Keyboard shortcuts"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
        </svg>
        <span className="text-xs font-medium">
          <kbd className="font-mono">?</kbd>
        </span>
      </button>
    </div>
  );
}
