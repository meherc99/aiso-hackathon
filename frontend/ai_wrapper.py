"""Utility helpers for generating friendly AI replies to user messages."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Iterable, List, Mapping, Sequence

import openai
from dotenv import load_dotenv
from openai import APIError, OpenAIError, RateLimitError

ConversationTurn = Mapping[str, str]


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
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *conversation,
                ],
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


# Shared singleton instance that the rest of the app can reuse.
friendly_ai = FriendlyAIWrapper()


