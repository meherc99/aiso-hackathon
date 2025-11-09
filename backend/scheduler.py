"""
Scheduler to run the agent every minute.
"""

import schedule
import time
import sys
from datetime import datetime
from agent import master_agent


def job():
    """Run the agent and log execution."""
    print(f"\n{'='*70}")
    print(f"🤖 Running agent at {datetime.now().isoformat()}")
    print(f"{'='*70}\n")
    
    try:
        master_agent()
        print(f"\n✅ Agent completed successfully at {datetime.now().isoformat()}\n")
    except Exception as e:
        print(f"\n❌ Agent failed at {datetime.now().isoformat()}: {e}\n", file=sys.stderr)


def main():
    """Main scheduler loop."""
    print("🚀 Slack Agent Scheduler started")
    print(f"⏰ Will run every minute")
    print(f"🔄 First run: immediately")
    print(f"📍 Next run: {datetime.now().replace(second=0, microsecond=0).replace(minute=datetime.now().minute + 1)}")
    print("\nPress Ctrl+C to stop\n")
    
    # Run immediately on start
    job()
    
    # Schedule to run every minute
    schedule.every().minute.do(job)
    
    # Keep the script running
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)  # Check every second
    except KeyboardInterrupt:
        print("\n\n🛑 Scheduler stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()