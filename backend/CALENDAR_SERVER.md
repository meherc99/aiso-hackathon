# Calendar Server - Quick Start Guide

## Overview
The `calendar_server.py` provides a REST API for managing calendar events and serves the React calendar application.

## Features
- ✅ RESTful API for calendar events (CRUD operations)
- ✅ SQLite database storage (shared with chatbot conversations)
- ✅ CORS support for cross-origin requests
- ✅ Static file serving for React app
- ✅ Automatic database schema initialization

## Installation

Install required dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

Start the calendar server:
```bash
python backend/calendar_server.py
```

The server will start on `http://localhost:5000` by default.

### Environment Variables
- `CALENDAR_PORT`: Port number (default: 5000)
- `FLASK_DEBUG`: Enable debug mode (default: false)

Example:
```bash
set CALENDAR_PORT=8080
set FLASK_DEBUG=true
python backend/calendar_server.py
```

## API Endpoints

### Health Check
```
GET /api/health
```
Returns server status.

### List Events
```
GET /api/events
GET /api/events?startDate=2025-01-01&endDate=2025-12-31
```
Get all events, optionally filtered by date range.

### Get Single Event
```
GET /api/events/{event_id}
```
Retrieve a specific event by ID.

### Create Event
```
POST /api/events
Content-Type: application/json

{
  "title": "Team Meeting",
  "description": "Weekly sync",
  "startDate": "2025-11-08",
  "endDate": "2025-11-08",
  "startTime": "14:00",
  "endTime": "15:00",
  "category": "meeting",
  "done": false
}
```

### Update Event
```
PUT /api/events/{event_id}
Content-Type: application/json

{
  "title": "Updated Meeting",
  "done": true
}
```

### Delete Event
```
DELETE /api/events/{event_id}
```

## Testing

Test the API endpoints:
```bash
# Make sure the server is running first
python tests/test_calendar_api.py
```

Or test manually with curl:
```bash
# Health check
curl http://localhost:5000/api/health

# Get all events
curl http://localhost:5000/api/events

# Create event
curl -X POST http://localhost:5000/api/events \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Test Event\",\"startDate\":\"2025-11-08\",\"endDate\":\"2025-11-08\"}"
```

## React App Integration

The server also serves the React calendar app from `/src/dist/`.

1. Build the React app:
```bash
cd src
npm install
npm run build
cd ..
```

2. Start the calendar server:
```bash
python backend/calendar_server.py
```

3. Access the React app at: `http://localhost:5000/`

## Database

Events are stored in `frontend/conversations.db` alongside chat conversations.

Database schema:
```sql
CREATE TABLE events (
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
);
```

## Integration with Chatbot

The calendar server shares the same database as the chatbot, enabling:
- Events created in chat appear in the calendar
- Events created in the calendar can be referenced in chat
- Unified data storage and management

## Next Steps

1. **Update React app** to use API instead of localStorage
2. **Modify chatbot** to create events from conversations
3. **Add Gradio tab** to embed the calendar view
4. **Implement real-time sync** between chat and calendar

## Troubleshooting

**Port already in use:**
```bash
set CALENDAR_PORT=5001
python backend/calendar_server.py
```

**React app not found:**
- Make sure you've built the React app: `cd src && npm run build`
- Check that `src/dist/` directory exists

**CORS errors:**
- CORS is enabled by default for all origins
- Check browser console for specific error messages
