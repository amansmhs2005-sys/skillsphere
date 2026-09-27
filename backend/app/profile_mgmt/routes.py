from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.user import User
from app.models.availability import Availability, DAYS
from app.models.progress import Progress

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


def _current_user() -> User:
    return User.query.get_or_404(int(get_jwt_identity()))


@profile_bp.get("")
@jwt_required()
def get_profile():
    return jsonify(user=_current_user().to_dict())


@profile_bp.get("/<int:user_id>")
def get_public_profile(user_id):
    """Public profile view (e.g. a learner viewing a tutor's profile)."""
    user = User.query.get_or_404(user_id)
    return jsonify(user=user.to_dict())


@profile_bp.put("")
@jwt_required()
def update_profile():
    """REQ-3: edit profile — name, academic details, short bio."""
    user = _current_user()
    data = request.get_json(silent=True) or {}

    if "name" in data:
        name = (data["name"] or "").strip()
        if not name:
            return jsonify(error="name cannot be empty"), 400
        user.name = name
    if "branch" in data:
        user.branch = data["branch"]
    if "year" in data:
        user.year = data["year"]
    if "bio" in data:
        user.bio = data["bio"]
    if "is_learner" in data or "is_tutor" in data:
        is_learner = data.get("is_learner", user.is_learner)
        is_tutor = data.get("is_tutor", user.is_tutor)
        if not is_learner and not is_tutor:
            return jsonify(error="a user must be at least a learner or a tutor"), 400
        user.is_learner = is_learner
        user.is_tutor = is_tutor

    db.session.commit()
    return jsonify(message="profile updated", user=user.to_dict())


# ---------------------------------------------------------------
# Availability  (REQ-18)
# ---------------------------------------------------------------
@profile_bp.get("/availability")
@jwt_required()
def list_availability():
    user = _current_user()
    slots = Availability.query.filter_by(tutor_id=user.user_id).all()
    return jsonify(availability=[s.to_dict() for s in slots])


@profile_bp.post("/availability")
@jwt_required()
def add_availability():
    user = _current_user()
    if not user.is_tutor:
        return jsonify(error="only tutors can set availability"), 403

    data = request.get_json(silent=True) or {}
    day = data.get("day")
    start_time = data.get("start_time")  # "HH:MM"
    end_time = data.get("end_time")

    if day not in DAYS:
        return jsonify(error=f"day must be one of {DAYS}"), 400
    try:
        start = datetime.strptime(start_time, "%H:%M").time()
        end = datetime.strptime(end_time, "%H:%M").time()
    except (TypeError, ValueError):
        return jsonify(error="start_time and end_time must be in HH:MM format"), 400
    if start >= end:
        return jsonify(error="start_time must be before end_time"), 400

    slot = Availability(tutor_id=user.user_id, day=day, start_time=start, end_time=end)
    db.session.add(slot)
    db.session.commit()
    return jsonify(message="availability added", availability=slot.to_dict()), 201


@profile_bp.delete("/availability/<int:availability_id>")
@jwt_required()
def delete_availability(availability_id):
    user = _current_user()
    slot = Availability.query.get_or_404(availability_id)
    if slot.tutor_id != user.user_id:
        return jsonify(error="not your availability slot"), 403

    db.session.delete(slot)
    db.session.commit()
    return jsonify(message="availability removed")


# ---------------------------------------------------------------
# Progress checklist  (REQ-20)
# ---------------------------------------------------------------
@profile_bp.get("/progress")
@jwt_required()
def get_progress():
    user = _current_user()
    rows = Progress.query.filter_by(learner_id=user.user_id).all()
    return jsonify(progress=[r.to_dict() for r in rows])
