#!/usr/bin/env bash
set -e

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

if [ ! -f ".env" ]; then
  echo "No .env found — copying .env.example. Add your GEMINI_API_KEY before running!"
  cp .env.example .env
fi

echo "Starting server at http://localhost:8000"
uvicorn backend.main:app --reload --port 8000
