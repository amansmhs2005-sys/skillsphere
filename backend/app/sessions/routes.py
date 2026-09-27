from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.user import User
from app.models.skill import Skill
from app.models.request_session import RequestSession
from app.models.progress import Progress
from app.notifications.utils import notify
from app.ai_engine.nlp import generate_session_summary
from app.trust import recalculate_trust_score

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/sessions")


def _current_user() -> User:
    return User.query.get_or_404(int(get_jwt_identity()))


def _parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_time(value):
    if not value:
        return None
    return datetime.strptime(value, "%H:%M").time()


def _session_or_403(session_id, user, allow_roles=("learner", "tutor")):
    """Fetch a session and confirm the current user is a party to it."""
    session_row = RequestSession.query.get_or_404(session_id)
    is_learner = session_row.learner_id == user.user_id and "learner" in allow_roles
    is_tutor = session_row.tutor_id == user.user_id and "tutor" in allow_roles
    if not (is_learner or is_tutor):
        return None
    return session_row


# ---------------------------------------------------------------
# REQ-10: create a session request
# ---------------------------------------------------------------
@sessions_bp.post("")
@jwt_required()
def create_request():
    user = _current_user()
    if not user.is_learner:
        return jsonify(error="only learners can send session requests"), 403

    data = request.get_json(silent=True) or {}
    topic_id = data.get("topic_id")
    mode = data.get("mode", "online")
    problem_description = (data.get("problem_description") or "").strip()
    preferred_date = data.get("preferred_date")  # "YYYY-MM-DD"
    preferred_time = data.get("preferred_time")  # "HH:MM"

    if not topic_id:
        return jsonify(error="topic_id is required"), 400
    if mode not in ("online", "offline"):
        return jsonify(error="mode must be 'online' or 'offline'"), 400

    topic = Skill.query.get(topic_id)
    if not topic:
        return jsonify(error="topic not found"), 404
    if topic.tutor_id == user.user_id:
        return jsonify(error="you cannot request a session with yourself"), 400

    try:
        pref_date = _parse_date(preferred_date)
        pref_time = _parse_time(preferred_time)
    except ValueError:
        return jsonify(error="preferred_date must be YYYY-MM-DD and preferred_time HH:MM"), 400

    session_row = RequestSession(
        learner_id=user.user_id,
        tutor_id=topic.tutor_id,
        topic_id=topic.skill_id,
        problem_description=problem_description,
        mode=mode,
        preferred_date=pref_date,
        preferred_time=pref_time,
        status="pending",
    )
    db.session.add(session_row)
    db.session.commit()

    # REQ-11 (notification half), REQ-19
    notify(
        topic.tutor,
        "session_requested",
        f"{user.name} requested a session on {topic.skill_name} — {topic.topic_name}.",
        related_id=session_row.request_id,
        email_subject="New SkillSphere session request",
    )

    return jsonify(message="session request sent", session=session_row.to_dict(detail=True)), 201


# ---------------------------------------------------------------
# REQ-13: list my sessions
# ---------------------------------------------------------------
@sessions_bp.get("/mine")
@jwt_required()
def list_my_sessions():
    user = _current_user()
    role = request.args.get("role", "learner")  # "learner" | "tutor"
    status = request.args.get("status")

    if role == "tutor":
        query = RequestSession.query.filter_by(tutor_id=user.user_id)
    else:
        query = RequestSession.query.filter_by(learner_id=user.user_id)

    if status:
        query = query.filter_by(status=status)

    rows = query.order_by(RequestSession.created_at.desc()).all()
    return jsonify(sessions=[s.to_dict() for s in rows])


@sessions_bp.get("/<int:session_id>")
@jwt_required()
def get_session(session_id):
    user = _current_user()
    session_row = _session_or_403(session_id, user)
    if session_row is None:
        return jsonify(error="not your session"), 403
    return jsonify(session=session_row.to_dict(detail=True))


# ---------------------------------------------------------------
# REQ-11: tutor accepts/rejects; REQ-12: schedule on acceptance
# ---------------------------------------------------------------
@sessions_bp.post("/<int:session_id>/accept")
@jwt_required()
def accept_session(session_id):
    user = _current_user()
    session_row = _session_or_403(session_id, user, allow_roles=("tutor",))
    if session_row is None:
        return jsonify(error="not your session"), 403
    if session_row.status != "pending":
        return jsonify(error=f"cannot accept a session in '{session_row.status}' status"), 409

    data = request.get_json(silent=True) or {}
    try:
        scheduled_date = _parse_date(data.get("scheduled_date")) or session_row.preferred_date
        scheduled_time = _parse_time(data.get("scheduled_time")) or session_row.preferred_time
    except ValueError:
        return jsonify(error="scheduled_date must be YYYY-MM-DD and scheduled_time HH:MM"), 400

    session_row.status = "accepted"
    session_row.scheduled_date = scheduled_date
    session_row.scheduled_time = scheduled_time
    db.session.commit()

    notify(
        session_row.learner,
        "session_accepted",
        f"{user.name} accepted your session request for "
        f"{session_row.topic.skill_name} — {session_row.topic.topic_name}.",
        related_id=session_row.request_id,
        email_subject="Your SkillSphere session request was accepted",
    )
    return jsonify(message="session accepted", session=session_row.to_dict(detail=True))


