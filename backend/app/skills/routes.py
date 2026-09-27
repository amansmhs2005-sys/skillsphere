from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_

from app.extensions import db
from app.models.user import User
from app.models.skill import Skill

skills_bp = Blueprint("skills", __name__, url_prefix="/api/skills")

VALID_DIFFICULTIES = ("beginner", "intermediate", "advanced")


def _current_user() -> User:
    return User.query.get_or_404(int(get_jwt_identity()))


@skills_bp.get("/mine")
@jwt_required()
def my_skills():
    user = _current_user()
    rows = Skill.query.filter_by(tutor_id=user.user_id).all()
    return jsonify(skills=[s.to_dict() for s in rows])


@skills_bp.post("")
@jwt_required()
def add_skill():
    """REQ-4: add a skill/topic the user is able to tutor."""
    user = _current_user()
    if not user.is_tutor:
        return jsonify(error="only tutors can add skills"), 403

    data = request.get_json(silent=True) or {}
    skill_name = (data.get("skill_name") or "").strip()
    topic_name = (data.get("topic_name") or "").strip()
    difficulty = data.get("difficulty", "beginner")
    description = data.get("description", "")

    if not skill_name or not topic_name:
        return jsonify(error="skill_name and topic_name are required"), 400
    if difficulty not in VALID_DIFFICULTIES:
        return jsonify(error=f"difficulty must be one of {VALID_DIFFICULTIES}"), 400

    skill = Skill(
        tutor_id=user.user_id,
        skill_name=skill_name,
        topic_name=topic_name,
        difficulty=difficulty,
        description=description,
    )
    db.session.add(skill)
    db.session.commit()
    return jsonify(message="skill added", skill=skill.to_dict()), 201


@skills_bp.put("/<int:skill_id>")
@jwt_required()
def edit_skill(skill_id):
    """REQ-4: edit a skill/topic."""
    user = _current_user()
    skill = Skill.query.get_or_404(skill_id)
    if skill.tutor_id != user.user_id:
        return jsonify(error="not your skill"), 403

    data = request.get_json(silent=True) or {}
    if "skill_name" in data:
        skill.skill_name = (data["skill_name"] or "").strip() or skill.skill_name
    if "topic_name" in data:
        skill.topic_name = (data["topic_name"] or "").strip() or skill.topic_name
    if "difficulty" in data:
        if data["difficulty"] not in VALID_DIFFICULTIES:
            return jsonify(error=f"difficulty must be one of {VALID_DIFFICULTIES}"), 400
        skill.difficulty = data["difficulty"]
    if "description" in data:
        skill.description = data["description"]

    db.session.commit()
    return jsonify(message="skill updated", skill=skill.to_dict())


@skills_bp.delete("/<int:skill_id>")
@jwt_required()
def remove_skill(skill_id):
    """REQ-4: remove a skill/topic."""
    user = _current_user()
    skill = Skill.query.get_or_404(skill_id)
    if skill.tutor_id != user.user_id:
        return jsonify(error="not your skill"), 403

    db.session.delete(skill)
    db.session.commit()
    return jsonify(message="skill removed")


@skills_bp.get("/search")
def search_skills():
    """REQ-5: free-text / keyword-based topic search.

    This is deliberately a plain SQL keyword match, not the AI/NLP
    topic-detection engine described in REQ-6/REQ-7 (Section 4.2) —
    that is a separate module and can call into this same table.
    """
    query = (request.args.get("q") or "").strip()
    difficulty = request.args.get("difficulty")

    if not query:
        return jsonify(error="query parameter 'q' is required"), 400

    like = f"%{query}%"
    q = Skill.query.filter(
        or_(
            Skill.skill_name.ilike(like),
            Skill.topic_name.ilike(like),
            Skill.description.ilike(like),
        )
    )
    if difficulty:
        if difficulty not in VALID_DIFFICULTIES:
            return jsonify(error=f"difficulty must be one of {VALID_DIFFICULTIES}"), 400
        q = q.filter(Skill.difficulty == difficulty)

    results = q.order_by(Skill.skill_name).limit(50).all()
    return jsonify(results=[s.to_dict(include_tutor=True) for s in results])
