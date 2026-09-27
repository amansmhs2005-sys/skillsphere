from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db, limiter
from app.models.search_history import SearchHistory
from app.ai_engine.nlp import detect_topic, rank_tutors_for_topic, related_topics, RELEVANCE_THRESHOLD

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@ai_bp.post("/detect-topic")
@jwt_required()
@limiter.limit("10 per minute")  # 5.3: rate-limit AI/NLP queries to prevent abuse
def detect_topic_route():
    """REQ-6, REQ-7, REQ-8: analyze free text, detect the topic, rank
    tutors for it, and suggest related topics."""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify(error="'text' is required"), 400
    if len(text) > 2000:
        return jsonify(error="text is too long (max 2000 characters)"), 400

    user_id = int(get_jwt_identity())

    results = detect_topic(text)
    if not results or results[0]["score"] < RELEVANCE_THRESHOLD:
        # Log the miss too — still useful search history, and lets the
        # frontend fall back to plain keyword search (assumption 2.7).
        db.session.add(SearchHistory(user_id=user_id, query_text=text, detected_skill_id=None))
        db.session.commit()
        return jsonify(
            detected=None,
            message="No confident topic match found — try the keyword search instead.",
            tutors=[],
            related_topics=[],
        )

    top = results[0]["skill"]
    db.session.add(SearchHistory(user_id=user_id, query_text=text, detected_skill_id=top.skill_id))
    db.session.commit()

    ranked = rank_tutors_for_topic(results, top)
    related = related_topics(top, user_id)

    return jsonify(
        detected={
            "skill_name": top.skill_name,
            "topic_name": top.topic_name,
            "confidence": round(results[0]["score"], 4),
        },
        tutors=[
            {
                "skill": r["skill"].to_dict(),
                "tutor": r["tutor"].to_dict(),
                "weighted_score": r["weighted_score"],
                "breakdown": r["breakdown"],
            }
            for r in ranked
        ],
        related_topics=related,
    )
