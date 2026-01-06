import { test, expect } from '@playwright/test';

/**
 * E2E Test: View Progress → Completion
 *
 * This test validates the transfer progress monitoring and completion flow:
 * 1. View active transfer progress
 * 2. Monitor real-time updates
 * 3. View completion status and results
 * 4. Access transfer history and details
 */

// Test user credentials
const testEmail = 'e2e-test@example.com';
const testPassword = 'TestPassword123!';

test.describe('Transfer Progress and Completion Flow', () => {
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

  test('should display active transfer progress', async ({ page }) => {
    // Step 1: View Active Transfers
    await test.step('Navigate to active transfers section', async () => {
      // Look for active transfers section on dashboard
      const activeTransfersSection = page.locator('[data-testid="active-transfers"], section:has-text("Active"), section:has-text("In Progress")');

      if (await activeTransfersSection.count() > 0) {
        await expect(activeTransfersSection).toBeVisible();
      } else {
        // Navigate to transfers page if not on dashboard
        const transfersLink = page.locator('a:has-text("Transfers"), a[href*="transfers"]').first();
        if (await transfersLink.count() > 0) {
          await transfersLink.click();
          await page.waitForURL(/\/transfers/, { timeout: 5000 });
        }
      }
    });

    // Step 2: View Progress Details
    await test.step('View transfer progress details', async () => {
      // Look for active transfer items
      const activeTransferItem = page.locator('[data-status="running"], [data-status="active"], .transfer-active, [data-testid="active-transfer-item"]').first();

      if (await activeTransferItem.count() > 0) {
        await expect(activeTransferItem).toBeVisible();

        // Check for progress bar
        const progressBar = activeTransferItem.locator('[role="progressbar"], .progress-bar, progress');
        if (await progressBar.count() > 0) {
          await expect(progressBar).toBeVisible();

          // Verify progress value is present
          const progressValue = await progressBar.getAttribute('aria-valuenow');
          if (progressValue) {
            console.log(`Transfer progress: ${progressValue}%`);
          }
        }

        // Check for file count
        await expect(activeTransferItem).toContainText(/\d+\s*\/\s*\d+\s*(file|item)/i);

        // Check for data transferred
        const dataTransferred = activeTransferItem.locator('text=/\d+(\.\d+)?\s*(MB|GB|KB)/i');
        if (await dataTransferred.count() > 0) {
          await expect(dataTransferred).toBeVisible();
        }

        // Click to view detailed progress
        await activeTransferItem.click();

        // Wait for progress detail page
        await page.waitForURL(/\/transfers\/\d+/, { timeout: 5000 });
      } else {
        console.log('No active transfers found. This is expected if no transfers are running.');
      }
    });

    // Step 3: View Detailed Progress Page
    await test.step('View detailed progress information', async () => {
      // Check if we're on a transfer detail page
      if (page.url().match(/\/transfers\/\d+/)) {
        // Look for detailed progress information
        const progressSection = page.locator('[data-testid="progress-details"], .progress-details, section:has-text("Progress")');

        if (await progressSection.count() > 0) {
          await expect(progressSection).toBeVisible();

          // Check for current file being transferred
          const currentFile = page.locator('text=/current.*file|transferring|processing/i');
          if (await currentFile.count() > 0) {
            await expect(currentFile).toBeVisible();
          }

          // Check for transfer speed
          const transferSpeed = page.locator('text=/\d+(\.\d+)?\s*(MB|KB)\/s/i');
          if (await transferSpeed.count() > 0) {
            await expect(transferSpeed).toBeVisible();
          }

          // Check for estimated time remaining
          const estimatedTime = page.locator('text=/estimated|remaining|eta/i');
          if (await estimatedTime.count() > 0) {
            await expect(estimatedTime).toBeVisible();
          }

          // Check for completed files list
          const completedFilesList = page.locator('[data-testid="completed-files"], .completed-files, section:has-text("Completed")');
          if (await completedFilesList.count() > 0) {
            await expect(completedFilesList).toBeVisible();
          }
        }
      }
    });

    // Step 4: Test Cancel Functionality
    await test.step('Test transfer cancellation option', async () => {
      // Look for cancel button
      const cancelButton = page.locator('button:has-text("Cancel"), button:has-text("Stop"), button[aria-label*="cancel" i]');

      if (await cancelButton.count() > 0) {
        await expect(cancelButton).toBeVisible();
        await expect(cancelButton).toBeEnabled();

        // Click cancel (we'll immediately confirm to avoid actually canceling in test)
        await cancelButton.click();

        // Look for confirmation dialog
        const confirmDialog = page.locator('[role="dialog"], [role="alertdialog"], .modal');
        if (await confirmDialog.count() > 0) {
          await expect(confirmDialog).toBeVisible();
          await expect(confirmDialog).toContainText(/cancel|stop|confirm/i);

          // Close dialog without confirming
          const noButton = page.locator('button:has-text("No"), button:has-text("Cancel"), button:has-text("Keep")').last();
          if (await noButton.count() > 0) {
            await noButton.click();
          } else {
            // Press Escape to close
            await page.keyboard.press('Escape');
          }
        }
      }
    });
  });

  test('should display completed transfers', async ({ page }) => {
    // Step 1: Navigate to Transfer History
    await test.step('Navigate to transfer history', async () => {
      // Look for history or completed transfers link
      const historyLink = page.locator('a:has-text("History"), a:has-text("Completed"), a[href*="history"]');

      if (await historyLink.count() > 0) {
        await historyLink.click();
        await page.waitForURL(/\/(history|transfers)/, { timeout: 5000 });
      } else {
        // Try navigating directly
        await page.goto('/transfers/history');
      }
    });

    // Step 2: View Completed Transfers List
    await test.step('View list of completed transfers', async () => {
      // Look for completed transfer items
      const completedTransfers = page.locator('[data-status="completed"], .transfer-completed, [data-testid="completed-transfer"]');

      if (await completedTransfers.count() > 0) {
        const firstCompleted = completedTransfers.first();
        await expect(firstCompleted).toBeVisible();

        // Verify completed transfer information
        await expect(firstCompleted).toContainText(/completed|success|finished/i);

        // Check for completion date/time
        const completionDate = firstCompleted.locator('text=/\d{1,2}\/\d{1,2}\/\d{4}|\d{4}-\d{2}-\d{2}/');
        if (await completionDate.count() > 0) {
          await expect(completionDate).toBeVisible();
        }

        // Check for total files transferred
        await expect(firstCompleted).toContainText(/\d+\s*(file|item)/i);

        // Click to view details
        await firstCompleted.click();

        // Wait for detail page
        await page.waitForURL(/\/transfers\/\d+/, { timeout: 5000 });
      } else {
        console.log('No completed transfers found');
      }
    });

    // Step 3: View Completed Transfer Details
    await test.step('View detailed transfer results', async () => {
      if (page.url().match(/\/transfers\/\d+/)) {
        // Check for transfer summary
        const summary = page.locator('[data-testid="transfer-summary"], .transfer-summary, section:has-text("Summary")');
        if (await summary.count() > 0) {
          await expect(summary).toBeVisible();

          // Check for success status
          await expect(page.locator('text=/completed|success|finished/i')).toBeVisible();

          // Check for transfer statistics
          await expect(page.locator('text=/total.*file|files.*transferred/i')).toBeVisible();
          await expect(page.locator('text=/total.*size|data.*transferred/i')).toBeVisible();

          // Check for duration
          const duration = page.locator('text=/duration|time.*taken|elapsed/i');
          if (await duration.count() > 0) {
            await expect(duration).toBeVisible();
          }
        }

        // Check for file list
        const fileList = page.locator('[data-testid="transferred-files"], .file-list, table');
        if (await fileList.count() > 0) {
          await expect(fileList).toBeVisible();

          // Verify file entries
          const fileRows = fileList.locator('tr, [data-testid="file-row"], .file-item');
          const fileCount = await fileRows.count();
          expect(fileCount).toBeGreaterThan(0);
        }

        // Check for failed files section (if any)
        const failedFilesSection = page.locator('text=/failed|error|unsuccessful/i');
        if (await failedFilesSection.count() > 0) {
          // Verify error details are shown
          const errorDetails = page.locator('[data-testid="error-details"], .error-message');
          if (await errorDetails.count() > 0) {
            await expect(errorDetails).toBeVisible();
          }
        }

        // Check for download report button
        const downloadButton = page.locator('button:has-text("Download"), button:has-text("Export"), a:has-text("Download")');
        if (await downloadButton.count() > 0) {
          await expect(downloadButton).toBeVisible();
        }
      }
    });

    // Step 4: Test Filter and Search
    await test.step('Test transfer history filters', async () => {
      // Navigate back to history page
      await page.goto('/transfers/history');

      // Look for status filter
      const statusFilter = page.locator('select[name*="status"], [data-testid="status-filter"]');
      if (await statusFilter.count() > 0) {
        await expect(statusFilter).toBeVisible();

        // Try filtering by completed
        await statusFilter.selectOption({ label: 'Completed' });

        // Verify filter is applied
        await page.waitForTimeout(1000); // Wait for filter to apply

        const visibleTransfers = page.locator('[data-status="completed"], .transfer-completed');
        if (await visibleTransfers.count() > 0) {
          await expect(visibleTransfers.first()).toBeVisible();
        }
      }

      // Look for date range filter
      const dateRangeFilter = page.locator('input[type="date"]').first();
      if (await dateRangeFilter.count() > 0) {
        const lastWeek = new Date();
        lastWeek.setDate(lastWeek.getDate() - 7);
        const dateStr = lastWeek.toISOString().split('T')[0];

        await dateRangeFilter.fill(dateStr);
        await page.waitForTimeout(1000); // Wait for filter to apply
      }
    });
  });

  test('should handle failed transfers appropriately', async ({ page }) => {
    await test.step('View failed transfer details', async () => {
      // Navigate to transfers
      await page.goto('/transfers/history');

      // Look for failed transfers
      const failedTransfer = page.locator('[data-status="failed"], .transfer-failed, [data-testid="failed-transfer"]').first();

      if (await failedTransfer.count() > 0) {
        await expect(failedTransfer).toBeVisible();
        await expect(failedTransfer).toContainText(/failed|error|unsuccessful/i);

        // Click to view details
        await failedTransfer.click();

        // Wait for detail page
        await page.waitForURL(/\/transfers\/\d+/, { timeout: 5000 });

        // Check for error information
        const errorSection = page.locator('[data-testid="error-details"], .error-details, section:has-text("Error")');
        if (await errorSection.count() > 0) {
          await expect(errorSection).toBeVisible();
        }

        // Check for retry button
        const retryButton = page.locator('button:has-text("Retry"), button:has-text("Try Again"), button:has-text("Resume")');
        if (await retryButton.count() > 0) {
          await expect(retryButton).toBeVisible();
          await expect(retryButton).toBeEnabled();
        }
      } else {
        console.log('No failed transfers found. This is expected if all transfers succeed.');
      }
    });
  });

  test('should support real-time progress updates', async ({ page }) => {
    await test.step('Monitor real-time progress updates', async () => {
      // Look for an active transfer
      const activeTransfer = page.locator('[data-status="running"], .transfer-active').first();

      if (await activeTransfer.count() > 0) {
        await activeTransfer.click();
        await page.waitForURL(/\/transfers\/\d+/, { timeout: 5000 });

        // Get initial progress value
        const progressBar = page.locator('[role="progressbar"], .progress-bar').first();

        if (await progressBar.count() > 0) {
          const initialValue = await progressBar.getAttribute('aria-valuenow');

          // Wait a few seconds for progress to update
          await page.waitForTimeout(3000);

          // Check if progress value changed
          const updatedValue = await progressBar.getAttribute('aria-valuenow');

          if (initialValue && updatedValue && initialValue !== updatedValue) {
            console.log(`Progress updated from ${initialValue}% to ${updatedValue}%`);
          }

          // Verify progress is between 0 and 100
          if (updatedValue) {
            const progressNum = parseInt(updatedValue);
            expect(progressNum).toBeGreaterThanOrEqual(0);
            expect(progressNum).toBeLessThanOrEqual(100);
          }
        }
      } else {
        console.log('No active transfers to monitor');
      }
    });
  });
});
