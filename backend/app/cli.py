from datetime import datetime, timedelta
import click

from app.extensions import db
from app.models.request_session import RequestSession
from app.notifications.utils import notify


def register_cli(app):
    @app.cli.command("send-reminders")
    def send_reminders():
        """REQ-19: notify both parties when an accepted session starts
        within the next 24 hours. Intended to be run periodically via
        cron (e.g. every 15-30 minutes) — see README."""
        now = datetime.utcnow()
        window_end = now + timedelta(hours=24)

        candidates = RequestSession.query.filter_by(status="accepted", reminder_sent=False).all()
        sent = 0
        for s in candidates:
            if not s.scheduled_date or not s.scheduled_time:
                continue
            scheduled_at = datetime.combine(s.scheduled_date, s.scheduled_time)
            if now <= scheduled_at <= window_end:
                topic_label = f"{s.topic.skill_name} — {s.topic.topic_name}" if s.topic else "your session"
                message = f"Reminder: your session on {topic_label} starts at {scheduled_at.strftime('%Y-%m-%d %H:%M')}."
                notify(s.learner, "session_reminder", message, related_id=s.request_id, email_subject="Upcoming SkillSphere session")
                notify(s.tutor, "session_reminder", message, related_id=s.request_id, email_subject="Upcoming SkillSphere session")
                s.reminder_sent = True
                sent += 1

        db.session.commit()
        click.echo(f"Sent reminders for {sent} upcoming session(s).")
