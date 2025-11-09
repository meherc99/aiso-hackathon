"""
Check for upcoming meetings (within 15 minutes) and send Slack notifications
to the appropriate channels.
All times are displayed in Amsterdam time (Europe/Amsterdam timezone).
"""
import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from database import get_default_db

load_dotenv()

# Amsterdam timezone
AMSTERDAM_TZ = ZoneInfo("Europe/Amsterdam")


def _parse_meeting_datetime(date_str: str, time_str: str):
    """Return a timezone-aware datetime (Amsterdam time) or None."""
    if not date_str or not time_str:
        return None
    try:
        # Parse as naive datetime
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        # Assume input is in Amsterdam time
        return dt.replace(tzinfo=AMSTERDAM_TZ)
    except Exception:
        try:
            dt = datetime.fromisoformat(f"{date_str}T{time_str}")
            if dt.tzinfo is None:
                # Assume Amsterdam time if no timezone info
                dt = dt.replace(tzinfo=AMSTERDAM_TZ)
            else:
                # Convert to Amsterdam time
                dt = dt.astimezone(AMSTERDAM_TZ)
            return dt
        except Exception:
            return None


def find_upcoming_meetings(within_minutes: int = 15):
    """
    Return meetings from the DB that start within the next `within_minutes` minutes.
    Returns list of tuples: (meeting_dict, datetime_object)
    """
    db = get_default_db()
    results = []
    now = datetime.now(AMSTERDAM_TZ)
    seen_keys: set[tuple[str, str, str, str]] = set()
    duplicates: list[str] = []

    for m in db.get_all_meetings():
        if m.get("category") and m.get("category") != "meetings":
            continue
        channel_id = m.get("channel_id")
        if not channel_id:
            continue
        if m.get("notified"):
            continue
        if m.get("meeting_completed"):
            continue
        date_str = m.get("date_of_meeting")
        time_str = m.get("start_time") or m.get("start") or m.get("time")
        dt = _parse_meeting_datetime(date_str, time_str)
        if not dt:
            continue

        if dt < now:
            meeting_id = m.get("id")
            if meeting_id:
                db.update_meeting(meeting_id, {"meeting_completed": True, "notified": True})
            continue

        delta = dt - now
        if timedelta(0) <= delta <= timedelta(minutes=within_minutes):
            key = (
                channel_id,
                date_str or "",
                (time_str or "").strip(),
                (m.get("title") or "").strip().lower(),
            )
            if key in seen_keys:
                meeting_id = m.get("id")
                if meeting_id:
                    duplicates.append(meeting_id)
                continue
            seen_keys.add(key)
            results.append((m, dt))

    for meeting_id in duplicates:
        db.update_meeting(meeting_id, {"notified": True})
    
    return results


def get_channel_members(channel_id: str, client: WebClient):
    """
    Get all members of a channel.
    
    Args:
        channel_id: The Slack channel ID
        client: WebClient instance
        
    Returns:
        List of user IDs in the channel
    """
    try:
        response = client.conversations_members(channel=channel_id)
        return response.get("members", [])
    except SlackApiError as e:
        print(f"Error fetching channel members for {channel_id}: {e.response['error']}")
        return []


def send_slack_notification(channel_id: str, meeting: dict, dt: datetime, client: WebClient):
    """Send a Slack message to the specified channel about the upcoming meeting."""
    title = meeting.get("title", "Untitled Meeting")
    description = meeting.get("description", "No description provided.")
    
    # Format time in Amsterdam timezone
    human_time = dt.strftime("%Y-%m-%d %H:%M")
    timezone_name = dt.strftime("%Z")  # Will show CET or CEST
    
    # Calculate minutes until meeting
    now = datetime.now(AMSTERDAM_TZ)
    minutes_until = int((dt - now).total_seconds() / 60)
    
    # Get created_at timestamp and convert to Amsterdam time if it exists
    created_at = meeting.get("created_at", "")
    created_at_formatted = ""
    if created_at:
        try:
            # Parse ISO format timestamp
            created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            # Convert to Amsterdam time
            created_dt = created_dt.astimezone(AMSTERDAM_TZ)
            created_at_formatted = f"\n*Created:* {created_dt.strftime('%Y-%m-%d %H:%M:%S')} {created_dt.strftime('%Z')}"
        except Exception:
            pass
    
    # Get all channel members and create mentions
    members = get_channel_members(channel_id, client)
    
    # Get bot user ID to exclude it from mentions
    bot_user_id = os.getenv("SLACK_BOT_USER_ID", "")
    
    # Filter out the bot itself from mentions
    user_mentions = [f"<@{user_id}>" for user_id in members if user_id != bot_user_id]
    mentions_string = " ".join(sorted(set(user_mentions)))
    if not mentions_string:
        mentions_string = "<!channel>"
    
    # Build message with Slack formatting
    message = f"""
{mentions_string}

*Upcoming Meeting Reminder*

*Title:* {title}
*Time:* {human_time} {timezone_name}
*Starts in:* {minutes_until} minute(s)
*Description:* {description}{created_at_formatted}

Don't forget to join!
    """.strip()
    
    try:
        response = client.chat_postMessage(
            channel=channel_id,
            text=message,
            unfurl_links=False,
            unfurl_media=False
        )
        return True
    except SlackApiError as e:
        print(f"Error sending message to {channel_id}: {e.response['error']}")
        return False


def get_channel_for_meeting(meeting: dict):
    """
    Determine which Slack channel this meeting belongs to.
    Returns the channel_id if stored in the meeting, else None.
    """
    return meeting.get("channel_id")


def main():
    # Initialize Slack client with increased timeout
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        print("Error: SLACK_BOT_TOKEN not found in environment")
        return 2
    
    client = WebClient(token=token, timeout=60)
    
    # Find upcoming meetings
    upcoming = find_upcoming_meetings(15)
    
    if not upcoming:
        print("No upcoming meetings within 15 minutes.")
        return 0
    
    print(f"Found {len(upcoming)} upcoming meeting(s)")
    
    # Track which meetings we've notified about
    db = get_default_db()
    
    # Send notifications
    success_count = 0
    for meeting, dt in upcoming:
        meeting_id = meeting.get("id")
        channel_id = get_channel_for_meeting(meeting)
        
        if not channel_id:
            print(f"Warning: No channel_id for meeting '{meeting.get('title')}' (ID: {meeting_id})")
            continue
        
        # Check if we've already notified about this meeting
        if meeting.get("notified"):
            print(f"Already notified for meeting '{meeting.get('title')}'")
            continue
        
        # Send notification
        print(f"Sending notification to channel {channel_id} for meeting '{meeting.get('title')}'")
        if send_slack_notification(channel_id, meeting, dt, client):
            # Mark as notified so we don't spam
            db.update_meeting(meeting_id, {"notified": True})
            success_count += 1
            print(f"Notification sent successfully")
        else:
            print(f"Failed to send notification")
    
    print(f"\nSent {success_count}/{len(upcoming)} notifications")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())