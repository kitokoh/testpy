# -*- coding: utf-8 -*-
import sys
import os
import logging # For main.py's own logging needs, and for translator parts if setup_logging isn't called first

# Core PyQt5 imports for application execution
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QLocale, QLibraryInfo, QTranslator, Qt
from PyQt5.QtGui import QFont

# Imports from project structure
from app_setup import (
    APP_ROOT_DIR, CONFIG,
    setup_logging, load_stylesheet_global, initialize_default_templates
)
from utils import is_first_launch, mark_initial_setup_complete
# Import InitialSetupDialog and PromptCompanyInfoDialog
from initial_setup_dialog import InitialSetupDialog, PromptCompanyInfoDialog
from PyQt5.QtWidgets import QDialog # Required for QDialog.Accepted check
# Import specific db functions needed
import db as db_manager
from db import get_all_companies, add_company # Specific imports for company check
from auth.login_window import LoginWindow # Added for authentication
from PyQt5.QtWidgets import QDialog # Required for QDialog.Accepted check (already present, but good to note)
# from initial_setup_dialog import InitialSetupDialog # Redundant import, already imported above
# import db as db_manager # For db initialization - already imported above
from main_window import DocumentManager # The main application window

import datetime # Added for session timeout
from PyQt5.QtCore import QSettings # Added for Remember Me

# Global variables for session information
CURRENT_SESSION_TOKEN = None
CURRENT_USER_ROLE = None
CURRENT_USER_ID = None
SESSION_START_TIME = None
# Initialize from CONFIG, providing a default if key is missing
SESSION_TIMEOUT_SECONDS = CONFIG.get("session_timeout_minutes", 30) * 60

