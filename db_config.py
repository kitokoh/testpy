import os

# --- Database Configuration ---
DATABASE_NAME = "app_data.db" # Keep the original DB name
# APP_ROOT_DIR_CONTEXT should point to the directory containing this db_config.py file.
# If db_config.py is in the root of the application (/app), this is correct.
APP_ROOT_DIR_CONTEXT = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(APP_ROOT_DIR_CONTEXT, DATABASE_NAME)

# --- Logo Configuration ---
# Assuming logos are stored in a subdirectory within the app's root directory
LOGO_SUBDIR_CONTEXT = "company_logos"  # Subdirectory name for logos, matches original db.py
LOGO_DIR_PATH = os.path.join(APP_ROOT_DIR_CONTEXT, LOGO_SUBDIR_CONTEXT)

# Ensure the logo directory exists (moved from original db.py's initialize_database)
# This is more of an application setup task, but placing it here for now as it was in db.py
# A separate app_setup.py might be better for this.
if not os.path.exists(LOGO_DIR_PATH):
    os.makedirs(LOGO_DIR_PATH, exist_ok=True)

# --- Default User Configuration (for initial seeding) ---
DEFAULT_ADMIN_USERNAME = "admin"
# In a real app, use a more secure default, an environment variable, or prompt user during setup.
DEFAULT_ADMIN_PASSWORD = "adminpassword" # Changed from "admin_password" to match original db.py seeding logic

# --- Partner Documents Configuration ---
PARTNERS_DOCUMENTS_DIR = os.path.join(APP_ROOT_DIR_CONTEXT, "partners_documents")

# --- Other Configurations (Add as needed) ---
# Example:
# API_KEY = "your_api_key_here"
# DEBUG_MODE = True

# print(f"Database will be located at: {DATABASE_PATH}")
# print(f"Logo directory is: {LOGO_DIR_PATH}")
# print(f"Default admin username for seeding: {DEFAULT_ADMIN_USERNAME}")
