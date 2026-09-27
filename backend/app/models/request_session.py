from datetime import datetime
from app.extensions import db


class RequestSession(db.Model):
    """A session request between a learner and a tutor, and its lifecycle
    (REQ-10, REQ-11, REQ-12, REQ-13). Named RequestSession (not Session)
    to avoid clashing with Flask/SQLAlchemy's own "session" concept.
    """

    __tablename__ = "requests_sessions"

    request_id = db.Column(db.Integer, primary_key=True)
    learner_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    tutor_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("skills.skill_id"), nullable=False)

    problem_description = db.Column(db.Text)
    mode = db.Column(db.Enum("online", "offline", name="session_mode_enum"), nullable=False, default="online")

    preferred_date = db.Column(db.Date)
    preferred_time = db.Column(db.Time)
    scheduled_date = db.Column(db.Date)
    scheduled_time = db.Column(db.Time)

    status = db.Column(
        db.Enum("pending", "accepted", "rejected", "completed", "cancelled", name="session_status_enum"),
        nullable=False,
        default="pending",
    )
    reject_reason = db.Column(db.String(255))

    attended = db.Column(db.Boolean)  # null until session is closed
    session_notes = db.Column(db.Text)
    session_summary = db.Column(db.Text)

    reminder_sent = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    learner = db.relationship("User", foreign_keys=[learner_id])
    tutor = db.relationship("User", foreign_keys=[tutor_id])
    topic = db.relationship("Skill")
    review = db.relationship("Review", backref="session", uselist=False, cascade="all, delete-orphan")
    reports = db.relationship("Report", backref="session", cascade="all, delete-orphan")

    def to_dict(self, detail=False):
        data = {
            "request_id": self.request_id,
            "learner_id": self.learner_id,
            "learner_name": self.learner.name if self.learner else None,
            "tutor_id": self.tutor_id,
            "tutor_name": self.tutor.name if self.tutor else None,
            "topic_id": self.topic_id,
            "skill_name": self.topic.skill_name if self.topic else None,
            "topic_name": self.topic.topic_name if self.topic else None,
            "mode": self.mode,
            "status": self.status,
            "preferred_date": self.preferred_date.isoformat() if self.preferred_date else None,
            "preferred_time": self.preferred_time.strftime("%H:%M") if self.preferred_time else None,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "scheduled_time": self.scheduled_time.strftime("%H:%M") if self.scheduled_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if detail:
            data.update(
                {
                    "problem_description": self.problem_description,
                    "reject_reason": self.reject_reason,
                    "attended": self.attended,
                    "session_notes": self.session_notes,
                    "session_summary": self.session_summary,
                    "has_review": self.review is not None,
                }
            )
        return data
