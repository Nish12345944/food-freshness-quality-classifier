# API Documentation (v1)

Base URL: `/api/v1`

All responses use a consistent JSON envelope:

```json
{ "success": true, "data": { ... } }
```

```json
{ "success": false, "error": "human-readable message" }
```

Authentication uses the same session cookie as the web app
(Flask-Login). Endpoints marked 🔒 require a logged-in user.

---

## GET /api/v1/health

Service health check. Performs no inference.

**Response** `200` (healthy) or `503` (degraded):

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "model_loaded": true,
    "model_version": "1.0.0",
    "database": "connected",
    "version": "1.0.0"
  }
}
```

---

## POST /api/v1/predict 🔒

Predict freshness for one image.

**Request** `multipart/form-data`:

| Field | Type | Notes |
|---|---|---|
| `image` | file | JPG/PNG/WEBP, ≤ 16 MB, ≥ 64×64 px |

**Response** `200`:

```json
{
  "success": true,
  "data": {
    "analysis_id": 42,
    "prediction": "Fresh",
    "confidence": 0.924,
    "confidence_level": "High",
    "low_confidence_warning": false,
    "probabilities": {"Fresh": 0.924, "Okay": 0.051, "Avoid": 0.025},
    "food_type": "fruit",
    "model_version": "1.0.0",
    "inference_time_ms": 184.2,
    "quality": {
      "quality_label": "Good",
      "resolution": "1024x768",
      "blur_score": 182.3
    }
  }
}
```

**Errors**: `400` missing file · `422` invalid file type or failed quality
gate · `503` model not loaded · `429` rate limited (30/hour, 5/minute).

---

## POST /api/v1/predict/batch 🔒

Predict freshness for up to 10 images.

**Request** `multipart/form-data`: repeatable `images` file field.

**Response** `200`:

```json
{
  "success": true,
  "data": {
    "results": [ { "...same shape as single predict..." } ],
    "errors": [ {"filename": "bad.exe", "error": "File type '.exe' is not allowed."} ],
    "total_processed": 7,
    "total_failed": 1
  }
}
```

**Errors**: `400` no images · `422` all images failed · `503` model not loaded.

---

## GET /api/v1/history 🔒

Paginated history for the current user.

**Query params**: `page` (default 1), `per_page` (default 20, max 50),
`label` (optional filter: `Fresh` / `Okay` / `Avoid`).

**Response** `200`:

```json
{
  "success": true,
  "data": {
    "analyses": [
      {
        "id": 42,
        "label": "Fresh",
        "confidence": 0.924,
        "confidence_level": "High",
        "food_type": "fruit",
        "resolution": "1024x768",
        "blur_score": 182.3,
        "inference_ms": 184.2,
        "model_version": "1.0.0",
        "timestamp": "2024-06-01 14:30"
      }
    ],
    "page": 1,
    "total_pages": 1,
    "total": 1
  }
}
```

---

## GET /api/v1/analysis/{id} 🔒

Fetch one analysis by ID. Owner-only.

**Response** `200` with the same shape as a history item.
**Errors**: `403` not the owner · `404` unknown ID.

---

## GET /api/v1/explain/{id} 🔒

Generate a Grad-CAM attention heatmap for an analysis (owner-only).
Rate limited to 20/hour.

**Response** `200`:

```json
{
  "success": true,
  "data": {
    "image_url": "/static/gradcam/gradcam_42.png",
    "note": "Grad-CAM shows where the model focused its attention. It does not prove causality."
  }
}
```

**Errors**: `403` not owner · `404` original image missing · `500` heatmap
generation failed · `503` model not loaded.

---

## Status code summary

| Code | Meaning |
|---|---|
| 200 | Success |
| 400 | Malformed request (missing file/field) |
| 403 | Authenticated but not authorised (not owner) |
| 404 | Resource not found |
| 413 | Upload exceeds server body limit |
| 422 | File rejected by validation or quality gate |
| 429 | Rate limit exceeded |
| 500 | Unexpected server error (details logged, never exposed) |
| 503 | Model not loaded / service degraded |