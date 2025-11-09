import os
import sys
from pathlib import Path
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

from check_meetings import check_for_meetings, check_for_tasks
from parse_messages import parse_messages_list
from slack import fetch_all_messages
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


def master_agent() -> None:
    """Main agent that orchestrates the workflow."""
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

    channel_id = os.getenv("SLACK_CHANNEL_ID", "C09RKGDKDRT")
    print("Fetching Slack messages...")
    try:
        print(f"Fetching messages from Slack channel {channel_id}...", file=sys.stderr)
        messages = fetch_all_messages(channel_id)
        if not messages:
            print(f"Error: No messages fetched from Slack channel {channel_id}.", file=sys.stderr)
            sys.exit(2)
    except Exception as exc:
        print(f"Error fetching from Slack: {exc}", file=sys.stderr)
        sys.exit(2)

    parsed_messages, mentions = parse_messages_list(messages)
    if not parsed_messages:
        print("No new messages found.")
        return

    # Check for meetings and persist
    print(f"Analyzing {len(parsed_messages)} messages for meetings...")
    try:
        meetings_result = check_for_meetings(parsed_messages, client)
        if meetings_result:
            db.add_meetings(meetings_result)
            print(f"Persisted {len(meetings_result)} meeting(s) to database.")
        print(meetings_result)
    except Exception as exc:
        print(f"Error calling OpenAI for meetings: {exc}", file=sys.stderr)
        sys.exit(3)
    
    # Check for tasks and persist
    if not mentions:
        print("No mentions found in messages.")
    else:
        print(f"Analyzing {len(mentions)} mentioned messages for tasks...")
        try:
            tasks_result = check_for_tasks(mentions, client)
            if tasks_result:
                db.add_tasks(tasks_result)
                print(f"Persisted {len(tasks_result)} task(s) to database.")
            print("Tasks found:")
            print(json.dumps(tasks_result, indent=2, ensure_ascii=False))
        except Exception as exc:
            print(f"Error calling OpenAI for tasks: {exc}", file=sys.stderr)
            sys.exit(4)

    if meetings_result:
        print("Meeting(s) found and persisted!")
    else:
        print("No meetings detected.")


if __name__ == "__main__":
    master_agent()