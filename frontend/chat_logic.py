import datetime
from typing import Any, Dict, List, Optional

Message = Dict[str, str]


def build_bot_reply(user_message: str) -> str:
    """Return a simple echoed response including the current time."""
    timestamp = datetime.datetime.now().strftime("%H:%M")
    return (
        "✨ Thanks for sharing!\n"
        f"- Current time: {timestamp}\n"
        f"- You said: {user_message}"
    )


def messages_to_history(messages: List[Dict[str, Any]]) -> List[Message]:
    """Convert stored message dictionaries into Chatbot-compatible history."""
    history: List[Message] = []
    for entry in messages:
        role = entry.get("role")
        content = entry.get("content", "")
        if role and content:
            history.append({"role": role, "content": content})
    return history

