"""
check_meetings.py

Utilities for asking an OpenAI-compatible service to analyse parsed Slack
messages and infer calendar meetings.

The primary entrypoint is `check_for_meetings(messages, client)` which expects:
- `messages`: list of dictionaries produced by `parse_messages_list`
- `client`: an `openai.OpenAI` instance (or compatible) already configured

The function returns a list of augmented meeting JSON objects that can be stored
directly in the calendar database.
"""

from typing import List, Dict, Any
import os
import json
import sys
from datetime import datetime, timezone
import uuid
import openai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def check_for_meetings(messages: List[Dict[str, str]], client: OpenAI) -> List[Dict[str, Any]]:
    """Send conversations to OpenAI and return the assistant reply as a string.

    - messages: list of dicts each with 'username' and 'message'
    - model: openai model id
    - api_key: optional API key; if None, will read from env OPENAI_API_KEY or API_KEY
    """
    instruction = (
        "We have this conversation in a JSON format. Your task is to determine when a meeting should be scheduled, based on the messages. If multiple meetings are mentioned, you should return multiple json objects that follow the same pattern, but with different parameters, depending on the meetings dates, times and also descriptions."
        "Return multiple JSON objects and nothing else, with the details below. An object must have five keys: "
        "`date_of_meeting` whose value is the date agreed for the meeting in ISO8601 format YYYY-MM-DD, for example: {\"date_of_meeting\": \"2024-06-10\"}. If no date is mentioned, use the current date in UTC. "
        "`start_time` whose value is the agreed meeting time in 24-hour HH:MM format in UTC, for example: {\"time\": \"00:00\"}. "
        "`end_time` whose value is the agreed end time of the meeting. If nothing is agreed, the timestamp returned here should consider a duration of 30 minutes per meeting. The format is also HH:MM in UTC, for example: {\"end_time\": \"00:30\"}. "
        "`description` whose value is the description of the meeting. This will  be simple text that summerized what the meeting will be about. If nothing is mentioned just leave it blank. It shouldn't be longer than a 20 words." \
        "`title` whose value is the title of the meeting. This can be derived from the description. It shouldn't be longer than a few words."
        "Do not include any extra text, explanation, or formatting — only the JSON objects."
    )

    model: str = 'gpt-5'
    model = os.environ.get('MODEL', 'gpt-5')

    user_content = json.dumps(messages, ensure_ascii=False)

    chat_messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": user_content}
    ]

    # Resolve API key from param or environment
    key = os.environ.get('OPENAI_API_KEY') or os.environ.get('API_KEY')
    if not key:
        raise RuntimeError('No OpenAI API key provided. Set OPENAI_API_KEY or API_KEY in the environment.')

    # Use the official openai package if available


    client = openai.OpenAI(
        api_key=key,
        base_url="https://fj7qg3jbr3.execute-api.eu-west-1.amazonaws.com/v1"
    )

    # Pass the filtered messages (username + message) correctly structured
    resp = client.chat.completions.create(
        model="gpt-5-nano",
        messages=chat_messages,  # Already contains system instruction + user content with filtered data
    )

    # Extract assistant content (only the JSON response)
    try:
        assistant_text = resp.choices[0].message.content
        parsed = json.loads(assistant_text.strip())
        if isinstance(parsed, dict):
            json_objects = [parsed]
        elif isinstance(parsed, list):
            json_objects = parsed
        else:
            raise TypeError(f"Unexpected JSON payload type: {type(parsed)!r}")
    except Exception as e:
        print(f"Error processing response: {e}", file=sys.stderr)
        json_objects = []
    # Augment each found JSON object with extra fields:
    # - id: UUID4 string
    # - category: always "work"
    # - done: true if current UTC timestamp is after the meeting date+start_time
    # - created_at: current UTC timestamp in ISO format
    now = datetime.now(timezone.utc)
    created_at = now.isoformat()

    for obj in json_objects:
        # Ensure we work with a dict
        if not isinstance(obj, dict):
            continue

        # Add id and category and created_at
        obj.setdefault('id', str(uuid.uuid4()))
        obj['category'] = 'work'
        obj['created_at'] = created_at

        # Determine if the meeting is done. Expecting keys:
        # - date_of_meeting: YYYY-MM-DD
        # - start_time: HH:MM (24-hour, UTC)
        meeting_completed = False
        try:
            date_str = obj.get('date_of_meeting')
            time_str = obj.get('start_time') or '00:00'
            if date_str:
                # Build a UTC datetime for the meeting
                meeting_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                # Treat the parsed time as UTC
                meeting_dt = meeting_dt.replace(tzinfo=timezone.utc)
                meeting_completed = now > meeting_dt
        except Exception:
            # If parsing fails, leave meeting_completed as False
            meeting_completed = False

        obj['meeting_completed'] = meeting_completed

    # Print all found and augmented JSON objects
    print("\nOpenAI Response - Found {} JSON object(s):".format(len(json_objects)))
    for i, obj in enumerate(json_objects, 1):
        print(f"\nJSON Object {i}:")
        print(json.dumps(obj, indent=2, ensure_ascii=False))

    # Return the list of augmented JSON objects
    return json_objects


