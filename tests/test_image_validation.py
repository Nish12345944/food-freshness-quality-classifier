"""Image validation and quality-gate tests."""
import os

from conftest import make_image
from werkzeug.datastructures import FileStorage

from app.services.image_service import check_image_quality, validate_and_save


def _fs(buf, name="test.png", mime="image/png"):
    return FileStorage(stream=buf, filename=name, content_type=mime)


def test_valid_image_passes_validation(tmp_path):
    result = validate_and_save(_fs(make_image()), str(tmp_path))
    assert result.valid
    assert os.path.exists(result.filepath)
    # Randomised filename keeps the original base name
    assert result.filename.startswith("test_")
    assert result.filename.endswith(".png")


def test_disallowed_extension_rejected(tmp_path):
    result = validate_and_save(_fs(make_image(), name="evil.exe"), str(tmp_path))
    assert not result.valid
    assert "not allowed" in result.error


def test_disallowed_mime_rejected(tmp_path):
    result = validate_and_save(
        _fs(make_image(), mime="application/octet-stream"), str(tmp_path)
    )
    assert not result.valid


def test_empty_file_rejected(tmp_path):
    import io
    result = validate_and_save(
        _fs(io.BytesIO(b""), name="empty.png"), str(tmp_path)
    )
    assert not result.valid


def test_non_image_content_rejected(tmp_path):
    import io
    result = validate_and_save(
        _fs(io.BytesIO(b"this is not an image at all"), name="fake.png"),
        str(tmp_path),
    )
    assert not result.valid


def test_tiny_image_fails_quality_gate(tmp_path):
    result = validate_and_save(_fs(make_image(width=50, height=50)), str(tmp_path))
    assert result.valid  # file itself is fine
    report = check_image_quality(result.filepath)
    assert not report.passed
    assert "too small" in report.reason


def test_dark_image_fails_quality_gate(tmp_path):
    result = validate_and_save(_fs(make_image(color=(2, 2, 2))), str(tmp_path))
    report = check_image_quality(result.filepath)
    assert not report.passed


def test_good_image_passes_quality_gate(tmp_path):
    result = validate_and_save(_fs(make_image()), str(tmp_path))
    report = check_image_quality(result.filepath)
    assert report.passed, f"expected pass, got: {report.reason}"