import html
import logging
import os
import sys
import subprocess
import threading
from typing import Any, List, Optional, Tuple
import time

from datetime import datetime, date, timedelta

import gradio as gr
import requests

from chat_logic import Message, build_bot_reply, messages_to_history
from storage import ConversationStore

store = ConversationStore()
logger = logging.getLogger(__name__)
CALENDAR_API = os.getenv("VITE_CALENDAR_API", "http://localhost:5050/api")

# Get the path to the CSS file
CSS_FILE = os.path.join(os.path.dirname(__file__), "static", "chatbot.css")

# Link to external CSS for browser caching
PANEL_CSS = '<link rel="stylesheet" href="/static/chatbot.css">'


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
    try:
        base = datetime.strptime(start_time, "%H:%M")
    except ValueError:
        base = datetime.strptime("09:00", "%H:%M")
    end = base + timedelta(hours=1)
    return end.strftime("%H:%M")


def _normalise_time(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    try:
        datetime.strptime(value, "%H:%M")
        return value
    except ValueError:
        return None


def apply_calendar_action(action: Optional[dict]) -> Optional[str]:
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
            "category": action.get("category") or "work",
        }

        try:
            resp = requests.post(f"{CALENDAR_API}/events", json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to create calendar event: %s", exc)
            return "⚠️ I tried to add that meeting but something went wrong."

        logger.info("Created calendar event: %s", payload)
        return f"✅ Scheduled “{title}” on {date_str} at {start_time}."

    if action_type == "delete":
        try:
            events = fetch_calendar_events(None)
        except Exception:
            events = []

        candidate_id = action.get("event_id") or action.get("id")
        title_hint = (action.get("title") or "").strip().lower()
        date_hint = (action.get("date") or action.get("date_of_meeting") or "").strip()
        time_hint = (action.get("start_time") or action.get("startTime") or "").strip()

        if not candidate_id:
            for event in events:
                event_title = (event.get("title") or "").lower()
                event_date = event.get("startDate") or event.get("date_of_meeting") or ""
                event_time = event.get("startTime") or event.get("start_time") or ""

                if title_hint and title_hint not in event_title:
                    continue
                if date_hint and date_hint != event_date:
                    continue
                if time_hint and time_hint != event_time:
                    continue
                candidate_id = event.get("id")
                if candidate_id:
                    break

        if not candidate_id:
            logger.debug("Calendar delete: fell back to events search, candidate=%s", candidate_id)

        if not candidate_id:
            logger.debug("Calendar delete ignored: no matching event for %s", action)
            return "⚠️ I couldn’t find a matching meeting to delete."

        try:
            resp = requests.delete(f"{CALENDAR_API}/events/{candidate_id}", timeout=10)
            if resp.status_code == 404:
                return "⚠️ I couldn’t find a matching meeting to delete."
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to delete calendar event: %s", exc)
            return "⚠️ I tried to remove that meeting but something went wrong."

        logger.info("Deleted calendar event id=%s", candidate_id)
        return "🗑️ Removed the meeting from your calendar."

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
    Run the backend agent.py script and wait for scheduler to process results.
    This ensures the UI shows accurate data after completion.
    """
    try:
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        agent_path = os.path.join(project_root, "backend", "agent.py")
        
        print(f"[chatbot] Starting AI agent: {agent_path}")
        
        # Get initial counts to compare later
        initial_events = fetch_calendar_events(conversation_id)
        initial_tasks = fetch_task_list(conversation_id)
        initial_event_count = len(initial_events)
        initial_task_count = len(initial_tasks)
        
        # Run the agent script synchronously
        result = subprocess.run(
            [sys.executable, agent_path],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print(f"[chatbot] AI agent completed successfully")
            print(f"[chatbot] Agent output:\n{result.stdout}")
            
            # Wait for scheduler to process the results
            # Poll the database every 2 seconds for up to 2 minutes
            max_wait_time = 120  # 2 minutes
            poll_interval = 2  # seconds
            elapsed = 0
            
            print(f"[chatbot] Waiting for scheduler to process results...")
            
            while elapsed < max_wait_time:
                time.sleep(poll_interval)
                elapsed += poll_interval
                
                # Check if new events or tasks have appeared
                current_events = fetch_calendar_events(conversation_id)
                current_tasks = fetch_task_list(conversation_id)
                current_event_count = len(current_events)
                current_task_count = len(current_tasks)
                
                # If we have new data, the scheduler has processed
                if current_event_count > initial_event_count or current_task_count > initial_task_count:
                    print(f"[chatbot] Scheduler processed results after {elapsed}s")
                    print(f"[chatbot] Events: {initial_event_count} -> {current_event_count}")
                    print(f"[chatbot] Tasks: {initial_task_count} -> {current_task_count}")
                    break
                
                # Show progress
                if elapsed % 10 == 0:
                    print(f"[chatbot] Still waiting... ({elapsed}s elapsed)")
            
            # Fetch final data after waiting
            final_events = fetch_calendar_events(conversation_id)
            final_tasks = fetch_task_list(conversation_id)
            meetings_count = len(final_events)
            tasks_count = len(final_tasks)
            
            # Calculate what was added
            new_meetings = meetings_count - initial_event_count
            new_tasks = tasks_count - initial_task_count
            
            # Render the updated panels
            schedule_html = render_schedule(get_todays_events(conversation_id))
            tasks_html = render_tasks(final_tasks)
            
            # Add success message with actual counts
            if new_meetings > 0 or new_tasks > 0:
                success_msg = f"""
                <div style="padding: 12px; margin-bottom: 12px; background: linear-gradient(135deg, #00ff8822 0%, #00ff4422 100%); border-radius: 8px; border: 2px solid #00ff8844;">
                    <div style="font-weight: 600; color: #00aa44; margin-bottom: 4px;">✓ AI Agent Completed</div>
                    <div style="font-size: 0.9em; color: #666;">
                        Added {new_meetings} new meeting(s) and {new_tasks} new task(s)
                        <br>Total: {meetings_count} meeting(s) and {tasks_count} task(s)
                    </div>
                </div>
                {schedule_html}
                """
            else:
                success_msg = f"""
                <div style="padding: 12px; margin-bottom: 12px; background: linear-gradient(135deg, #ffaa0022 0%, #ff880022 100%); border-radius: 8px; border: 2px solid #ffaa0044;">
                    <div style="font-weight: 600; color: #cc6600; margin-bottom: 4px;">✓ AI Agent Completed</div>
                    <div style="font-size: 0.9em; color: #666;">
                        No new meetings or tasks found
                        <br>Waited {elapsed}s for scheduler processing
                    </div>
                </div>
                {schedule_html}
                """
            
            return success_msg, tasks_html
            
        else:
            print(f"[chatbot] AI agent failed with code {result.returncode}")
            print(f"[chatbot] Error output:\n{result.stderr}")
            
            error_msg = """
            <div style="padding: 12px; background: linear-gradient(135deg, #ff444422 0%, #ff000022 100%); border-radius: 8px; border: 2px solid #ff444444;">
                <div style="font-weight: 600; color: #cc0000; margin-bottom: 4px;">✗ AI Agent Failed</div>
                <div style="font-size: 0.9em; color: #666;">Check terminal logs for details</div>
            </div>
            """
            
            schedule_html = render_schedule(get_todays_events(conversation_id))
            tasks_html = render_tasks(fetch_task_list(conversation_id))
            
            return error_msg + schedule_html, tasks_html
            
    except subprocess.TimeoutExpired:
        print(f"[chatbot] AI agent timed out after 5 minutes")
        
        timeout_msg = """
        <div style="padding: 12px; background: linear-gradient(135deg, #ffaa0022 0%, #ff880022 100%); border-radius: 8px; border: 2px solid #ffaa0044;">
            <div style="font-weight: 600; color: #cc6600; margin-bottom: 4px;">⏱ AI Agent Timeout</div>
            <div style="font-size: 0.9em; color: #666;">Processing took longer than 5 minutes</div>
        </div>
        """
        
        schedule_html = render_schedule(get_todays_events(conversation_id))
        tasks_html = render_tasks(fetch_task_list(conversation_id))
        
        return timeout_msg + schedule_html, tasks_html
        
    except Exception as exc:
        print(f"[chatbot] Failed to run AI agent: {exc}")
        
        error_msg = f"""
        <div style="padding: 12px; background: linear-gradient(135deg, #ff444422 0%, #ff000022 100%); border-radius: 8px; border: 2px solid #ff444444;">
            <div style="font-weight: 600; color: #cc0000; margin-bottom: 4px;">✗ Error Running Agent</div>
            <div style="font-size: 0.9em; color: #666;">{html.escape(str(exc))}</div>
        </div>
        """
        
        schedule_html = render_schedule(get_todays_events(conversation_id))
        tasks_html = render_tasks(fetch_task_list(conversation_id))
        
        return error_msg + schedule_html, tasks_html


def handle_user_message(
    message: str,
    history: List[Message],
    conversation_id: Optional[str],
) -> Tuple[List[Message], str, str, str, str]:
    history = history or []
    cleaned = message.strip()

    conversation_id = conversation_id or store.default_conversation_id()

    if not cleaned:
        schedule_html = render_schedule(get_todays_events(conversation_id))
        tasks_html = render_tasks(fetch_task_list(conversation_id))
        return history, "", conversation_id, schedule_html, tasks_html

    store.append_message(conversation_id, "user", cleaned)
    bot_reply, calendar_action = build_bot_reply(cleaned, history)
    action_feedback = apply_calendar_action(calendar_action)
    if action_feedback:
        bot_reply = f"{bot_reply}\n\n{action_feedback}"
    store.append_message(conversation_id, "assistant", bot_reply)

    messages = store.fetch_messages(conversation_id)
    updated_history = messages_to_history(messages)
    schedule_html = render_schedule(get_todays_events(conversation_id))
    tasks_html = render_tasks(fetch_task_list(conversation_id))
    return updated_history, "", conversation_id, schedule_html, tasks_html


def initialize_interface() -> Tuple[List[Message], str, str, str, str]:
    conversation_id = store.default_conversation_id()
    messages = store.fetch_messages(conversation_id)
    history = messages_to_history(messages)
    schedule_html = render_schedule(get_todays_events(conversation_id))
    tasks_html = render_tasks(fetch_task_list(conversation_id))
    return history, "", conversation_id, schedule_html, tasks_html


def start_new_conversation() -> Tuple[List[Message], str, str, str, str]:
    store.reset_conversation(store.default_conversation_id())
    return initialize_interface()


def clear_current_conversation(
    conversation_id: Optional[str],
) -> Tuple[List[Message], str, str, str, str]:
    store.reset_conversation(store.default_conversation_id())
    return initialize_interface()


def load_conversation(
    conversation_id: Optional[str],
) -> Tuple[List[Message], str, str, str, str]:
    return initialize_interface()


def build_app() -> gr.Blocks:
    theme = gr.themes.Soft(primary_hue="blue", secondary_hue="slate", radius_size="lg")

    with gr.Blocks(theme=theme, css_paths=[CSS_FILE]) as demo:
        conversation_state = gr.State()

        # Tab system for Chat and Calendar views
        with gr.Tabs() as tabs:
            # Chat Tab
            with gr.TabItem("Chat Assistant", id="chat_tab"):
                with gr.Row(equal_height=True):
                    with gr.Column(scale=1, min_width=240, elem_classes=["sidebar-column"]):
                        gr.HTML("&nbsp;")

                    with gr.Column(scale=4):
                        chatbot = gr.Chatbot(
                            label="Chat",
                            height="80vh",
                            type="messages",
                        )

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
                            send = gr.Button("Send", size="sm", scale=1, min_width=50)  # Moved outside of gr.Group to align on the right

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
                schedule_panel,
                tasks_panel,
            ],
            queue=False,
        )

        magic_button.click(
            run_agent_background,
            inputs=[conversation_state],
            outputs=[schedule_panel, tasks_panel],
            queue=True,  # Enable queue to show loading state
        )

    return demo


demo = build_app()


if __name__ == "__main__":
    demo.launch()
