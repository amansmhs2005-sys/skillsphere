from datetime import datetime
from app.extensions import db


class Skill(db.Model):
    """A single topic a tutor is registered to teach (REQ-4, REQ-5)."""

    __tablename__ = "skills"

    skill_id = db.Column(db.Integer, primary_key=True)
    tutor_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)

    skill_name = db.Column(db.String(150), nullable=False, index=True)
    topic_name = db.Column(db.String(150), nullable=False, index=True)
    difficulty = db.Column(
        db.Enum("beginner", "intermediate", "advanced", name="difficulty_enum"),
        nullable=False,
        default="beginner",
    )
    description = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, include_tutor=False):
        data = {
            "skill_id": self.skill_id,
            "tutor_id": self.tutor_id,
            "skill_name": self.skill_name,
            "topic_name": self.topic_name,
            "difficulty": self.difficulty,
            "description": self.description,
        }
        if include_tutor and self.tutor:
            data["tutor"] = {
                "user_id": self.tutor.user_id,
                "name": self.tutor.name,
                "trust_score": float(self.tutor.trust_score),
            }
        return data
