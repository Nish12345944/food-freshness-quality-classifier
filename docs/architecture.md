# Architecture

## High-level request flow

```
Browser
  ↓
Flask Application (app factory, blueprints)
  ↓
Image Validation        (extension, MIME, size, decodability)
  ↓
Image Quality Gate      (resolution, blur, brightness — separate from prediction)
  ↓
Prediction Service      (loaded once at startup)
  ↓
Vision Model            (MobileNetV3-Small, CPU inference)
  ↓
Confidence / Explainability   (softmax probabilities, Grad-CAM)
  ↓
Database                (SQLAlchemy → PostgreSQL or SQLite)
```

## Project layout

```
app/
├── __init__.py          # App factory: extensions, blueprints, migration, health
├── config.py            # All configuration from environment variables
├── routes/
│   ├── main.py          # Landing page, privacy
│   ├── auth.py          # Register / login / logout / profile
│   ├── prediction.py    # Dashboard, upload, camera, results, PDF, email, demo, history
│   ├── analytics.py     # KPIs and chart data
│   ├── api.py           # Legacy /api endpoints + root /health
│   └── api_v1.py        # Versioned JSON API (/api/v1)
├── services/
│   ├── prediction_service.py  # Model loading + deterministic inference
│   ├── image_service.py       # Validation, quality gate, food-type heuristic, Grad-CAM
│   └── report_service.py      # PDF generation + email delivery
├── models/
│   ├── user.py          # User ORM model (hashed passwords)
│   └── analysis.py      # Analysis ORM model (prediction records)
└── utils/
    ├── security.py           # Rate limiter instance
    ├── security_headers.py   # CSP and other response headers
    ├── error_handlers.py     # 400/401/403/404/413/422/429/500 handlers
    ├── logging_config.py     # Structured logging setup
    └── validators.py         # Registration/login validation rules

training/               # Reproducible training pipeline (see training/README.md)
tests/                  # Pytest suite (no external services required)
docs/                   # This documentation
wsgi.py                 # Production entry point (gunicorn wsgi:app)
```

## Authentication

- Session-based auth via Flask-Login.
- Passwords hashed with Werkzeug's `generate_password_hash` (PBKDF2-SHA256).
- `@login_required` protects all user pages and API data endpoints.
- Every analysis record is scoped by `user_id`; all reads verify ownership.

## API

Two layers:

1. **Server-rendered pages** — dashboard, result, history, analytics (HTML).
2. **Versioned JSON API** under `/api/v1` — see [`api.md`](api.md).

Consistent JSON envelope: `{"success": true, "data": ...}` or
`{"success": false, "error": "..."}` with correct HTTP status codes.

## Storage architecture

| Data | Development | Production (Render) |
|---|---|---|
| Database | SQLite (`instance/users.db`) | PostgreSQL via `DATABASE_URL` |
| Uploaded images | `static/uploads/` (local disk) | Local disk — **ephemeral** |
| Reports | `static/reports/` (local disk) | Generated on demand — ephemeral |
| Grad-CAM overlays | `static/gradcam/` | Generated on demand — ephemeral |

> **Important:** Render's local filesystem is not durable across deploys and
> restarts. Uploaded images and generated reports will be lost. For permanent
> user data, configure an external object store (e.g., S3-compatible) and swap
> the save/read helpers in `app/services/image_service.py`. The application
> fails gracefully when files referenced by DB records no longer exist
> (e.g., Grad-CAM returns a clear 404 message).

The database is the source of truth for analysis metadata; image files are
regenerable display assets.

## Render deployment

- `render.yaml` defines a Python web service using `build.sh` and gunicorn.
- Start command binds to Render's `$PORT`: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`.
- Health check path `/health` returns 200 only when the model is loaded and
  the database responds; otherwise 503 (honest degraded state).
- Debug mode is never enabled in production; Flask's dev server is not used.
- Secrets (`SECRET_KEY`, SMTP credentials) are set via the Render dashboard,
  never committed. See [`.env.example`](../.env.example).

## Startup behaviour

On boot the app factory:

1. Configures logging
2. Initialises extensions (SQLAlchemy, LoginManager, Limiter)
3. Registers all blueprints, error handlers, and security headers
4. Runs `db.create_all()` plus an idempotent, non-destructive schema migration
   (adds missing columns; never drops tables or recreates the database)
5. Loads the ML model once (or logs a clear warning if the artifact is absent)