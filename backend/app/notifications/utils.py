from app.extensions import db
from app.models.notification import Notification
from app.emailing import send_email


def notify(user, type_: str, message: str, related_id: int = None, email_subject: str = None) -> None:
    """REQ-19: notify a user in-app and via email.

    `user` is a User model instance (needs .user_id and .email).
    If email_subject is omitted, only the in-app notification is created —
    used for lower-priority updates that don't need an inbox ping.
    """
    note = Notification(
        user_id=user.user_id,
        type=type_,
        message=message,
        related_id=related_id,
    )
    db.session.add(note)
    db.session.commit()

    if email_subject:
        html = f"<p>Hi {user.name},</p><p>{message}</p>"
        send_email(email_subject, [user.email], html)
