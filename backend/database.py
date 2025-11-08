"""
database.py

Simple JSON-based file database for storing meetings and tasks.
Uses a single JSON file with two collections: "meetings" and "tasks".
Each item is stored with its full JSON object including id, category, etc.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class Database:
    """Simple JSON file-based database for meetings and tasks."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database with a file path.
        
        Args:
            db_path: Path to JSON database file. Defaults to backend/data/db.json
        """
        if db_path is None:
            # Default to backend/data/db.json
            backend_dir = Path(__file__).parent
            data_dir = backend_dir / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "db.json")
        
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self) -> None:
        """Create empty database file if it doesn't exist."""
        if not os.path.exists(self.db_path):
            initial_data = {
                "meetings": [],
                "tasks": [],
                "metadata": {
                    "created_at": datetime.utcnow().isoformat(),
                    "last_modified": datetime.utcnow().isoformat()
                }
            }
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
    
    def _read_db(self) -> Dict[str, Any]:
        """Read and return the entire database."""
        with open(self.db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _write_db(self, data: Dict[str, Any]) -> None:
        """Write data to database file."""
        data["metadata"]["last_modified"] = datetime.utcnow().isoformat()
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add_meeting(self, meeting: Dict[str, Any]) -> None:
        """Add a meeting to the database.
        
        Args:
            meeting: Meeting object with at least 'id' and 'category' fields
        """
        db = self._read_db()
        # Check if meeting with this id already exists
        existing_ids = {m.get('id') for m in db['meetings']}
        if meeting.get('id') not in existing_ids:
            db['meetings'].append(meeting)
            self._write_db(db)
    
    def add_task(self, task: Dict[str, Any]) -> None:
        """Add a task to the database.
        
        Args:
            task: Task object with at least 'id' and 'category' fields
        """
        db = self._read_db()
        # Check if task with this id already exists
        existing_ids = {t.get('id') for t in db['tasks']}
        if task.get('id') not in existing_ids:
            db['tasks'].append(task)
            self._write_db(db)
    
    def add_meetings(self, meetings: List[Dict[str, Any]]) -> None:
        """Add multiple meetings to the database.
        
        Args:
            meetings: List of meeting objects
        """
        for meeting in meetings:
            self.add_meeting(meeting)
    
    def add_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Add multiple tasks to the database.
        
        Args:
            tasks: List of task objects
        """
        for task in tasks:
            self.add_task(task)
    
    def get_all_meetings(self) -> List[Dict[str, Any]]:
        """Get all meetings from the database."""
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
    
    def update_meeting(self, meeting_id: str, updates: Dict[str, Any]) -> bool:
        """Update a meeting by ID.
        
        Args:
            meeting_id: ID of the meeting to update
            updates: Dictionary of fields to update
            
        Returns:
            True if meeting was found and updated, False otherwise
        """
        db = self._read_db()
        for i, meeting in enumerate(db['meetings']):
            if meeting.get('id') == meeting_id:
                db['meetings'][i].update(updates)
                self._write_db(db)
                return True
        return False
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """Update a task by ID.
        
        Args:
            task_id: ID of the task to update
            updates: Dictionary of fields to update
            
        Returns:
            True if task was found and updated, False otherwise
        """
        db = self._read_db()
        for i, task in enumerate(db['tasks']):
            if task.get('id') == task_id:
                db['tasks'][i].update(updates)
                self._write_db(db)
                return True
        return False
    
    def delete_meeting(self, meeting_id: str) -> bool:
        """Delete a meeting by ID.
        
        Args:
            meeting_id: ID of the meeting to delete
            
        Returns:
            True if meeting was found and deleted, False otherwise
        """
        db = self._read_db()
        initial_len = len(db['meetings'])
        db['meetings'] = [m for m in db['meetings'] if m.get('id') != meeting_id]
        if len(db['meetings']) < initial_len:
            self._write_db(db)
            return True
        return False
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID.
        
        Args:
            task_id: ID of the task to delete
            
        Returns:
            True if task was found and deleted, False otherwise
        """
        db = self._read_db()
        initial_len = len(db['tasks'])
        db['tasks'] = [t for t in db['tasks'] if t.get('id') != task_id]
        if len(db['tasks']) < initial_len:
            self._write_db(db)
            return True
        return False
    
    def clear_all(self) -> None:
        """Clear all meetings and tasks from the database."""
        db = self._read_db()
        db['meetings'] = []
        db['tasks'] = []
        self._write_db(db)


# Convenience functions for quick access
_default_db = None

def get_default_db() -> Database:
    """Get or create the default database instance."""
    global _default_db
    if _default_db is None:
        _default_db = Database()
    return _default_db


if __name__ == "__main__":
    # Demo usage
    db = Database()
    
    # Example meeting
    sample_meeting = {
        "id": "test-meeting-1",
        "category": "work",
        "date_of_meeting": "2025-11-15",
        "start_time": "14:00",
        "end_time": "15:00",
        "title": "Team Sync",
        "description": "Weekly team synchronization meeting",
        "created_at": datetime.utcnow().isoformat(),
        "done": False
    }
    
    # Example task
    sample_task = {
        "id": "test-task-1",
        "category": "tasks",
        "date_of_meeting": "2025-11-10",
        "start_time": "23:59",
        "end_time": "23:59",
        "title": "Code Review",
        "description": "Review PR #123",
        "created_at": datetime.utcnow().isoformat(),
        "done": False
    }
    
    # Add items
    db.add_meeting(sample_meeting)
    db.add_task(sample_task)
    
    # Retrieve and print
    print("All meetings:")
    print(json.dumps(db.get_all_meetings(), indent=2))
    
    print("\nAll tasks:")
    print(json.dumps(db.get_all_tasks(), indent=2))