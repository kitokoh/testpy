# -*- coding: utf-8 -*-
import sys
import os

# Determine project root and add to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import logging # For main.py's own logging needs, and for translator parts if setup_logging isn't called first
import icons_rc # Import the compiled resource file
import subprocess # Added for starting API server
import atexit # Added for stopping API server on exit

# Core PyQt5 imports for application execution
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QLocale, QLibraryInfo, QTranslator, Qt
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import QStringListModel

# Imports from project structure
from app_setup import (
    APP_ROOT_DIR, CONFIG,
    setup_logging, load_stylesheet_global, initialize_default_templates
)
from utils import save_config # Changed import from app_config to utils
from utils import is_first_launch, mark_initial_setup_complete
from auth.roles import SUPER_ADMIN
# Import InitialSetupDialog and PromptCompanyInfoDialog
from initial_setup_dialog import InitialSetupDialog, PromptCompanyInfoDialog
from PyQt5.QtWidgets import QDialog # Required for QDialog.Accepted check
# Import specific db functions needed
import db # Added import for db module
from db.db_seed import run_seed
from db import get_all_companies, add_company # Specific imports for company check
# from db.cruds.application_settings_crud import get_setting # Removed direct import
# from db.init_schema import initialize_database # This will be db.initialize_database after this change
from auth.login_window import LoginWindow # Added for authentication
from PyQt5.QtWidgets import QDialog # Required for QDialog.Accepted check (already present, but good to note)
# from initial_setup_dialog import InitialSetupDialog # Redundant import, already imported above
# import db as db_manager # For db initialization - already imported above, now using 'import db'
from main_window import DocumentManager # The main application window
from notifications import NotificationManager # Added for notifications
from db.cruds.users_crud import users_crud_instance # Added for default operational user
from PyQt5.QtWidgets import QMessageBox # Added for error dialog
from PyQt5.QtWidgets import QSplashScreen

import datetime # Added for session timeout
from PyQt5.QtCore import QSettings # Added for Remember Me

# Global variables for session information
CURRENT_SESSION_TOKEN = None
CURRENT_USER_ROLE = None
CURRENT_USER_ID = None
SESSION_START_TIME = None
# Initialize from CONFIG, providing a default if key is missing
SESSION_TIMEOUT_SECONDS = CONFIG.get("session_timeout_minutes", 30) * 60

# Global variable for the API server process
api_server_process = None

# --- DEVELOPMENT/TESTING FLAG ---
# Set to True to bypass the login screen for faster testing.
# WARNING: This will log in as the default admin user with super_admin privileges
# and should ONLY be used for development/testing purposes.
# Ensure this is set to False for production or normal use.
BYPASS_LOGIN_FOR_TESTING = True
# --- End Development/Testing: Bypass Login Flag ---

# Old database initialization block removed as it's now called directly in main()

def start_api_server():
    """Starts the FastAPI server as a subprocess."""
    global api_server_process
    try:
        # Ensure the command is correctly formatted.
        # If 'api.main' is a module, uvicorn needs to be able to find it.
        # This might require adjusting PYTHONPATH or running from a specific directory.
        # For now, assume 'api.main:app' is discoverable by uvicorn in the current environment.
        command = ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

        # Using Popen for non-blocking execution.
        # Ensure that the subprocess's stdout/stderr are handled appropriately
        # to prevent blocking or deadlocks if they fill up.
        # For basic logging, we can capture them or redirect to DEVNULL if not needed.
        api_server_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Small delay to check if process started, then check poll()
        # This is a very basic check. A more robust check would involve
        # trying to connect to the server's health endpoint if available.
        # Or, monitoring its output for a startup confirmation message.
        # For now, we assume if Popen doesn't raise an error and poll() is None, it's starting.
        if api_server_process.poll() is None:
            logging.info(f"FastAPI server process started successfully with PID: {api_server_process.pid}. Command: {' '.join(command)}")
        else:
            # This means the process terminated quickly, likely an error.
            stdout, stderr = api_server_process.communicate() # Get output
            logging.error(f"FastAPI server process failed to start. Exit code: {api_server_process.returncode}")
            logging.error(f"Stdout: {stdout.decode().strip()}")
            logging.error(f"Stderr: {stderr.decode().strip()}")
            api_server_process = None # Reset as it failed

    except FileNotFoundError:
        logging.error("Error starting FastAPI server: 'uvicorn' command not found. Ensure uvicorn is installed and in PATH.")
        api_server_process = None
    except Exception as e:
        logging.error(f"An unexpected error occurred while starting the FastAPI server: {e}", exc_info=True)
        api_server_process = None

