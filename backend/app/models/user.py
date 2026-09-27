import bcrypt
from datetime import datetime
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(190), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    branch = db.Column(db.String(100))
    year = db.Column(db.String(20))
    bio = db.Column(db.Text)

    is_learner = db.Column(db.Boolean, nullable=False, default=True)
    is_tutor = db.Column(db.Boolean, nullable=False, default=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    verification_token = db.Column(db.String(255))

    # Admin-performed verification (business rule 5.5), distinct from the
    # self-service email link above. Feeds 10% of the trust score (REQ-15).
    admin_verified = db.Column(db.Boolean, nullable=False, default=False)
    is_suspended = db.Column(db.Boolean, nullable=False, default=False)

    trust_score = db.Column(db.Numeric(5, 2), nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    skills = db.relationship("Skill", backref="tutor", cascade="all, delete-orphan")
    availability_slots = db.relationship(
        "Availability", backref="tutor", cascade="all, delete-orphan"
    )

    # ---- password helpers (REQ-1, security: hashed, never plaintext) ----
    def set_password(self, raw_password: str) -> None:
        hashed = bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt())
        self.password_hash = hashed.decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        return bcrypt.checkpw(
            raw_password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def to_dict(self, include_private=False):
        data = {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "branch": self.branch,
            "year": self.year,
            "bio": self.bio,
            "is_learner": self.is_learner,
            "is_tutor": self.is_tutor,
            "is_verified": self.is_verified,
            "admin_verified": self.admin_verified,
            "trust_score": float(self.trust_score),
        }
        if include_private:
            data["is_admin"] = self.is_admin
            data["is_suspended"] = self.is_suspended
        return data
