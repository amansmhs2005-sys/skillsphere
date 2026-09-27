from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from email_validator import validate_email, EmailNotValidError

from app.extensions import db
from app.models.user import User
from app.auth.utils import (
    is_institutional_email,
    generate_verification_token,
    send_verification_email,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    """REQ-1, REQ-2: register with institutional email + password,
    create a pending (unverified) account, send a verification email."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role", "learner")  # "learner" | "tutor" | "both"

    if not name or not email or not password:
        return jsonify(error="name, email and password are required"), 400

    if len(password) < 8:
        return jsonify(error="password must be at least 8 characters"), 400

    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError as e:
        return jsonify(error=str(e)), 400

    if not is_institutional_email(email):
        domain = current_app.config["ALLOWED_EMAIL_DOMAIN"]
        return jsonify(error=f"registration requires a {domain} email address"), 400

    if User.query.filter_by(email=email).first():
        return jsonify(error="an account with this email already exists"), 409

    user = User(
        name=name,
        email=email,
        is_learner=role in ("learner", "both"),
        is_tutor=role in ("tutor", "both"),
        is_verified=False,
        verification_token=generate_verification_token(),
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    send_verification_email(user)

    return jsonify(
        message="Account created. Check your email to verify your account.",
        user=user.to_dict(),
    ), 201


@auth_bp.post("/verify-email")
def verify_email():
    """REQ-2: activate the account once the verification link is clicked."""
    data = request.get_json(silent=True) or {}
    token = data.get("token") or request.args.get("token")

    if not token:
        return jsonify(error="verification token is required"), 400

    user = User.query.filter_by(verification_token=token).first()
    if not user:
        return jsonify(error="invalid or expired verification token"), 400

    user.is_verified = True
    user.verification_token = None
    db.session.commit()

    return jsonify(message="Email verified. You can now log in.")


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify(error="invalid email or password"), 401

    if not user.is_verified:
        # Business rule 5.5: unverified accounts have read-only access.
        return jsonify(error="please verify your email before logging in"), 403

    if user.is_suspended:
        return jsonify(error="this account has been suspended by an administrator"), 403

    token = create_access_token(
        identity=str(user.user_id),
        additional_claims={"is_admin": user.is_admin},
    )
    return jsonify(access_token=token, user=user.to_dict(include_private=True))


@auth_bp.get("/me")
@jwt_required()
def me():
    user = User.query.get_or_404(int(get_jwt_identity()))
    return jsonify(user=user.to_dict(include_private=True))
