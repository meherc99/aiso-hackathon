# aiso-hackathon

AI-powered calendar assistant with integrated chatbot and calendar management.

## Components

### Backend
- **`calendar_server.py`** — REST API server for calendar events with SQLite storage
- **`parse_messages.py`** — Slack message parser and OpenAI integration
- **`openai_wrapper.py`** — OpenAI Chat API wrapper
- **`slack.py`** — Slack integration utilities

### Frontend
- **`chatbot.py`** — Gradio-based chat interface with conversation management
- **`chat_logic.py`** — Chat message processing and AI response handling
- **`storage.py`** — SQLite database management for conversations and events
- **`ai_wrapper.py`** — AI integration wrapper

### Calendar App (React)
- **`src/`** — Full-featured calendar application built with React + Vite
- Calendar view with event management (CRUD operations)
- Integration with backend API for persistent storage

Setup
1. Create a Python virtual environment and activate it.
	 ```powershell
	 python -m venv .venv
	 .\.venv\Scripts\Activate.ps1
	 ```
2. Install requirements:
	 ```powershell
	 pip install -r requirements.txt
	 ```
3. Copy `.env.example` to `.env` and set your key (or set the env var directly):
	 - Copy file:
		 ```powershell
		 copy .env.example .env
		 ```
	 - Edit `.env` and replace `OPENAI_API_KEY=sk-REPLACE_ME` with your real key.

## Quick Start

### Option 1: Run Both Servers (Recommended)
```powershell
.\start_servers.bat
```
Or on PowerShell:
```powershell
.\start_servers.ps1
```
This starts:
- Calendar API server on `http://localhost:5000`
- Chatbot UI with embedded calendar on `http://localhost:7860`

**Features:**
- **Chat Assistant Tab**: AI-powered chat with calendar sidebar showing today's events
- **Full Calendar Tab**: Complete calendar view with event management (embedded React app)

### Option 2: Run Servers Individually

**Start Calendar Server:**
```powershell
python backend\calendar_server.py
```

**Start Chatbot:**
```powershell
python frontend\chatbot.py
```

### Option 3: Build and Run React Calendar App

1. Build the React app:
```powershell
cd src
npm install
npm run build
cd ..
```

2. The built app will be served by the calendar server at `http://localhost:5000/`

## API Usage

### Calendar API Endpoints

```powershell
# Get all events
curl http://localhost:5000/api/events

# Create an event
curl -X POST http://localhost:5000/api/events -H "Content-Type: application/json" -d "{\"title\":\"Meeting\",\"startDate\":\"2025-11-08\",\"endDate\":\"2025-11-08\",\"startTime\":\"14:00\",\"endTime\":\"15:00\"}"

# Update an event
curl -X PUT http://localhost:5000/api/events/{event_id} -H "Content-Type: application/json" -d "{\"title\":\"Updated Meeting\"}"

# Delete an event
curl -X DELETE http://localhost:5000/api/events/{event_id}
```

For detailed API documentation, see [`backend/CALENDAR_SERVER.md`](backend/CALENDAR_SERVER.md)

### Legacy Usage (Slack Message Parsing)
- Dry run (no network, prints payload and simulated assistant reply):
	```powershell
	python .\parse_messages.py --send-to-openai --dry-run --show-payload
	```
- Real run (make sure you set `OPENAI_API_KEY` in `.env` or environment):
	```powershell
	python .\parse_messages.py --send-to-openai
	```

Security
- Never commit a real `.env` file to source control. Use the `.env.example` as a template.
