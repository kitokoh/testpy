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
import db as db_manager # For db initialization
from main_window import DocumentManager # The main application window

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


def main():
    # 1. Configure logging as the very first step.
    setup_logging()
    logging.info("Application starting...")

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
    """) # The # color: white; part for QListWidget::item:selected was commented out in original.

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
       
    # 10. Create and Show Main Window
    # DocumentManager is imported from main_window
    # APP_ROOT_DIR is imported from app_setup
    main_window = DocumentManager(APP_ROOT_DIR) 
    main_window.show()
    logging.info("Main window shown. Application is running.")

    # 11. Execute Application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
