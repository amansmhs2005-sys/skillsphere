from datetime import datetime
from flask import Blueprint, request, jsonify

from app.extensions import db
from app.authz import admin_required
from app.models.user import User
from app.models.request_session import RequestSession
from app.models.report import Report
from app.notifications.utils import notify

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ---------------------------------------------------------------
# User verification & suspension (business rule 5.5)
# ---------------------------------------------------------------
@admin_bp.get("/users")
@admin_required
def list_users():
    query = User.query
    if request.args.get("admin_verified") == "false":
        query = query.filter_by(admin_verified=False)
    if request.args.get("suspended") == "true":
        query = query.filter_by(is_suspended=True)
    users = query.order_by(User.created_at.desc()).all()
    return jsonify(users=[u.to_dict(include_private=True) for u in users])


@admin_bp.post("/users/<int:user_id>/verify")
@admin_required
def verify_user(user_id):
    """Admin-performed verification, distinct from the self-service email
    link (REQ-2). See schema.sql comment on users.admin_verified."""
    user = User.query.get_or_404(user_id)
    user.admin_verified = True
    db.session.commit()
    from app.trust import recalculate_trust_score

    if user.is_tutor:
        recalculate_trust_score(user.user_id)  # verification feeds 10% of REQ-15
    return jsonify(message="user verified", user=user.to_dict(include_private=True))


@admin_bp.post("/users/<int:user_id>/suspend")
@admin_required
def suspend_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_suspended = True
    db.session.commit()
    notify(user, "account_suspended", "Your SkillSphere account has been suspended by an administrator.")
    return jsonify(message="user suspended", user=user.to_dict(include_private=True))


@admin_bp.post("/users/<int:user_id>/unsuspend")
@admin_required
def unsuspend_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_suspended = False
    db.session.commit()
    return jsonify(message="user unsuspended", user=user.to_dict(include_private=True))


@admin_bp.delete("/users/<int:user_id>")
@admin_required
def delete_user(user_id):
    """Hard delete. schema.sql has ON DELETE CASCADE on every table that
    references users (skills, availability, progress, requests_sessions,
    reviews, reports, notifications, search_history), so this also
    removes everything tied to the account. There is no undo — consider
    suspend instead if you just want to stop the account being usable
    while keeping its session/review history intact."""
    from flask_jwt_extended import get_jwt_identity

    if user_id == int(get_jwt_identity()):
        return jsonify(error="you cannot delete your own account while logged in as it"), 400

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify(message="user deleted")


# ---------------------------------------------------------------
# REQ-17: review flagged reports
# ---------------------------------------------------------------
@admin_bp.get("/reports")
@admin_required
def list_reports():
    status = request.args.get("status", "open")
    query = Report.query
    if status != "all":
        query = query.filter_by(status=status)
    reports = query.order_by(Report.created_at.desc()).all()
    return jsonify(reports=[r.to_dict() for r in reports])


@admin_bp.post("/reports/<int:report_id>/resolve")
@admin_required
def resolve_report(report_id):
    report = Report.query.get_or_404(report_id)
    data = request.get_json(silent=True) or {}
    status = data.get("status")  # "reviewed" | "dismissed"
    action = (data.get("action") or "").strip()
    suspend_user_id = data.get("suspend_user_id")

    if status not in ("reviewed", "dismissed"):
        return jsonify(error="status must be 'reviewed' or 'dismissed'"), 400

    report.status = status
    report.admin_action = action or None
    report.resolved_at = datetime.utcnow()

    if suspend_user_id:
        target = User.query.get_or_404(suspend_user_id)
        target.is_suspended = True
        notify(target, "account_suspended", "Your SkillSphere account has been suspended by an administrator.")

    db.session.commit()
    return jsonify(message="report resolved", report=report.to_dict())


# ---------------------------------------------------------------
# Platform activity monitor
# ---------------------------------------------------------------
@admin_bp.get("/stats")
@admin_required
def stats():
    return jsonify(
        users={
            "total": User.query.count(),
            "pending_admin_verification": User.query.filter_by(admin_verified=False).count(),
            "suspended": User.query.filter_by(is_suspended=True).count(),
        },
        sessions={
            status: RequestSession.query.filter_by(status=status).count()
            for status in ("pending", "accepted", "rejected", "completed", "cancelled")
        },
        reports={"open": Report.query.filter_by(status="open").count()},
    )
