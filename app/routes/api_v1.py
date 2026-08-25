"""Versioned public API: /api/v1/"""
import logging

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from app import db
from app.models.analysis import Analysis
from app.services.image_service import (
    check_image_quality, detect_food_type, validate_and_save,
)
from app.services.prediction_service import get_prediction_service
from app.utils.security import limiter

logger = logging.getLogger(__name__)
api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def _ok(data, status=200):
    return jsonify({"success": True, "data": data}), status


def _err(message, status=400):
    return jsonify({"success": False, "error": message}), status


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@api_v1_bp.route("/health")
def health():
    """API health check — no inference performed."""
    svc = get_prediction_service()
    db_ok = _check_db()
    healthy = svc.is_loaded and db_ok
    return jsonify({
        "success": True,
        "data": {
            "status": "healthy" if healthy else "degraded",
            "model_loaded": svc.is_loaded,
            "model_version": svc.model_version,
            "database": "connected" if db_ok else "error",
            "version": current_app.config.get("APP_VERSION", "unknown"),
        },
    }), 200 if healthy else 503


# ---------------------------------------------------------------------------
# Predict (single image)
# ---------------------------------------------------------------------------

@api_v1_bp.route("/predict", methods=["POST"])
@login_required
@limiter.limit("30 per hour;5 per minute")
def predict():
    """Predict freshness for a single uploaded image."""
    # Validate input first so malformed requests always get 400
    file = request.files.get("image")
    if not file or file.filename == "":
        return _err("No image provided. Send a multipart/form-data 'image' field.", 400)

    svc = get_prediction_service()
    if not svc.is_loaded:
        return _err("Model is not loaded.", 503)

    val = validate_and_save(file, current_app.config["UPLOAD_FOLDER"])
    if not val.valid:
        logger.warning("API upload rejected: %s", val.error)
        return _err(val.error, 422)

    quality = check_image_quality(val.filepath)
    if not quality.passed:
        logger.info("API quality gate failed: %s", quality.reason)
        import os
        os.remove(val.filepath)
        return _err(quality.reason, 422)

    food_type = detect_food_type(val.filepath)

    try:
        pred = svc.predict(val.filepath)
    except Exception:
        logger.exception("API inference failed")
        import os
        os.remove(val.filepath)
        return _err("Prediction failed. Please try again.", 500)

    # Persist for logged-in users
    analysis = Analysis(
        user_id=current_user.id,
        image_filename=val.filename,
        label=pred.label,
        confidence=pred.confidence,
        confidence_level=pred.confidence_level,
        food_type=food_type,
        resolution=quality.resolution,
        blur_score=quality.blur_score,
        inference_ms=pred.inference_ms,
        model_version=pred.model_version,
    )
    db.session.add(analysis)
    db.session.commit()

    return _ok({
        "analysis_id": analysis.id,
        "prediction": pred.label,
        "confidence": round(pred.confidence, 3),
        "confidence_level": pred.confidence_level,
        "low_confidence_warning": pred.low_confidence_warning,
        "probabilities": {k: round(v, 3) for k, v in pred.probabilities.items()},
        "food_type": food_type,
        "model_version": pred.model_version,
        "inference_time_ms": round(pred.inference_ms, 1),
        "quality": {
            "quality_label": quality.quality_label,
            "resolution": quality.resolution,
            "blur_score": round(quality.blur_score, 1),
        },
    })


# ---------------------------------------------------------------------------
# Predict (batch)
# ---------------------------------------------------------------------------

