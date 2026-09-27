from datetime import datetime
from app.extensions import db


class Progress(db.Model):
    """Per-topic completion checklist for a learner (REQ-20, REQ-21).

    Rows here are normally created/updated by the Session Management
    module when a tutor confirms a topic was covered. A row is also
    created lazily (status='pending') the first time a learner views
    a tutor's topic, so the checklist has something to show before
    Session Management exists.
    """

    __tablename__ = "progress"

    progress_id = db.Column(db.Integer, primary_key=True)
    learner_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("skills.skill_id"), nullable=False)
    status = db.Column(
        db.Enum("pending", "completed", name="progress_status_enum"),
        nullable=False,
        default="pending",
    )
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("learner_id", "topic_id", name="uq_learner_topic"),)

    topic = db.relationship("Skill")

    def to_dict(self):
        return {
            "progress_id": self.progress_id,
            "topic_id": self.topic_id,
            "skill_name": self.topic.skill_name if self.topic else None,
            "topic_name": self.topic.topic_name if self.topic else None,
            "status": self.status,
        }
