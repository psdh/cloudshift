#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Run Celery beat scheduler
celery -A app.core.celery_app beat --loglevel=info
