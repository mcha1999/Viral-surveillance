'use client';

import { useState, useEffect } from 'react';
import { Globe } from '@/components/globe/Globe';
import { SearchBar } from '@/components/ui/SearchBar';
import { DossierPanel } from '@/components/dossier/DossierPanel';
import { TimeScrubber } from '@/components/ui/TimeScrubber';
import { Watchlist } from '@/components/watchlist/Watchlist';
import { ViewControls } from '@/components/ui/ViewControls';
import { WelcomeModal, WelcomeBack, GettingStarted, KeyboardShortcuts } from '@/components/onboarding';
import { useLocationStore, useOnboardingStore, useUIStore } from '@/lib/store';

export default function Home() {
  const { selectedLocation, showFlightArcs, homeLocation, setSelectedLocation } = useLocationStore();
  const {
    hasSeenWelcome,
    lastVisit,
    setLastVisit,
    locationsViewed,
  } = useOnboardingStore();
  const { setShortcutsOpen } = useUIStore();

  const [currentDate, setCurrentDate] = useState(new Date());
  const [showWelcome, setShowWelcome] = useState(false);
  const [showWelcomeBack, setShowWelcomeBack] = useState(false);
  const [showGettingStarted, setShowGettingStarted] = useState(true);

  // Initialize onboarding state
  useEffect(() => {
    // Check if first visit
    if (!hasSeenWelcome) {
      setShowWelcome(true);
      return;
    }

    // Check if returning user (visited more than 1 hour ago)
    if (lastVisit) {
      const lastVisitDate = new Date(lastVisit);
      const hoursSinceVisit = (Date.now() - lastVisitDate.getTime()) / (1000 * 60 * 60);

      if (hoursSinceVisit > 1 && homeLocation) {
        setShowWelcomeBack(true);
      }
    }

    // Update last visit
    setLastVisit(new Date().toISOString());
  }, [hasSeenWelcome, lastVisit, homeLocation, setLastVisit]);

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in input
      if (document.activeElement?.tagName === 'INPUT' ||
          document.activeElement?.tagName === 'TEXTAREA') {
        return;
      }

      // H - Go to home location
      if (e.key === 'h' || e.key === 'H') {
        if (homeLocation) {
          setSelectedLocation(homeLocation);
        }
      }

      // F - Toggle flight routes
      if (e.key === 'f' || e.key === 'F') {
        const { showFlightArcs, setShowFlightArcs } = useLocationStore.getState();
        setShowFlightArcs(!showFlightArcs);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [homeLocation, setSelectedLocation]);

  const handleWelcomeComplete = () => {
    setShowWelcome(false);
    setLastVisit(new Date().toISOString());
  };

  const handleWelcomeBackDismiss = () => {
    setShowWelcomeBack(false);
  };

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-dark-bg">
      {/* Globe (background) */}
      <div className="globe-container">
        <Globe currentDate={currentDate} showFlightArcs={showFlightArcs} />
      </div>

      {/* Search bar (top center) */}
      <div className="search-bar">
        <SearchBar />
      </div>

      {/* View controls (top right) */}
      <ViewControls />

      {/* Watchlist (top left) */}
      <div className="fixed top-20 left-4 z-[90] w-72">
        <Watchlist />
      </div>

      {/* Dossier panel (right side, shown when location selected) */}
      {selectedLocation && (
        <DossierPanel locationId={selectedLocation} />
      )}

      {/* Time scrubber (bottom) */}
      <div className="time-scrubber">
        <TimeScrubber
          currentDate={currentDate}
          onDateChange={setCurrentDate}
        />
      </div>

      {/* Getting started checklist */}
      {showGettingStarted && hasSeenWelcome && locationsViewed < 5 && (
        <GettingStarted onClose={() => setShowGettingStarted(false)} />
      )}

      {/* Attribution */}
      <div className="fixed bottom-16 left-4 text-xs text-dark-muted">
        Data: CDC NWSS, Nextstrain, AviationStack
      </div>

      {/* Modals */}
      {showWelcome && (
        <WelcomeModal onComplete={handleWelcomeComplete} />
      )}

      {showWelcomeBack && (
        <WelcomeBack onDismiss={handleWelcomeBackDismiss} />
      )}

      <KeyboardShortcuts />
    </main>
  );
}
