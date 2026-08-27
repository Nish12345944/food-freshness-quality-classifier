"""
Prediction service: MobileNetV3-Small transfer-learning model.

Model loading happens once at startup.  Inference is deterministic and
confidence values come directly from softmax probabilities — no random
values, no HSV heuristics as the primary classifier.

If no trained model file exists the service falls back to a clearly-labelled
"model not loaded" state so the application still starts and the /health
endpoint reports the truth.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

logger = logging.getLogger(__name__)

LABELS = ["Fresh", "Okay", "Avoid"]
NUM_CLASSES = len(LABELS)

# ImageNet normalisation — same stats used during training
_TRANSFORM = transforms.Compose(
    [
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)


def build_model() -> nn.Module:
    """Return MobileNetV3-Small with a 3-class head."""
    model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    # Replace the classifier head
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, NUM_CLASSES)
    return model


@dataclass
class PredictionResult:
    label: str
    confidence: float          # 0.0 – 1.0
    confidence_level: str      # High / Medium / Low
    probabilities: dict        # {label: prob}
    inference_ms: float
    model_version: str
    low_confidence_warning: bool


class PredictionService:
    def __init__(self, model_path: str, model_version: str, conf_high: float, conf_medium: float):
        self.model_path = model_path
        self.model_version = model_version
        self.conf_high = conf_high
        self.conf_medium = conf_medium
        self.input_size = 224
        self._model: Optional[nn.Module] = None
        self._loaded = False
        self._load_model()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def model(self) -> Optional[nn.Module]:
        """Access the underlying nn.Module (used by Grad-CAM explainability)."""
        if not self._loaded:
            raise RuntimeError("Model is not loaded.")
        return self._model

    def predict(self, image_path: str) -> PredictionResult:
        if not self._loaded:
            raise RuntimeError("Model is not loaded. Train and export a model first.")

        t0 = time.perf_counter()
        tensor = self._preprocess(image_path)
        with torch.no_grad():
            logits = self._model(tensor)
            probs = torch.softmax(logits, dim=1).squeeze().cpu().numpy()

        inference_ms = (time.perf_counter() - t0) * 1000
        idx = int(np.argmax(probs))
        label = LABELS[idx]
        confidence = float(probs[idx])
        confidence_level = self._confidence_level(confidence)

        logger.info(
            "Prediction: %s (%.1f%%) [%s] in %.1fms",
            label,
            confidence * 100,
            confidence_level,
            inference_ms,
        )

        return PredictionResult(
            label=label,
            confidence=confidence,
            confidence_level=confidence_level,
            probabilities={LABELS[i]: float(probs[i]) for i in range(NUM_CLASSES)},
            inference_ms=inference_ms,
            model_version=self.model_version,
            low_confidence_warning=(confidence_level == "Low"),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        if not os.path.exists(self.model_path):
            logger.warning(
                "Model file not found at '%s'. "
                "Run training/train.py to generate it. "
                "Prediction endpoints will be unavailable until the model is present.",
                self.model_path,
            )
            return

        try:
            model = build_model()
            state = torch.load(self.model_path, map_location="cpu", weights_only=True)
            model.load_state_dict(state)
            model.eval()
            self._model = model
            self._loaded = True
            logger.info("Model loaded from '%s' (version %s)", self.model_path, self.model_version)
        except Exception:
            logger.exception("Failed to load model from '%s'", self.model_path)

    def _preprocess(self, image_path: str) -> torch.Tensor:
        img = Image.open(image_path).convert("RGB")
        return _TRANSFORM(img).unsqueeze(0)

    def _confidence_level(self, confidence: float) -> str:
        if confidence >= self.conf_high:
            return "High"
        if confidence >= self.conf_medium:
            return "Medium"
        return "Low"


# Module-level singleton — initialised by the Flask app factory
_service: Optional[PredictionService] = None


def init_prediction_service(app) -> None:
    global _service

    cfg = app.config

    model_enabled = cfg.get("MODEL_ENABLED", True)

    if not model_enabled:
        logger.info(
            "Model loading disabled by configuration."
        )

        _service = PredictionService.__new__(
            PredictionService
        )

        _service.model_path = cfg["MODEL_PATH"]
        _service.model_version = cfg["MODEL_VERSION"]
        _service.conf_high = cfg["CONFIDENCE_HIGH"]
        _service.conf_medium = cfg["CONFIDENCE_MEDIUM"]
        _service.input_size = 224
        _service._model = None
        _service._loaded = False

    else:
        _service = PredictionService(
            model_path=cfg["MODEL_PATH"],
            model_version=cfg["MODEL_VERSION"],
            conf_high=cfg["CONFIDENCE_HIGH"],
            conf_medium=cfg["CONFIDENCE_MEDIUM"],
        )

    app.extensions["prediction_service"] = _service


def get_prediction_service() -> PredictionService:
    if _service is None:
        raise RuntimeError("PredictionService not initialised. Call init_prediction_service() first.")
    return _service
