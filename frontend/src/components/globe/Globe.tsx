"use client";

import React, { useCallback, useMemo, useState, useEffect } from "react";
import { DeckGL } from "@deck.gl/react";
import { GlobeView } from "@deck.gl/core";
import { ScatterplotLayer, ArcLayer } from "@deck.gl/layers";
import { cn, getRiskLevel } from "@/lib/utils";
import { useApp } from "@/store/app-context";
import type { Location, FlightArc, RiskLevel } from "@/types";
import { SkeletonGlobe } from "@/components/ui";

// Risk level to color mapping
const RISK_COLORS: Record<RiskLevel, [number, number, number, number]> = {
  low: [34, 197, 94, 200], // Green
  moderate: [234, 179, 8, 200], // Yellow
  elevated: [249, 115, 22, 200], // Orange
  high: [239, 68, 68, 200], // Red
  "very-high": [153, 27, 27, 200], // Dark red
};

interface GlobeProps {
  locations: Location[];
  flightArcs?: FlightArc[];
  showArcs?: boolean;
  onLocationClick?: (location: Location) => void;
  onLocationHover?: (location: Location | null) => void;
  className?: string;
}

export function Globe({
  locations,
  flightArcs = [],
  showArcs = false,
  onLocationClick,
  onLocationHover,
  className,
}: GlobeProps) {
  const { state, dispatch, selectLocation } = useApp();
  const [isLoading, setIsLoading] = useState(true);
  const [hoveredLocation, setHoveredLocation] = useState<Location | null>(null);

  // Simulate loading
  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 1500);
    return () => clearTimeout(timer);
  }, []);

  // Handle view state changes
  const onViewStateChange = useCallback(
    ({ viewState }: { viewState: Record<string, unknown> }) => {
      dispatch({
        type: "SET_VIEW_STATE",
        payload: viewState as { longitude: number; latitude: number; zoom: number },
      });
    },
    [dispatch]
  );

  // Location marker layer
  const locationLayer = useMemo(
    () =>
      new ScatterplotLayer<Location>({
        id: "locations",
        data: locations,
        pickable: true,
        opacity: 0.8,
        stroked: true,
        filled: true,
        radiusScale: 1,
        radiusMinPixels: 8,
        radiusMaxPixels: 30,
        lineWidthMinPixels: 2,
        getPosition: (d) => d.coordinates,
        getRadius: (d) => {
          // Scale by population if available, otherwise use risk score
          const base = d.population ? Math.log10(d.population) * 2 : 10;
          return base * (0.5 + d.riskScore / 200);
        },
        getFillColor: (d) => RISK_COLORS[getRiskLevel(d.riskScore)],
        getLineColor: [255, 255, 255, 180],
        onClick: ({ object }) => {
          if (object) {
            onLocationClick?.(object);
            selectLocation(object);
          }
        },
        onHover: ({ object }) => {
          setHoveredLocation(object || null);
          onLocationHover?.(object || null);
        },
        updateTriggers: {
          getFillColor: [locations],
          getRadius: [locations],
        },
      }),
    [locations, onLocationClick, onLocationHover, selectLocation]
  );

  // Flight arc layer
  const arcLayer = useMemo(
    () =>
      showArcs
        ? new ArcLayer<FlightArc>({
            id: "flight-arcs",
            data: flightArcs,
            pickable: true,
            getSourcePosition: (d) => d.origin.coordinates,
            getTargetPosition: (d) => d.destination.coordinates,
            getSourceColor: (d) => RISK_COLORS[getRiskLevel(d.origin.riskScore)],
            getTargetColor: (d) => RISK_COLORS[getRiskLevel(d.destination.riskScore)],
            getWidth: (d) => Math.log10(d.dailyPassengers + 1) * 0.5,
            getHeight: 0.5,
            greatCircle: true,
          })
        : null,
    [flightArcs, showArcs]
  );

  const layers = useMemo(
    () => [locationLayer, arcLayer].filter(Boolean),
    [locationLayer, arcLayer]
  );

  // Globe view configuration
  const views = useMemo(() => new GlobeView({ id: "globe", resolution: 10 }), []);

  if (isLoading) {
    return <SkeletonGlobe className={className} />;
  }

  return (
    <div className={cn("relative w-full h-full", className)}>
      <DeckGL
        views={views}
        viewState={state.viewState}
        onViewStateChange={onViewStateChange}
        layers={layers}
        controller={{
          inertia: true,
          scrollZoom: { speed: 0.01, smooth: true },
          dragRotate: true,
          touchRotate: true,
        }}
        getCursor={({ isHovering }) => (isHovering ? "pointer" : "grab")}
        style={{ background: "linear-gradient(180deg, #0F172A 0%, #1E293B 100%)" }}
      />

      {/* Hover tooltip */}
      {hoveredLocation && (
        <LocationTooltip location={hoveredLocation} />
      )}

      {/* Globe controls hint */}
      <div className="absolute bottom-4 left-4 text-xs text-foreground-muted glass-dark rounded-lg px-3 py-2">
        <span>Scroll to zoom • Drag to rotate</span>
      </div>
    </div>
  );
}

// Location tooltip on hover
function LocationTooltip({ location }: { location: Location }) {
  const riskLevel = getRiskLevel(location.riskScore);

  return (
    <div className="absolute top-4 left-4 glass-dark rounded-lg p-3 max-w-xs pointer-events-none animate-fade-in">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{getFlagEmoji(location.countryCode)}</span>
        <span className="font-semibold text-foreground">{location.name}</span>
      </div>
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "inline-flex items-center justify-center w-8 h-8 rounded-lg font-bold font-mono text-sm",
            `bg-risk-${riskLevel}/30 text-risk-${riskLevel}`
          )}
        >
          {location.riskScore}
        </span>
        <span className="text-sm text-foreground-secondary">
          {location.weeklyChange > 0 ? "+" : ""}
          {location.weeklyChange}% this week
        </span>
      </div>
    </div>
  );
}

// Helper to get flag emoji from country code
function getFlagEmoji(countryCode: string): string {
  if (!countryCode || countryCode.length !== 2) return "🌍";
  const codePoints = countryCode
    .toUpperCase()
    .split("")
    .map((char) => 127397 + char.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
}

export default Globe;
