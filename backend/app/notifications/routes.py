from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.notification import Notification

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notifications_bp.get("")
@jwt_required()
def list_notifications():
    """REQ-19: in-app notification inbox, unread first."""
    user_id = int(get_jwt_identity())
    rows = (
        Notification.query.filter_by(user_id=user_id)
        .order_by(Notification.is_read.asc(), Notification.created_at.desc())
        .limit(100)
        .all()
    )
    unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    return jsonify(notifications=[n.to_dict() for n in rows], unread_count=unread_count)


@notifications_bp.post("/<int:notification_id>/read")
@jwt_required()
def mark_read(notification_id):
    user_id = int(get_jwt_identity())
    note = Notification.query.get_or_404(notification_id)
    if note.user_id != user_id:
        return jsonify(error="not your notification"), 403
    note.is_read = True
    db.session.commit()
    return jsonify(message="marked read")


@notifications_bp.post("/read-all")
@jwt_required()
def mark_all_read():
    user_id = int(get_jwt_identity())
    Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify(message="all marked read")
