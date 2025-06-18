import os
import time
import logging
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Temporary file patterns and extensions to ignore
TEMP_FILE_EXTENSIONS = ['.crdownload', '.part', '.tmp', '.partial']
TEMP_FILE_PATTERNS = ['~$', '.~lock.'] # Office temporary files, LibreOffice lock files

class DownloadEventHandler(FileSystemEventHandler):
    """Handles file system events for monitoring new downloads."""

    def __init__(self, parent_service):
        super().__init__()
        self.parent_service = parent_service
        self.logger = logging.getLogger(__name__ + ".DownloadEventHandler")

    def on_created(self, event):
        if event.is_directory:
            self.logger.debug(f"Ignoring directory creation: {event.src_path}")
            return

        src_path = event.src_path
        filename = os.path.basename(src_path).lower()
        self.logger.info(f"File creation event detected: {src_path}")

        # Filter out temporary files by extension
        if any(filename.endswith(ext) for ext in TEMP_FILE_EXTENSIONS):
            self.logger.info(f"Ignoring temporary file by extension: {src_path}")
            return

        # Filter out temporary files by pattern
        if any(filename.startswith(pattern) for pattern in TEMP_FILE_PATTERNS):
            self.logger.info(f"Ignoring temporary file by pattern: {src_path}")
            return

        # Further check for hidden files (less common for direct downloads but good practice)
        if filename.startswith('.'):
            self.logger.info(f"Ignoring hidden file: {src_path}")
            return

        # Stability Check
        try:
            self.logger.debug(f"Performing stability check for: {src_path}")
            time.sleep(1.5) # Wait for 1.5 seconds for the file to be written

            if not os.path.exists(src_path):
                self.logger.warning(f"File {src_path} disappeared after initial detection.")
                return

            initial_size = os.path.getsize(src_path)
            if initial_size == 0: # Some apps create an empty file first
                time.sleep(1.5) # Wait a bit longer
                initial_size = os.path.getsize(src_path)
                if initial_size == 0 and not filename.endswith(('.txt', '.json', '.xml')): # Allow zero size for some text files
                    self.logger.info(f"Ignoring zero-byte file (after delay): {src_path}")
                    return


            time.sleep(1) # Wait another second

            if not os.path.exists(src_path): # Check existence again
                self.logger.warning(f"File {src_path} disappeared during stability check.")
                return

            current_size = os.path.getsize(src_path)

            if initial_size != current_size:
                self.logger.info(f"File size changed for {src_path} ({initial_size} -> {current_size}). Assuming still writing.")
                # Optionally, could schedule another check or rely on on_modified
                return

            if current_size == 0 and not filename.endswith(('.txt', '.json', '.xml')): # Final check for zero-byte files
                self.logger.info(f"Ignoring zero-byte file (final check): {src_path}")
                return

            self.logger.info(f"File deemed stable: {src_path}, size: {current_size}")
            self.parent_service.new_document_detected.emit(src_path)

        except FileNotFoundError:
            self.logger.error(f"File not found during stability check: {src_path}")
        except Exception as e:
            self.logger.error(f"Error during stability check for {src_path}: {e}", exc_info=True)

    def on_modified(self, event):
        if event.is_directory:
            return
        # This could be used to re-evaluate a file if on_created was inconclusive,
        # or if a file was initially temporary and then renamed.
        # For now, we primarily rely on on_created with robust filtering.
        # self.logger.debug(f"File modified event: {event.src_path}")
        pass


