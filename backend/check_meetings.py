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
from datetime import datetime, time, timezone
import uuid
import openai
from openai import OpenAI, max_retries
from dotenv import load_dotenv

load_dotenv()


import os
import re
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
import openai


def check_for_meetings(messages: List[Dict[str, str]], client: openai.OpenAI) -> List[Dict[str, Any]]:
    attempt = 0
    max_retries = 3
    try:
        instruction = (
            "Don't switch to reasoning models. The date we are in is 2025-11-09, so make sure you correctly check current dates. To create the time_stamps and the dates, please look at the timestamps provided to you. The start time We have this conversation in a JSON format. Your task is to determine when a meeting should be scheduled, based on the messages. "
            "If multiple meetings are mentioned, you should return multiple json objects that follow the same pattern, but with different parameters, "
            "depending on the meetings' dates, times and also descriptions. "
            "Return multiple JSON objects and nothing else, with the details below. An object must have five keys: "
            "date_of_meeting whose value is the date agreed for the meeting in ISO8601 format YYYY-MM-DD, for example: {\"date_of_meeting\": \"2025-06-10\"}. If not date is specified, try to look for words like tommorrow or today, so a context can be infered based on the current date in UTC"
            "If no date is mentioned or time-related words, use the current date in UTC. "
            "start_time whose value is the agreed meeting time in 24-hour HH:MM format in UTC, for example: {\"time\": \"00:00\"}. "
            "end_time whose value is the agreed end time of the meeting. If nothing is agreed, the timestamp returned here should consider a duration of 30 minutes per meeting. "
            "The format is also HH:MM in UTC, for example: {\"end_time\": \"00:30\"}. "
            "description whose value is the description of the meeting. This will be simple text summarizing what the meeting will be about. "
            "If nothing is mentioned just leave it blank. It shouldn't be longer than 20 words. "
            "title whose value is the title of the meeting. This can be derived from the description. It shouldn't be longer than a few words. "
            "Do not include any extra text, explanation, or formatting — only the JSON objects."
        )

        model = os.environ.get("MODEL", "gpt-5")

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

        print(chat_messages)

        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=chat_messages,
            timeout=120
        )

        content = response.choices[0].message.content.strip()
        print(f"LLM response for meetings:\n{content}\n")

        # Parse JSON - handle multiple formats
        meetings = []

        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                meetings = parsed
            elif isinstance(parsed, dict):
                meetings = [parsed]
        except json.JSONDecodeError:
            array_pattern = r'\[\s*\{.*?\}\s*\]'
            array_matches = re.findall(array_pattern, content, re.DOTALL)
            for match in array_matches:
                try:
                    parsed = json.loads(match)
                    if isinstance(parsed, list):
                        meetings.extend(parsed)
                    elif isinstance(parsed, dict):
                        meetings.append(parsed)
                except json.JSONDecodeError:
                    continue

            if not meetings:
                brace_count = 0
                current_obj = []
                in_string = False
                escape_next = False

                for char in content:
                    if escape_next:
                        current_obj.append(char)
                        escape_next = False
                        continue

                    if char == '\\':
                        escape_next = True
                        current_obj.append(char)
                        continue

                    if char == '"' and not escape_next:
                        in_string = not in_string
                        current_obj.append(char)
                        continue

                    if not in_string:
                        if char == '{':
                            if brace_count == 0:
                                current_obj = [char]
                            else:
                                current_obj.append(char)
                            brace_count += 1
                        elif char == '}':
                            current_obj.append(char)
                            brace_count -= 1
                            if brace_count == 0:
                                obj_str = ''.join(current_obj)
                                try:
                                    parsed = json.loads(obj_str)
                                    if isinstance(parsed, dict):
                                        meetings.append(parsed)
                                except json.JSONDecodeError:
                                    pass
                                current_obj = []
                        elif brace_count > 0:
                            current_obj.append(char)
                    else:
                        current_obj.append(char)

        if not meetings:
            print("No meetings detected in messages")
            return []

        now_iso = datetime.utcnow().isoformat()
        for meeting in meetings:
            meeting["id"] = str(uuid.uuid4())
            meeting["category"] = "meetings"
            meeting["meeting_completed"] = False
            meeting["created_at"] = now_iso

        print(f"Extracted {len(meetings)} meeting(s)")
        return meetings

    except Exception as exc:
            error_msg = str(exc)
            if "503" in error_msg or "Service Unavailable" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2
                    print(f"Service unavailable (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s...")
                    time_module.sleep(wait_time)
                    attempt += 1
                else:
                    print(f"Error in check_for_meetings after {max_retries} attempts: {exc}")
                    return []
            else:
                print(f"Error in check_for_meetings: {exc}")
                return []
    
    return []


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