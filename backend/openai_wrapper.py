"""
openai_wrapper.py

Small wrapper around the OpenAI Chat API to send a list of messages (username/message)
and return the assistant reply as a string.

Security: this module does NOT hardcode any API key. It reads the key from the
environment variable `OPENAI_API_KEY` or `API_KEY`. Do NOT paste real keys into files.

Usage examples:
  # Dry run (no network call)
  python openai_wrapper.py --dry-run

  # Real call (make sure OPENAI_API_KEY is set in env)
  python openai_wrapper.py --model gpt-3.5-turbo --input messages.json

API contract:
  send_messages_to_openai(messages, model='gpt-3.5-turbo', api_key=None, dry_run=False) -> str

Where `messages` is a list of objects with keys `username` and `message`.
The wrapper will construct a prompt:
  "We have these conversation in a JSON Format. Your task is to determine between which times should a meeting be schedule. Please only return the timestamps without any additional text."
and send the JSON-formatted messages as the user content.

The function returns the assistant's raw reply string (no parsing).
"""

from typing import List, Dict, Optional, Any
import os
import json
import sys
import openai
from openai import OpenAI
import tiktoken
import uuid
from datetime import datetime, timezone

try:
    # If python-dotenv is installed and a .env file exists, load it so env vars are available
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional; we'll still read environment variables directly
    pass


def send_messages_to_openai(messages: List[Dict[str, str]],
                            model: str = 'gpt-5',
                            api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Send conversations to OpenAI and return the assistant reply as a string.

    - messages: list of dicts each with 'username' and 'message'
    - model: openai model id
    - api_key: optional API key; if None, will read from env OPENAI_API_KEY or API_KEY
    """
    instruction = (
        "We have this conversation in a JSON format. Your task is to determine when a meeting should be scheduled, based on the messages. If multiple meetings are mentioned, you should return multiple json objects that follow the same pattern, but with different parameters, depending on the meetings dates, times and also descriptions."
        "Return multiple JSON objects and nothing else, with the details below. An object must have five keys: "
        "`date_of_meeting` whose value is the date agreed for the meeting in ISO8601 format YYYY-MM-DD, for example: {\"date_of_meeting\": \"2024-06-10\"}, "
        "`start_time` whose value is the agreed meeting time in 24-hour HH:MM format in UTC, for example: {\"time\": \"00:00\"}. "
        "`end_time` whose value is the agreed end time of the meeting. If nothing is agreed, the timestamp returned here should consider a duration of 30 minutes per meeting. The format is also HH:MM in UTC, for example: {\"end_time\": \"00:30\"}. "
        "`description` whose value is the description of the meeting. This will  be simple text that summerized what the meeting will be about. If nothing is mentioned just leave it blank. It shouldn't be longer than a 20 words." \
        "`title` whose value is the title of the meeting. This can be derived from the description. It shouldn't be longer than a few words."
        "Do not include any extra text, explanation, or formatting — only the JSON objects."
    )

    # (do not short-circuit on dry_run yet; we want to allow printing the payload)

    # Allow overriding the default model from the environment (but keep explicit model param)
    model = model or os.environ.get('MODEL', 'gpt-5')

    user_content = json.dumps(messages, ensure_ascii=False)

    chat_messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": user_content}
    ]

    # Resolve API key from param or environment
    key = api_key or os.environ.get('OPENAI_API_KEY') or os.environ.get('API_KEY')
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

    # Print the full response for debugging
    
    # Extract assistant content (only the JSON response)
    try:
        assistant_text = resp.choices[0].message.content
    except Exception as e:
        # Fallback: return full response as string
        print(f"Error extracting content: {e}", file=sys.stderr)
        assistant_text = str(resp)

    # Parse multiple JSON objects from the response
    json_objects: List[Dict[str, Any]] = []
    try:
        # Try to parse as a single JSON first
        single_json = json.loads(assistant_text.strip())
        json_objects.append(single_json)
    except json.JSONDecodeError:
        # If that fails, try to find multiple JSON objects
        import re
        # Find all JSON objects in the text (looking for {...} patterns)
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, assistant_text)
        
        for match in matches:
            try:
                parsed = json.loads(match)
                json_objects.append(parsed)
            except json.JSONDecodeError:
                continue
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
        done = False
        try:
            date_str = obj.get('date_of_meeting')
            time_str = obj.get('start_time') or '00:00'
            if date_str:
                # Build a UTC datetime for the meeting
                meeting_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                # Treat the parsed time as UTC
                meeting_dt = meeting_dt.replace(tzinfo=timezone.utc)
                done = now > meeting_dt
        except Exception:
            # If parsing fails, leave done as False
            done = False

        obj['done'] = done

    # Print all found and augmented JSON objects
    print("\nOpenAI Response - Found {} JSON object(s):".format(len(json_objects)))
    for i, obj in enumerate(json_objects, 1):
        print(f"\nJSON Object {i}:")
        print(json.dumps(obj, indent=2, ensure_ascii=False))

    # Return the list of augmented JSON objects
    return json_objects


if __name__ == '__main__':
        """
        Main function - kept for backward compatibility.
        Note: Use slack.py to run the full pipeline automatically.
        """
        print("Note: This module is now called from slack.py")
        print("Run: python backend/slack.py to execute the full pipeline")
        print("\nIf you want to use this directly, import and call:")
        print("  - send_messages_to_openai(parsed_messages)")
