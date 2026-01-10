"use client";

import React, { useState, useMemo } from "react";
import { Search, Home, Bell } from "lucide-react";
import { AppProvider, useApp } from "@/store/app-context";
import { Globe, SearchOverlay, TimeScrubber } from "@/components/globe";
import { DossierPanel } from "@/components/dossier";
import { OnboardingModal } from "@/components/onboarding";
import { Button } from "@/components/ui";
import type { Location, FlightArc } from "@/types";

// Mock data for demo
const MOCK_LOCATIONS: Location[] = [
  {
    id: "nyc",
    name: "New York City",
    country: "United States",
    countryCode: "US",
    coordinates: [-74.006, 40.7128],
    population: 8400000,
    riskScore: 54,
    weeklyChange: 12,
    lastUpdated: new Date(Date.now() - 2 * 3600000),
    variants: [
      { id: "jn1", name: "JN.1", prevalence: 68, severity: "moderate", transmissibility: "high" },
      { id: "ba286", name: "BA.2.86", prevalence: 22, severity: "moderate", transmissibility: "moderate" },
    ],
  },
  {
    id: "london",
    name: "London",
    country: "United Kingdom",
    countryCode: "GB",
    coordinates: [-0.1276, 51.5074],
    population: 8982000,
    riskScore: 67,
    weeklyChange: 8,
    lastUpdated: new Date(Date.now() - 4 * 3600000),
    variants: [
      { id: "jn1", name: "JN.1", prevalence: 72, severity: "moderate", transmissibility: "high" },
    ],
  },
  {
    id: "tokyo",
    name: "Tokyo",
    country: "Japan",
    countryCode: "JP",
    coordinates: [139.6917, 35.6895],
    population: 13960000,
    riskScore: 32,
    weeklyChange: -5,
    lastUpdated: new Date(Date.now() - 6 * 3600000),
    variants: [
      { id: "jn1", name: "JN.1", prevalence: 45, severity: "moderate", transmissibility: "high" },
    ],
  },
  {
    id: "paris",
    name: "Paris",
    country: "France",
    countryCode: "FR",
    coordinates: [2.3522, 48.8566],
    population: 2161000,
    riskScore: 45,
    weeklyChange: 3,
    lastUpdated: new Date(Date.now() - 3 * 3600000),
    variants: [],
  },
  {
    id: "sydney",
    name: "Sydney",
    country: "Australia",
    countryCode: "AU",
    coordinates: [151.2093, -33.8688],
    population: 5312000,
    riskScore: 28,
    weeklyChange: -2,
    lastUpdated: new Date(Date.now() - 8 * 3600000),
    variants: [],
  },
  {
    id: "berlin",
    name: "Berlin",
    country: "Germany",
    countryCode: "DE",
    coordinates: [13.405, 52.52],
    population: 3645000,
    riskScore: 41,
    weeklyChange: 1,
    lastUpdated: new Date(Date.now() - 5 * 3600000),
    variants: [],
  },
  {
    id: "singapore",
    name: "Singapore",
    country: "Singapore",
    countryCode: "SG",
    coordinates: [103.8198, 1.3521],
    population: 5686000,
    riskScore: 25,
    weeklyChange: -3,
    lastUpdated: new Date(Date.now() - 4 * 3600000),
    variants: [],
  },
  {
    id: "mumbai",
    name: "Mumbai",
    country: "India",
    countryCode: "IN",
    coordinates: [72.8777, 19.076],
    population: 20411000,
    riskScore: 58,
    weeklyChange: 15,
    lastUpdated: new Date(Date.now() - 12 * 3600000),
    variants: [],
  },
  {
    id: "saopaulo",
    name: "São Paulo",
    country: "Brazil",
    countryCode: "BR",
    coordinates: [-46.6333, -23.5505],
    population: 12325000,
    riskScore: 72,
    weeklyChange: 20,
    lastUpdated: new Date(Date.now() - 6 * 3600000),
    variants: [],
  },
  {
    id: "seoul",
    name: "Seoul",
    country: "South Korea",
    countryCode: "KR",
    coordinates: [126.978, 37.5665],
    population: 9776000,
    riskScore: 42,
    weeklyChange: 0,
    lastUpdated: new Date(Date.now() - 3 * 3600000),
    variants: [],
  },
];

const MOCK_FLIGHT_ARCS: FlightArc[] = [
  {
    id: "arc1",
    origin: MOCK_LOCATIONS[1], // London
    destination: MOCK_LOCATIONS[0], // NYC
    dailyPassengers: 12000,
    riskContribution: 15,
  },
  {
    id: "arc2",
    origin: MOCK_LOCATIONS[3], // Paris
    destination: MOCK_LOCATIONS[0], // NYC
    dailyPassengers: 8500,
    riskContribution: 8,
  },
  {
    id: "arc3",
    origin: MOCK_LOCATIONS[2], // Tokyo
    destination: MOCK_LOCATIONS[0], // NYC
    dailyPassengers: 5200,
    riskContribution: 5,
  },
];

export default function HomePage() {
  return (
    <AppProvider>
      <MainContent />
    </AppProvider>
  );
}

