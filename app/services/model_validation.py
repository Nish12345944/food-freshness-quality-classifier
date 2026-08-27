"""Startup validation for the production prediction model."""

from __future__ import annotations

import logging
import os
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


def _result(
    valid: bool,
    checks: list[dict[str, Any]],
    probabilities=None,
    prediction=None,
) -> dict[str, Any]:
    """Build a consistent validation result."""
    return {
        "valid": bool(valid),
        "ready": bool(valid),
        "checks": checks,
        "probabilities": probabilities,
        "prediction": prediction,
    }


def validate_model(prediction_service) -> dict[str, Any]:
    """Run a lightweight inference smoke test against the loaded model."""

    checks: list[dict[str, Any]] = []
    valid = True

    probabilities = None
    prediction = None

    # ---------------------------------------------------------
    # Model file exists
    # ---------------------------------------------------------

    model_path = getattr(prediction_service, "model_path", None)

    model_file_exists = bool(
        model_path
        and os.path.isfile(str(model_path))
    )

    valid &= _record(
        checks,
        "model_file_exists",
        model_file_exists,
        f"path={model_path}",
    )

    if not model_file_exists:
        return _result(
            False,
            checks,
            probabilities,
            prediction,
        )

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
        return _result(
            False,
            checks,
            probabilities,
            prediction,
        )

    # ---------------------------------------------------------
    # Model available
    # ---------------------------------------------------------

    model = prediction_service.model

    model_available = model is not None

    valid &= _record(
        checks,
        "model_available",
        model_available,
        "model object is available",
    )

    if not model_available:
        return _result(
            False,
            checks,
            probabilities,
            prediction,
        )

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

        model.eval()

        with torch.no_grad():
            output = model(dummy)

        inference_ok = output is not None

        valid &= _record(
            checks,
            "inference_success",
            inference_ok,
            "dummy inference completed",
        )

        if not inference_ok:
            return _result(
                False,
                checks,
                probabilities,
                prediction,
            )

        # -----------------------------------------------------
        # Output shape
        # -----------------------------------------------------

        shape_ok = (
            hasattr(output, "shape")
            and len(output.shape) == 2
            and output.shape[0] == 1
            and output.shape[1] > 0
        )

        valid &= _record(
            checks,
            "output_shape",
            shape_ok,
            f"shape={getattr(output, 'shape', None)}",
        )

        if not shape_ok:
            return _result(
                False,
                checks,
                probabilities,
                prediction,
            )

        # -----------------------------------------------------
        # Probabilities
        # -----------------------------------------------------

        probability_tensor = torch.softmax(
            output,
            dim=1,
        )

        probs = (
            probability_tensor
            .detach()
            .cpu()
            .numpy()[0]
        )

        # Keep this as a NumPy array because the test suite
        # expects probabilities.sum() to be available.
        probabilities = probs

        finite_ok = bool(
            np.isfinite(probs).all()
        )

        valid &= _record(
            checks,
            "probabilities_finite",
            finite_ok,
            f"values={probs.tolist()}",
        )

        nonnegative_ok = bool(
            (probs >= 0).all()
        )

        valid &= _record(
            checks,
            "probabilities_nonnegative",
            nonnegative_ok,
            "all probabilities >= 0",
        )

        within_range_ok = bool(
            (probs <= 1).all()
        )

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

        predicted_index = int(
            np.argmax(probs)
        )

        labels = getattr(
            prediction_service,
            "classes",
            ["Fresh", "Okay", "Avoid"],
        )

        # Some implementations expose class labels through
        # a different attribute. Fall back safely.
        if not labels:
            labels = ["Fresh", "Okay", "Avoid"]

        if (
            0 <= predicted_index
            < len(labels)
        ):
            prediction = labels[predicted_index]
        else:
            prediction = None

        num_classes = int(
            probs.shape[0]
        )

        prediction_ok = (
            num_classes > 0
            and 0 <= predicted_index < num_classes
            and prediction in labels
        )

        valid &= _record(
            checks,
            "prediction_index",
            prediction_ok,
            f"index={predicted_index}",
        )

    except Exception as exc:
        logger.exception(
            "Model validation inference failed"
        )

        valid &= _record(
            checks,
            "inference_success",
            False,
            f"{type(exc).__name__}: {exc}",
        )

    return _result(
        valid,
        checks,
        probabilities,
        prediction,
    )


__all__ = [
    "validate_model",
]