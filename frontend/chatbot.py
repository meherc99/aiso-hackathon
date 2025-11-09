import html
import logging
import os
import re
import subprocess
import threading
from typing import Any, List, Optional, Tuple

from datetime import datetime, date, timedelta

import gradio as gr
import requests

from chat_logic import Message, build_bot_reply, messages_to_history
from storage import ConversationStore

store = ConversationStore()
logger = logging.getLogger(__name__)
CALENDAR_API = os.getenv("VITE_CALENDAR_API", "http://localhost:5050/api")

PANEL_CSS = """
<style>
.panel-card {
    background: var(--block-background-fill);
    border: 1px solid var(--border-color-primary);
    border-radius: var(--radius-lg);
    padding: 12px;
    gap: 10px;
    margin-bottom: 12px;
}
.panel-card:last-of-type {
    margin-bottom: 0;
}
.panel-card h3 {
    margin: 0;
    font-size: 1.05rem;
}
.schedule-grid {
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-height: 360px;
    overflow-y: auto;
    padding-right: 4px;
}
.schedule-row {
    display: grid;
    grid-template-columns: 70px 1fr;
    align-items: center;
    column-gap: 12px;
    padding: 6px 8px;
    border-radius: var(--radius-md);
    background: var(--background-fill-secondary);
}
.schedule-row.has-meeting {
    background: color-mix(in srgb, var(--secondary-600) 18%, transparent);
    border-left: 3px solid var(--secondary-500);
}
.schedule-time {
    font-weight: 600;
    color: var(--body-text-color);
}
.schedule-title {
    color: var(--body-text-color);
    opacity: 0.85;
}
.schedule-empty {
    color: var(--body-text-color);
    opacity: 0.4;
    font-style: italic;
}
.schedule-grid::-webkit-scrollbar {
    width: 0;
    height: 0;
}
.schedule-grid {
    scrollbar-width: none;
}
.tasks-list {
    list-style: disc inside;
    padding-left: 0;
    margin: 0;
    max-height: 260px;
    overflow-y: auto;
    padding-right: 4px;
}
.tasks-list li {
    margin-bottom: 10px;
    color: var(--body-text-color);
}
.tasks-list li:last-of-type {
    margin-bottom: 0;
}
.task-title {
    font-weight: 600;
    color: var(--body-text-color);
}
.task-desc {
    font-size: 0.9rem;
    opacity: 0.75;
    margin-top: 4px;
}
.task-status {
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.85rem;
}
.status-not-started,
.status-in-progress,
.status-blocked {
    display: none;
}
.task-empty {
    font-style: italic;
    opacity: 0.6;
}
.tasks-list::-webkit-scrollbar {
    width: 0;
    height: 0;
}
.tasks-list {
    scrollbar-width: none;
}
.sidebar-column {
    gap: 12px;
}
.conversation-card {
    gap: 10px;
}
.sidebar-heading {
    margin: 0;
}
.sidebar-new-btn button {
    width: 100%;
}
.gradio-container .loading,
.gradio-container .progress-bar,
.gradio-container .progress-bar-wrap,
.gradio-container .progress-bars,
.gradio-container .progress-info,
.gradio-container .progress-viewer,
.gradio-container .progress-viewer * ,
.gradio-container .absolute.w-full.h-full.bg-gradient-to-r.from-gray-50.to-gray-100/80.backdrop-blur {
    display: none !important;
    opacity: 0 !important;
    visibility: hidden !important;
}
.gradio-container .loading span {
    display: none !important;
}

/* Magic AI Button Styling */
#magic-ai-button {
    position: relative;
    background: linear-gradient(135deg, #0066ff 0%, #00ccff 100%);
    border: none;
    border-radius: 50px;
    padding: 16px 48px;
    font-size: 18px;
    font-weight: 600;
    color: white;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    box-shadow: 
        0 4px 15px rgba(0, 102, 255, 0.4),
        0 0 30px rgba(0, 204, 255, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.3);
    cursor: pointer;
    transition: all 0.3s ease;
    overflow: hidden;
    margin: 20px auto;
    display: block;
    width: fit-content;
}

#magic-ai-button::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: linear-gradient(
        45deg,
        transparent,
        rgba(255, 255, 255, 0.1),
        transparent
    );
    transform: rotate(45deg);
    animation: shimmer 3s infinite;
}

@keyframes shimmer {
    0% {
        transform: translateX(-100%) translateY(-100%) rotate(45deg);
    }
    100% {
        transform: translateX(100%) translateY(100%) rotate(45deg);
    }
}

#magic-ai-button:hover {
    transform: translateY(-2px);
    box-shadow: 
        0 6px 25px rgba(0, 102, 255, 0.6),
        0 0 50px rgba(0, 204, 255, 0.5),
        inset 0 1px 0 rgba(255, 255, 255, 0.4);
    background: linear-gradient(135deg, #0077ff 0%, #00ddff 100%);
}

#magic-ai-button:active {
    transform: translateY(0px);
    box-shadow: 
        0 2px 10px rgba(0, 102, 255, 0.5),
        0 0 20px rgba(0, 204, 255, 0.4),
        inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

/* Pulsing glow animation */
@keyframes pulse-glow {
    0%, 100% {
        box-shadow: 
            0 4px 15px rgba(0, 102, 255, 0.4),
            0 0 30px rgba(0, 204, 255, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
    }
    50% {
        box-shadow: 
            0 4px 20px rgba(0, 102, 255, 0.6),
            0 0 45px rgba(0, 204, 255, 0.5),
            inset 0 1px 0 rgba(255, 255, 255, 0.3);
    }
}

#magic-ai-button {
    animation: pulse-glow 2s ease-in-out infinite;
}
</style>
"""


