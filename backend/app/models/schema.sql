-- Viral Weather Database Schema
-- PostgreSQL 15 + PostGIS 3.4

-- =============================================================================
-- Extensions
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For fuzzy text search

-- =============================================================================
-- Enums
-- =============================================================================

CREATE TYPE signal_type AS ENUM ('wastewater', 'genomic', 'flight');
CREATE TYPE granularity_tier AS ENUM ('tier_1', 'tier_2', 'tier_3');

-- =============================================================================
-- Core Tables
-- =============================================================================

-- Location nodes (geographic anchors)
CREATE TABLE location_nodes (
    location_id VARCHAR(50) PRIMARY KEY,
    h3_index VARCHAR(15) NOT NULL,

    -- Hierarchy
    name VARCHAR(255) NOT NULL,
    admin1 VARCHAR(255),  -- State/Province
    country VARCHAR(100) NOT NULL,
    iso_code CHAR(2) NOT NULL,

    -- Metadata
    granularity granularity_tier NOT NULL DEFAULT 'tier_3',
    geometry GEOMETRY(Point, 4326) NOT NULL,
    catchment_population INTEGER,
    timezone VARCHAR(50) DEFAULT 'UTC',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for location_nodes
CREATE INDEX idx_location_h3 ON location_nodes(h3_index);
CREATE INDEX idx_location_geo ON location_nodes USING GIST(geometry);
CREATE INDEX idx_location_country ON location_nodes(iso_code);
CREATE INDEX idx_location_name_trgm ON location_nodes USING GIN(name gin_trgm_ops);

-- Surveillance events (signals from data sources)
CREATE TABLE surveillance_events (
    event_id VARCHAR(50) PRIMARY KEY,
    location_id VARCHAR(50) NOT NULL REFERENCES location_nodes(location_id) ON DELETE CASCADE,

    -- Source info
    timestamp TIMESTAMPTZ NOT NULL,
    data_source VARCHAR(50) NOT NULL,
    signal signal_type NOT NULL,

    -- Wastewater metrics
    raw_load FLOAT,  -- copies/L
    normalized_score FLOAT CHECK (normalized_score IS NULL OR (normalized_score >= 0 AND normalized_score <= 1)),
    velocity FLOAT,  -- week-over-week change

    -- Genomic data
    confirmed_variants TEXT[],
    suspected_variants TEXT[],

    -- Quality
    quality_score FLOAT CHECK (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1)),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicates
    CONSTRAINT unique_event UNIQUE (location_id, timestamp, data_source)
);

-- Indexes for surveillance_events
CREATE INDEX idx_event_location ON surveillance_events(location_id);
CREATE INDEX idx_event_timestamp ON surveillance_events(timestamp DESC);
CREATE INDEX idx_event_source ON surveillance_events(data_source);
CREATE INDEX idx_event_signal ON surveillance_events(signal);
CREATE INDEX idx_event_location_time ON surveillance_events(location_id, timestamp DESC);

-- Vector arcs (flight connections)
CREATE TABLE vector_arcs (
    arc_id VARCHAR(100) PRIMARY KEY,
    origin_location_id VARCHAR(50) NOT NULL REFERENCES location_nodes(location_id),
    dest_location_id VARCHAR(50) NOT NULL REFERENCES location_nodes(location_id),

    -- Time
    date DATE NOT NULL,

    -- Volume
    pax_estimate INTEGER,
    flight_count INTEGER,

    -- Risk
    export_risk_score FLOAT CHECK (export_risk_score IS NULL OR (export_risk_score >= 0 AND export_risk_score <= 1)),
    primary_variant VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicates
    CONSTRAINT unique_arc UNIQUE (origin_location_id, dest_location_id, date)
);

-- Indexes for vector_arcs
CREATE INDEX idx_arc_origin ON vector_arcs(origin_location_id);
CREATE INDEX idx_arc_dest ON vector_arcs(dest_location_id);
CREATE INDEX idx_arc_date ON vector_arcs(date DESC);
CREATE INDEX idx_arc_origin_date ON vector_arcs(origin_location_id, date DESC);

