# CloudShift Deployment Guide

This guide covers deploying CloudShift to production using Docker and Docker Compose.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Database Migration Strategy](#database-migration-strategy)
- [Docker Deployment](#docker-deployment)
- [Environment Configuration](#environment-configuration)
- [Running Migrations](#running-migrations)
- [Health Checks](#health-checks)
- [Monitoring](#monitoring)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Server Requirements

- **OS:** Ubuntu 20.04 LTS or later (recommended)
- **CPU:** 2+ cores
- **RAM:** 4GB minimum, 8GB recommended
- **Storage:** 20GB minimum
- **Docker:** 20.10 or later
- **Docker Compose:** 2.0 or later

### Required Accounts

- AWS account (S3, SES)
- Microsoft Azure account (OneDrive OAuth)
- Google Cloud account (Google Drive OAuth)
- Twilio account (optional - for SMS notifications)

## Database Migration Strategy

CloudShift uses **Alembic** for database migrations with a zero-downtime strategy.

### Migration Philosophy

1. **Incremental Changes:** Each migration represents a single, atomic change
2. **Backwards Compatible:** Migrations should allow old code to run temporarily
3. **Automated:** Migrations run automatically on deployment
4. **Reversible:** Each migration has a downgrade path

### Migration Workflow

#### 1. Development Phase

When developing new features that require schema changes:

```bash
# Create a new migration
cd backend
alembic revision --autogenerate -m "Add user preferences table"

# Review the generated migration file
# Edit alembic/versions/<timestamp>_add_user_preferences_table.py

# Test migration locally
alembic upgrade head

# Test rollback
alembic downgrade -1
```

#### 2. Deployment Phase

**Step 1: Backup Database**
```bash
docker-compose exec postgres pg_dump -U cloudshift cloudshift > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Step 2: Run Migrations**

Migrations run automatically on container startup in production (see `docker-compose.prod.yml`):

```bash
# Backend service runs migrations before starting
sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"
```

**Step 3: Verify Migration**
```bash
# Check migration status
docker-compose exec backend alembic current

# View migration history
docker-compose exec backend alembic history
```

#### 3. Rollback Strategy

If a migration fails or causes issues:

```bash
# Rollback to previous version
docker-compose exec backend alembic downgrade -1

# Rollback to specific revision
docker-compose exec backend alembic downgrade <revision_id>

# Restore from backup (if needed)
docker-compose exec -T postgres psql -U cloudshift cloudshift < backup_20260106_120000.sql
```

### Migration Best Practices

1. **Never Edit Applied Migrations:** Create a new migration instead
2. **Test Migrations Locally:** Always test upgrade and downgrade paths
3. **Avoid Data Loss:** Use multi-step migrations for destructive changes:
   - Step 1: Add new column (nullable)
   - Step 2: Migrate data
   - Step 3: Make column non-nullable
4. **Use Transactions:** Wrap migrations in transactions when possible
5. **Monitor Long-Running Migrations:** Large table alterations may lock tables

### Zero-Downtime Migration Pattern

For production deployments with no downtime:

```python
# Example: Renaming a column without downtime

# Migration 1: Add new column
def upgrade():
    op.add_column('users', sa.Column('email_address', sa.String(255), nullable=True))

# Migration 2: Copy data (can run while old code is running)
def upgrade():
    op.execute("UPDATE users SET email_address = email WHERE email_address IS NULL")

# Migration 3: Make non-nullable
def upgrade():
    op.alter_column('users', 'email_address', nullable=False)

# Migration 4: Drop old column (deploy new code first!)
def upgrade():
    op.drop_column('users', 'email')
```

## Docker Deployment

### Development Deployment

```bash
# Clone repository
git clone https://github.com/your-org/cloudshift.git
cd cloudshift

# Create environment file
cp backend/.env.example backend/.env
# Edit backend/.env with your configuration

# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Deployment

```bash
# Set environment variables
export POSTGRES_PASSWORD="strong_random_password"
export REDIS_PASSWORD="strong_random_password"
export NEXT_PUBLIC_API_URL="https://api.cloudshift.example.com"

# Create production environment file
cp backend/.env.example backend/.env.production
# Edit backend/.env.production with production values

# Build and start with production overrides
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# View logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
```

### Service Management

```bash
# Restart specific service
docker-compose restart backend

# Scale Celery workers
docker-compose up -d --scale celery-worker=4

# View service status
docker-compose ps

# Execute commands in containers
docker-compose exec backend bash
docker-compose exec postgres psql -U cloudshift cloudshift
```

## Environment Configuration

### Production Environment Variables

Create `/backend/.env.production` with:

```bash
# Application
DEBUG=false
APP_NAME=CloudShift
APP_VERSION=1.0.0

# Database (use strong password!)
DATABASE_URL=postgresql+asyncpg://cloudshift:${POSTGRES_PASSWORD}@postgres:5432/cloudshift

# Redis (use strong password!)
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# JWT (generate new secret!)
JWT_SECRET_KEY=<generated_secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Encryption (generate new key!)
ENCRYPTION_KEY=<generated_fernet_key>

# AWS
AWS_ACCESS_KEY_ID=<production_key>
AWS_SECRET_ACCESS_KEY=<production_secret>
AWS_REGION=us-east-1
S3_BUCKET_NAME=cloudshift-prod-transfers

# OAuth
ONEDRIVE_CLIENT_ID=<production_client_id>
ONEDRIVE_CLIENT_SECRET=<production_client_secret>
GOOGLE_CLIENT_ID=<production_client_id>
GOOGLE_CLIENT_SECRET=<production_client_secret>

# Notifications
SES_FROM_EMAIL=noreply@cloudshift.example.com
TWILIO_ACCOUNT_SID=<production_sid>
TWILIO_AUTH_TOKEN=<production_token>
TWILIO_PHONE_NUMBER=<production_number>

# Frontend
FRONTEND_URL=https://cloudshift.example.com
```

### Security Checklist

- [ ] Changed all default secrets and passwords
- [ ] Set DEBUG=false
- [ ] Generated new JWT_SECRET_KEY
- [ ] Generated new ENCRYPTION_KEY
- [ ] Used strong database password
- [ ] Enabled Redis password
- [ ] Updated OAuth redirect URIs to production URLs
- [ ] Configured SSL/TLS certificates
- [ ] Set up firewall rules (allow only ports 80, 443)

## Running Migrations

### Manual Migration Commands

```bash
# Check current migration version
docker-compose exec backend alembic current

# Upgrade to latest
docker-compose exec backend alembic upgrade head

# Upgrade to specific revision
docker-compose exec backend alembic upgrade <revision_id>

# Downgrade one step
docker-compose exec backend alembic downgrade -1

# View migration history
docker-compose exec backend alembic history

# Generate new migration
docker-compose exec backend alembic revision --autogenerate -m "description"
```

### Migration Monitoring

```bash
# Monitor migration progress
docker-compose logs -f backend | grep alembic

# Check for migration errors
docker-compose logs backend | grep -i error
```

## Health Checks

### Endpoint Health Checks

```bash
# Backend API health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","database":"connected"}

# Frontend health (if implemented)
curl http://localhost:3000/api/health
```

### Service Health Checks

```bash
# PostgreSQL
docker-compose exec postgres pg_isready -U cloudshift

# Redis
docker-compose exec redis redis-cli ping

# Celery worker
docker-compose exec celery-worker celery -A app.core.celery_app inspect ping
```

### Docker Health Status

```bash
# View health status of all services
docker-compose ps

# Services should show "healthy" status
```

## Monitoring

### Log Management

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f celery-worker

# Follow logs with timestamps
docker-compose logs -f --timestamps

# View last 100 lines
docker-compose logs --tail=100
```

### Resource Monitoring

```bash
# Monitor resource usage
docker stats

# Monitor specific container
docker stats cloudshift-backend
```

### Application Metrics

- **API Response Times:** Monitor via application logs
- **Celery Task Queue:** Check Redis queue length
- **Database Connections:** Monitor PostgreSQL connection pool
- **Transfer Success Rate:** Track via audit logs

## Backup and Recovery

### Database Backups

#### Automated Backups

Create a backup script (`/scripts/backup.sh`):

```bash
#!/bin/bash
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/cloudshift_$TIMESTAMP.sql"

# Create backup
docker-compose exec -T postgres pg_dump -U cloudshift cloudshift > "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"

# Delete backups older than 30 days
find "$BACKUP_DIR" -name "cloudshift_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

Schedule with cron:
```bash
# Run daily at 2 AM
0 2 * * * /path/to/scripts/backup.sh
```

#### Manual Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U cloudshift cloudshift > backup.sql

# Restore from backup
docker-compose exec -T postgres psql -U cloudshift cloudshift < backup.sql
```

### S3 Backup Strategy

- **Lifecycle Policy:** Auto-delete transfer files after 7 days
- **Versioning:** Enable S3 versioning for disaster recovery
- **Replication:** Consider cross-region replication for critical data

## Troubleshooting

### Common Issues

#### Backend Won't Start

```bash
# Check logs
docker-compose logs backend

# Common causes:
# - Database not ready: Wait for postgres health check
# - Migration failed: Check alembic logs
# - Missing environment variables: Verify .env file
```

#### Database Connection Errors

```bash
# Verify database is running
docker-compose ps postgres

# Check connection
docker-compose exec postgres psql -U cloudshift cloudshift

# Reset database (CAUTION: destroys data!)
docker-compose down -v
docker-compose up -d postgres
docker-compose exec backend alembic upgrade head
```

#### Celery Tasks Not Running

```bash
# Check worker status
docker-compose logs celery-worker

# Check Redis connection
docker-compose exec redis redis-cli ping

# Restart worker
docker-compose restart celery-worker
```

#### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean up Docker
docker system prune -a --volumes

# Remove old logs
docker-compose down
rm -rf logs/*
docker-compose up -d
```

### Performance Tuning

#### PostgreSQL

Edit `docker-compose.prod.yml` to adjust:
- `max_connections`: Increase for more concurrent users
- `shared_buffers`: 25% of available RAM
- `effective_cache_size`: 50-75% of available RAM

#### Celery

Adjust worker concurrency based on CPU cores:
```bash
# 4 workers for CPU-bound tasks
docker-compose up -d --scale celery-worker=1
# Or adjust --concurrency in docker-compose.prod.yml
```

#### Redis

Monitor memory usage:
```bash
docker-compose exec redis redis-cli info memory
```

## Support

For deployment issues:
- Documentation: `/backend/docs`
- GitHub Issues: https://github.com/your-org/cloudshift/issues
- Email: support@cloudshift.example.com
