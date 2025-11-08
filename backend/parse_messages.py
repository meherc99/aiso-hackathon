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
from typing import Any, Dict, List, Union

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
        currTimestamp = item.get('ts')
        # Include only if message and username exist; otherwise include whatever is present
        entry: Dict[str, Any] = {}
        if username is not None:
            entry['username'] = username
        if message is not None:
            entry['message'] = message
        if currTimestamp is not None:
            entry['send_time'] = currTimestamp
        if entry:
            final.append(entry)

    return final


def main():
    """
    Main function - kept for backward compatibility.
    Note: Use slack.py to run the full pipeline automatically.
    """
    print("Note: This script is now called from slack.py")
    print("Run: python backend/slack.py to execute the full pipeline")
    print("\nIf you want to use this directly, please use the functions:")
    print("  - parse_messages_list(messages) to parse messages")
    print("  - Then call openai_wrapper.send_messages_to_openai(parsed_messages)")


if __name__ == '__main__':
    main()
