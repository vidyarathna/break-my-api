#!/usr/bin/env bash
# Start the deliberately buggy API on http://127.0.0.1:8000
cd "$(dirname "$0")"
exec uvicorn app.main:app --reload --port 8000
