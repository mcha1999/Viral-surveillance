export type RiskLevel = "low" | "moderate" | "elevated" | "high" | "very-high";

export type FreshnessStatus = "current" | "stale" | "old" | "expired";

export interface Location {
  id: string;
  name: string;
  country: string;
  countryCode: string;
  coordinates: [number, number]; // [longitude, latitude]
  population?: number;
  riskScore: number;
  weeklyChange: number;
  lastUpdated: Date;
  variants: Variant[];
  wastewaterData?: WastewaterDataPoint[];
}

export interface Variant {
  id: string;
  name: string;
  prevalence: number;
  severity: "low" | "moderate" | "high";
  transmissibility: "low" | "moderate" | "high";
  mutations?: string[];
}

export interface WastewaterDataPoint {
  date: Date;
  value: number;
  normalized: number;
}

export interface FlightArc {
  id: string;
  origin: Location;
  destination: Location;
  dailyPassengers: number;
  riskContribution: number;
}

export interface WatchlistItem {
  locationId: string;
  addedAt: Date;
  alertThreshold: number;
}

export interface UserPreferences {
  homeLocation?: Location;
  watchlist: WatchlistItem[];
  onboardingComplete: boolean;
  tooltipsShown: string[];
}

export interface ViewState {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch: number;
  bearing: number;
  transitionDuration?: number;
}

export interface GlobalStats {
  totalLocations: number;
  hotZones: number;
  averageRiskScore: number;
  trend: "rising" | "falling" | "stable";
  lastUpdated: Date;
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  meta: {
    timestamp: string;
    requestId: string;
  };
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    hasMore: boolean;
  };
}

export interface SearchResult {
  id: string;
  name: string;
  country: string;
  type: "city" | "state" | "country";
  coordinates: [number, number];
  riskScore?: number;
}
