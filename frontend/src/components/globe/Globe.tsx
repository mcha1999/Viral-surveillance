'use client';

import { useCallback, useMemo, useState, useEffect } from 'react';
import { Map } from 'react-map-gl';
import DeckGL from '@deck.gl/react';
import { ArcLayer, ScatterplotLayer } from '@deck.gl/layers';
import { useQuery } from '@tanstack/react-query';
import { getLocations, getFlightArcs, getVariantSpreadArcs, getFirstDetections, listVariants } from '@/lib/api';
import { useLocationStore, useUIStore } from '@/lib/store';
import { useGlobeAnimation, getTimeBasedColor, getPulsingWidth } from '@/hooks/useGlobeAnimation';
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
  if (score === null) return [128, 128, 128, 180];
  if (score >= 70) return [239, 68, 68, 220];
  if (score >= 30) return [245, 158, 11, 220];
  return [34, 197, 94, 220];
}

// Color for arcs based on origin risk
function getArcColor(originRisk: number | null): [number, number, number, number] {
  if (originRisk === null) return [100, 100, 100, 100];
  if (originRisk >= 70) return [239, 68, 68, 180];
  if (originRisk >= 30) return [245, 158, 11, 150];
  return [34, 197, 94, 120];
}

// Size scale for risk scores
function getRiskRadius(score: number | null, granularity: string): number {
  const baseSize = granularity === 'tier_1' ? 8000 : granularity === 'tier_2' ? 15000 : 25000;
  if (score === null) return baseSize;
  return baseSize * (0.5 + (score / 100) * 1.5);
}

// Arc data types
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

interface VariantSpreadArc {
  arc_id: string;
  origin_lat: number;
  origin_lon: number;
  origin_name: string;
  origin_country: string;
  dest_lat: number;
  dest_lon: number;
  dest_name: string;
  dest_country: string;
  variant_id: string;
  days_since_origin_detection: number;
  pax_volume: number;
  first_detection_date: string;
  is_active: boolean;
}

interface DetectionMarker {
  location_id: string;
  location_name: string;
  country: string;
  lat: number;
  lon: number;
  variant_id: string;
  detection_date: string;
  detection_type: 'traveler' | 'local';
  confidence: number;
}

interface GlobeProps {
  currentDate: Date;
  showFlightArcs?: boolean;
}

