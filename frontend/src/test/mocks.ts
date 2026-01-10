import { vi } from 'vitest';
import type { Location, LocationDossier, RiskScore, SearchResult } from '@/types';

// Sample location data for tests
export const mockLocation: Location = {
  location_id: 'loc_us_new_york',
  name: 'New York',
  country: 'United States',
  iso_code: 'US',
  granularity: 'tier_1',
  coordinates: { lat: 40.7128, lon: -74.006 },
  risk_score: 45.5,
  last_updated: '2026-01-10T12:00:00Z',
  variants: ['JN.1', 'BA.2.86'],
};

export const mockLocations: Location[] = [
  mockLocation,
  {
    location_id: 'loc_gb_london',
    name: 'London',
    country: 'United Kingdom',
    iso_code: 'GB',
    granularity: 'tier_1',
    coordinates: { lat: 51.5074, lon: -0.1278 },
    risk_score: 55.2,
    last_updated: '2026-01-10T12:00:00Z',
    variants: ['JN.1'],
  },
  {
    location_id: 'loc_jp_tokyo',
    name: 'Tokyo',
    country: 'Japan',
    iso_code: 'JP',
    granularity: 'tier_1',
    coordinates: { lat: 35.6762, lon: 139.6503 },
    risk_score: 32.8,
    last_updated: '2026-01-10T12:00:00Z',
    variants: ['XBB.1.5'],
  },
];

export const mockLocationDossier: LocationDossier = {
  ...mockLocation,
  risk_trend: 'rising',
  dominant_variant: 'JN.1',
  weekly_change: 12.5,
  catchment_population: 8500000,
  incoming_threats: [
    {
      origin_name: 'London',
      origin_country: 'United Kingdom',
      flight_count: 15,
      pax_estimate: 3500,
      source_risk_score: 55.2,
      primary_variant: 'JN.1',
    },
  ],
  data_quality: 'excellent',
};

export const mockRiskScore: RiskScore = {
  location_id: 'loc_us_new_york',
  risk_score: 45.5,
  components: {
    wastewater_load: 40.0,
    growth_velocity: 15.0,
    import_pressure: 35.0,
  },
  confidence: 0.85,
  last_updated: '2026-01-10T12:00:00Z',
};

export const mockSearchResults: SearchResult[] = [
  {
    location_id: 'loc_us_new_york',
    name: 'New York',
    country: 'United States',
    iso_code: 'US',
    granularity: 'tier_1',
    match_score: 0.95,
  },
  {
    location_id: 'loc_us_new_orleans',
    name: 'New Orleans',
    country: 'United States',
    iso_code: 'US',
    granularity: 'tier_2',
    match_score: 0.75,
  },
];

export const mockFlightArcs = {
  arcs: [
    {
      arc_id: 'arc_123',
      origin_lat: 40.6413,
      origin_lon: -73.7781,
      origin_name: 'New York',
      origin_country: 'US',
      dest_lat: 51.47,
      dest_lon: -0.4543,
      dest_name: 'London',
      dest_country: 'GB',
      pax_estimate: 1500,
      flight_count: 8,
      origin_risk: 45.0,
    },
  ],
  total: 1,
  date: '2026-01-10',
};

export const mockHistoricalData = {
  data: [
    { location_id: 'loc_us_new_york', date: '2026-01-01', risk_score: 40.0, velocity: 0.05, variants: ['JN.1'] },
    { location_id: 'loc_us_new_york', date: '2026-01-02', risk_score: 42.0, velocity: 0.08, variants: ['JN.1'] },
    { location_id: 'loc_us_new_york', date: '2026-01-03', risk_score: 45.0, velocity: 0.10, variants: ['JN.1'] },
  ],
  locations: 1,
  date_range: { start: '2026-01-01', end: '2026-01-03' },
};

// Mock API functions
export const mockApi = {
  getLocations: vi.fn().mockResolvedValue({ items: mockLocations, total: 3 }),
  getLocation: vi.fn().mockResolvedValue(mockLocationDossier),
  getLocationHistory: vi.fn().mockResolvedValue({
    location_id: 'loc_us_new_york',
    days: 7,
    history: mockHistoricalData.data,
  }),
  getRiskScore: vi.fn().mockResolvedValue(mockRiskScore),
  getRiskForecast: vi.fn().mockResolvedValue({
    location_id: 'loc_us_new_york',
    current_score: 45.5,
    forecast: [
      { date: '2026-01-11', risk_score: 47.0, confidence_low: 42.0, confidence_high: 52.0 },
      { date: '2026-01-12', risk_score: 48.5, confidence_low: 43.0, confidence_high: 54.0 },
    ],
    trend: 'rising',
  }),
  getGlobalSummary: vi.fn().mockResolvedValue({
    total_locations: 150,
    high_risk_count: 12,
    medium_risk_count: 45,
    low_risk_count: 93,
    hotspots: [mockLocation],
    last_updated: '2026-01-10T12:00:00Z',
  }),
  searchLocations: vi.fn().mockResolvedValue(mockSearchResults),
  autocomplete: vi.fn().mockResolvedValue([
    { id: 'loc_us_new_york', label: 'New York, United States' },
  ]),
  getFlightArcs: vi.fn().mockResolvedValue(mockFlightArcs),
  getImportPressure: vi.fn().mockResolvedValue({
    location_id: 'loc_us_new_york',
    import_pressure: 35.0,
    top_sources: [],
    timestamp: '2026-01-10T12:00:00Z',
  }),
  getHistoricalData: vi.fn().mockResolvedValue(mockHistoricalData),
};

// Create mock fetch responses
export function createMockFetchResponse(data: any, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  });
}
