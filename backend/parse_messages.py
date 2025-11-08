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
import re
from typing import Any, Dict, List, Union, Tuple

# Import Slack message fetcher
try:
    from backend.slack import fetch_all_messages
except ImportError:
    try:
        from slack import fetch_all_messages
    except ImportError:
        fetch_all_messages = None


# Mapping of final keys (send_time, message, username) to incoming keys
INCOMING_KEYS = {
    'send_time': 'ts',
    'message': 'text',
    'username': 'user'
}


def parse_message(raw: Union[str, Dict[str, Any]]) -> Union[Dict[str, Any], None]:
    """Parse a single raw message (string or dict) and return a dict
    with keys: send_time, message, username.
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
        return None

    out: Dict[str, Any] = {}
    # Map incoming keys to our canonical keys
    for out_key, in_key in INCOMING_KEYS.items():
        if in_key in obj:
            out[out_key] = obj[in_key]

    if not out:
        return None
    return out


def parse_messages_list(messages: List[Union[str, Dict[str, Any]]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Parse a list of messages, normalize and sort them.

    Returns a tuple: (final_list, mentioned_list)
      - final_list: list of dicts with keys 'username', 'message', and optional 'send_time'
      - mentioned_list: subset of final_list where the message contains a Slack mention (<@USERID>)
    """
    parsed: List[Dict[str, Any]] = []
    for raw in messages:
        p = parse_message(raw)
        if p is not None:
            parsed.append(p)

    # Sort by numeric timestamp (send_time is a string like '1762611979.560459')
    try:
        parsed.sort(key=lambda x: float(x.get('send_time', 0)))
    except Exception:
        pass

    # Build final list (only username, message, and keep send_time for reference)
    final: List[Dict[str, Any]] = []
    for item in parsed:
        username = item.get('username')
        message = item.get('message')
        currTimestamp = item.get('send_time')
        entry: Dict[str, Any] = {}
        if username is not None:
            entry['username'] = username
        if message is not None:
            entry['message'] = message
        if currTimestamp is not None:
            entry['send_time'] = currTimestamp
        if entry:
            final.append(entry)

    # Detect mentions (Slack format: <@USERID>) and collect those entries
    mention_pattern = re.compile(r'<@[^>\s]+>')
    task_pattern = re.compile(r'\btask(s)?\b', re.IGNORECASE)
    mentioned: List[Dict[str, Any]] = []
    for entry in final:
        msg = entry.get('message', '')
        if msg and mention_pattern.search(msg) and task_pattern.search(msg):
            mentioned.append(entry.copy())

    return final, mentioned
