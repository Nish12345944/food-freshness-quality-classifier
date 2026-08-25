from datetime import datetime
from app import db


class Analysis(db.Model):
    __tablename__ = "analysis"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    image_filename = db.Column(db.String(200), nullable=False)
    label = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    confidence_level = db.Column(db.String(20), nullable=True)  # High / Medium / Low
    food_type = db.Column(db.String(100), nullable=True)
    resolution = db.Column(db.String(50), nullable=True)
    blur_score = db.Column(db.Float, nullable=True)
    inference_ms = db.Column(db.Float, nullable=True)
    model_version = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "confidence_level": self.confidence_level,
            "food_type": self.food_type,
            "resolution": self.resolution,
            "blur_score": round(self.blur_score, 2) if self.blur_score else None,
            "inference_ms": round(self.inference_ms, 1) if self.inference_ms else None,
            "model_version": self.model_version,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M"),
        }

    def __repr__(self) -> str:
        return f"<Analysis {self.id} - {self.label}>"