@sessions_bp.post("/<int:session_id>/reject")
@jwt_required()
def reject_session(session_id):
    user = _current_user()
    session_row = _session_or_403(session_id, user, allow_roles=("tutor",))
    if session_row is None:
        return jsonify(error="not your session"), 403
    if session_row.status != "pending":
        return jsonify(error=f"cannot reject a session in '{session_row.status}' status"), 409

    data = request.get_json(silent=True) or {}
    session_row.status = "rejected"
    session_row.reject_reason = (data.get("reason") or "").strip() or None
    db.session.commit()

    notify(
        session_row.learner,
        "session_rejected",
        f"{user.name} was unable to accept your session request for "
        f"{session_row.topic.skill_name} — {session_row.topic.topic_name}.",
        related_id=session_row.request_id,
        email_subject="Your SkillSphere session request was declined",
    )
    return jsonify(message="session rejected", session=session_row.to_dict(detail=True))


@sessions_bp.post("/<int:session_id>/cancel")
@jwt_required()
def cancel_session(session_id):
    user = _current_user()
    session_row = _session_or_403(session_id, user)
    if session_row is None:
        return jsonify(error="not your session"), 403
    if session_row.status not in ("pending", "accepted"):
        return jsonify(error=f"cannot cancel a session in '{session_row.status}' status"), 409

    session_row.status = "cancelled"
    db.session.commit()

    other_party = session_row.tutor if user.user_id == session_row.learner_id else session_row.learner
    notify(
        other_party,
        "session_cancelled",
        f"{user.name} cancelled the session on {session_row.topic.skill_name} — {session_row.topic.topic_name}.",
        related_id=session_row.request_id,
        email_subject="A SkillSphere session was cancelled",
    )

    # A cancellation after acceptance counts against the tutor's completion rate (REQ-15).
    recalculate_trust_score(session_row.tutor_id)

    return jsonify(message="session cancelled", session=session_row.to_dict(detail=True))


# ---------------------------------------------------------------
# REQ-9 / REQ-21: tutor closes the session
# ---------------------------------------------------------------
@sessions_bp.post("/<int:session_id>/complete")
@jwt_required()
def complete_session(session_id):
    user = _current_user()
    session_row = _session_or_403(session_id, user, allow_roles=("tutor",))
    if session_row is None:
        return jsonify(error="not your session"), 403
    if session_row.status != "accepted":
        return jsonify(error="only an accepted session can be marked complete"), 409

    data = request.get_json(silent=True) or {}
    attended = data.get("attended")
    if attended is None:
        return jsonify(error="'attended' (true/false) is required"), 400

    session_row.session_notes = (data.get("session_notes") or "").strip()
    session_row.attended = bool(attended)
    session_row.status = "completed"

    # REQ-21: mark the topic completed on the learner's progress checklist.
    if session_row.attended:
        progress = Progress.query.filter_by(
            learner_id=session_row.learner_id, topic_id=session_row.topic_id
        ).first()
        if progress:
            progress.status = "completed"
        else:
            progress = Progress(
                learner_id=session_row.learner_id, topic_id=session_row.topic_id, status="completed"
            )
            db.session.add(progress)

    db.session.commit()

    # REQ-9: generate the session summary from the tutor's notes.
    summary = generate_session_summary(session_row)
    lines = [f"Summary: {summary['summary']}"]
    if summary["key_concepts"]:
        lines.append("Key concepts: " + ", ".join(summary["key_concepts"]))
    lines.append(f"Homework: {summary['homework']}")
    if summary["recommended_next_topic"]:
        nt = summary["recommended_next_topic"]
        lines.append(f"Recommended next topic: {nt['skill_name']} — {nt['topic_name']}")
    session_row.session_summary = "\n".join(lines)
    db.session.commit()

    recalculate_trust_score(session_row.tutor_id)

    notify(
        session_row.learner,
        "session_completed",
        f"Your session on {session_row.topic.skill_name} — {session_row.topic.topic_name} is complete. "
        "Please leave a rating!",
        related_id=session_row.request_id,
        email_subject="Your SkillSphere session is complete — leave a rating",
    )

    return jsonify(message="session marked complete", session=session_row.to_dict(detail=True))


@sessions_bp.get("/<int:session_id>/summary")
@jwt_required()
def get_summary(session_id):
    user = _current_user()
    session_row = _session_or_403(session_id, user)
    if session_row is None:
        return jsonify(error="not your session"), 403
    if session_row.status != "completed":
        return jsonify(error="summary is only available once the session is completed"), 409
    return jsonify(summary=session_row.session_summary)
