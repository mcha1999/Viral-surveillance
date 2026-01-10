import { describe, it, expect, beforeEach } from 'vitest';
import { useLocationStore } from './store';

describe('useLocationStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useLocationStore.setState({
      selectedLocation: null,
      currentDate: new Date(),
      watchlist: [],
    });
  });

  describe('selectedLocation', () => {
    it('should initialize with null', () => {
      const state = useLocationStore.getState();
      expect(state.selectedLocation).toBeNull();
    });

    it('should set selected location', () => {
      useLocationStore.getState().setSelectedLocation('loc_us_new_york');

      const state = useLocationStore.getState();
      expect(state.selectedLocation).toBe('loc_us_new_york');
    });

    it('should clear selected location', () => {
      useLocationStore.getState().setSelectedLocation('loc_us_new_york');
      useLocationStore.getState().clearSelectedLocation();

      const state = useLocationStore.getState();
      expect(state.selectedLocation).toBeNull();
    });
  });

  describe('currentDate', () => {
    it('should initialize with current date', () => {
      const state = useLocationStore.getState();
      expect(state.currentDate).toBeInstanceOf(Date);
    });

    it('should update current date', () => {
      const newDate = new Date('2026-01-15');
      useLocationStore.getState().setCurrentDate(newDate);

      const state = useLocationStore.getState();
      expect(state.currentDate.toISOString()).toBe(newDate.toISOString());
    });
  });

  describe('watchlist', () => {
    it('should initialize with empty array', () => {
      const state = useLocationStore.getState();
      expect(state.watchlist).toEqual([]);
    });

    it('should add location to watchlist', () => {
      useLocationStore.getState().addToWatchlist('loc_us_new_york');

      const state = useLocationStore.getState();
      expect(state.watchlist).toContain('loc_us_new_york');
    });

    it('should not add duplicate to watchlist', () => {
      useLocationStore.getState().addToWatchlist('loc_us_new_york');
      useLocationStore.getState().addToWatchlist('loc_us_new_york');

      const state = useLocationStore.getState();
      expect(state.watchlist.filter(id => id === 'loc_us_new_york')).toHaveLength(1);
    });

    it('should remove location from watchlist', () => {
      useLocationStore.getState().addToWatchlist('loc_us_new_york');
      useLocationStore.getState().addToWatchlist('loc_gb_london');
      useLocationStore.getState().removeFromWatchlist('loc_us_new_york');

      const state = useLocationStore.getState();
      expect(state.watchlist).not.toContain('loc_us_new_york');
      expect(state.watchlist).toContain('loc_gb_london');
    });

    it('should check if location is in watchlist', () => {
      useLocationStore.getState().addToWatchlist('loc_us_new_york');

      const state = useLocationStore.getState();
      expect(state.isInWatchlist('loc_us_new_york')).toBe(true);
      expect(state.isInWatchlist('loc_gb_london')).toBe(false);
    });

    it('should enforce watchlist limit of 5', () => {
      const locations = [
        'loc_1', 'loc_2', 'loc_3', 'loc_4', 'loc_5', 'loc_6'
      ];

      locations.forEach(loc => {
        useLocationStore.getState().addToWatchlist(loc);
      });

      const state = useLocationStore.getState();
      expect(state.watchlist.length).toBeLessThanOrEqual(5);
    });
  });
});
