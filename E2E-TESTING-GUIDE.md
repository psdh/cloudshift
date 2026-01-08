# E2E Testing - Quick Start Guide

## Three Ways to Run E2E Tests Locally

### Option 1: Frontend Only (Quickest - Tests will partially fail)

If you just want to see Playwright in action and test UI interactions:

```bash
cd frontend
npm run test:e2e:ui
```

**What works:** UI rendering, form validation, navigation
**What fails:** API calls, login, data fetching

---

### Option 2: Full Stack (Recommended - Complete testing)

Runs all services (database, backend, frontend):

```bash
# From project root
./run-e2e-local.sh

# Or run in UI mode to see what's happening
./run-e2e-local.sh ui

# Or run in headed mode (visible browser)
./run-e2e-local.sh headed
```

**What it does:**
1. ✅ Starts PostgreSQL and Redis (via Docker)
2. ✅ Runs database migrations
3. ✅ Starts backend API on port 8000
4. ✅ Auto-starts frontend on port 3000 (via Playwright)
5. ✅ Runs all E2E tests

**Prerequisites:**
- Docker installed and running
- Python 3 installed
- Node.js installed

---

### Option 3: Manual Setup (Full Control)

Start each service manually in separate terminals:

**Terminal 1 - Database:**
```bash
docker-compose up postgres redis
```

**Terminal 2 - Backend:**
```bash
cd backend
source venv/bin/activate  # or create: python3 -m venv venv
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Terminal 3 - Frontend & Tests:**
```bash
cd frontend
npm run test:e2e:ui
```

---

## Current Test Status

⚠️ **Important:** These tests will have failures because:

1. **No OAuth configured** - Tests expect OneDrive/Google OAuth to work
2. **No test user** - Tests try to register/login but user may already exist
3. **No test data** - Tests expect cloud storage files to exist

## Making Tests Pass

### Quick Fix: Skip OAuth Tests

Edit the test files to skip OAuth-dependent tests:

```typescript
// frontend/e2e/auth-and-connect.spec.ts
test.skip('should connect OneDrive account', async ({ page }) => {
  // This test is skipped until OAuth is configured
});
```

### Better Fix: Mock OAuth (Recommended for Development)

I can help you create mock OAuth endpoints. Would you like me to:
1. Add test-only OAuth mock endpoints to backend
2. Update E2E tests to use mock OAuth
3. Create test data seeding scripts

---

## Troubleshooting

### "Backend not responding"
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check backend logs
tail -f /tmp/backend.log
```

### "Database connection failed"
```bash
# Check if PostgreSQL is running
docker-compose ps

# Restart database
docker-compose restart postgres
```

### "Port already in use"
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill

# Kill process on port 3000
lsof -ti:3000 | xargs kill
```

### "Playwright not installed"
```bash
cd frontend
npx playwright install chromium
```

---

## Test Modes Explained

| Command | Mode | Best For |
|---------|------|----------|
| `npm run test:e2e` | Headless | CI/CD, quick validation |
| `npm run test:e2e:ui` | Interactive UI | Development, debugging |
| `npm run test:e2e:headed` | Visible browser | Watching tests run |
| `npm run test:e2e:debug` | Debug mode | Stepping through tests |

---

## Next Steps

After running tests locally, you can:

1. **Review test results:**
   ```bash
   npx playwright show-report
   ```

2. **View test videos/screenshots:**
   ```bash
   ls frontend/test-results/
   ```

3. **Update tests** based on your actual implementation

4. **Configure for staging:**
   ```bash
   E2E_BASE_URL=https://staging.yourapp.com npm run test:e2e
   ```

---

## Need Help?

Common questions:

**Q: Do I need all services running?**
A: For basic UI tests, no. For full integration tests, yes.

**Q: Can I run against a remote backend?**
A: Yes! Set `NEXT_PUBLIC_API_URL=https://your-backend.com` in `.env.local`

**Q: Tests are slow, can I speed them up?**
A: Yes, run specific test files:
```bash
npx playwright test e2e/auth-and-connect.spec.ts
```

**Q: How do I debug a failing test?**
A: Use debug mode:
```bash
npm run test:e2e:debug
```
Then click on the test you want to debug.
