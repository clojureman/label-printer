#!/usr/bin/env python3

import sys
import time
import os
import subprocess
import threading
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import queue

def check_venv():
    """Checks if a virtual environment named 'venv' in the same directory is active."""
    venv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv")
    if not os.path.exists(venv_path) or not os.path.isdir(venv_path):
        print(f"Error: Virtual environment 'venv' not found in the same directory as the script.")
        sys.exit(1)

    # Check for activation indicator (platform-dependent)
    if sys.prefix == sys.base_prefix:
        print(f"Error: Virtual environment '{venv_path}' is not active. Please activate it before running this script.")
        print("  On Linux/macOS: source venv/bin/activate")
        print("  On Windows: .\\venv\\Scripts\\activate")
        sys.exit(1)
    else:
        print(f"Virtual environment '{venv_path}' is active.")

def print_label(filepath, brother_ql_global_args, brother_ql_print_args, error_suffix=".error", done_suffix=".done", timeout_seconds=30):
    """Prints a label using brother_ql in a separate process with a timeout."""
    full_command = ["brother_ql", *brother_ql_global_args, "print", *brother_ql_print_args, filepath]
    print(f"Attempting to run brother_ql with command: {' '.join(full_command)}")
    try:
        process = subprocess.Popen(
            full_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate(timeout=timeout_seconds)

        if process.returncode == 0:
            print(f"Successfully printed: {filepath}")
            os.rename(filepath, filepath + done_suffix)
        else:
            print(f"Error printing {filepath}: {stderr.decode()}")
            os.rename(filepath, filepath + error_suffix)

    except subprocess.TimeoutExpired:
        print(f"Timeout while printing {filepath}. Skipping.")
        os.rename(filepath, filepath + error_suffix)
    except FileNotFoundError:
        print("Error: brother_ql command not found. Please ensure it's installed and in your PATH (within the active venv).")
        os._exit(1)  # Exit the entire program as brother_ql is essential
    except Exception as e:
        print(f"An unexpected error occurred while printing {filepath}: {e}")
        os.rename(filepath, filepath + error_suffix)

class NewFileHandler(FileSystemEventHandler):
    def __init__(self, watch_folder, brother_ql_global_args, brother_ql_print_args, error_suffix, done_suffix, timeout_seconds, print_queue):
        self.watch_folder = watch_folder
        self.brother_ql_global_args = brother_ql_global_args
        self.brother_ql_print_args = brother_ql_print_args
        self.error_suffix = error_suffix
        self.done_suffix = done_suffix
        self.timeout_seconds = timeout_seconds
        self.processed_files = set()
        self.print_queue = print_queue

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".png"):
            filepath = event.src_path
            if filepath not in self.processed_files:
                print(f"New PNG file detected: {filepath}")
                self.processed_files.add(filepath)
                self.print_queue.put((filepath, self.brother_ql_global_args, self.brother_ql_print_args, self.error_suffix, self.done_suffix, self.timeout_seconds))

def worker_thread(print_queue):
    """Worker thread to process print jobs one at a time."""
    while True:
        job = print_queue.get()
        if job is None:  # Sentinel value to signal thread termination
            break
        filepath, brother_ql_global_args, brother_ql_print_args, error_suffix, done_suffix, timeout_seconds = job
        print_label(filepath, brother_ql_global_args, brother_ql_print_args, error_suffix, done_suffix, timeout_seconds)
        print_queue.task_done()

def main():
    check_venv()
    parser = argparse.ArgumentParser(description="Watch a folder for new PNG files and print them using brother_ql.")
    parser.add_argument("watch_folder", help="The folder to watch for new PNG files.")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds for the brother_ql print command.")
    parser.add_argument("--error_suffix", type=str, default=".error", help="Suffix to add to skipped files.")
    parser.add_argument("--done_suffix", type=str, default=".done", help="Suffix to add to successfully printed files.")
    parser.add_argument("brother_ql_args", nargs=argparse.REMAINDER, help="Arguments to pass to brother_ql, separate global options from 'print' subcommand options with '--'.")

    args = parser.parse_args()

    watch_folder = os.path.abspath(args.watch_folder)
    timeout_seconds = args.timeout
    error_suffix = args.error_suffix
    done_suffix = args.done_suffix

    brother_ql_global_args = []
    brother_ql_print_args = []

    if "print" in args.brother_ql_args:
        try:
            print_index = args.brother_ql_args.index("print")
            brother_ql_global_args = args.brother_ql_args[:print_index]
            brother_ql_print_args = args.brother_ql_args[print_index + 1:]
        except ValueError:
            # This should not happen if "print" check passed, but for robustness
            brother_ql_global_args = args.brother_ql_args
    else:
        brother_ql_global_args = args.brother_ql_args

    if not os.path.isdir(watch_folder):
        print(f"Error: Watch folder '{watch_folder}' does not exist or is not a directory.")
        sys.exit(1)

    print_queue = queue.Queue()
    event_handler = NewFileHandler(watch_folder, brother_ql_global_args, brother_ql_print_args, error_suffix, done_suffix, timeout_seconds, print_queue)
    observer = Observer()
    observer.schedule(event_handler, watch_folder, recursive=False)
    observer.start()

    worker = threading.Thread(target=worker_thread, args=(print_queue,))
    worker.daemon = True
    worker.start()

    try:
        print(f"Watching folder '{watch_folder}' for new PNG files...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping the watcher.")
    finally:
        print_queue.put(None)  # Signal worker thread to exit
        worker.join()
        observer.stop()
        observer.join()

if __name__ == "__main__":
    main()