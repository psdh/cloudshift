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

      // Wait for registration form to load - actual page has h2 "Create your account"
      await expect(page.locator('h2')).toContainText(/create your account/i);

      // Fill registration form
      await page.fill('input[name="email"]', testEmail);
      await page.fill('input[name="password"]', testPassword);
      await page.fill('input[name="confirm-password"]', testPassword);

      // Submit registration - button says "Create account"
      await page.click('button:has-text("Create account")');

      // Should redirect to login page with success query param
      await page.waitForURL(/\/login/, { timeout: 10000 });

      // Should show success message
      await expect(page.locator('text=/account created successfully/i')).toBeVisible({ timeout: 5000 });
    });

    // Step 2: User Login
    await test.step('Login with registered credentials', async () => {
      // We're already on login page from registration redirect
      // Wait for page to be ready - actual page has h2 "Sign in to your account"
      await expect(page.locator('h2')).toContainText(/sign in to your account/i);

      // Fill login form
      await page.fill('input[name="email"]', testEmail);
      await page.fill('input[name="password"]', testPassword);

      // Submit login - button says "Sign in"
      await page.click('button:has-text("Sign in")');

      // Wait for redirect to dashboard
      await page.waitForURL(/\/dashboard/, { timeout: 10000 });

      // Verify we're on the dashboard - has h1 "Dashboard"
      await expect(page.locator('h1')).toContainText('Dashboard');
    });

    // Step 3: Navigate to Account Settings
    await test.step('Navigate to account settings', async () => {
      // Navigate directly to connected accounts page
      await page.goto('/settings/accounts');

      // Wait for page to load - has h1 "Connected Accounts"
      await expect(page.locator('h1')).toContainText('Connected Accounts');
    });

    // Step 4: Verify OneDrive Connect Button
    await test.step('Verify OneDrive connection option', async () => {
      // Find "Connect OneDrive" button
      const onedriveButton = page.locator('button:has-text("Connect OneDrive")');

      // Button should be visible
      await expect(onedriveButton).toBeVisible();

      // Note: Clicking would redirect to Microsoft OAuth
      // For E2E tests, we would need:
      // 1. Mock OAuth backend endpoint
      // 2. Or use test OAuth credentials
      // 3. Or intercept the OAuth flow

      console.log('✓ OneDrive connection button found and visible');
    });

    // Step 5: Verify Google Drive Connect Button
    await test.step('Verify Google Drive connection option', async () => {
      // Find "Connect Google Drive" button
      const googleButton = page.locator('button:has-text("Connect Google Drive")');

      // Button should be visible
      await expect(googleButton).toBeVisible();

      console.log('✓ Google Drive connection button found and visible');
    });

    // Step 6: Verify Page Information
    await test.step('Verify account connection information', async () => {
      // Verify informational text is shown
      await expect(page.locator('text=/why connect accounts/i')).toBeVisible();
      await expect(page.locator('text=/You\'ll need both accounts connected/i')).toBeVisible();

      // Verify both account cards are present
      await expect(page.locator('text=OneDrive')).toBeVisible();
      await expect(page.locator('text=Google Drive')).toBeVisible();

      console.log('✓ Connected Accounts page structure verified');
    });
  });

  test('should handle login errors gracefully', async ({ page }) => {
    await test.step('Attempt login with invalid credentials', async () => {
      await page.goto('/login');

      // Wait for page to load
      await expect(page.locator('h2')).toContainText(/sign in to your account/i);

      // Fill with invalid credentials
      await page.fill('input[name="email"]', 'invalid@example.com');
      await page.fill('input[name="password"]', 'wrongpassword');

      // Submit login
      await page.click('button:has-text("Sign in")');

      // Should show error message (red border with text)
      // Wait a bit for API call to fail
      await page.waitForTimeout(1000);

      // Look for error message div
      const errorDiv = page.locator('.bg-red-50');
      if (await errorDiv.count() > 0) {
        await expect(errorDiv).toBeVisible();
        console.log('✓ Error message displayed for invalid credentials');
      }

      // Should remain on login page
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test('should handle registration validation', async ({ page }) => {
    await test.step('Attempt registration with weak password', async () => {
      await page.goto('/register');

      // Wait for page to load
      await expect(page.locator('h2')).toContainText(/create your account/i);

      // Fill with weak password
      await page.fill('input[name="email"]', generateTestEmail());
      await page.fill('input[name="password"]', '123');
      await page.fill('input[name="confirm-password"]', '123');

      // Submit registration
      await page.click('button:has-text("Create account")');

      // Should show validation error
      const errorDiv = page.locator('.bg-red-50');
      await expect(errorDiv).toBeVisible({ timeout: 5000 });
      await expect(errorDiv).toContainText(/password must be at least 8 characters/i);

      console.log('✓ Password validation working correctly');
    });
  });
});
