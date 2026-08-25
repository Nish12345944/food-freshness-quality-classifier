import logging
from flask import Flask, jsonify, render_template, request

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:

    @app.errorhandler(400)
    def bad_request(e):
        return _json_or_html(400, "Bad Request", str(e.description))

    @app.errorhandler(401)
    def unauthorized(e):
        return _json_or_html(401, "Unauthorized", "Authentication required.")

    @app.errorhandler(403)
    def forbidden(e):
        return _json_or_html(403, "Forbidden", "You do not have permission to access this resource.")

    @app.errorhandler(404)
    def not_found(e):
        return _json_or_html(404, "Not Found", "The page you're looking for doesn't exist or has been moved.")

    @app.errorhandler(413)
    def too_large(e):
        return _json_or_html(413, "File Too Large", "The uploaded file exceeds the size limit.")

    @app.errorhandler(422)
    def unprocessable(e):
        return _json_or_html(422, "Unprocessable Entity", str(e.description))

    @app.errorhandler(429)
    def rate_limited(e):
        return _json_or_html(429, "Too Many Requests", "You've made too many requests. Please wait a moment and try again.")

    @app.errorhandler(500)
    def internal_error(e):
        logger.exception("Internal server error: %s", e)
        return _json_or_html(500, "Something Went Wrong", "An unexpected error occurred. Please try again later.")


def _json_or_html(code: int, title: str, detail: str):
    if request.accept_mimetypes.best == "application/json" or request.path.startswith("/api/"):
        return jsonify({"success": False, "error": detail}), code
    try:
        return render_template("error.html", code=code, title=title, detail=detail), code
    except Exception:
        logger.exception("Failed to render error template for %s", code)
        html = f"<h1>{code} — {title}</h1><p>{detail}</p><p><a href='/'>Return home</a></p>"
        return html, code