def stop_api_server():
    """Stops the FastAPI server process if it is running."""
    global api_server_process
    if api_server_process and api_server_process.poll() is None: # Check if process exists and is running
        logging.info(f"Attempting to terminate API server process with PID: {api_server_process.pid}")
        try:
            api_server_process.terminate() # Send SIGTERM
            try:
                # Wait for a few seconds for graceful shutdown
                api_server_process.wait(timeout=5)
                logging.info(f"API server process with PID: {api_server_process.pid} terminated.")
            except subprocess.TimeoutExpired:
                logging.warning(f"API server process with PID: {api_server_process.pid} did not terminate in time. Sending SIGKILL.")
                api_server_process.kill() # Send SIGKILL
                api_server_process.wait() # Wait for kill to complete
                logging.info(f"API server process with PID: {api_server_process.pid} killed.")
            except Exception as e_wait: # Catch other errors during wait (e.g. process already died)
                logging.info(f"Error waiting for API server process {api_server_process.pid} to terminate: {e_wait}. It might have already exited.")
        except ProcessLookupError: # Raised if process does not exist (e.g. already terminated)
            logging.info(f"API server process with PID: {api_server_process.pid} not found. Likely already stopped.")
        except Exception as e:
            logging.error(f"Error terminating/killing API server process with PID: {api_server_process.pid}: {e}", exc_info=True)
    elif api_server_process: # Process exists but poll() is not None, meaning it already terminated
        logging.info(f"API server process with PID: {api_server_process.pid} was already stopped (return code: {api_server_process.returncode}).")
    else: # api_server_process is None
        logging.info("No API server process to stop (api_server_process is None).")

def expire_session():
    global CURRENT_SESSION_TOKEN, CURRENT_USER_ROLE, CURRENT_USER_ID, SESSION_START_TIME
    CURRENT_SESSION_TOKEN = None
    CURRENT_USER_ROLE = None
    CURRENT_USER_ID = None
    SESSION_START_TIME = None
    logging.info("Session expired and token/user info cleared.")
    # In a real app, this would likely trigger a re-login UI flow.

def check_session_timeout() -> bool:
    """Checks if the current session has timed out. Returns True if timed out, False otherwise."""
    global CURRENT_SESSION_TOKEN, SESSION_START_TIME, SESSION_TIMEOUT_SECONDS
    if CURRENT_SESSION_TOKEN is None or SESSION_START_TIME is None:
        # No active session or session already marked as expired
        return False # Not "timed out now", but "no valid session"

    elapsed_time = datetime.datetime.now() - SESSION_START_TIME
    if elapsed_time.total_seconds() > SESSION_TIMEOUT_SECONDS:
        logging.info(f"Session timed out. Elapsed: {elapsed_time.total_seconds()}s, Timeout: {SESSION_TIMEOUT_SECONDS}s")
        expire_session()
        return True # Session has timed out
    return False # Session is still valid

