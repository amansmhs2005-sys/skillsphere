from datetime import datetime
from app.extensions import db


class SearchHistory(db.Model):
    """Logs each AI topic-detection query (REQ-6), so REQ-8's "related
    topics based on ... search history" has something concrete to draw
    on. Not in SRS 6.1's entity table — an implementation detail needed
    to make REQ-8 literally true rather than only "same skill" matching.
    """

    __tablename__ = "search_history"

    search_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    query_text = db.Column(db.Text, nullable=False)
    detected_skill_id = db.Column(db.Integer, db.ForeignKey("skills.skill_id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
