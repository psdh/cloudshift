# CloudShift Environment Configuration Guide

This document describes all environment variables required to run CloudShift and provides setup instructions for local development.

## Quick Start

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Fill in the required values (see sections below)

3. Start the development server:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

## Environment Variables

### Application Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_NAME` | No | CloudShift | Application name |
| `APP_VERSION` | No | 1.0.0 | Application version |
| `DEBUG` | No | false | Enable debug mode (set to `true` for development) |
| `HOST` | No | 0.0.0.0 | Server bind address |
| `PORT` | No | 8000 | Server port |

### Database Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | **YES** | PostgreSQL connection string in format: `postgresql+asyncpg://user:password@host:port/database` |

**Setup Instructions:**

1. Install PostgreSQL (or use Docker):
   ```bash
   # Using Docker
   docker run --name cloudshift-postgres \
     -e POSTGRES_USER=cloudshift \
     -e POSTGRES_PASSWORD=password \
     -e POSTGRES_DB=cloudshift \
     -p 5432:5432 \
     -d postgres:15
   ```

2. Update `.env` with your connection string:
   ```
   DATABASE_URL=postgresql+asyncpg://cloudshift:password@localhost:5432/cloudshift
   ```

3. Run database migrations:
   ```bash
   alembic upgrade head
   ```

### Redis Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `REDIS_URL` | **YES** | Redis connection string for Celery task queue |

**Setup Instructions:**

1. Install Redis (or use Docker):
   ```bash
   # Using Docker
   docker run --name cloudshift-redis \
     -p 6379:6379 \
     -d redis:7-alpine
   ```

2. Update `.env`:
   ```
   REDIS_URL=redis://localhost:6379/0
   ```

### JWT Authentication

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | **YES** | - | Secret key for signing JWT tokens (MUST be changed in production!) |
| `JWT_ALGORITHM` | No | HS256 | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | 15 | Access token expiration time in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | 7 | Refresh token expiration time in days |

**Setup Instructions:**

1. Generate a secure secret key:
   ```python
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. Update `.env`:
   ```
   JWT_SECRET_KEY=<generated_key>
   ```

### Encryption

| Variable | Required | Description |
|----------|----------|-------------|
| `ENCRYPTION_KEY` | **YES** | 32-byte URL-safe base64-encoded key for Fernet encryption (used to encrypt OAuth tokens) |

**Setup Instructions:**

1. Generate encryption key:
   ```python
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. Update `.env`:
   ```
   ENCRYPTION_KEY=<generated_key>
   ```

### AWS Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_ACCESS_KEY_ID` | **YES** | AWS access key ID |
| `AWS_SECRET_ACCESS_KEY` | **YES** | AWS secret access key |
| `AWS_REGION` | No | AWS region (default: us-east-1) |
| `S3_BUCKET_NAME` | **YES** | S3 bucket name for intermediate file storage |

**Setup Instructions:**

1. Create an AWS account and IAM user with S3 and SES permissions

2. Create an S3 bucket:
   ```bash
   aws s3 mb s3://cloudshift-transfers --region us-east-1
   ```

3. Enable encryption:
   ```bash
   aws s3api put-bucket-encryption \
     --bucket cloudshift-transfers \
     --server-side-encryption-configuration \
     '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
   ```

4. Set lifecycle policy (optional - auto-delete files after 7 days):
   ```bash
   aws s3api put-bucket-lifecycle-configuration \
     --bucket cloudshift-transfers \
     --lifecycle-configuration file://s3-lifecycle.json
   ```

5. Update `.env`:
   ```
   AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
   AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   S3_BUCKET_NAME=cloudshift-transfers
   ```

### OAuth - OneDrive

| Variable | Required | Description |
|----------|----------|-------------|
| `ONEDRIVE_CLIENT_ID` | **YES** | Microsoft Azure App Registration client ID |
| `ONEDRIVE_CLIENT_SECRET` | **YES** | Microsoft Azure App Registration client secret |

**Setup Instructions:**

1. Go to [Azure App Registrations](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)

2. Click "New registration":
   - Name: CloudShift
   - Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
   - Redirect URI: Web - `http://localhost:8000/api/oauth/onedrive/callback`

3. After creation:
   - Copy the "Application (client) ID"
   - Go to "Certificates & secrets" → "New client secret" → Copy the value

4. Go to "API permissions":
   - Add permission → Microsoft Graph → Delegated permissions
   - Add: `Files.Read`, `Files.ReadWrite`, `offline_access`

5. Update `.env`:
   ```
   ONEDRIVE_CLIENT_ID=<your_client_id>
   ONEDRIVE_CLIENT_SECRET=<your_client_secret>
   ```

