import { Location, LocationDossier, RiskScore, SearchResult } from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new ApiError(response.status, `API error: ${response.statusText}`);
    }

    return response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, `Network error: ${error}`);
  }
}

// Locations
export async function getLocations(params?: {
  page?: number;
  pageSize?: number;
  country?: string;
  minRisk?: number;
}): Promise<{ items: Location[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set('page', params.page.toString());
  if (params?.pageSize) searchParams.set('page_size', params.pageSize.toString());
  if (params?.country) searchParams.set('country', params.country);
  if (params?.minRisk) searchParams.set('min_risk', params.minRisk.toString());

  const query = searchParams.toString();
  return fetchApi(`/api/locations${query ? `?${query}` : ''}`);
}

export async function getLocation(id: string): Promise<LocationDossier> {
  return fetchApi(`/api/locations/${id}`);
}

export async function getLocationHistory(
  id: string,
  days: number = 30
): Promise<{
  location_id: string;
  days: number;
  history: Array<{
    date: string;
    risk_score: number | null;
    velocity: number | null;
    variants: string[];
  }>;
}> {
  return fetchApi(`/api/locations/${id}/history?days=${days}`);
}

// Risk
export async function getRiskScore(id: string): Promise<RiskScore> {
  return fetchApi(`/api/risk/${id}`);
}

export async function getRiskForecast(
  id: string,
  days: number = 7
): Promise<{
  location_id: string;
  current_score: number;
  forecast: Array<{
    date: string;
    risk_score: number;
    confidence_low: number;
    confidence_high: number;
  }>;
  trend: 'rising' | 'falling' | 'stable';
}> {
  return fetchApi(`/api/risk/${id}/forecast?days=${days}`);
}

export async function getGlobalSummary(): Promise<{
  total_locations: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  hotspots: Array<{
    location_id: string;
    name: string;
    country: string;
    risk_score: number;
    variants: string[];
  }>;
  last_updated: string;
}> {
  return fetchApi('/api/risk/summary/global');
}

// Search
export async function searchLocations(
  query: string,
  limit: number = 10
): Promise<SearchResult[]> {
  const result = await fetchApi<{ results: SearchResult[] }>(
    `/api/search?q=${encodeURIComponent(query)}&limit=${limit}`
  );
  return result.results;
}

export async function autocomplete(
  query: string,
  limit: number = 5
): Promise<Array<{ id: string; label: string; risk_score?: number }>> {
  return fetchApi(`/api/search/autocomplete?q=${encodeURIComponent(query)}&limit=${limit}`);
}

// Flight arcs
export async function getFlightArcs(params?: {
  date?: string;
  minPassengers?: number;
  originCountry?: string;
  destCountry?: string;
}): Promise<{
  arcs: Array<{
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
  }>;
  total: number;
  date: string;
}> {
  const searchParams = new URLSearchParams();
  if (params?.date) searchParams.set('date', params.date);
  if (params?.minPassengers) searchParams.set('min_pax', params.minPassengers.toString());
  if (params?.originCountry) searchParams.set('origin_country', params.originCountry);
  if (params?.destCountry) searchParams.set('dest_country', params.destCountry);

  const query = searchParams.toString();
  return fetchApi(`/api/flights/arcs${query ? `?${query}` : ''}`);
}

export async function getImportPressure(locationId: string): Promise<{
  location_id: string;
  import_pressure: number;
  top_sources: Array<{
    origin_name: string;
    origin_country: string;
    passengers: number;
    risk_contribution: number;
  }>;
  timestamp: string;
}> {
  return fetchApi(`/api/flights/import-pressure/${locationId}`);
}

// Variant waves and composition
export async function getVariantWaves(params?: {
  locationId?: string;
  days?: number;
}): Promise<{
  waves: Array<{
    variant_id: string;
    display_name: string;
    color: string;
    start_date: string;
    peak_date: string;
    end_date: string | null;
    peak_percentage: number;
    is_active: boolean;
  }>;
  date_range: { start: string; end: string };
  location_id: string | null;
}> {
  const searchParams = new URLSearchParams();
  if (params?.locationId) searchParams.set('location_id', params.locationId);
  if (params?.days) searchParams.set('days', params.days.toString());

  const query = searchParams.toString();
  return fetchApi(`/api/history/variant-waves${query ? `?${query}` : ''}`);
}

export async function getVariantSpreadArcs(
  variantId: string,
  days: number = 30
): Promise<{
  variant_id: string;
  arcs: Array<{
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
  }>;
  date_range: { start: string; end: string };
  total_arcs: number;
}> {
  return fetchApi(`/api/variants/spread-arcs/${variantId}?days=${days}`);
}

export async function getFirstDetections(
  variantId: string,
  days: number = 60
): Promise<{
  variant_id: string;
  markers: Array<{
    location_id: string;
    location_name: string;
    country: string;
    lat: number;
    lon: number;
    variant_id: string;
    detection_date: string;
    detection_type: 'traveler' | 'local';
    confidence: number;
  }>;
  earliest_detection: string;
  total_locations: number;
}> {
  return fetchApi(`/api/variants/first-detections/${variantId}?days=${days}`);
}

export async function getEvidenceChain(
  locationId: string,
  variantId: string,
  days: number = 60
): Promise<{
  location_id: string;
  location_name: string;
  variant_id: string;
  events: Array<{
    event_id: string;
    event_type: string;
    date: string;
    variant_id: string;
    description: string;
    source_location?: string;
    count?: number;
    confidence: number;
    icon: string;
  }>;
  lead_time_days: number | null;
  chain_confidence: number;
  summary: string;
}> {
  return fetchApi(`/api/evidence/chain/${locationId}/${variantId}?days=${days}`);
}

export async function getAllEvidenceChains(
  locationId: string,
  days: number = 60
): Promise<{
  location_id: string;
  location_name: string;
  chains: Array<{
    location_id: string;
    location_name: string;
    variant_id: string;
    events: Array<{
      event_id: string;
      event_type: string;
      date: string;
      variant_id: string;
      description: string;
      confidence: number;
      icon: string;
    }>;
    lead_time_days: number | null;
    chain_confidence: number;
    summary: string;
  }>;
  total_chains: number;
}> {
  return fetchApi(`/api/evidence/chains/${locationId}?days=${days}`);
}

export async function listVariants(): Promise<{
  variants: Array<{
    id: string;
    display_name: string;
    is_active: boolean;
  }>;
}> {
  return fetchApi('/api/variants/list');
}

export async function getVariantComposition(
  locationId: string,
  days: number = 90,
  granularity: 'daily' | 'weekly' = 'weekly'
): Promise<{
  location_id: string;
  series: Array<{
    date: string;
    variants: Record<string, number>;
  }>;
  variants: string[];
  date_range: { start: string; end: string };
}> {
  return fetchApi(
    `/api/history/variant-composition/${locationId}?days=${days}&granularity=${granularity}`
  );
}

// Historical data
export async function getHistoricalData(params: {
  startDate: string;
  endDate: string;
  locationIds?: string[];
  granularity?: 'daily' | 'weekly';
}): Promise<{
  data: Array<{
    location_id: string;
    date: string;
    risk_score: number | null;
    velocity: number | null;
    variants: string[];
  }>;
  locations: number;
  date_range: { start: string; end: string };
}> {
  const searchParams = new URLSearchParams();
  searchParams.set('start_date', params.startDate);
  searchParams.set('end_date', params.endDate);
  if (params.granularity) searchParams.set('granularity', params.granularity);
  if (params.locationIds?.length) {
    params.locationIds.forEach(id => searchParams.append('location_id', id));
  }

  return fetchApi(`/api/history?${searchParams.toString()}`);
}
