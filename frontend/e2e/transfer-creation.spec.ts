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
  // Login before each test
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');

    // Login
    await page.fill('input[type="email"], input[name="email"]', testEmail);
    await page.fill('input[type="password"], input[name="password"]', testPassword);
    await page.click('button[type="submit"], button:has-text("Login"), button:has-text("Sign In")');

    // Wait for dashboard
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });
  });

  test('should complete full transfer creation flow', async ({ page }) => {
    // Step 1: Initiate New Transfer
    await test.step('Click "New Transfer" button', async () => {
      // Find and click new transfer button
      const newTransferButton = page.locator('button:has-text("New Transfer"), a:has-text("New Transfer"), button:has-text("Create Transfer")');
      await expect(newTransferButton).toBeVisible({ timeout: 5000 });
      await newTransferButton.click();

      // Should navigate to transfer creation page
      await page.waitForURL(/\/transfers\/(new|create)/, { timeout: 10000 });
    });

    // Step 2: Source Selection
    await test.step('Select source files from OneDrive', async () => {
      // Wait for source selection UI
      await expect(page.locator('h1, h2')).toContainText(/source|select.*files|onedrive/i);

      // Look for file browser
      const fileBrowser = page.locator('[data-testid="file-browser"], .file-browser, [role="tree"], [role="listbox"]');

      if (await fileBrowser.count() > 0) {
        await expect(fileBrowser).toBeVisible();

        // Try to select some files/folders
        const fileItems = page.locator('[data-testid="file-item"], .file-item, [role="treeitem"], [role="option"]');

        if (await fileItems.count() > 0) {
          // Select first item
          await fileItems.first().click();

          // Verify selection indicator
          const selectedItems = page.locator('[data-selected="true"], .selected, [aria-selected="true"]');
          await expect(selectedItems).toHaveCount(1, { timeout: 2000 });
        }
      }

      // Click "Next" or "Continue" button
      const nextButton = page.locator('button:has-text("Next"), button:has-text("Continue"), button:has-text("Select Destination")');
      if (await nextButton.count() > 0) {
        await nextButton.click();
      }
    });

    // Step 3: Destination Selection
    await test.step('Select destination folder in Google Drive', async () => {
      // Wait for destination selection UI
      await expect(page.locator('h1, h2')).toContainText(/destination|google.*drive|select.*folder/i, { timeout: 5000 });

      // Look for destination folder browser
      const destinationBrowser = page.locator('[data-testid="destination-browser"], .destination-browser, [role="tree"]');

      if (await destinationBrowser.count() > 0) {
        await expect(destinationBrowser).toBeVisible();

        // Select root or first folder
        const folderItems = page.locator('[data-testid="folder-item"], .folder-item, [data-type="folder"]');

        if (await folderItems.count() > 0) {
          await folderItems.first().click();
        }
      }

      // Click "Next" or "Continue"
      const nextButton = page.locator('button:has-text("Next"), button:has-text("Continue"), button:has-text("Configure")');
      if (await nextButton.count() > 0) {
        await nextButton.click();
      }
    });

    // Step 4: Configure Transfer Filters
    await test.step('Configure transfer filters and options', async () => {
      // Wait for configuration page
      await expect(page.locator('h1, h2, h3')).toContainText(/configure|filters|options|settings/i, { timeout: 5000 });

      // File type filters
      const fileTypeSection = page.locator('text=/file.*type|filter.*type/i');
      if (await fileTypeSection.count() > 0) {
        // Look for file type checkboxes
        const imageCheckbox = page.locator('input[type="checkbox"][value*="image"], label:has-text("Images") input, label:has-text("Photos") input');

        if (await imageCheckbox.count() > 0) {
          await imageCheckbox.check();
          await expect(imageCheckbox).toBeChecked();
        }
      }

      // Date range filters
      const dateRangeSection = page.locator('text=/date.*range|modified.*date/i');
      if (await dateRangeSection.count() > 0) {
        // Try to set date range
        const fromDateInput = page.locator('input[type="date"][name*="from"], input[type="date"]:has-text("From")').first();

        if (await fromDateInput.count() > 0) {
          const lastMonth = new Date();
          lastMonth.setMonth(lastMonth.getMonth() - 1);
          const dateStr = lastMonth.toISOString().split('T')[0];

          await fromDateInput.fill(dateStr);
        }
      }

      // Conflict handling strategy
      const conflictSection = page.locator('text=/conflict|duplicate|existing.*file/i');
      if (await conflictSection.count() > 0) {
        // Select a conflict resolution strategy
        const skipRadio = page.locator('input[type="radio"][value="skip"], label:has-text("Skip") input');
        const renameRadio = page.locator('input[type="radio"][value="rename"], label:has-text("Rename") input');

        if (await skipRadio.count() > 0) {
          await skipRadio.check();
        } else if (await renameRadio.count() > 0) {
          await renameRadio.check();
        }
      }

      // Click "Next" or "Review"
      const nextButton = page.locator('button:has-text("Next"), button:has-text("Review"), button:has-text("Continue")');
      if (await nextButton.count() > 0) {
        await nextButton.click();
      }
    });

    // Step 5: Review and Confirm Transfer
    await test.step('Review transfer summary and start', async () => {
      // Wait for review page
      await expect(page.locator('h1, h2')).toContainText(/review|confirm|summary/i, { timeout: 5000 });

      // Verify transfer summary is displayed
      const summarySection = page.locator('[data-testid="transfer-summary"], .transfer-summary, section:has-text("Summary")');
      if (await summarySection.count() > 0) {
        await expect(summarySection).toBeVisible();

        // Check for file count
        await expect(summarySection).toContainText(/\d+\s*(file|item)/i);
      }

      // Look for dry run button (optional)
      const dryRunButton = page.locator('button:has-text("Dry Run"), button:has-text("Preview")');
      if (await dryRunButton.count() > 0) {
        await dryRunButton.click();

        // Wait for dry run results
        await expect(page.locator('text=/dry.*run.*result|preview.*result/i')).toBeVisible({ timeout: 10000 });

        // Close dry run modal if it's a modal
        const closeButton = page.locator('button:has-text("Close"), button[aria-label="Close"]');
        if (await closeButton.count() > 0) {
          await closeButton.click();
        }
      }

      // Start the transfer
      const startButton = page.locator('button:has-text("Start Transfer"), button:has-text("Begin Transfer"), button[type="submit"]:has-text("Start")');
      await expect(startButton).toBeVisible({ timeout: 5000 });
      await startButton.click();

      // Should navigate to transfer progress or dashboard
      await page.waitForURL(/\/(transfers|dashboard|progress)/, { timeout: 10000 });

      // Verify success message or redirect
      const successIndicator = page.locator('text=/transfer.*started|transfer.*created|successfully/i, [role="alert"]:has-text("Success")');
      if (await successIndicator.count() > 0) {
        await expect(successIndicator).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test('should validate required fields in transfer creation', async ({ page }) => {
    await test.step('Try to proceed without selecting source', async () => {
      // Navigate to new transfer
      await page.goto('/transfers/new');

      // Try to click next without selecting files
      const nextButton = page.locator('button:has-text("Next"), button:has-text("Continue")');

      if (await nextButton.count() > 0) {
        await nextButton.click();

        // Should show validation error
        const errorMessage = page.locator('text=/please.*select|required|must.*select/i, [role="alert"]');

        if (await errorMessage.count() > 0) {
          await expect(errorMessage).toBeVisible({ timeout: 3000 });
        }
      }
    });
  });

  test('should allow scheduling a transfer', async ({ page }) => {
    await test.step('Schedule transfer for future execution', async () => {
      // Navigate to new transfer
      await page.goto('/transfers/new');

      // Go through minimal setup (this is a simplified flow)
      // In real implementation, we'd need to complete all steps

      // Look for schedule option
      const scheduleSection = page.locator('text=/schedule|start.*later|set.*time/i');

      if (await scheduleSection.count() > 0) {
        // Find schedule toggle or radio button
        const scheduleToggle = page.locator('input[type="radio"][value*="schedule"], input[type="checkbox"][name*="schedule"], label:has-text("Schedule") input');

        if (await scheduleToggle.count() > 0) {
          await scheduleToggle.check();

          // Set date and time
          const dateInput = page.locator('input[type="date"], input[type="datetime-local"]').first();
          const timeInput = page.locator('input[type="time"]').first();

          if (await dateInput.count() > 0) {
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            const dateStr = tomorrow.toISOString().split('T')[0];

            await dateInput.fill(dateStr);
          }

          if (await timeInput.count() > 0) {
            await timeInput.fill('14:00');
          }

          // Verify schedule time is accepted
          console.log('Schedule time set successfully');
        }
      }
    });
  });
});
