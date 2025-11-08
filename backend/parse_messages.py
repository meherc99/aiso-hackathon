"""
parse_messages.py

This script contains a sample list of messages (JSON-like strings or dicts),
parses them, and outputs a JSON list where each item contains ONLY the
fields: send_time, message, username.

Usage:
    python parse_messages.py            # runs built-in samples
    python parse_messages.py input.json # read a JSON array from a file

Notes / assumptions:
- If the original JSON uses `userrname` (typo) or `user`, or `sender`, the
  script will try common fallbacks and normalize to `username` in output.
- Only keys present (after normalization) will be included for each item.
"""
import json
import argparse
import sys
from typing import Any, Dict, List, Union, Optional

# Import Slack message fetcher
try:
    from backend.slack import fetch_all_messages
except ImportError:
    try:
        from slack import fetch_all_messages
    except ImportError:
        fetch_all_messages = None

# we'll import the openai wrapper lazily when needed

# Mapping of final keys (send_time, message, username) to incoming keys
INCOMING_KEYS = {
    'send_time': 'ts',
    'message': 'text',
    'username': 'user'
}


def parse_message(raw: Union[str, Dict[str, Any]]) -> Union[Dict[str, Any], None]:
    """Parse a single raw message (string or dict) and return a dict
    with exactly these keys: send_time, message, username.

    Rules / assumptions:
    - Input items are dict-like with keys 'user', 'type', 'text', 'ts'.
    - Only include items where obj.get('type') == 'message' AND the item does not
      have a 'subtype' key (this excludes events like channel_join). This matches the
      requirement "filter the messages by type so that only message types are included".
      If you'd rather include items with 'subtype' present, we can change this.
    - Timestamps in 'ts' are strings like '1762611979.560459' and will be sorted
      numerically.
    """
    obj = None
    if isinstance(raw, str):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return None
    elif isinstance(raw, dict):
        obj = raw
    else:
        return None

    # Must be a message and not an event-like subtype
    if obj.get('type') != 'message':
        return None
    if 'subtype' in obj:
        # exclude join/other subtype events; change this logic if you want to keep them
        return None

    out: Dict[str, Any] = {}
    # Map incoming keys to our canonical keys
    for out_key, in_key in INCOMING_KEYS.items():
        if in_key in obj:
            out[out_key] = obj[in_key]

    # If no target keys found, skip
    if not out:
        return None
    return out


def parse_messages_list(messages: List[Union[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Parse a list of messages, filter and normalize them, and sort by timestamp.

    Returns a list of dicts with keys send_time, message, username sorted by send_time (ascending).
    """
    parsed: List[Dict[str, Any]] = []
    for raw in messages:
        p = parse_message(raw)
        if p is not None:
            parsed.append(p)

    # Sort by numeric timestamp (ts is a string like '1762611979.560459')
    try:
        parsed.sort(key=lambda x: float(x.get('send_time', 0)))
    except Exception:
        # If conversion fails for any item, leave current order
        pass

    # Final output should only include username and message (timestamps were used only for sorting)
    final: List[Dict[str, Any]] = []
    for item in parsed:
        username = item.get('username')
        message = item.get('message')
        # Include only if message and username exist; otherwise include whatever is present
        entry: Dict[str, Any] = {}
        if username is not None:
            entry['username'] = username
        if message is not None:
            entry['message'] = message
        if entry:
            final.append(entry)

    return final


def load_messages_from_file(path: str) -> List[Union[str, Dict[str, Any]]]:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError('Input file must contain a JSON array')
    return data


def main():
    parser = argparse.ArgumentParser(description='Parse messages and keep only username and message (timestamps used for sorting)')
    parser.add_argument('input', nargs='?', help='Optional input JSON file (array of raw messages). If omitted, fetches from Slack.')
    parser.add_argument('--channel-id', default='C09RKGDKDRT', help='Slack channel ID to fetch messages from (default: C09RKGDKDRT)')
    parser.add_argument('--send-to-openai', action='store_true', help='Send the parsed messages to OpenAI using openai_wrapper')
    parser.add_argument('--model', default='gpt-5', help='OpenAI model id to use when sending')
    parser.add_argument('--api-key', help='Optional OpenAI API key (better to set OPENAI_API_KEY env var)')
    parser.add_argument('--dry-run', action='store_true', help='When sending to OpenAI, do a dry run (no network call)')
    parser.add_argument('--interpret-utc', action='store_true', help='If sending to OpenAI, interpret returned timestamps as UTC ISO8601')
    parser.add_argument('--output', '-o', help='Optional output file to write the final result (assistant reply or parsed JSON). If omitted, prints to stdout')
    parser.add_argument('--show-payload', action='store_true', help='When sending to OpenAI, print the chat payload that will be sent')
    args = parser.parse_args()

    # Determine message source: file or Slack
    if args.input:
        try:
            messages = load_messages_from_file(args.input)
        except Exception as e:
            print(f'Error reading input file: {e}', file=sys.stderr)
            sys.exit(2)
    else:
        # Fetch messages from Slack (default behavior)
        if fetch_all_messages is None:
            print('Error: slack.py is not available. Cannot fetch messages from Slack.', file=sys.stderr)
            sys.exit(2)
        try:
            print(f'Fetching messages from Slack channel {args.channel_id}...', file=sys.stderr)
            messages = fetch_all_messages(args.channel_id)
            if not messages:
                print('Error: No messages fetched from Slack channel {args.channel_id}.', file=sys.stderr)
                sys.exit(2)
        except Exception as e:
            print(f'Error fetching from Slack: {e}', file=sys.stderr)
            sys.exit(2)

    parsed = parse_messages_list(messages)

    # If not sending to OpenAI, just print the parsed list (username+message)
    if not args.send_to_openai:
        out_str = json.dumps(parsed, ensure_ascii=False)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(out_str)
        else:
            print(out_str)
        return

    # Send to OpenAI via the wrapper
    try:
        try:
            import backend.openai_wrapper as openai_wrapper
        except ImportError:
            # If running from backend directory, try relative import
            import openai_wrapper
    except Exception as e:
        print('Cannot import openai_wrapper. Make sure openai_wrapper.py exists and is importable. Error:', e, file=sys.stderr)
        sys.exit(3)

    # The wrapper expects a list of dicts with 'username' and 'message'. We already have that.
    try:
        reply = openai_wrapper.send_messages_to_openai(parsed, model=args.model, api_key=args.api_key, dry_run=args.dry_run, show_payload=args.show_payload)
    except Exception as e:
        print('Error sending to OpenAI:', e, file=sys.stderr)
        sys.exit(4)

    if args.interpret_utc:
        try:
            reply = openai_wrapper.interpret_timestamps_in_reply(reply)
        except Exception as e:
            print('Error interpreting timestamps:', e, file=sys.stderr)
            sys.exit(5)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(reply)
    else:
        print(reply)


if __name__ == '__main__':
    main()
