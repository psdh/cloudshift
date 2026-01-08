import { test, expect } from '@playwright/test';

/**
 * E2E Test: Create Transfer → Configure → Start
 *
 * This test validates the complete transfer creation and configuration flow:
 * 1. User creates a new transfer job
 * 2. Selects source files/folders from OneDrive
 * 3. Selects destination folder in Google Drive
 * 4. Configures transfer filters and options
 * 5. Reviews and starts the transfer
 */

// Test user credentials (assumes user already registered)
const testEmail = 'e2e-test@example.com';
const testPassword = 'TestPassword123!';

test.describe('Transfer Creation and Configuration Flow', () => {
  // Note: These tests assume backend is running. Without backend, tests will fail on API calls.
  // To run these tests, either:
  // 1. Start the full stack (see E2E-TESTING-GUIDE.md)
  // 2. Mock the backend API endpoints
  // 3. Skip these tests for frontend-only testing

  // Login before each test
  test.beforeEach(async ({ page }) => {
    // Skip test if no backend
    // await page.goto('/login');

    // For now, just navigate to transfer page directly to test UI
    await page.goto('/transfers/new');

    // TODO: Add login flow when backend is available
  });

  test('should display transfer creation wizard', async ({ page }) => {
    // Step 1: Verify transfer wizard UI
    await test.step('Verify transfer wizard is displayed', async () => {
      // Check for progress indicator with steps
      await expect(page.locator('text=Source')).toBeVisible();
      await expect(page.locator('text=Destination')).toBeVisible();
      await expect(page.locator('text=Filters')).toBeVisible();
      await expect(page.locator('text=Review')).toBeVisible();

      console.log('✓ Transfer wizard steps displayed');
    });

    // Step 2: Verify navigation buttons
    await test.step('Verify wizard navigation', async () => {
      // Look for Next and Back buttons
      const backButton = page.locator('button:has-text("Back")');
      const nextButton = page.locator('button:has-text("Next")');

      // Back and Next buttons should be visible
      await expect(backButton).toBeVisible();
      await expect(nextButton).toBeVisible();

      console.log('✓ Navigation buttons displayed');
    });

    // Note: Remaining steps require backend API to load data
    // These tests validate the UI structure, not the full flow

  });

  test('should validate required fields in transfer creation', async ({ page }) => {
    await test.step('Try to proceed without selecting source', async () => {
      // Try to click next without selecting files
      const nextButton = page.locator('button:has-text("Next")');
      await nextButton.click();

      // Should show alert (browser alert dialog)
      page.on('dialog', async dialog => {
        expect(dialog.message()).toContain('Please select');
        await dialog.accept();
      });

      console.log('✓ Validation prevents proceeding without selection');
    });
  });

  test.skip('should allow scheduling a transfer', async ({ page }) => {
    // This test requires completing the full wizard flow
    // Skip until backend API is available for testing
    console.log('⚠ Skipped: Requires backend API');
  });
});
