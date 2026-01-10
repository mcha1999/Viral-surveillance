'use client';

import { useCallback, useMemo, useState } from 'react';
import { Map } from 'react-map-gl';
import DeckGL from '@deck.gl/react';
import { ArcLayer, ScatterplotLayer } from '@deck.gl/layers';
import { useQuery } from '@tanstack/react-query';
import { getLocations, getFlightArcs } from '@/lib/api';
import { useLocationStore } from '@/lib/store';
import type { Location } from '@/types';

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

// Initial view state - global view
const INITIAL_VIEW_STATE = {
  longitude: 0,
  latitude: 20,
  zoom: 1.5,
  pitch: 0,
  bearing: 0,
};

// Color scale for risk scores
function getRiskColor(score: number | null): [number, number, number, number] {
  if (score === null) return [128, 128, 128, 180]; // Gray for no data

  if (score >= 70) return [239, 68, 68, 220];   // Red - high
  if (score >= 30) return [245, 158, 11, 220];  // Amber - medium
  return [34, 197, 94, 220];                     // Green - low
}

// Color for arcs based on origin risk
function getArcColor(originRisk: number | null): [number, number, number, number] {
  if (originRisk === null) return [100, 100, 100, 100]; // Gray for unknown

  if (originRisk >= 70) return [239, 68, 68, 180];   // Red - high risk origin
  if (originRisk >= 30) return [245, 158, 11, 150];  // Amber - medium risk
  return [34, 197, 94, 120];                          // Green - low risk
}

// Size scale for risk scores
function getRiskRadius(score: number | null, granularity: string): number {
  const baseSize = granularity === 'tier_1' ? 8000 : granularity === 'tier_2' ? 15000 : 25000;

  if (score === null) return baseSize;
  return baseSize * (0.5 + (score / 100) * 1.5);
}

// Arc data type from API
interface FlightArc {
  arc_id: string;
  origin_lat: number;
  origin_lon: number;
  origin_name: string;
  origin_country: string;
  dest_lat: number;
  dest_lon: number;
  dest_name: string;
  dest_country: string;
  pax_estimate: number;
  flight_count: number;
  origin_risk: number | null;
}

interface GlobeProps {
  currentDate: Date;
  showFlightArcs?: boolean;
}

