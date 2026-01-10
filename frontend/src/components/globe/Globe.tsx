'use client';

import { useCallback, useMemo } from 'react';
import { Map } from 'react-map-gl';
import DeckGL from '@deck.gl/react';
import { GeoJsonLayer, ArcLayer, ScatterplotLayer } from '@deck.gl/layers';
import { useQuery } from '@tanstack/react-query';
import { getLocations } from '@/lib/api';
import { useLocationStore } from '@/lib/store';
import type { Location, VectorArc } from '@/types';

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

// Size scale for risk scores
function getRiskRadius(score: number | null, granularity: string): number {
  const baseSize = granularity === 'tier_1' ? 8000 : granularity === 'tier_2' ? 15000 : 25000;

  if (score === null) return baseSize;
  return baseSize * (0.5 + (score / 100) * 1.5);
}

interface GlobeProps {
  currentDate: Date;
}

export function Globe({ currentDate }: GlobeProps) {
  const { setSelectedLocation } = useLocationStore();

  // Fetch locations data
  const { data: locationsData, isLoading } = useQuery({
    queryKey: ['locations'],
    queryFn: () => getLocations({ pageSize: 1000 }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const locations = locationsData?.items || [];

  // Handle location click
  const onClick = useCallback((info: any) => {
    if (info.object) {
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

  // TODO: Add ArcLayer for flight connections
  // const arcLayer = useMemo(() => { ... }, [arcs]);

  const layers = [locationLayer];

  return (
    <DeckGL
      initialViewState={INITIAL_VIEW_STATE}
      controller={true}
      layers={layers}
      getTooltip={({ object }: any) => {
        if (!object) return null;
        const loc = object as Location;
        return {
          html: `
            <div style="padding: 8px; background: rgba(0,0,0,0.8); border-radius: 4px;">
              <strong>${loc.name}</strong><br/>
              ${loc.country}<br/>
              Risk: ${loc.risk_score !== null ? loc.risk_score.toFixed(0) : 'N/A'}
            </div>
          `,
          style: {
            color: '#fff',
            fontSize: '12px',
          },
        };
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
          <div className="text-white text-lg">Loading global data...</div>
        </div>
      )}
    </DeckGL>
  );
}
