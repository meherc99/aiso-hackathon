@echo off
REM Batch script to run the agent with virtual environment

cd /d C:\Users\pctir\aiso-hackathon
call .venv\Scripts\activate.bat
python backend\agent.py
deactivate

REM Optional: Log the output with timestamp
REM python backend\agent.py >> logs\agent_%date:~-4,4%%date:~-7,2%%date:~-10,2%.log 2>&1