import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.models.user import User
from app.utils.validators import validate_login, validate_registration

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("prediction.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        errors = validate_login(username, password)
        if errors:
            return render_template("auth.html", error=errors[0], is_register=False)

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            logger.info("User '%s' logged in", username)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("prediction.dashboard"))

        logger.warning("Failed login attempt for username '%s'", username)
        return render_template("auth.html", error="Invalid username or password.", is_register=False)

    return render_template("auth.html", is_register=False)


@auth_bp.route("/auth/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("prediction.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip() or None
        password = request.form.get("password", "")

        errors = validate_registration(username, email or "", password)
        if errors:
            return render_template("auth.html", error=errors[0], is_register=True)

        if User.query.filter_by(username=username).first():
            return render_template("auth.html", error="Username already taken.", is_register=True)
        if email and User.query.filter_by(email=email).first():
            return render_template("auth.html", error="Email already registered.", is_register=True)

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        logger.info("New user registered: '%s'", username)
        return render_template("auth.html", success="Registration successful! Please log in.", is_register=False)

    return render_template("auth.html", is_register=True)


@auth_bp.route("/logout")
@login_required
def logout():
    logger.info("User '%s' logged out", current_user.username)
    logout_user()
    return redirect(url_for("main.landing"))


@auth_bp.route("/profile")
@login_required
def profile():
    from app.models.analysis import Analysis
    total_analyses = Analysis.query.filter_by(user_id=current_user.id).count()
    return render_template("profile.html", total_analyses=total_analyses)


@auth_bp.route("/update-profile", methods=["POST"])
@login_required
def update_profile():
    import os, uuid
    from flask import current_app
    try:
        email = request.form.get("email", "").strip() or None
        if email:
            current_user.email = email

        if "profile_picture" in request.files:
            file = request.files["profile_picture"]
            if file and file.filename:
                from app.services.image_service import validate_and_save
                result = validate_and_save(file, current_app.config["PROFILES_FOLDER"])
                if result.valid:
                    current_user.profile_picture = result.filename

        db.session.commit()
        flash("Profile updated successfully!", "success")
    except Exception:
        logger.exception("Profile update failed for user %s", current_user.id)
        flash("Error updating profile.", "error")
    return redirect(url_for("auth.profile"))
