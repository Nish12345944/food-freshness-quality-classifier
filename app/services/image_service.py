"""
Image service: validation, quality gate, food-type detection, Grad-CAM.

Quality checks are kept strictly separate from freshness prediction.
If an image fails the quality gate, inference is skipped and the user
is told to upload a clearer image.
"""

import logging
import os
import uuid
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_MIMES = {"image/png", "image/jpeg", "image/webp"}
MAX_FILE_BYTES = 16 * 1024 * 1024   # 16 MB
MIN_DIMENSION = 64                   # px
MAX_DIMENSION = 8000                 # px
BLUR_THRESHOLD = 30.0                # Laplacian variance
BRIGHTNESS_MIN = 20.0
BRIGHTNESS_MAX = 240.0


def _extension(filename: str) -> str:
    """Return the lowercased extension (without dot) of a filename."""
    return os.path.splitext(filename)[1].lstrip(".").lower()


@dataclass
class QualityReport:
    passed: bool
    reason: Optional[str]          # human-readable rejection reason
    resolution: str
    blur_score: float
    brightness: float
    quality_label: str             # Good / Fair / Poor


@dataclass
class ValidationResult:
    valid: bool
    error: Optional[str]
    filepath: Optional[str]
    filename: Optional[str]


# ---------------------------------------------------------------------------
# File validation & saving
# ---------------------------------------------------------------------------

def validate_and_save(file: FileStorage, upload_folder: str) -> ValidationResult:
    """Validate extension, MIME, size, decodability, then save with a random name."""
    if not file or file.filename == "":
        return ValidationResult(False, "No file selected.", None, None)

    ext = _extension(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        return ValidationResult(False, f"File type '.{ext}' is not allowed.", None, None)

    mime = file.mimetype or ""
    if mime and mime not in ALLOWED_MIMES:
        return ValidationResult(False, f"MIME type '{mime}' is not allowed.", None, None)

    # Read bytes for size + decode check
    data = file.read()
    if len(data) > MAX_FILE_BYTES:
        return ValidationResult(False, "File exceeds the 16 MB size limit.", None, None)
    if len(data) == 0:
        return ValidationResult(False, "Uploaded file is empty.", None, None)

    # Verify it is actually a decodable image
    try:
        import io
        img = Image.open(io.BytesIO(data))
        img.verify()
    except Exception:
        return ValidationResult(False, "File could not be decoded as an image.", None, None)

    # Save with randomised filename
    safe_base = secure_filename(os.path.splitext(file.filename)[0]) or "upload"
    filename = f"{safe_base}_{uuid.uuid4().hex[:8]}.{ext}"
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    with open(filepath, "wb") as f:
        f.write(data)

    return ValidationResult(True, None, filepath, filename)


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------

def check_image_quality(filepath: str) -> QualityReport:
    """Return a QualityReport.  If passed=False, inference should be skipped."""
    try:
        img_bgr = cv2.imread(filepath)
        if img_bgr is None:
            return QualityReport(False, "Image could not be read.", "unknown", 0.0, 0.0, "Poor")

        h, w = img_bgr.shape[:2]
        resolution = f"{w}x{h}"

        if w < MIN_DIMENSION or h < MIN_DIMENSION:
            return QualityReport(
                False,
                f"Image is too small ({resolution}). Minimum is {MIN_DIMENSION}px on each side.",
                resolution, 0.0, 0.0, "Poor",
            )
        if w > MAX_DIMENSION or h > MAX_DIMENSION:
            return QualityReport(
                False,
                f"Image is too large ({resolution}). Maximum is {MAX_DIMENSION}px on each side.",
                resolution, 0.0, 0.0, "Poor",
            )

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(np.mean(gray))

        if blur_score < BLUR_THRESHOLD:
            return QualityReport(
                False,
                "Image is too blurry. Please upload a sharper photo.",
                resolution, blur_score, brightness, "Poor",
            )
        if brightness < BRIGHTNESS_MIN:
            return QualityReport(
                False,
                "Image is too dark. Please use better lighting.",
                resolution, blur_score, brightness, "Poor",
            )
        if brightness > BRIGHTNESS_MAX:
            return QualityReport(
                False,
                "Image is overexposed. Please reduce lighting or glare.",
                resolution, blur_score, brightness, "Poor",
            )

        if blur_score > 100 and w >= 224 and h >= 224:
            quality_label = "Good"
        elif blur_score > BLUR_THRESHOLD:
            quality_label = "Fair"
        else:
            quality_label = "Poor"

        return QualityReport(True, None, resolution, blur_score, brightness, quality_label)

    except Exception:
        logger.exception("Quality check failed for %s", filepath)
        return QualityReport(False, "Quality check failed unexpectedly.", "unknown", 0.0, 0.0, "Poor")


# ---------------------------------------------------------------------------
# Food type detection (heuristic — used for storage tips only, not freshness)
# ---------------------------------------------------------------------------

_FOOD_TYPES = ["fruit", "vegetable", "meat", "dairy", "cooked_food", "bread", "seafood", "eggs"]

def detect_food_type(filepath: str) -> str:
    """Lightweight HSV heuristic to guess food category for storage tips."""
    try:
        img = cv2.imread(filepath)
        if img is None:
            return "fruit"
        h, w = img.shape[:2]
        if w > 320 or h > 320:
            scale = 320 / max(w, h)
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        total = hsv.shape[0] * hsv.shape[1]
        s_mean = float(np.mean(hsv[:, :, 1]))
        v_mean = float(np.mean(hsv[:, :, 2]))

        white_r = np.sum((hsv[:, :, 1] < 40) & (hsv[:, :, 2] > 120)) / total
        green_r = np.sum((hsv[:, :, 0] > 40) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] > 30)) / total
        brown_r = np.sum((hsv[:, :, 0] > 5) & (hsv[:, :, 0] < 35) & (hsv[:, :, 1] < 100) & (hsv[:, :, 2] > 40)) / total
        orange_r = np.sum((hsv[:, :, 0] > 10) & (hsv[:, :, 0] <= 40) & (hsv[:, :, 1] > 40)) / total

        if white_r > 0.50:
            return "dairy"
        if brown_r > 0.30 and s_mean < 50:
            return "bread"
        if green_r > 0.25:
            return "vegetable"
        if white_r > 0.25 and (orange_r > 0.15 or green_r > 0.10):
            return "cooked_food"
        if s_mean > 60 and v_mean > 100:
            return "fruit"
        return "cooked_food"
    except Exception:
        return "fruit"


