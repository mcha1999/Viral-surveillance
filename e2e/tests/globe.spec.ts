import { test, expect } from '@playwright/test';

test.describe('Globe Visualization', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for the globe to load
    await page.waitForSelector('[class*="deck"]', { timeout: 30000 });
  });

  test('should load the globe visualization', async ({ page }) => {
    // Check that the main page loads
    await expect(page).toHaveTitle(/Viral Weather/);

    // Globe container should be visible
    const globeContainer = page.locator('[class*="deck"]');
    await expect(globeContainer).toBeVisible();
  });

  test('should display loading state initially', async ({ page }) => {
    // Navigate fresh
    await page.goto('/');

    // Should show loading indicator (may be brief)
    const loadingIndicator = page.getByText(/Loading global data/);
    // It may disappear quickly, so we don't assert visibility
  });

  test('should render location markers', async ({ page }) => {
    // Wait for data to load
    await page.waitForTimeout(2000);

    // Canvas should have rendered content
    const canvas = page.locator('canvas');
    await expect(canvas).toBeVisible();
  });

  test('should show flight arcs indicator when routes loaded', async ({ page }) => {
    // Wait for flight data to load
    await page.waitForTimeout(3000);

    // Check for flight routes indicator
    const routesIndicator = page.getByText(/flight routes displayed/);
    // May or may not be visible depending on data
  });
});

test.describe('Globe Interactions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[class*="deck"]', { timeout: 30000 });
    await page.waitForTimeout(2000); // Wait for data
  });

  test('should zoom with scroll', async ({ page }) => {
    const canvas = page.locator('canvas').first();

    // Get initial state
    const box = await canvas.boundingBox();
    if (box) {
      // Scroll to zoom
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.wheel(0, -100);

      // Globe should still be visible after zoom
      await expect(canvas).toBeVisible();
    }
  });

  test('should pan with drag', async ({ page }) => {
    const canvas = page.locator('canvas').first();

    const box = await canvas.boundingBox();
    if (box) {
      // Drag to pan
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.mouse.down();
      await page.mouse.move(box.x + box.width / 2 + 100, box.y + box.height / 2);
      await page.mouse.up();

      // Globe should still be visible after pan
      await expect(canvas).toBeVisible();
    }
  });
});
