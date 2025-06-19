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


class WatchdogThread(QThread):
    """Runs the watchdog observer in a separate thread."""
    def __init__(self, path_to_watch, event_handler, parent=None):
        super().__init__(parent)
        self.path_to_watch = path_to_watch
        self.event_handler = event_handler
        self.observer = Observer()
        self.logger = logging.getLogger(__name__ + ".WatchdogThread")

    def run(self):
        self.logger.info(f"WatchdogThread started for path: {self.path_to_watch}")
        try:
            self.observer.schedule(self.event_handler, self.path_to_watch, recursive=False)
            self.observer.start()
            self.logger.info("Observer started.")
            # Keep the thread alive while the observer is running
            while self.observer.is_alive():
                self.observer.join(timeout=1) # Check every second
        except Exception as e:
            self.logger.error(f"Error in WatchdogThread run: {e}", exc_info=True)
        finally:
            if self.observer.is_alive():
                self.observer.stop()
            self.observer.join() # Ensure it's fully stopped before thread exits
            self.logger.info("WatchdogThread finished.")

    def stop(self):
        self.logger.info("Stopping WatchdogThread observer...")
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join(timeout=5) # Wait for observer to stop
            if self.observer.is_alive():
                self.logger.warning("Observer did not stop gracefully after 5 seconds.")
            else:
                self.logger.info("Observer stopped.")
        else:
            self.logger.info("Observer was not alive.")


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
        self.event_handler = DownloadEventHandler(parent_service=self)
        self.worker_thread = None # Will hold the WatchdogThread instance
        self.logger = logging.getLogger(__name__ + ".DownloadMonitorService")

    def start(self):
        if not self.monitored_path or not os.path.isdir(self.monitored_path):
            self.logger.error(f"Monitored path does not exist or is invalid: {self.monitored_path}")
            return

        if self.worker_thread is not None and self.worker_thread.isRunning():
            self.logger.warning("Service already running.")
            return

        self.logger.info(f"Starting DownloadMonitorService for path: {self.monitored_path}")
        self.worker_thread = WatchdogThread(self.monitored_path, self.event_handler)
        self.worker_thread.start()
        self.logger.info(f"WatchdogThread started. Thread ID: {self.worker_thread.currentThreadId()}")


    def stop(self):
        self.logger.info("Attempting to stop download monitoring service...")
        if self.worker_thread is not None and self.worker_thread.isRunning():
            try:
                self.logger.info("Calling worker_thread.stop()...")
                self.worker_thread.stop() # Signal the observer to stop

                self.logger.info("Calling worker_thread.quit()...")
                self.worker_thread.quit() # Tell the QThread event loop to exit (if it had one, not strictly necessary for observer.join model)

                self.logger.info("Calling worker_thread.wait(5000)...")
                if not self.worker_thread.wait(5000): # Wait up to 5 seconds
                    self.logger.warning("WatchdogThread did not terminate gracefully. Forcing termination (not ideal).")
                    # self.worker_thread.terminate() # Use with caution
                else:
                    self.logger.info("WatchdogThread terminated successfully.")
            except Exception as e:
                self.logger.error(f"Error during WatchdogThread cleanup: {e}", exc_info=True)
        else:
            self.logger.info("Service was not running or worker_thread already stopped/None.")

        self.worker_thread = None # Clear the thread reference
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