class DownloadMonitorService(QObject):
    """
    Monitors a specified directory for new (non-temporary) files using watchdog,
    running the observer in a separate QThread.
    """
    new_document_detected = pyqtSignal(str) # Signal emitting the path of the new document

    def __init__(self, monitored_path, parent=None):
        super().__init__(parent)
        self.monitored_path = monitored_path
        self.observer = Observer()
        self.event_handler = DownloadEventHandler(parent_service=self)
        self.watchdog_thread = None
        self.logger = logging.getLogger(__name__ + ".DownloadMonitorService")

    def start(self):
        if not self.monitored_path or not os.path.isdir(self.monitored_path):
            self.logger.error(f"Monitored path does not exist or is invalid: {self.monitored_path}")
            return

        if self.watchdog_thread is not None and self.watchdog_thread.isRunning():
            self.logger.warning("Service already running.")
            return

        self.watchdog_thread = QThread()
        # Important: Move the observer itself to the thread, not just its methods.
        # The observer's internal mechanisms need to run in that thread.
        self.observer.moveToThread(self.watchdog_thread)

        # Schedule must happen before observer.start, but can be done from the main thread.
        # The observer must be running in its thread before it can process events.
        try:
            # Ensure observer is fresh if restarted
            if self.observer.is_alive(): # Should not happen if logic is correct
                self.observer.stop()
                self.observer.join(timeout=1) # Give it a moment to stop

            self.observer = Observer() # Re-initialize observer for a clean state
            self.observer.moveToThread(self.watchdog_thread)
            self.observer.schedule(self.event_handler, self.monitored_path, recursive=False)
        except Exception as e:
            self.logger.error(f"Failed to schedule observer for {self.monitored_path}: {e}", exc_info=True)
            self.watchdog_thread.quit() # Clean up thread if schedule fails
            self.watchdog_thread.wait()
            return

        # Connect thread's started signal to observer's start method
        self.watchdog_thread.started.connect(self.observer.start)

        self.watchdog_thread.start()
        self.logger.info(f"Download monitoring service started for path: {self.monitored_path}")
        self.logger.info(f"Observer scheduled. Thread ID: {self.watchdog_thread.currentThreadId()}")


    def stop(self):
        self.logger.info("Attempting to stop download monitoring service...")
        if self.observer.is_alive():
            try:
                self.observer.stop()
                self.logger.info("Observer stop signal sent.")
            except Exception as e:
                self.logger.error(f"Error sending stop to observer: {e}", exc_info=True)

        if self.watchdog_thread is not None and self.watchdog_thread.isRunning():
            try:
                if self.observer.is_alive(): # Check again, might have stopped quickly
                    self.observer.join(timeout=2) # Wait for the observer thread to finish
                    if self.observer.is_alive():
                        self.logger.warning("Observer thread did not join in time.")
                    else:
                        self.logger.info("Observer thread joined.")

                self.watchdog_thread.quit()
                self.logger.info("QThread quit signal sent.")
                if not self.watchdog_thread.wait(3000): # Wait for 3 seconds
                    self.logger.warning("Watchdog QThread did not terminate gracefully. Forcing termination (not ideal).")
                    # self.watchdog_thread.terminate() # Use with caution
                else:
                    self.logger.info("Watchdog QThread terminated successfully.")
            except Exception as e:
                self.logger.error(f"Error during thread cleanup: {e}", exc_info=True)
        else:
            self.logger.info("Service was not running or thread already stopped.")

        self.watchdog_thread = None # Clear the thread reference
        # Re-initialize observer for potential restart, ensure it's not in a stopped state from previous run
        self.observer = Observer()
        self.logger.info("Download monitoring service stopped.")

if __name__ == '__main__':
    # This is a simple test script to run the service.
    # In a real application, this service would be managed by the main GUI.
    from PyQt5.QtCore import QCoreApplication
    import sys

    app = QCoreApplication(sys.argv)

    # Create a dummy downloads folder for testing
    test_download_dir = "test_downloads"
    if not os.path.exists(test_download_dir):
        os.makedirs(test_download_dir)

    abs_test_download_dir = os.path.abspath(test_download_dir)
    print(f"Monitoring directory: {abs_test_download_dir}")

    monitor_service = DownloadMonitorService(monitored_path=abs_test_download_dir)

    def on_new_file(path):
        print(f"MAIN APP SIGNAL: New document detected by service: {path}")

    monitor_service.new_document_detected.connect(on_new_file)
    monitor_service.start()

    print(f"Service started. Create files in '{abs_test_download_dir}' to test.")
    print("Common temporary files (.crdownload, .part, .tmp, ~$name.xlsx) should be ignored.")
    print("Ctrl+C to stop.")

    try:
        # Keep the application running
        # In a real GUI app, app.exec_() would handle this.
        # For this console test, we'll loop until Ctrl+C.
        while True:
            time.sleep(1)
            # Example: create a test file after some time
            # if int(time.time()) % 30 == 0 :
            #     with open(os.path.join(abs_test_download_dir, f"testfile_{int(time.time())}.txt"), "w") as f:
            #         f.write("Test content")
            #     time.sleep(1) # avoid re-triggering immediately

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Stopping service...")
    finally:
        monitor_service.stop()
        print("Service stopped. Exiting.")
        # Clean up dummy directory (optional)
        # import shutil
        # shutil.rmtree(test_download_dir)
        # print(f"Cleaned up {test_download_dir}")

    sys.exit() # Not strictly necessary for QCoreApplication if no event loop started
