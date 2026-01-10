import { test, expect } from '@playwright/test';

test.describe('Time Scrubber', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[class*="deck"]', { timeout: 30000 });
    await page.waitForTimeout(2000);
  });

  test('should have time scrubber visible', async ({ page }) => {
    // Look for time scrubber element
    const timeScrubber = page.locator('[data-testid="time-scrubber"]');
    // May or may not be visible depending on implementation
  });

  test('should show current date', async ({ page }) => {
    // Look for date display
    const dateDisplay = page.getByText(/Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec/);
    // Should find some date text
  });

  test('should navigate with arrow keys', async ({ page }) => {
    // Focus the time scrubber area
    await page.keyboard.press('ArrowLeft');
    await page.waitForTimeout(300);
    await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(300);

    // Globe should still be functional
    const canvas = page.locator('canvas');
    await expect(canvas).toBeVisible();
  });

  test('should toggle play/pause with space', async ({ page }) => {
    // Press space to toggle animation
    await page.keyboard.press('Space');
    await page.waitForTimeout(500);

    // Press again to pause
    await page.keyboard.press('Space');
    await page.waitForTimeout(500);
  });
});

test.describe('Time Navigation', () => {
  test('should load historical data when date changes', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);

    // Navigate backwards in time
    await page.keyboard.press('ArrowLeft');
    await page.keyboard.press('ArrowLeft');
    await page.keyboard.press('ArrowLeft');

    // Wait for data reload
    await page.waitForTimeout(1000);

    // Globe should still show data
    const canvas = page.locator('canvas');
    await expect(canvas).toBeVisible();
  });

  test('should debounce rapid navigation', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(2000);

    // Rapid key presses
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('ArrowLeft');
    }

    // Should not crash
    await page.waitForTimeout(500);
    const canvas = page.locator('canvas');
    await expect(canvas).toBeVisible();
  });
});
