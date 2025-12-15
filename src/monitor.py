import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.config import config

logger = logging.getLogger(__name__)

class AutoLibrarianHandler(FileSystemEventHandler):
    def __init__(self, stability_checker):
        self.stability_checker = stability_checker

    def on_created(self, event):
        if not event.is_directory:
            self.stability_checker.add_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.stability_checker.add_file(event.dest_path)
            
    # Also listen for modified events to update stability tracker?
    # Usually writes trigger modified events.
    def on_modified(self, event):
         if not event.is_directory:
            self.stability_checker.update_activity(event.src_path)

class StabilityChecker:
    def __init__(self, process_callback):
        self.process_callback = process_callback
        self.tracked_files = {} # filepath -> {last_size, last_mtime, stable_start_time}

    def add_file(self, filepath):
        if filepath not in self.tracked_files:
            # Check if extension is allowed before tracking
            ext = os.path.splitext(filepath)[1].lower()
            if ext in config.ALLOWED_EXTENSIONS or ext == ".zip": # tracking zip for extraction
                logger.info(f"Tracking file for stability: {filepath}")
                self.tracked_files[filepath] = {
                    'last_size': -1,
                    'last_mtime': -1,
                    'stable_start_time': None
                }
    
    def update_activity(self, filepath):
        # If we receive a modified event, we know it's active.
        # However, checking stat in check() is more reliable for "stopped changing".
        # We can ensure it's in tracked_files if it's relevant.
        if filepath in self.tracked_files:
             # Just reset stable start time implicitly by the next check logic
             pass
        else:
             self.add_file(filepath)

    def check(self):
        to_process = []
        current_time = time.time()
        
        for filepath, data in list(self.tracked_files.items()):
            if not os.path.exists(filepath):
                logger.warning(f"File disappeared: {filepath}")
                del self.tracked_files[filepath]
                continue

            try:
                stat = os.stat(filepath)
                size = stat.st_size
                mtime = stat.st_mtime
            except OSError as e:
                logger.error(f"Error stating file {filepath}: {e}")
                continue

            if size == data['last_size'] and mtime == data['last_mtime']:
                if data['stable_start_time'] is None:
                    data['stable_start_time'] = current_time
                elif current_time - data['stable_start_time'] >= config.STABILITY_CHECK_DURATION:
                    to_process.append(filepath)
            else:
                # Reset stability timer
                data['last_size'] = size
                data['last_mtime'] = mtime
                data['stable_start_time'] = None

        for filepath in to_process:
            del self.tracked_files[filepath]
            logger.info(f"File stable: {filepath}")
            try:
                self.process_callback(filepath)
            except Exception as e:
                logger.error(f"Error processing file {filepath}: {e}")

    def get_stats(self):
        return {
            "tracked_files_count": len(self.tracked_files)
        }

class Monitor:
    def __init__(self, path, callback):
        self.path = path
        self.callback = callback
        self.stability_checker = StabilityChecker(callback)
        self.handler = AutoLibrarianHandler(self.stability_checker)
        self.observer = Observer()

    def start(self):
        logger.info(f"Starting monitor on {self.path}")
        if not os.path.exists(self.path):
            os.makedirs(self.path)
            
        # Scan for existing files
        self.scan_existing_files()
        
        self.observer.schedule(self.handler, self.path, recursive=True)
        self.observer.start()

    def scan_existing_files(self):
        logger.info(f"Scanning {self.path} for existing files...")
        for root, dirs, files in os.walk(self.path):
            for filename in files:
                filepath = os.path.join(root, filename)
                # Filter strictly by ignore/exclude logic if we had any,
                # but StabilityChecker handles extensions.
                if "__mac" in filepath or ".DS_Store" in filepath: # Basic junk filter
                     continue
                self.stability_checker.add_file(filepath)

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def tick(self):
        self.stability_checker.check()

    def get_stats(self):
        return self.stability_checker.get_stats()
