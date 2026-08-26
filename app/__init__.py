from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from .config import Config
from .utils.logging_config import setup_logging

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config: Config = None) -> Flask:
    setup_logging()

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(config or Config())

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.prediction import prediction_bp
    from .routes.analytics import analytics_bp
    from .routes.api import api_bp
    from .routes.api_v1 import api_v1_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(api_v1_bp)

    # Error handlers
    from .utils.error_handlers import register_error_handlers
    register_error_handlers(app)

    # Security headers (applied after every request)
    from .utils.security_headers import register_security_headers
    register_security_headers(app)

    # Health endpoint (root-level, no prefix)
    from .routes.api import health
    app.add_url_rule("/health", "health", health)

    # Rate limiter (after routes are registered)
    from .utils.security import limiter
    limiter.enabled = True
    limiter.init_app(app)

    # ML prediction service (loads model once)
    from .services.prediction_service import init_prediction_service
    with app.app_context():
        db.create_all()
        _migrate_schema()
        init_prediction_service(app)
        _validate_model_on_startup(app)

    return app


def _validate_model_on_startup(app) -> None:
    """Log a real smoke-test of the model at boot; never blocks startup.

    The result is exposed via the /health endpoints as ``model_validated``.
    """
    import logging

    from .services.model_validation import validate_model
    from .services.prediction_service import get_prediction_service

    logger = logging.getLogger(__name__)
    svc = get_prediction_service()
    app.extensions["model_validated"] = None  # explicit "not validated" default
    if not svc.is_loaded:
        logger.info("No model loaded at startup — model validation skipped.")
        return
    try:
        result = validate_model(svc)
        app.extensions["model_validated"] = result
        logger.info(
            "Startup model smoke test: %s (valid=%s)",
            "PASS" if result.get("valid") else "FAIL",
            result.get("valid"),
        )
    except Exception:
        logger.exception("Startup model validation errored")
        app.extensions["model_validated"] = None


def _migrate_schema() -> None:
    """Safe, non-destructive migration for the legacy SQLite schema.

    The legacy auth.py User model stored plaintext passwords in a `password`
    column.  The refactored model uses `password_hash`.  db.create_all() does
    not alter existing tables, so we add the column and migrate existing
    plaintext values to hashes — without dropping or recreating the database.
    """
    import logging
    from sqlalchemy import inspect, text
    from werkzeug.security import generate_password_hash

    logger = logging.getLogger(__name__)
    inspector = inspect(db.engine)
    if "user" not in inspector.get_table_names():
        return

    columns = {c["name"] for c in inspector.get_columns("user")}
    has_password_hash = "password_hash" in columns
    has_legacy_password = "password" in columns

    # 1. Add password_hash if missing (first-time migration)
    if not has_password_hash:
        logger.info("Migrating legacy user table: adding password_hash column")
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE user ADD COLUMN password_hash VARCHAR(256)"))
        has_password_hash = True  # re-fetch so step 2+3 run in the same pass

    # 2. Migrate any plaintext passwords to hashes (idempotent — fills any NULLs)
    if has_password_hash and has_legacy_password:
        with db.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT id, password FROM user WHERE password IS NOT NULL AND password_hash IS NULL")
            ).fetchall()
            for user_id, plain in rows:
                if plain:
                    hashed = generate_password_hash(plain)
                    conn.execute(
                        text("UPDATE user SET password_hash = :h WHERE id = :i"),
                        {"h": hashed, "i": user_id},
                    )
        logger.info("Migrated %d existing user password(s) to hashed form", len(rows))

    # 3. Drop the legacy password column once its data is in password_hash.
    #    SQLite supports ALTER TABLE ... DROP COLUMN from 3.35+.
    if has_legacy_password:
        try:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE user DROP COLUMN password"))
            logger.info("Dropped legacy 'password' column")
        except Exception:
            logger.warning(
                "Could not drop legacy 'password' column "
                "(SQLite may be too old). It will be removed on a newer SQLite."
            )
            # Don't raise — app should still start.

    # 4. Migrate the analysis table: add columns introduced by the refactored
    #    Analysis model (confidence_level, inference_ms, model_version).
    _migrate_analysis_table()


def _migrate_analysis_table() -> None:
    """Add columns the refactored Analysis model expects, if missing."""
    import logging
    from sqlalchemy import inspect, text

    logger = logging.getLogger(__name__)
    inspector = inspect(db.engine)
    if "analysis" not in inspector.get_table_names():
        return

    existing = {c["name"] for c in inspector.get_columns("analysis")}
    needed = {
        "confidence_level": "VARCHAR(20)",
        "inference_ms": "FLOAT",
        "model_version": "VARCHAR(50)",
    }
    with db.engine.begin() as conn:
        for col, typ in needed.items():
            if col not in existing:
                logger.info("Adding column '%s' to analysis table", col)
                conn.execute(text(f"ALTER TABLE analysis ADD COLUMN {col} {typ}"))
