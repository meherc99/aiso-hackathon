import datetime
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    """Return an ISO 8601 timestamp in UTC."""
    return datetime.datetime.now(datetime.UTC).isoformat()


class ConversationStore:
    """Persist conversations using a lightweight SQLite database."""

    def __init__(self) -> None:
        self._db_path = Path(__file__).resolve().parent / "conversations.db"
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._status = f"Using SQLite at {self._db_path}"
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
                """
            )

    @property
    def status(self) -> str:
        return self._status

    def create_conversation(self) -> str:
        conversation_id = str(uuid.uuid4())
        now = utc_now_iso()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO conversations (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, None, now, now),
            )
        return conversation_id

    def append_message(self, conversation_id: str, role: str, content: str) -> None:
        timestamp = utc_now_iso()
        with self._conn:
            # Ensure the conversation exists before inserting a message.
            self._conn.execute(
                """
                INSERT OR IGNORE INTO conversations (id, title, created_at, updated_at)
                VALUES (?, NULL, ?, ?)
                """,
                (conversation_id, timestamp, timestamp),
            )
            self._conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, role, content, timestamp),
            )
            self._conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (timestamp, conversation_id),
            )

    def update_title_if_missing(self, conversation_id: str, candidate: str) -> None:
        title = candidate.strip().splitlines()[0][:60]
        if not title:
            return
        with self._conn:
            row = self._conn.execute(
                "SELECT title FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if row and row["title"]:
                return
            timestamp = utc_now_iso()
            self._conn.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (title, timestamp, conversation_id),
            )

    def list_conversations(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM conversations
            ORDER BY datetime(updated_at) DESC, datetime(created_at) DESC
            """
        ).fetchall()
        return [
            {
                "_id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def fetch_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT role, content, timestamp
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
        ).fetchall()
        return [
            {
                "role": row["role"],
                "content": row["content"],
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]

    def reset_conversation(self, conversation_id: str) -> None:
        timestamp = utc_now_iso()
        with self._conn:
            self._conn.execute(
                "DELETE FROM messages WHERE conversation_id = ?", (conversation_id,)
            )
            self._conn.execute(
                """
                UPDATE conversations
                SET title = NULL, updated_at = ?
                WHERE id = ?
                """,
                (timestamp, conversation_id),
            )