# Initialize the central database using db_manager.
# This should be called once, early in the application startup,
# before any operations that might require the database.
# Placing it under `if __name__ == "__main__":` ensures it runs when script is executed directly.
# And before the main function that might use it.
if __name__ == "__main__" or not hasattr(db_manager, '_initialized_main_app_main_py'):
    # Using a unique attribute to avoid conflict if db_manager is imported and checked elsewhere
    db_manager.initialize_database()
    if __name__ != "__main__": # For import scenarios (e.g. testing)
        db_manager._initialized_main_app_main_py = True

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
    language_code = CONFIG.get("language", QLocale.system().name().split('_')[0])
    
    translator = QTranslator()
    translation_path_app = os.path.join(APP_ROOT_DIR, "translations", f"app_{language_code}.qm")
    if translator.load(translation_path_app):
        app.installTranslator(translator)
        logging.info(f"Loaded custom translation for {language_code} from {translation_path_app}")
    else:
        logging.warning(f"Failed to load custom translation for {language_code} from {translation_path_app}")

    qt_translator = QTranslator()
    # Use QLibraryInfo.location(QLibraryInfo.TranslationsPath) for Qt base translations
    qt_translation_path_base = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    if qt_translator.load(QLocale(language_code), "qtbase", "_", qt_translation_path_base):
        app.installTranslator(qt_translator)
        logging.info(f"Loaded Qt base translations for {language_code} from {qt_translation_path_base}")
    else:
        logging.warning(f"Failed to load Qt base translations for {language_code} from {qt_translation_path_base}")

    # 9. Initialize Default Templates (after DB and CONFIG are ready)
    # initialize_default_templates is imported from app_setup
    initialize_default_templates(CONFIG, APP_ROOT_DIR)

    # --- Startup Dialog Logic ---
    # Default paths for templates and clients, used by is_first_launch and mark_initial_setup_complete
    default_templates_dir = os.path.join(APP_ROOT_DIR, "templates")
    default_clients_dir = os.path.join(APP_ROOT_DIR, "clients")
    if 'templates_dir' in CONFIG:
        default_templates_dir = CONFIG['templates_dir']
    if 'clients_dir' in CONFIG:
        default_clients_dir = CONFIG['clients_dir']

    if is_first_launch(APP_ROOT_DIR, default_templates_dir, default_clients_dir):
        logging.info("Application detected first launch. Executing InitialSetupDialog.")
        initial_setup_dialog = InitialSetupDialog()
        result = initial_setup_dialog.exec_()

        if result == QDialog.Accepted:
            logging.info("InitialSetupDialog accepted by user.")
            mark_initial_setup_complete(APP_ROOT_DIR, default_templates_dir, default_clients_dir)
            logging.info("Initial setup marked as complete.")
            # After initial setup, also prompt for company info if none exists,
            # as InitialSetupDialog doesn't handle company creation.
            try:
                companies = get_all_companies()
                if not companies:
                    logging.info("No companies found after initial setup. Prompting for company information.")
                    prompt_dialog = PromptCompanyInfoDialog() # Consider if this dialog needs a parent
                    dialog_result_company = prompt_dialog.exec_()
                    if dialog_result_company == QDialog.Accepted:
                        if prompt_dialog.use_default_company:
                            logging.info("User opted to use a default company after initial setup.")
                            default_company_data = {
                                "company_name": "My Business",
                                "address": "Not specified",
                                "is_default": True,
                                "logo_path": None,
                                "payment_info": "",
                                "other_info": "Default company created post initial setup."
                            }
                            new_company_id = add_company(default_company_data)
                            if new_company_id:
                                logging.info(f"Default company 'My Business' added with ID: {new_company_id}.")
                            else:
                                logging.error("Failed to add default company post initial setup.")
                        else: # User entered data
                            user_company_data = prompt_dialog.get_company_data()
                            if user_company_data and user_company_data['company_name']:
                                company_to_add = {
                                    "company_name": user_company_data['company_name'],
                                    "address": user_company_data.get('address', ''),
                                    "is_default": True,
                                    "logo_path": None,
                                    "payment_info": "",
                                    "other_info": "Company created via prompt post initial setup."
                                }
                                new_company_id = add_company(company_to_add)
                                if new_company_id:
                                    logging.info(f"User-defined company '{company_to_add['company_name']}' added with ID: {new_company_id}.")
                                else:
                                    logging.error(f"Failed to add user-defined company '{company_to_add['company_name']}' post initial setup.")
                            else:
                                logging.warning("Company prompt accepted, but no company name provided. No company added.")
                    else: # Dialog was cancelled
                        logging.warning("User cancelled company prompt after initial setup. Application may function without a company, or this might be handled later.")
                else: # Companies exist after initial setup (perhaps created by a previous partial setup)
                    logging.info("Companies found in the database after initial setup. No need to prompt for company info now.")
            except Exception as e:
                logging.critical(f"Error during company check/setup after InitialSetupDialog: {e}", exc_info=True)
        else:
            logging.warning("InitialSetupDialog cancelled or closed by user. Application may lack necessary configurations.")
            # Depending on policy, could exit here: QApplication.quit() or sys.exit(1)
    else: # Not the first launch
        logging.info("Application not on first launch. Checking for company existence.")
        try:
            companies = get_all_companies()
            if not companies:
                logging.info("No companies found in the database on a subsequent launch. Executing PromptCompanyInfoDialog.")
                prompt_dialog = PromptCompanyInfoDialog()
                dialog_result = prompt_dialog.exec_()

                if dialog_result == QDialog.Accepted:
                    if prompt_dialog.use_default_company:
                        logging.info("User opted to use a default company.")
                        default_company_data = {
                            "company_name": "My Business",
                            "address": "Not specified",
                            "is_default": True,
                            "logo_path": None,
                            "payment_info": "",
                            "other_info": "Default company created on subsequent launch."
                        }
                        new_company_id = add_company(default_company_data)
                        if new_company_id:
                            logging.info(f"Default company 'My Business' added with ID: {new_company_id}.")
                        else:
                            logging.error("Failed to add default company.")
                    else: # User entered data
                        user_company_data = prompt_dialog.get_company_data()
                        if user_company_data and user_company_data['company_name']:
                            company_to_add = {
                                "company_name": user_company_data['company_name'],
                                "address": user_company_data.get('address', ''),
                                "is_default": True,
                                "logo_path": None,
                                "payment_info": "",
                                "other_info": "Company created via prompt on subsequent launch."
                            }
                            new_company_id = add_company(company_to_add)
                            if new_company_id:
                                logging.info(f"User-defined company '{company_to_add['company_name']}' added with ID: {new_company_id}.")
                            else:
                                logging.error(f"Failed to add user-defined company: {company_to_add['company_name']}.")
                        else:
                            logging.warning("Save and Continue chosen, but company name was empty. No company added.")
                else: # Dialog was cancelled
                    logging.warning("User cancelled company prompt. Application might not function as expected without a company.")
            else:
                logging.info("Companies found in the database. No need to prompt for company info.")
        except Exception as e:
            logging.critical(f"Error during company check on a subsequent launch: {e}. Application may not function correctly.", exc_info=True)

    # 10. Authentication Flow
    settings = QSettings()
    remember_me_active = settings.value("auth/remember_me_active", False, type=bool)
    proceed_to_main_app = False

    if remember_me_active:
        logging.info("Found active 'Remember Me' flag.")
        stored_token = settings.value("auth/session_token", None)
        stored_user_id = settings.value("auth/user_id", None)
        stored_username = settings.value("auth/username", "Unknown") # Default for logging
        stored_user_role = settings.value("auth/user_role", None)

        if stored_token and stored_user_id and stored_user_role:
            logging.info(f"Attempting to restore session for user: {stored_username} (ID: {stored_user_id}) with stored token.")

            global CURRENT_SESSION_TOKEN, CURRENT_USER_ID, CURRENT_USER_ROLE, SESSION_START_TIME
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
            logging.info("Login failed or cancelled by user. Exiting application.")
            sys.exit()

    if proceed_to_main_app:
        main_window = DocumentManager(APP_ROOT_DIR)
        main_window.show()
        logging.info("Main window shown. Application is running.")
        sys.exit(app.exec_())
    else:
        # This path should ideally not be reached if logic is correct,
        # as either proceed_to_main_app is true or sys.exit() was called.
        logging.error("Fatal error in authentication flow. Application cannot start.")
        sys.exit(1)
    login_dialog = LoginWindow() # Create LoginWindow instance
    login_result = login_dialog.exec_() # Show login dialog modally

    if login_result == QDialog.Accepted:
        session_token = login_dialog.get_session_token()
        logged_in_user = login_dialog.get_current_user()

        CURRENT_SESSION_TOKEN = session_token
        if logged_in_user:
            CURRENT_USER_ROLE = logged_in_user.get('role')
            CURRENT_USER_ID = logged_in_user.get('user_id')
            # Set session start time
            SESSION_START_TIME = datetime.datetime.now()
            logging.info(f"Login successful. User: {logged_in_user.get('username')}, Role: {CURRENT_USER_ROLE}, Token: {CURRENT_SESSION_TOKEN}, Session started: {SESSION_START_TIME}")
        else:
            logging.error("Login reported successful, but no user data retrieved. Exiting.")
            sys.exit(1)

        # 11. Create and Show Main Window (only after successful login)
        # DocumentManager is imported from main_window
        # APP_ROOT_DIR is imported from app_setup
        main_window = DocumentManager(APP_ROOT_DIR) # Pass user_id and role if needed by DocumentManager
        main_window.show()
        logging.info("Main window shown. Application is running.")

        # 12. Execute Application
        sys.exit(app.exec_())
    else:
        logging.info("Login failed or cancelled. Exiting application.")
        sys.exit() # Exit if login is not successful


if __name__ == "__main__":
    main()