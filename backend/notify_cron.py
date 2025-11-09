"""
Run the check_upcoming_and_notify.py every 5 minutes using `schedule`.
"""
import time
import schedule
import subprocess
import sys
from datetime import datetime

SCRIPT = "backend/check_upcoming_and_notify.py"

def job():
    print(f"[{datetime.now().isoformat()}] Running upcoming meeting check")
    rc = subprocess.call([sys.executable, SCRIPT])
    print(f"[{datetime.now().isoformat()}] Return code: {rc}")

def main():
    print("🚀 Meeting Reminder Scheduler started")
    print("⏰ Checking for upcoming meetings every 5 minutes")
    print("Press Ctrl+C to stop\n")
    
    # Run immediately, then every 5 minutes
    job()
    schedule.every(5).minutes.do(job)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Scheduler stopped by user")

if __name__ == "__main__":
    main()