export function Globe({ currentDate, showFlightArcs = true }: GlobeProps) {
  const { setSelectedLocation, historyDays } = useLocationStore();
  const { isPlaying } = useUIStore();
  const [hoveredArc, setHoveredArc] = useState<FlightArc | VariantSpreadArc | null>(null);
  const [showVariantSpread, setShowVariantSpread] = useState(false);
  const [selectedVariant, setSelectedVariant] = useState<string | null>(null);

  // Animation hook
  const { pulseValue, animationFrame } = useGlobeAnimation({ fps: 30 });

  // Fetch locations data
  const { data: locationsData, isLoading: locationsLoading } = useQuery({
    queryKey: ['locations'],
    queryFn: () => getLocations({ pageSize: 1000 }),
    staleTime: 5 * 60 * 1000,
  });

  // Fetch available variants
  const { data: variantsData } = useQuery({
    queryKey: ['variants-list'],
    queryFn: listVariants,
    staleTime: 30 * 60 * 1000,
  });

  // Fetch flight arcs data
  const { data: arcsData, isLoading: arcsLoading } = useQuery({
    queryKey: ['flight-arcs', currentDate.toISOString().split('T')[0]],
    queryFn: () => getFlightArcs({
      date: currentDate.toISOString().split('T')[0],
      minPassengers: 100,
    }),
    staleTime: 30 * 60 * 1000,
    enabled: showFlightArcs && !showVariantSpread,
  });

  // Fetch variant spread arcs
  const { data: spreadData, isLoading: spreadLoading } = useQuery({
    queryKey: ['variant-spread', selectedVariant, historyDays],
    queryFn: () => getVariantSpreadArcs(selectedVariant!, historyDays),
    staleTime: 5 * 60 * 1000,
    enabled: showVariantSpread && !!selectedVariant,
  });

  // Fetch first detection markers
  const { data: detectionsData } = useQuery({
    queryKey: ['first-detections', selectedVariant, historyDays],
    queryFn: () => getFirstDetections(selectedVariant!, historyDays),
    staleTime: 5 * 60 * 1000,
    enabled: showVariantSpread && !!selectedVariant,
  });

  const locations = locationsData?.items || [];
  const arcs = arcsData?.arcs || [];
  const spreadArcs = spreadData?.arcs || [];
  const detectionMarkers = detectionsData?.markers || [];
  const variants = variantsData?.variants || [];

  // Set default variant when list loads
  useEffect(() => {
    if (variants.length > 0 && !selectedVariant) {
      const activeVariant = variants.find(v => v.is_active);
      setSelectedVariant(activeVariant?.id || variants[0].id);
    }
  }, [variants, selectedVariant]);

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

  // Regular flight arcs layer
  const arcLayer = useMemo(() => {
    if (!showFlightArcs || showVariantSpread || arcs.length === 0) return null;

    return new ArcLayer({
      id: 'flight-arcs',
      data: arcs,
      pickable: true,
      getWidth: (d: FlightArc) => Math.max(1, Math.min(8, d.pax_estimate / 500)),
      getSourcePosition: (d: FlightArc) => [d.origin_lon, d.origin_lat],
      getTargetPosition: (d: FlightArc) => [d.dest_lon, d.dest_lat],
      getSourceColor: (d: FlightArc) => getArcColor(d.origin_risk),
      getTargetColor: (d: FlightArc) => {
        const color = getArcColor(d.origin_risk);
        return [color[0], color[1], color[2], Math.floor(color[3] * 0.5)] as [number, number, number, number];
      },
      getHeight: 0.3,
      greatCircle: true,
      onHover: ({ object }: any) => setHoveredArc(object || null),
    });
  }, [arcs, showFlightArcs, showVariantSpread]);

  // Animated variant spread arcs layer
  const spreadArcLayer = useMemo(() => {
    if (!showVariantSpread || spreadArcs.length === 0) return null;

    return new ArcLayer({
      id: 'variant-spread-arcs',
      data: spreadArcs,
      pickable: true,
      getWidth: (d: VariantSpreadArc) => {
        const baseWidth = Math.max(2, Math.min(10, Math.log(d.pax_volume) * 1.5));
        return getPulsingWidth(baseWidth, pulseValue, d.is_active);
      },
      getSourcePosition: (d: VariantSpreadArc) => [d.origin_lon, d.origin_lat],
      getTargetPosition: (d: VariantSpreadArc) => [d.dest_lon, d.dest_lat],
      getSourceColor: (d: VariantSpreadArc) => getTimeBasedColor(d.days_since_origin_detection, 200),
      getTargetColor: (d: VariantSpreadArc) => {
        const color = getTimeBasedColor(d.days_since_origin_detection, 200);
        return [color[0], color[1], color[2], Math.floor(color[3] * 0.4)] as [number, number, number, number];
      },
      getHeight: 0.4,
      greatCircle: true,
      onHover: ({ object }: any) => setHoveredArc(object || null),
      updateTriggers: {
        getWidth: [pulseValue],
      },
    });
  }, [spreadArcs, showVariantSpread, pulseValue]);

  // First detection markers layer
  const detectionMarkerLayer = useMemo(() => {
    if (!showVariantSpread || detectionMarkers.length === 0) return null;

    return new ScatterplotLayer({
      id: 'detection-markers',
      data: detectionMarkers,
      pickable: true,
      opacity: 0.9,
      stroked: true,
      filled: true,
      radiusScale: 1 + pulseValue * 0.3,
      radiusMinPixels: 6,
      radiusMaxPixels: 20,
      lineWidthMinPixels: 2,
      getPosition: (d: DetectionMarker) => [d.lon, d.lat],
      getRadius: (d: DetectionMarker) => d.detection_type === 'traveler' ? 15000 : 12000,
      getFillColor: (d: DetectionMarker) =>
        d.detection_type === 'traveler'
          ? [255, 100, 100, 200] as [number, number, number, number]
          : [100, 200, 255, 200] as [number, number, number, number],
      getLineColor: [255, 255, 255, 200],
      updateTriggers: {
        radiusScale: [pulseValue],
      },
    });
  }, [detectionMarkers, showVariantSpread, pulseValue]);

  const layers = [
    arcLayer,
    spreadArcLayer,
    locationLayer,
    detectionMarkerLayer,
  ].filter(Boolean);

  const isLoading = locationsLoading || (showFlightArcs && arcsLoading) || (showVariantSpread && spreadLoading);

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
            style: { color: '#fff', fontSize: '12px' },
          };
        }

        // Variant spread arc tooltip
        if (layer?.id === 'variant-spread-arcs') {
          const arc = object as VariantSpreadArc;
          return {
            html: `
              <div style="padding: 8px; background: rgba(0,0,0,0.85); border-radius: 4px; max-width: 280px;">
                <div style="font-weight: bold; color: #a855f7; margin-bottom: 4px;">${arc.variant_id} Spread</div>
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                  <span>${arc.origin_name}</span>
                  <span style="color: #666;">→</span>
                  <span>${arc.dest_name}</span>
                </div>
                <div style="font-size: 11px; color: #999; display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
                  <span>Days since origin:</span>
                  <span style="text-align: right; color: ${arc.days_since_origin_detection <= 7 ? '#ef4444' : arc.days_since_origin_detection <= 14 ? '#f59e0b' : '#06b6d4'}">${arc.days_since_origin_detection}d</span>
                  <span>Passengers:</span>
                  <span style="text-align: right;">${arc.pax_volume.toLocaleString()}</span>
                  <span>First detected:</span>
                  <span style="text-align: right;">${arc.first_detection_date}</span>
                </div>
              </div>
            `,
            style: { color: '#fff', fontSize: '12px' },
          };
        }

        // Detection marker tooltip
        if (layer?.id === 'detection-markers') {
          const marker = object as DetectionMarker;
          return {
            html: `
              <div style="padding: 8px; background: rgba(0,0,0,0.85); border-radius: 4px; max-width: 220px;">
                <div style="font-weight: bold; margin-bottom: 4px;">${marker.location_name}</div>
                <div style="font-size: 11px; color: #999;">${marker.country}</div>
                <div style="margin-top: 6px; font-size: 12px;">
                  <div style="color: ${marker.detection_type === 'traveler' ? '#f87171' : '#60a5fa'}">
                    ${marker.detection_type === 'traveler' ? '✈ Traveler Detection' : '🔬 Local Detection'}
                  </div>
                  <div style="margin-top: 4px;">Date: ${marker.detection_date}</div>
                  <div>Confidence: ${(marker.confidence * 100).toFixed(0)}%</div>
                </div>
              </div>
            `,
            style: { color: '#fff', fontSize: '12px' },
          };
        }

        // Regular flight arc tooltip
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
                  <span style="color: #999;">Origin Risk:</span>
                  <span style="text-align: right; color: ${arc.origin_risk && arc.origin_risk >= 70 ? '#ef4444' : arc.origin_risk && arc.origin_risk >= 30 ? '#f59e0b' : '#22c55e'}">
                    ${arc.origin_risk !== null ? arc.origin_risk.toFixed(0) : 'N/A'}
                  </span>
                </div>
              </div>
            `,
            style: { color: '#fff', fontSize: '12px' },
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
            Loading...
          </div>
        </div>
      )}

      {/* Variant spread controls */}
      <div className="absolute top-4 left-4 bg-black/70 backdrop-blur-sm rounded-lg p-3 space-y-3">
        {/* Toggle switch */}
        <div className="flex items-center justify-between gap-4">
          <span className="text-xs text-dark-muted">Variant Spread</span>
          <button
            onClick={() => setShowVariantSpread(!showVariantSpread)}
            className={`relative w-10 h-5 rounded-full transition-colors ${
              showVariantSpread ? 'bg-purple-600' : 'bg-dark-surface'
            }`}
          >
            <div
              className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                showVariantSpread ? 'translate-x-5' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>

        {/* Variant selector */}
        {showVariantSpread && variants.length > 0 && (
          <div className="space-y-2">
            <select
              value={selectedVariant || ''}
              onChange={(e) => setSelectedVariant(e.target.value)}
              className="w-full bg-dark-surface border border-dark-border rounded px-2 py-1 text-xs text-white"
            >
              {variants.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.display_name} {v.is_active ? '(active)' : ''}
                </option>
              ))}
            </select>

            {/* Legend */}
            <div className="text-[10px] space-y-1">
              <div className="flex items-center gap-2">
                <div className="w-3 h-1 rounded bg-red-500" />
                <span className="text-dark-muted">0-7 days</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-1 rounded bg-amber-500" />
                <span className="text-dark-muted">1-2 weeks</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-1 rounded bg-cyan-500" />
                <span className="text-dark-muted">3+ weeks</span>
              </div>
            </div>

            {/* Detection markers legend */}
            <div className="pt-2 border-t border-dark-border text-[10px] space-y-1">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-red-400" />
                <span className="text-dark-muted">Traveler detection</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-blue-400" />
                <span className="text-dark-muted">Local detection</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Arc count indicator */}
      {!showVariantSpread && showFlightArcs && arcs.length > 0 && (
        <div className="absolute bottom-4 left-4 bg-black/60 px-3 py-2 rounded text-xs text-gray-300">
          {arcs.length} flight routes displayed
        </div>
      )}

      {showVariantSpread && spreadArcs.length > 0 && (
        <div className="absolute bottom-4 left-4 bg-black/60 px-3 py-2 rounded text-xs text-gray-300">
          {spreadArcs.length} spread routes • {detectionMarkers.length} detection sites
        </div>
      )}
    </DeckGL>
  );
}
