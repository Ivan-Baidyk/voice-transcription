"""Email notification service for deactivation alerts."""

import logging
from email.mime.text import MIMEText
from smtplib import SMTP

from app.config import settings

logger = logging.getLogger(__name__)


async def send_deactivation_email(
    to_email: str,
    user_email: str,
    user_id: int,
    count: int,
) -> None:
    """Send notification when a user reaches their transcription limit."""
    if not settings.smtp_host:
        return

    subject = f"User {user_email} deactivated — limit reached ({count} transcriptions)"
    body = f"""
    User {user_email} (ID: {user_id}) has been deactivated
    after reaching the transcription limit of {settings.transcription_limit}.

    Total transcriptions: {count}

    To reactivate, update the user in the admin panel.
    """

    msg = MIMEText(body.strip())
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = to_email

    try:
        with SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        logger.info("Deactivation email sent to %s about user %s", to_email, user_email)
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        raise
