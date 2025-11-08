@echo off
echo ========================================
echo Starting Calendar Server and Chatbot
echo ========================================
echo.

echo Starting Calendar Server in background...
start /min python backend\calendar_server.py

echo Waiting for calendar server to start...
timeout /t 3 /nobreak >nul

echo.
echo Starting Chatbot...
echo.
echo ========================================
echo Both servers are running!
echo ========================================
echo Calendar API: http://localhost:5050/api/events
echo Chatbot UI:   http://localhost:7860
echo.
echo Press Ctrl+C to stop the chatbot
echo (Calendar server will keep running in background)
echo.

python frontend\chatbot.py
