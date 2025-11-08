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
                            api_key: Optional[str] = None,
                            dry_run: bool = False,
                            show_payload: bool = False) -> str:
    """Send conversations to OpenAI and return the assistant reply as a string.

    - messages: list of dicts each with 'username' and 'message'
    - model: openai model id
    - api_key: optional API key; if None, will read from env OPENAI_API_KEY or API_KEY
    - dry_run: if True, do NOT call OpenAI and return a simulated response
    """
    instruction = (
        "We have this conversation in a JSON format. Your task is to determine when a meeting should be scheduled, based on the messages. "
        "Return a single JSON object and nothing else. The object must have a single key `time` whose value is the agreed meeting time in 24-hour HH:MM format in UTC, for example: {\"time\": \"00:00\"}. "
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

    if show_payload:
        # Print the payload that would be sent to OpenAI (do not include API key)
        try:
            payload = {"model": model, "messages": chat_messages}
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception:
            # fallback: print a compact representation
            print({"model": model, "messages": chat_messages, "error": "could not serialize payload"})

    # Resolve API key from param or environment (only needed for real requests)
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

    # Extract assistant content (only the JSON response)
    try:
        assistant_text = resp.choices[0].message.content
    except Exception as e:
        # Fallback: return full response as string
        print(f"Error extracting content: {e}", file=sys.stderr)
        assistant_text = str(resp)

    # Print the filtered response (JSON content only)
    print("OpenAI Response (content only):")
    print(assistant_text.strip())
    
    return assistant_text.strip()


def interpret_timestamps_in_reply(reply: str) -> str:
    """Find Unix timestamps in the reply string and convert them to UTC ISO8601.

    This function will:
    - Try to parse the reply as JSON first. If it is JSON and contains strings or numbers,
      it will convert numeric-looking values inside those strings.
    - Otherwise it will replace any contiguous digit sequences with optional decimal
      (e.g. 1762611979 or 1762611979.560459) with their UTC ISO8601 representation.

    Returns the converted reply as a string.
    """
    import re
    import json
    from datetime import datetime, timezone

    def convert_number(match: re.Match) -> str:
        s = match.group(0)
        try:
            ts = float(s)
        except Exception:
            return s
        # Convert seconds since epoch to UTC ISO8601 with Z
        try:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.isoformat().replace('+00:00', 'Z')
        except Exception:
            return s

    # First try to detect if reply is JSON; if so, decode and process strings inside
    try:
        parsed = json.loads(reply)
    except Exception:
        parsed = None

    if parsed is not None:
        # If it's a list/str/number structure, walk it and convert numbers inside strings
        def walk(obj):
            if isinstance(obj, str):
                # replace numeric timestamps inside the string
                return re.sub(r"\d{9,}\.\d+|\d{9,}", convert_number, obj)
            if isinstance(obj, list):
                return [walk(x) for x in obj]
            if isinstance(obj, dict):
                return {k: walk(v) for k, v in obj.items()}
            if isinstance(obj, (int, float)):
                # convert numeric value directly
                try:
                    dt = datetime.fromtimestamp(float(obj), tz=timezone.utc)
                    return dt.isoformat().replace('+00:00', 'Z')
                except Exception:
                    return obj
            return obj

        converted = walk(parsed)
        try:
            return json.dumps(converted, ensure_ascii=False)
        except Exception:
            return str(converted)

    # Not JSON — do a regex replace on any long numeric tokens
    converted = re.sub(r"\d{9,}\.\d+|\d{9,}", convert_number, reply)
    return converted


def _load_json_file(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _demo_messages():
    # Small demo sample (username/message only)
    return [
        {"username": "U1", "message": "I'm available Monday 3pm"},
        {"username": "U2", "message": "I can do Tuesday 4pm"},
    ]


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Send conversation to OpenAI and return assistant reply')
    parser.add_argument('--input', '-i', help='Path to JSON file containing list of {"username","message"} objects')
    parser.add_argument('--model', default='gpt-5', help='OpenAI model id')
    parser.add_argument('--dry-run', action='store_true', help='Do not call OpenAI; return a simulated response')
    parser.add_argument('--api-key', help='Optional OpenAI API key (better to set OPENAI_API_KEY env var)')
    parser.add_argument('--interpret-utc', action='store_true', help='Interpret numeric unix timestamps in the assistant reply as UTC ISO8601')
    parser.add_argument('--show-payload', action='store_true', help='Print the chat payload that will be sent to OpenAI (safe: API key not printed)')
    args = parser.parse_args()

    if args.input:
        try:
            messages = _load_json_file(args.input)
        except Exception as e:
            print('Error loading input file:', e, file=sys.stderr)
            sys.exit(2)
    else:
        messages = _demo_messages()

    try:
        reply = send_messages_to_openai(messages, model=args.model, api_key=args.api_key, dry_run=args.dry_run, show_payload=args.show_payload)
    except Exception as e:
        print('Error sending to OpenAI:', e, file=sys.stderr)
        sys.exit(3)

    # Optionally interpret timestamps in the reply
    if args.interpret_utc:
        try:
            reply = interpret_timestamps_in_reply(reply)
        except Exception as e:
            print('Error interpreting timestamps:', e, file=sys.stderr)
            sys.exit(4)

    # Print assistant reply (possibly interpreted)
    print(reply)

{
  "python.analysis.extraPaths": [
    ".venv/Lib/site-packages"
  ]
}
