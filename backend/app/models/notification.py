from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    """In-app notification (REQ-19). Not itemised as its own entity in
    SRS 6.1, but needed to actually implement "notify a user in-app"."""

    __tablename__ = "notifications"

    notification_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    related_id = db.Column(db.Integer)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "notification_id": self.notification_id,
            "type": self.type,
            "message": self.message,
            "related_id": self.related_id,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
