# End-to-End Tests

This directory contains E2E tests for CloudShift using Playwright.

## Test Files

- `auth-and-connect.spec.ts` - Tests user registration, login, and account connection flow
- `transfer-creation.spec.ts` - Tests transfer creation, configuration, and initiation
- `transfer-progress.spec.ts` - Tests transfer progress monitoring and completion
- `helpers.ts` - Common utilities and helper functions for tests

## Running Tests

### Prerequisites

1. Install dependencies:
   ```bash
   npm install
   ```

2. Install Playwright browsers:
   ```bash
   npx playwright install
   ```

### Local Development

Run tests against local development server:

```bash
# Run all tests
npm run test:e2e

# Run tests in UI mode (interactive)
npx playwright test --ui

# Run specific test file
npx playwright test e2e/auth-and-connect.spec.ts

# Run tests in headed mode (see browser)
npx playwright test --headed

# Debug tests
npx playwright test --debug
```

### Staging Environment

Run tests against staging environment:

```bash
E2E_BASE_URL=https://staging.cloudshift.example.com npm run test:e2e
```

## Test Coverage

### Critical User Flows

1. **Authentication and Account Connection**
   - User registration with validation
   - User login
   - Connect OneDrive account via OAuth
   - Connect Google Drive account via OAuth
   - Error handling for invalid credentials

2. **Transfer Creation and Configuration**
   - Create new transfer job
   - Select source files/folders from OneDrive
   - Select destination folder in Google Drive
   - Configure file type filters
   - Configure date range filters
   - Set conflict resolution strategy
   - Schedule transfer for future execution
   - Run dry run preview
   - Start transfer

3. **Transfer Progress and Completion**
   - View active transfer progress
   - Monitor real-time progress updates
   - View current file being transferred
   - View transfer speed and ETA
   - Cancel active transfer
   - View completed transfer details
   - View failed transfer details with errors
   - Retry failed transfers
   - Filter transfer history
   - Download transfer report

## Configuration

E2E tests are configured in `playwright.config.ts` with the following settings:

- **Browser**: Chromium (can be extended to Firefox and Safari)
- **Base URL**: `http://localhost:3000` (or `E2E_BASE_URL` env var)
- **Retries**: 2 retries in CI, 0 in local development
- **Screenshots**: Captured on failure
- **Traces**: Captured on first retry
- **Web Server**: Automatically starts dev server if not running

## Writing New Tests

### Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup before each test
  });

  test('should perform specific action', async ({ page }) => {
    await test.step('Step 1 description', async () => {
      // Test step 1
    });

    await test.step('Step 2 description', async () => {
      // Test step 2
    });
  });
});
```

### Best Practices

1. **Use test.step()** for better organization and reporting
2. **Use data-testid** attributes in components for reliable selectors
3. **Handle asynchronous operations** with proper waits
4. **Mock OAuth flows** in test environment
5. **Clean up test data** after tests complete
6. **Use helpers** from `helpers.ts` to reduce duplication
7. **Add timeouts** for operations that may take time
8. **Test error states** and edge cases

### Locator Strategies

Prefer locators in this order:

1. `data-testid` attributes: `page.locator('[data-testid="element"]')`
2. Accessible roles: `page.locator('button[role="submit"]')`
3. Text content: `page.locator('text="Button Text"')`
4. CSS selectors: Only as last resort

## OAuth Testing

OAuth flows require special handling in E2E tests:

### Option 1: Mock OAuth in Test Environment

Configure your backend to accept test OAuth tokens in staging:

```typescript
// In test environment
process.env.OAUTH_TEST_MODE = 'true';
```

### Option 2: Use Real OAuth with Test Accounts

Create test accounts for Microsoft and Google:
- Microsoft: Use developer account
- Google: Use test user in Google Cloud Console

Store credentials securely:

```bash
# .env.test
ONEDRIVE_TEST_EMAIL=test@example.com
ONEDRIVE_TEST_PASSWORD=secure_password
GOOGLE_TEST_EMAIL=test@example.com
GOOGLE_TEST_PASSWORD=secure_password
```

### Option 3: Intercept and Mock OAuth Responses

Use Playwright's route interception:

```typescript
await page.route('**/api/oauth/**', (route) => {
  route.fulfill({
    status: 200,
    body: JSON.stringify({ success: true, token: 'mock-token' })
  });
});
```

## CI/CD Integration

Tests run automatically in CI/CD pipeline:

```yaml
# .github/workflows/e2e-tests.yml
- name: Run E2E tests
  run: |
    npm run build
    E2E_BASE_URL=https://staging.example.com npm run test:e2e
```

## Debugging

### View Test Results

After test run:

```bash
npx playwright show-report
```

### Debug Failed Tests

```bash
# Run specific test in debug mode
npx playwright test e2e/auth-and-connect.spec.ts --debug

# View trace for failed test
npx playwright show-trace trace.zip
```

### Common Issues

1. **Timeouts**: Increase timeout in test or config
2. **Flaky tests**: Add proper waits for dynamic content
3. **OAuth failures**: Ensure OAuth credentials are configured
4. **Element not found**: Check if page has fully loaded

## Environment Variables

- `E2E_BASE_URL` - Base URL for tests (default: http://localhost:3000)
- `CI` - Set to 'true' in CI environment
- `OAUTH_TEST_MODE` - Enable OAuth mocking (default: false)

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Debugging Guide](https://playwright.dev/docs/debug)
