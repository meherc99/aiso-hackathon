import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from check_meetings import check_for_meetings, check_for_tasks
from parse_messages import parse_messages_list
from slack import fetch_all_messages


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
    except Exception as exc:  # pragma: no cover - network errors
        print(f"Error fetching from Slack: {exc}", file=sys.stderr)
        sys.exit(2)

    parsed_messages, mentions = parse_messages_list(messages)
    if not parsed_messages:
        print("No new messages found.")
        return

    print(f"Analyzing {len(parsed_messages)} messages for meetings...")
    try:
        result = check_for_meetings(parsed_messages, client)
        print(result)
    except Exception as exc:  # pragma: no cover - external API
        print(f"Error calling OpenAI: {exc}", file=sys.stderr)
        sys.exit(3)
    
    if not mentions:
        print("No mentions found in messages.")

    else:
        print(f"Analyzing {len(mentions)} mentioned messages for tasks...")
        try:
            tasks_result = check_for_tasks(mentions, client)
            print("Mentions found:")
            print(tasks_result)
        except Exception as exc:  # pragma: no cover - external API
            print(f"Error calling OpenAI for tasks: {exc}", file=sys.stderr)
            sys.exit(4)


    if result:
        print("Meeting found!")
        print(result)
    else:
        print("No meetings detected.")
        print(result)


if __name__ == "__main__":
    master_agent()