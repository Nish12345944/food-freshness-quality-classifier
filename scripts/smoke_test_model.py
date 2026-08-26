#!/usr/bin/env python3
"""Standalone real-model smoke test.

Usage:
    python scripts/smoke_test_model.py [PATH_TO_MODEL.pt]

Runs the full prediction pipeline validation on the trained MobileNetV3-Small
artifact and exits 0 on success, 1 on failure.  Never fabricates results.

Example:
    python scripts/smoke_test_model.py models/food_freshness.pt
"""
import os
import sys

# Allow running from anywhere in the repo.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Config  # noqa: E402
from app.services.model_validation import validate_model  # noqa: E402
from app.services.prediction_service import PredictionService  # noqa: E402


def main() -> int:
    model_path = sys.argv[1] if len(sys.argv) > 1 else Config.MODEL_PATH

    if not os.path.isfile(model_path):
        print(f"ERROR: Model file not found at '{model_path}'.", file=sys.stderr)
        print("Train it first:  cd training && python train.py", file=sys.stderr)
        return 1

    service = PredictionService(
        model_path=model_path,
        model_version=Config.MODEL_VERSION,
        conf_high=Config.CONFIDENCE_HIGH,
        conf_medium=Config.CONFIDENCE_MEDIUM,
    )

    if not service.is_loaded:
        print("ERROR: the model failed to load.", file=sys.stderr)
        return 1

    result = validate_model(service)
    print(f"\nModel: {model_path}")
    print(f"Architecture: MobileNetV3-Small | classes: {len(service.LABELS) if hasattr(service, 'LABELS') else 3}")
    print("Checks:")
    for ch in result["checks"]:
        status = "PASS" if ch["passed"] else "FAIL"
        print(f"  [{status}] {ch['check']} — {ch['detail']}")
    if result["probabilities"] is not None:
        print("Visualisation input softmax:", [round(float(v), 4) for v in result["probabilities"]])
        print(f"Argmax prediction: {result['prediction']}")

    if not result["valid"]:
        print("\nRESULT: FAIL — the model artifact did not pass validation.", file=sys.stderr)
        return 1
    print("\nRESULT: PASS — model is real, loads, and produces valid 3-class probabilities.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())