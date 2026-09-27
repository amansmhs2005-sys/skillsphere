from app.extensions import db
from app.models.user import User
from app.models.request_session import RequestSession
from app.models.review import Review


def recalculate_trust_score(tutor_id: int) -> float:
    """REQ-15: weighted formula — 50% average rating, 20% session
    completion rate, 20% attendance rate, 10% verification status.
    Business rule 5.5: recalculated after every new rating.

    Simplifications made explicit here (a real product would track more
    state, e.g. an "accepted_at" timestamp to know whether a cancelled
    session had ever been accepted):
      - completion_rate = completed / (completed + cancelled)
      - attendance_rate = attended / (attended + no-show), among
        completed sessions only (attended is only set at completion)
    Any ratio with a zero denominator contributes 0, not undefined.
    """
    tutor = User.query.get(tutor_id)
    if tutor is None:
        return 0.0

    # --- 50%: average rating, scored 1-5 -> normalized to 0-1 ---
    reviews = (
        db.session.query(Review.rating)
        .join(RequestSession, Review.session_id == RequestSession.request_id)
        .filter(RequestSession.tutor_id == tutor_id)
        .all()
    )
    ratings = [r[0] for r in reviews]
    avg_rating_norm = (sum(ratings) / len(ratings) / 5.0) if ratings else 0.0

    # --- 20%: completion rate ---
    completed_count = RequestSession.query.filter_by(tutor_id=tutor_id, status="completed").count()
    cancelled_count = RequestSession.query.filter_by(tutor_id=tutor_id, status="cancelled").count()
    completion_denom = completed_count + cancelled_count
    completion_rate = (completed_count / completion_denom) if completion_denom else 0.0

    # --- 20%: attendance rate (only meaningful among completed sessions) ---
    attended_true = RequestSession.query.filter_by(tutor_id=tutor_id, status="completed", attended=True).count()
    attended_false = RequestSession.query.filter_by(tutor_id=tutor_id, status="completed", attended=False).count()
    attendance_denom = attended_true + attended_false
    attendance_rate = (attended_true / attendance_denom) if attendance_denom else 0.0

    # --- 10%: admin-verified status ---
    verification_component = 1.0 if tutor.admin_verified else 0.0

    score = (
        0.5 * avg_rating_norm * 100
        + 0.2 * completion_rate * 100
        + 0.2 * attendance_rate * 100
        + 0.1 * verification_component * 100
    )
    score = round(score, 2)

    tutor.trust_score = score
    db.session.commit()
    return score
