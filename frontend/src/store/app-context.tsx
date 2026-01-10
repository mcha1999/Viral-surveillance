"use client";

import React, { createContext, useContext, useReducer, useEffect, ReactNode } from "react";
import type { Location, UserPreferences, ViewState, WatchlistItem } from "@/types";

// State shape
interface AppState {
  // User preferences (persisted to localStorage)
  preferences: UserPreferences;

  // UI state
  selectedLocation: Location | null;
  isOnboardingOpen: boolean;
  isDossierOpen: boolean;
  isSearchOpen: boolean;

  // Globe state
  viewState: ViewState;

  // Data loading states
  isLoading: boolean;
  error: string | null;
}

// Actions
type Action =
  | { type: "SET_HOME_LOCATION"; payload: Location }
  | { type: "CLEAR_HOME_LOCATION" }
  | { type: "SELECT_LOCATION"; payload: Location | null }
  | { type: "TOGGLE_DOSSIER"; payload?: boolean }
  | { type: "TOGGLE_SEARCH"; payload?: boolean }
  | { type: "TOGGLE_ONBOARDING"; payload?: boolean }
  | { type: "SET_VIEW_STATE"; payload: Partial<ViewState> }
  | { type: "ADD_TO_WATCHLIST"; payload: WatchlistItem }
  | { type: "REMOVE_FROM_WATCHLIST"; payload: string }
  | { type: "UPDATE_WATCHLIST_THRESHOLD"; payload: { locationId: string; threshold: number } }
  | { type: "MARK_TOOLTIP_SHOWN"; payload: string }
  | { type: "COMPLETE_ONBOARDING" }
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SET_ERROR"; payload: string | null }
  | { type: "HYDRATE_PREFERENCES"; payload: UserPreferences };

// Initial state
const initialViewState: ViewState = {
  longitude: 0,
  latitude: 20,
  zoom: 1.5,
  pitch: 0,
  bearing: 0,
};

const initialPreferences: UserPreferences = {
  homeLocation: undefined,
  watchlist: [],
  onboardingComplete: false,
  tooltipsShown: [],
};

const initialState: AppState = {
  preferences: initialPreferences,
  selectedLocation: null,
  isOnboardingOpen: false,
  isDossierOpen: false,
  isSearchOpen: false,
  viewState: initialViewState,
  isLoading: false,
  error: null,
};

// Reducer
function appReducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "SET_HOME_LOCATION":
      return {
        ...state,
        preferences: {
          ...state.preferences,
          homeLocation: action.payload,
        },
      };

    case "CLEAR_HOME_LOCATION":
      return {
        ...state,
        preferences: {
          ...state.preferences,
          homeLocation: undefined,
        },
      };

    case "SELECT_LOCATION":
      return {
        ...state,
        selectedLocation: action.payload,
        isDossierOpen: action.payload !== null,
      };

    case "TOGGLE_DOSSIER":
      return {
        ...state,
        isDossierOpen: action.payload ?? !state.isDossierOpen,
      };

    case "TOGGLE_SEARCH":
      return {
        ...state,
        isSearchOpen: action.payload ?? !state.isSearchOpen,
      };

    case "TOGGLE_ONBOARDING":
      return {
        ...state,
        isOnboardingOpen: action.payload ?? !state.isOnboardingOpen,
      };

    case "SET_VIEW_STATE":
      return {
        ...state,
        viewState: {
          ...state.viewState,
          ...action.payload,
        },
      };

    case "ADD_TO_WATCHLIST":
      if (state.preferences.watchlist.length >= 5) {
        return state; // Max 5 items
      }
      return {
        ...state,
        preferences: {
          ...state.preferences,
          watchlist: [...state.preferences.watchlist, action.payload],
        },
      };

    case "REMOVE_FROM_WATCHLIST":
      return {
        ...state,
        preferences: {
          ...state.preferences,
          watchlist: state.preferences.watchlist.filter(
            (item) => item.locationId !== action.payload
          ),
        },
      };

    case "UPDATE_WATCHLIST_THRESHOLD":
      return {
        ...state,
        preferences: {
          ...state.preferences,
          watchlist: state.preferences.watchlist.map((item) =>
            item.locationId === action.payload.locationId
              ? { ...item, alertThreshold: action.payload.threshold }
              : item
          ),
        },
      };

    case "MARK_TOOLTIP_SHOWN":
      if (state.preferences.tooltipsShown.includes(action.payload)) {
        return state;
      }
      return {
        ...state,
        preferences: {
          ...state.preferences,
          tooltipsShown: [...state.preferences.tooltipsShown, action.payload],
        },
      };

    case "COMPLETE_ONBOARDING":
      return {
        ...state,
        preferences: {
          ...state.preferences,
          onboardingComplete: true,
        },
        isOnboardingOpen: false,
      };

    case "SET_LOADING":
      return { ...state, isLoading: action.payload };

    case "SET_ERROR":
      return { ...state, error: action.payload };

    case "HYDRATE_PREFERENCES":
      return {
        ...state,
        preferences: action.payload,
        isOnboardingOpen: !action.payload.onboardingComplete,
      };

    default:
      return state;
  }
}

