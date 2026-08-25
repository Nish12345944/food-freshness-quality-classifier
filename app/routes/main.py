"""Main routes: landing page, privacy policy."""
import logging

from flask import Blueprint, render_template
from flask_login import current_user

logger = logging.getLogger(__name__)
main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def landing():
    """Product landing page."""
    if current_user.is_authenticated:
        from flask import redirect, url_for
        return redirect(url_for("prediction.dashboard"))
    return render_template("landing.html")


@main_bp.route("/privacy")
def privacy():
    """Privacy policy page."""
    return render_template("privacy.html")