def main() -> None:
    """
    Minimal CLI usage:
      python backend/check_meetings.py messages.json
    Requires OPENAI credentials configured.
    """
    import argparse
    from openai import OpenAI

    parser = argparse.ArgumentParser(description="Inspect parsed Slack messages for meetings.")
    parser.add_argument("source", help="Path to JSON file containing parsed messages.")
    args = parser.parse_args()

    with open(args.source, "r", encoding="utf-8") as handle:
        parsed_messages = json.load(handle)

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY / API_KEY is required.")

    client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL"))
    result = check_for_meetings(parsed_messages, client)
    print(json.dumps(result, indent=2, ensure_ascii=False))

def check_for_tasks(messages: List[Dict[str, str]], client):
    """Send conversations to OpenAI and return the assistant reply as a list of JSON objects (tasks).
    The returned objects follow the same schema as meetings, but will be categorized as 'tasks'."""
    instruction = (
        "We have this conversation in a JSON format. Your task is to determine tasks that are mentioned or assigned in the messages. "
        "For each task you find, return a JSON object (or multiple objects). Each object must have five keys: "
        "`date_of_meeting` (use this field to represent the task due date in ISO8601 YYYY-MM-DD), this should be the date the task is due. If no date is mentioned, use the current date in UTC. "
        "`start_time` (use this for the due time in 24-hour HH:MM UTC), this should be the time the task is due. If no time is mentioned, use 23:59. "
        "`end_time`  this should be equal to start_time you computed earlier, "
        "`description` (a short summary of the task, <= 20 words) "
        "`title` (a short title for the task). "
        "Return multiple JSON objects if multiple tasks are present. Do not include any additional text or explanation — only the JSON objects."
    )

    messages = json.dumps(messages, ensure_ascii=False)

    chat_messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": messages}
    ]
    
    # Pass the filtered messages (username + message) correctly structured
    resp = client.chat.completions.create(
        model=os.environ.get('MODEL', 'gpt-5'),
        messages=chat_messages,  # Already contains system instruction + user content with filtered data
        response_format={"type": "json_object"},
    )

    # Extract assistant content (only the JSON response)
    try:
        assistant_text = resp.choices[0].message.content
        parsed = json.loads(assistant_text.strip())
        if isinstance(parsed, dict):
            json_objects = [parsed]
        elif isinstance(parsed, list):
            json_objects = parsed
        else:
            raise TypeError(f"Unexpected JSON payload type: {type(parsed)!r}")
    except Exception as e:
        print(f"Error processing response: {e}", file=sys.stderr)
        json_objects = []
    # Augment each found JSON object with extra fields:
    # - id: UUID4 string
    # - category: always "work"
    # - done: true if current UTC timestamp is after the meeting date+start_time
    # - created_at: current UTC timestamp in ISO format
    now = datetime.now(timezone.utc)
    created_at = now.isoformat()

    for obj in json_objects:
        # Ensure we work with a dict
        if not isinstance(obj, dict):
            continue

        # Add id and category and created_at
        obj.setdefault('id', str(uuid.uuid4()))
        obj['category'] = 'tasks'
        obj['created_at'] = created_at

        # Determine if the meeting is done. Expecting keys:
        # - date_of_meeting: YYYY-MM-DD
        # - start_time: HH:MM (24-hour, UTC)
        meeting_completed = False
        try:
            date_str = obj.get('date_of_meeting')
            time_str = obj.get('start_time') or '00:00'
            if date_str:
                # Build a UTC datetime for the meeting
                meeting_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                # Treat the parsed time as UTC
                meeting_dt = meeting_dt.replace(tzinfo=timezone.utc)
                meeting_completed = now > meeting_dt
        except Exception:
            # If parsing fails, leave meeting_completed as False
            meeting_completed = False

        obj['meeting_completed'] = meeting_completed

    # Print all found and augmented JSON objects
    print("\nOpenAI Response - Found {} JSON object(s):".format(len(json_objects)))
    for i, obj in enumerate(json_objects, 1):
        print(f"\nJSON Object {i}:")
        print(json.dumps(obj, indent=2, ensure_ascii=False))

    # Return the list of augmented JSON objects
    return json_objects