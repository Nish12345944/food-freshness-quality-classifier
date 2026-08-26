"""Real-model smoke test (integration).

Verifies that a genuine trained artifact (models/food_freshness.pt) loads,
matches the expected MobileNetV3-Small + 3-class architecture, runs inference,
and returns valid probabilities summing to ~1 with a label in
Fresh / Okay / Avoid.

This test SKIPS when no real model is present — it never fabricates model
results.  CI runs it only when a MODEL_URL/model is configured.
"""
import os

import pytest

from app.config import Config
from app.services.model_validation import validate_model
from app.services.prediction_service import LABELS, PredictionService

MODEL_PATH = os.environ.get("MODEL_PATH", Config.MODEL_PATH)


def test_model_smoke_validation():
    if not os.path.isfile(MODEL_PATH):
        pytest.skip("Trained model artifact not present — skipping real-model smoke test.")

    service = PredictionService(
        model_path=MODEL_PATH,
        model_version=Config.MODEL_VERSION,
        conf_high=Config.CONFIDENCE_HIGH,
        conf_medium=Config.CONFIDENCE_MEDIUM,
    )

    assert service.is_loaded, "Model must load from the artifact."
    result = validate_model(service)

    # Provide a readable failure listing every check.
    assert result.get("valid"), "Model validation failed:\n" + "\n".join(
        f"  - {ch['check']}: {'PASS' if ch['passed'] else 'FAIL'} ({ch['detail']})"
        for ch in result["checks"]
    )

    # Explicit assertions for the headline checks the task requires.
    assert result["prediction"] in LABELS, "Prediction must be Fresh/Okay/Avoid."
    probs = result["probabilities"]
    assert probs is not None and abs(float(probs.sum()) - 1.0) < 1e-3
    assert result["checks"][0]["check"] == "model_file_exists"