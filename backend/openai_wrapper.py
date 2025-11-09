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

from typing import List, Dict, Optional
import os
import json
import sys
import openai
from openai import OpenAI

try:
    # If python-dotenv is installed and a .env file exists, load it so env vars are available
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional; we'll still read environment variables directly
    pass


def send_messages_to_openai(messages: List[Dict[str, str]],
                            model: str = 'gpt-5',
                            api_key: Optional[str] = None) -> str:
    """Send conversations to OpenAI and return the assistant reply as a string.

    - messages: list of dicts each with 'username' and 'message'
    - model: openai model id
    - api_key: optional API key; if None, will read from env OPENAI_API_KEY or API_KEY
    """
    instruction = (
        "We have this conversation in a JSON format. Your task is to determine when a meeting should be scheduled, based on the messages. "
        "Return a single JSON object and nothing else. The object must have three keys: "
        "`date_of_meeting` whose value is the date agreed for the meeting in ISO8601 format YYYY-MM-DD, for example: {\"date_of_meeting\": \"2024-06-10\"}, "
        "`start_time` whose value is the agreed meeting time in 24-hour HH:MM format in UTC, for example: {\"time\": \"00:00\"}. "
        "`end_time` whose value is the agreed end time of the meeting. If nothing is agreed, the timestamp returned here should consider a duration of 30 minutes per meeting. The format is also HH:MM in UTC, for example: {\"end_time\": \"00:30\"}. "
        "An example of a full valid response is: {\"date_of_meeting\": \"2024-06-10\", \"start_time\": \"00:00\", \"end_time\": \"00:30\"}. "
        "Do not include any extra text, explanation, or formatting — only the JSON object."
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

    # Print the filtered response (JSON content only)
    print("\nOpenAI Response (content only):")
    print(assistant_text.strip())
    
    return assistant_text.strip()


if __name__ == '__main__':
    """
    Main function - kept for backward compatibility.
    Note: Use slack.py to run the full pipeline automatically.
    """
    print("Note: This module is now called from slack.py")
    print("Run: python backend/slack.py to execute the full pipeline")
    print("\nIf you want to use this directly, import and call:")
    print("  - send_messages_to_openai(parsed_messages)")

{
  "python.analysis.extraPaths": [
    ".venv/Lib/site-packages"
  ]
}