// Context
interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<Action>;
  // Convenience methods
  setHomeLocation: (location: Location) => void;
  selectLocation: (location: Location | null) => void;
  addToWatchlist: (locationId: string) => void;
  removeFromWatchlist: (locationId: string) => void;
  flyTo: (longitude: number, latitude: number, zoom?: number) => void;
  openSearch: () => void;
  closeSearch: () => void;
  markTooltipShown: (tooltipId: string) => void;
  isTooltipShown: (tooltipId: string) => boolean;
  isInWatchlist: (locationId: string) => boolean;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

// Provider component
export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // Hydrate preferences from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("viral-weather-preferences");
    if (stored) {
      try {
        const preferences = JSON.parse(stored) as UserPreferences;
        dispatch({ type: "HYDRATE_PREFERENCES", payload: preferences });
      } catch (e) {
        console.error("Failed to parse stored preferences:", e);
      }
    } else {
      // Show onboarding for new users
      dispatch({ type: "TOGGLE_ONBOARDING", payload: true });
    }
  }, []);

  // Persist preferences to localStorage
  useEffect(() => {
    localStorage.setItem("viral-weather-preferences", JSON.stringify(state.preferences));
  }, [state.preferences]);

  // Convenience methods
  const setHomeLocation = (location: Location) => {
    dispatch({ type: "SET_HOME_LOCATION", payload: location });
  };

  const selectLocation = (location: Location | null) => {
    dispatch({ type: "SELECT_LOCATION", payload: location });
    if (location) {
      flyTo(location.coordinates[0], location.coordinates[1], 5);
    }
  };

  const addToWatchlist = (locationId: string) => {
    dispatch({
      type: "ADD_TO_WATCHLIST",
      payload: {
        locationId,
        addedAt: new Date(),
        alertThreshold: 50,
      },
    });
  };

  const removeFromWatchlist = (locationId: string) => {
    dispatch({ type: "REMOVE_FROM_WATCHLIST", payload: locationId });
  };

  const flyTo = (longitude: number, latitude: number, zoom = 5) => {
    dispatch({
      type: "SET_VIEW_STATE",
      payload: {
        longitude,
        latitude,
        zoom,
        transitionDuration: 1500,
      },
    });
  };

  const openSearch = () => dispatch({ type: "TOGGLE_SEARCH", payload: true });
  const closeSearch = () => dispatch({ type: "TOGGLE_SEARCH", payload: false });

  const markTooltipShown = (tooltipId: string) => {
    dispatch({ type: "MARK_TOOLTIP_SHOWN", payload: tooltipId });
  };

  const isTooltipShown = (tooltipId: string) => {
    return state.preferences.tooltipsShown.includes(tooltipId);
  };

  const isInWatchlist = (locationId: string) => {
    return state.preferences.watchlist.some((item) => item.locationId === locationId);
  };

  return (
    <AppContext.Provider
      value={{
        state,
        dispatch,
        setHomeLocation,
        selectLocation,
        addToWatchlist,
        removeFromWatchlist,
        flyTo,
        openSearch,
        closeSearch,
        markTooltipShown,
        isTooltipShown,
        isInWatchlist,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

// Hook
export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
}
