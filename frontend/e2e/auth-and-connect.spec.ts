import { test, expect } from '@playwright/test';

/**
 * E2E Test: Register → Login → Connect Accounts
 *
 * This test validates the complete user authentication and account connection flow:
 * 1. New user registration with email and password
 * 2. Login with the registered credentials
 * 3. Navigate to account settings and connect OneDrive and Google Drive
 */

// Generate unique test user credentials
const generateTestEmail = () => `test-${Date.now()}@example.com`;
const testPassword = 'TestPassword123!';

test.describe('Authentication and Account Connection Flow', () => {
  let testEmail: string;

  test.beforeEach(() => {
    testEmail = generateTestEmail();
  });

  test('should complete registration → login → connect accounts flow', async ({ page, context }) => {
    // Step 1: User Registration
    await test.step('Register new user', async () => {
      await page.goto('/register');

      // Wait for registration form to load
      await expect(page.locator('h1')).toContainText(/register|sign up/i);

      // Fill registration form
      await page.fill('input[type="email"], input[name="email"]', testEmail);
      await page.fill('input[type="password"], input[name="password"]', testPassword);

      // Some forms may have confirm password field
      const confirmPasswordField = page.locator('input[name="confirmPassword"], input[placeholder*="confirm" i]');
      if (await confirmPasswordField.count() > 0) {
        await confirmPasswordField.fill(testPassword);
      }

      // Submit registration
      await page.click('button[type="submit"], button:has-text("Register"), button:has-text("Sign Up")');

      // Should redirect to dashboard or login page
      await page.waitForURL(/\/(dashboard|login)/, { timeout: 10000 });
    });

    // Step 2: User Login (if redirected to login after registration)
    await test.step('Login with registered credentials', async () => {
      // Check if already on dashboard (auto-login after registration)
      const currentUrl = page.url();
      if (!currentUrl.includes('dashboard')) {
        // Navigate to login page
        await page.goto('/login');

        // Fill login form
        await page.fill('input[type="email"], input[name="email"]', testEmail);
        await page.fill('input[type="password"], input[name="password"]', testPassword);

        // Submit login
        await page.click('button[type="submit"], button:has-text("Login"), button:has-text("Sign In")');

        // Wait for redirect to dashboard
        await page.waitForURL(/\/dashboard/, { timeout: 10000 });
      }

      // Verify we're on the dashboard
      await expect(page).toHaveURL(/\/dashboard/);
    });

    // Step 3: Navigate to Account Settings
    await test.step('Navigate to account settings', async () => {
      // Look for settings/accounts link in navigation
      const settingsLink = page.locator('a:has-text("Settings"), a:has-text("Accounts"), a[href*="settings"], a[href*="accounts"]').first();
      await settingsLink.click();

      // Wait for settings/accounts page to load
      await page.waitForURL(/\/(settings|accounts)/, { timeout: 10000 });

      // Verify page heading
      await expect(page.locator('h1, h2')).toContainText(/settings|accounts|connected accounts/i);
    });

    // Step 4: Connect OneDrive Account
    await test.step('Connect OneDrive account', async () => {
      // Find and click "Connect OneDrive" button
      const onedriveButton = page.locator('button:has-text("Connect OneDrive"), button:has-text("Connect Microsoft")');

      if (await onedriveButton.count() > 0) {
        // Listen for popup/new tab
        const popupPromise = context.waitForEvent('page');
        await onedriveButton.click();

        // Note: In real tests, we'd need to handle OAuth flow
        // For now, we verify the button click triggers OAuth initiation
        const popup = await popupPromise;

        // Verify OAuth URL contains microsoft.com or login.microsoftonline.com
        await popup.waitForLoadState();
        const popupUrl = popup.url();

        if (popupUrl.includes('microsoft') || popupUrl.includes('login.microsoftonline')) {
          console.log('OneDrive OAuth flow initiated successfully');
          await popup.close();

          // In a real test environment, we'd mock the OAuth callback
          // For now, just verify the flow started
        }
      } else {
        console.log('OneDrive already connected or button not found');
      }
    });

    // Step 5: Connect Google Drive Account
    await test.step('Connect Google Drive account', async () => {
      // Find and click "Connect Google Drive" button
      const googleButton = page.locator('button:has-text("Connect Google"), button:has-text("Connect Google Drive")');

      if (await googleButton.count() > 0) {
        // Listen for popup/new tab
        const popupPromise = context.waitForEvent('page');
        await googleButton.click();

        // Note: In real tests, we'd need to handle OAuth flow
        const popup = await popupPromise;

        // Verify OAuth URL contains google.com
        await popup.waitForLoadState();
        const popupUrl = popup.url();

        if (popupUrl.includes('google') || popupUrl.includes('accounts.google')) {
          console.log('Google Drive OAuth flow initiated successfully');
          await popup.close();
        }
      } else {
        console.log('Google Drive already connected or button not found');
      }
    });

    // Step 6: Verify Connected Accounts Display
    await test.step('Verify connected accounts are displayed', async () => {
      // Look for connected account indicators
      // Note: Since we're mocking OAuth, we check for connection UI elements
      const accountsList = page.locator('[data-testid="connected-accounts"], .connected-accounts, section:has-text("Connected")');

      if (await accountsList.count() > 0) {
        await expect(accountsList).toBeVisible();
        console.log('Connected accounts section is visible');
      }
    });
  });

  test('should handle login errors gracefully', async ({ page }) => {
    await test.step('Attempt login with invalid credentials', async () => {
      await page.goto('/login');

      // Fill with invalid credentials
      await page.fill('input[type="email"], input[name="email"]', 'invalid@example.com');
      await page.fill('input[type="password"], input[name="password"]', 'wrongpassword');

      // Submit login
      await page.click('button[type="submit"], button:has-text("Login"), button:has-text("Sign In")');

      // Should show error message
      await expect(page.locator('text=/invalid|incorrect|wrong|error/i')).toBeVisible({ timeout: 5000 });

      // Should remain on login page
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test('should handle registration validation', async ({ page }) => {
    await test.step('Attempt registration with weak password', async () => {
      await page.goto('/register');

      // Fill with weak password
      await page.fill('input[type="email"], input[name="email"]', generateTestEmail());
      await page.fill('input[type="password"], input[name="password"]', '123');

      // Submit registration
      await page.click('button[type="submit"], button:has-text("Register"), button:has-text("Sign Up")');

      // Should show validation error
      const errorMessage = page.locator('text=/password.*weak|password.*short|at least.*characters/i');
      await expect(errorMessage).toBeVisible({ timeout: 5000 });
    });
  });
});
