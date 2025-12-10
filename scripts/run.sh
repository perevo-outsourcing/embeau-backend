#!/bin/bash

# EMBEAU API Runner Script

set -e

cd "$(dirname "$0")/.."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your configuration"
fi

# Initialize database if it doesn't exist
if [ ! -f embeau.db ]; then
    echo "Initializing database..."
    uv run python -m embeau_api.db.init_db
fi

# Run the server
echo "Starting EMBEAU API server..."
uv run uvicorn embeau_api.main:app --host 0.0.0.0 --port 8000 --reload