# ---------------------------------------------------------------------------
# Grad-CAM
# ---------------------------------------------------------------------------

class GradCAM:
    """Grad-CAM for MobileNetV3-Small.  Targets the last conv layer."""

    def __init__(self, model: nn.Module):
        self._model = model
        self._gradients: Optional[torch.Tensor] = None
        self._activations: Optional[torch.Tensor] = None
        self._hook_handles = []
        self._register_hooks()

    def _register_hooks(self):
        # Last conv block in MobileNetV3-Small features
        target_layer = self._model.features[-1]

        def fwd_hook(_, __, output):
            self._activations = output.detach()

        def bwd_hook(_, __, grad_output):
            self._gradients = grad_output[0].detach()

        self._hook_handles.append(target_layer.register_forward_hook(fwd_hook))
        self._hook_handles.append(target_layer.register_full_backward_hook(bwd_hook))

    def generate(self, tensor: torch.Tensor, class_idx: int) -> np.ndarray:
        """Return a normalised heatmap (H×W float32 0–1)."""
        self._model.zero_grad()
        output = self._model(tensor)
        score = output[0, class_idx]
        score.backward()

        grads = self._gradients[0]          # C×H×W
        acts = self._activations[0]         # C×H×W
        weights = grads.mean(dim=(1, 2))    # C
        cam = torch.relu((weights[:, None, None] * acts).sum(dim=0))
        cam = cam.cpu().numpy()
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
        return cam.astype(np.float32)

    def remove_hooks(self):
        for h in self._hook_handles:
            h.remove()


def generate_gradcam_overlay(
    model: nn.Module,
    image_path: str,
    class_idx: int,
    output_path: str,
) -> bool:
    """
    Save a Grad-CAM overlay image.  Returns True on success.
    The overlay shows where the model attended — it does NOT prove causality.
    """
    try:
        from torchvision import transforms
        transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        img_pil = Image.open(image_path).convert("RGB")
        tensor = transform(img_pil).unsqueeze(0)
        tensor.requires_grad_(True)

        cam_gen = GradCAM(model)
        cam = cam_gen.generate(tensor, class_idx)
        cam_gen.remove_hooks()

        # Resize cam to original image size
        orig = np.array(img_pil.resize((224, 224)))
        cam_resized = cv2.resize(cam, (224, 224))
        heatmap = cv2.applyColorMap(np.uint8(255 * cam_resized), cv2.COLORMAP_JET)
        heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
        overlay = (0.5 * orig + 0.5 * heatmap).astype(np.uint8)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        Image.fromarray(overlay).save(output_path)
        return True
    except Exception:
        logger.exception("Grad-CAM generation failed")
        return False
