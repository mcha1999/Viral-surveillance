import { test, expect } from '@playwright/test';

const API_BASE = process.env.API_URL || 'http://localhost:8000';

test.describe('API Integration Tests', () => {
  test.describe('Health Endpoints', () => {
    test('API root should be accessible', async ({ request }) => {
      const response = await request.get(`${API_BASE}/`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data.name).toBe('Viral Weather API');
      expect(data.status).toBe('operational');
    });

    test('Health endpoint should return status', async ({ request }) => {
      const response = await request.get(`${API_BASE}/health`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data.status).toMatch(/healthy|degraded|unhealthy/);
    });
  });

  test.describe('Locations API', () => {
    test('should return list of locations', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/locations`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('items');
      expect(data).toHaveProperty('total');
      expect(Array.isArray(data.items)).toBeTruthy();
    });

    test('should support pagination', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/locations?page=1&page_size=5`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data.items.length).toBeLessThanOrEqual(5);
    });

    test('should filter by country', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/locations?country=US`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      for (const loc of data.items) {
        expect(loc.iso_code === 'US' || loc.country === 'United States').toBeTruthy();
      }
    });

    test('should return location by ID', async ({ request }) => {
      // First get a list to find a valid ID
      const listResponse = await request.get(`${API_BASE}/api/locations?page_size=1`);
      const listData = await listResponse.json();

      if (listData.items.length > 0) {
        const locId = listData.items[0].location_id;
        const response = await request.get(`${API_BASE}/api/locations/${locId}`);
        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data.location_id).toBe(locId);
      }
    });

    test('should return 404 for non-existent location', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/locations/loc_nonexistent_123`);
      expect(response.status()).toBe(404);
    });
  });

  test.describe('Risk API', () => {
    test('should return risk score for location', async ({ request }) => {
      const listResponse = await request.get(`${API_BASE}/api/locations?page_size=1`);
      const listData = await listResponse.json();

      if (listData.items.length > 0) {
        const locId = listData.items[0].location_id;
        const response = await request.get(`${API_BASE}/api/risk/${locId}`);
        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data).toHaveProperty('risk_score');
        expect(data.risk_score).toBeGreaterThanOrEqual(0);
        expect(data.risk_score).toBeLessThanOrEqual(100);
      }
    });

    test('should return global summary', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/risk/summary/global`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('total_locations');
      expect(data).toHaveProperty('high_risk_count');
      expect(data).toHaveProperty('hotspots');
    });

    test('should return forecast', async ({ request }) => {
      const listResponse = await request.get(`${API_BASE}/api/locations?page_size=1`);
      const listData = await listResponse.json();

      if (listData.items.length > 0) {
        const locId = listData.items[0].location_id;
        const response = await request.get(`${API_BASE}/api/risk/${locId}/forecast?days=7`);
        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data).toHaveProperty('forecast');
        expect(Array.isArray(data.forecast)).toBeTruthy();
      }
    });
  });

  test.describe('Search API', () => {
    test('should search locations by query', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/search?q=new%20york`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('results');
      expect(Array.isArray(data.results)).toBeTruthy();
    });

    test('should return autocomplete suggestions', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/search/autocomplete?q=lon&limit=5`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(Array.isArray(data)).toBeTruthy();
      expect(data.length).toBeLessThanOrEqual(5);
    });
  });

  test.describe('Flights API', () => {
    test('should return flight arcs', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/flights/arcs`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('arcs');
      expect(data).toHaveProperty('total');
      expect(data).toHaveProperty('date');
    });

    test('should filter arcs by date', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/flights/arcs?date=2026-01-10`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data.date).toBe('2026-01-10');
    });

    test('should filter arcs by minimum passengers', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/flights/arcs?min_pax=500`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      for (const arc of data.arcs) {
        expect(arc.pax_estimate).toBeGreaterThanOrEqual(500);
      }
    });

    test('should reject invalid date format', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/flights/arcs?date=invalid`);
      expect(response.status()).toBe(400);
    });

    test('should return import pressure', async ({ request }) => {
      const response = await request.get(`${API_BASE}/api/flights/import-pressure/loc_us_new_york`);
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('import_pressure');
      expect(data.import_pressure).toBeGreaterThanOrEqual(0);
      expect(data.import_pressure).toBeLessThanOrEqual(100);
    });
  });

  test.describe('History API', () => {
    test('should return historical data', async ({ request }) => {
      const response = await request.get(
        `${API_BASE}/api/history?start_date=2026-01-01&end_date=2026-01-10`
      );
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('data');
      expect(data).toHaveProperty('date_range');
    });

    test('should reject invalid date range', async ({ request }) => {
      const response = await request.get(
        `${API_BASE}/api/history?start_date=2026-01-10&end_date=2026-01-01`
      );
      expect(response.status()).toBe(400);
    });

    test('should reject date range over 365 days', async ({ request }) => {
      const response = await request.get(
        `${API_BASE}/api/history?start_date=2024-01-01&end_date=2026-01-10`
      );
      expect(response.status()).toBe(400);
    });

    test('should return time series data', async ({ request }) => {
      const response = await request.get(
        `${API_BASE}/api/history/timeseries/loc_us_new_york?days=30`
      );
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('series');
      expect(data).toHaveProperty('metric');
    });

    test('should compare locations', async ({ request }) => {
      const response = await request.get(
        `${API_BASE}/api/history/compare?location_ids=loc_us_new_york&location_ids=loc_gb_london&days=7`
      );
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('locations');
    });
  });
});

test.describe('API Error Handling', () => {
  test('should return 404 for unknown endpoints', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/unknown/endpoint`);
    expect(response.status()).toBe(404);
  });

  test('should return proper error format', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/locations/nonexistent`);
    expect(response.status()).toBe(404);

    const data = await response.json();
    expect(data).toHaveProperty('detail');
  });
});
