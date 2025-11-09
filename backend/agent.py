import os
import sys
from pathlib import Path
import json
import re
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

from check_meetings import check_for_meetings, check_for_tasks
from parse_messages import parse_messages_list
from slack import fetch_all_messages, get_user_channels
from database import get_default_db


def _load_env() -> None:
    """Ensure the project-level .env file is loaded regardless of cwd."""
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"
    # Only attempt to load if the file exists; this keeps CI runs happy.
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    else:
        load_dotenv(override=False)


def _create_openai_client() -> OpenAI:
    """Create and return an OpenAI client configured for the custom endpoint."""
    key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
    if not key:
        raise RuntimeError(
            "No OpenAI API key provided. Set OPENAI_API_KEY or API_KEY in the environment."
        )

    base_url = os.getenv(
        "OPENAI_BASE_URL",
        "https://fj7qg3jbr3.execute-api.eu-west-1.amazonaws.com/v1",
    )
    return OpenAI(api_key=key, base_url=base_url)


def process_channel(channel_id: str, client: OpenAI, db) -> dict:
    """
    Process a single channel: fetch messages, check for meetings/tasks, and persist to DB.
    Only processes messages sent after the last processed timestamp for this channel.
    
    Args:
        channel_id: The Slack channel ID to process
        client: OpenAI client instance
        db: Database instance
    
    Returns:
        dict: Summary of processing results with keys 'channel_id', 'meetings_count', 'tasks_count', 'error'
    """
    result = {
        'channel_id': channel_id,
        'meetings_count': 0,
        'tasks_count': 0,
        'error': None
    }
    
    try:
        print(f"\n{'='*70}")
        print(f"Processing channel: {channel_id}")
        
        # Check if this is the first time processing this channel
        last_processed = db.get_channel_last_processed(channel_id)
        if last_processed is None:
            # First time - initialize to yesterday
            db.initialize_channel_timestamp_yesterday(channel_id)
            last_processed = db.get_channel_last_processed(channel_id)
            print(f"First time processing - initialized timestamp to yesterday")
        else:
            print(f"Last processed: {last_processed}")
        
        print(f"{'='*70}")
        
        # Fetch messages from channel AFTER the last processed timestamp
        print(f"Fetching messages from channel {channel_id} after {last_processed}...")
        messages = fetch_all_messages(channel_id, oldest_timestamp=last_processed)
        
        if not messages:
            print(f"No new messages found in channel {channel_id}")
            # Update timestamp even if no messages
            db.update_channel_timestamp(channel_id)
            return result
        
        # Track the latest message timestamp for updating the database
        latest_message_ts = None
        for msg in messages:
            msg_ts = msg.get('ts')
            if msg_ts:
                if latest_message_ts is None or float(msg_ts) > float(latest_message_ts):
                    latest_message_ts = msg_ts
        
        print(f"Found {len(messages)} new message(s)")
        
        # Parse messages
        parsed_messages, mentions = parse_messages_list(messages)
        if not parsed_messages:
            print(f"No valid messages to process in channel {channel_id}")
            # Update timestamp to the latest message timestamp
            if latest_message_ts:
                # Convert Slack timestamp to ISO format
                from datetime import datetime
                dt = datetime.fromtimestamp(float(latest_message_ts), tz=timezone.utc)
                db.update_channel_timestamp(channel_id, dt.isoformat())
            else:
                db.update_channel_timestamp(channel_id)
            return result
        
        print(f"Parsed {len(parsed_messages)} message(s), {len(mentions)} mention(s)")
        
        # Check for meetings
        if parsed_messages:
            print(f"Analyzing {len(parsed_messages)} messages for meetings...")
            try:
                try:
                    meetings_result = check_for_meetings(parsed_messages, client)
                except Exception as exc:
                    print(f"ERROR: Exception during meeting check: {exc}", file=sys.stderr)
                    meetings_result = []
                if meetings_result:
<<<<<<< Updated upstream
                    try:
                        db.add_meetings(meetings_result)
                        result['meetings_count'] = len(meetings_result)
                        print(f"Persisted {len(meetings_result)} meeting(s) from channel {channel_id}")
                    except Exception as exc:
                        print(f"WARNING: Error adding meetings to database for channel {channel_id}: {exc}", file=sys.stderr)
            except Exception as exc:
                print(f"WARNING: Error checking meetings in channel {channel_id}: {exc}", file=sys.stderr)
=======
                    # Add channel_id to each meeting so we know where to send notifications
                    for meeting in meetings_result:
                        meeting['channel_id'] = channel_id
                        meeting['notified'] = False  # Track if we've sent a notification
                    
                    db.add_meetings(meetings_result)
                    result['meetings_count'] = len(meetings_result)
                    print(f"Persisted {len(meetings_result)} meeting(s) from channel {channel_id}")
            except Exception as exc:
                print(f"Error checking meetings in channel {channel_id}: {exc}", file=sys.stderr)
