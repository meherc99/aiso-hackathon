import os
import sys
from pathlib import Path
import json
import re
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

from check_meetings import check_for_meetings, check_for_tasks
from parse_messages import parse_messages_list
from slack import fetch_all_messages


def _load_env() -> None:
    """Ensure the project-level .env file is loaded regardless of cwd."""
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"
    # Only attempt to load if the file exists; this keeps CI runs happy.
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    else:
        load_dotenv(override=False)


def _create_openai_client() -> OpenAI:
    """Create and return an OpenAI client configured for the custom endpoint."""
    key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
    if not key:
        raise RuntimeError(
            "No OpenAI API key provided. Set OPENAI_API_KEY or API_KEY in the environment."
        )

    base_url = os.getenv(
        "OPENAI_BASE_URL",
        "https://fj7qg3jbr3.execute-api.eu-west-1.amazonaws.com/v1",
    )
    return OpenAI(api_key=key, base_url=base_url)


def master_agent() -> None:
    """Main agent that orchestrates the workflow."""
    _load_env()

    try:
        client = _create_openai_client()
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        sys.exit(2)

    channel_id = os.getenv("SLACK_CHANNEL_ID", "C09RKGDKDRT")
    print("Fetching Slack messages...")
    try:
        print(f"Fetching messages from Slack channel {channel_id}...", file=sys.stderr)
        messages = fetch_all_messages(channel_id)
        if not messages:
            print(f"Error: No messages fetched from Slack channel {channel_id}.", file=sys.stderr)
            sys.exit(2)
    except Exception as exc:  # pragma: no cover - network errors
        print(f"Error fetching from Slack: {exc}", file=sys.stderr)
        sys.exit(2)

    parsed_messages, mentions = parse_messages_list(messages)
    if not parsed_messages:
        print("No new messages found.")
        return

    print(f"Analyzing {len(parsed_messages)} messages for meetings...")
    try:
        result = check_for_meetings(parsed_messages, client)
        print(result)
    except Exception as exc:  # pragma: no cover - external API
        print(f"Error calling OpenAI: {exc}", file=sys.stderr)
        sys.exit(3)
    
    if not mentions:
        print("No mentions found in messages.")
    else:
        # Inline tasks-check logic (moved from check_for_tasks into agent)
        print(f"Analyzing {len(mentions)} mentioned messages for tasks...")
        try:
            # Build instruction tailored for tasks
            instruction = (
                "We have this conversation in a JSON format. Your task is to detect tasks mentioned or assigned in the messages. "
                "For each task return a JSON object with these keys: "
                "\"date_of_meeting\" (task due date YYYY-MM-DD, use current UTC date if not specified), "
                "\"start_time\" (due time HH:MM 24-hour UTC, use 23:59 if not specified), "
                "\"end_time\" (use same as start_time if not specified), "
                "\"description\" (short <=20 words), "
                "\"title\" (short few-word title). "
                "Return a JSON array of objects or multiple JSON objects only — no extra text."
            )
            user_content = json.dumps(mentions, ensure_ascii=False)
            chat_messages = [
                {"role": "system", "content": instruction},
                {"role": "user", "content": user_content}
            ]

            resp = client.chat.completions.create(
                model=os.environ.get("MODEL", "gpt-5"),
                messages=chat_messages,
            )

            assistant_text = ""
            try:
                assistant_text = resp.choices[0].message.content
            except Exception as e:
                print(f"Error extracting assistant content for tasks: {e}", file=sys.stderr)

            # Small robust parser for multiple JSON objects / arrays
            def _parse_multiple_json_objects(text: str):
                text = (text or "").strip()
                if not text:
                    return []
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, list):
                        return parsed
                    if isinstance(parsed, dict):
                        return [parsed]
                except Exception:
                    pass
                # JSON lines
                objs = []
                for line in text.splitlines():
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        o = json.loads(s)
                        if isinstance(o, dict):
                            objs.append(o)
                    except Exception:
                        continue
                if objs:
                    return objs
                # fallback: extract {...} blocks
                matches = re.findall(r'\{.*?\}', text, flags=re.DOTALL)
                out = []
                for m in matches:
                    try:
                        o = json.loads(m)
                        if isinstance(o, dict):
                            out.append(o)
                    except Exception:
                        continue
                return out

            json_objects = _parse_multiple_json_objects(assistant_text)

            # Augment each task object
            now = datetime.now(timezone.utc)
            created_at = now.isoformat()
            tasks_result = []
            for obj in json_objects:
                if not isinstance(obj, dict):
                    continue
                obj.setdefault("id", str(uuid.uuid4()))
                obj["category"] = "tasks"
                obj["created_at"] = created_at
                # compute done based on date_of_meeting + start_time
                done = False
                try:
                    date_str = obj.get("date_of_meeting")
                    time_str = obj.get("start_time") or "23:59"
                    if date_str:
                        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                        dt = dt.replace(tzinfo=timezone.utc)
                        done = now > dt
                except Exception:
                    done = False
                obj["done"] = done
                tasks_result.append(obj)

            print("Mentions found (tasks):")
            print(json.dumps(tasks_result, indent=2, ensure_ascii=False))
        except Exception as exc:  # pragma: no cover - external API
            print(f"Error calling OpenAI for tasks: {exc}", file=sys.stderr)
            sys.exit(4)


    if result:
        print("Meeting found!")
        print(result)
    else:
        print("No meetings detected.")
        print(result)


if __name__ == "__main__":
    master_agent()