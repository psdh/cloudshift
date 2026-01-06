# CloudShift Backend

FastAPI-based backend for CloudShift cloud file migration service.

## Prerequisites

- Python 3.12+
- PostgreSQL 16+ (local installation or Docker)
- Redis 7+ (local installation or Docker)

## Setup

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Database Setup

#### Option A: Using Docker (Recommended)

```bash
# From project root
docker compose up -d
```

This will start both PostgreSQL and Redis containers.

#### Option B: Local Installation

Install PostgreSQL and Redis locally and create a database:

```bash
createdb cloudshift
```

### 3. Environment Variables

Copy `.env.example` to `.env` and update the values:

```bash
cp .env.example .env
```

Update `DATABASE_URL` and `REDIS_URL` in `.env`:

```
DATABASE_URL=postgresql+asyncpg://cloudshift:cloudshift_dev_password@localhost:5432/cloudshift
REDIS_URL=redis://localhost:6379/0
```

### 4. Run Database Migrations

```bash
alembic upgrade head
```

### 5. Start the Server

```bash
python -m uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

```bash
pytest
```

## Project Structure

```
backend/
├── app/
│   ├── api/          # API routes
│   ├── core/         # Core utilities and config
│   ├── models/       # Database models
│   ├── services/     # Business logic
│   └── main.py       # Application entry point
├── tests/            # Test suite
├── alembic/          # Database migrations
└── requirements.txt  # Python dependencies
```
