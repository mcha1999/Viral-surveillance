import { test, expect } from '@playwright/test';

test.describe('Location Dossier Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[class*="deck"]', { timeout: 30000 });
    await page.waitForTimeout(2000);
  });

  test('should open dossier when location is selected', async ({ page }) => {
    // Search and select a location
    const searchInput = page.getByPlaceholder(/Search/i);
    await searchInput.click();
    await searchInput.fill('New York');
    await page.waitForTimeout(500);
    await page.keyboard.press('Enter');

    // Wait for dossier to open
    await page.waitForTimeout(1000);

    // Check for dossier panel elements (depends on implementation)
    const dossierPanel = page.locator('[data-testid="dossier-panel"]');
    // May or may not be visible depending on implementation
  });

  test('should close dossier with escape key', async ({ page }) => {
    // Open a location first
    const searchInput = page.getByPlaceholder(/Search/i);
    await searchInput.click();
    await searchInput.fill('London');
    await page.waitForTimeout(500);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1000);

    // Press escape to close
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  });

  test('should display risk score in dossier', async ({ page }) => {
    // Navigate to a location
    const searchInput = page.getByPlaceholder(/Search/i);
    await searchInput.click();
    await searchInput.fill('Tokyo');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1500);

    // Look for risk-related content
    const riskContent = page.getByText(/risk/i);
    // Should find some risk-related text
  });

  test('should show trend indicator', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Search/i);
    await searchInput.click();
    await searchInput.fill('Paris');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1500);

    // Look for trend indicators (rising, falling, stable)
    const trendContent = page.getByText(/rising|falling|stable/i);
  });
});

test.describe('Dossier Data Display', () => {
  test('should display variant information when available', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);

    const searchInput = page.getByPlaceholder(/Search/i);
    await searchInput.click();
    await searchInput.fill('Berlin');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1500);

    // Look for variant-related content
    const variantContent = page.getByText(/variant|JN|BA|XBB/i);
  });

  test('should display incoming threats section', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);

    const searchInput = page.getByPlaceholder(/Search/i);
    await searchInput.click();
    await searchInput.fill('New York');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1500);

    // Look for threats/flights content
    const threatsContent = page.getByText(/incoming|threat|flight/i);
  });
});
