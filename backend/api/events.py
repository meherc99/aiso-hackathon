import datetime
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

def utc_now_iso() -> str:
    """Return an ISO 8601 timestamp in UTC."""
    return datetime.datetime.now(datetime.UTC).isoformat()

class EventStore:

    def __init__(self) -> None:
        self._db_path = Path(__file__).resolve().parent / "events.db"
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._status = f"Using SQLite at {self._db_path}"
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize the database schema."""
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    start_time TEXT,
                    end_time TEXT,
                    category TEXT,
                    done BOOLEAN NOT NULL DEFAULT 0
                )
            """)
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    color TEXT NOT NULL
                )
            """)
        
    @property
    def status(self) -> str:
        return self._status
    
    def add_event(self, title: str, description: str, start_date: str, end_date: Optional[str],
                  start_time: Optional[str] = None, end_time: Optional[str] = None,
                  category: Optional[str] = None, done: bool = False) -> str:
        """Add a new event to the store."""
        event_id = str(uuid.uuid4())
        created_at = utc_now_iso()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO events (id, title, description, created_at, start_date, end_date, start_time, end_time, category, done)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, title, description, created_at, start_date, end_date, start_time, end_time, category, done)
            )
        return event_id
    
    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an event by its ID."""
        cursor = self._conn.execute(
            "SELECT * FROM events WHERE id = ?",
            (event_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def list_events(self) -> List[Dict[str, Any]]:
        """List all events."""
        cursor = self._conn.execute("SELECT * FROM events")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_today_events(self) -> List[Dict[str, Any]]:
        """List events occurring today."""
        today = datetime.datetime.now(datetime.UTC).date().isoformat()
        cursor = self._conn.execute(
            "SELECT * FROM events WHERE start_date <= ? AND end_date >= ?",
            (today, today)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def update_event(self, event_id: str, **updates: Any) -> bool:
        """Update an event with the given fields."""
        fields = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [event_id]
        with self._conn:
            cursor = self._conn.execute(
                f"UPDATE events SET {fields} WHERE id = ?",
                values
            )
        return cursor.rowcount > 0
    
    def delete_event(self, event_id: str) -> bool:
        """Delete an event by its ID."""
        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM events WHERE id = ?",
                (event_id,)
            )
        return cursor.rowcount > 0
    
    def add_category(self, name: str, color: str) -> int:
        """Add a new category."""
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO categories (name, color) VALUES (?, ?)",
                (name, color)
            )
        return cursor.lastrowid
    
    def list_categories(self) -> List[Dict[str, Any]]:
        """List all categories."""
        cursor = self._conn.execute("SELECT * FROM categories")
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_category(self, category_id: int) -> bool:
        """Delete a category by its ID."""
        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM categories WHERE id = ?",
                (category_id,)
            )
        return cursor.rowcount > 0
    
event_store = EventStore()
__all__ = ["event_store", "EventStore"]
