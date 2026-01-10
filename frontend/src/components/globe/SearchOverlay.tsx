"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, X, MapPin, Clock } from "lucide-react";
import { useApp } from "@/store/app-context";
import { Badge } from "@/components/ui";
import type { SearchResult } from "@/types";

// Mock search results
const MOCK_LOCATIONS: SearchResult[] = [
  { id: "nyc", name: "New York City", country: "United States", type: "city", coordinates: [-74.006, 40.7128], riskScore: 54 },
  { id: "london", name: "London", country: "United Kingdom", type: "city", coordinates: [-0.1276, 51.5074], riskScore: 67 },
  { id: "tokyo", name: "Tokyo", country: "Japan", type: "city", coordinates: [139.6917, 35.6895], riskScore: 32 },
  { id: "paris", name: "Paris", country: "France", type: "city", coordinates: [2.3522, 48.8566], riskScore: 45 },
  { id: "sydney", name: "Sydney", country: "Australia", type: "city", coordinates: [151.2093, -33.8688], riskScore: 28 },
  { id: "berlin", name: "Berlin", country: "Germany", type: "city", coordinates: [13.405, 52.52], riskScore: 41 },
  { id: "singapore", name: "Singapore", country: "Singapore", type: "city", coordinates: [103.8198, 1.3521], riskScore: 25 },
  { id: "amsterdam", name: "Amsterdam", country: "Netherlands", type: "city", coordinates: [4.9041, 52.3676], riskScore: 38 },
  { id: "seoul", name: "Seoul", country: "South Korea", type: "city", coordinates: [126.978, 37.5665], riskScore: 42 },
  { id: "toronto", name: "Toronto", country: "Canada", type: "city", coordinates: [-79.3832, 43.6532], riskScore: 35 },
];

