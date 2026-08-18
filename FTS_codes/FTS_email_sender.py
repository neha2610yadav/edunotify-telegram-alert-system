"""SMTP email delivery for student Telegram-account linking."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr

from FTS_config import get_config_value


def _smtp_settings():
    host = get_config_value("SMTP_HOST") or "smtp.gmail.com"
    port_text = get_config_value("SMTP_PORT") or "587"
    username = get_config_value("SMTP_USERNAME")
    password = get_config_value("SMTP_PASSWORD")
    sender = get_config_value("SMTP_FROM_EMAIL") or username
    sender_name = get_config_value("SMTP_FROM_NAME") or "EduNotify Faculty Communication"
    try:
        port = int(port_text)
    except ValueError:
        return None
    if not username or not password or not sender:
        return None
    return host, port, username, password, sender, sender_name


def _valid_email(address):
    _name, parsed_address = parseaddr(address or "")
    return parsed_address == (address or "").strip() and "@" in parsed_address


def send_email_message(receiver_email, subject, html_message, plain_message=None):
    """Send a HTML email using configured SMTP credentials."""
    if not receiver_email:
        return "Failed: No email address registered for this student"
    if not _valid_email(receiver_email):
        return "Failed: Invalid student email address"

    settings = _smtp_settings()
    if not settings:
        return "Failed: SMTP configuration is missing. Check the .env file"
    host, port, username, password, sender, sender_name = settings

    email = MIMEMultipart("alternative")
    email["From"] = f"{sender_name} <{sender}>"
    email["To"] = receiver_email
    email["Subject"] = subject
    email.attach(MIMEText(plain_message or "Please view this email in HTML format.", "plain", "utf-8"))
    email.attach(MIMEText(html_message, "html", "utf-8"))

    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(email)
        return "Sent"
    except smtplib.SMTPAuthenticationError:
        return "Failed: SMTP authentication failed. Use a Gmail App Password"
    except smtplib.SMTPException as error:
        return f"Failed: Unable to send email ({error})"
    except OSError:
        return "Failed: SMTP server is unavailable or the network is offline"


def send_telegram_link_email(student_name, receiver_email, telegram_link):
    """Send a student-specific Telegram deep link through email."""
    if not telegram_link:
        return "Failed: Telegram linking URL could not be generated"

    html_message = f"""
    <html><body style=\"font-family:Segoe UI,Arial,sans-serif;color:#1f2937;\">
      <p>Hello {student_name},</p>
      <p>Your faculty has invited you to connect your Telegram account with the Faculty–Student Communication System.</p>
      <p><a href=\"{telegram_link}\" style=\"display:inline-block;padding:12px 20px;background:#1e3c72;color:#ffffff;text-decoration:none;border-radius:6px;font-weight:bold;\">Connect Telegram</a></p>
      <p>After Telegram opens, press <strong>START</strong>. If START does not appear, open the bot and type <code>/start</code>.</p>
      <p>Backup link:<br><a href=\"{telegram_link}\">{telegram_link}</a></p>
      <p>Regards,<br>Faculty–Student Communication System</p>
    </body></html>
    """
    plain_message = (
        f"Hello {student_name},\n\nOpen this Telegram link and press START to connect:\n"
        f"{telegram_link}\n\nRegards,\nFaculty–Student Communication System"
    )
    return send_email_message(
        receiver_email,
        "Connect Your Telegram Account",
        html_message,
        plain_message,
    )
