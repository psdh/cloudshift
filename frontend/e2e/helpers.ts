import { Page } from '@playwright/test';

/**
 * E2E Test Helpers
 *
 * Common utilities for E2E tests to reduce duplication
 */

/**
 * Login helper - performs login flow
 */
export async function login(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.fill('input[type="email"], input[name="email"]', email);
  await page.fill('input[type="password"], input[name="password"]', password);
  await page.click('button[type="submit"], button:has-text("Login"), button:has-text("Sign In")');
  await page.waitForURL(/\/dashboard/, { timeout: 10000 });
}

/**
 * Register helper - performs registration flow
 */
export async function register(page: Page, email: string, password: string) {
  await page.goto('/register');
  await page.fill('input[type="email"], input[name="email"]', email);
  await page.fill('input[type="password"], input[name="password"]', password);

  // Handle confirm password field if present
  const confirmPasswordField = page.locator('input[name="confirmPassword"], input[placeholder*="confirm" i]');
  if (await confirmPasswordField.count() > 0) {
    await confirmPasswordField.fill(password);
  }

  await page.click('button[type="submit"], button:has-text("Register"), button:has-text("Sign Up")');
  await page.waitForURL(/\/(dashboard|login)/, { timeout: 10000 });
}

/**
 * Navigate to new transfer page
 */
export async function navigateToNewTransfer(page: Page) {
  const newTransferButton = page.locator('button:has-text("New Transfer"), a:has-text("New Transfer"), button:has-text("Create Transfer")');
  await newTransferButton.click();
  await page.waitForURL(/\/transfers\/(new|create)/, { timeout: 10000 });
}

/**
 * Wait for element with text to appear
 */
export async function waitForText(page: Page, text: string | RegExp, timeout = 5000) {
  const locator = typeof text === 'string'
    ? page.locator(`text="${text}"`)
    : page.locator(`text=${text}`);

  await locator.waitFor({ state: 'visible', timeout });
  return locator;
}

/**
 * Generate unique test email
 */
export function generateTestEmail(): string {
  return `test-${Date.now()}@example.com`;
}

/**
 * Check if running in CI environment
 */
export function isCI(): boolean {
  return !!process.env.CI;
}

/**
 * Get staging environment URL
 */
export function getStagingURL(): string {
  return process.env.E2E_BASE_URL || 'http://localhost:3000';
}

/**
 * Mock OAuth callback for testing
 * Note: In real staging environment, you'd need to configure OAuth test credentials
 */
export async function mockOAuthCallback(page: Page, provider: 'onedrive' | 'google') {
  // This would handle mocking OAuth in test environment
  // Implementation depends on your OAuth setup
  console.log(`Mocking OAuth callback for ${provider}`);

  // In real implementation, you'd:
  // 1. Intercept OAuth redirect
  // 2. Mock the callback with test tokens
  // 3. Complete the OAuth flow
}

/**
 * Wait for transfer to complete (for integration testing)
 */
export async function waitForTransferCompletion(page: Page, transferId: string, timeout = 60000) {
  await page.goto(`/transfers/${transferId}`);

  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    const status = await page.locator('[data-testid="transfer-status"], .transfer-status').textContent();

    if (status && /completed|failed|cancelled/i.test(status)) {
      return status.toLowerCase();
    }

    await page.waitForTimeout(2000);
    await page.reload();
  }

  throw new Error(`Transfer did not complete within ${timeout}ms`);
}

/**
 * Clean up test data after tests
 */
export async function cleanupTestUser(page: Page, email: string) {
  // This would call a test-only API endpoint to delete test user data
  // Only available in test/staging environments
  if (isCI() || process.env.NODE_ENV === 'test') {
    console.log(`Cleaning up test user: ${email}`);
    // await fetch('/api/test/cleanup', { method: 'POST', body: JSON.stringify({ email }) });
  }
}
