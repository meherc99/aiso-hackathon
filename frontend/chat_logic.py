from typing import Any, Dict, List, Optional, Sequence, Tuple

from ai_wrapper import friendly_ai

Message = Dict[str, str]


def build_bot_reply(
    user_message: str, history: Sequence[Message] | None = None
) -> Tuple[str, Optional[dict]]:
    """Return a conversational reply and an optional calendar action."""
    reply = friendly_ai.generate_reply(user_message, history)
    action = friendly_ai.plan_calendar_action(user_message, history)
    return reply, action


def messages_to_history(messages: List[Dict[str, Any]]) -> List[Message]:
    """Convert stored message dictionaries into Chatbot-compatible history."""
    history: List[Message] = []
    for entry in messages:
        role = entry.get("role")
        content = entry.get("content", "")
        if role and content:
            history.append({"role": role, "content": content})
    return history

