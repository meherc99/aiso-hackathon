"""
Scheduler that checks for upcoming meetings every 5 minutes and sends Slack notifications.
"""
import time
import schedule
import sys
from datetime import datetime
from check_upcoming_and_notify import main as check_and_notify


def job():
    """Run the meeting check and notification process."""
    print(f"\n{'='*70}")
    print(f"🔔 Checking for upcoming meetings at {datetime.now().isoformat()}")
    print(f"{'='*70}\n")
    
    try:
        check_and_notify()
        print(f"\n✅ Check completed at {datetime.now().isoformat()}\n")
    except Exception as e:
        print(f"\n❌ Check failed at {datetime.now().isoformat()}: {e}\n", file=sys.stderr)


def main():
    """Main scheduler loop - runs every 5 minutes."""
    print("🚀 Meeting Reminder Scheduler started")
    print("⏰ Checking for upcoming meetings every 5 minutes")
    print("📍 First check: immediately")
    next_run = datetime.now().replace(second=0, microsecond=0)
    next_run = next_run.replace(minute=(next_run.minute // 5 + 1) * 5 % 60)
    if next_run.minute == 0:
        next_run = next_run.replace(hour=next_run.hour + 1)
    print(f"📍 Next scheduled check: {next_run}")
    print("\nPress Ctrl+C to stop\n")
    
    # Run immediately on start
    job()
    
    # Schedule to run every 5 minutes
    schedule.every(5).minutes.do(job)
    
    # Keep the script running
    try:
        while True:
            schedule.run_pending()
            time.sleep(10)  # Check every 10 seconds
    except KeyboardInterrupt:
        print("\n\n🛑 Meeting reminder scheduler stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()