from flask import current_app
from flask_mail import Message
from app.extensions import mail


def send_email(subject: str, recipients: list, html: str) -> None:
    """REQ-19 / REQ-2: SMTP-based email notifications.

    In local dev (MAIL_SUPPRESS_SEND=true) this just logs instead of
    calling out to a real SMTP server, matching the .env.example default.
    """
    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        current_app.logger.info("[DEV EMAIL] to=%s subject=%s\n%s", recipients, subject, html)
        return

    msg = Message(subject=subject, recipients=recipients, html=html)
    mail.send(msg)
