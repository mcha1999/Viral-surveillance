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
    }),
    {
      name: 'viral-weather-storage',
      partialize: (state) => ({
        watchlist: state.watchlist,
        homeLocation: state.homeLocation,
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
}

export const useUIStore = create<UIState>((set) => ({
  isDossierOpen: false,
  setDossierOpen: (open) => set({ isDossierOpen: open }),

  isSearchFocused: false,
  setSearchFocused: (focused) => set({ isSearchFocused: focused }),

  isPlaying: false,
  setPlaying: (playing) => set({ isPlaying: playing }),
}));
