"""Report service: PDF generation and email dispatch."""

import logging
import os

logger = logging.getLogger(__name__)


def build_analysis_data(analysis, storage_tips: dict, upload_folder: str) -> dict:
    return {
        "id": analysis.id,
        "timestamp": analysis.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "label": analysis.label,
        "confidence": round(analysis.confidence * 100, 1),
        "confidence_level": analysis.confidence_level,
        "food_type": analysis.food_type or "unknown",
        "quality": {
            "quality": analysis.blur_score and ("Good" if analysis.blur_score > 100 else "Fair") or "Unknown",
            "resolution": analysis.resolution or "Unknown",
            "blur_score": analysis.blur_score,
        },
        "image_path": os.path.join(upload_folder, analysis.image_filename),
        "storage_tips": storage_tips,
    }


def generate_pdf(analysis_data: dict, reports_folder: str) -> str | None:
    """Generate PDF and return its path, or None on failure."""
    try:
        from pdf_generator import generate_pdf_report
        os.makedirs(reports_folder, exist_ok=True)
        pdf_path = os.path.join(reports_folder, f"report_{analysis_data['id']}.pdf")
        if generate_pdf_report(analysis_data, pdf_path):
            return pdf_path
    except Exception:
        logger.exception("PDF generation failed for analysis %s", analysis_data.get("id"))
    return None


def send_report_email(recipient: str, analysis_data: dict, pdf_path: str | None) -> bool:
    """Send email report.  Returns True on success."""
    try:
        from email_sender import send_email_report, generate_email_body
        subject = f"Food Freshness Analysis Report — {analysis_data['label']}"
        body = generate_email_body(analysis_data)
        return send_email_report(recipient, subject, body, pdf_path)
    except Exception:
        logger.exception("Email dispatch failed to %s", recipient)
        return False
