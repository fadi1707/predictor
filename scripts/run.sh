#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
uvicorn app.main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8080}" --reload
