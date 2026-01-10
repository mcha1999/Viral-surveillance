import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  getLocations,
  getLocation,
  getRiskScore,
  searchLocations,
  getFlightArcs,
  getHistoricalData,
} from './api';
import { mockLocations, mockLocationDossier, mockRiskScore, mockFlightArcs, mockHistoricalData } from '@/test/mocks';

describe('API Client', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getLocations', () => {
    it('should fetch locations successfully', async () => {
      const mockResponse = { items: mockLocations, total: 3 };
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await getLocations();

      expect(result.items).toHaveLength(3);
      expect(result.total).toBe(3);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/locations'),
        expect.any(Object)
      );
    });

    it('should pass pagination parameters', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ items: [], total: 0 }),
      });

      await getLocations({ page: 2, pageSize: 10 });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('page=2'),
        expect.any(Object)
      );
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('page_size=10'),
        expect.any(Object)
      );
    });

    it('should pass country filter', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ items: [], total: 0 }),
      });

      await getLocations({ country: 'US' });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('country=US'),
        expect.any(Object)
      );
    });

    it('should throw ApiError on failure', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      await expect(getLocations()).rejects.toThrow('API error');
    });
  });

  describe('getLocation', () => {
    it('should fetch location details', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockLocationDossier),
      });

      const result = await getLocation('loc_us_new_york');

      expect(result.location_id).toBe('loc_us_new_york');
      expect(result.incoming_threats).toBeDefined();
    });

    it('should handle 404 for non-existent location', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      });

      await expect(getLocation('loc_nonexistent')).rejects.toThrow();
    });
  });

  describe('getRiskScore', () => {
    it('should fetch risk score with components', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockRiskScore),
      });

      const result = await getRiskScore('loc_us_new_york');

      expect(result.risk_score).toBe(45.5);
      expect(result.components).toBeDefined();
      expect(result.components.wastewater_load).toBeDefined();
    });
  });

  describe('searchLocations', () => {
    it('should search locations by query', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({
          results: [
            { location_id: 'loc_us_new_york', name: 'New York', match_score: 0.95 },
          ],
        }),
      });

      const results = await searchLocations('new york');

      expect(results).toHaveLength(1);
      expect(results[0].name).toBe('New York');
    });

    it('should encode query parameter', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ results: [] }),
      });

      await searchLocations('new york');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('new%20york'),
        expect.any(Object)
      );
    });
  });

  describe('getFlightArcs', () => {
    it('should fetch flight arcs', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockFlightArcs),
      });

      const result = await getFlightArcs();

      expect(result.arcs).toBeDefined();
      expect(result.total).toBe(1);
    });

    it('should pass date filter', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockFlightArcs),
      });

      await getFlightArcs({ date: '2026-01-10' });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('date=2026-01-10'),
        expect.any(Object)
      );
    });

    it('should pass minimum passengers filter', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockFlightArcs),
      });

      await getFlightArcs({ minPassengers: 500 });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('min_pax=500'),
        expect.any(Object)
      );
    });
  });

  describe('getHistoricalData', () => {
    it('should fetch historical data with date range', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockHistoricalData),
      });

      const result = await getHistoricalData({
        startDate: '2026-01-01',
        endDate: '2026-01-10',
      });

      expect(result.data).toBeDefined();
      expect(result.date_range).toBeDefined();
    });

    it('should pass granularity option', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockHistoricalData),
      });

      await getHistoricalData({
        startDate: '2026-01-01',
        endDate: '2026-01-31',
        granularity: 'weekly',
      });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('granularity=weekly'),
        expect.any(Object)
      );
    });
  });

  describe('Error handling', () => {
    it('should handle network errors', async () => {
      global.fetch = vi.fn().mockRejectedValueOnce(new Error('Network error'));

      await expect(getLocations()).rejects.toThrow('Network error');
    });

    it('should include status code in error', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
      });

      try {
        await getLocations();
      } catch (error: any) {
        expect(error.status).toBe(503);
      }
    });
  });
});
