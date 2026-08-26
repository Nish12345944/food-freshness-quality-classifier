# 🚀 Deployment Guide — Render

This guide matches the **current** repository state: WSGI entry `wsgi:app`,
Python 3.13.5, and a fail-closed model-artifact contract.

## Before you can deploy a working app: you need a trained model

The classifier uses a **real trained MobileNetV3-Small** artifact at
`models/food_freshness.pt`. This file is **not** in the repository (large binary,
kept out of git). Render’s build (`build.sh`) will **fail** unless you provide it
one of two ways:

1. **Set `MODEL_URL`** in the Render dashboard to a direct HTTPS URL of a real
   `food_freshness.pt` file (e.g. a Hugging Face Hub “resolve/main” link), OR
2. **Commit the trained model** into the repository at `models/food_freshness.pt`
   (not recommended — large binary, must be in git).

> ⚠️ Do not set `MODEL_URL` until you actually have a trained artifact. There is
> no default/published model URL for this project.

### Train the model first (local machine)

```bash
# 1. Put your dataset in data/food_freshness/{Fresh,Okay,Avoid}/<images>
cd training
pip install torch torchvision scikit-learn   # training-only deps
python train.py                              # writes ../models/food_freshness.pt
python evaluate.py --model ../models/food_freshness.pt   # writes metrics.json (real numbers)
```

See [`training/README.md`](training/README.md) for the dataset layout.

### Verify the trained model locally

```bash
python scripts/smoke_test_model.py models/food_freshness.pt   # exits 0 on PASS
python -m pytest tests/test_model_smoke.py -v
```

## Deploy on Render

1. Push this repository to GitHub.
2. In Render: **New → Web Service** → connect your repo → **Blueprint** (uses
   `render.yaml`) or **Manual**.
3. If using “Manual”, set:
   - **Runtime:** `Python 3`
   - **Build Command:** `./build.sh`
   - **Start Command:** `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
   - **Health Check Path:** `/health`
4. Add environment variables (Render dashboard):
   - `SECRET_KEY` (generate: `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `MODEL_URL` → your real trained artifact URL (or commit the model)
   - `PYTHON_VERSION` → `3.13.5`
   - Optional: `DATABASE_URL` (Render PostgreSQL), SMTP_* for email reports

## PostgreSQL in production

- Create a **PostgreSQL** database on Render.
- Copy its **Internal Database URL** and set it as `DATABASE_URL`.
- The app reads `DATABASE_URL` and uses PostgreSQL automatically
  (`psycopg2-binary` is in `requirements.txt`).
- No `DATABASE_URL` → falls back to local SQLite (fine for demos only; Render’s
  disk is ephemeral).
- `db.create_all()` is non-destructive: existing data is preserved, missing
  columns are added in-place. The database is never dropped/recreated on start.

## Email (optional)

SMTP is optional. Without `SENDER_EMAIL`/`SENDER_PASSWORD` the app still starts,
predictions still work, and the email-report button fails gracefully.

## Storage note

Render’s local filesystem is ephemeral — uploaded images and generated PDFs are
lost on redeploy. For durable storage add an object store (S3-compatible) and
point the app at it. Object storage is **not** required for basic prediction.

## Confirming the deploy is healthy

The build will succeed only when a real model is present. After startup:

```text
GET /health          -> {"status":"healthy","model_loaded":true,"model_validated":true,...}
GET /api/v1/health   -> same shape under "data"
```

If `model_loaded`/`model_validated` is `false`, the model is missing or invalid —
do not treat the app as fully functional.

## Troubleshooting

- **Build fails with “A trained model artifact is required for production”** →
  `MODEL_URL` is empty and no `models/food_freshness.pt` exists. Set a valid
  `MODEL_URL` or commit the model.
- **Login slow?** Free tier cold-starts (~30–60s on first request).
- **Webcam capture** is a local-only feature (no webcam on the server).