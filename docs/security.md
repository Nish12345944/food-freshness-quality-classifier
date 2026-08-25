# Security Documentation

## Password storage

- Passwords are never stored in plaintext.
- `werkzeug.security.generate_password_hash` (PBKDF2-SHA256, per-password salt)
  hashes on registration; `check_password_hash` verifies on login.
- A startup migration converts any legacy plaintext passwords to hashes and
  drops the legacy column — without destroying existing accounts.
- No default/admin credentials are auto-created in production.

## Authentication & sessions

- Flask-Login session-based authentication; `SECRET_KEY` signs session cookies
  and is generated at startup if not provided (set it explicitly in production).
- All user pages and data endpoints require login (`@login_required`).
- Login failures return a generic message ("Invalid username or password") to
  prevent username enumeration, and are logged server-side.

## Authorisation & user-data isolation

- Every analysis record carries a `user_id`.
- All reads (`/result/<id>`, `/api/v1/analysis/<id>`, `/api/v1/explain/<id>`,
  PDF download, email report) verify `analysis.user_id == current_user.id`
  before serving. Violations return 302/403 and are logged as warnings.
- History and analytics queries are always filtered by the current user.

## File upload validation

Every upload passes through `validate_and_save()`:

1. **Extension allow-list**: only `png`, `jpg`, `jpeg`, `webp`
2. **MIME type check** against an image MIME allow-list
3. **Size limit**: 16 MB per file (plus Flask's `MAX_CONTENT_LENGTH`)
4. **Actual decoding**: the bytes must decode as a real image via Pillow
5. **Randomised filenames**: original base name + UUID suffix, extension
   re-derived from the allow-list — prevents path traversal and overwrites

After saving, an independent **quality gate** checks resolution, blur
(Laplacian variance), and brightness/exposure. Poor-quality images are deleted
and rejected with actionable guidance instead of being guessed at.

## Rate limiting

Flask-Limiter protects expensive endpoints:

| Endpoint | Limit |
|---|---|
| Demo predict | 10/hour, 3/minute |
| Predict (upload) | 30/hour, 5/minute |
| Batch predict | 10/hour, 2/minute |
| Grad-CAM explain | 20/hour |
| Camera capture | 20/hour |

Limits are configurable via environment variables. Excess requests receive a
clean 429 response.

## Environment secrets

- All secrets come from environment variables (see [`.env.example`](../.env.example)).
- `.env` files are gitignored; only the variable-name template is committed.
- Render secrets are set in the dashboard, never in `render.yaml` values.
- Passwords and tokens are never written to logs.

## Security headers

Applied to every response (`app/utils/security_headers.py`):

- `Content-Security-Policy` — restricts script/style/font/image sources
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY` (clickjacking protection)
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` — camera limited to same-origin, mic/geolocation denied

## Error handling

- Raw exceptions are never shown to users.
- Handlers for 400/401/403/404/413/422/429/500 return friendly HTML pages or
  JSON errors (for `/api/*` paths); full tracebacks go to server logs only.