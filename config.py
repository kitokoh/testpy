import os

APP_ROOT_DIR_CONTEXT = os.path.abspath(os.path.dirname(__file__))
DATABASE_NAME = "app_data.db"
DATABASE_PATH = os.path.join(APP_ROOT_DIR_CONTEXT, DATABASE_NAME)
LOGO_SUBDIR_CONTEXT = "company_logos"

# For compatibility with existing code that might use APP_ROOT_DIR
APP_ROOT_DIR = APP_ROOT_DIR_CONTEXT

# Define other paths if they were used/expected from the old db.py or elsewhere
MEDIA_FILES_DIR_NAME = "media_files"
MEDIA_FILES_BASE_PATH = os.path.join(APP_ROOT_DIR_CONTEXT, MEDIA_FILES_DIR_NAME)

DEFAULT_DOWNLOAD_DIR_NAME = "downloaded_media"
DEFAULT_DOWNLOAD_PATH = os.path.join(APP_ROOT_DIR_CONTEXT, DEFAULT_DOWNLOAD_DIR_NAME)

# Example of another constant that might be useful, ensure it's added if needed by any module
# COMPANY_LOGOS_DIR = os.path.join(APP_ROOT_DIR_CONTEXT, LOGO_SUBDIR_CONTEXT)
