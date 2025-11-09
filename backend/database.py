"""
database.py

Provides a simple JSON file-based database for meetings and tasks.
All timestamps are stored in UTC but can be displayed in Amsterdam time.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import List, Dict, Any, Optional

# Amsterdam timezone
AMSTERDAM_TZ = ZoneInfo("Europe/Amsterdam")


class JSONDatabase:
    """Simple JSON file-based database for meetings and tasks."""

    def __init__(self, db_path: str = "data/db.json"):
        """
        Initialize the database.
        
        Args:
            db_path: Path to the JSON database file
        """
        self.db_path = Path(db_path)
        self._ensure_db_exists()

    def _ensure_db_exists(self) -> None:
        """Create the database file and directory if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            self._write_db({
                "meetings": [],
                "tasks": [],
                "channel_timestamps": {}
            })

    def _read_db(self) -> Dict[str, Any]:
        """Read the entire database."""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"meetings": [], "tasks": [], "channel_timestamps": {}}

    def _write_db(self, data: Dict[str, Any]) -> None:
        """Write the entire database."""
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # Channel timestamp management
    def get_channel_last_processed(self, channel_id: str) -> Optional[str]:
        """Get the last processed timestamp for a channel."""
        data = self._read_db()
        return data.get("channel_timestamps", {}).get(channel_id)

    def update_channel_timestamp(self, channel_id: str, timestamp: Optional[str] = None) -> None:
        """
        Update the last processed timestamp for a channel.
        
        Args:
            channel_id: The Slack channel ID
            timestamp: ISO format timestamp. If None, uses current time in Amsterdam timezone.
        """
        data = self._read_db()
        if "channel_timestamps" not in data:
            data["channel_timestamps"] = {}
        
        if timestamp is None:
            # Use current Amsterdam time
            now = datetime.now(AMSTERDAM_TZ)
            timestamp = now.isoformat()
        
        data["channel_timestamps"][channel_id] = timestamp
        self._write_db(data)

    def initialize_channel_timestamp_yesterday(self, channel_id: str) -> None:
        """Initialize a channel's timestamp to yesterday (Amsterdam time)."""
        yesterday = datetime.now(AMSTERDAM_TZ) - timedelta(days=1)
        self.update_channel_timestamp(channel_id, yesterday.isoformat())

    # Meeting operations
    def add_meetings(self, meetings: List[Dict[str, Any]]) -> None:
        """Add multiple meetings to the database."""
        data = self._read_db()
        data["meetings"].extend(meetings)
        self._write_db(data)

    def get_all_meetings(self) -> List[Dict[str, Any]]:
        """Get all meetings from the database."""
<<<<<<< Updated upstream
        db = self._read_db()
        return db.get('meetings', [])
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks from the database."""
        db = self._read_db()
        return db.get('tasks', [])
    
    def get_meeting_by_id(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific meeting by ID."""
        meetings = self.get_all_meetings()
        for meeting in meetings:
            if meeting.get('id') == meeting_id:
                return meeting
        return None
    
    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID."""
        tasks = self.get_all_tasks()
        for task in tasks:
            if task.get('id') == task_id:
                return task
        return None
    
    def update_meeting(self, meeting_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a meeting by ID.
=======
        data = self._read_db()
        return data.get("meetings", [])

    def update_meeting(self, meeting_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a meeting by ID.
>>>>>>> Stashed changes
        
        Args:
            meeting_id: The meeting ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated meeting dict if found, otherwise None
        """
<<<<<<< Updated upstream
        db = self._read_db()
        for i, meeting in enumerate(db['meetings']):
            if meeting.get('id') == meeting_id:
                db['meetings'][i].update(updates)
                self._write_db(db)
                return db['meetings'][i]
        return None

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a task by ID.
=======
        data = self._read_db()
        meetings = data.get("meetings", [])
        
        for meeting in meetings:
            if meeting.get("id") == meeting_id:
                meeting.update(updates)
                self._write_db(data)
                return True
        
        return False

    # Task operations
    def add_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Add multiple tasks to the database."""
        data = self._read_db()
        data["tasks"].extend(tasks)
        self._write_db(data)

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks from the database."""
        data = self._read_db()
        return data.get("tasks", [])

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a task by ID.
>>>>>>> Stashed changes
        
        Args:
            task_id: The task ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated task dict if found, otherwise None
        """
<<<<<<< Updated upstream
        db = self._read_db()
        for i, task in enumerate(db['tasks']):
            if task.get('id') == task_id:
                db['tasks'][i].update(updates)
                self._write_db(db)
                return db['tasks'][i]
        return None
    
    def delete_meeting(self, meeting_id: str) -> bool:
        """Delete a meeting by ID.
=======
        data = self._read_db()
        tasks = data.get("tasks", [])
        
        for task in tasks:
            if task.get("id") == task_id:
                task.update(updates)
                self._write_db(data)
                return True
>>>>>>> Stashed changes
        
        return False

    def clear_all(self) -> None:
        """Clear all data from the database."""
        self._write_db({
            "meetings": [],
            "tasks": [],
            "channel_timestamps": {}
        })


# Default database instance
_default_db = None


def get_default_db() -> JSONDatabase:
    """Get or create the default database instance."""
    global _default_db
    if _default_db is None:
        _default_db = JSONDatabase()
    return _default_db


if __name__ == "__main__":
    # Test the database
    db = get_default_db()
    
    print("Database initialized")
    print(f"Meetings: {len(db.get_all_meetings())}")
    print(f"Tasks: {len(db.get_all_tasks())}")
    
    # Show current Amsterdam time
    now_amsterdam = datetime.now(AMSTERDAM_TZ)
    print(f"\nCurrent Amsterdam time: {now_amsterdam.strftime('%Y-%m-%d %H:%M:%S %Z')}")