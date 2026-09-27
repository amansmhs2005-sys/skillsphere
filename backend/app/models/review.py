from datetime import datetime
from app.extensions import db


class Review(db.Model):
    """A learner's rating + optional feedback for a completed session
    (REQ-14). Feeds the trust-score formula (REQ-15)."""

    __tablename__ = "reviews"

    review_id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("requests_sessions.request_id"), nullable=False, unique=True)
    rating = db.Column(db.SmallInteger, nullable=False)
    feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "review_id": self.review_id,
            "session_id": self.session_id,
            "rating": self.rating,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
