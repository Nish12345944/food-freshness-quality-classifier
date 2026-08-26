# 🥗 FoodFresh AI

**AI-Powered Food Freshness Intelligence**

[![Tests](https://github.com/Nish12345944/food-freshness-quality-classifier/actions/workflows/tests.yml/badge.svg)](https://github.com/Nish12345944/food-freshness-quality-classifier/actions/workflows/tests.yml)
[![Deploy Check](https://github.com/Nish12345944/food-freshness-quality-classifier/actions/workflows/deploy-check.yml/badge.svg)](https://github.com/Nish12345944/food-freshness-quality-classifier/actions/workflows/deploy-check.yml)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-MobileNetV3-EE4C2C?logo=pytorch&logoColor=white)
![Deploy](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white)

> Upload a photo of your food and get an instant **visual freshness estimate** —
> powered by a real deep-learning model with confidence scoring, explainable AI
> heatmaps, and smart storage recommendations.

🔗 **GitHub:** [this repository](https://github.com/Nish12345944/food-freshness-quality-classifier)

> **⚠️ Live-deploy status at a glance:** the web app builds and runs, but a
> **trained model is required** before freshness predictions actually work. The
> production build **fails closed** until `models/food_freshness.pt` exists or
> `MODEL_URL` points at one. Predictions return 503 (`model_loaded: false`)
> until a real model is provided. See [Model deployment](#model-deployment).

---

## Overview

FoodFresh AI is a full-stack machine-learning web application that estimates
whether food looks **Fresh**, **Okay**, or should be **Avoided** — from a
single photo. It is a genuine end-to-end ML product: a reproducible training
pipeline, a deterministic CPU inference service, a secure Flask backend, a
versioned REST API, explainability via Grad-CAM, and a polished responsive UI.

**⚠️ Important:** this tool provides a *visual estimate only*. It is not a
laboratory test and cannot guarantee food safety. See
[Limitations](#limitations).

## Key Features

| | |
|---|---|
| 🧠 **Computer Vision** | MobileNetV3-Small transfer learning, real softmax probabilities |
| 🎯 **Confidence Scoring** | Every prediction carries High / Medium / Low confidence; low-confidence results are flagged, never presented as definitive |
| 📚 **Batch Analysis** | Up to 10 images per run with per-item results and summary stats |
| 🔍 **Explainable AI** | Grad-CAM attention heatmaps ("where the model looked" — not causality) |
| 🕘 **Analysis History** | Searchable, filterable, paginated history with per-user isolation |
| 💡 **Storage Recommendations** | Temperature, humidity, and shelf-life guidance by food category |

## Architecture

```
Browser
  ↓
Flask Application (app factory + blueprints)
  ↓
Image Validation        extension · MIME · size · decodability
  ↓
Image Quality Gate      resolution · blur · brightness (separate from prediction)
  ↓
Prediction Service      loaded once at startup
  ↓
Vision Model            MobileNetV3-Small · CPU inference
  ↓
Confidence / Explainability   softmax probabilities · Grad-CAM
  ↓
Database                SQLAlchemy → PostgreSQL (prod) / SQLite (dev)
```

Full details in [`docs/architecture.md`](docs/architecture.md).

## ML Pipeline

```
training/
├── train.py      # transfer learning, augmentation, early stopping, checkpoints
├── evaluate.py   # accuracy, precision/recall/F1, per-class metrics, confusion matrix
├── dataset.py    # stratified splits, transforms, weighted sampler for imbalance
├── metrics.py    # metric computation helpers
└── config.py     # all hyperparameters, seed = 42 for reproducibility
```

- **Model:** MobileNetV3-Small (ImageNet-pretrained backbone, new 3-class head)
- **Input:** 224×224 RGB, ImageNet normalisation
- **Training:** Adam + StepLR, early stopping (patience 5), optional weighted sampler
- **Deterministic inference:** same image → same probabilities, every time

See [`docs/model.md`](docs/model.md) and [`training/README.md`](training/README.md).

## Model Performance

This repository does **not** ship a trained artifact or fabricated accuracy
numbers. Metrics are produced by running evaluation on your own dataset:

```bash
cd training && python evaluate.py --model ../models/food_freshness.pt
```

This writes `models/metrics.json` with measured accuracy, macro P/R/F1,
per-class metrics, and a confusion matrix. Inference latency is recorded for
every prediction (`inference_time_ms` in the API) — see
[`docs/performance.md`](docs/performance.md) for indicative CPU numbers.

## Explainable AI

The result page can generate a **Grad-CAM heatmap** showing which regions of
the image most influenced the prediction, side-by-side with the original.
The UI explicitly states that the heatmap shows model attention and does not
prove causality.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, Flask 3, Gunicorn |
| ML | PyTorch, torchvision (MobileNetV3-Small), OpenCV, Pillow |
| Database | SQLAlchemy 2 → PostgreSQL (prod) / SQLite (dev) |
| Auth | Flask-Login, PBKDF2-SHA256 password hashing |
| Frontend | Server-rendered Jinja2, vanilla JS, Chart.js, Inter font |
| Reports | ReportLab (PDF), SMTP email |
| Testing | Pytest (40 tests, no external services) |
| CI/CD | GitHub Actions (tests + deploy checks) |
| Hosting | Render (gunicorn, `/health` probe) |

## API

Versioned JSON API under `/api/v1` with a consistent envelope:

```json
{ "success": true, "data": { "prediction": "Fresh", "confidence": 0.924 } }
```

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/health` | — | Service health (no inference) |
| POST | `/api/v1/predict` | 🔒 | Single-image prediction |
| POST | `/api/v1/predict/batch` | 🔒 | Batch prediction (≤10 images) |
| GET | `/api/v1/history` | 🔒 | Paginated history (+ filters) |
| GET | `/api/v1/analysis/{id}` | 🔒 | One analysis (owner-only) |
| GET | `/api/v1/explain/{id}` | 🔒 | Grad-CAM heatmap (owner-only) |

Full request/response docs: [`docs/api.md`](docs/api.md).

## Security

- 🔐 Passwords hashed (PBKDF2-SHA256) — never plaintext, no default admin
- ✅ Upload validation: extension + MIME allow-lists, size limit, real image decoding, randomised filenames
- 👤 Strict user-data isolation on every read (verified by tests)
- ⏱️ Rate limiting on all expensive endpoints
- 🛡️ Security headers: CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy
- 🚫 Raw exceptions never exposed; secrets only via environment variables

Details: [`docs/security.md`](docs/security.md).

## Local Setup

```bash
git clone https://github.com/Nish12345944/food-freshness-quality-classifier.git
cd food-freshness-quality-classifier

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements-dev.txt
cp .env.example .env             # fill in SECRET_KEY etc. (optional locally)

python wsgi.py                   # dev server at http://localhost:5000
```

The app starts even without a trained model — it reports `model_loaded: false`
honestly and disables prediction endpoints until you train one.

### Train the model

```bash
# 1. Place data as  data/food_freshness/{Fresh,Okay,Avoid}/<images>
cd training
python train.py                  # writes models/food_freshness.pt
python evaluate.py               # writes models/metrics.json
```

See [`training/README.md`](training/README.md) for dataset layout and options.

### Run tests

```bash
pytest tests/ -v                 # 40 tests, fully offline
```

## Deployment (Render)

1. Push to GitHub and create a Render Web Service from this repo
2. Render reads `render.yaml`: build via `build.sh`, start via
   `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
3. Set environment variables in the dashboard (`SECRET_KEY`, optionally
   `DATABASE_URL` pointing at Render PostgreSQL, SMTP credentials)
4. Health check path is `/health`

Notes:
- Without `DATABASE_URL`, the app falls back to SQLite (fine for demos).
- Render's local filesystem is ephemeral — uploaded images/reports are lost on
  redeploy. Use object storage for durable files (see
  [`docs/architecture.md`](docs/architecture.md#storage-architecture)).

### Model deployment (fail-closed)

`build.sh` obtains the model artifact (`models/food_freshness.pt`) as follows:

```
if model file present      -> use it
else if MODEL_URL set      -> download + verify it
else if REQUIRE_MODEL=1    -> BUILD FAILS (never silently ship a broken AI app)
else (REQUIRE_MODEL=0)     -> degraded boot, model_loaded=false
```

To deploy a **genuinely working** classifier you must provide a real trained
artifact — commit it to `models/food_freshness.pt` **or** set `MODEL_URL` to a
direct HTTPS link to one. There is **no default/published model URL** in this
repo. See [`DEPLOYMENT.md`](DEPLOYMENT.md) and [`training/README.md`](training/README.md).

### Verify a real model (local + CI)

```bash
python scripts/smoke_test_model.py models/food_freshness.pt   # exit 0 = PASS
python -m pytest tests/test_model_smoke.py -v                 # skips if no model
```

The GitHub Actions workflow `.github/workflows/model-smoke.yml` runs this check
against a real artifact when `MODEL_URL` is configured, and reports a skip
otherwise — it never fabricates model results.

## Testing

```text
tests/
├── conftest.py               # fixtures: fresh app/client, synthetic test images
├── test_auth.py              # registration, login, hashing, logout, user isolation
├── test_prediction.py        # upload flow, demo, batch routing, model-unavailable handling
├── test_image_validation.py  # valid/invalid/oversized/low-quality images
├── test_api.py               # API auth, envelope shape, owner-only access, status codes
├── test_analytics.py         # KPIs, filters, empty states
├── test_health.py            # health endpoints, honest degraded state
├── test_model_smoke.py       # REAL-model smoke test (skips when no artifact)
└── test_security.py          # security headers, error pages, rate limiting
```

CI runs the suite plus an app-boot smoke check and deployment-config
consistency checks on every push (`.github/workflows/`).

## Limitations

- **Visual estimate only.** Freshness cannot be guaranteed from an image;
  bacteria, odours, and internal spoilage are invisible to a camera.
- **Not food-safety advice.** Always use your own judgment and official guidance.
- **Image quality matters.** Blur, poor lighting, or odd angles reduce
  reliability (poor images are rejected rather than guessed at).
- **Dataset limitations.** Results depend on the training data's quality,
  lighting conditions, and food coverage.
- **Unseen categories.** Foods not represented during training may produce
  unreliable predictions.
- **Ephemeral storage on free hosting.** Uploaded images are not permanently
  retained unless you add object storage.

## Future Improvements

- [ ] External object storage (S3-compatible) for durable uploads
- [ ] More food categories and larger, more diverse training data
- [ ] Token-based API authentication for programmatic access
- [ ] Async/batched inference queue under load
- [ ] Per-user analytics export (CSV)

## Author

Built by [@Nish12345944](https://github.com/Nish12345944) — feedback and PRs welcome!

---

*FoodFresh AI provides AI-powered visual freshness assessment. It does not
replace professional food safety evaluation.*