import os
import secrets


class Config:
    SECRET_KEY: str = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Database — PostgreSQL in production, SQLite locally
    _db_url: str = os.environ.get("DATABASE_URL", "sqlite:///users.db")
    SQLALCHEMY_DATABASE_URI: str = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Upload settings
    MAX_CONTENT_LENGTH: int = int(
        os.environ.get("MAX_UPLOAD_MB", "16")
    ) * 1024 * 1024

    UPLOAD_FOLDER: str = os.path.join("static", "uploads")
    REPORTS_FOLDER: str = os.path.join("static", "reports")
    PROFILES_FOLDER: str = os.path.join("static", "profiles")

    ALLOWED_EXTENSIONS: set = {"png", "jpg", "jpeg", "webp"}
    MAX_BATCH_SIZE: int = int(
        os.environ.get("MAX_BATCH_SIZE", "10")
    )

    # ML model
    MODEL_PATH: str = os.environ.get(
        "MODEL_PATH",
        os.path.join("models", "food_freshness.pt"),
    )

    MODEL_VERSION: str = os.environ.get(
        "MODEL_VERSION",
        "1.0.0",
    )

    MODEL_INPUT_SIZE: int = 224

    # Enable/disable model loading.
    # Production/local default: enabled.
    MODEL_ENABLED: bool = os.environ.get(
        "MODEL_ENABLED",
        "true",
    ).lower() in ("1", "true", "yes", "on")

    # Confidence thresholds
    CONFIDENCE_HIGH: float = float(
        os.environ.get("CONFIDENCE_HIGH", "0.70")
    )

    CONFIDENCE_MEDIUM: float = float(
        os.environ.get("CONFIDENCE_MEDIUM", "0.50")
    )

    # Rate limiting
    RATELIMIT_DEFAULT: str = os.environ.get(
        "RATELIMIT_DEFAULT",
        "200 per day;50 per hour",
    )

    RATELIMIT_PREDICT: str = os.environ.get(
        "RATELIMIT_PREDICT",
        "30 per hour;5 per minute",
    )

    RATELIMIT_STORAGE_URI: str = os.environ.get(
        "RATELIMIT_STORAGE_URI",
        "memory://",
    )

    # Email (optional)
    SMTP_SERVER: str = os.environ.get(
        "SMTP_SERVER",
        "smtp.gmail.com",
    )

    SMTP_PORT: int = int(
        os.environ.get("SMTP_PORT", "587")
    )

    SENDER_EMAIL: str = os.environ.get(
        "SENDER_EMAIL",
        "",
    )

    SENDER_PASSWORD: str = os.environ.get(
        "SENDER_PASSWORD",
        "",
    )

    # Application
    APP_VERSION: str = os.environ.get(
        "APP_VERSION",
        "1.0.0",
    )