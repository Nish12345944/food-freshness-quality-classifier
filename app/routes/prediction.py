import logging
import os

from flask import (
    Blueprint, current_app, flash, jsonify, redirect,
    render_template, request, send_file, session, url_for,
)
from flask_login import current_user, login_required

from app import db
from app.models.analysis import Analysis
from app.services.image_service import (
    check_image_quality, detect_food_type, validate_and_save,
)
from app.services.prediction_service import get_prediction_service
from app.utils.security import limiter

logger = logging.getLogger(__name__)
prediction_bp = Blueprint("prediction", __name__)

# Storage tips data (kept here — used only for display, not for prediction)
STORAGE_TIPS = {
    "fruit": {"temperature": "35-45°F (2-7°C)", "humidity": "85-95%", "shelf_life": "3-7 days",
              "tips": ["Store in refrigerator crisper", "Wash before eating, not before storing"]},
    "vegetable": {"temperature": "32-40°F (0-4°C)", "humidity": "90-95%", "shelf_life": "5-10 days",
                  "tips": ["Store in refrigerator crisper", "Remove any damaged pieces"]},
    "meat": {"temperature": "32-40°F (0-4°C)", "humidity": "80-85%", "shelf_life": "1-3 days",
             "tips": ["Store in coldest part of fridge", "Use within 2 days or freeze"]},
    "dairy": {"temperature": "35-40°F (2-4°C)", "humidity": "80-85%", "shelf_life": "5-14 days",
              "tips": ["Keep refrigerated at all times", "Check expiration dates"]},
    "cooked_food": {"temperature": "35-40°F (2-4°C)", "humidity": "70-80%", "shelf_life": "2-4 days",
                    "tips": ["Refrigerate within 2 hours of cooking", "Store in airtight containers"]},
    "bread": {"temperature": "68-72°F (20-22°C)", "humidity": "60-70%", "shelf_life": "3-7 days",
              "tips": ["Store in cool, dry place", "Freeze for longer storage"]},
    "seafood": {"temperature": "32-38°F (0-3°C)", "humidity": "95-100%", "shelf_life": "1-2 days",
                "tips": ["Store on ice in refrigerator", "Use immediately or freeze"]},
    "eggs": {"temperature": "35-40°F (2-4°C)", "humidity": "70-80%", "shelf_life": "3-5 weeks",
             "tips": ["Store in refrigerator", "Keep in original carton"]},
}


def get_storage_tips(food_type: str) -> dict:
    return STORAGE_TIPS.get(food_type, STORAGE_TIPS["fruit"])


# ---------------------------------------------------------------------------
# Demo mode (no login required — uses real production pipeline)
# ---------------------------------------------------------------------------

DEMO_SAMPLES = [
    {"id": "apple", "label": "Apple", "icon": "fa-apple-alt", "description": "Fresh red apple"},
    {"id": "banana", "label": "Banana", "icon": "fa-lemon", "description": "Ripe banana"},
    {"id": "tomato", "label": "Tomato", "icon": "fa-seedling", "description": "Fresh tomato"},
    {"id": "bread", "label": "Bread", "icon": "fa-bread-slice", "description": "Sliced bread"},
]


@prediction_bp.route("/demo")
def demo():
    """Demo page — visitors can try sample images without registering."""
    svc = get_prediction_service()
    return render_template(
        "demo.html",
        samples=DEMO_SAMPLES,
        model_loaded=svc.is_loaded,
    )


@prediction_bp.route("/demo/predict", methods=["POST"])
@limiter.limit("10 per hour;3 per minute")
def demo_predict():
    """Run a real prediction on a demo image (no login required)."""
    svc = get_prediction_service()
    if not svc.is_loaded:
        return jsonify({
            "success": False,
            "error": "The AI model is not loaded yet. Please try again later.",
        }), 503

    file = request.files.get("image")
    if not file or file.filename == "":
        return jsonify({"success": False, "error": "No image provided."}), 400

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    val = validate_and_save(file, upload_folder)
    if not val.valid:
        logger.warning("Demo upload rejected: %s", val.error)
        return jsonify({"success": False, "error": val.error}), 422

    quality = check_image_quality(val.filepath)
    if not quality.passed:
        logger.info("Demo quality gate failed: %s", quality.reason)
        os.remove(val.filepath)
        return jsonify({"success": False, "error": quality.reason}), 422

    food_type = detect_food_type(val.filepath)

    try:
        pred = svc.predict(val.filepath)
    except Exception:
        logger.exception("Demo inference failed")
        os.remove(val.filepath)
        return jsonify({"success": False, "error": "Prediction failed. Please try again."}), 500

    # Clean up demo image after inference (not persisted to history)
    try:
        os.remove(val.filepath)
    except OSError:
        pass

    return jsonify({
        "success": True,
        "prediction": pred.label,
        "confidence": round(pred.confidence * 100, 1),
        "confidence_level": pred.confidence_level,
        "low_confidence_warning": pred.low_confidence_warning,
        "probabilities": {k: round(v * 100, 1) for k, v in pred.probabilities.items()},
        "food_type": food_type,
        "quality": {
            "quality_label": quality.quality_label,
            "resolution": quality.resolution,
            "blur_score": round(quality.blur_score, 1),
        },
        "model_version": pred.model_version,
        "inference_ms": round(pred.inference_ms, 1),
    })


