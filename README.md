# Slacky – AI Calendar Assistant

This repository bundles everything you need to run an AI-assisted calendar workflow:

* a Slack-aware agent that turns conversations into meetings/tasks and writes them to the calendar database,
* a Gradio chatbot UI that lets you talk to the assistant directly,
* a REST calendar API + React calendar front-end.

The instructions below take you from a clean checkout to a fully working stack on localhost.

---

## 1. Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.10+ | All backend services (agent, scheduler, calendar API, chatbot) are Python. |
| Node.js 18+ + npm | Only needed if you want to rebuild the React calendar UI. |
| Slack Bot Token (optional) | Required if you want the agent to read Slack channels and send reminders. |
| OpenAI-compatible API key | Used for natural-language meeting extraction and chatbot replies. |

---

## 2. Environment Setup

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

Copy `.env.example` to `.env` (or `.env.local` if you prefer) and fill in the keys you have:

```bash
cp .env.example .env
```

Important variables:

```
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...        # optional, only required for Slack ingestion/notifications
SLACK_BOT_USER_ID=U12345...     # lets the reminder skip pinging itself
```

> ⚠️ Never commit your real `.env`. Keep `.env.example` as the template.

---

## 3. Starting Everything the Easy Way

For development you can bring up *all services* (calendar API, chatbot UI, agent scheduler, reminder runner, React calendar) with one command:

```bash
python start_all_services.py
```

The helper script:

* builds/serves the React calendar (via Vite dev server),
* runs the calendar REST API on **http://localhost:5050**,
* launches the Gradio chatbot on **http://localhost:7860**,
* kicks off the master scheduler (Slack agent + meeting reminders).

You’ll see tabbed logs for each component in the terminal.

---

## 4. Running Services Manually (à la carte)

### 4.1 Calendar REST API
Stores meetings/tasks in `backend/data/db.json` and serves the React build.

```bash
python backend/calendar_server.py
```

### 4.2 React Calendar (Dev mode)

```bash
cd src
npm install
npm run dev          # serves http://localhost:5173
```

Build for production (served by the calendar server):

```bash
npm run build
```

### 4.3 Gradio Chatbot UI

```bash
python frontend/chatbot.py
```

### 4.4 Slack Agent + Reminder Scheduler

Runs the Slack ingestion agent first, then reminder notifications (default every 5 minutes). Needs `OPENAI_API_KEY` and, if you want Slack, the bot token + channel memberships.

```bash
python backend/master_scheduler.py
```

---

## 5. How the System Works

1. **Slack Agent (`agent.py`)**  
   Fetches messages from the channels where the bot is invited. It calls `check_meetings.py` to extract meeting requests and `check_models.py`/`check_upcoming_and_notify.py` to send reminders.

2. **Calendar & Tasks DB (`backend/database.py`)**  
   Persisted SQLite/JSON store used by both the calendar API and chatbot.

3. **Reminder Sweep (`check_upcoming_and_notify.py`)**  
   Every time the scheduler runs, it checks the DB for meetings starting within the next 15 minutes (per channel) and posts a Slack reminder pinging channel members.

4. **Chatbot (`frontend/chatbot.py`)**  
   Gradio interface that lets users create/reschedule/cancel meetings and view “today” plus task lists.

---

## 6. Development Tips

* **Resetting data:** delete `backend/data/db.json` and `frontend/conversations.db` while services are stopped.
* **Running tests quickly:** the master scheduler cadence can be changed in `backend/master_scheduler.py` (default every 5 minutes).
* **React live reload:** run `npm run dev` in `src/` and keep the calendar server running separately.
* **Slack reminders:** if you only want chatbot + calendar, you can skip the Slack token. The agent scheduler will still run but simply find no channels.

---

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| “Request failed: 401” from OpenAI | Double-check `OPENAI_API_KEY` and restart services. |
| No Slack reminders after restart | Ensure the master scheduler is running; it executes the agent then reminders sequentially. |
| Calendar UI blank | Confirm React dev server/build is running and calendar API responds on port 5050. |
| Duplicate reminders | The scheduler de-duplicates by `(channel, date, time, title)`; if you manually edit the DB, make sure `notified` stays `true` for already-alerted meetings. |

---

## 8. Repository Structure (Highlights)

```
backend/
  agent.py                  # Slack ingestion
  calendar_server.py        # REST API
  check_meetings.py         # OpenAI meeting extraction
  check_upcoming_and_notify.py  # Slack reminders
  master_scheduler.py       # Agent + reminder orchestrator
frontend/
  chatbot.py                # Gradio assistant
  storage.py                # Conversation persistence
src/                        # React calendar
start_all_services.py       # Convenience launcher
```

---

That’s it—launch the services, open http://localhost:7860 for the chatbot, http://localhost:5050 for the calendar, and invite your Slack bot to a channel to watch meetings get captured automatically. Happy hacking! 🚀
