from datetime import datetime
from app.extensions import db


class Report(db.Model):
    """A flagged behavior report tied to a session, for Admin review
    (REQ-17, REQ-22)."""

    __tablename__ = "reports"

    report_id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("requests_sessions.request_id"), nullable=False)
    reported_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.Enum("open", "reviewed", "dismissed", name="report_status_enum"),
        nullable=False,
        default="open",
    )
    admin_action = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

    reporter = db.relationship("User", foreign_keys=[reported_by])

    def to_dict(self):
        return {
            "report_id": self.report_id,
            "session_id": self.session_id,
            "reported_by": self.reported_by,
            "reporter_name": self.reporter.name if self.reporter else None,
            "reason": self.reason,
            "status": self.status,
            "admin_action": self.admin_action,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
