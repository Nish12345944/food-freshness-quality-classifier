import json
import logging
from datetime import datetime, timedelta

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.models.analysis import Analysis

logger = logging.getLogger(__name__)
analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/analytics")
@login_required
def analytics():
    analyses = Analysis.query.filter_by(user_id=current_user.id).all()
    total = len(analyses)
    fresh = sum(1 for a in analyses if a.label == "Fresh")
    okay = sum(1 for a in analyses if a.label == "Okay")
    avoid = sum(1 for a in analyses if a.label == "Avoid")

    cutoff = datetime.utcnow() - timedelta(days=30)
    recent = [a for a in analyses if a.timestamp >= cutoff]

    daily_stats: dict = {}
    for a in recent:
        key = a.timestamp.strftime("%Y-%m-%d")
        daily_stats.setdefault(key, {"Fresh": 0, "Okay": 0, "Avoid": 0})
        daily_stats[key][a.label] += 1

    food_type_stats: dict = {}
    for a in analyses:
        ft = a.food_type or "unknown"
        food_type_stats[ft] = food_type_stats.get(ft, 0) + 1

    return render_template(
        "analytics.html",
        total=total,
        fresh=fresh,
        okay=okay,
        avoid=avoid,
        daily_stats=json.dumps(daily_stats),
        food_type_stats=json.dumps(food_type_stats),
    )
