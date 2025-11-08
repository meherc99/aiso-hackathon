# aiso-hackathon

This repository contains two scripts:

- `parse_messages.py` — filters raw Slack-style messages down to objects with `username` and `message`, sorts by timestamp, and can send the result to OpenAI.
- `openai_wrapper.py` — small wrapper to send a conversation payload to the OpenAI Chat API and return the assistant reply.

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

Usage
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