function MainContent() {
  const { state, dispatch, openSearch } = useApp();
  const [currentDate, setCurrentDate] = useState(new Date());

  // Calculate date range (30 days back, 7 days forward)
  const dateRange = useMemo(() => {
    const end = new Date();
    end.setDate(end.getDate() + 7);
    const start = new Date();
    start.setDate(start.getDate() - 30);
    return { start, end };
  }, []);

  // Get flight arcs for selected location
  const selectedArcs = useMemo(() => {
    if (!state.selectedLocation) return [];
    return MOCK_FLIGHT_ARCS.filter(
      (arc) => arc.destination.id === state.selectedLocation?.id
    );
  }, [state.selectedLocation]);

  const handleOnboardingComplete = () => {
    dispatch({ type: "TOGGLE_ONBOARDING", payload: false });
  };

  const handleOnboardingSkip = () => {
    dispatch({ type: "TOGGLE_ONBOARDING", payload: false });
  };

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-background">
      {/* Header */}
      <header className="absolute top-0 left-0 right-0 z-20 p-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
              <span className="text-white font-bold text-lg">V</span>
            </div>
            <div className="hidden sm:block">
              <h1 className="font-semibold text-foreground text-lg">Viral Weather</h1>
              <p className="text-xs text-foreground-muted">Real-time viral radar</p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {/* Search button */}
            <Button
              variant="secondary"
              size="sm"
              onClick={openSearch}
              className="glass-dark border-0"
            >
              <Search className="h-4 w-4 mr-2" />
              <span className="hidden sm:inline">Search</span>
              <kbd className="hidden sm:inline ml-2 px-1.5 py-0.5 text-[10px] bg-white/10 rounded">
                /
              </kbd>
            </Button>

            {/* Home button (if home location set) */}
            {state.preferences.homeLocation && (
              <Button
                variant="ghost"
                size="icon-sm"
                className="glass-dark border-0"
                onClick={() => {
                  if (state.preferences.homeLocation) {
                    const home = state.preferences.homeLocation;
                    dispatch({
                      type: "SET_VIEW_STATE",
                      payload: {
                        longitude: home.coordinates[0],
                        latitude: home.coordinates[1],
                        zoom: 5,
                        transitionDuration: 1500,
                      },
                    });
                  }
                }}
              >
                <Home className="h-4 w-4" />
              </Button>
            )}

            {/* Notifications */}
            <Button variant="ghost" size="icon-sm" className="glass-dark border-0 relative">
              <Bell className="h-4 w-4" />
              {state.preferences.watchlist.length > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-risk-high text-white text-[10px] rounded-full flex items-center justify-center">
                  {state.preferences.watchlist.length}
                </span>
              )}
            </Button>
          </div>
        </div>
      </header>

      {/* Global Stats Bar */}
      <div className="absolute top-20 left-4 z-10">
        <div className="glass-dark rounded-lg px-3 py-2 flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-risk-high animate-pulse" />
            <span className="text-xs text-foreground-secondary">
              <span className="font-semibold text-foreground">3</span> Hot Zones
            </span>
          </div>
          <div className="w-px h-4 bg-border" />
          <div className="text-xs text-foreground-secondary">
            Global trend: <span className="text-risk-elevated font-medium">Rising</span>
          </div>
        </div>
      </div>

      {/* Globe */}
      <Globe
        locations={MOCK_LOCATIONS}
        flightArcs={MOCK_FLIGHT_ARCS}
        showArcs={!!state.selectedLocation}
        className="absolute inset-0"
      />

      {/* Time Scrubber */}
      <div className="absolute bottom-0 left-0 right-0 z-10 md:right-[400px]">
        <TimeScrubber
          startDate={dateRange.start}
          endDate={dateRange.end}
          currentDate={currentDate}
          onDateChange={setCurrentDate}
          forecastDays={7}
        />
      </div>

      {/* Dossier Panel */}
      <DossierPanel
        location={state.selectedLocation}
        flightArcs={selectedArcs}
      />

      {/* Search Overlay */}
      <SearchOverlay />

      {/* Onboarding Modal */}
      <OnboardingModal
        isOpen={state.isOnboardingOpen}
        onComplete={handleOnboardingComplete}
        onSkip={handleOnboardingSkip}
      />

      {/* Keyboard shortcuts listener */}
      <KeyboardShortcuts />
    </div>
  );
}

// Keyboard shortcuts handler
function KeyboardShortcuts() {
  const { openSearch, dispatch, state } = useApp();

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      switch (e.key) {
        case "/":
          e.preventDefault();
          openSearch();
          break;
        case "Escape":
          if (state.isSearchOpen) {
            dispatch({ type: "TOGGLE_SEARCH", payload: false });
          } else if (state.isDossierOpen) {
            dispatch({ type: "SELECT_LOCATION", payload: null });
          }
          break;
        case "h":
        case "H":
          if (state.preferences.homeLocation) {
            const home = state.preferences.homeLocation;
            dispatch({
              type: "SET_VIEW_STATE",
              payload: {
                longitude: home.coordinates[0],
                latitude: home.coordinates[1],
                zoom: 5,
                transitionDuration: 1500,
              },
            });
          }
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [openSearch, dispatch, state]);

  return null;
}
