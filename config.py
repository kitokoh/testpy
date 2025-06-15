import os

# --- Application Root ---
APP_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Database Settings ---
DATABASE_NAME = "app_data.db"
DATABASE_PATH = os.path.join(APP_ROOT_DIR, DATABASE_NAME)

# --- Default Admin User Settings (for initial seeding) ---
DEFAULT_ADMIN_USERNAME = "admin"
# For production, ensure DEFAULT_ADMIN_PASSWORD environment variable is set to a strong, unique password.
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "adminpassword_dev_fallback")

# --- Path Settings ---
LOGO_SUBDIR = "company_logos"
LOGO_DIR_PATH = os.path.join(APP_ROOT_DIR, LOGO_SUBDIR)

PARTNERS_DOCUMENTS_SUBDIR = "partners_documents"
PARTNERS_DOCUMENTS_DIR = os.path.join(APP_ROOT_DIR, PARTNERS_DOCUMENTS_SUBDIR)

MEDIA_FILES_SUBDIR = "media_files" # Changed from MEDIA_FILES_DIR_NAME to match new var name
MEDIA_FILES_BASE_PATH = os.path.join(APP_ROOT_DIR, MEDIA_FILES_SUBDIR)

DEFAULT_DOWNLOAD_SUBDIR = "downloaded_media" # Changed from DEFAULT_DOWNLOAD_DIR_NAME
DEFAULT_DOWNLOAD_PATH = os.path.join(APP_ROOT_DIR, DEFAULT_DOWNLOAD_SUBDIR)

# Note: The os.makedirs(LOGO_DIR_PATH, exist_ok=True) line previously in db_config.py
# has been removed. This directory creation logic should be handled in app_setup.py
# or a similar application initialization script.

# --- API Specific Settings ---
# Example: API_SECRET_KEY = os.getenv("API_SECRET_KEY", "a_sEcReT_kEy_for_dev_only")
# (This is handled in api/auth.py, but could be centralized here if desired for other keys)

# print(f"Config loaded. Database Path: {DATABASE_PATH}")
# print(f"Root app dir: {APP_ROOT_DIR}")
