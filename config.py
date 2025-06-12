# config.py
import os

APP_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_NAME = "app_data.db" # Retain for reference or if basename is needed elsewhere
DATABASE_PATH = os.path.join(APP_ROOT_DIR, DATABASE_NAME)

MEDIA_FILES_DIR_NAME = "media_files"
MEDIA_FILES_BASE_PATH = os.path.join(APP_ROOT_DIR, MEDIA_FILES_DIR_NAME)

DEFAULT_DOWNLOAD_DIR_NAME = "downloaded_media"
DEFAULT_DOWNLOAD_PATH = os.path.join(APP_ROOT_DIR, DEFAULT_DOWNLOAD_DIR_NAME)
