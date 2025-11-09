"""
Combined scheduler: runs agent every minute and meeting reminders every 5 minutes.
Uses threading to prevent timeouts and allow concurrent execution.
Meeting reminders only start after the first agent run completes.
All times displayed in Amsterdam timezone.
"""
import schedule
import time
import sys
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from agent import master_agent
from check_upcoming_and_notify import main as check_and_notify

# Amsterdam timezone
AMSTERDAM_TZ = ZoneInfo("Europe/Amsterdam")

# Flag to track if agent has run at least once
agent_has_run = threading.Event()


def run_agent():
    """Run the agent to process new messages in a separate thread."""
    def execute():
        now = datetime.now(AMSTERDAM_TZ)
        print(f"\n{'='*70}")
        print(f"Running agent at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"{'='*70}\n")
        try:
            master_agent()
            now = datetime.now(AMSTERDAM_TZ)
            print(f"\nAgent completed at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")
            # Signal that agent has completed at least once
            if not agent_has_run.is_set():
                agent_has_run.set()
                # Run reminder check immediately after first agent run
                print("First agent run completed - running initial reminder check...")
                run_reminder_check()
        except Exception as e:
            now = datetime.now(AMSTERDAM_TZ)
            print(f"\nAgent failed at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}: {e}\n", file=sys.stderr)
    
    # Run in separate thread to avoid blocking
    thread = threading.Thread(target=execute, daemon=True)
    thread.start()


def run_reminder_check():
    """Check for upcoming meetings and send reminders in a separate thread."""
    def execute():
        # Wait for agent to run at least once before sending reminders
        if not agent_has_run.is_set():
            now = datetime.now(AMSTERDAM_TZ)
            print(f"\n{'='*70}")
            print(f"Skipping reminder check at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print("Waiting for agent to complete first run before sending notifications")
            print(f"{'='*70}\n")
            return
        
        now = datetime.now(AMSTERDAM_TZ)
        print(f"\n{'='*70}")
        print(f"Checking for upcoming meetings at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"{'='*70}\n")
        try:
            check_and_notify()
            now = datetime.now(AMSTERDAM_TZ)
            print(f"\nReminder check completed at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")
        except Exception as e:
            now = datetime.now(AMSTERDAM_TZ)
            print(f"\nReminder check failed at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}: {e}\n", file=sys.stderr)
    
    # Run in separate thread to avoid blocking
    thread = threading.Thread(target=execute, daemon=True)
    thread.start()


def main():
    """Main scheduler loop."""
    now = datetime.now(AMSTERDAM_TZ)
    print("Master Scheduler started")
    print(f"Current Amsterdam time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("Agent runs: every 3 minutes (process new Slack messages)")
    print("Reminder check: every 5 minutes (notify upcoming meetings)")
    print("Note: Reminders will run immediately after first agent completes, then every 5 minutes")
    print("Using threaded execution to prevent timeouts")
    print("\nPress Ctrl+C to stop\n")
    
    # Run agent immediately on start
    run_agent()
    
    # Schedule tasks
    schedule.every(3).minutes.do(run_agent)
    schedule.every(5).minutes.do(run_reminder_check)
    
    # Keep running
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nMaster scheduler stopped by user")
        # Give threads time to finish
        print("Waiting for running tasks to complete...")
        time.sleep(2)
        sys.exit(0)


if __name__ == "__main__":
    main()