-- Variants catalog
CREATE TABLE variants (
    variant_id VARCHAR(50) PRIMARY KEY,  -- Pango lineage (e.g., BA.2.86)

    -- Metadata
    display_name VARCHAR(100),  -- Marketing name if any
    parent_lineage VARCHAR(50),
    first_detected_date DATE,
    first_detected_location VARCHAR(50) REFERENCES location_nodes(location_id),

    -- Characteristics (0-10 scale)
    transmissibility SMALLINT CHECK (transmissibility IS NULL OR (transmissibility >= 0 AND transmissibility <= 10)),
    immune_evasion SMALLINT CHECK (immune_evasion IS NULL OR (immune_evasion >= 0 AND immune_evasion <= 10)),
    severity SMALLINT CHECK (severity IS NULL OR (severity >= 0 AND severity <= 10)),

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    who_designation VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Data sources registry
CREATE TABLE data_sources (
    source_id VARCHAR(50) PRIMARY KEY,

    -- Metadata
    name VARCHAR(100) NOT NULL,
    source_type signal_type NOT NULL,
    country VARCHAR(100),

    -- Reliability
    reliability_score FLOAT CHECK (reliability_score >= 0 AND reliability_score <= 1) DEFAULT 0.8,
    typical_lag_days INTEGER DEFAULT 3,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_successful_sync TIMESTAMPTZ,
    last_error TEXT,

    -- Config (JSON for flexibility)
    config JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- Materialized Views
-- =============================================================================

-- Current risk scores (refreshed hourly)
CREATE MATERIALIZED VIEW risk_scores AS
SELECT
    ln.location_id,
    ln.name,
    ln.country,
    ln.iso_code,
    ln.geometry,
    ln.granularity,

    -- Calculate risk score (0-100)
    LEAST(100, GREATEST(0,
        COALESCE(AVG(se.normalized_score) * 100, 0)
    ))::NUMERIC(5,1) as risk_score,

    -- Metadata
    MAX(se.timestamp) as last_updated,
    COUNT(se.event_id) as event_count,

    -- Variants
    (SELECT array_agg(DISTINCT v)
     FROM surveillance_events se2, unnest(se2.confirmed_variants) v
     WHERE se2.location_id = ln.location_id
       AND se2.timestamp > NOW() - INTERVAL '14 days'
    ) as variants,

    -- Velocity (average week-over-week change)
    AVG(se.velocity) as avg_velocity

FROM location_nodes ln
LEFT JOIN surveillance_events se ON ln.location_id = se.location_id
    AND se.timestamp > NOW() - INTERVAL '14 days'
GROUP BY ln.location_id, ln.name, ln.country, ln.iso_code, ln.geometry, ln.granularity;

CREATE UNIQUE INDEX idx_risk_location ON risk_scores(location_id);
CREATE INDEX idx_risk_score ON risk_scores(risk_score DESC);
CREATE INDEX idx_risk_geo ON risk_scores USING GIST(geometry);

-- =============================================================================
-- Functions
-- =============================================================================

-- Function to refresh risk scores
CREATE OR REPLACE FUNCTION refresh_risk_scores()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY risk_scores;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate location risk score
CREATE OR REPLACE FUNCTION calculate_risk_score(
    p_location_id VARCHAR(50),
    p_lookback_days INTEGER DEFAULT 14
)
RETURNS NUMERIC AS $$
DECLARE
    v_wastewater_score NUMERIC;
    v_velocity NUMERIC;
    v_import_pressure NUMERIC;
    v_final_score NUMERIC;
BEGIN
    -- Wastewater component (40%)
    SELECT AVG(normalized_score) INTO v_wastewater_score
    FROM surveillance_events
    WHERE location_id = p_location_id
      AND signal = 'wastewater'
      AND timestamp > NOW() - (p_lookback_days || ' days')::INTERVAL;

    -- Velocity component (30%)
    SELECT AVG(velocity) INTO v_velocity
    FROM surveillance_events
    WHERE location_id = p_location_id
      AND signal = 'wastewater'
      AND timestamp > NOW() - (p_lookback_days || ' days')::INTERVAL;

    -- Import pressure component (30%)
    SELECT AVG(export_risk_score) INTO v_import_pressure
    FROM vector_arcs
    WHERE dest_location_id = p_location_id
      AND date > CURRENT_DATE - p_lookback_days;

    -- Combine (normalize velocity to 0-1 range)
    v_final_score := (
        COALESCE(v_wastewater_score, 0) * 0.4 +
        LEAST(1, GREATEST(0, COALESCE(v_velocity, 0) + 0.5)) * 0.3 +
        COALESCE(v_import_pressure, 0) * 0.3
    ) * 100;

    RETURN LEAST(100, GREATEST(0, v_final_score));
END;
$$ LANGUAGE plpgsql;

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Triggers
-- =============================================================================

CREATE TRIGGER trg_location_updated
    BEFORE UPDATE ON location_nodes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_variant_updated
    BEFORE UPDATE ON variants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_source_updated
    BEFORE UPDATE ON data_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- Seed Data - Data Sources
-- =============================================================================

INSERT INTO data_sources (source_id, name, source_type, country, reliability_score, typical_lag_days)
VALUES
    ('CDC_NWSS', 'CDC National Wastewater Surveillance System', 'wastewater', 'USA', 0.95, 3),
    ('UKHSA', 'UK Health Security Agency', 'wastewater', 'United Kingdom', 0.90, 4),
    ('RIVM', 'Netherlands RIVM', 'wastewater', 'Netherlands', 0.90, 5),
    ('RKI', 'Robert Koch Institute', 'wastewater', 'Germany', 0.85, 7),
    ('NEXTSTRAIN', 'Nextstrain Genomic Surveillance', 'genomic', NULL, 0.95, 1),
    ('AVIATIONSTACK', 'AviationStack Flight Data', 'flight', NULL, 0.80, 0)
ON CONFLICT (source_id) DO NOTHING;

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON TABLE location_nodes IS 'Geographic anchors for surveillance data (cities, regions, countries)';
COMMENT ON TABLE surveillance_events IS 'Time-series signals from wastewater, genomic, and flight sources';
COMMENT ON TABLE vector_arcs IS 'Flight connections between locations with passenger estimates';
COMMENT ON TABLE variants IS 'Catalog of tracked viral variants with characteristics';
COMMENT ON TABLE data_sources IS 'Registry of data sources with reliability and status tracking';
COMMENT ON MATERIALIZED VIEW risk_scores IS 'Pre-computed risk scores per location, refresh hourly';
