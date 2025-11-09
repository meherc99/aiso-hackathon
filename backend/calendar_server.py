"""
Calendar Server - REST API for calendar events and static file serving.

This server provides:
- RESTful API endpoints for CRUD operations on calendar events
- Static file serving for the React calendar app
- CORS support for integration with Gradio frontend
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from database import get_default_db


class CalendarStore:
    """Manage calendar events using the JSON database."""

    def __init__(self) -> None:
        self._db = get_default_db()

    @staticmethod
    def _meeting_to_event(meeting: Dict[str, Any]) -> Dict[str, Any]:
        if not meeting:
            return {}

        start_date = meeting.get("date_of_meeting") or ""
        end_date = meeting.get("end_date") or start_date

        return {
            "id": meeting.get("id"),
            "title": meeting.get("title", "Untitled Event"),
            "description": meeting.get("description") or "",
            "startDate": start_date,
            "endDate": end_date,
            "startTime": meeting.get("start_time") or "",
            "endTime": meeting.get("end_time") or "",
            "category": meeting.get("category") or "",
            "done": bool(meeting.get("meeting_completed", False)),
            "created_at": meeting.get("created_at"),
        }

    @staticmethod
    def _event_to_meeting(
        event: Dict[str, Any],
        existing: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        existing = existing or {}

        meeting_id = event.get("id") or existing.get("id") or str(uuid.uuid4())
        start_date = (
            event.get("startDate")
            or event.get("date_of_meeting")
            or existing.get("date_of_meeting")
        )

        if not start_date:
            raise ValueError("startDate is required")

        end_date = event.get("endDate") or event.get("end_date") or start_date
        created_at = (
            existing.get("created_at")
            or event.get("created_at")
            or datetime.utcnow().isoformat()
        )

        done_value = event.get("done")
        if done_value is None:
            done_value = existing.get("meeting_completed", False)

        meeting_completed = bool(done_value)

        return {
            "id": meeting_id,
            "title": event.get("title", existing.get("title", "Untitled Event")),
            "description": event.get("description", existing.get("description", "")),
            "date_of_meeting": start_date,
            "end_date": end_date,
            "start_time": event.get("startTime", existing.get("start_time", "")),
            "end_time": event.get("endTime", existing.get("end_time", "")),
            "category": event.get("category", existing.get("category", "")),
            "created_at": created_at,
            "meeting_completed": meeting_completed,
        }

    def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new calendar event."""
        meeting = self._event_to_meeting(event_data)
        self._db.add_meeting(meeting)
        stored = self._db.get_meeting_by_id(meeting["id"])
        return self._meeting_to_event(stored)

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single event by ID."""
        meeting = self._db.get_meeting_by_id(event_id)
        if not meeting:
            return None
        return self._meeting_to_event(meeting)

    def list_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all events, optionally filtered by date range."""
        meetings = self._db.get_all_meetings()
        meetings.sort(key=lambda m: (m.get("date_of_meeting") or "", m.get("start_time") or ""))

        if start_date and end_date:
            def _within_range(meeting: Dict[str, Any]) -> bool:
                date_value = meeting.get("date_of_meeting")
                return bool(date_value) and start_date <= date_value <= end_date

            meetings = [meeting for meeting in meetings if _within_range(meeting)]

        return [self._meeting_to_event(meeting) for meeting in meetings]

    def update_event(self, event_id: str, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing event."""
        existing_meeting = self._db.get_meeting_by_id(event_id)
        if not existing_meeting:
            return None

        current_event = self._meeting_to_event(existing_meeting)
        current_event.update(event_data)

        meeting_payload = self._event_to_meeting(current_event, existing=existing_meeting)
        updated = self._db.update_meeting(event_id, meeting_payload)
        if not updated:
            return None
        return self._meeting_to_event(updated)

    def delete_event(self, event_id: str) -> bool:
        """Delete an event by ID."""
        if self._db.delete_meeting(event_id):
            return True
        return self._db.delete_task(event_id)

    def list_tasks(self) -> List[Dict[str, Any]]:
        """Return raw task records from the JSON database."""
        return self._db.get_all_tasks()


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


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    """Return tasks captured by the agent."""
    tasks = calendar_store.list_tasks()
    return jsonify(tasks)


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
    port = int(os.environ.get("CALENDAR_PORT", 5050))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    
    print(f"Calendar Server starting on http://localhost:{port}")
    print(f"API available at http://localhost:{port}/api/events")
    
    if STATIC_DIR.exists():
        print(f"React app available at http://localhost:{port}/")
    else:
        print(f"WARNING: React app not built. Run 'npm run build' in src/ directory")
    
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
