"""
Start all services in parallel using Python's subprocess module.
Works cross-platform (Windows, Linux, macOS).
"""
import subprocess
import sys
import os
import time
import signal
from pathlib import Path
from threading import Thread
from queue import Queue

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.resolve()

# Define services to run
SERVICES = [
    {
        "name": "NPM Build",
        "command": ["npm", "run", "build"],
        "cwd": PROJECT_ROOT / "src",
        "color": "\033[95m",  # Magenta
        "run_once": True,  # Only run once, not continuously
    },
    {
        "name": "NPM Dev Server",
        "command": ["npm", "run", "dev"],
        "cwd": PROJECT_ROOT / "src",
        "color": "\033[92m",  # Green
    },
    {
        "name": "Scheduler",
        "command": [sys.executable, "master_scheduler.py"],
        "cwd": PROJECT_ROOT / "backend",
        "color": "\033[93m",  # Yellow
    },
    {
        "name": "Servers (Chatbot + Calendar)",
        "command": [sys.executable, "start_servers.py"],
        "cwd": PROJECT_ROOT,
        "color": "\033[94m",  # Blue
    },
]

processes = []
output_queues = []


def read_output(proc, queue, service_name, color):
    """Read process output in a separate thread."""
    try:
        for line in iter(proc.stdout.readline, ''):
            if line:
                queue.put((service_name, color, line.strip()))
    except Exception as e:
        queue.put((service_name, "\033[91m", f"Error reading output: {e}"))


def print_output_worker(queue, start_time_ref):
    """Print output from all services."""
    first_log_printed = [False]  # Use list to allow modification in nested scope
    first_api_call_printed = [False]  # Track first API call
    
    while True:
        try:
            service_name, color, line = queue.get(timeout=0.1)
            if line:
                print(f"{color}[{service_name}]\033[0m {line}")
                
                # Print runtime after first service log (only once)
                if not first_log_printed[0]:
                    first_log_printed[0] = True
                    elapsed = time.time() - start_time_ref[0]
                    print(f"\n\033[90mTime to first service log: {elapsed:.2f} seconds\033[0m\n")
                
                # Print runtime after first API call (only once)
                if not first_api_call_printed[0] and "GET /api/" in line and '"' in line:
                    first_api_call_printed[0] = True
                    elapsed = time.time() - start_time_ref[0]
                    print(f"\n\033[90mTime to first API call: {elapsed:.2f} seconds\033[0m\n")
        except:
            continue


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n\033[91mStopping all services...\033[0m")
    for proc, service in zip(processes, SERVICES):
        try:
            print(f"  Stopping {service['name']}...")
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception as e:
            print(f"  Error stopping {service['name']}: {e}")
    print("\033[92mAll services stopped.\033[0m")
    sys.exit(0)


def start_service(service):
    """Start a single service with error handling."""
    try:
        # On Windows, use shell=True for npm commands
        use_shell = sys.platform == "win32" and service["command"][0] == "npm"
        
        proc = subprocess.Popen(
            service["command"],
            cwd=service["cwd"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=use_shell,
            text=True,
            bufsize=1,
        )
        return proc
    except Exception as e:
        print(f"{service['color']}  Failed to start {service['name']}: {e}\033[0m")
        return None


def main():
    start_time = time.time()
    
    print("\033[96m" + "="*60)
    print("Starting All Services")
    print("="*60 + "\033[0m\n")

    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, signal_handler)

    # Create a shared queue for output
    output_queue = Queue()
    
    # Shared reference for start time (so printer thread can access it)
    start_time_ref = [start_time]
    
    # Start output printer thread
    printer_thread = Thread(target=print_output_worker, args=(output_queue, start_time_ref), daemon=True)
    printer_thread.start()

    # Start all services
    for service in SERVICES:
        print(f"{service['color']}Starting {service['name']}...\033[0m")
        
        # Check if this is a run-once command (like build)
        if service.get("run_once", False):
            # Run synchronously and wait for completion
            use_shell = sys.platform == "win32" and service["command"][0] == "npm"
            try:
                result = subprocess.run(
                    service["command"],
                    cwd=service["cwd"],
                    shell=use_shell,
                    capture_output=False,
                    text=True,
                )
                if result.returncode == 0:
                    print(f"  {service['name']} completed successfully")
                    # After a successful build, remove the local DB file so the backend starts with a clean DB.
                    try:
                        if sys.platform == "win32":
                            # Use PowerShell Remove-Item on Windows as requested
                            rm_cmd = [
                                "powershell",
                                "-NoProfile",
                                "-Command",
                                "Remove-Item 'backend\\data\\db.json' -ErrorAction SilentlyContinue",
                            ]
                        else:
                            # Fallback for non-Windows systems
                            rm_cmd = ["rm", "-f", str(PROJECT_ROOT / "backend" / "data" / "db.json")]

                        subprocess.run(rm_cmd, cwd=PROJECT_ROOT, shell=False, check=False)
                        print("  Removed backend/data/db.json (if it existed)")
                    except Exception as e:
                        print(f"  Failed to remove backend/data/db.json: {e}")
                else:
                    print(f"  {service['name']} failed with exit code {result.returncode}")
                processes.append(None)  # Don't monitor this process
            except Exception as e:
                print(f"  Failed to run {service['name']}: {e}")
                processes.append(None)
        else:
            # Start as background process
            proc = start_service(service)
            if proc:
                processes.append(proc)
                output_queues.append(output_queue)
                
                # Start thread to read output
                output_thread = Thread(
                    target=read_output, 
                    args=(proc, output_queue, service['name'], service['color']),
                    daemon=True
                )
                output_thread.start()
                
                print(f"  {service['name']} started (PID: {proc.pid})")
            else:
                processes.append(None)
        
        time.sleep(1)  # Small delay between starts

    print("\n\033[96m" + "="*60)
    print("All services started!")
    print("="*60 + "\033[0m")
    print("\033[93m\nPress Ctrl+C to stop all services\033[0m\n")
    print("\033[90m" + "-"*60 + "\033[0m\n")
    print("Main app running on: http://localhost:7860")
    print("Calendar app running on: http://localhost:5050")
    print("React dev server running on: http://localhost:5173")
    
    # Calculate and display startup time
    elapsed_time = time.time() - start_time
    print(f"\nStartup completed in {elapsed_time:.2f} seconds")
    print("\033[90m" + "-"*60 + "\033[0m\n")

    # Monitor processes
    first_log_seen = False
    try:
        while True:
            time.sleep(2)
            
            # Check if any process has died
            for i, (proc, service) in enumerate(zip(processes, SERVICES)):
                if proc and proc.poll() is not None:
                    print(f"\n\033[91mWARNING: {service['name']} has stopped (exit code: {proc.returncode})\033[0m")
                    
                    # Read any remaining output
                    if proc.stdout:
                        remaining = proc.stdout.read()
                        if remaining:
                            print(f"\033[91mLast output from {service['name']}:\033[0m")
                            print(remaining)
                    
                    # Try to restart the service
                    print(f"\nRestarting {service['name']}...")
                    time.sleep(2)  # Wait a bit before restart
                    
                    new_proc = start_service(service)
                    if new_proc:
                        processes[i] = new_proc
                        
                        # Start new output reader thread
                        output_thread = Thread(
                            target=read_output,
                            args=(new_proc, output_queue, service['name'], service['color']),
                            daemon=True
                        )
                        output_thread.start()
                        
                        print(f"  {service['name']} restarted (PID: {new_proc.pid})\n")
                    else:
                        print(f"  Failed to restart {service['name']}\n")
                        
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