# ---------------------------------------------------------------------------
# History page
# ---------------------------------------------------------------------------

@prediction_bp.route("/history")
@login_required
def history():
    """User's analysis history with search and filters."""
    from flask import request as _request

    page = max(1, _request.args.get("page", 1, type=int))
    per_page = 20
    label_filter = _request.args.get("label", "")
    search = _request.args.get("q", "").strip()

    query = Analysis.query.filter_by(user_id=current_user.id)
    if label_filter in ("Fresh", "Okay", "Avoid"):
        query = query.filter_by(label=label_filter)
    if search:
        query = query.filter(Analysis.food_type.ilike(f"%{search}%"))

    pagination = query.order_by(Analysis.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template(
        "history.html",
        analyses=pagination.items,
        page=pagination.page,
        total_pages=pagination.pages or 1,
        total=pagination.total,
        label_filter=label_filter,
        search=search,
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@prediction_bp.route("/dashboard")
@login_required
def dashboard():
    from camera import check_camera_availability
    camera_available = check_camera_availability()
    recent = (
        Analysis.query.filter_by(user_id=current_user.id)
        .order_by(Analysis.timestamp.desc())
        .limit(5)
        .all()
    )
    svc = get_prediction_service()
    return render_template(
        "dashboard.html",
        camera_available=camera_available,
        recent_analyses=recent,
        model_loaded=svc.is_loaded,
    )


# ---------------------------------------------------------------------------
# Predict (batch upload)
# ---------------------------------------------------------------------------

@prediction_bp.route("/predict", methods=["POST"])
@login_required
@limiter.limit("30 per hour;5 per minute")
def predict():
    svc = get_prediction_service()
    if not svc.is_loaded:
        flash("The ML model is not loaded. Please contact the administrator.", "error")
        return redirect(url_for("prediction.dashboard"))

    files = request.files.getlist("images")
    if not files or files[0].filename == "":
        flash("No image file selected.", "error")
        return redirect(url_for("prediction.dashboard"))

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    max_batch = current_app.config["MAX_BATCH_SIZE"]
    results = []

    for file in files[:max_batch]:
        # 1. Validate & save
        val = validate_and_save(file, upload_folder)
        if not val.valid:
            logger.warning("Upload rejected: %s", val.error)
            flash(f"File rejected: {val.error}", "warning")
            continue

        # 2. Quality gate
        quality = check_image_quality(val.filepath)
        if not quality.passed:
            logger.info("Quality gate failed for %s: %s", val.filename, quality.reason)
            flash(f"Image quality issue: {quality.reason}", "warning")
            os.remove(val.filepath)
            continue

        # 3. Food type (for storage tips only)
        food_type = detect_food_type(val.filepath)

        # 4. Real ML inference
        try:
            pred = svc.predict(val.filepath)
        except Exception:
            logger.exception("Inference failed for %s", val.filename)
            flash("Inference failed for one image. Please try again.", "error")
            continue

        # 5. Persist
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
        db.session.flush()  # get id before commit

        results.append({
            "id": analysis.id,
            "filename": val.filename,
            "label": pred.label,
            "confidence": pred.confidence,
            "confidence_level": pred.confidence_level,
            "low_confidence_warning": pred.low_confidence_warning,
            "probabilities": pred.probabilities,
            "food_type": food_type,
            "quality": {
                "quality": quality.quality_label,
                "resolution": quality.resolution,
                "blur_score": quality.blur_score,
            },
        })

    db.session.commit()

    if not results:
        flash("No images were successfully processed.", "error")
        return redirect(url_for("prediction.dashboard"))

    if len(results) == 1:
        return redirect(url_for("prediction.result", analysis_id=results[0]["id"]))

    session["batch_results"] = results
    return redirect(url_for("prediction.batch_results"))


# ---------------------------------------------------------------------------
# Camera capture
# ---------------------------------------------------------------------------

@prediction_bp.route("/capture-camera", methods=["POST"])
@login_required
@limiter.limit("20 per hour")
def capture_camera():
    svc = get_prediction_service()
    if not svc.is_loaded:
        flash("The ML model is not loaded.", "error")
        return redirect(url_for("prediction.dashboard"))

    upload_folder = current_app.config["UPLOAD_FOLDER"]

    if "camera_image" in request.files:
        file = request.files["camera_image"]
        val = validate_and_save(file, upload_folder)
        if not val.valid:
            flash(f"Camera image rejected: {val.error}", "error")
            return redirect(url_for("prediction.dashboard"))
        filepath, filename = val.filepath, val.filename
    else:
        try:
            from camera import capture_image
            filepath, filename = capture_image(upload_folder)
        except Exception:
            logger.exception("Camera capture failed")
            flash("Camera capture failed.", "error")
            return redirect(url_for("prediction.dashboard"))

    quality = check_image_quality(filepath)
    if not quality.passed:
        flash(f"Image quality issue: {quality.reason}", "warning")
        os.remove(filepath)
        return redirect(url_for("prediction.dashboard"))

    food_type = detect_food_type(filepath)

    try:
        pred = svc.predict(filepath)
    except Exception:
        logger.exception("Inference failed for camera image")
        flash("Inference failed. Please try again.", "error")
        return redirect(url_for("prediction.dashboard"))

    analysis = Analysis(
        user_id=current_user.id,
        image_filename=filename,
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
    return redirect(url_for("prediction.result", analysis_id=analysis.id))


# ---------------------------------------------------------------------------
# Result pages
# ---------------------------------------------------------------------------

@prediction_bp.route("/batch-results")
@login_required
def batch_results():
    results = session.get("batch_results", [])
    if not results:
        flash("No results found.", "error")
        return redirect(url_for("prediction.dashboard"))
    return render_template("batch_results.html", results=results)


@prediction_bp.route("/result/<int:analysis_id>")
@login_required
def result(analysis_id):
    analysis = db.get_or_404(Analysis, analysis_id)
    if analysis.user_id != current_user.id:
        logger.warning(
            "User %s attempted to access analysis %s owned by user %s",
            current_user.id, analysis_id, analysis.user_id,
        )
        flash("You do not have permission to view this analysis.", "error")
        return redirect(url_for("prediction.dashboard"))

    storage_tips = get_storage_tips(analysis.food_type)
    return render_template("result.html", analysis=analysis, storage_tips=storage_tips)


# ---------------------------------------------------------------------------
# PDF download
# ---------------------------------------------------------------------------

@prediction_bp.route("/download-pdf/<int:analysis_id>")
@login_required
def download_pdf(analysis_id):
    analysis = db.get_or_404(Analysis, analysis_id)
    if analysis.user_id != current_user.id:
        flash("Unauthorized.", "error")
        return redirect(url_for("prediction.dashboard"))

    from app.services.report_service import build_analysis_data, generate_pdf
    storage_tips = get_storage_tips(analysis.food_type)
    data = build_analysis_data(analysis, storage_tips, current_app.config["UPLOAD_FOLDER"])
    pdf_path = generate_pdf(data, current_app.config["REPORTS_FOLDER"])

    if pdf_path:
        return send_file(pdf_path, as_attachment=True, download_name=f"report_{analysis.id}.pdf")
    flash("PDF generation failed.", "error")
    return redirect(url_for("prediction.result", analysis_id=analysis_id))


# ---------------------------------------------------------------------------
# Email report
# ---------------------------------------------------------------------------

@prediction_bp.route("/email-report/<int:analysis_id>", methods=["POST"])
@login_required
def email_report(analysis_id):
    analysis = db.get_or_404(Analysis, analysis_id)
    if analysis.user_id != current_user.id:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    recipient = request.form.get("email") or current_user.email
    if not recipient:
        return jsonify({"success": False, "error": "No email address provided."}), 400

    from app.services.report_service import build_analysis_data, generate_pdf, send_report_email
    storage_tips = get_storage_tips(analysis.food_type)
    data = build_analysis_data(analysis, storage_tips, current_app.config["UPLOAD_FOLDER"])
    pdf_path = generate_pdf(data, current_app.config["REPORTS_FOLDER"])

    if send_report_email(recipient, data, pdf_path):
        return jsonify({"success": True, "message": "Email sent successfully!"})
    return jsonify({"success": False, "error": "Failed to send email."}), 500