export function Globe({ currentDate, showFlightArcs = true }: GlobeProps) {
  const { setSelectedLocation } = useLocationStore();
  const [hoveredArc, setHoveredArc] = useState<FlightArc | null>(null);

  // Fetch locations data
  const { data: locationsData, isLoading: locationsLoading } = useQuery({
    queryKey: ['locations'],
    queryFn: () => getLocations({ pageSize: 1000 }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch flight arcs data
  const { data: arcsData, isLoading: arcsLoading } = useQuery({
    queryKey: ['flight-arcs', currentDate.toISOString().split('T')[0]],
    queryFn: () => getFlightArcs({
      date: currentDate.toISOString().split('T')[0],
      minPassengers: 100, // Only show significant routes
    }),
    staleTime: 30 * 60 * 1000, // 30 minutes
    enabled: showFlightArcs,
  });

  const locations = locationsData?.items || [];
  const arcs = arcsData?.arcs || [];

  // Handle location click
  const onClick = useCallback((info: any) => {
    if (info.object && info.layer?.id === 'locations') {
      setSelectedLocation(info.object.location_id);
    }
  }, [setSelectedLocation]);

  // Location markers layer
  const locationLayer = useMemo(() => {
    return new ScatterplotLayer({
      id: 'locations',
      data: locations,
      pickable: true,
      opacity: 0.8,
      stroked: true,
      filled: true,
      radiusScale: 1,
      radiusMinPixels: 4,
      radiusMaxPixels: 30,
      lineWidthMinPixels: 1,
      getPosition: (d: Location) => [d.coordinates.lon, d.coordinates.lat],
      getRadius: (d: Location) => getRiskRadius(d.risk_score, d.granularity),
      getFillColor: (d: Location) => getRiskColor(d.risk_score),
      getLineColor: [255, 255, 255, 100],
      onClick,
    });
  }, [locations, onClick]);

  // Flight arcs layer
  const arcLayer = useMemo(() => {
    if (!showFlightArcs || arcs.length === 0) return null;

    return new ArcLayer({
      id: 'flight-arcs',
      data: arcs,
      pickable: true,
      getWidth: (d: FlightArc) => Math.max(1, Math.min(8, d.pax_estimate / 500)),
      getSourcePosition: (d: FlightArc) => [d.origin_lon, d.origin_lat],
      getTargetPosition: (d: FlightArc) => [d.dest_lon, d.dest_lat],
      getSourceColor: (d: FlightArc) => getArcColor(d.origin_risk),
      getTargetColor: (d: FlightArc) => {
        // Fade to lighter at destination
        const color = getArcColor(d.origin_risk);
        return [color[0], color[1], color[2], Math.floor(color[3] * 0.5)] as [number, number, number, number];
      },
      getHeight: 0.3, // Arc height as proportion of distance
      greatCircle: true, // Use great circle paths
      onHover: ({ object }: any) => setHoveredArc(object || null),
    });
  }, [arcs, showFlightArcs]);

  const layers = [
    arcLayer,      // Arcs below locations
    locationLayer, // Locations on top
  ].filter(Boolean);

  const isLoading = locationsLoading || (showFlightArcs && arcsLoading);

  return (
    <DeckGL
      initialViewState={INITIAL_VIEW_STATE}
      controller={true}
      layers={layers}
      getTooltip={({ object, layer }: any) => {
        if (!object) return null;

        // Location tooltip
        if (layer?.id === 'locations') {
          const loc = object as Location;
          return {
            html: `
              <div style="padding: 8px; background: rgba(0,0,0,0.85); border-radius: 4px; max-width: 200px;">
                <strong style="font-size: 14px;">${loc.name}</strong><br/>
                <span style="color: #999;">${loc.country}</span><br/>
                <div style="margin-top: 4px; display: flex; justify-content: space-between;">
                  <span>Risk Score:</span>
                  <strong style="color: ${loc.risk_score && loc.risk_score >= 70 ? '#ef4444' : loc.risk_score && loc.risk_score >= 30 ? '#f59e0b' : '#22c55e'}">
                    ${loc.risk_score !== null ? loc.risk_score.toFixed(0) : 'N/A'}
                  </strong>
                </div>
              </div>
            `,
            style: {
              color: '#fff',
              fontSize: '12px',
            },
          };
        }

        // Arc tooltip
        if (layer?.id === 'flight-arcs') {
          const arc = object as FlightArc;
          return {
            html: `
              <div style="padding: 8px; background: rgba(0,0,0,0.85); border-radius: 4px; max-width: 250px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                  <span style="color: #999;">✈</span>
                  <strong>${arc.origin_name}</strong>
                  <span style="color: #666;">→</span>
                  <strong>${arc.dest_name}</strong>
                </div>
                <div style="font-size: 11px; color: #999; margin-bottom: 6px;">
                  ${arc.origin_country} → ${arc.dest_country}
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 12px;">
                  <span style="color: #999;">Passengers:</span>
                  <span style="text-align: right;">${arc.pax_estimate.toLocaleString()}</span>
                  <span style="color: #999;">Flights:</span>
                  <span style="text-align: right;">${arc.flight_count}</span>
                  <span style="color: #999;">Origin Risk:</span>
                  <span style="text-align: right; color: ${arc.origin_risk && arc.origin_risk >= 70 ? '#ef4444' : arc.origin_risk && arc.origin_risk >= 30 ? '#f59e0b' : '#22c55e'}">
                    ${arc.origin_risk !== null ? arc.origin_risk.toFixed(0) : 'N/A'}
                  </span>
                </div>
              </div>
            `,
            style: {
              color: '#fff',
              fontSize: '12px',
            },
          };
        }

        return null;
      }}
    >
      <Map
        mapboxAccessToken={MAPBOX_TOKEN}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        projection={{ name: 'globe' }}
        fog={{
          range: [0.5, 10],
          color: '#0a0a0a',
          'horizon-blend': 0.1,
        }}
      />

      {/* Loading indicator */}
      {isLoading && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
          <div className="text-white text-lg flex items-center gap-2">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading global data...
          </div>
        </div>
      )}

      {/* Arc count indicator */}
      {showFlightArcs && arcs.length > 0 && (
        <div className="absolute bottom-4 left-4 bg-black/60 px-3 py-2 rounded text-xs text-gray-300">
          {arcs.length} flight routes displayed
        </div>
      )}
    </DeckGL>
  );
}
