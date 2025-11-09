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
import re
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import uuid
import openai
from dotenv import load_dotenv

load_dotenv()

AMSTERDAM_TZ = ZoneInfo("Europe/Amsterdam")
logger = logging.getLogger(__name__)


def _parse_time_offset(text: str | None) -> int | None:
    if not text:
        return None
    lowered = text.lower()

    in_pattern = re.compile(r"in\s+(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>hours?|hrs?|minutes?|mins?)")
    numeric_pattern = re.compile(
        r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>hours?|hrs?|minutes?|mins?)(?:\s*(?P<direction>later|after|earlier|before|forward|sooner|back))?"
    )
    word_pattern = re.compile(
        r"(?P<amount_word>zero|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|half|quarter)\s*(?P<unit>hours?|hrs?|minutes?|mins?)(?:\s*(?P<direction>later|after|earlier|before|forward|sooner|back))?"
    )

    match = in_pattern.search(lowered)
    if match:
        amount = float(match.group("amount"))
        unit = match.group("unit").lower()
        direction = "later"
    else:
        match = numeric_pattern.search(lowered)
        if match:
            amount = float(match.group("amount"))
            unit = match.group("unit").lower()
            direction = (match.group("direction") or "later").lower()
        else:
            match = word_pattern.search(lowered)
            if not match:
                return None
            amount_word = match.group("amount_word").lower()
            amount_map = {
                "zero": 0,
                "a": 1,
                "an": 1,
                "one": 1,
                "two": 2,
                "three": 3,
                "four": 4,
                "five": 5,
                "six": 6,
                "seven": 7,
                "eight": 8,
                "nine": 9,
                "ten": 10,
                "eleven": 11,
                "twelve": 12,
                "half": 0.5,
                "quarter": 0.25,
            }
            amount = amount_map.get(amount_word)
            if amount is None:
                return None
            unit = match.group("unit").lower()
            direction = (match.group("direction") or "later").lower()

    minutes = int(amount * 60) if unit.startswith(("hour", "hr")) else int(amount)
    if direction in {"earlier", "before", "forward", "sooner", "ahead", "back"}:
        minutes *= -1
    return minutes


