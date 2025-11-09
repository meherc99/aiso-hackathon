import os
import sys
from pathlib import Path
import json
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
        print(f"{'='*70}")
        
        # Fetch messages from channel
        print(f"Fetching messages from channel {channel_id}...")
        messages = fetch_all_messages(channel_id)
        
        if not messages:
            print(f"No messages found in channel {channel_id}")
            return result
        
        # Parse messages
        parsed_messages, mentions = parse_messages_list(messages)
        if not parsed_messages:
            print(f"No valid messages to process in channel {channel_id}")
            return result
        
        # Check for meetings
        print(f"Analyzing {len(parsed_messages)} messages for meetings...")
        try:
            meetings_result = check_for_meetings(parsed_messages, client)
            if meetings_result:
                db.add_meetings(meetings_result)
                result['meetings_count'] = len(meetings_result)
                print(f"✅ Persisted {len(meetings_result)} meeting(s) from channel {channel_id}")
        except Exception as exc:
            print(f"⚠️  Error checking meetings in channel {channel_id}: {exc}", file=sys.stderr)
        
        # Check for tasks
        if mentions:
            print(f"Analyzing {len(mentions)} mentioned messages for tasks...")
            try:
                tasks_result = check_for_tasks(mentions, client)
                if tasks_result:
                    db.add_tasks(tasks_result)
                    result['tasks_count'] = len(tasks_result)
                    print(f"✅ Persisted {len(tasks_result)} task(s) from channel {channel_id}")
            except Exception as exc:
                print(f"⚠️  Error checking tasks in channel {channel_id}: {exc}", file=sys.stderr)
        else:
            print(f"No mentions found in channel {channel_id}")
        
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
    db.clear_all()
    print("Cleared existing meetings/tasks from database.")

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
    print("📊 PROCESSING SUMMARY")
    print("="*70)
    
    total_meetings = sum(r['meetings_count'] for r in results)
    total_tasks = sum(r['tasks_count'] for r in results)
    errors = [r for r in results if r['error']]
    
    print(f"\nChannels processed: {len(channel_ids)}")
    print(f"Total meetings found: {total_meetings}")
    print(f"Total tasks found: {total_tasks}")
    print(f"Errors encountered: {len(errors)}")
    
    if errors:
        print("\n⚠️  Channels with errors:")
        for r in errors:
            print(f"  - {r['channel_id']}: {r['error']}")
    
    # Show database contents
    print("\n" + "="*70)
    print("📊 DATABASE VERIFICATION")
    print("="*70)
    all_meetings = db.get_all_meetings()
    all_tasks = db.get_all_tasks()
    print(f"Total meetings in DB: {len(all_meetings)}")
    print(f"Total tasks in DB: {len(all_tasks)}")
    
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