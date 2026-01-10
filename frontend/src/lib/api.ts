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
): Promise<Array<{ id: string; label: string }>> {
  return fetchApi(`/api/search/autocomplete?q=${encodeURIComponent(query)}&limit=${limit}`);
}
