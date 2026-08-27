"""Startup validation for the production prediction model."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def _record(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    detail: str,
) -> bool:
    """Record one validation check and return its boolean result."""
    checks.append(
        {
            "check": name,
            "passed": bool(passed),
            "detail": detail,
        }
    )
    return bool(passed)


def validate_model(prediction_service) -> dict[str, Any]:
    """Run a lightweight inference smoke test against the loaded model."""

    checks: list[dict[str, Any]] = []
    valid = True

    # ---------------------------------------------------------
    # Model loaded
    # ---------------------------------------------------------

    loaded = bool(prediction_service.is_loaded)

    valid &= _record(
        checks,
        "model_loaded",
        loaded,
        "prediction service reports loaded",
    )

    if not loaded:
        return {
            "valid": False,
            "checks": checks,
        }

    # ---------------------------------------------------------
    # Model metadata
    # ---------------------------------------------------------

    model = prediction_service.model

    valid &= _record(
        checks,
        "model_available",
        model is not None,
        "model object is available",
    )

    if model is None:
        return {
            "valid": False,
            "checks": checks,
        }

    # ---------------------------------------------------------
    # Dummy inference
    # ---------------------------------------------------------

    try:
        import torch

        input_size = getattr(
            prediction_service,
            "input_size",
            224,
        )

        dummy = torch.zeros(
            1,
            3,
            input_size,
            input_size,
        )

        device = next(model.parameters()).device
        dummy = dummy.to(device)

        with torch.no_grad():
            output = model(dummy)

        valid &= _record(
            checks,
            "inference_success",
            output is not None,
            "dummy inference completed",
        )

        # -----------------------------------------------------
        # Output shape
        # -----------------------------------------------------

        shape_ok = (
            hasattr(output, "shape")
            and len(output.shape) == 2
            and output.shape[0] == 1
        )

        valid &= _record(
            checks,
            "output_shape",
            shape_ok,
            f"shape={getattr(output, 'shape', None)}",
        )

        if not shape_ok:
            return {
                "valid": False,
                "checks": checks,
            }

        # -----------------------------------------------------
        # Probabilities
        # -----------------------------------------------------

        probabilities = torch.softmax(output, dim=1)

        probs = probabilities.detach().cpu().numpy()[0]

        finite_ok = bool(np.isfinite(probs).all())

        valid &= _record(
            checks,
            "probabilities_finite",
            finite_ok,
            f"values={probs.tolist()}",
        )

        nonnegative_ok = bool((probs >= 0).all())

        valid &= _record(
            checks,
            "probabilities_nonnegative",
            nonnegative_ok,
            "all probabilities >= 0",
        )

        within_range_ok = bool((probs <= 1).all())

        valid &= _record(
            checks,
            "probabilities_range",
            within_range_ok,
            "all probabilities <= 1",
        )

        prob_sum = float(probs.sum())

        sum_ok = abs(prob_sum - 1.0) < 1e-5

        valid &= _record(
            checks,
            "probabilities_sum",
            sum_ok,
            f"sum={prob_sum:.6f}",
        )

        # -----------------------------------------------------
        # Prediction
        # -----------------------------------------------------

        predicted_index = int(np.argmax(probs))

        num_classes = int(probs.shape[0])

        prediction_ok = (
            num_classes > 0
            and 0 <= predicted_index < num_classes
        )

        valid &= _record(
            checks,
            "prediction_index",
            prediction_ok,
            f"index={predicted_index}",
        )

    except Exception as exc:
        logger.exception("Model validation inference failed")

        valid &= _record(
            checks,
            "inference_success",
            False,
            f"{type(exc).__name__}: {exc}",
        )

    return {
        "valid": bool(valid),
        "checks": checks,
    }