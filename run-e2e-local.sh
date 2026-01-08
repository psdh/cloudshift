#!/bin/bash

# Script to run E2E tests locally
# This starts all required services and runs the tests

set -e  # Exit on error

echo "🚀 Starting CloudShift E2E Test Environment..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    # Kill background processes
    jobs -p | xargs kill 2>/dev/null || true
}
trap cleanup EXIT

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command_exists docker; then
    echo -e "${RED}❌ Docker not found. Please install Docker.${NC}"
    exit 1
fi

if ! command_exists python3; then
    echo -e "${RED}❌ Python3 not found. Please install Python.${NC}"
    exit 1
fi

if ! command_exists node; then
    echo -e "${RED}❌ Node.js not found. Please install Node.js.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites found${NC}"

# Step 1: Start database and redis
echo -e "\n${YELLOW}Step 1: Starting PostgreSQL and Redis...${NC}"
docker-compose up -d postgres redis
sleep 3

# Wait for postgres to be ready
echo "Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U cloudshift > /dev/null 2>&1; do
    printf '.'
    sleep 1
done
echo -e "${GREEN}✅ Database is ready${NC}"

# Step 2: Run database migrations
echo -e "\n${YELLOW}Step 2: Running database migrations...${NC}"
cd backend
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

# Run migrations
alembic upgrade head
echo -e "${GREEN}✅ Migrations complete${NC}"

# Step 3: Start backend API
echo -e "\n${YELLOW}Step 3: Starting backend API...${NC}"
uvicorn app.main:app --reload --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is running${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Backend failed to start. Check /tmp/backend.log${NC}"
        cat /tmp/backend.log
        exit 1
    fi
    printf '.'
    sleep 1
done

# Step 4: Frontend is auto-started by Playwright
echo -e "\n${YELLOW}Step 4: Frontend will be auto-started by Playwright...${NC}"

# Step 5: Run E2E tests
echo -e "\n${YELLOW}Step 5: Running E2E tests...${NC}"
cd frontend

# Check which mode to run
MODE="${1:-test}"

case $MODE in
    "ui")
        echo "Running in UI mode (interactive)..."
        npm run test:e2e:ui
        ;;
    "headed")
        echo "Running in headed mode (visible browser)..."
        npm run test:e2e:headed
        ;;
    "debug")
        echo "Running in debug mode..."
        npm run test:e2e:debug
        ;;
    *)
        echo "Running in headless mode..."
        npm run test:e2e
        ;;
esac

echo -e "\n${GREEN}✅ E2E tests completed!${NC}"
