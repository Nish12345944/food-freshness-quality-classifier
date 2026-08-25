import logging

from flask import Blueprint, current_app, jsonify
from flask_login import current_user, login_required

from app.models.analysis import Analysis
from app.services.prediction_service import get_prediction_service

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/health")
def health():
    """Health check — does not perform inference."""
    svc = get_prediction_service()
    db_ok = _check_db()
    status = "healthy" if svc.is_loaded and db_ok else "degraded"
    return jsonify({
        "status": status,
        "model_loaded": svc.is_loaded,
        "model_version": svc.model_version,
        "database": "connected" if db_ok else "error",
        "version": current_app.config.get("APP_VERSION", "unknown"),
    }), 200 if status == "healthy" else 503


@api_bp.route("/history")
@login_required
def history():
    analyses = (
        Analysis.query.filter_by(user_id=current_user.id)
        .order_by(Analysis.timestamp.desc())
        .limit(20)
        .all()
    )
    return jsonify([a.to_dict() for a in analyses])


def _check_db() -> bool:
    try:
        from app import db
        db.session.execute(db.text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False
