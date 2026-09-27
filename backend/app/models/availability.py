from app.extensions import db

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


class Availability(db.Model):
    """Tutor-declared free time slots (REQ-18)."""

    __tablename__ = "availability"

    availability_id = db.Column(db.Integer, primary_key=True)
    tutor_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)

    day = db.Column(db.Enum(*DAYS, name="day_enum"), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    def to_dict(self):
        return {
            "availability_id": self.availability_id,
            "tutor_id": self.tutor_id,
            "day": self.day,
            "start_time": self.start_time.strftime("%H:%M"),
            "end_time": self.end_time.strftime("%H:%M"),
        }
