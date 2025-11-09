import os
from datetime import datetime, timezone, timedelta
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# project database access
from database import get_default_db

load_dotenv()


def _parse_meeting_datetime(date_str: str, time_str: str):
    """Return a timezone-aware datetime (UTC) or None."""
    if not date_str or not time_str:
        return None
    try:
        # Expecting date YYYY-MM-DD and time HH:MM
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        try:
            # Fallback to ISO parsing
            dt = datetime.fromisoformat(f"{date_str}T{time_str}")
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None


def find_upcoming_meetings(within_minutes: int = 15):
    """Return meetings from the DB that start within the next `within_minutes` minutes."""
    db = get_default_db()
    results = []
    now = datetime.now(timezone.utc)

    for m in db.get_all_meetings():
        date_str = m.get("date_of_meeting")
        time_str = m.get("start_time") or m.get("start") or m.get("time")
        dt = _parse_meeting_datetime(date_str, time_str)
        if not dt:
            continue

        delta = dt - now
        if timedelta(0) <= delta <= timedelta(minutes=within_minutes):
            results.append((m, dt))
    return results


def send_email(subject: str, body: str, to_address: str):
    host = os.getenv("EMAIL_SMTP_HOST")
    port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    user = os.getenv("EMAIL_SMTP_USER")
    password = os.getenv("EMAIL_SMTP_PASSWORD")
    from_addr = os.getenv("EMAIL_FROM", user)

    if not (host and port and user and password and from_addr):
        raise RuntimeError("SMTP configuration incomplete in environment variables")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_address
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.ehlo()
        if port == 587:
            smtp.starttls()
            smtp.ehlo()
        smtp.login(user, password)
        smtp.send_message(msg)


def _format_meeting_entry(meeting: dict, dt: datetime) -> str:
    """Return a human readable string with date/time, title and description."""
    title = meeting.get("title", "Untitled")
    description = meeting.get("description", "").strip() or "No description provided."
    # Human readable time (UTC)
    human_ts = dt.strftime("%Y-%m-%d %H:%M UTC")
    iso_ts = dt.isoformat()
    lines = [
        f"Title      : {title}",
        f"Date & Time: {human_ts}  (ISO: {iso_ts})",
        f"Description: {description}"
    ]
    return "\n".join(lines)


def build_message(upcoming):
    lines = []
    for m, dt in upcoming:
        lines.append(_format_meeting_entry(m, dt))
        lines.append("-" * 40)
    body = "Upcoming meetings in the next 15 minutes:\n\n" + "\n".join(lines)
    return body


def main():
    to_addr = os.getenv("ALERT_TO", "pctirziu@gmail.com")
    upcoming = find_upcoming_meetings(15)
    if not upcoming:
        print("No upcoming meetings within 15 minutes.")
        return 0

    subject = f"[Reminder] {len(upcoming)} meeting(s) starting soon"
    body = build_message(upcoming)
    try:
        send_email(subject, body, to_addr)
        print(f"Sent alert to {to_addr}")
        return 0
    except Exception as e:
        print("Failed to send email:", e)
        return 2


if __name__ == "__main__":
    import sys
    sys.exit(main())