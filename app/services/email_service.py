import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
from app.database import log_email

logger = logging.getLogger(__name__)


async def send_flag_email(
    creative_id: int,
    email_to: str,
    advertiser: str,
    creative_name: str,
    creative_title: str,
    fail_reason: str,
    note: str = "",
):
    """Send an email to the AM about a flagged creative."""
    subject = f"Flagged Creative: {advertiser} — {creative_name}"

    body = f"""Hi,

A creative has been flagged during compliance review and requires your attention.

Advertiser: {advertiser}
Creative: {creative_name}
Title: {creative_title}

Issues Found:
{fail_reason}

{('Note from reviewer: ' + note) if note else ''}

Please review this creative and take appropriate action.

— Rokt Creative Compliance Audit
"""

    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning(
            f"SMTP not configured. Would have sent email to {email_to}: {subject}"
        )
        await log_email(creative_id, email_to, subject, body, status="skipped_no_smtp")
        return True

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_FROM
        msg["To"] = email_to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        await log_email(creative_id, email_to, subject, body, status="sent")
        logger.info(f"Email sent to {email_to} for creative {creative_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {email_to}: {e}")
        await log_email(creative_id, email_to, subject, body, status=f"failed: {str(e)}")
        return False