### OAuth - Google Drive

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_CLIENT_ID` | **YES** | Google Cloud OAuth 2.0 client ID |
| `GOOGLE_CLIENT_SECRET` | **YES** | Google Cloud OAuth 2.0 client secret |

**Setup Instructions:**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)

2. Create a new project or select existing

3. Enable Google Drive API:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Drive API" → Enable

4. Create OAuth credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: Web application
   - Name: CloudShift
   - Authorized redirect URIs: `http://localhost:8000/api/oauth/google/callback`

5. Copy the client ID and client secret

6. Update `.env`:
   ```
   GOOGLE_CLIENT_ID=<your_client_id>.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=<your_client_secret>
   ```

### Email Notifications (Optional)

| Variable | Required | Description |
|----------|----------|-------------|
| `SES_FROM_EMAIL` | No | AWS SES verified email address for sending notifications |

**Setup Instructions:**

1. Verify your email address in AWS SES:
   ```bash
   aws ses verify-email-identity --email-address noreply@cloudshift.example.com
   ```

2. Check verification status:
   ```bash
   aws ses get-identity-verification-attributes \
     --identities noreply@cloudshift.example.com
   ```

3. Update `.env`:
   ```
   SES_FROM_EMAIL=noreply@cloudshift.example.com
   ```

**Note:** If not configured, email notifications will be disabled.

### SMS Notifications (Optional)

| Variable | Required | Description |
|----------|----------|-------------|
| `TWILIO_ACCOUNT_SID` | No | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | No | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | No | Twilio phone number (E.164 format, e.g., +12345678900) |

**Setup Instructions:**

1. Create a Twilio account at [twilio.com](https://www.twilio.com/)

2. Get a phone number and copy credentials from console

3. Update `.env`:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=+12345678900
   ```

**Note:** If not configured, SMS notifications will be disabled.

### Frontend Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FRONTEND_URL` | No | http://localhost:3000 | Frontend URL for email links and CORS configuration |

## Local Development Setup

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 13 or higher
- Redis 6 or higher
- AWS account (for S3 and optionally SES)
- Microsoft Azure account (for OneDrive OAuth)
- Google Cloud account (for Google Drive OAuth)

### Step-by-Step Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/cloudshift.git
   cd cloudshift/backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and fill in required values
   ```

5. **Start PostgreSQL and Redis:**
   ```bash
   docker-compose up -d postgres redis
   ```

6. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

7. **Start Celery worker (in separate terminal):**
   ```bash
   celery -A app.core.celery_app worker --loglevel=info
   ```

8. **Start Celery beat (in separate terminal):**
   ```bash
   celery -A app.core.celery_app beat --loglevel=info
   ```

9. **Start development server:**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

10. **Access the application:**
    - API: http://localhost:8000
    - API Docs: http://localhost:8000/docs
    - Health Check: http://localhost:8000/health

## Production Deployment

For production deployment, ensure:

1. **Change all default secrets:**
   - Generate new `JWT_SECRET_KEY`
   - Generate new `ENCRYPTION_KEY`
   - Use strong database passwords

2. **Set DEBUG to false:**
   ```
   DEBUG=false
   ```

3. **Use production database:**
   - Use managed PostgreSQL service (AWS RDS, Google Cloud SQL, etc.)
   - Enable SSL connections
   - Regular backups

4. **Secure Redis:**
   - Use managed Redis service (AWS ElastiCache, etc.)
   - Enable authentication
   - Use TLS

5. **Configure proper CORS:**
   - Update `FRONTEND_URL` to production URL
   - Configure proper CORS origins

6. **Set up monitoring:**
   - Application logs
   - Error tracking (Sentry, etc.)
   - Performance monitoring

7. **Configure OAuth redirect URIs:**
   - Update redirect URIs in Azure and Google Cloud Console to production URLs

## Troubleshooting

### Database connection fails

- Verify PostgreSQL is running: `docker ps` or `pg_isready`
- Check connection string format
- Ensure database exists: `psql -U postgres -c "\l"`

### Redis connection fails

- Verify Redis is running: `redis-cli ping`
- Check Redis URL format

### OAuth errors

- Verify client IDs and secrets are correct
- Check redirect URIs match exactly (including http/https)
- Ensure API permissions are granted

### Celery tasks not running

- Ensure Celery worker is running
- Check Redis connection
- Verify task imports in `celery_app.py`

## Security Best Practices

1. **Never commit `.env` file to git** (already in `.gitignore`)
2. **Rotate secrets regularly** in production
3. **Use environment-specific credentials** (dev, staging, prod)
4. **Enable AWS CloudTrail** for audit logging
5. **Use IAM roles** instead of access keys when running on AWS
6. **Enable 2FA** on all cloud provider accounts
7. **Regularly update dependencies**: `pip list --outdated`

## Support

For setup assistance:
- Documentation: `/docs` folder
- Issues: GitHub Issues
- Email: support@cloudshift.example.com