def main():
    global CURRENT_SESSION_TOKEN, CURRENT_USER_ROLE, CURRENT_USER_ID, SESSION_START_TIME

    # 1. Configure logging as the very first step.
    setup_logging()
    logging.info("Application starting...")

    # Start the API server
    start_api_server()

    # Register the function to stop the API server on application exit
    # This ensures that if start_api_server() actually started a process,
    # we attempt to clean it up.
    atexit.register(stop_api_server)

    # Initialize database after logging and API server start attempt
    db.initialize_database()
    # Log the configured session timeout value
    logging.info(f"Session timeout is set to: {SESSION_TIMEOUT_SECONDS // 60} minutes ({SESSION_TIMEOUT_SECONDS} seconds).")

    # 2. Initialize Database (already done outside main for direct script execution,
    #    but if main could be called from elsewhere without the above block, ensure it's done)
    #    However, the current structure with the top-level if __name__ == "__main__" handles this.

    # 3. Set High DPI Scaling Attributes
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 4. Create QApplication Instance
    app = QApplication(sys.argv)

    # Display Splash Screen
    splash_pix = QPixmap(os.path.join(APP_ROOT_DIR, "icons", "leopard_logo.svg"))
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    splash.show()
    app.processEvents() # Ensure splash screen is displayed promptly

    # 5. Set Application Name and Style
    app.setApplicationName("ClientDocManager")
    app.setOrganizationName("SaadiyaManagement") # Added for QSettings consistency
    app.setStyle("Fusion") # Or any other style like "Windows", "GTK+"

    # 6. Set Default Font
    default_font = QFont("Segoe UI", 9)  # Default for Windows
    if sys.platform != "win32":  # Basic platform check for font
        default_font = QFont("Arial", 10) # Or "Helvetica", "DejaVu Sans" etc. for other platforms
    app.setFont(default_font)

    # 7. Load Global Stylesheet
    # load_stylesheet_global is imported from app_setup
    load_stylesheet_global(app) 
    
    # Apply the basic QSS stylesheet (this was the one previously embedded)
    # This can be moved to style.qss and loaded by load_stylesheet_global if preferred.
    app.setStyleSheet("""
        QWidget {}
        QPushButton {
            padding: 6px 12px; border: 1px solid #cccccc; border-radius: 4px;
        background-color: #f8f9fa; min-width: 80px;
        }
        QPushButton:hover { background-color: #e9ecef; border-color: #adb5bd; }
        QPushButton:pressed { background-color: #dee2e6; border-color: #adb5bd; }
        QPushButton:disabled { background-color: #e9ecef; color: #6c757d; border-color: #ced4da; }
        QPushButton#primaryButton, QPushButton[primary="true"] {
            background-color: #007bff; color: white; border-color: #007bff;
        }
        QPushButton#primaryButton:hover, QPushButton[primary="true"]:hover {
            background-color: #0069d9; border-color: #0062cc;
        }
        QPushButton#primaryButton:pressed, QPushButton[primary="true"]:pressed {
            background-color: #005cbf; border-color: #005cbf;
        }
        QPushButton#dangerButton, QPushButton[danger="true"] {
            background-color: #dc3545; color: white; border-color: #dc3545;
        }
        QPushButton#dangerButton:hover, QPushButton[danger="true"]:hover {
            background-color: #c82333; border-color: #bd2130;
        }
        QPushButton#dangerButton:pressed, QPushButton[danger="true"]:pressed {
            background-color: #b21f2d; border-color: #b21f2d;
        }
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            padding: 5px; border: 1px solid #ced4da; border-radius: 4px;
        }
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border-color: #80bdff;
        }
        QGroupBox {
            font-weight: bold; border: 1px solid #ced4da; border-radius: 4px;
            margin-top: 10px; padding: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin; subcontrol-position: top left;
            padding: 0 3px 0 3px; left: 10px; background-color: transparent;
        }
        QTabWidget::pane { border-top: 1px solid #ced4da; padding: 10px; }
        QTabBar::tab {
            padding: 8px 15px; border: 1px solid #ced4da; border-bottom: none;
            border-top-left-radius: 4px; border-top-right-radius: 4px;
            background-color: #e9ecef; margin-right: 2px;
        }
        QTabBar::tab:selected { background-color: #ffffff; border-color: #ced4da; }
        QTabBar::tab:hover:!selected { background-color: #f8f9fa; }
        QTableWidget {
            border: 1px solid #dee2e6; gridline-color: #dee2e6;
            alternate-background-color: #f8f9fa;
        }
        QHeaderView::section {
            background-color: #e9ecef; padding: 4px; border: 1px solid #dee2e6;
            font-weight: bold;
        }
        QListWidget { border: 1px solid #ced4da; border-radius: 4px; }
        QListWidget::item { padding: 5px; }
        QListWidget::item:alternate { background-color: #f8f9fa; }
        QListWidget::item:hover { background-color: #e9ecef; }
        QListWidget::item:selected { background-color: #007bff; /* color: white; */ }
    # """) # The # color: white; part for QListWidget::item:selected was commented out in original.

    # 8. Setup Translations
    # Try to get language from DB settings
    # 8. Setup Translations
    language_code_from_db = db.get_setting('user_selected_language') # Use db.get_setting

    if language_code_from_db and isinstance(language_code_from_db, str) and language_code_from_db.strip():
        language_code = language_code_from_db.strip()
        logging.info(f"Language '{language_code}' loaded from database setting.")
    else:
        default_lang = QLocale.system().name().split('_')[0]
        language_code = CONFIG.get("language", default_lang if default_lang in ["en", "fr"] else "en") # Fallback to 'en' if system lang not supported
        if language_code_from_db is None:
            logging.info(f"Language '{language_code}' loaded from config/system locale (DB setting 'user_selected_language' not found).")
        else: # Empty string or not a string
            logging.warning(f"Language '{language_code}' loaded from config/system locale (DB setting 'user_selected_language' was invalid: '{language_code_from_db}'). Defaulting to '{language_code}'.")

    # Load application translations
    # First, try to load from the language-specific directory (e.g., translations/qm/fr/main.qm)
    app_translator = QTranslator()
    translation_filename = "main.qm" # Assuming your QM file is named main.qm
    lang_spec_translation_path = os.path.join(APP_ROOT_DIR, "translations", "qm", language_code, translation_filename)

    if os.path.exists(lang_spec_translation_path):
        if app_translator.load(lang_spec_translation_path):
            app.installTranslator(app_translator)
            logging.info(f"Successfully loaded and installed application translation: {lang_spec_translation_path}")
        else:
            logging.warning(f"Failed to load application translation from {lang_spec_translation_path}. Error: {app_translator.errorString()}")
    else:
        # Fallback to loading from the general qm directory (e.g., translations/qm/fr.qm or en.qm)
        # This might be useful if you don't use subdirectories per language for qm files.
        # However, current structure implies subdirectories.
        logging.warning(f"Application translation file not found at specific path: {lang_spec_translation_path}. Trying general path if applicable or skipping.")
        # Example of a more general path (adjust if your structure is different):
        # general_translation_path = os.path.join(APP_ROOT_DIR, "translations", "qm", f"{language_code}.qm")
        # if os.path.exists(general_translation_path):
        #    if app_translator.load(general_translation_path):
        #        app.installTranslator(app_translator)
        #        logging.info(f"Successfully loaded and installed application translation from general path: {general_translation_path}")
        #    else:
        #        logging.warning(f"Failed to load application translation from general path {general_translation_path}. Error: {app_translator.errorString()}")
        # else:
        #    logging.warning(f"No application translation file found for language '{language_code}'.")


    # Load Qt base translations
    qt_translator = QTranslator()
    qt_translation_path_base = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    if qt_translator.load(QLocale(language_code), "qtbase", "_", qt_translation_path_base):
        app.installTranslator(qt_translator)
        logging.info(f"Loaded Qt base translations for {language_code} from {qt_translation_path_base}")
    else:
        # Try a more generic locale if the specific one (e.g., fr_FR) fails
        generic_locale_name = language_code.split('_')[0]
        if generic_locale_name != language_code: # Avoid redundant logging if already generic
            logging.info(f"Trying generic Qt base translations for {generic_locale_name} from {qt_translation_path_base}")
            if qt_translator.load(QLocale(generic_locale_name), "qtbase", "_", qt_translation_path_base):
                app.installTranslator(qt_translator)
                logging.info(f"Loaded generic Qt base translations for {generic_locale_name} from {qt_translation_path_base}")
            else:
                logging.warning(f"Failed to load Qt base translations for {language_code} or {generic_locale_name} from {qt_translation_path_base}")
        else:
            logging.warning(f"Failed to load Qt base translations for {language_code} from {qt_translation_path_base}")

    # 9. Initialize Default Templates (after DB and CONFIG are ready)
    # initialize_default_templates is imported from app_setup
    # This function is now responsible for ensuring default template FILES (Excel, general HTML) exist on disk.
    # Database seeding for templates is handled by db_manager.seed_initial_data.
    initialize_default_templates(CONFIG, APP_ROOT_DIR)
    logging.info("Call to app_setup.initialize_default_templates completed (ensures template files on disk).")

    # --- Coordinated Data Seeding ---
    # This block handles the seeding of initial data after the schema is created,
    # using the dedicated seeding module.
    try:
        logging.info("Attempting to run data seeding if necessary...")
        run_seed() # Call the main seeding function from db_seed.py
        # run_seed() handles its own connection, commit, rollback, and logging.
        logging.info("Data seeding process via run_seed() completed.")
    except Exception as e_seed_run:
        # Catch any unexpected error from run_seed() itself, though it should handle its own.
        logging.error(f"An unexpected error occurred when calling run_seed(): {e_seed_run}", exc_info=True)
    # --- End Coordinated Data Seeding ---

    # --- Startup Dialog Logic ---
    show_setup_prompt_config_value = CONFIG.get("show_initial_setup_on_startup", False)
    # Use CONFIG for directory paths in is_first_launch
    first_launch_detected = is_first_launch(APP_ROOT_DIR, CONFIG.get('templates_dir'), CONFIG.get('clients_dir'))
    companies_exist = bool(db.get_all_companies()) # Check once

    should_reset_config_flag_after_dialog = False

    if first_launch_detected:
        logging.info("Application detected first launch. Executing InitialSetupDialog.")
        # initial_setup_dialog = InitialSetupDialog()
        # result = initial_setup_dialog.exec_()
        # if result == QDialog.Accepted:
        #     # Use CONFIG for directory paths in mark_initial_setup_complete
        #     mark_initial_setup_complete(APP_ROOT_DIR, CONFIG.get('templates_dir'), CONFIG.get('clients_dir'))
        #     logging.info("Initial setup marked as complete.")
        #     companies_exist = bool(db.get_all_companies()) # Re-check companies after setup
        # else:
        #     logging.warning("InitialSetupDialog cancelled. Application may lack configurations.")
        #     # Potentially exit or show critical error if setup is vital

    # Now, handle the PromptCompanyInfoDialog based on company existence and the flag
    if not companies_exist:
        if first_launch_detected or show_setup_prompt_config_value: # Show if first launch OR if flag is true
            logging.info("No companies found or setup prompt explicitly enabled. Prompting for company information.")
            # prompt_dialog = PromptCompanyInfoDialog()
            # dialog_result_company = prompt_dialog.exec_()

            # if dialog_result_company == QDialog.Accepted:
            # Simulate dialog acceptance to proceed with default company creation if logic expects it
            dialog_result_company = QDialog.Accepted # SIMULATED ACCEPTANCE
            prompt_dialog = type('obj', (object,), {'use_default_company': True, 'get_company_data': lambda: None})() # SIMULATED DIALOG

            if dialog_result_company == QDialog.Accepted:
                if prompt_dialog.use_default_company:
                    logging.info("User opted to use a default company.")
                    default_company_data = {
                        "company_name": "My Business", "address": "Not specified", "is_default": True,
                        "logo_path": None, "payment_info": "", "other_info": "Default company created."
                    }
                    new_company_id = add_company(default_company_data)
                    if new_company_id:
                        logging.info(f"Default company 'My Business' added with ID: {new_company_id}.")
                        companies_exist = True # Update companies_exist status
                    else:
                        logging.error("Failed to add default company.")
                else: # User entered data
                    user_company_data = prompt_dialog.get_company_data()
                    if user_company_data and user_company_data['company_name']:
                        company_to_add = {
                            "company_name": user_company_data['company_name'],
                            "address": user_company_data.get('address', ''), "is_default": True,
                            "logo_path": None, "payment_info": "", "other_info": "Company created via prompt."
                        }
                        new_company_id = add_company(company_to_add)
                        if new_company_id:
                            logging.info(f"User-defined company '{company_to_add['company_name']}' added with ID: {new_company_id}.")
                            companies_exist = True # Update companies_exist status
                        else:
                            logging.error(f"Failed to add user-defined company '{company_to_add['company_name']}'.")
                    else:
                        logging.warning("Company prompt accepted, but no company name provided. No company added.")
            else: # Dialog was cancelled
                logging.warning("User cancelled company prompt.")

            # If the prompt was shown because of the config flag (and not strictly first_launch path that also sets it)
            if show_setup_prompt_config_value and not first_launch_detected:
                should_reset_config_flag_after_dialog = True
        else:
            logging.info("No companies found, but setup prompt is not enabled by config and not first launch. Skipping company prompt.")
    else: # Companies exist
        logging.info("Companies found in the database. No need to prompt for company info now.")
        # If companies exist, but the flag was true, it implies the user wanted to see the prompt (even if not strictly necessary).
        # Reset it as the condition (no companies) for the prompt to be useful wasn't met, or it was already met.
        if show_setup_prompt_config_value:
             should_reset_config_flag_after_dialog = True


    if should_reset_config_flag_after_dialog:
        logging.info("Resetting 'show_initial_setup_on_startup' flag to False.")
        CONFIG["show_initial_setup_on_startup"] = False
        save_config(CONFIG)

    proceed_to_main_app = False # Initialize before bypass and remember me

    # --- Development/Testing: Bypass Login ---
    if BYPASS_LOGIN_FOR_TESTING:
        logging.warning("Login screen is being bypassed due to BYPASS_LOGIN_FOR_TESTING flag.")
        try:
            # Ensure db operations can be performed to get admin user
            from db.cruds.users_crud import users_crud_instance
            # from auth.roles import SUPER_ADMIN # Make sure SUPER_ADMIN is imported if not already (it is)

            admin_user = users_crud_instance.get_user_by_username("admin") # Assuming "admin" is the default admin username
            if admin_user:
                CURRENT_USER_ID = admin_user['user_id']
                CURRENT_USER_ROLE = SUPER_ADMIN # Assign super_admin role
                CURRENT_SESSION_TOKEN = "BYPASS_TOKEN_ADMIN_SUPER"
                SESSION_START_TIME = datetime.datetime.now()
                proceed_to_main_app = True # This sets it to True if bypass is successful
                logging.info(f"Bypassed login. Logged in as default admin: {admin_user['username']} (ID: {CURRENT_USER_ID}), Role: {CURRENT_USER_ROLE}")
            else:
                logging.error("BYPASS_LOGIN_FOR_TESTING: Could not find default admin user 'admin'. Login cannot be bypassed.")
                # proceed_to_main_app will remain False, forcing normal login
        except Exception as e_bypass:
            logging.error(f"BYPASS_LOGIN_FOR_TESTING: Error during login bypass: {e_bypass}", exc_info=True)
            # proceed_to_main_app will remain False, normal login flow will occur.
    # --- End Development/Testing: Bypass Login ---

    # 10. Authentication Flow
    settings = QSettings()

    # Now check "Remember Me" ONLY if bypass did not occur
    if not proceed_to_main_app:
        remember_me_active = settings.value("auth/remember_me_active", False, type=bool)
        if remember_me_active:
            logging.info("Found active 'Remember Me' flag.")
            stored_token = settings.value("auth/session_token", None)
            stored_user_id = settings.value("auth/user_id", None)
            stored_username = settings.value("auth/username", "Unknown") # Default for logging
            stored_user_role = settings.value("auth/user_role", None)

            if stored_token and stored_user_id and stored_user_role:
                logging.info(f"Attempting to restore session for user: {stored_username} (ID: {stored_user_id}) with stored token.")

                # global CURRENT_SESSION_TOKEN, CURRENT_USER_ID, CURRENT_USER_ROLE, SESSION_START_TIME # Already global
                CURRENT_SESSION_TOKEN = stored_token
                CURRENT_USER_ID = stored_user_id
                CURRENT_USER_ROLE = stored_user_role
                SESSION_START_TIME = datetime.datetime.now() # Reset session timer

                logging.info(f"Session restored for user: {stored_username}, Role: {CURRENT_USER_ROLE}. Token: {CURRENT_SESSION_TOKEN}")
                logging.info(f"Session (restored) started at: {SESSION_START_TIME}")
                proceed_to_main_app = True
            else:
                logging.warning("Found 'Remember Me' flag but token or user details are missing. Clearing invalid 'Remember Me' data.")
                settings.setValue("auth/remember_me_active", False)
                settings.remove("auth/session_token")
                settings.remove("auth/user_id")
                settings.remove("auth/username")
                settings.remove("auth/user_role")
        else:
            logging.info("'Remember Me' is not active.")

    if not proceed_to_main_app:
        logging.info("Proceeding to show LoginWindow.")
        login_dialog = LoginWindow()
        login_result = login_dialog.exec_()

        if login_result == QDialog.Accepted:
            session_token = login_dialog.get_session_token()
            logged_in_user = login_dialog.get_current_user()

            # global CURRENT_SESSION_TOKEN, CURRENT_USER_ROLE, CURRENT_USER_ID, SESSION_START_TIME # Already global
            CURRENT_SESSION_TOKEN = session_token # These are assigned again here for clarity
            if logged_in_user:
                CURRENT_USER_ROLE = logged_in_user.get('role')
                CURRENT_USER_ID = logged_in_user.get('user_id')
                SESSION_START_TIME = datetime.datetime.now()
                logging.info(f"Login successful. User: {logged_in_user.get('username')}, Role: {CURRENT_USER_ROLE}, Token: {CURRENT_SESSION_TOKEN}, Session started: {SESSION_START_TIME}")
            else: # Should not happen if dialog.accept() is called correctly
                logging.error("Login reported successful by dialog, but no user data retrieved. Exiting.")
                sys.exit(1)
            proceed_to_main_app = True # Mark to proceed
        else:
            logging.warning("Login dialog was not accepted (failed, cancelled, or closed). Attempting to use default operational user.")
            DEFAULT_OPERATIONAL_USERNAME = "default_operational_user"
            try:
                # Assuming users_crud_instance does not require explicit connection management here
                # or it handles it internally for read-only operations like get_user_by_username.
                # If main.py initializes a global DB connection that CRUD instances can use, that's also fine.
                default_user = users_crud_instance.get_user_by_username(DEFAULT_OPERATIONAL_USERNAME)
                if default_user:
                    CURRENT_USER_ID = default_user.get('user_id')
                    CURRENT_USER_ROLE = default_user.get('role')
                    SESSION_START_TIME = datetime.datetime.now()
                    CURRENT_SESSION_TOKEN = "default_user_session_token" # Placeholder token
                    logging.info(f"Proceeding with default operational user: {DEFAULT_OPERATIONAL_USERNAME} (ID: {CURRENT_USER_ID}, Role: {CURRENT_USER_ROLE})")
                    proceed_to_main_app = True
                else:
                    logging.critical(f"Default operational user '{DEFAULT_OPERATIONAL_USERNAME}' not found in the database.")
                    QMessageBox.critical(None, "Critical Error", f"Default operational user profile ('{DEFAULT_OPERATIONAL_USERNAME}') not found. Application cannot start. Please contact support or run database seeding.")
                    sys.exit(1)
            except Exception as e_default_user:
                logging.critical(f"An error occurred while trying to fetch the default operational user '{DEFAULT_OPERATIONAL_USERNAME}': {e_default_user}", exc_info=True)
                QMessageBox.critical(None, "Critical Database Error", f"An error occurred while accessing user data. Application cannot start. Check logs for details.")
                sys.exit(1)

    if proceed_to_main_app:
        main_window = DocumentManager(APP_ROOT_DIR, CURRENT_USER_ID)

        # Setup Notification Manager
        # Ensure 'app' is the QApplication instance, available in this scope
        notification_manager = NotificationManager(parent_window=main_window)
        QApplication.instance().notification_manager = notification_manager

        main_window.show()
        splash.finish(main_window) # Close splash screen
        logging.info("Main window shown. Application is running.")
        sys.exit(app.exec_())
    else:
        # This path should ideally not be reached if logic is correct,
        # as either proceed_to_main_app is true or sys.exit() was called.
        logging.error("Fatal error in authentication flow. Application cannot start.")
        splash.hide() # Ensure splash screen is hidden on error
        sys.exit(1)

    # The following block seems redundant due to the logic above,
    # but if it's reached, ensure splash screen is handled.
    # Consider refactoring to avoid this redundancy.
    # login_dialog = LoginWindow() # Create LoginWindow instance
    # login_result = login_dialog.exec_() # Show login dialog modally
    #
    # if login_result == QDialog.Accepted:
    #     session_token = login_dialog.get_session_token()
    #     logged_in_user = login_dialog.get_current_user()
    #
    #     CURRENT_SESSION_TOKEN = session_token
    #     if logged_in_user:
    #         CURRENT_USER_ROLE = logged_in_user.get('role')
    #         CURRENT_USER_ID = logged_in_user.get('user_id')
    #         SESSION_START_TIME = datetime.datetime.now()
    #         logging.info(f"Login successful. User: {logged_in_user.get('username')}, Role: {CURRENT_USER_ROLE}, Token: {CURRENT_SESSION_TOKEN}, Session started: {SESSION_START_TIME}")
    #     else:
    #         logging.error("Login reported successful, but no user data retrieved. Exiting.")
    #         splash.hide()
    #         sys.exit(1)
    #
    #     main_window = DocumentManager(APP_ROOT_DIR, CURRENT_USER_ID)
    #     main_window.show()
    #     splash.finish(main_window)
    #     logging.info("Main window shown. Application is running.")
    #
    #     sys.exit(app.exec_())
    # else:
    #     logging.info("Login failed or cancelled. Exiting application.")
    #     splash.hide()
    #     sys.exit()

def get_notification_manager():
    """
    Global accessor for the NotificationManager instance.

    Returns:
        NotificationManager or None: The global NotificationManager instance if it has been set
                                     on the QApplication instance, otherwise None.
    """
    app_instance = QApplication.instance()
    if hasattr(app_instance, 'notification_manager'):
        return app_instance.notification_manager
    logging.warning("NotificationManager not found on QApplication instance.")
    return None

if __name__ == "__main__":
    main()