@api_v1_bp.route("/predict/batch", methods=["POST"])
@login_required
@limiter.limit("10 per hour;2 per minute")
def predict_batch():
    """Predict freshness for multiple images in one request."""
    files = request.files.getlist("images")
    if not files or files[0].filename == "":
        return _err("No images provided. Send a multipart/form-data 'images' field.", 400)

    svc = get_prediction_service()
    if not svc.is_loaded:
        return _err("Model is not loaded.", 503)

    max_batch = current_app.config["MAX_BATCH_SIZE"]
    results = []
    errors = []

    import os
    for file in files[:max_batch]:
        val = validate_and_save(file, current_app.config["UPLOAD_FOLDER"])
        if not val.valid:
            errors.append({"filename": file.filename, "error": val.error})
            continue

        quality = check_image_quality(val.filepath)
        if not quality.passed:
            os.remove(val.filepath)
            errors.append({"filename": file.filename, "error": quality.reason})
            continue

        food_type = detect_food_type(val.filepath)
        try:
            pred = svc.predict(val.filepath)
        except Exception:
            logger.exception("Batch inference failed for %s", val.filename)
            os.remove(val.filepath)
            errors.append({"filename": file.filename, "error": "Prediction failed."})
            continue

        analysis = Analysis(
            user_id=current_user.id,
            image_filename=val.filename,
            label=pred.label,
            confidence=pred.confidence,
            confidence_level=pred.confidence_level,
            food_type=food_type,
            resolution=quality.resolution,
            blur_score=quality.blur_score,
            inference_ms=pred.inference_ms,
            model_version=pred.model_version,
        )
        db.session.add(analysis)
        db.session.flush()

        results.append({
            "analysis_id": analysis.id,
            "prediction": pred.label,
            "confidence": round(pred.confidence, 3),
            "confidence_level": pred.confidence_level,
            "low_confidence_warning": pred.low_confidence_warning,
            "probabilities": {k: round(v, 3) for k, v in pred.probabilities.items()},
            "food_type": food_type,
            "model_version": pred.model_version,
            "inference_time_ms": round(pred.inference_ms, 1),
            "quality": {
                "quality_label": quality.quality_label,
                "resolution": quality.resolution,
                "blur_score": round(quality.blur_score, 1),
            },
        })

    db.session.commit()

    if not results and errors:
        return _err("All images failed processing.", 422)

    return _ok({
        "results": results,
        "errors": errors,
        "total_processed": len(results),
        "total_failed": len(errors),
    })


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@api_v1_bp.route("/history")
@login_required
def history():
    """Get the current user's analysis history."""
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(50, max(1, request.args.get("per_page", 20, type=int)))
    label_filter = request.args.get("label", "")

    query = Analysis.query.filter_by(user_id=current_user.id)
    if label_filter in ("Fresh", "Okay", "Avoid"):
        query = query.filter_by(label=label_filter)

    pagination = query.order_by(Analysis.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return _ok({
        "analyses": [a.to_dict() for a in pagination.items],
        "page": pagination.page,
        "total_pages": pagination.pages or 1,
        "total": pagination.total,
    })


# ---------------------------------------------------------------------------
# Single analysis
# ---------------------------------------------------------------------------

@api_v1_bp.route("/analysis/<int:analysis_id>")
@login_required
def get_analysis(analysis_id):
    """Get a single analysis by ID (owner only)."""
    analysis = db.get_or_404(Analysis, analysis_id)
    if analysis.user_id != current_user.id:
        logger.warning(
            "User %s attempted to access analysis %s owned by user %s via API",
            current_user.id, analysis_id, analysis.user_id,
        )
        return _err("You do not have permission to view this analysis.", 403)
    return _ok(analysis.to_dict())


# ---------------------------------------------------------------------------
# Explainability (Grad-CAM)
# ---------------------------------------------------------------------------

@api_v1_bp.route("/explain/<int:analysis_id>")
@login_required
@limiter.limit("20 per hour")
def explain(analysis_id):
    """Generate a Grad-CAM heatmap for an analysis (owner only)."""
    import os

    analysis = db.get_or_404(Analysis, analysis_id)
    if analysis.user_id != current_user.id:
        logger.warning(
            "User %s attempted to explain analysis %s owned by user %s",
            current_user.id, analysis_id, analysis.user_id,
        )
        return _err("You do not have permission to view this analysis.", 403)

    svc = get_prediction_service()
    if not svc.is_loaded:
        return _err("Model is not loaded.", 503)

    from app.services.image_service import generate_gradcam_overlay
    from app.services.prediction_service import LABELS

    image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], analysis.image_filename)
    if not os.path.exists(image_path):
        return _err("Original image file no longer exists.", 404)

    class_idx = LABELS.index(analysis.label) if analysis.label in LABELS else 0
    output_dir = os.path.join(current_app.static_folder, "gradcam")
    output_name = f"gradcam_{analysis.id}.png"
    output_path = os.path.join(output_dir, output_name)

    ok = generate_gradcam_overlay(svc.model, image_path, class_idx, output_path)
    if not ok:
        return _err("Could not generate the explanation heatmap.", 500)

    return _ok({
        "image_url": f"/static/gradcam/{output_name}",
        "note": (
            "Grad-CAM shows where the model focused its attention. "
            "It does not prove causality."
        ),
    })


def _check_db() -> bool:
    try:
        from app import db as _db
        _db.session.execute(_db.text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False