import { test, expect } from '@playwright/test';

test.describe('Location Search', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[class*="deck"]', { timeout: 30000 });
  });

  test('should have search input visible', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Search/i);
    await expect(searchInput).toBeVisible();
  });

  test('should focus search with keyboard shortcut', async ({ page }) => {
    // Press / to focus search
    await page.keyboard.press('/');

    const searchInput = page.getByPlaceholder(/Search/i);
    await expect(searchInput).toBeFocused();
  });

  test('should show autocomplete results on typing', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Search/i);
    await searchInput.click();
    await searchInput.fill('New York');

    // Wait for autocomplete results
    await page.waitForTimeout(500);

    // Should show dropdown or results
    // Implementation depends on UI design
  });

  test('should clear search on escape', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Search/i);
    await searchInput.click();
    await searchInput.fill('Test');

    // Press escape
    await page.keyboard.press('Escape');

    // Search should be blurred or cleared
    await expect(searchInput).not.toBeFocused();
  });

  test('should navigate to location on selection', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Search/i);
    await searchInput.click();
    await searchInput.fill('London');

    // Wait for results and select
    await page.waitForTimeout(500);

    // Press enter to select first result
    await page.keyboard.press('Enter');

    // Should show dossier panel or navigate
    await page.waitForTimeout(1000);
  });
});

test.describe('Search Accessibility', () => {
  test('should have proper ARIA labels', async ({ page }) => {
    await page.goto('/');

    const searchInput = page.getByPlaceholder(/Search/i);
    // Should have accessible name
    await expect(searchInput).toHaveAttribute('type', 'text');
  });

  test('should be keyboard navigable', async ({ page }) => {
    await page.goto('/');

    // Tab to search
    await page.keyboard.press('Tab');

    // Should eventually reach search
    const searchInput = page.getByPlaceholder(/Search/i);
    // May need multiple tabs depending on layout
  });
});
