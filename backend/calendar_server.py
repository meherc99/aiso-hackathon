"""
Calendar Server - REST API for calendar events and static file serving.

This server provides:
- RESTful API endpoints for CRUD operations on calendar events
- Static file serving for the React calendar app
- CORS support for integration with Gradio frontend
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS


class CalendarStore:
    """Manage calendar events in SQLite database."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = Path(__file__).resolve().parent.parent / "frontend" / "conversations.db"
        self._db_path = db_path
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize events table in the database."""
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    startDate TEXT NOT NULL,
                    endDate TEXT NOT NULL,
                    startTime TEXT,
                    endTime TEXT,
                    category TEXT,
                    done INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new calendar event."""
        event_id = event_data.get("id") or str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        event = {
            "id": event_id,
            "title": event_data.get("title", "Untitled Event"),
            "description": event_data.get("description", ""),
            "startDate": event_data.get("startDate", ""),
            "endDate": event_data.get("endDate", ""),
            "startTime": event_data.get("startTime", ""),
            "endTime": event_data.get("endTime", ""),
            "category": event_data.get("category", ""),
            "done": 1 if event_data.get("done") else 0,
            "created_at": now,
            "updated_at": now,
        }

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO events (
                    id, title, description, startDate, endDate,
                    startTime, endTime, category, done, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"],
                    event["title"],
                    event["description"],
                    event["startDate"],
                    event["endDate"],
                    event["startTime"],
                    event["endTime"],
                    event["category"],
                    event["done"],
                    event["created_at"],
                    event["updated_at"],
                ),
            )
        
        # Convert done back to boolean for response
        event["done"] = bool(event["done"])
        return event

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single event by ID."""
        row = self._conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        
        if not row:
            return None
        
        return self._row_to_dict(row)

    def list_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all events, optionally filtered by date range."""
        if start_date and end_date:
            rows = self._conn.execute(
                """
                SELECT * FROM events
                WHERE startDate >= ? AND endDate <= ?
                ORDER BY startDate, startTime
                """,
                (start_date, end_date),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM events ORDER BY startDate, startTime"
            ).fetchall()
        
        return [self._row_to_dict(row) for row in rows]

    def update_event(self, event_id: str, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing event."""
        existing = self.get_event(event_id)
        if not existing:
            return None

        now = datetime.now().isoformat()
        
        # Update only provided fields
        updated = {
            "title": event_data.get("title", existing["title"]),
            "description": event_data.get("description", existing["description"]),
            "startDate": event_data.get("startDate", existing["startDate"]),
            "endDate": event_data.get("endDate", existing["endDate"]),
            "startTime": event_data.get("startTime", existing["startTime"]),
            "endTime": event_data.get("endTime", existing["endTime"]),
            "category": event_data.get("category", existing["category"]),
            "done": 1 if event_data.get("done", existing["done"]) else 0,
            "updated_at": now,
        }

        with self._conn:
            self._conn.execute(
                """
                UPDATE events SET
                    title = ?, description = ?, startDate = ?, endDate = ?,
                    startTime = ?, endTime = ?, category = ?, done = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    updated["title"],
                    updated["description"],
                    updated["startDate"],
                    updated["endDate"],
                    updated["startTime"],
                    updated["endTime"],
                    updated["category"],
                    updated["done"],
                    updated["updated_at"],
                    event_id,
                ),
            )
        
        updated["id"] = event_id
        updated["done"] = bool(updated["done"])
        updated["created_at"] = existing["created_at"]
        return updated

    def delete_event(self, event_id: str) -> bool:
        """Delete an event by ID."""
        with self._conn:
            cursor = self._conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
            return cursor.rowcount > 0

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a dictionary."""
        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "startDate": row["startDate"],
            "endDate": row["endDate"],
            "startTime": row["startTime"],
            "endTime": row["endTime"],
            "category": row["category"],
            "done": bool(row["done"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize calendar store
calendar_store = CalendarStore()

# Determine static file directory for React app
STATIC_DIR = Path(__file__).resolve().parent.parent / "src" / "dist"


# ============================================================================
# API Routes
# ============================================================================

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "calendar-server"})


@app.route("/api/events", methods=["GET"])
def get_events():
    """
    Get all events, optionally filtered by date range.
    Query params: startDate, endDate (ISO format)
    """
    start_date = request.args.get("startDate")
    end_date = request.args.get("endDate")
    
    events = calendar_store.list_events(start_date, end_date)
    return jsonify(events)


@app.route("/api/events/<event_id>", methods=["GET"])
def get_event(event_id: str):
    """Get a single event by ID."""
    event = calendar_store.get_event(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(event)


@app.route("/api/events", methods=["POST"])
def create_event():
    """Create a new event."""
    if not request.json:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    try:
        event = calendar_store.create_event(request.json)
        return jsonify(event), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/events/<event_id>", methods=["PUT", "PATCH"])
def update_event(event_id: str):
    """Update an existing event."""
    if not request.json:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    try:
        event = calendar_store.update_event(event_id, request.json)
        if not event:
            return jsonify({"error": "Event not found"}), 404
        return jsonify(event)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/events/<event_id>", methods=["DELETE"])
def delete_event(event_id: str):
    """Delete an event."""
    success = calendar_store.delete_event(event_id)
    if not success:
        return jsonify({"error": "Event not found"}), 404
    return jsonify({"success": True, "message": "Event deleted"})


# ============================================================================
# Static File Serving for React App
# ============================================================================

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react_app(path: str):
    """Serve the React calendar app."""
    if not STATIC_DIR.exists():
        return jsonify({
            "error": "React app not built",
            "message": "Please run 'npm run build' in the src directory"
        }), 404
    
    # Serve specific file if it exists
    if path and (STATIC_DIR / path).exists():
        return send_from_directory(STATIC_DIR, path)
    
    # Otherwise serve index.html (for SPA routing)
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return send_from_directory(STATIC_DIR, "index.html")
    
    return jsonify({"error": "index.html not found"}), 404


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Start the calendar server."""
    port = int(os.environ.get("CALENDAR_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    
    print(f"🚀 Calendar Server starting on http://localhost:{port}")
    print(f"📊 API available at http://localhost:{port}/api/events")
    
    if STATIC_DIR.exists():
        print(f"📱 React app available at http://localhost:{port}/")
    else:
        print(f"⚠️  React app not built. Run 'npm run build' in src/ directory")
    
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
