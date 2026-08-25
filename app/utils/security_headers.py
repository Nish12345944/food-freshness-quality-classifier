"""Security headers applied to every response."""
import logging

logger = logging.getLogger(__name__)


def register_security_headers(app):
    """Add standard security headers without breaking app functionality."""

    @app.after_request
    def set_security_headers(response):
        # Prevent MIME-type sniffing
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # Prevent clickjacking
        response.headers.setdefault("X-Frame-Options", "DENY")
        # Limit referrer leakage
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # Restrict browser features
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(self), microphone=(), geolocation=()",
        )
        # Content Security Policy — allow CDN assets used by templates
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com "
            "https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self';",
        )
        return response