"""
notification.py
----------------
Generates and stores alerts when a plant crosses a critical threshold.
Supports desktop notifications (via plyer, optional/best-effort) and
always logs to the database so the dashboard can show a notification feed
even on headless machines or when plyer isn't available.

Email alerts are implemented as a clearly-labeled stub: sending real email
requires SMTP credentials that don't belong hardcoded in a portfolio repo.
The function is fully wired so a user can drop in their own credentials.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import get_connection, now_iso

THRESHOLDS = {
    "water_critical": 15,      # below this %, water is critically low
    "temperature_high": 38,    # above this °C, heat alert
    "health_critical_score": 30,
}


def check_and_notify(plant_id: int, plant_name: str, water_level: float,
                      temperature: float, health_score: float, health_status: str) -> list:
    """
    Evaluate thresholds and create notifications for any that are breached.
    Returns the list of newly created notification messages.
    """
    new_alerts = []

    if water_level <= THRESHOLDS["water_critical"]:
        new_alerts.append(("Water level critically low — irrigate immediately.", "high"))

    if temperature >= THRESHOLDS["temperature_high"]:
        new_alerts.append(("Temperature exceeds safe threshold for this species.", "high"))

    if health_status == "Critical":
        new_alerts.append(("Plant health is in the CRITICAL zone.", "high"))
    elif health_status == "Dead":
        new_alerts.append(("Plant health has reached zero — plant has died.", "critical"))

    for message, severity in new_alerts:
        _store_notification(plant_id, message, severity)
        _send_desktop_notification(plant_name, message)

    return [m for m, _ in new_alerts]


def _store_notification(plant_id: int, message: str, severity: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO Notifications (plant_id, message, severity, created_at, is_read) "
            "VALUES (?, ?, ?, ?, 0)",
            (plant_id, message, severity, now_iso()),
        )


def _send_desktop_notification(plant_name: str, message: str):
    """
    Best-effort desktop notification using plyer. Silently no-ops if plyer
    isn't installed or the OS doesn't support it (e.g. some Linux/CI envs) —
    desktop notification failures should never crash the simulation.
    """
    try:
        from plyer import notification
        notification.notify(
            title=f"Plant Alert: {plant_name}",
            message=message,
            timeout=6,
        )
    except Exception:
        pass  # Desktop notifications are a nice-to-have, not critical path


def send_email_alert(to_email: str, subject: str, body: str,
                      smtp_server: str = None, smtp_port: int = 587,
                      smtp_user: str = None, smtp_password: str = None) -> bool:
    """
    Send an email alert via SMTP. Requires the caller to supply SMTP
    credentials (e.g. from environment variables) — none are hardcoded
    here for security. Returns True on success, False otherwise.

    Example usage:
        send_email_alert(
            to_email="user@example.com",
            subject="Plant Alert",
            body="Your rose needs water.",
            smtp_server="smtp.gmail.com",
            smtp_user=os.environ.get("PLANT_APP_EMAIL"),
            smtp_password=os.environ.get("PLANT_APP_EMAIL_PASSWORD"),
        )
    """
    if not all([smtp_server, smtp_user, smtp_password]):
        return False  # Not configured — caller should check the return value

    import smtplib
    from email.mime.text import MIMEText

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_email

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, [to_email], msg.as_string())
        return True
    except Exception:
        return False


def get_unread_notifications(plant_id: int) -> list:
    """Return unread notifications for a plant, most recent first."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM Notifications WHERE plant_id = ? AND is_read = 0 "
            "ORDER BY created_at DESC",
            (plant_id,),
        ).fetchall()
        return [dict(r) for r in rows]
