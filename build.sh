#!/usr/bin/env bash
# Reproducible Render build script.
#
# Responsibilities:
#   1. Install dependencies (CPU-only PyTorch for lean Render builds).
#   2. Ensure runtime directories exist.
#   3. Obtain the trained model artifact (models/food_freshness.pt) either
#      because it is already present, or by downloading it from MODEL_URL.
#   4. Fail the build (fail-closed) if a model is required but unavailable —
#      we never silently deploy an AI service with no model.
set -o errexit
set -o nounset
set -o pipefail

# ---------------------------------------------------------------------------
# 1. Install dependencies
# ---------------------------------------------------------------------------
pip install --upgrade pip

# Install CPU-only PyTorch from the official CPU wheel index first, so Render's
# build does not pull the large CUDA-enabled wheels from PyPI.
pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.6.0" "torchvision>=0.21.0"
pip install -r requirements.txt

# ---------------------------------------------------------------------------
# 2. Create runtime directories (contents are ephemeral on Render)
# ---------------------------------------------------------------------------
mkdir -p static/uploads static/reports static/profiles static/gradcam instance models

# ---------------------------------------------------------------------------
# 3 & 4. Model artifact contract (fail-closed)
# ---------------------------------------------------------------------------
MODEL_PATH="${MODEL_PATH:-models/food_freshness.pt}"
# "1" (default) = production must have a real model; "0" = allow degraded boot.
REQUIRE_MODEL="${REQUIRE_MODEL:-1}"

download_model() {
  local url="$1"
  local dest="$2"
  echo "Downloading model from MODEL_URL -> ${dest}"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --retry 3 --connect-timeout 60 -o "${dest}" "${url}"
  else
    wget -q -O "${dest}" "${url}"
  fi
}

if [ -f "${MODEL_PATH}" ]; then
  echo "==> Model already present at ${MODEL_PATH}; skipping download."
elif [ -n "${MODEL_URL:-}" ]; then
  download_model "${MODEL_URL}" "${MODEL_PATH}"
else
  echo "==> MODEL_URL is not set and no model file exists at ${MODEL_PATH}." >&2
  if [ "${REQUIRE_MODEL}" = "1" ]; then
    echo "ERROR: A trained model artifact is required for production." >&2
    echo "       Train it (see training/README.md) or set MODEL_URL to a real artifact." >&2
    exit 1
  fi
  echo "WARNING: REQUIRE_MODEL=0 — deploying degraded (model_loaded=false)." >&2
fi

# Verify the model file actually exists before proceeding.
if [ ! -f "${MODEL_PATH}" ]; then
  echo "ERROR: Model file still missing at ${MODEL_PATH} after build." >&2
  exit 1
fi
echo "==> Model artifact verified: ${MODEL_PATH}"

echo "Build complete."