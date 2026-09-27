import secrets
from flask import current_app, render_template_string
from app.emailing import send_email

VERIFY_EMAIL_TEMPLATE = """
<p>Hi {{ name }},</p>
<p>Welcome to SkillSphere. Please confirm your institutional email address
by clicking the link below:</p>
<p><a href="{{ link }}">{{ link }}</a></p>
<p>If you did not create this account, you can ignore this email.</p>
"""


def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)


def is_institutional_email(email: str) -> bool:
    """REQ-1: registration must use the institutional email domain."""
    domain = current_app.config["ALLOWED_EMAIL_DOMAIN"].lower()
    return email.lower().strip().endswith("@" + domain)


def send_verification_email(user) -> None:
    """REQ-2: verify a new account via an email confirmation link."""
    link = f"{current_app.config['FRONTEND_BASE_URL']}/verify-email?token={user.verification_token}"
    html = render_template_string(VERIFY_EMAIL_TEMPLATE, name=user.name, link=link)
    send_email("Verify your SkillSphere account", [user.email], html)