FREE_TIME_KEYWORDS = {
    "pool",
    "swim",
    "gym",
    "run",
    "yoga",
    "dinner",
    "lunch",
    "breakfast",
    "brunch",
    "party",
    "vacation",
    "holiday",
    "family",
    "friends",
    "hangout",
    "movie",
    "concert",
    "wedding",
    "birthday",
    "personal",
    "relax",
    "hobby",
}


def _infer_category(action: dict | None, default: str = "work") -> str:
    if not action:
        return default

    raw = (action.get("new_category") or action.get("category") or "").strip().lower()
    if raw in {"work", "personal"}:
        return raw

    text_bits = [
        action.get("title") or "",
        action.get("description") or "",
        action.get("new_title") or "",
        action.get("new_description") or "",
    ]
    blob = " ".join(text_bits).lower()
    if any(keyword in blob for keyword in FREE_TIME_KEYWORDS):
        return "personal"

    return default or "work"


def conversation_list_update(selected_id: Optional[str], prioritize_selected: bool = False):
    conversations = store.list_conversations()
    if not conversations:
        return gr.update(choices=[], value=None)

    conversation_ids = [str(item.get("_id") or item.get("id")) for item in conversations]
    if selected_id not in conversation_ids:
        selected_id = conversation_ids[0]

    choices = [
        (item.get("title") or f"Conversation {index + 1}", str(item.get("_id") or item.get("id")))
        for index, item in enumerate(conversations)
    ]
    if prioritize_selected and selected_id:
        selected_choice = [choice for choice in choices if choice[1] == selected_id]
        remaining_choices = [choice for choice in choices if choice[1] != selected_id]
        choices = [*selected_choice, *remaining_choices]

    return gr.update(choices=choices, value=selected_id)


def fetch_calendar_events(_: Optional[str]) -> List[dict]:
    """Fetch events from the calendar server REST API."""
    try:
        response = requests.get(f"{CALENDAR_API}/events", timeout=10)
        response.raise_for_status()
        events = response.json()
        if isinstance(events, list):
            return events
    except Exception as exc:
        print(f"[chatbot] Failed to load calendar events: {exc}")
    return []


