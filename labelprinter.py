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
import re

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

def print_label(filepath, brother_ql_global_args, brother_ql_print_args, no_cut, error_suffix=".error", done_suffix=".done", timeout_seconds=30):
    """Prints a label using brother_ql in a separate process with a timeout."""
    command_parts = ["brother_ql", *brother_ql_global_args, "print", *brother_ql_print_args, filepath]
    if no_cut:
        command_parts.append("--no-cut")
    full_command = command_parts
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

    def __init__(self, watch_folder, brother_ql_global_args, brother_ql_print_args, error_suffix, done_suffix, timeout_seconds, print_queue, group_separator, grace_period):
        self.watch_folder = watch_folder
        self.brother_ql_global_args = brother_ql_global_args
        self.brother_ql_print_args = brother_ql_print_args
        self.error_suffix = error_suffix
        self.done_suffix = done_suffix
        self.timeout_seconds = timeout_seconds
        self.print_queue = print_queue
        self.group_separator = group_separator
        self.grace_period = grace_period
        self.current_group = None
        self.pending_group_files = []
        self._processing_timer = None
        self.processed_files = set()

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".png"):
            filepath = event.src_path
            if filepath not in self.processed_files:
                self.processed_files.add(filepath)
                self._enqueue_file(filepath)

    def _enqueue_file(self, filepath):
        group_match = re.match(f"^(.*){re.escape(self.group_separator)}", os.path.basename(filepath))
        current_file_group = group_match.group(1) if group_match else None

        if current_file_group == self.current_group and self._processing_timer:
            self.pending_group_files.append(filepath)
            self._reset_timer()
        elif current_file_group == self.current_group and not self._processing_timer:
            self.pending_group_files.append(filepath)
            self._start_timer()
        else:
            self._process_pending_group()
            self.current_group = current_file_group
            self.pending_group_files.append(filepath)
            self._start_timer()

    def _start_timer(self):
        if self._processing_timer is None:
            self._processing_timer = threading.Timer(self.grace_period, self._process_pending_group)
            self._processing_timer.start()

    def _reset_timer(self):
        if self._processing_timer:
            self._processing_timer.cancel()
            self._processing_timer = threading.Timer(self.grace_period, self._process_pending_group)
            self._processing_timer.start()

    def _process_pending_group(self):
        if self._processing_timer:
            self._processing_timer.cancel()
            self._processing_timer = None

        if self.pending_group_files:
            self.pending_group_files.sort(key=os.path.getmtime)
            num_files = len(self.pending_group_files)
            for i, filepath in enumerate(self.pending_group_files):
                no_cut = i < num_files - 1  # Use --no-cut if there are more files in the group
                self.print_queue.put((filepath, self.brother_ql_global_args, self.brother_ql_print_args, no_cut, self.error_suffix, self.done_suffix, self.timeout_seconds))

            self.pending_group_files = []
            self.current_group = None

def worker_thread(print_queue):
    """Worker thread to process print jobs one at a time."""
    while True:
        job = print_queue.get()
        if job is None:  # Sentinel value to signal thread termination
            break
        filepath, brother_ql_global_args, brother_ql_print_args, no_cut, error_suffix, done_suffix, timeout_seconds = job
        if filepath:
            print_label(filepath, brother_ql_global_args, brother_ql_print_args, no_cut, error_suffix, done_suffix, timeout_seconds)
        print_queue.task_done()

def main():
    parser = argparse.ArgumentParser(description="Watch a folder for new PNG files and print them using brother_ql with grouping and grace period.")
    parser.add_argument("watch_folder", help="The folder to watch for new PNG files.")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds for the brother_ql print command.")
    parser.add_argument("--error_suffix", type=str, default=".error", help="Suffix to add to skipped files.")
    parser.add_argument("--done_suffix", type=str, default=".done", help="Suffix to add to successfully printed files.")
    parser.add_argument("--group_separator", type=str, default="__", help="Separator in filename to define groups for no-cut (e.g., '__').")
    parser.add_argument("--grace_period", type=float, default=0.25, help="Grace period in seconds (default 0.25s) to wait for new files in the same group.")
    parser.add_argument("--skip_venv_check", action='store_true', help="Skip virtual env check. Allows running without virtual env - typically in containers.")
    parser.add_argument("brother_ql_args", nargs=argparse.REMAINDER, help="Arguments to pass to brother_ql, separate global options from 'print' subcommand options with 'print'.")

    args = parser.parse_args()

    if not args.skip_venv_check:
        check_venv()

    watch_folder = os.path.abspath(args.watch_folder)
    timeout_seconds = args.timeout
    error_suffix = args.error_suffix
    done_suffix = args.done_suffix
    group_separator = args.group_separator
    grace_period = args.grace_period

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
    event_handler = NewFileHandler(watch_folder, brother_ql_global_args, brother_ql_print_args, error_suffix, done_suffix, timeout_seconds, print_queue, group_separator, grace_period)
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