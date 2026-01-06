# CloudShift CI/CD Workflows

This directory contains GitHub Actions workflows for continuous integration and deployment of CloudShift.

## Workflows

### 1. CI (Continuous Integration)

**File:** `ci.yml`

**Trigger:** Pull requests and pushes to `main` and `develop` branches

**Jobs:**
- **Backend Tests:** Runs pytest with PostgreSQL and Redis services
- **Backend Linting:** Black (formatting), Flake8 (linting), MyPy (type checking)
- **Frontend Tests:** ESLint, TypeScript type checking, Jest tests
- **Frontend Build:** Verifies production build succeeds
- **Security Scan:** Trivy vulnerability scanner
- **Docker Build Test:** Validates Dockerfiles build successfully

**Required Secrets:** None (uses public services)

**Status Checks:** All jobs must pass before PR can be merged

---

### 2. Deploy to Staging

**File:** `deploy-staging.yml`

**Trigger:** Push to `main` branch

**Jobs:**
1. Build and push Docker images with `staging` tag
2. Deploy to staging server via SSH
3. Run database migrations
4. Perform health checks
5. Run smoke tests
6. Send Slack notifications

**Required Secrets:**
- `DOCKER_USERNAME` - Docker Hub username
- `DOCKER_PASSWORD` - Docker Hub password
- `STAGING_HOST` - Staging server hostname/IP
- `STAGING_USERNAME` - SSH username for staging server
- `STAGING_SSH_KEY` - SSH private key for staging server
- `SLACK_WEBHOOK_URL` - Slack webhook for notifications (optional)

**Deployment Strategy:** Replace existing containers

---

### 3. Deploy to Production

**File:** `deploy-production.yml`

**Trigger:** Manual workflow dispatch with version tag

**Jobs:**
1. Validate version tag exists
2. Check staging health
3. Create database backup
4. Build and push Docker images with version tag
5. Rolling update deployment (zero downtime)
6. Run database migrations
7. Perform health checks
8. Create deployment tag
9. Create GitHub release
10. Send Slack notifications

**Required Secrets:**
- `DOCKER_USERNAME` - Docker Hub username
- `DOCKER_PASSWORD` - Docker Hub password
- `PRODUCTION_HOST` - Production server hostname/IP
- `PRODUCTION_USERNAME` - SSH username for production server
- `PRODUCTION_SSH_KEY` - SSH private key for production server
- `SLACK_WEBHOOK_URL` - Slack webhook for notifications (optional)

**Deployment Strategy:** Rolling update with zero downtime

**Usage:**
```bash
# From GitHub UI:
Actions → Deploy to Production → Run workflow → Enter version (e.g., v1.0.0)
```

---

### 4. Docker Release

**File:** `docker-release.yml`

**Trigger:**
- Release published
- Push of version tags (v*.*.*)

**Jobs:**
1. Build multi-platform Docker images (amd64, arm64)
2. Push to Docker Hub with version tags
3. Scan images for vulnerabilities
4. Update Docker Hub descriptions
5. Send Slack notifications

**Required Secrets:**
- `DOCKER_USERNAME` - Docker Hub username
- `DOCKER_PASSWORD` - Docker Hub password
- `SLACK_WEBHOOK_URL` - Slack webhook for notifications (optional)

**Image Tags Generated:**
- `v1.2.3` (exact version)
- `v1.2` (minor version)
- `v1` (major version)
- `main-<sha>` (commit SHA)

---

## Setup Instructions

### 1. Configure Repository Secrets

Go to **Settings → Secrets and variables → Actions** and add:

#### Docker Hub
```
DOCKER_USERNAME=your_dockerhub_username
DOCKER_PASSWORD=your_dockerhub_token
```

#### Staging Server
```
STAGING_HOST=staging.cloudshift.example.com
STAGING_USERNAME=deploy
STAGING_SSH_KEY=<paste_private_key>
```

#### Production Server
```
PRODUCTION_HOST=cloudshift.example.com
PRODUCTION_USERNAME=deploy
PRODUCTION_SSH_KEY=<paste_private_key>
```

#### Notifications (Optional)
```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 2. Configure Environments

Go to **Settings → Environments** and create:

#### Staging Environment
- **Name:** `staging`
- **URL:** `https://staging.cloudshift.example.com`
- **Protection rules:** None (auto-deploy on merge to main)

#### Production Environment
- **Name:** `production`
- **URL:** `https://cloudshift.example.com`
- **Protection rules:**
  - Required reviewers (at least 1)
  - Wait timer (optional, e.g., 5 minutes)

