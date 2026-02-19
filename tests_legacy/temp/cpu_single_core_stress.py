import multiprocessing
import os
import time

# --- Configuration ---
# Explicitly set to use only 1 CPU core
NUM_CORES = 1
# Set the running duration in seconds. Set to None or 0 to run indefinitely until manually stopped.
RUN_DURATION = 30  # Example: Run for 30 seconds

def cpu_intensive_task():
    """
    A simple CPU-intensive task that executes an infinite loop of computation.
    This task will continuously occupy 100% of one core's resources.
    """
    # Get the current process ID (PID)
    pid = os.getpid()
    print(f"Starting single-core CPU stress process (PID: {pid})...")

    # Execute infinite computation loop
    while True:
        # Simple calculation: square root
        x = 0
        while x < 1000000:
            x ** 0.5
            x += 1
        
        # Reset x to ensure the loop keeps running
        if x == 1000000:
            x = 0

def main():
    """
    Main function: Creates only 1 process to execute the stress task.
    """
    print(f"Starting {NUM_CORES} high-load process, occupying only one core.")
    if RUN_DURATION and RUN_DURATION > 0:
        print(f"The script will automatically stop after {RUN_DURATION} seconds...")
    else:
        print("The script will run continuously. Press Ctrl+C to stop manually.")
        
    processes = []
    
    # Create only one process
    p = multiprocessing.Process(target=cpu_intensive_task)
    processes.append(p)
    p.start()

    print("--- Single-core high-load process started ---")

    try:
        if RUN_DURATION and RUN_DURATION > 0:
            # Automatic termination after specified time
            time.sleep(RUN_DURATION)
            
        else:
            # Run continuously, waiting for Ctrl+C
            for p in processes:
                p.join()
                
    except KeyboardInterrupt:
        # Catch Ctrl+C interrupt signal
        print("\nCaught Ctrl+C, terminating process...")
    
    finally:
        # Ensure the process is safely terminated
        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join()
        print("Single-core CPU stress process has stopped.")
        print("Script execution finished.")

if __name__ == "__main__":
    main()