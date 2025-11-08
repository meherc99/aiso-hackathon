#!/usr/bin/env python3
"""
Utility script to launch the Gradio frontend and calendar backend together.

Usage:
    python start_servers.py

Press Ctrl+C to stop both processes.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent


def _python_executable() -> str:
    """Return the python executable to use (current interpreter)."""
    return sys.executable or "python"


def _spawn(cmd: List[str], cwd: Path) -> subprocess.Popen:
    """Start a subprocess and return the Popen handle."""
    env = os.environ.copy()
    return subprocess.Popen(cmd, cwd=cwd, env=env)


def main() -> None:
    python = _python_executable()

    commands = [
        {
            "name": "gradio-frontend",
            "cmd": [python, "chatbot.py"],
            "cwd": ROOT / "frontend",
        },
        {
            "name": "calendar-backend",
            "cmd": [python, "calendar_server.py"],
            "cwd": ROOT / "backend",
        },
    ]

    processes: List[subprocess.Popen] = []

    def _terminate_all(signum: int, frame) -> None:
        print("\nStopping servers...")
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, _terminate_all)
    signal.signal(signal.SIGTERM, _terminate_all)

    try:
        for entry in commands:
            print(f"➡️  Starting {entry['name']} ({' '.join(entry['cmd'])})")
            proc = _spawn(entry["cmd"], entry["cwd"])
            processes.append(proc)

        # Wait for any process to exit
        while True:
            for proc, entry in zip(processes, commands):
                retcode = proc.poll()
                if retcode is not None:
                    print(f"⚠️  {entry['name']} exited with code {retcode}. Shutting down.")
                    _terminate_all(0, None)
            # Avoid busy loop but keep the loop responsive cross-platform
            try:
                signal.pause()
            except AttributeError:
                import time
                time.sleep(1)

    except KeyboardInterrupt:
        _terminate_all(0, None)


if __name__ == "__main__":
    main()


