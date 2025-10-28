import multiprocessing
import os
import time
import argparse

# --- Constants ---
# Use the maximum available cores for informational purposes
TOTAL_CORES = multiprocessing.cpu_count()

def cpu_intensive_task(process_id):
    """
    A simple CPU-intensive task that executes an infinite loop of computation.
    This task will continuously occupy 100% of the core it runs on.
    """
    pid = os.getpid()
    print(f"Starting CPU stress process #{process_id} (PID: {pid})...")

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

def parse_arguments():
    """
    Handles command-line arguments using argparse.
    """
    parser = argparse.ArgumentParser(
        description="A Python script to generate high CPU load using multiple processes.",
        epilog=f"Total logical CPU cores available: {TOTAL_CORES}"
    )
    
    # Required argument: Number of cores to use
    parser.add_argument(
        '-c', '--cores', 
        type=int, 
        required=True, 
        help="The number of CPU cores to utilize (e.g., 1, 4, or max)."
    )
    
    # Optional argument: Running time in seconds
    parser.add_argument(
        '-t', '--time', 
        type=int, 
        default=0, 
        help="Duration to run the stress test in seconds. Set to 0 (default) for continuous run."
    )
    
    args = parser.parse_args()
    
    # Validation
    if args.cores <= 0:
        parser.error("The number of cores must be a positive integer.")
    if args.time < 0:
        parser.error("The run time must be zero or a positive integer.")
        
    return args

def main():
    """
    Main function: Parses arguments and starts the stress processes.
    """
    args = parse_arguments()
    num_processes = args.cores
    run_duration = args.time

    print(f"Total logical CPU cores available: {TOTAL_CORES}")
    print(f"Targeting {num_processes} CPU core(s) for high-load.")
    
    if run_duration > 0:
        print(f"The script will automatically stop after {run_duration} seconds.")
    else:
        print("The script will run continuously. Press Ctrl+C to stop manually.")
        
    processes = []
    
    # Create the specified number of processes
    for i in range(num_processes):
        # Pass process index to the task function
        p = multiprocessing.Process(target=cpu_intensive_task, args=(i + 1,))
        processes.append(p)
        p.start()

    print("--- High-load processes started ---")

    try:
        if run_duration > 0:
            # Automatic termination after specified time
            time.sleep(run_duration)
            
        else:
            # Run continuously, wait for Ctrl+C
            # Using join on all processes keeps the main process alive
            for p in processes:
                p.join()
                
    except KeyboardInterrupt:
        # Catch Ctrl+C interrupt signal
        print("\nCaught Ctrl+C, terminating all processes...")
    
    finally:
        # Ensure all processes are safely terminated
        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join()
        print("All CPU stress processes have stopped.")
        print("Script execution finished.")

if __name__ == "__main__":
    main()