### 3. Server Setup

Both staging and production servers need:

#### Install Docker and Docker Compose
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### Create deployment directory
```bash
sudo mkdir -p /opt/cloudshift
sudo chown $USER:$USER /opt/cloudshift
cd /opt/cloudshift

# Clone repository or copy docker-compose files
git clone https://github.com/your-org/cloudshift.git .

# Create environment file
cp backend/.env.example backend/.env.production
# Edit backend/.env.production with production values
```

#### Setup SSH access for GitHub Actions
```bash
# On your local machine, generate SSH key pair
ssh-keygen -t ed25519 -C "github-actions" -f cloudshift-deploy

# Copy public key to server
ssh-copy-id -i cloudshift-deploy.pub deploy@staging.cloudshift.example.com

# Add private key to GitHub Secrets as STAGING_SSH_KEY
cat cloudshift-deploy
```

### 4. Branch Protection Rules

Go to **Settings → Branches** and protect `main`:

- ✅ Require a pull request before merging
- ✅ Require status checks to pass before merging
  - Required checks:
    - Backend Tests
    - Frontend Tests
    - Docker Build Test
- ✅ Require conversation resolution before merging
- ✅ Do not allow bypassing the above settings

---

## Workflow Execution

### Development Workflow

1. **Create feature branch:**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Make changes and commit:**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin feature/new-feature
   ```

3. **Create pull request:**
   - CI workflow runs automatically
   - All tests must pass
   - Code review required

4. **Merge to main:**
   - Staging deployment triggers automatically
   - Smoke tests run on staging

### Release Workflow

1. **Create release tag:**
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin v1.0.0
   ```

2. **Docker images build automatically:**
   - Multi-platform images pushed to Docker Hub
   - Vulnerability scanning performed

3. **Deploy to production (manual):**
   - Go to Actions → Deploy to Production
   - Click "Run workflow"
   - Enter version tag (e.g., `v1.0.0`)
   - Approve deployment (if protection rules configured)

### Rollback Workflow

If production deployment fails or issues are detected:

1. **Immediate rollback via SSH:**
   ```bash
   ssh deploy@cloudshift.example.com
   cd /opt/cloudshift

   # Restore from backup
   docker-compose exec -T postgres psql -U cloudshift cloudshift < /backups/pre_deploy_YYYYMMDD_HHMMSS.sql

   # Deploy previous version
   export BACKEND_IMAGE=cloudshift-backend:v1.0.0
   export FRONTEND_IMAGE=cloudshift-frontend:v1.0.0
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

2. **Or re-run production workflow with previous version**

---

## Monitoring and Alerts

### GitHub Actions Monitoring

- **View workflow runs:** Actions tab
- **Monitor deployment status:** Environments tab
- **Check workflow logs:** Click on any workflow run

### Slack Notifications

All workflows send notifications to Slack:
- ✅ Success messages (green)
- ❌ Failure messages (red)

Configure `SLACK_WEBHOOK_URL` secret to enable.

### Email Notifications

GitHub automatically sends emails for:
- Workflow failures (to committer)
- Deployment failures (to deployment triggerer)

---

## Troubleshooting

### CI Failures

**Tests fail:**
```bash
# Run tests locally
cd backend
pytest tests/ -v
```

**Docker build fails:**
```bash
# Build locally
docker build -t cloudshift-backend backend/
```

### Deployment Failures

**SSH connection fails:**
- Verify `STAGING_HOST` or `PRODUCTION_HOST` is correct
- Verify SSH key has correct permissions
- Check server firewall allows SSH from GitHub Actions IPs

**Database migration fails:**
```bash
# SSH to server and check logs
docker-compose logs backend

# Manual migration
docker-compose exec backend alembic upgrade head
```

**Health check fails:**
```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs backend

# Manual health check
curl http://localhost:8000/health
```

---

## Best Practices

1. **Always create PRs:** Never push directly to `main`
2. **Wait for CI:** Ensure all checks pass before merging
3. **Test on staging:** Verify changes work on staging before production
4. **Version tags:** Use semantic versioning (v1.2.3)
5. **Review deployment logs:** Always check logs after production deployment
6. **Monitor post-deployment:** Watch error rates and performance metrics
7. **Keep secrets secure:** Never commit secrets to repository

---

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Hub](https://hub.docker.com)
- [Semantic Versioning](https://semver.org)