def get_todays_events(conversation_id: Optional[str]) -> List[dict]:
    """Filter calendar events for the current day."""
    events = fetch_calendar_events(conversation_id)
    today_str = date.today().isoformat()
    todays_events = [
        event for event in events if event.get("startDate") == today_str
    ]
    return todays_events


def fetch_task_list(_: Optional[str]) -> List[dict]:
    """Fetch tasks captured by the agent from the calendar server REST API."""
    try:
        response = requests.get(f"{CALENDAR_API}/tasks", timeout=10)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print(f"[chatbot] Failed to load tasks: {exc}")
        return []

    if not isinstance(payload, list):
        return []

    tasks: List[dict] = []
    for item in payload:
        tasks.append(
            {
                "title": item.get("title") or "Untitled task",
                "description": item.get("description") or "",
                "dueDate": item.get("date_of_meeting"),
                "dueTime": item.get("start_time"),
                "completed": item.get("meeting_completed", False),
            }
        )
    return tasks


def _add_one_hour(start_time: str) -> str:
    return _add_minutes_to_time(start_time, 60)


def _normalise_time(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    try:
        datetime.strptime(value, "%H:%M")
        return value
    except ValueError:
        return None


def _coerce_time_string(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip()
    if not value:
        return ""

    normal = _normalise_time(value)
    if normal:
        return normal

    if len(value) >= 5 and value[2] == ":":
        candidate = value[:5]
        normal = _normalise_time(candidate)
        if normal:
            return normal

    if value.isdigit():
        if len(value) <= 2:
            candidate = value.zfill(2) + ":00"
            normal = _normalise_time(candidate)
            if normal:
                return normal

    return value


_NUMBER_WORDS = {
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

_NEGATIVE_KEYWORDS = {"earlier", "before", "forward", "sooner", "ahead"}


def _parse_time_offset(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    lowered = text.lower()

    numeric_pattern = re.compile(
        r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>hours?|hrs?|minutes?|mins?)\s*(?P<direction>later|after|earlier|before|forward|sooner|back)",
        re.IGNORECASE,
    )
    word_pattern = re.compile(
        r"(?P<amount_word>zero|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|half|quarter)\s*(?P<unit>hours?|hrs?|minutes?|mins?)\s*(?P<direction>later|after|earlier|before|forward|sooner|back)",
        re.IGNORECASE,
    )

    match = numeric_pattern.search(lowered)
    if match:
        amount = float(match.group("amount"))
        unit = match.group("unit").lower()
        direction = match.group("direction").lower()
    else:
        match = word_pattern.search(lowered)
        if not match:
            return None
        amount_word = match.group("amount_word").lower()
        amount = _NUMBER_WORDS.get(amount_word)
        if amount is None:
            return None
        unit = match.group("unit").lower()
        direction = match.group("direction").lower()

    if unit.startswith("hour") or unit.startswith("hr"):
        minutes = int(amount * 60)
    else:
        minutes = int(amount * 1)

    if direction in _NEGATIVE_KEYWORDS:
        minutes *= -1
    return minutes


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M")
    except ValueError:
        return None


def _add_minutes_to_time(start_time: Optional[str], minutes: int, default: str = "09:00") -> str:
    base = _parse_time(start_time) or _parse_time(default)
    if not base:
        base = datetime.strptime("09:00", "%H:%M")
    total_minutes = base.hour * 60 + base.minute + minutes
    total_minutes = max(0, min(total_minutes, 23 * 60 + 59))
    hour = total_minutes // 60
    minute = total_minutes % 60
    return f"{hour:02d}:{minute:02d}"


def _compute_duration_minutes(start_time: Optional[str], end_time: Optional[str]) -> Optional[int]:
    start_dt = _parse_time(start_time)
    end_dt = _parse_time(end_time)
    if not start_dt or not end_dt:
        return None
    delta = end_dt - start_dt
    minutes = int(delta.total_seconds() // 60)
    return minutes if minutes > 0 else None


def apply_calendar_action(action: Optional[dict], user_message: Optional[str] = None) -> Optional[str]:
    if not action or action.get("action") in (None, "none"):
        return None

    action_type = action.get("action")

    if action_type == "create":
        date_str = (action.get("date") or action.get("date_of_meeting") or "").strip()
        if not date_str:
            logger.debug("Calendar action create ignored: missing date in %s", action)
            return "⚠️ I couldn’t schedule that meeting because no date was given."

        start_time = _normalise_time(action.get("start_time") or action.get("startTime"))
        if not start_time:
            start_time = "09:00"
        end_time = _normalise_time(action.get("end_time") or action.get("endTime"))
        if not end_time:
            end_time = _add_one_hour(start_time)

        title = (action.get("title") or "Meeting").strip() or "Meeting"
        description = (action.get("description") or "").strip()
        payload = {
            "title": title,
            "description": description,
            "startDate": date_str,
            "endDate": date_str,
            "startTime": start_time,
            "endTime": end_time,
            "category": "work",
            "time": start_time,
        }
        payload["category"] = _infer_category({**(action or {}), **payload}, default="work")

        try:
            resp = requests.post(f"{CALENDAR_API}/events", json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to create calendar event: %s", exc)
            return "⚠️ I tried to add that meeting but something went wrong."

        logger.info("Created calendar event: %s", payload)
        return f"✅ Scheduled “{title}” on {date_str} at {start_time}."

    if action_type == "delete" or action_type == "reschedule":
        try:
            events = fetch_calendar_events(None)
        except Exception:
            events = []

        candidate_id = action.get("event_id") or action.get("id")
        target_event = None
        title_hint = (action.get("title") or "").strip().lower()
        date_hint = (action.get("date") or action.get("date_of_meeting") or "").strip()
        raw_time_hint = (action.get("start_time") or action.get("startTime") or "").strip()
        time_hint = _coerce_time_string(raw_time_hint)

        if candidate_id and not target_event:
            target_event = next((ev for ev in events if ev.get("id") == candidate_id), None)

        if not candidate_id:
            for event in events:
                if target_event:
                    break
                event_title = (event.get("title") or "").lower()
                event_date = event.get("startDate") or event.get("date_of_meeting") or ""
                event_time_raw = event.get("startTime") or event.get("start_time") or event.get("time") or ""
                event_time_norm = _coerce_time_string(event_time_raw)

                if title_hint and title_hint not in event_title:
                    continue
                if date_hint and date_hint != event_date:
                    continue
                if time_hint and time_hint != event_time_norm:
                    continue

                candidate_id = event.get("id")
                target_event = event
                if candidate_id:
                    break

        if not candidate_id:
            fallback_matches = []
            for event in events:
                event_title = (event.get("title") or "").lower()
                event_date = event.get("startDate") or event.get("date_of_meeting") or ""
                if date_hint and date_hint != event_date:
                    continue
                if title_hint and title_hint not in event_title:
                    continue
                fallback_matches.append(event)

            if fallback_matches:
                target_event = fallback_matches[0]
                candidate_id = target_event.get("id")

        if not candidate_id:
            logger.debug("Calendar delete/reschedule ignored: no matching event for %s", action)
            return "⚠️ I couldn’t find a matching meeting to delete." if action_type == "delete" else "⚠️ I couldn’t find the meeting to reschedule."

        if not target_event and candidate_id:
            target_event = next((ev for ev in events if ev.get("id") == candidate_id), None)

        try:
            resp = requests.delete(f"{CALENDAR_API}/events/{candidate_id}", timeout=10)
            if resp.status_code == 404:
                return "⚠️ I couldn’t find a matching meeting to delete." if action_type == "delete" else "⚠️ I couldn’t find the meeting to reschedule."
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to delete calendar event: %s", exc)
            return "⚠️ I tried to remove that meeting but something went wrong."

        logger.info("Deleted calendar event id=%s", candidate_id)

        if action_type == "delete":
            return "🗑️ Removed the meeting from your calendar."

        # Reschedule branch
        if not target_event:
            logger.debug("Reschedule: deleted event but missing cached details, cannot recreate")
            return "⚠️ Removed the original meeting but couldn’t create the new one."  # Unlikely

        existing_title = target_event.get("title") or "Meeting"
        existing_description = target_event.get("description") or ""
        existing_date = target_event.get("startDate") or target_event.get("date_of_meeting") or ""
        existing_start = (
            target_event.get("startTime")
            or target_event.get("start_time")
            or target_event.get("time")
            or "09:00"
        )
        existing_end = target_event.get("endTime") or target_event.get("end_time") or ""
        existing_category = target_event.get("category") or "work"
        existing_duration = _compute_duration_minutes(existing_start, existing_end)

        new_title = (action.get("new_title") or action.get("title") or existing_title).strip() or existing_title
        new_description = (action.get("new_description") or action.get("description") or existing_description).strip()
        new_date = (action.get("new_date") or action.get("date") or action.get("date_of_meeting") or existing_date).strip() or existing_date

        new_start_candidate = _coerce_time_string(
            action.get("new_start_time") or action.get("start_time") or action.get("startTime")
        )
        new_start = _normalise_time(new_start_candidate)

        offset_minutes = _parse_time_offset(user_message)
        if offset_minutes is not None:
            base_for_offset = existing_start or new_start or "09:00"
            new_start = _add_minutes_to_time(base_for_offset, offset_minutes)

        if not new_start:
            new_start = existing_start or "09:00"

        new_end_candidate = _coerce_time_string(
            action.get("new_end_time") or action.get("end_time") or action.get("endTime")
        )
        new_end = _normalise_time(new_end_candidate)

        if offset_minutes is not None and existing_duration is not None:
            new_end = _add_minutes_to_time(new_start, existing_duration)

        if not new_end:
            if existing_duration is not None:
                new_end = _add_minutes_to_time(new_start, existing_duration)
            else:
                new_end = _add_one_hour(new_start)

        category = _infer_category({**(action or {}), **target_event}, default=existing_category or "work")

        payload = {
            "title": new_title,
            "description": new_description,
            "startDate": new_date,
            "endDate": new_date,
            "startTime": new_start,
            "endTime": new_end,
            "category": category,
            "time": new_start,
        }
        payload["category"] = _infer_category({**(action or {}), **payload}, default=category)

        try:
            resp = requests.post(f"{CALENDAR_API}/events", json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to create rescheduled event: %s", exc)
            return "⚠️ I removed the original meeting but couldn’t create the new one."

        logger.info("Rescheduled calendar event: %s -> %s", target_event.get("id"), payload)
        return f"🔁 Rescheduled “{new_title}” for {new_date} at {new_start}."

    return None


def render_schedule(events: List[dict]) -> str:
    hours = [f"{hour:02d}:00" for hour in range(8, 23)]
    slots: dict[str, List[str]] = {hour: [] for hour in hours}
    all_day: List[str] = []

    for event in events:
        title = html.escape(event.get("title") or "Untitled event")
        start_time = event.get("startTime")
        end_time = event.get("endTime")
        time_range = ""
        if start_time and end_time:
            time_range = f"{start_time}–{end_time}"
        elif start_time:
            time_range = start_time

        description = html.escape(event.get("description") or "")
        meta = f"{title}"
        if time_range:
            meta += f" · {time_range}"
        if description:
            meta += f"<br><small>{description}</small>"

        if start_time:
            hour_slot = f"{start_time[:2]}:00"
            slots.setdefault(hour_slot, []).append(meta)
        else:
            all_day.append(meta)

    rows: List[str] = []
    if all_day:
        rows.append(
            '<div class="schedule-row has-meeting">'
            '<div class="schedule-time">All Day</div>'
            f'<div class="schedule-title">{"<br>".join(all_day)}</div>'
            "</div>"
        )

    for hour in hours:
        meetings = slots.get(hour, [])
        is_meeting = bool(meetings)
        content = "<br>".join(meetings) if meetings else '<span class="schedule-empty">– free –</span>'
        row_class = "schedule-row has-meeting" if is_meeting else "schedule-row"
        rows.append(
            f'<div class="{row_class}"><div class="schedule-time">{hour}</div>'
            f'<div class="schedule-title">{content}</div></div>'
        )

    return f'<div class="schedule-grid">{"".join(rows)}</div>'


def render_tasks(tasks: List[dict]) -> str:
    if not tasks:
        return '<ul class="tasks-list"><li class="task-empty">No tasks yet.</li></ul>'

    items: List[str] = []
    for task in tasks:
        title = html.escape(task.get("title", "Untitled task"))
        description_raw = (task.get("description") or "").strip()
        if description_raw and len(description_raw) > 140:
            description_raw = description_raw[:137].rstrip() + "..."
        description = html.escape(description_raw)
        desc_html = f'<div class="task-desc">{description}</div>' if description else ""
        items.append(f"<li><span class=\"task-title\">{title}</span>{desc_html}</li>")
    return f'<ul class="tasks-list">{"".join(items)}</ul>'


def run_agent_background(conversation_id: Optional[str]) -> Tuple[str, str]:
    """
    Run the backend agent.py script in a background thread.
    Returns updated schedule and tasks HTML after execution.
    """
    def run_agent():
        try:
            # Get the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            agent_path = os.path.join(project_root, "backend", "agent.py")
            
            print(f"[chatbot] Starting AI agent: {agent_path}")
            
            # Run the agent script
            result = subprocess.run(
                ["python", agent_path],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print(f"[chatbot] AI agent completed successfully")
                print(f"[chatbot] Agent output:\n{result.stdout}")
            else:
                print(f"[chatbot] AI agent failed with code {result.returncode}")
                print(f"[chatbot] Error output:\n{result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"[chatbot] AI agent timed out after 5 minutes")
        except Exception as exc:
            print(f"[chatbot] Failed to run AI agent: {exc}")
    
    # Start agent in background thread
    thread = threading.Thread(target=run_agent, daemon=True)
    thread.start()
    
    # Return status message
    status_message = """
    <div style="padding: 20px; text-align: center; background: linear-gradient(135deg, #0066ff22 0%, #00ccff22 100%); border-radius: 12px; border: 2px solid #0066ff44;">
        <h3 style="color: #0066ff; margin: 0 0 10px 0;">🚀 AI Agent Running</h3>
        <p style="margin: 0; color: #666;">Processing Slack messages and extracting meetings/tasks...</p>
        <p style="margin: 10px 0 0 0; font-size: 0.9em; color: #999;">This may take a few minutes. Results will appear when complete.</p>
    </div>
    """
    
    return status_message, status_message


def handle_user_message(
    message: str,
    history: List[Message],
    conversation_id: Optional[str],
) -> Tuple[List[Message], str, str, Any, str, str]:
    history = history or []
    cleaned = message.strip()

    created_now = False
    if not conversation_id:
        conversation_id = store.create_conversation()
        created_now = True

    if not cleaned:
        sidebar_update = conversation_list_update(
            conversation_id,
            prioritize_selected=created_now,
        )
        schedule_html = render_schedule(get_todays_events(conversation_id))
        tasks_html = render_tasks(fetch_task_list(conversation_id))
        return history, "", conversation_id, sidebar_update, schedule_html, tasks_html

    store.append_message(conversation_id, "user", cleaned)
    bot_reply, calendar_action = build_bot_reply(cleaned, history)
    action_feedback = apply_calendar_action(calendar_action, cleaned)
    if action_feedback:
        bot_reply = f"{bot_reply}\n\n{action_feedback}"
    store.append_message(conversation_id, "assistant", bot_reply)
    store.update_title_if_missing(conversation_id, cleaned)

    # Reload the full conversation history from storage to ensure consistency
    messages = store.fetch_messages(conversation_id)
    updated_history = messages_to_history(messages)

    sidebar_update = conversation_list_update(
        conversation_id,
        prioritize_selected=created_now,
    )
    schedule_html = render_schedule(get_todays_events(conversation_id))
    tasks_html = render_tasks(fetch_task_list(conversation_id))
    return updated_history, "", conversation_id, sidebar_update, schedule_html, tasks_html


def initialize_interface() -> Tuple[List[Message], str, str, Any, str, str]:
    conversations = store.list_conversations()
    if conversations:
        conversation_id = str(conversations[0].get("_id") or conversations[0].get("id"))
    else:
        conversation_id = store.create_conversation()
        conversations = store.list_conversations()

    messages = store.fetch_messages(conversation_id)
    history = messages_to_history(messages)
    sidebar_update = conversation_list_update(conversation_id)
    schedule_html = render_schedule(get_todays_events(conversation_id))
    tasks_html = render_tasks(fetch_task_list(conversation_id))
    return history, "", conversation_id, sidebar_update, schedule_html, tasks_html


def start_new_conversation() -> Tuple[List[Message], str, str, Any, str, str]:
    conversation_id = store.create_conversation()
    sidebar_update = conversation_list_update(
        conversation_id,
        prioritize_selected=True,
    )
    schedule_html = render_schedule(get_todays_events(conversation_id))
    tasks_html = render_tasks(fetch_task_list(conversation_id))
    return [], "", conversation_id, sidebar_update, schedule_html, tasks_html


def clear_current_conversation(
    conversation_id: Optional[str],
) -> Tuple[List[Message], str, str, Any, str, str]:
    if conversation_id:
        store.reset_conversation(conversation_id)
        sidebar_update = conversation_list_update(conversation_id)
        messages = store.fetch_messages(conversation_id)
        history = messages_to_history(messages)
        schedule_html = render_schedule(get_todays_events(conversation_id))
        tasks_html = render_tasks(fetch_task_list(conversation_id))
        return history, "", conversation_id, sidebar_update, schedule_html, tasks_html

    new_id = store.create_conversation()
    sidebar_update = conversation_list_update(
        new_id,
        prioritize_selected=True,
    )
    schedule_html = render_schedule(get_todays_events(new_id))
    tasks_html = render_tasks(fetch_task_list(new_id))
    return [], "", new_id, sidebar_update, schedule_html, tasks_html


def load_conversation(
    conversation_id: Optional[str],
) -> Tuple[List[Message], str, str, Any, str, str]:
    if not conversation_id:
        new_id = store.create_conversation()
        sidebar_update = conversation_list_update(
            new_id,
            prioritize_selected=True,
        )
        schedule_html = render_schedule(get_todays_events(new_id))
        tasks_html = render_tasks(fetch_task_list(new_id))
        return [], "", new_id, sidebar_update, schedule_html, tasks_html

    messages = store.fetch_messages(conversation_id)
    history = messages_to_history(messages)
    sidebar_update = conversation_list_update(conversation_id)
    schedule_html = render_schedule(get_todays_events(conversation_id))
    tasks_html = render_tasks(fetch_task_list(conversation_id))
    return history, "", conversation_id, sidebar_update, schedule_html, tasks_html


def build_app() -> gr.Blocks:
    theme = gr.themes.Soft(primary_hue="blue", secondary_hue="slate", radius_size="lg")

    with gr.Blocks(theme=theme) as demo:
        gr.HTML(PANEL_CSS)
        conversation_state = gr.State()

        # Tab system for Chat and Calendar views
        with gr.Tabs() as tabs:
            # Chat Tab
            with gr.TabItem("Chat Assistant", id="chat_tab"):
                with gr.Row(equal_height=True):
                    with gr.Column(scale=1, min_width=240, elem_classes=["sidebar-column"]):
                        with gr.Column(elem_classes=["panel-card", "conversation-card"]):
                            gr.Markdown("### Conversations", elem_classes=["sidebar-heading"])
                            new_conversation_btn = gr.Button("New", size="sm", elem_classes=["sidebar-new-btn"])
                            conversation_list = gr.Radio(
                                label="",
                                show_label=False,
                                choices=[],
                                value=None,
                                interactive=True,
                                container=True,
                            )

                    with gr.Column(scale=4):
                        chatbot = gr.Chatbot(
                            label="Chat",
                            height="80vh",
                            type="messages",
                        )
                        
                        # Magic AI Button
                        magic_button = gr.Button(
                            "AI Magic",
                            elem_id="magic-ai-button",
                            size="lg",
                            variant="primary"
                        )
                        
                        with gr.Row():
                            
                            message = gr.Textbox(
                                show_label=False,
                                placeholder="Send a message…",
                                autofocus=True,
                                lines=1,
                                max_lines=3,
                                scale=9,
                            )
                            send = gr.Button("➤", size="sm", scale=1, min_width=50)  # Moved outside of gr.Group to align on the right

                    with gr.Column(scale=2, min_width=260):
                        initial_schedule = render_schedule(get_todays_events(None))
                        initial_tasks = render_tasks(fetch_task_list(None))
                        with gr.Column(elem_classes=["panel-card"]):
                            gr.Markdown("### Today's Calendar")
                            schedule_panel = gr.HTML(initial_schedule)
                        with gr.Column(elem_classes=["panel-card"]):
                            gr.Markdown("### Tasks")
                            tasks_panel = gr.HTML(initial_tasks)
            
            # Calendar Tab
            with gr.TabItem("Full Calendar", id="calendar_tab"):
                
                # Iframe to embed the React calendar app
                # The calendar will be served from http://localhost:5050 (calendar server)
                # or from http://localhost:5173 (Vite dev server)
                calendar_iframe = gr.HTML(
                    """
                    <iframe 
                        src="http://localhost:5050/" 
                        width="100%" 
                        height="800px" 
                        frameborder="0"
                        style="border: 1px solid #ddd; border-radius: 8px; background: white;"
                        onload="this.style.display='block';"
                        onerror="this.innerHTML='<div style=padding:20px;text-align:center;>Calendar app not available. Please ensure:<br>1. Calendar server is running: python backend/calendar_server.py<br>2. Or React dev server is running: cd src && npm run dev</div>';"
                    >
                        <p>Loading calendar... If this message persists, please check:</p>
                        <ol style="text-align: left; display: inline-block;">
                            <li>Calendar server is running: <code>python backend/calendar_server.py</code></li>
                            <li>Or React dev server is running: <code>cd src && npm run dev</code></li>
                            <li>Try accessing directly: <a href="http://localhost:5050" target="_blank">http://localhost:5050</a></li>
                        </ol>
                    </iframe>
                    """
                )
             

        demo.load(
            initialize_interface,
            inputs=None,
            outputs=[
                chatbot,
                message,
                conversation_state,
                conversation_list,
                schedule_panel,
                tasks_panel,
            ],
        )

        message.submit(
            handle_user_message,
            inputs=[message, chatbot, conversation_state],
            outputs=[
                chatbot,
                message,
                conversation_state,
                conversation_list,
                schedule_panel,
                tasks_panel,
            ],
            queue=False,
        )
        send.click(
            handle_user_message,
            inputs=[message, chatbot, conversation_state],
            outputs=[
                chatbot,
                message,
                conversation_state,
                conversation_list,
                schedule_panel,
                tasks_panel,
            ],
            queue=False,
        )

        new_conversation_btn.click(
            start_new_conversation,
            inputs=None,
            outputs=[
                chatbot,
                message,
                conversation_state,
                conversation_list,
                schedule_panel,
                tasks_panel,
            ],
            queue=False,
        )

        conversation_list.change(
            load_conversation,
            inputs=[conversation_list],
            outputs=[
                chatbot,
                message,
                conversation_state,
                conversation_list,
                schedule_panel,
                tasks_panel,
            ],
            queue=False,
        )

        magic_button.click(
            run_agent_background,
            inputs=[conversation_state],
            outputs=[schedule_panel, tasks_panel],
            queue=False,
        )

    return demo


demo = build_app()


if __name__ == "__main__":
    demo.launch()
