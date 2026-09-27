from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity

from app.models.user import User


def admin_required(fn):
    """Business rule 5.5: only the Admin role may verify/suspend accounts
    and review reports."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if not claims.get("is_admin"):
            return jsonify(error="admin access required"), 403
        return fn(*args, **kwargs)

    return wrapper


def current_user() -> User:
    return User.query.get_or_404(int(get_jwt_identity()))
