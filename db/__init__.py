import os
import sys

# Attempt to import db_config relative to the parent directory (app root)
try:
    from .. import db_config
except (ImportError, ValueError) as e1:
    # Fallback: if db is top-level or script is run from within db,
    # or if the relative import fails for other reasons,
    # try to add parent directory (app root) to sys.path and import directly.

    # Correctly get the /app directory (parent of current file's directory, which is db/)
    current_dir = os.path.dirname(os.path.abspath(__file__)) # This is /path/to/app/db
    app_dir = os.path.dirname(current_dir) # This should be /path/to/app

    if app_dir not in sys.path:
        sys.path.insert(0, app_dir) # Insert at the beginning for priority

    try:
        import db_config
    except ImportError as e2:
        # If db_config is still not found, create a fallback configuration.
        # This fallback is similar to what's in db/utils.py and db/schema.py
        print(f"CRITICAL: db_config.py not found after attempting path modifications from db/__init__.py. Error1: {e1}, Error2: {e2}. Using fallback DATABASE_PATH.")

        class db_config_fallback:
            # Determine a sensible fallback path. If APP_ROOT_DIR was set by app_setup.py,
            # that would be ideal. Here, we use app_dir calculated above.
            DATABASE_PATH = os.path.join(app_dir, "app_data_fallback_from_db_init.db")
            # Add other constants that might be expected by db_config users if necessary,
            # though for DATABASE_NAME, only DATABASE_PATH is crucial.
            APP_ROOT_DIR_CONTEXT = app_dir
            LOGO_SUBDIR_CONTEXT = "company_logos_fallback"
            DEFAULT_ADMIN_USERNAME = "admin_fallback_init"
            DEFAULT_ADMIN_PASSWORD = "password_fallback_init"

        db_config = db_config_fallback

# Now, DATABASE_NAME is assigned the value of DATABASE_PATH from the resolved db_config
DATABASE_NAME = db_config.DATABASE_PATH

# Optionally, to make other db_config attributes accessible via db.something
# you could do:
# DB_CONFIG = db_config
# Or expose specific items:
# APP_ROOT_DIR_CONTEXT = db_config.APP_ROOT_DIR_CONTEXT

# Clean up sys.path if it was modified by this script,
# though generally it's fine to leave it for the app's lifecycle.
# if app_dir in sys.path and 'e2' in locals(): # Only if fallback import was attempted
#    sys.path.remove(app_dir)
