"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MapPin, Search, Globe, ArrowRight, Check } from "lucide-react";
import { useApp } from "@/store/app-context";
import { Button, Input, Badge } from "@/components/ui";
import type { Location, SearchResult } from "@/types";

// Mock search results for demo
const MOCK_LOCATIONS: SearchResult[] = [
  { id: "nyc", name: "New York City", country: "United States", type: "city", coordinates: [-74.006, 40.7128], riskScore: 54 },
  { id: "london", name: "London", country: "United Kingdom", type: "city", coordinates: [-0.1276, 51.5074], riskScore: 67 },
  { id: "tokyo", name: "Tokyo", country: "Japan", type: "city", coordinates: [139.6917, 35.6895], riskScore: 32 },
  { id: "paris", name: "Paris", country: "France", type: "city", coordinates: [2.3522, 48.8566], riskScore: 45 },
  { id: "sydney", name: "Sydney", country: "Australia", type: "city", coordinates: [151.2093, -33.8688], riskScore: 28 },
  { id: "berlin", name: "Berlin", country: "Germany", type: "city", coordinates: [13.405, 52.52], riskScore: 41 },
];

interface OnboardingModalProps {
  isOpen: boolean;
  onComplete: () => void;
  onSkip: () => void;
}

export function OnboardingModal({ isOpen, onComplete, onSkip }: OnboardingModalProps) {
  const { setHomeLocation, flyTo, dispatch } = useApp();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLocation, setSelectedLocation] = useState<SearchResult | null>(null);
  const [step, setStep] = useState<"welcome" | "location" | "confirm">("welcome");

  // Filter locations based on search
  const filteredLocations = searchQuery.length > 0
    ? MOCK_LOCATIONS.filter(
        (loc) =>
          loc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          loc.country.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : MOCK_LOCATIONS.slice(0, 4);

  const handleLocationSelect = (location: SearchResult) => {
    setSelectedLocation(location);
    setStep("confirm");
  };

  const handleConfirm = () => {
    if (selectedLocation) {
      // Create a full Location object from the search result
      const fullLocation: Location = {
        id: selectedLocation.id,
        name: selectedLocation.name,
        country: selectedLocation.country,
        countryCode: getCountryCode(selectedLocation.country),
        coordinates: selectedLocation.coordinates,
        riskScore: selectedLocation.riskScore || 0,
        weeklyChange: 0,
        lastUpdated: new Date(),
        variants: [],
      };
      setHomeLocation(fullLocation);
      flyTo(selectedLocation.coordinates[0], selectedLocation.coordinates[1], 5);
      dispatch({ type: "COMPLETE_ONBOARDING" });
      onComplete();
    }
  };

  const handleSkip = () => {
    dispatch({ type: "COMPLETE_ONBOARDING" });
    onSkip();
  };

  const backdropVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1 },
  };

  const modalVariants = {
    hidden: { opacity: 0, scale: 0.95, y: 20 },
    visible: {
      opacity: 1,
      scale: 1,
      y: 0,
      transition: { type: "spring", damping: 25, stiffness: 300 },
    },
    exit: {
      opacity: 0,
      scale: 0.95,
      y: 20,
      transition: { duration: 0.15 },
    },
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial="hidden"
          animate="visible"
          exit="hidden"
          variants={backdropVariants}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
        >
          <motion.div
            variants={modalVariants}
            className="w-full max-w-md bg-background-panel rounded-2xl shadow-xl overflow-hidden panel-light"
          >
            {step === "welcome" && (
              <WelcomeStep onContinue={() => setStep("location")} onSkip={handleSkip} />
            )}
            {step === "location" && (
              <LocationStep
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                locations={filteredLocations}
                onSelect={handleLocationSelect}
                onBack={() => setStep("welcome")}
                onSkip={handleSkip}
              />
            )}
            {step === "confirm" && selectedLocation && (
              <ConfirmStep
                location={selectedLocation}
                onConfirm={handleConfirm}
                onBack={() => setStep("location")}
              />
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Step 1: Welcome
function WelcomeStep({ onContinue, onSkip }: { onContinue: () => void; onSkip: () => void }) {
  return (
    <div className="p-6 text-center">
      <div className="mb-6">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
          <Globe className="h-8 w-8 text-primary" />
        </div>
        <h2 className="text-xl font-semibold text-neutral-900 mb-2">
          Welcome to Viral Weather
        </h2>
        <p className="text-neutral-500 text-sm">
          See viral activity worldwide. Get personalized risk updates for the places you care about.
        </p>
      </div>

      {/* Feature highlights */}
      <div className="space-y-3 mb-6 text-left">
        <FeatureItem
          icon="🌍"
          title="Global Coverage"
          description="Track viral activity across 50+ countries"
        />
        <FeatureItem
          icon="📊"
          title="Real-time Data"
          description="Wastewater surveillance updated daily"
        />
        <FeatureItem
          icon="🔔"
          title="Smart Alerts"
          description="Get notified when risk levels change"
        />
      </div>

      <div className="space-y-3">
        <Button className="w-full" onClick={onContinue}>
          Get Started
          <ArrowRight className="h-4 w-4 ml-2" />
        </Button>
        <Button variant="ghost" className="w-full" onClick={onSkip}>
          Skip for now
        </Button>
      </div>
    </div>
  );
}

function FeatureItem({
  icon,
  title,
  description,
}: {
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="text-xl">{icon}</span>
      <div>
        <p className="font-medium text-neutral-900 text-sm">{title}</p>
        <p className="text-xs text-neutral-500">{description}</p>
      </div>
    </div>
  );
}

// Step 2: Location selection
function LocationStep({
  searchQuery,
  onSearchChange,
  locations,
  onSelect,
  onBack,
  onSkip,
}: {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  locations: SearchResult[];
  onSelect: (location: SearchResult) => void;
  onBack: () => void;
  onSkip: () => void;
}) {
  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={onBack}
          className="p-2 hover:bg-neutral-100 rounded-lg -ml-2"
        >
          <ArrowRight className="h-5 w-5 text-neutral-600 rotate-180" />
        </button>
        <button onClick={onSkip} className="text-sm text-neutral-500 hover:text-neutral-700">
          Skip
        </button>
      </div>

      <div className="text-center mb-6">
        <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-primary/10 flex items-center justify-center">
          <MapPin className="h-6 w-6 text-primary" />
        </div>
        <h2 className="text-lg font-semibold text-neutral-900 mb-1">
          Set your home location
        </h2>
        <p className="text-sm text-neutral-500">
          Get personalized risk updates for your area
        </p>
      </div>

      <Input
        icon={<Search className="h-4 w-4" />}
        placeholder="Search for a city..."
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        className="mb-4"
      />

      <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
        {locations.map((location) => (
          <button
            key={location.id}
            onClick={() => onSelect(location)}
            className="w-full flex items-center justify-between p-3 hover:bg-neutral-50 rounded-lg transition-colors text-left"
          >
            <div className="flex items-center gap-3">
              <span className="text-xl">{getFlagEmoji(getCountryCode(location.country))}</span>
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
        ))}
      </div>
    </div>
  );
}

// Step 3: Confirm selection
function ConfirmStep({
  location,
  onConfirm,
  onBack,
}: {
  location: SearchResult;
  onConfirm: () => void;
  onBack: () => void;
}) {
  return (
    <div className="p-6 text-center">
      <div className="mb-6">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-risk-low/10 flex items-center justify-center">
          <Check className="h-8 w-8 text-risk-low" />
        </div>
        <h2 className="text-lg font-semibold text-neutral-900 mb-2">
          Confirm your location
        </h2>
      </div>

      <div className="p-4 bg-neutral-50 rounded-xl mb-6">
        <div className="flex items-center justify-center gap-3 mb-2">
          <span className="text-3xl">{getFlagEmoji(getCountryCode(location.country))}</span>
          <div className="text-left">
            <p className="text-lg font-semibold text-neutral-900">{location.name}</p>
            <p className="text-sm text-neutral-500">{location.country}</p>
          </div>
        </div>
        {location.riskScore !== undefined && (
          <p className="text-sm text-neutral-600">
            Current risk score: <span className="font-semibold">{location.riskScore}/100</span>
          </p>
        )}
      </div>

      <div className="space-y-3">
        <Button className="w-full" onClick={onConfirm}>
          Set as Home Location
        </Button>
        <Button variant="ghost" className="w-full" onClick={onBack}>
          Choose a different location
        </Button>
      </div>
    </div>
  );
}

// Helper functions
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
  };
  return codes[country] || "XX";
}

export default OnboardingModal;
