import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface LocationState {
  selectedLocation: string | null;
  setSelectedLocation: (id: string | null) => void;
  clearSelectedLocation: () => void;

  currentDate: Date;
  setCurrentDate: (date: Date) => void;

  watchlist: string[];
  addToWatchlist: (id: string) => void;
  removeFromWatchlist: (id: string) => void;
  isInWatchlist: (id: string) => boolean;

  homeLocation: string | null;
  setHomeLocation: (id: string | null) => void;

  // View preferences
  showFlightArcs: boolean;
  setShowFlightArcs: (show: boolean) => void;
}

export const useLocationStore = create<LocationState>()(
  persist(
    (set, get) => ({
      // Selected location
      selectedLocation: null,
      setSelectedLocation: (id) => set({ selectedLocation: id }),
      clearSelectedLocation: () => set({ selectedLocation: null }),

      // Current date for time scrubber
      currentDate: new Date(),
      setCurrentDate: (date) => set({ currentDate: date }),

      // Watchlist (max 5)
      watchlist: [],
      addToWatchlist: (id) => {
        const { watchlist } = get();
        if (watchlist.length < 5 && !watchlist.includes(id)) {
          set({ watchlist: [...watchlist, id] });
        }
      },
      removeFromWatchlist: (id) => {
        set({ watchlist: get().watchlist.filter((w) => w !== id) });
      },
      isInWatchlist: (id) => get().watchlist.includes(id),

      // Home location
      homeLocation: null,
      setHomeLocation: (id) => set({ homeLocation: id }),

      // View preferences
      showFlightArcs: false, // Off by default for cleaner UX
      setShowFlightArcs: (show) => set({ showFlightArcs: show }),
    }),
    {
      name: 'viral-weather-storage',
      partialize: (state) => ({
        watchlist: state.watchlist,
        homeLocation: state.homeLocation,
        showFlightArcs: state.showFlightArcs,
      }),
    }
  )
);

interface UIState {
  isDossierOpen: boolean;
  setDossierOpen: (open: boolean) => void;

  isSearchFocused: boolean;
  setSearchFocused: (focused: boolean) => void;

  isPlaying: boolean;
  setPlaying: (playing: boolean) => void;

  // Keyboard shortcuts modal
  isShortcutsOpen: boolean;
  setShortcutsOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  isDossierOpen: false,
  setDossierOpen: (open) => set({ isDossierOpen: open }),

  isSearchFocused: false,
  setSearchFocused: (focused) => set({ isSearchFocused: focused }),

  isPlaying: false,
  setPlaying: (playing) => set({ isPlaying: playing }),

  isShortcutsOpen: false,
  setShortcutsOpen: (open) => set({ isShortcutsOpen: open }),
}));

// Onboarding state - persisted
interface OnboardingState {
  hasSeenWelcome: boolean;
  setHasSeenWelcome: (seen: boolean) => void;

  hasSeenDossierTooltip: boolean;
  setHasSeenDossierTooltip: (seen: boolean) => void;

  hasSeenWatchlistTooltip: boolean;
  setHasSeenWatchlistTooltip: (seen: boolean) => void;

  hasSeenTimeScrubberTooltip: boolean;
  setHasSeenTimeScrubberTooltip: (seen: boolean) => void;

  hasSeenFlightArcsTooltip: boolean;
  setHasSeenFlightArcsTooltip: (seen: boolean) => void;

  // Getting started checklist
  completedSteps: string[];
  markStepComplete: (step: string) => void;

  locationsViewed: number;
  incrementLocationsViewed: () => void;

  lastVisit: string | null;
  setLastVisit: (date: string) => void;

  // Reset onboarding (for testing)
  resetOnboarding: () => void;
}

export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set, get) => ({
      hasSeenWelcome: false,
      setHasSeenWelcome: (seen) => set({ hasSeenWelcome: seen }),

      hasSeenDossierTooltip: false,
      setHasSeenDossierTooltip: (seen) => set({ hasSeenDossierTooltip: seen }),

      hasSeenWatchlistTooltip: false,
      setHasSeenWatchlistTooltip: (seen) => set({ hasSeenWatchlistTooltip: seen }),

      hasSeenTimeScrubberTooltip: false,
      setHasSeenTimeScrubberTooltip: (seen) => set({ hasSeenTimeScrubberTooltip: seen }),

      hasSeenFlightArcsTooltip: false,
      setHasSeenFlightArcsTooltip: (seen) => set({ hasSeenFlightArcsTooltip: seen }),

      completedSteps: [],
      markStepComplete: (step) => {
        const { completedSteps } = get();
        if (!completedSteps.includes(step)) {
          set({ completedSteps: [...completedSteps, step] });
        }
      },

      locationsViewed: 0,
      incrementLocationsViewed: () => set({ locationsViewed: get().locationsViewed + 1 }),

      lastVisit: null,
      setLastVisit: (date) => set({ lastVisit: date }),

      resetOnboarding: () => set({
        hasSeenWelcome: false,
        hasSeenDossierTooltip: false,
        hasSeenWatchlistTooltip: false,
        hasSeenTimeScrubberTooltip: false,
        hasSeenFlightArcsTooltip: false,
        completedSteps: [],
        locationsViewed: 0,
      }),
    }),
    {
      name: 'viral-weather-onboarding',
    }
  )
);
