#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
mkdir -p workspace workspace/.rollbacks data config
touch workspace/demo.txt
echo "Installed. Copy .env.example to .env and adjust as needed."
