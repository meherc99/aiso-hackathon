import datetime
import uuid
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    """Return an ISO 8601 timestamp in UTC."""
    return datetime.datetime.now(datetime.UTC).isoformat()


class ConversationStore:
    """Persist conversations in memory for the current session."""

    def __init__(self) -> None:
        self._status = "Using in-memory storage."
        self._store: Dict[str, Dict[str, Any]] = {}

    @property
    def status(self) -> str:
        return self._status

    def create_conversation(self) -> str:
        conversation_id = str(uuid.uuid4())
        self._store[conversation_id] = {
            "_id": conversation_id,
            "title": None,
            "messages": [],
            "created_at": utc_now_iso(),
        }
        return conversation_id

    def append_message(self, conversation_id: str, role: str, content: str) -> None:
        entry = {"role": role, "content": content, "timestamp": utc_now_iso()}
        conversation = self._store.setdefault(
            conversation_id,
            {"_id": conversation_id, "title": None, "messages": [], "created_at": utc_now_iso()},
        )
        conversation["messages"].append(entry)

    def update_title_if_missing(self, conversation_id: str, candidate: str) -> None:
        title = candidate.strip().splitlines()[0][:60]
        if not title:
            return
        conversation = self._store.get(conversation_id)
        if conversation and not conversation.get("title"):
            conversation["title"] = title

    def list_conversations(self) -> List[Dict[str, Any]]:
        return sorted(
            self._store.values(),
            key=lambda doc: doc.get("created_at", utc_now_iso()),
            reverse=True,
        )

    def fetch_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        conversation = self._store.get(conversation_id)
        if not conversation:
            return []
        return conversation.get("messages", [])

    def reset_conversation(self, conversation_id: str) -> None:
        conversation = self._store.get(conversation_id)
        if conversation:
            conversation["messages"] = []
            conversation["title"] = None