>>>>>>> Stashed changes
        
        # Check for tasks (only from mentions)
        if mentions:
            print(f"Analyzing {len(mentions)} mentioned messages for tasks...")
            try:
                tasks_result = check_for_tasks(mentions, client)
                if tasks_result:
                    # Add channel_id to tasks as well
                    for task in tasks_result:
                        task['channel_id'] = channel_id
                    
                    db.add_tasks(tasks_result)
                    result['tasks_count'] = len(tasks_result)
                    print(f"Persisted {len(tasks_result)} task(s) from channel {channel_id}")
            except Exception as exc:
<<<<<<< Updated upstream
                print(f"WARNING: Error checking tasks in channel {channel_id}: {exc}", file=sys.stderr)
=======
                print(f"Error checking tasks in channel {channel_id}: {exc}", file=sys.stderr)
>>>>>>> Stashed changes
        else:
            print(f"No mentions found in new messages from channel {channel_id}")
        
        # Update the channel's last processed timestamp to the latest message timestamp
        if latest_message_ts:
            from datetime import datetime
            dt = datetime.fromtimestamp(float(latest_message_ts), tz=timezone.utc)
            db.update_channel_timestamp(channel_id, dt.isoformat())
            print(f"Updated channel timestamp to: {dt.isoformat()}")
        else:
            db.update_channel_timestamp(channel_id)
            print(f"Updated channel timestamp")
        
        return result
        
    except Exception as exc:
        error_msg = f"Error processing channel {channel_id}: {exc}"
        print(error_msg, file=sys.stderr)
        result['error'] = str(exc)
        return result


def master_agent() -> None:
    """Main agent that orchestrates the workflow across all channels."""
    _load_env()
    
    # Initialize database
    db = get_default_db()

    try:
        client = _create_openai_client()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        sys.exit(2)

    # Get all channels the bot is a member of
    print("Fetching all channels...")
    channel_ids = get_user_channels()
    
    if not channel_ids:
        print("No channels found or error fetching channels.", file=sys.stderr)
        sys.exit(2)
    
    print(f"\n{'='*70}")
    print(f"Found {len(channel_ids)} channel(s) to process")
    print(f"{'='*70}")
    
    # Process each channel
    results = []
    for i, channel_id in enumerate(channel_ids, 1):
        print(f"\n[{i}/{len(channel_ids)}] Processing channel {channel_id}...")
        result = process_channel(channel_id, client, db)
        results.append(result)
    
    # Print summary
    print("\n" + "="*70)
<<<<<<< Updated upstream
    print(" PROCESSING SUMMARY")
=======
    print("PROCESSING SUMMARY")
>>>>>>> Stashed changes
    print("="*70)
    
    total_meetings = sum(r['meetings_count'] for r in results)
    total_tasks = sum(r['tasks_count'] for r in results)
    errors = [r for r in results if r['error']]
    
    print(f"\nChannels processed: {len(channel_ids)}")
    print(f"Total meetings found: {total_meetings}")
    print(f"Total tasks found: {total_tasks}")
    print(f"Errors encountered: {len(errors)}")
    
    if errors:
<<<<<<< Updated upstream
        print("\nWARNING: Channels with errors:")
=======
        print("\nChannels with errors:")
>>>>>>> Stashed changes
        for r in errors:
            print(f"  - {r['channel_id']}: {r['error']}")
    
    # Show database contents
    print("\n" + "="*70)
<<<<<<< Updated upstream
    print(" DATABASE VERIFICATION")
=======
    print("DATABASE VERIFICATION")
>>>>>>> Stashed changes
    print("="*70)
    all_meetings = db.get_all_meetings()
    all_tasks = db.get_all_tasks()
    print(f"Total meetings in DB: {len(all_meetings)}")
    print(f"Total tasks in DB: {len(all_tasks)}")
    
    # Show channel timestamps
    db_data = db._read_db()
    channel_timestamps = db_data.get('channel_timestamps', {})
    if channel_timestamps:
        print(f"\nChannel timestamps:")
        for ch_id, ts in channel_timestamps.items():
            print(f"  - {ch_id}: {ts}")
    
    if all_meetings:
        print("\nLatest meetings:")
        for m in all_meetings[-5:]:  # Show last 5
            print(f"  - {m.get('title')} on {m.get('date_of_meeting')}")
    
    if all_tasks:
        print("\nLatest tasks:")
        for t in all_tasks[-5:]:  # Show last 5
            print(f"  - {t.get('title')} due {t.get('date_of_meeting')}")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    master_agent()