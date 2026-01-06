#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Run Celery worker
celery -A app.core.celery_app worker --loglevel=info --concurrency=4
