"""
Master scheduler that runs the Slack agent and, after it finishes, the reminder check.
Both steps are executed sequentially inside a background thread so the scheduler loop
remains responsive. All timestamps are shown in Amsterdam time.
"""
import schedule
import time
import sys
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from agent import master_agent
from check_upcoming_and_notify import main as check_and_notify

AMSTERDAM_TZ = ZoneInfo("Europe/Amsterdam")


def run_cycle():
    """Run the agent followed immediately by the reminder check."""
    def execute():
        cycle_start = datetime.now(AMSTERDAM_TZ)
        print(f"\n{'='*70}")
        print(f"Starting cycle at {cycle_start.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"{'='*70}\n")

        # Step 1: run the agent (adds meetings/tasks to the database)
        try:
            print(f"Running agent...")
            master_agent()
            print(f"Agent finished at {datetime.now(AMSTERDAM_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        except Exception as exc:
            print(f"Agent failed: {exc}", file=sys.stderr)
            return  # Skip reminder if agent failed

        # Step 2: run reminders (now that DB is up-to-date)
        try:
            print("Running reminder check...")
            check_and_notify()
            print(f"Reminder check completed at {datetime.now(AMSTERDAM_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        except Exception as exc:
            print(f"Reminder check failed: {exc}", file=sys.stderr)

        cycle_end = datetime.now(AMSTERDAM_TZ)
        print(f"\n{'='*70}")
        print(f"Cycle completed at {cycle_end.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Total cycle duration: {(cycle_end - cycle_start).total_seconds():.1f}s")
        print(f"{'='*70}\n")

    threading.Thread(target=execute, daemon=True).start()


def main():
    """Main scheduler loop."""
    now = datetime.now(AMSTERDAM_TZ)
    print("Master Scheduler started")
    print(f"Current Amsterdam time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("Cycle cadence: every 1 minute (agent runs first, reminders second)")
    print("Using threaded execution to keep the loop responsive")
    print("\nPress Ctrl+C to stop\n")

    # Run immediately on start
    run_cycle()

    # Schedule subsequent cycles
    schedule.every(1).minutes.do(run_cycle)

    # Keep running
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nMaster scheduler stopped by user")
        print("Waiting for running tasks to complete...")
        time.sleep(2)
        sys.exit(0)


if __name__ == "__main__":
    main()
