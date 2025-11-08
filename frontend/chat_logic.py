from typing import Any, Dict, List, Optional, Sequence

from ai_wrapper import friendly_ai

Message = Dict[str, str]


def build_bot_reply(user_message: str, history: Sequence[Message] | None = None) -> str:
    """Return a conversational, friendly AI-powered reply."""
    return friendly_ai.generate_reply(user_message, history)


def messages_to_history(messages: List[Dict[str, Any]]) -> List[Message]:
    """Convert stored message dictionaries into Chatbot-compatible history."""
    history: List[Message] = []
    for entry in messages:
        role = entry.get("role")
        content = entry.get("content", "")
        if role and content:
            history.append({"role": role, "content": content})
    return history

