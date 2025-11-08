"""
check_meetings.py

Utilities for asking an OpenAI-compatible service to analyse parsed Slack
messages and infer calendar meetings.

The primary entrypoint is check_for_meetings(messages, client) which expects:
- messages: list of dictionaries produced by parse_messages_list
- client: an openai.OpenAI instance (or compatible) already configured

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
        "date_of_meeting whose value is the date agreed for the meeting in ISO8601 format YYYY-MM-DD, for example: {\"date_of_meeting\": \"2024-06-10\"}. If no date is mentioned, use the current date in UTC. "
        "start_time whose value is the agreed meeting time in 24-hour HH:MM format in UTC, for example: {\"time\": \"00:00\"}. "
        "end_time whose value is the agreed end time of the meeting. If nothing is agreed, the timestamp returned here should consider a duration of 30 minutes per meeting. The format is also HH:MM in UTC, for example: {\"end_time\": \"00:30\"}. "
        "description whose value is the description of the meeting. This will  be simple text that summerized what the meeting will be about. If nothing is mentioned just leave it blank. It shouldn't be longer than a 20 words." \
        "title whose value is the title of the meeting. This can be derived from the description. It shouldn't be longer than a few words."
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

    try:
        assistant_text = resp.choices[0].message.content
        print(f"\n[DEBUG] Raw OpenAI response for tasks:\n{assistant_text}\n")
    except Exception as e:
        print(f"Error extracting assistant content: {e}", file=sys.stderr)
        return []

    # Parse multiple JSON objects (handles JSON array, single object, or line-separated objects)
    json_objects = []
    assistant_text = assistant_text.strip()
    
    # Try parsing as a single JSON value first (array or object)
    try:
        parsed = json.loads(assistant_text)
        if isinstance(parsed, list):
            json_objects = parsed
        elif isinstance(parsed, dict):
            json_objects = [parsed]
    except json.JSONDecodeError:
        # If that fails, try parsing line-by-line (JSON Lines format)
        for line in assistant_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    json_objects.append(obj)
            except json.JSONDecodeError as e:
                print(f"Failed to parse line as JSON: {line[:100]}", file=sys.stderr)
                continue

    if not json_objects:
        print(f"No valid JSON objects found in response", file=sys.stderr)
        return []

    now = datetime.now(timezone.utc)
    created_at = now.isoformat()

    augmented = []
    for obj in json_objects:
        if not isinstance(obj, dict):
            print(f"Skipping non-dict task object: {obj}", file=sys.stderr)
            continue
        
        obj.setdefault('id', str(uuid.uuid4()))
        obj['category'] = 'work'
        obj['created_at'] = created_at

        task_completed = False
        try:
            date_str = obj.get('date_of_meeting')
            time_str = obj.get('start_time') or '23:59'
            if date_str:
                task_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                task_dt = task_dt.replace(tzinfo=timezone.utc)
                task_completed = now > task_dt
        except Exception:
            task_completed = False

        obj['meeting_completed'] = task_completed
        augmented.append(obj)

    print(f"\nOpenAI Response - Found {len(augmented)} task(s):")
    for i, obj in enumerate(augmented, 1):
        print(f"\nTask {i}:")
        print(json.dumps(obj, indent=2, ensure_ascii=False))

    return augmented


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
        "We have these tasks in a JSON format, one task per entry. You can ignore the username parameter. Your job is to determine the tasks that are mentioned or assigned in the messages. There should be one Json object returned per each of the JSON objects sent to you."
        "Each of these returned JSON objects must have five keys: "
        "`date_of_meeting` (use this field to represent the task due date in ISO8601 YYYY-MM-DD), this should be the date the task is due. If no date is mentioned, use the current date in UTC. "
        "`start_time` (use this for the due time in 24-hour HH:MM UTC), this should be the time the task is due. If no time is mentioned, use 23:59. "
        "`end_time`  this should be equal to start_time you computed earlier, "
        "`description` (a short summary of the task, <= 20 words) "
        "`title` (a short title for the task). "
        "Return multiple JSON objects if multiple tasks are present. Do not include any additional text or explanation — only the JSON objects."
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

    client = openai.OpenAI(
        api_key=key,
        base_url="https://fj7qg3jbr3.execute-api.eu-west-1.amazonaws.com/v1"
    )

    resp = client.chat.completions.create(
        model="gpt-5-nano",
        messages=chat_messages,
    )

    # Extract assistant content
    try:
        assistant_text = resp.choices[0].message.content
        print(f"\n[DEBUG] Raw OpenAI response for tasks:\n{assistant_text}\n")
    except Exception as e:
        print(f"Error extracting assistant content: {e}", file=sys.stderr)
        return []

    # Parse multiple JSON objects (handles JSON array, single object, or line-separated objects)
    json_objects = []
    assistant_text = assistant_text.strip()
    
    # Try parsing as a single JSON value first (array or object)
    try:
        parsed = json.loads(assistant_text)
        if isinstance(parsed, list):
            json_objects = parsed
        elif isinstance(parsed, dict):
            json_objects = [parsed]
    except json.JSONDecodeError:
        # If that fails, try parsing line-by-line (JSON Lines format)
        for line in assistant_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    json_objects.append(obj)
            except json.JSONDecodeError as e:
                print(f"Failed to parse line as JSON: {line[:100]}", file=sys.stderr)
                continue

    if not json_objects:
        print(f"No valid JSON objects found in response", file=sys.stderr)
        return []

    now = datetime.now(timezone.utc)
    created_at = now.isoformat()

    augmented = []
    for obj in json_objects:
        if not isinstance(obj, dict):
            print(f"Skipping non-dict task object: {obj}", file=sys.stderr)
            continue
        
        obj.setdefault('id', str(uuid.uuid4()))
        obj['category'] = 'tasks'
        obj['created_at'] = created_at

        task_completed = False
        try:
            date_str = obj.get('date_of_meeting')
            time_str = obj.get('start_time') or '23:59'
            if date_str:
                task_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                task_dt = task_dt.replace(tzinfo=timezone.utc)
                task_completed = now > task_dt
        except Exception:
            task_completed = False

        obj['meeting_completed'] = task_completed
        augmented.append(obj)

    print(f"\nOpenAI Response - Found {len(augmented)} task(s):")
    for i, obj in enumerate(augmented, 1):
        print(f"\nTask {i}:")
        print(json.dumps(obj, indent=2, ensure_ascii=False))

    return augmented