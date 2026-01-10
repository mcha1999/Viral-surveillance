// Location types
export interface Coordinates {
  lat: number;
  lon: number;
}

export interface Location {
  location_id: string;
  name: string;
  country: string;
  iso_code: string;
  granularity: 'tier_1' | 'tier_2' | 'tier_3';
  coordinates: Coordinates;
  risk_score: number | null;
  last_updated: string | null;
  variants: string[];
}

export interface IncomingThreat {
  origin_name: string;
  origin_country: string;
  flight_count: number;
  pax_estimate: number;
  source_risk_score: number;
  primary_variant: string | null;
}

export interface LocationDossier extends Location {
  risk_trend: 'rising' | 'falling' | 'stable';
  dominant_variant: string | null;
  weekly_change: number | null;
  catchment_population: number | null;
  incoming_threats: IncomingThreat[];
  data_quality: 'excellent' | 'good' | 'limited';
}

// Risk types
export interface RiskScore {
  location_id: string;
  risk_score: number;
  components: {
    wastewater_load: number;
    growth_velocity: number;
    import_pressure: number;
  };
  confidence: number;
  last_updated: string | null;
}

export interface RiskForecastPoint {
  date: string;
  risk_score: number;
  confidence_low: number;
  confidence_high: number;
}

// Search types
export interface SearchResult {
  location_id: string;
  name: string;
  country: string;
  iso_code: string;
  granularity: string;
  match_score: number;
}

// Variant types
export interface Variant {
  variant_id: string;
  display_name: string | null;
  parent_lineage: string | null;
  first_detected_date: string | null;
  transmissibility: number | null;
  immune_evasion: number | null;
  severity: number | null;
  is_active: boolean;
}

// Arc types (for flight visualization)
export interface VectorArc {
  arc_id: string;
  origin: Coordinates;
  destination: Coordinates;
  origin_name: string;
  dest_name: string;
  pax_estimate: number;
  flight_count: number;
  risk_score: number;
  primary_variant: string | null;
}
