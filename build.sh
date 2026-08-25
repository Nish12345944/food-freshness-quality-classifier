#!/usr/bin/env bash
# Reproducible Render build script
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Ensure runtime directories exist (contents are ephemeral on Render — see docs/architecture.md)
mkdir -p static/uploads static/reports static/profiles static/gradcam instance models

echo "Build complete."