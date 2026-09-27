from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.user import User
from app.models.request_session import RequestSession
from app.models.review import Review
from app.models.report import Report
from app.notifications.utils import notify
from app.trust import recalculate_trust_score

feedback_bp = Blueprint("feedback", __name__, url_prefix="/api")


def _current_user() -> User:
    return User.query.get_or_404(int(get_jwt_identity()))


# ---------------------------------------------------------------
# REQ-14, REQ-15, REQ-16: ratings & trust score
# ---------------------------------------------------------------
@feedback_bp.post("/sessions/<int:session_id>/review")
@jwt_required()
def submit_review(session_id):
    user = _current_user()
    session_row = RequestSession.query.get_or_404(session_id)

    if session_row.learner_id != user.user_id:
        return jsonify(error="only the learner in this session can leave a review"), 403
    if session_row.status != "completed":
        return jsonify(error="you can only review a completed session"), 409
    if session_row.review is not None:
        return jsonify(error="this session has already been reviewed"), 409

    data = request.get_json(silent=True) or {}
    rating = data.get("rating")
    feedback = (data.get("feedback") or "").strip()

    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify(error="rating must be an integer from 1 to 5"), 400

    review = Review(session_id=session_row.request_id, rating=rating, feedback=feedback)
    db.session.add(review)
    db.session.commit()

    new_score = recalculate_trust_score(session_row.tutor_id)  # REQ-15, business rule 5.5

    return jsonify(
        message="review submitted",
        review=review.to_dict(),
        tutor_trust_score=new_score,  # REQ-16
    ), 201


@feedback_bp.get("/tutors/<int:tutor_id>/reviews")
def list_tutor_reviews(tutor_id):
    """REQ-16: trust score + underlying reviews, visible to all learners."""
    tutor = User.query.get_or_404(tutor_id)
    rows = (
        db.session.query(Review)
        .join(RequestSession, Review.session_id == RequestSession.request_id)
        .filter(RequestSession.tutor_id == tutor_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return jsonify(trust_score=float(tutor.trust_score), reviews=[r.to_dict() for r in rows])


# ---------------------------------------------------------------
# REQ-22: report inappropriate behavior
# ---------------------------------------------------------------
@feedback_bp.post("/sessions/<int:session_id>/report")
@jwt_required()
def report_session(session_id):
    user = _current_user()
    session_row = RequestSession.query.get_or_404(session_id)

    if user.user_id not in (session_row.learner_id, session_row.tutor_id):
        return jsonify(error="you were not a party to this session"), 403

    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip()
    if not reason:
        return jsonify(error="reason is required"), 400

    report = Report(session_id=session_row.request_id, reported_by=user.user_id, reason=reason)
    db.session.add(report)
    db.session.commit()

    # Notify every admin so someone picks it up (REQ-17).
    for admin in User.query.filter_by(is_admin=True).all():
        notify(
            admin,
            "report_filed",
            f"{user.name} filed a report on session #{session_row.request_id}.",
            related_id=report.report_id,
        )

    return jsonify(message="report submitted", report=report.to_dict()), 201
