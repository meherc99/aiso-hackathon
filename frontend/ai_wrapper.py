"""Utility helpers for generating friendly AI replies to user messages."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable, List, Mapping, Sequence

import openai
import requests
from dotenv import load_dotenv
from openai import APIError, OpenAIError, RateLimitError

ConversationTurn = Mapping[str, str]

logger = logging.getLogger(__name__)


def _normalise_history(history: Iterable[ConversationTurn]) -> List[ConversationTurn]:
    """Ensure the history only contains role/content pairs with non-empty values."""
    normalised: List[ConversationTurn] = []
    for item in history:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role and content:
            normalised.append({"role": role, "content": content})
    return normalised


@dataclass
class FriendlyAIWrapper:
    """Thin wrapper around the OpenAI client for generating upbeat replies."""

    model: str = "gpt-5-nano"
    base_url: str = "https://fj7qg3jbr3.execute-api.eu-west-1.amazonaws.com/v1"
    system_prompt: str = (
        "You are a warm, upbeat conversation partner who acts like a friendly guide. "
        "Blend empathy with practical insight, highlight next steps or suggestions, "
        "and mirror the user’s mood without being overly formal. Keep answers concise "
        "(2-4 sentences), avoid jargon unless the user invites it, and always end with "
        "an optional question or invitation to continue the chat."
        
    )
    _client: openai.OpenAI | None = field(default=None, init=False, repr=False)
    _api_key_missing: bool = field(default=False, init=False, repr=False)

    calendar_api: str = field(default_factory=lambda: os.getenv("VITE_CALENDAR_API") or os.getenv("CALENDAR_API") or "http://localhost:5050/api")

    def __post_init__(self) -> None:
        load_dotenv(override=False)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logging.warning("OPENAI_API_KEY is not set; AI replies will use fallback text.")
            self._api_key_missing = True
            return

        try:
            self._client = openai.OpenAI(api_key=api_key, base_url=self.base_url)
        except OpenAIError as exc:  # Broad exception to capture misconfiguration at startup.
            logging.error("Unable to initialise OpenAI client: %s", exc)
            self._api_key_missing = True

    def generate_reply(
        self,
        user_message: str,
        history: Sequence[ConversationTurn] | None = None,
    ) -> str:
        """Return an AI-crafted friendly reply for the provided `user_message`."""
        cleaned = user_message.strip()
        if not cleaned:
            return "Could you share a bit more so I can help?"

        conversation: List[ConversationTurn] = _normalise_history(history or [])
        conversation.append({"role": "user", "content": cleaned})

        if self._api_key_missing or not self._client:
            return self._fallback_reply(cleaned)

        try:
            context_message = self._build_calendar_context()
            logger.debug("AI calendar context:\n%s", context_message or "<empty>")
            messages: List[ConversationTurn] = [{"role": "system", "content": self.system_prompt}]
            if context_message:
                messages.append({"role": "system", "content": context_message})
            messages.extend(conversation)

            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=1,
                max_tokens=127000,
            )
        except RateLimitError:
            logging.warning("Rate limit reached when generating reply; using fallback.")
            return self._fallback_reply(cleaned)
        except APIError as exc:
            logging.error("OpenAI API error: %s", exc)
            return self._fallback_reply(cleaned)
        except OpenAIError as exc:
            logging.exception("Unexpected OpenAI error.")
            return self._fallback_reply(cleaned)
       
        choice = (response.choices or [None])[0]
        if not choice or not (message := choice.message):
            logging.warning("OpenAI response had no choices; using fallback.")
            return self._fallback_reply(cleaned)

        reply = (message.content or "").strip()
        if not reply:
            logging.warning("OpenAI response content empty; using fallback.")
            return self._fallback_reply(cleaned)

        return reply

    @staticmethod
    def _fallback_reply(user_message: str) -> str:
        """Simple templated reply when the AI client is unavailable."""
        return (
            "✨ Thanks for the update! I’m keeping things friendly on my end. "
            f"You mentioned: “{user_message}”. How else can I support you?"
        )

    def plan_calendar_action(
        self,
        user_message: str,
        history: Sequence[ConversationTurn] | None = None,
    ) -> dict | None:
        """Ask the model whether the user is requesting a calendar change."""
        if self._api_key_missing or not self._client:
            return None

        conversation = _normalise_history(history or [])
        conversation.append({"role": "user", "content": user_message.strip()})

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an assistant that extracts calendar instructions. "
                            "Respond ONLY with JSON containing: "
                            '{"action":"none|create|delete|reschedule","title":"","description":"","date":"","start_time":"","end_time":"","event_id":"","category":"","new_title":"","new_description":"","new_date":"","new_start_time":"","new_end_time":"","new_category":""}. '
                            "Use ISO 8601 date (YYYY-MM-DD) and 24-hour HH:MM time in the user's locale. "
                            "If the user does not specify a time, leave start_time empty. "
                            "If deleting, populate event_id if provided; otherwise fill title/date fields as clues. "
                            "If rescheduling, fill both the original fields (title/date/start_time) so the existing meeting can be found, and provide the new_* fields with updated information (leave new_* blank if unchanged). "
                            "Set category to 'work' for work/professional commitments (including Slack-derived meetings) and 'personal' for leisure/free-time plans like hobbies, social events, or appointments. Use new_category when the rescheduled meeting should change category. "
                            "If no calendar action is needed, set action to 'none'."
                        ),
                    },
                    *conversation,
                ],
                temperature=1,
                max_tokens=126000,
            )
        except (RateLimitError, APIError, OpenAIError) as exc:
            logger.debug("Unable to plan calendar action: %s", exc)
            return None

        content = (response.choices[0].message.content or "").strip()
        if not content:
            return None

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.debug("Model returned invalid JSON for calendar action: %s", content)
            return None

        if not isinstance(data, dict):
            return None
        action = data.get("action")
        if action not in {"create", "delete", "reschedule", "none"}:
            return None
        logger.debug("Model calendar action: %s", data)
        return data

    def _build_calendar_context(self) -> str:
        """Fetch upcoming meetings and tasks so the assistant can reference them."""
        try:
            events_resp = requests.get(f"{self.calendar_api}/events", timeout=10)
            events_resp.raise_for_status()
            events_payload = events_resp.json()
        except Exception as exc:
            logging.debug("Unable to fetch calendar events: %s", exc)
            events_payload = []

        try:
            tasks_resp = requests.get(f"{self.calendar_api}/tasks", timeout=10)
            tasks_resp.raise_for_status()
            tasks_payload = tasks_resp.json()
        except Exception as exc:
            logging.debug("Unable to fetch tasks: %s", exc)
            tasks_payload = []

        context_parts: List[str] = []

        if isinstance(events_payload, list):
            upcoming = self._summarise_events(events_payload)
            if upcoming:
                context_parts.append(f"Upcoming meetings:\n{upcoming}")

        if isinstance(tasks_payload, list):
            task_summary = self._summarise_tasks(tasks_payload)
            if task_summary:
                context_parts.append(f"Tasks:\n{task_summary}")

        return "\n\n".join(context_parts)

    @staticmethod
    def _summarise_events(events: List[Mapping[str, str]], limit: int = 5) -> str:
        items: List[str] = []
        today = date.today()

        for event in events:
            try:
                event_date_str = event.get("startDate") or event.get("date_of_meeting")
                event_time = event.get("startTime") or event.get("start_time") or ""
                event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date() if event_date_str else None
            except Exception:
                event_date = None

            if event_date and event_date < today:
                continue

            title = (event.get("title") or "Untitled meeting").strip()
            description = (event.get("description") or "").strip()
            descriptor = description if description else ""

            time_fragment = f"{event_time}" if event_time else ""
            date_fragment = event_date.strftime("%Y-%m-%d") if event_date else "unscheduled date"
            parts = [date_fragment]
            if time_fragment:
                parts.append(time_fragment)
            parts.append(title)
            if descriptor:
                parts.append(f"({descriptor})")

            items.append(" - " + " · ".join(part for part in parts if part))

        return "\n".join(items[:limit])

    @staticmethod
    def _summarise_tasks(tasks: List[Mapping[str, str]], limit: int = 5) -> str:
        items: List[str] = []
        for task in tasks[:limit]:
            title = (task.get("title") or "Task").strip()
            description = (task.get("description") or "").strip()
            due_date = task.get("date_of_meeting") or task.get("dueDate") or ""
            due_time = task.get("start_time") or task.get("dueTime") or ""
            due_fragment = "due soon"
            if due_date:
                due_fragment = f"due {due_date}"
                if due_time:
                    due_fragment += f" at {due_time}"

            descriptor = f"{title} ({due_fragment})"
            if description:
                descriptor += f": {description}"
            items.append(" - " + descriptor)

        return "\n".join(items)


# Shared singleton instance that the rest of the app can reuse.
friendly_ai = FriendlyAIWrapper()