export function SearchOverlay() {
  const { state, closeSearch, flyTo, selectLocation } = useApp();
  const [query, setQuery] = useState("");
  const [recentSearches, setRecentSearches] = useState<SearchResult[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when opened
  useEffect(() => {
    if (state.isSearchOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [state.isSearchOpen]);

  // Load recent searches from localStorage
  useEffect(() => {
    const stored = localStorage.getItem("viral-weather-recent-searches");
    if (stored) {
      try {
        setRecentSearches(JSON.parse(stored));
      } catch (e) {
        console.error("Failed to parse recent searches:", e);
      }
    }
  }, []);

  // Handle Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && state.isSearchOpen) {
        closeSearch();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [state.isSearchOpen, closeSearch]);

  // Filter results
  const results = query.length > 0
    ? MOCK_LOCATIONS.filter(
        (loc) =>
          loc.name.toLowerCase().includes(query.toLowerCase()) ||
          loc.country.toLowerCase().includes(query.toLowerCase())
      )
    : [];

  const handleSelect = (location: SearchResult) => {
    // Add to recent searches
    const updated = [
      location,
      ...recentSearches.filter((r) => r.id !== location.id),
    ].slice(0, 5);
    setRecentSearches(updated);
    localStorage.setItem("viral-weather-recent-searches", JSON.stringify(updated));

    // Navigate to location
    flyTo(location.coordinates[0], location.coordinates[1], 5);

    // Select the location (would need full Location data in real app)
    selectLocation({
      id: location.id,
      name: location.name,
      country: location.country,
      countryCode: getCountryCode(location.country),
      coordinates: location.coordinates,
      riskScore: location.riskScore || 0,
      weeklyChange: Math.floor(Math.random() * 20) - 10,
      lastUpdated: new Date(),
      variants: [],
    });

    setQuery("");
    closeSearch();
  };

  const overlayVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1 },
  };

  const panelVariants = {
    hidden: { opacity: 0, y: -20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { type: "spring", damping: 25, stiffness: 300 },
    },
    exit: {
      opacity: 0,
      y: -20,
      transition: { duration: 0.15 },
    },
  };

  return (
    <AnimatePresence>
      {state.isSearchOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial="hidden"
            animate="visible"
            exit="hidden"
            variants={overlayVariants}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
            onClick={closeSearch}
          />

          {/* Search Panel */}
          <motion.div
            initial="hidden"
            animate="visible"
            exit="exit"
            variants={panelVariants}
            className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-full max-w-lg px-4"
          >
            <div className="bg-background-panel rounded-xl shadow-xl overflow-hidden panel-light">
              {/* Search Input */}
              <div className="relative p-3 border-b border-neutral-200">
                <Search className="absolute left-6 top-1/2 -translate-y-1/2 h-5 w-5 text-neutral-400" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search for a city or country..."
                  className="w-full pl-10 pr-10 py-2 bg-transparent text-neutral-900 placeholder:text-neutral-400 focus:outline-none"
                />
                <button
                  onClick={closeSearch}
                  className="absolute right-6 top-1/2 -translate-y-1/2 p-1 hover:bg-neutral-100 rounded"
                >
                  <X className="h-4 w-4 text-neutral-400" />
                </button>
              </div>

              {/* Results */}
              <div className="max-h-80 overflow-y-auto custom-scrollbar">
                {query.length > 0 ? (
                  results.length > 0 ? (
                    <div className="p-2">
                      {results.map((location) => (
                        <SearchResultItem
                          key={location.id}
                          location={location}
                          onClick={() => handleSelect(location)}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="p-6 text-center text-neutral-500">
                      <p className="text-sm">No results found for &quot;{query}&quot;</p>
                    </div>
                  )
                ) : recentSearches.length > 0 ? (
                  <div className="p-2">
                    <p className="px-3 py-2 text-xs font-medium text-neutral-400 uppercase tracking-wider">
                      Recent Searches
                    </p>
                    {recentSearches.map((location) => (
                      <SearchResultItem
                        key={location.id}
                        location={location}
                        onClick={() => handleSelect(location)}
                        showRecent
                      />
                    ))}
                  </div>
                ) : (
                  <div className="p-6 text-center text-neutral-500">
                    <MapPin className="h-8 w-8 mx-auto mb-2 text-neutral-300" />
                    <p className="text-sm">Start typing to search locations</p>
                  </div>
                )}
              </div>

              {/* Keyboard hint */}
              <div className="p-2 border-t border-neutral-200 bg-neutral-50">
                <div className="flex items-center justify-between text-xs text-neutral-400 px-2">
                  <span>Press <kbd className="px-1.5 py-0.5 bg-neutral-200 rounded text-neutral-600">Enter</kbd> to select</span>
                  <span><kbd className="px-1.5 py-0.5 bg-neutral-200 rounded text-neutral-600">Esc</kbd> to close</span>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function SearchResultItem({
  location,
  onClick,
  showRecent = false,
}: {
  location: SearchResult;
  onClick: () => void;
  showRecent?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center justify-between p-3 hover:bg-neutral-50 rounded-lg transition-colors text-left"
    >
      <div className="flex items-center gap-3">
        {showRecent ? (
          <Clock className="h-4 w-4 text-neutral-400" />
        ) : (
          <span className="text-lg">{getFlagEmoji(getCountryCode(location.country))}</span>
        )}
        <div>
          <p className="font-medium text-neutral-900">{location.name}</p>
          <p className="text-xs text-neutral-500">{location.country}</p>
        </div>
      </div>
      {location.riskScore !== undefined && (
        <Badge
          variant={
            location.riskScore <= 20
              ? "low"
              : location.riskScore <= 40
              ? "moderate"
              : location.riskScore <= 60
              ? "elevated"
              : "high"
          }
        >
          {location.riskScore}
        </Badge>
      )}
    </button>
  );
}

// Helpers
function getFlagEmoji(countryCode: string): string {
  if (!countryCode || countryCode.length !== 2) return "🌍";
  const codePoints = countryCode
    .toUpperCase()
    .split("")
    .map((char) => 127397 + char.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
}

function getCountryCode(country: string): string {
  const codes: Record<string, string> = {
    "United States": "US",
    "United Kingdom": "GB",
    Japan: "JP",
    France: "FR",
    Australia: "AU",
    Germany: "DE",
    Singapore: "SG",
    Netherlands: "NL",
    "South Korea": "KR",
    Canada: "CA",
  };
  return codes[country] || "XX";
}

export default SearchOverlay;
