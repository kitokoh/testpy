import logging
import os
from logging.handlers import RotatingFileHandler
from app_config import CONFIG

LOG_DIR = CONFIG.get("logs_dir", "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE_PATH = os.path.join(LOG_DIR, "app.log")

# Determine the log level from CONFIG, defaulting to INFO
log_level_str = CONFIG.get("log_level", "INFO").upper()
numeric_log_level = getattr(logging, log_level_str, logging.INFO)

# Basic configuration
logging.basicConfig(
    level=numeric_log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Get the root logger
logger = logging.getLogger()

# File handler
# Rotate logs: 10 MB per file, keep 5 backup files
file_handler = RotatingFileHandler(
    LOG_FILE_PATH, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
)
file_handler.setLevel(numeric_log_level)
file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s"
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler (optional, as basicConfig might already set one up)
# If basicConfig creates a default StreamHandler, we might get duplicate console logs.
# However, explicitly adding one gives more control if needed later.
# For now, let's rely on basicConfig's default console output.
# If duplicate logs appear, we can revisit this.

# Example of how to get a logger in other modules:
# import logging
# logger = logging.getLogger(__name__)
# logger.info("This is an info message.")

def get_logger(name):
    """
    Returns a logger instance with the specified name.
    This ensures that our custom formatting and handlers are used.
    """
    return logging.getLogger(name)

if __name__ == "__main__":
    # Test the logging setup
    test_logger = get_logger("logging_config_test")
    test_logger.debug("This is a debug message.")
    test_logger.info("This is an info message.")
    test_logger.warning("This is a warning message.")
    test_logger.error("This is an error message.")
    test_logger.critical("This is a critical message.")
    print(f"Logging configured. Log file: {LOG_FILE_PATH}")
    print(f"Log level set to: {log_level_str} ({numeric_log_level})")
    # Check if 'logs_dir' is in app_config.CONFIG
    if "logs_dir" not in CONFIG:
        print("Warning: 'logs_dir' not found in app_config.CONFIG. Defaulting to 'logs'.")
    if "log_level" not in CONFIG:
        print("Warning: 'log_level' not found in app_config.CONFIG. Defaulting to 'INFO'.")
