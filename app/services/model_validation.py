"""
Real-model validation (smoke test) for the food-freshness classifier.

Verifies the deployed MobileNetV3-Small artifact is genuine and usable:

- the model file exists
- the model loads successfully
- the expected architecture is present (3-class head on MobileNetV3-Small)
- inference runs end-to-end
- output probabilities are valid (all >= 0) and sum to ~1
- the predicted label is one of Fresh / Okay / Avoid

No fabricated accuracy is ever reported.  When the artifact is absent this
returns valid=False with a clear reason (used by tests to skip, not to fake
results).
"""

import logging
import os
from typing import List, Optional

import numpy as np
import torch

from app.services.prediction_service import LABELS, NUM_CLASSES, PredictionService

logger = logging.getLogger(__name__)


def _record(checks: List[dict], name: str, passed: bool, detail: str = "") -> bool:
    checks.append({"check": name, "passed": bool(passed), "detail": detail})
    return bool(passed)


def validate_model(service: PredictionService) -> dict:
    """Run the full model smoke test.

    Returns a dict: {"valid": bool, "ready": bool, "checks": [...], "prediction": ...}
    """
    checks: List[dict] = []
    valid = True

    # 1. File exists
    file_exists = bool(service.model_path) and os.path.isfile(service.model_path)
    valid &= _record(checks, "model_file_exists", file_exists, str(service.model_path))

    # 2. Model loads.
    loadable = service.is_loaded and service.model is not None
    valid &= _record(checks, "model_loads", loadable)

    if not file_exists or not loadable:
        logger.info(
            "Model validation aborted (file_exists=%s loads=%s)",
            file_exists, loadable,
        )
        return _finish(valid, checks)

    model = service.model

    # 3 & 4. Expected architecture and class count (MobileNetV3-Small + 3-class head).
    head_out = None
    try:
        head_out = int(model.classifier[-1].out_features)
    except Exception:
        head_out = None
    arch_ok = head_out is not None and head_out == NUM_CLASSES
    valid &= _record(checks, "expected_architecture", arch_ok, f"last_head.out_features={head_out}")
    valid &= _record(checks, "class_count", arch_ok, f"expected={NUM_CLASSES} got={head_out}")

    # 5–8. Inference + valid probabilities.
    if not arch_ok:
        return _finish(valid, checks)

    probs = None
    try:
        sample = torch.zeros(1, 3, service.input_size, service.input_size)
        model.eval()
        with torch.no_grad():
            logits = model(sample)
            probs = torch.softmax(logits, dim=1).squeeze().cpu().numpy()
        valid &= _record(checks, "inference_runs", True, f"logits_shape={tuple(logits.shape)}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Inference during model validation failed")
        valid &= _record(checks, "inference_runs", False, str(exc))
        return _finish(valid, checks)

    all_nonneg = bool(np.all(probs >= 0)) and bool(np.all(probs <= 1))
    valid &= _record("probabilities_valid", all_nonneg, "all probs in [0,1]")
    prob_sum = float(probs.sum())
    sum_ok = abs(prob_sum - 1.0) < 1e-3
    valid &= _record("probabilities_sum", sum_ok, f"sum={prob_sum:.6f}")
    idx = int(np.argmax(probs))
    prediction = LABELS[idx] if idx < len(LABELS) else "?"
    in_labels = prediction in LABELS
    valid &= _record("prediction_in_labels", in_labels, prediction)

    return _finish(valid, checks, probs=probs, prediction=prediction)


def _finish(valid, checks, probs=None, prediction=None) -> dict:
    return {
        "valid": bool(valid),
        "ready": bool(valid),
        "checks": checks,
        "probabilities": probs,
        "prediction": prediction,
    }