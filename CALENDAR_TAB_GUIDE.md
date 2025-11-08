# Calendar Tab Integration Guide

## Overview

The chatbot application now features a **tabbed interface** with two main views:

### 1. Chat Assistant Tab (Default)
- AI-powered conversational interface
- Real-time conversation management
- Today's calendar sidebar showing upcoming events
- Task list panel

### 2. Full Calendar Tab
- Complete calendar application embedded via iframe
- Full event management (Create, Read, Update, Delete)
- Synchronized with the chat assistant
- Direct interaction with calendar UI

## How It Works

### Architecture

```
┌─────────────────────────────────────────────┐
│         Gradio Chatbot App (Port 7860)      │
│  ┌───────────────┐     ┌─────────────────┐ │
│  │ Chat Tab      │     │ Calendar Tab    │ │
│  │ - Chatbot     │     │ - Iframe        │ │
│  │ - Sidebar     │     │ - React App     │ │
│  └───────────────┘     └─────────────────┘ │
└─────────────────────────────────────────────┘
                    ↓
        ┌───────────────────────────┐
        │  Calendar Server (Port    │
        │  5000) REST API + Static  │
        │  Files                    │
        └───────────────────────────┘
                    ↓
        ┌───────────────────────────┐
        │   SQLite Database         │
        │   - Conversations         │
        │   - Events                │
        └───────────────────────────┘
```

## Usage

### Starting the Application

1. **Start both servers:**
   ```bash
   # Windows batch script
   .\start_servers.bat
   
   # Or PowerShell script
   .\start_servers.ps1
   
   # Or manually (two terminals):
   # Terminal 1:
   python backend/calendar_server.py
   
   # Terminal 2:
   python frontend/chatbot.py
   ```

2. **Open the chatbot:**
   - Navigate to `http://localhost:7860`
   - You'll see two tabs at the top: "Chat Assistant" and "Full Calendar"

### Using the Chat Assistant Tab

- **Chat with AI**: Type messages to interact with the AI assistant
- **View Today's Events**: Check the right sidebar for today's schedule
- **View Tasks**: See your task list below the calendar
- **Manage Conversations**: Use the left sidebar to switch between conversations

### Using the Full Calendar Tab

- **View Calendar**: Switch to the "Full Calendar" tab to see the complete calendar
- **Create Events**: Click to add new events directly in the calendar
- **Edit Events**: Click on existing events to modify them
- **Delete Events**: Remove events you no longer need
- **Sync**: All changes sync automatically with the database

### Advanced: Changing Calendar URL

If you're running the React app on a different port (e.g., Vite dev server on port 5173):

1. Switch to the "Full Calendar" tab
2. Expand the "Advanced: Change Calendar URL" accordion
3. Enter the new URL (e.g., `http://localhost:5173/`)
4. Click "Update Calendar View"

## Deployment Options

### Option A: Built React App (Production)
1. Build the React app:
   ```bash
   cd src
   npm run build
   cd ..
   ```
2. The calendar server will serve the built files from `src/dist/`
3. Calendar tab will load from: `http://localhost:5000/`

### Option B: Vite Dev Server (Development)
1. Start the Vite dev server:
   ```bash
   cd src
   npm run dev
   ```
2. Update the calendar tab URL to: `http://localhost:5173/`
3. Hot reload enabled for development

## Troubleshooting

### Calendar Tab Shows Error Message

**Symptoms:** 
- Blank iframe or error message
- "Loading calendar..." message persists

**Solutions:**

1. **Ensure calendar server is running:**
   ```bash
   python backend/calendar_server.py
   ```
   Should show: `Calendar Server starting on http://localhost:5000`

2. **Check if React app is built:**
   ```bash
   cd src
   npm run build
   cd ..
   ```

3. **Try accessing calendar directly:**
   - Open `http://localhost:5000/` in a browser
   - If it works, refresh the chatbot tab

4. **Use Vite dev server instead:**
   ```bash
   cd src
   npm run dev
   ```
   Then update calendar URL to `http://localhost:5173/`

### CORS Errors

**Symptoms:**
- Console shows "CORS policy" errors
- Calendar doesn't load in iframe

**Solutions:**
- The calendar server has CORS enabled by default
- Check that both servers are running
- Clear browser cache and reload

### Events Don't Sync

**Symptoms:**
- Events created in calendar don't appear in chat
- Events from chat don't show in calendar

**Current Status:**
- Database is shared (events stored in same DB)
- React app needs to be updated to use API instead of localStorage
- See "Next Steps" section below

## Next Steps for Full Integration

### 1. Update React App to Use API

Currently, the React app uses localStorage. To sync with the chat:

**Edit `src/store/events.js`:**
```javascript
// Replace localStorage calls with API calls
const API_BASE = 'http://localhost:5000/api';

export const loadEvents = async () => {
  const response = await fetch(`${API_BASE}/events`);
  return await response.json();
};

export const createEvent = async (event) => {
  const response = await fetch(`${API_BASE}/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(event)
  });
  return await response.json();
};

// Similar for update and delete...
```

### 2. Update Chatbot to Create Events

**Edit `frontend/chatbot.py`:**
- Parse AI responses for meeting times
- Call calendar API to create events
- Refresh calendar sidebar after event creation

### 3. Enable Real-time Sync

- Add periodic refresh for calendar iframe
- Implement WebSocket for live updates
- Show notifications when events are created

## Code Changes

### Files Modified

1. **`frontend/chatbot.py`**
   - Added `gr.Tabs()` wrapper
   - Created "Chat Assistant" tab with existing UI
   - Created "Full Calendar" tab with iframe
   - Added URL customization feature

2. **`backend/calendar_server.py`**
   - REST API for calendar events
   - Static file serving for React app
   - CORS enabled

3. **`requirements.txt`**
   - Added Flask and Flask-CORS

4. **`start_servers.bat`** (new)
   - Windows batch script to start both servers

### Key Code Sections

**Tab Structure:**
```python
with gr.Tabs() as tabs:
    with gr.TabItem("Chat Assistant", id="chat_tab"):
        # Existing chat UI
        
    with gr.TabItem("Full Calendar", id="calendar_tab"):
        # Calendar iframe
```

**Calendar Iframe:**
```python
calendar_iframe = gr.HTML(
    """
    <iframe 
        src="http://localhost:5000/" 
        width="100%" 
        height="800px" 
        frameborder="0"
        style="border: 1px solid #ddd; border-radius: 8px;"
    >
    </iframe>
    """
)
```

## Benefits

✅ **Unified Interface**: Chat and calendar in one application
✅ **Easy Navigation**: Simple tab switching
✅ **Flexible Deployment**: Support for both built app and dev server
✅ **Shared Database**: Events and conversations in one place
✅ **Future Ready**: Foundation for full sync implementation

## Summary

The calendar tab integration provides a seamless way to access both the chat assistant and full calendar functionality within a single interface. While the UI integration is complete, full data synchronization between chat and calendar will require updating the React app to use the REST API instead of localStorage.