def _coerce_time_string(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None

    am_pm_match = re.match(
        r"^(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<meridiem>am|pm)$",
        value,
        re.IGNORECASE,
    )
    if am_pm_match:
        hour = int(am_pm_match.group("hour")) % 12
        minute = int(am_pm_match.group("minute") or "00")
        if am_pm_match.group("meridiem").lower() == "pm":
            hour += 12
        return f"{hour:02d}:{minute:02d}"

    try:
        datetime.strptime(value, "%H:%M")
        return value
    except ValueError:
        return None


def check_for_meetings(messages: List[Dict[str, str]], client: openai.OpenAI) -> List[Dict[str, Any]]:
    instruction = (
        "Don't switch to reasoning models. The date we are in is 2025-11-09. "
        "We have this conversation in a JSON format. Your task is to determine when a meeting should be scheduled, based on the messages. "
        "If multiple meetings are mentioned, return multiple JSON objects with the fields: "
        "date_of_meeting (ISO8601 YYYY-MM-DD), start_time (HH:MM UTC), end_time (HH:MM UTC, default 30 minutes after start), "
        "description (<= 20 words), title. Extract times using the message timestamps. "
        "Do not include any extra text, explanation, or formatting — only the JSON objects."
    )

    user_content = json.dumps(messages, ensure_ascii=False)

    chat_messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": user_content},
    ]

    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY")
    if not key:
        raise RuntimeError("No OpenAI API key provided. Set OPENAI_API_KEY or API_KEY in the environment.")

    client = openai.OpenAI(
        api_key=key,
        base_url="https://fj7qg3jbr3.execute-api.eu-west-1.amazonaws.com/v1",
    )

    logger.debug("Meeting extraction prompt: %s", chat_messages)

    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=chat_messages,
        timeout=120
    )

    try:
        assistant_text = resp.choices[0].message.content
        logger.debug("Raw OpenAI response for meetings:\n%s", assistant_text)
    except Exception as e:
        logger.error("Error extracting assistant content: %s", e)
        return []

    json_objects = []
    assistant_text = assistant_text.strip()

    try:
        parsed = json.loads(assistant_text)
        if isinstance(parsed, list):
            json_objects = parsed
        elif isinstance(parsed, dict):
            json_objects = [parsed]
    except json.JSONDecodeError:
        for line in assistant_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    json_objects.append(obj)
            except json.JSONDecodeError:
                logger.debug("Failed to parse line as JSON: %s", line[:100])
                continue

    if not json_objects:
        logger.debug("No valid JSON objects found in meetings response")
        return []

    now_utc = datetime.now(timezone.utc)
    created_at = now_utc.isoformat()

    latest_message = messages[-1] if messages else {}
    latest_text = latest_message.get("message")
    latest_timestamp = latest_message.get("send_time")
    message_dt = None
    if latest_timestamp:
        try:
            message_dt = datetime.fromisoformat(latest_timestamp.replace("Z", "+00:00")).astimezone(AMSTERDAM_TZ)
        except Exception:
            message_dt = None

    augmented = []
    for obj in json_objects:
        if not isinstance(obj, dict):
            logger.debug("Skipping non-dict meeting object: %s", obj)
            continue

        obj.setdefault("id", str(uuid.uuid4()))
        obj["category"] = "meetings"
        obj["created_at"] = created_at
        obj.setdefault("notified", False)

        date_str = obj.get("date_of_meeting")
        start_time = _coerce_time_string(obj.get("start_time"))
        end_time = _coerce_time_string(obj.get("end_time"))

        offset_minutes = _parse_time_offset(latest_text or "")
        if offset_minutes is not None and message_dt and not start_time:
            target_start = message_dt + timedelta(minutes=offset_minutes)
            obj["date_of_meeting"] = target_start.date().isoformat()
            obj["start_time"] = target_start.strftime("%H:%M")
            obj["end_time"] = (target_start + timedelta(minutes=30)).strftime("%H:%M")
        else:
            used_default = False
            try:
                if date_str and start_time:
                    try:
                        start_dt = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                    except ValueError:
                        start_dt = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    local_start = start_dt.astimezone(AMSTERDAM_TZ)
                    obj["date_of_meeting"] = local_start.date().isoformat()
                    obj["start_time"] = local_start.strftime("%H:%M")

                    if end_time:
                        try:
                            end_dt = datetime.strptime(f"{date_str} {end_time}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                        except ValueError:
                            end_dt = datetime.strptime(f"{date_str} {end_time}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                        obj["end_time"] = end_dt.astimezone(AMSTERDAM_TZ).strftime("%H:%M")
                    else:
                        obj["end_time"] = (local_start + timedelta(minutes=30)).strftime("%H:%M")
                elif message_dt:
                    obj["date_of_meeting"] = message_dt.date().isoformat()
                    obj["start_time"] = message_dt.strftime("%H:%M")
                    obj["end_time"] = (message_dt + timedelta(minutes=30)).strftime("%H:%M")
                else:
                    used_default = True
            except Exception:
                used_default = True

            if used_default and message_dt:
                obj["date_of_meeting"] = message_dt.date().isoformat()
                obj["start_time"] = message_dt.strftime("%H:%M")
                obj["end_time"] = (message_dt + timedelta(minutes=30)).strftime("%H:%M")

        try:
            start_dt_local = datetime.strptime(
                f"{obj['date_of_meeting']} {obj['start_time']}",
                "%Y-%m-%d %H:%M"
            ).replace(tzinfo=AMSTERDAM_TZ)
            obj["meeting_completed"] = now_utc > start_dt_local.astimezone(timezone.utc)
        except Exception:
            obj["meeting_completed"] = False

        augmented.append(obj)

    logger.debug("Processed %d meeting(s)", len(augmented))
    logger.debug("Augmented meetings payload: %s", json.dumps(augmented, indent=2, ensure_ascii=False))

    return augmented


def main() -> None:
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
        model="gpt-4.1",
        messages=chat_messages,
    )

    # Extract assistant content
    try:
        assistant_text = resp.choices[0].message.content
        logger.debug("Raw OpenAI response for tasks:\n%s", assistant_text)
    except Exception as e:
        logger.error("Error extracting assistant content: %s", e)
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
            except json.JSONDecodeError:
                logger.debug("Failed to parse line as JSON (tasks): %s", line[:100])
                continue

    if not json_objects:
        logger.debug("No valid JSON objects found in tasks response")
        return []

    now = datetime.now(timezone.utc)
    created_at = now.isoformat()

    augmented = []
    for obj in json_objects:
        if not isinstance(obj, dict):
            logger.debug("Skipping non-dict task object: %s", obj)
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

    logger.debug("Processed %d task(s)", len(augmented))
    logger.debug("Augmented tasks payload: %s", json.dumps(augmented, indent=2, ensure_ascii=False))

    return augmented