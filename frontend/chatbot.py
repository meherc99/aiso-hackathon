import html
from typing import Any, List, Optional, Tuple

from datetime import datetime, date

import gradio as gr

from chat_logic import Message, build_bot_reply, messages_to_history
from storage import ConversationStore

store = ConversationStore()

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
</style>
"""


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
    """Placeholder for real calendar events backing. Replace with real fetch."""
    today = date.today().isoformat()
    return [
        {
            "id": "event-1",
            "title": "Daily Standup",
            "description": "Team sync-up",
            "startDate": today,
            "endDate": today,
            "startTime": "08:30",
            "endTime": "09:00",
            "category": "",
            "done": False,
            "created_at": datetime.now().isoformat(),
        },
        {
            "id": "event-2",
            "title": "Client Sync",
            "description": "Status update with client",
            "startDate": today,
            "endDate": today,
            "startTime": "10:00",
            "endTime": "11:00",
            "category": "",
            "done": False,
            "created_at": datetime.now().isoformat(),
        },
        {
            "id": "event-3",
            "title": "Product Review",
            "description": "Review latest feature progress",
            "startDate": today,
            "endDate": today,
            "startTime": "13:30",
            "endTime": "14:00",
            "category": "",
            "done": False,
            "created_at": datetime.now().isoformat(),
        },
        {
            "id": "event-4",
            "title": "1:1 Check-in",
            "description": "Weekly 1:1",
            "startDate": today,
            "endDate": today,
            "startTime": "16:00",
            "endTime": "16:30",
            "category": "",
            "done": False,
            "created_at": datetime.now().isoformat(),
        },
    ]


def get_todays_events(conversation_id: Optional[str]) -> List[dict]:
    """Filter calendar events for the current day."""
    events = fetch_calendar_events(conversation_id)
    today_str = date.today().isoformat()
    todays_events = [
        event for event in events if event.get("startDate") == today_str
    ]
    return todays_events


def fetch_task_list(_: Optional[str]) -> List[dict]:
    """Stub function returning placeholder tasks for the sidebar."""
    return [
        {
            "title": "Draft project brief",
            "description": "Summarize objectives, timeline, and success metrics.",
        },
        {
            "title": "Review design mockups",
            "description": "Waiting on updated assets from design team.",
        },
        {
            "title": "Send status update email",
            "description": "Share latest milestones with stakeholders.",
        },
    ]


def render_schedule(events: List[dict]) -> str:
    hours = [f"{hour:02d}:00" for hour in range(8, 18)]
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
    bot_reply = build_bot_reply(cleaned, history)
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
                    gr.Markdown("### Today’s Calendar")
                    schedule_panel = gr.HTML(initial_schedule)
                with gr.Column(elem_classes=["panel-card"]):
                    gr.Markdown("### Tasks")
                    tasks_panel = gr.HTML(initial_tasks)

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

    return demo


demo = build_app()


if __name__ == "__main__":
    demo.launch()
