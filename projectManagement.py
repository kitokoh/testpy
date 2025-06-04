import sys
import sqlite3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QPushButton, QStackedWidget, QFrame, QSizePolicy,
                            QTableWidget, QTableWidgetItem, QComboBox, QDateEdit, QLineEdit,
                            QProgressBar, QTabWidget, QCheckBox, QMessageBox, QFileDialog,
                            QInputDialog, QFormLayout, QSpacerItem, QGroupBox)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap
import pyqtgraph as pg
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import hashlib
import os
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QSpinBox
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QDialogButtonBox
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtWidgets import QMenu
from PyQt5.QtCore import QSize
# Removed: from imports import DB_PATH_management
import db as main_db_manager
from db import get_status_setting_by_id, get_all_status_settings # For NotificationManager status checks

# Removed: class DatabaseManager and its methods (init_db, get_connection)
# All direct SQLite calls related to this class are implicitly removed.

class NotificationManager:
    def __init__(self, parent_window): # Removed db_manager argument
        self.parent_window = parent_window
        self.timer = QTimer(parent_window)

    def setup_timer(self, interval_ms=300000):  # Default 5 minutes
        self.timer.timeout.connect(self.check_notifications)
        self.timer.start(interval_ms)
        print(f"Notification timer started with interval: {interval_ms}ms") # For debugging

    def check_notifications(self):
        print(f"Checking notifications at {datetime.now()}") # For debugging
        notifications_found = []

        # Get all relevant statuses to avoid multiple DB calls for status properties
        all_project_statuses = {s['status_id']: s for s in get_all_status_settings(status_type='Project')}
        all_task_statuses = {s['status_id']: s for s in get_all_status_settings(status_type='Task')}

        try:
            all_projects = main_db_manager.get_all_projects()
            if all_projects is None: all_projects = []

            today_str = datetime.now().strftime('%Y-%m-%d')
            three_days_later = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')

            for p in all_projects:
                project_status_id = p.get('status_id')
                project_status_info = all_project_statuses.get(project_status_id, {})
                is_completed_or_archived = project_status_info.get('is_completion_status', False) or \
                                           project_status_info.get('is_archival_status', False)

                # Urgent Projects: priority = 2 (High)
                if p.get('priority') == 2 and not is_completed_or_archived:
                    notifications_found.append({
                        "title": "Urgent Project Reminder",
                        "message": f"Project '{p.get('project_name')}' (ID: {p.get('project_id')}) is high priority.",
                        "project_id": p.get('project_id')
                    })

                # Overdue Projects
                deadline_str = p.get('deadline_date')
                if deadline_str and deadline_str < today_str and not is_completed_or_archived:
                    notifications_found.append({
                        "title": "Overdue Project Alert",
                        "message": f"Project '{p.get('project_name')}' (ID: {p.get('project_id')}) was due on {deadline_str}.",
                        "project_id": p.get('project_id')
                    })

                # Tasks for this project
                tasks_for_project = main_db_manager.get_tasks_by_project_id(p.get('project_id'))
                if tasks_for_project is None: tasks_for_project = []

                for t in tasks_for_project:
                    task_status_id = t.get('status_id')
                    task_status_info = all_task_statuses.get(task_status_id, {})
                    is_task_completed = task_status_info.get('is_completion_status', False)
                    # Assuming tasks don't have 'archival' status, or add if they do.

                    task_deadline_str = t.get('due_date')

                    # Tasks Nearing Deadline (High Priority)
                    if t.get('priority') == 2 and not is_task_completed and \
                       task_deadline_str and today_str <= task_deadline_str <= three_days_later:
                        notifications_found.append({
                            "title": "High Priority Task Nearing Deadline",
                            "message": f"Task '{t.get('task_name')}' for project '{p.get('project_name')}' (Deadline: {task_deadline_str}) is high priority.",
                            "task_id": t.get('task_id')
                        })

                    # Overdue Tasks
                    if task_deadline_str and task_deadline_str < today_str and not is_task_completed:
                         notifications_found.append({
                            "title": "Overdue Task Alert",
                            "message": f"Task '{t.get('task_name')}' for project '{p.get('project_name')}' was due on {task_deadline_str}.",
                            "task_id": t.get('task_id')
                        })
        except Exception as e: # Catch generic Exception as db.py functions might raise various errors
            print(f"Error checking notifications: {e}")
            # Optionally show a subtle error to the user or log it more formally
            # self.show_notification("Notification System Error", f"Could not check for notifications: {e}")
            return # Stop processing if DB error

        if notifications_found:
            print(f"Found {len(notifications_found)} notifications.") # For debugging
            for notification in notifications_found:
                self.show_notification(
                    notification["title"],
                    notification["message"],
                    notification.get("project_id"),
                    notification.get("task_id")
                )
        else:
            print("No new notifications.") # For debugging


    def show_notification(self, title, message, project_id=None, task_id=None):
        # In a real application, you might want to make these notifications less intrusive
        # or allow users to click them to navigate to the item.
        # For now, a simple QMessageBox.
        print(f"Showing notification: {title} - {message}") # For debugging
        QMessageBox.information(self.parent_window, title, message)


class MainDashboard(QWidget): # Changed from QMainWindow to QWidget
    def __init__(self, parent=None, current_user=None): # Added current_user parameter
        super().__init__(parent)
        # self.parent = parent # parent is already handled by QWidget
        # self.db = DatabaseManager() # Removed
        self.current_user = current_user # Use passed-in user

        # self.setWindowTitle("Management Dashboard Pro") # Removed - main.py will handle title
        # self.setWindowIcon(QIcon(self.resource_path('icons/app_icon.png'))) # Removed
        # self.setGeometry(100, 100, 1400, 900) # Removed - main.py will handle geometry

        # Global style (can be kept if it's specific to this widget's content)
        # However, if main.py has global styles, this might be redundant or cause conflicts.
        # For now, let's keep it to maintain internal appearance.
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f7fa; /* Light gray background for the main widget */
                color: #333333; /* Default text color */
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px; /* Default font size */
            }
            QLabel {
                color: #333333;
                padding: 2px;
                font-size: 13px; /* Consistent with QWidget */
            }
            QLabel#logo_text_label { /* Specific for logo in topbar - handled by topbar's stylesheet */
                /* Styles moved to topbar stylesheet */
            }
            QLabel#user_name_label { /* Specific for user name in topbar - handled by topbar's stylesheet */
                 /* Styles moved to topbar stylesheet */
            }
            QLabel#user_role_label { /* Specific for user role in topbar - handled by topbar's stylesheet */
                 /* Styles moved to topbar stylesheet */
            }
             QLabel[font-weight="bold"] { /* Allow specific labels to be bold */
                font-weight: bold;
            }
            QPushButton {
                padding: 8px 15px; /* Standardized padding */
                font-size: 13px;
                border-radius: 4px;
                background-color: #e0e0e0; /* Default light gray */
                color: #333333;
                border: 1px solid #bdbdbd;
                min-height: 22px; /* Consistent min height for inputs/buttons */
            }
            QPushButton:hover {
                background-color: #d5d5d5;
            }
            QPushButton:pressed {
                background-color: #cccccc;
            }
            QPushButton#primary_action_button { /* Green for primary actions */
                background-color: #27ae60;
                color: white;
                border: none;
                font-weight: bold;
            }
            QPushButton#primary_action_button:hover {
                background-color: #219653;
            }
            QPushButton#primary_action_button:pressed {
                background-color: #1e8449;
            }
            QPushButton#standard_action_button { /* Blue for standard/general actions */
                 background-color: #3498db;
                 color: white;
                 border: none;
                 font-weight: 500; /* Medium weight */
            }
            QPushButton#standard_action_button:hover {
                 background-color: #2980b9;
            }
            QPushButton#standard_action_button:pressed {
                 background-color: #2372a3;
            }
            QPushButton#secondary_action_button { /* Red for destructive/warning actions */
                background-color: #e74c3c;
                color: white;
                border: none;
                font-weight: 500; /* Medium weight */
            }
            QPushButton#secondary_action_button:hover {
                background-color: #c0392b; /* Darker red on hover */
            }
            QPushButton#secondary_action_button:pressed {
                background-color: #a93226;
            }
            /* Icon-only buttons (used in tables, etc.) */
            QPushButton#icon_button {
                background-color: transparent;
                border: none;
                padding: 4px; /* Smaller padding for icon buttons */
                min-width: 28px; /* Adjust for icon size + padding */
                min-height: 28px;
            }
            QPushButton#icon_button:hover {
                background-color: #e0e0e0; /* Light highlight on hover */
            }
            QPushButton#icon_button:pressed {
                background-color: #cccccc;
            }
            QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit {
                padding: 8px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: #ffffff; /* White background for inputs */
                font-size: 13px;
                min-height: 22px; /* Consistent min height */
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
                border: 1px solid #3498db; /* Blue border on focus */
            }
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                gridline-color: #e0e0e0; /* Lighter grid lines */
                font-size: 13px;
                selection-background-color: #a8cce9; /* Light blue for selection */
                selection-color: #2c3e50; /* Dark text for selected items for contrast */
            }
            QHeaderView::section {
                background-color: #e9eef4; /* Light blue-gray for headers */
                color: #2c3e50; /* Dark text for header */
                padding: 10px 8px; /* Ample padding */
                font-weight: bold;
                font-size: 13px;
                border: none; /* Remove default border */
                border-bottom: 1px solid #d0d9e2; /* Subtle bottom border for separation */
            }
            QTableCornerButton::section { /* Style for the top-left corner button of the table */
                background-color: #e9eef4;
                border-bottom: 1px solid #d0d9e2;
                border-right: 1px solid #d0d9e2; /* Match header cell border */
            }
            QGroupBox {
                font-size: 16px; /* Slightly larger for group titles */
                font-weight: bold;
                color: #2c3e50; /* Dark blue/charcoal for title text */
                border: 1px solid #d0d9e2; /* Light border */
                border-radius: 6px;
                margin-top: 12px; /* Space above the group box */
                padding-top: 25px; /* Space for the title to sit above the content */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px; /* Padding around the title text */
                background-color: #f5f7fa; /* Match widget background so it looks cut-out */
                color: #3498db; /* Accent blue for the title text */
                font-size: 15px; /* Slightly smaller than groupbox font-size for visual hierarchy */
                left: 10px; /* Position from left */
            }
            QTabWidget::pane {
                border: 1px solid #d0d9e2;
                border-top: none; /* Pane border only on sides/bottom */
                border-radius: 0 0 5px 5px; /* Rounded bottom corners */
                padding: 15px; /* Padding inside the tab pane */
                background-color: #ffffff; /* White background for tab content area */
            }
            QTabBar::tab {
                padding: 10px 20px;
                background: #e9eef4; /* Light blue-gray, same as table headers */
                border: 1px solid #d0d9e2;
                border-bottom: none; /* No bottom border for inactive tabs */
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 2px;
                color: #555555; /* Medium gray for text */
                font-size: 13px;
                font-weight: 500; /* Medium weight */
            }
            QTabBar::tab:selected {
                background: #ffffff; /* White background for selected tab */
                color: #2c3e50; /* Dark text for selected tab */
                font-weight: bold;
                border-bottom: 1px solid #ffffff; /* Makes it look connected to the pane */
            }
            QTabBar::tab:hover {
                background: #f0f5fa; /* Slightly lighter on hover */
                color: #2c3e50;
            }
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                height: 20px; /* Slightly reduced height for compactness */
                color: #333333;
                background-color: #e0e0e0; /* Background of the progress bar track */
            }
            QProgressBar::chunk {
                background-color: #3498db; /* Blue for the progress chunk */
                border-radius: 4px;
                margin: 1px; /* Small margin for the chunk */
            }
            QScrollBar:horizontal {
                border: none;
                background: #e0e0e0;
                height: 10px;
                margin: 0px 20px 0 20px;
            }
            QScrollBar::handle:horizontal {
                background: #bdc3c7;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #e0e0e0;
                width: 10px;
                margin: 20px 0 20px 0;
            }
            QScrollBar::handle:vertical {
                background: #bdc3c7;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(10, 10, 10, 10)
        self._main_layout.setSpacing(0)

        self.init_ui() # Initialize UI components

        if self.current_user: # If user is passed, update UI and load data
            self.user_name.setText(self.current_user.get('full_name', "N/A"))
            self.user_role.setText(self.current_user.get('role', "N/A").capitalize())
            self.load_initial_data()
        else: # No user passed, potentially show internal login or a message
            self.user_name.setText("Guest (No User Context)")
            self.user_role.setText("Limited Functionality")
            # self.load_initial_data() # Data loading might fail or show empty if no user context

        # Notification System Initialization
        self.notification_manager = NotificationManager(self) # Pass self (MainDashboard) as parent
        self.notification_manager.setup_timer()

    def module_closed(self, module_id):
        """Clean up after module closure"""
        self.parent.modules[module_id] = None

    def resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    def init_ui(self):
        # central_widget is now self (the MainDashboard QWidget)
        # main_layout is self._main_layout, already set on self

        # Topbar (replaces sidebar)
        self.setup_topbar()
        self._main_layout.addWidget(self.topbar) # Add topbar to self._main_layout

        # Main content
        self.main_content = QStackedWidget()
        self.main_content.setStyleSheet("""
            QStackedWidget {
                background-color: #ffffff;
            }
        """)

        # Pages
        self.setup_dashboard_page()
        self.setup_team_page()
        self.setup_projects_page()
        self.setup_tasks_page()
        self.setup_reports_page()
        self.setup_settings_page()

        # Add main content below the topbar
        self._main_layout.addWidget(self.main_content) # Add main_content to self._main_layout

        # Status bar removed - self.statusBar().showMessage("Ready")

        # Check if user is logged in - Handled in __init__ now
        # if not self.current_user:
        #     # This might be shown if __init__ doesn't receive a user.
        #     # self.show_login_dialog()
        #     pass


    def setup_topbar(self):
        self.topbar = QFrame()
        self.topbar.setFixedHeight(60)
        self.topbar.setObjectName("topbar_frame")
        self.topbar.setStyleSheet("""
            QFrame#topbar_frame {
                background-color: #2c3e50; /* Dark blue/charcoal */
                border-bottom: 2px solid #3498db; /* Accent blue border */
            }
            /* General style for QPushButtons directly within the topbar QFrame */
            QFrame#topbar_frame > QPushButton {
                background-color: transparent;
                color: #ecf0f1; /* Light gray text */
                padding: 10px 15px;
                border: none;
                font-size: 14px;
                font-weight: 500;
                min-width: 100px;
                border-radius: 0px; /* Flat look */
            }
            QFrame#topbar_frame > QPushButton:hover {
                background-color: #34495e; /* Slightly lighter dark */
                color: #ffffff;
            }
            QFrame#topbar_frame > QPushButton:pressed {
                background-color: #233140; /* Darker shade when pressed */
            }
            QFrame#topbar_frame > QPushButton#selected { /* Specific style for the selected topbar button */
                background-color: #3498db; /* Accent blue */
                color: white;
                font-weight: bold;
                /* Optional: border-bottom: 3px solid #ffffff; White underline for selected */
            }
            /* Style for QLabels directly within the topbar QFrame */
            QFrame#topbar_frame > QLabel#logo_text_label {
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
                font-family: 'Segoe UI Light', Arial, sans-serif;
            }
            /* User info labels are inside a child QWidget, so direct child selector > won't work.
               Instead, we rely on object names if specific styling is needed beyond general QLabel styles from MainDashboard.
               If general QLabel styles are sufficient, these specific ones might not be needed here.
               For now, assuming they might need specific topbar context styling.
            */
            QLabel#user_name_label { /* For user name in topbar's user section */
                color: #ecf0f1;
                font-weight: bold;
                font-size: 13px;
            }
            QLabel#user_role_label { /* For user role in topbar's user section */
                color: #bdc3c7;
                font-size: 11px;
                font-style: italic;
            }
            /* Styling for QMenu associated with topbar buttons */
            QMenu {
                background-color: #34495e; /* Darker menu background */
                color: #ecf0f1; /* Light text */
                border: 1px solid #2c3e50; /* Border matching darker topbar elements */
                padding: 5px;
                font-size: 13px;
            }
            QMenu::item {
                padding: 8px 20px; /* Padding for menu items */
            }
            QMenu::item:selected {
                background-color: #3498db; /* Accent blue for selected menu item */
                color: white;
            }
            QMenu::icon {
                padding-left: 5px; /* Space for icons in menu items */
            }
            QMenu::separator {
                height: 1px;
                background: #2c3e50; /* Dark separator */
                margin-left: 10px;
                margin-right: 5px;
            }
        """)

        topbar_layout = QHBoxLayout(self.topbar)
        topbar_layout.setContentsMargins(15, 5, 15, 5)
        topbar_layout.setSpacing(10)

        # Logo and title - Left side
        logo_container = QHBoxLayout()
        logo_container.setSpacing(8)

        logo_icon = QLabel()
        logo_icon.setPixmap(QIcon(self.resource_path('icons/logo.png')).pixmap(32, 32))

        logo_text = QLabel("Management Pro")
        logo_text.setObjectName("logo_text_label")

        logo_container.addWidget(logo_icon)
        logo_container.addWidget(logo_text)
        topbar_layout.addLayout(logo_container)

        # Central space for menus
        topbar_layout.addStretch(1)

        # Main Menu - Center
        self.nav_buttons = []

        # Dashboard button (single)
        dashboard_btn = QPushButton("Dashboard")
        dashboard_btn.setObjectName("topbar_button")
        dashboard_btn.setIcon(QIcon(self.resource_path('icons/dashboard.png')))
        dashboard_btn.clicked.connect(lambda: self.change_page(0))
        self.nav_buttons.append(dashboard_btn)
        topbar_layout.addWidget(dashboard_btn)

        # Management Menu (Team + Settings)
        management_menu = QMenu()
        management_menu.addAction(
            QIcon(self.resource_path('icons/team.png')),
            "Team",
            lambda: self.change_page(1)
        )
        management_menu.addAction(
            QIcon(self.resource_path('icons/settings.png')),
            "Settings",
            lambda: self.change_page(5)
        )

        management_menu.addAction(
            QIcon(self.resource_path('icons/settings.png')),
            "Notifications",
            lambda: self.gestion_notification()
        )
        management_menu.addAction(
            QIcon(self.resource_path('icons/settings.png')),
            "Client Support",
            lambda: self.gestion_sav()
        )
        management_menu.addAction(
            QIcon(self.resource_path('icons/settings.png')),
            "Prospect",
            lambda: self.gestion_prospects()
        )
        management_menu.addAction(
            QIcon(self.resource_path('icons/settings.png')),
            "Documents",
            lambda: self.gestion_documents()
        )
        management_menu.addAction(
            QIcon(self.resource_path('icons/settings.png')),
            "Contacts",
            lambda: self.gestion_contacts()
        )

        management_btn = QPushButton("Management")
        management_btn.setObjectName("topbar_button")
        management_btn.setIcon(QIcon(self.resource_path('icons/management.png')))
        management_btn.setMenu(management_menu)
        self.nav_buttons.append(management_btn)
        topbar_layout.addWidget(management_btn)

        # Projects Menu (Projects + Tasks + Reports)
        projects_menu = QMenu()
        projects_menu.addAction(
            QIcon(self.resource_path('icons/projects.png')),
            "Projects",
            lambda: self.change_page(2)
        )
        projects_menu.addAction(
            QIcon(self.resource_path('icons/tasks.png')),
            "Tasks",
            lambda: self.change_page(3)
        )
        projects_menu.addAction(
            QIcon(self.resource_path('icons/reports.png')),
            "Reports",
            lambda: self.change_page(4)
        )

        projects_btn = QPushButton("Activities")
        projects_btn.setObjectName("topbar_button")
        projects_btn.setIcon(QIcon(self.resource_path('icons/activities.png')))
        projects_btn.setMenu(projects_menu)
        self.nav_buttons.append(projects_btn)
        topbar_layout.addWidget(projects_btn)

        # Add-on button (single)
        add_on_btn = QPushButton("Add-on")
        add_on_btn.setObjectName("topbar_button")
        add_on_btn.setIcon(QIcon(self.resource_path('icons/add_on.png')))
        add_on_btn.clicked.connect(lambda: self.add_on_page())
        self.nav_buttons.append(add_on_btn)
        topbar_layout.addWidget(add_on_btn)

        topbar_layout.addStretch(2)

        # User section - Right side
        user_container = QHBoxLayout()
        user_container.setSpacing(8)

        # User avatar
        user_avatar = QLabel()
        user_avatar.setPixmap(QIcon(self.resource_path('icons/user.png')).pixmap(32, 32))
        user_avatar.setStyleSheet("border-radius: 16px; border: 1px solid #3498db;")

        # User info
        user_info = QVBoxLayout()
        user_info.setSpacing(0)

        self.user_name = QLabel("Guest")
        self.user_name.setObjectName("user_name_label")

        self.user_role = QLabel("Not logged in")
        self.user_role.setObjectName("user_role_label")


        user_info.addWidget(self.user_name)
        user_info.addWidget(self.user_role)

        user_container.addWidget(user_avatar)
        user_container.addLayout(user_info)
        user_container.addSpacing(8)

        # Logout button
        logout_btn = QPushButton()
        logout_btn.setIcon(QIcon(self.resource_path('icons/logout.png')))
        logout_btn.setIconSize(QSize(20, 20))
        logout_btn.setToolTip("Logout")
        logout_btn.setFixedSize(36, 36)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: white;
                border: none;
                border-radius: 18px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        logout_btn.clicked.connect(self.logout)

        user_container.addWidget(logout_btn)

        user_widget = QWidget()
        user_widget.setLayout(user_container)
        topbar_layout.addWidget(user_widget)

        # Mark dashboard as selected by default
        if self.nav_buttons:
            self.nav_buttons[0].setObjectName("selected")
            self.nav_buttons[0].style().unpolish(self.nav_buttons[0])
            self.nav_buttons[0].style().polish(self.nav_buttons[0])


    # Function to manage notifications
    def gestion_notification(self):
        print("Notification management enabled.")
        # Add logic to send or receive notifications
        # Example: Check if new notifications exist, or send them
        notifications = ["Notification 1", "Notification 2"]
        for notification in notifications:
            print(f"Notification: {notification}")
        return notifications

    # Function to manage prospects
    def gestion_prospects(self):
        print("Prospect management enabled.")
        # Add logic to manage prospects
        # Example: Add a prospect to a list
        prospects = ["Prospect 1", "Prospect 2"]
        for prospect in prospects:
            print(f"Prospect: {prospect}")
        return prospects

    # Function to manage documents
    def gestion_documents(self):
        print("Document management enabled.")
        # Add logic to manage documents
        # Example: Download or delete a document
        documents = ["Document 1", "Document 2"]
        for document in documents:
            print(f"Document: {document}")
        return documents

    # Function to manage contacts
    def gestion_contacts(self):
        print("Contact management enabled.")
        # Add logic to add, modify, or delete contacts
        # Example: Add a contact
        contacts = ["Contact 1", "Contact 2"]
        for contact in contacts:
            print(f"Contact: {contact}")
        return contacts

    # Function to manage after-sales service (Support)
    def gestion_sav(self):
        print("Support management enabled.")
        # Add logic to manage after-sales service
        # Example: Track a support request
        support_requests = ["Support Request 1", "Support Request 2"]
        for request in support_requests:
            print(f"Support Request: {request}")
        return support_requests

    def setup_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header_widget = QWidget() # Use a QWidget as a container for the header layout
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0) # No margins for the inner layout

        title = QLabel("Management Dashboard")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;") # Slightly smaller, consistent color

        self.date_picker = QDateEdit(QDate.currentDate())
        self.date_picker.setCalendarPopup(True)
        # self.date_picker.setStyleSheet removed - will inherit global style

        self.date_picker.dateChanged.connect(self.update_dashboard)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("standard_action_button") # Use standard blue button style
        refresh_btn.setIcon(QIcon(self.resource_path('icons/refresh.png')))
        # refresh_btn.setStyleSheet removed - will inherit global style
        refresh_btn.clicked.connect(self.update_dashboard)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(QLabel("Date:")) # Add label for date picker
        header_layout.addWidget(self.date_picker)
        header_layout.addWidget(refresh_btn)
        header_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed) # Ensure header doesn't take too much vertical space

        # KPIs
        self.kpi_widget = QWidget() # This QWidget will contain the QHBoxLayout for KPIs
        self.kpi_layout = QHBoxLayout(self.kpi_widget)
        self.kpi_layout.setContentsMargins(0, 0, 0, 0) # No margins for the inner layout
        self.kpi_layout.setSpacing(20) # Increased spacing between KPI boxes
        self.kpi_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)


        # Charts
        graph_widget_container = QWidget() # Container for the charts
        graph_layout = QHBoxLayout(graph_widget_container)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_layout.setSpacing(20) # Spacing between charts

        # Performance chart
        self.performance_graph = pg.PlotWidget()
        self.performance_graph.setBackground('#ffffff') # Use hex for consistency
        self.performance_graph.setTitle("Team Performance", color="#2c3e50", size='14pt') # Consistent color, slightly larger
        self.performance_graph.showGrid(x=True, y=True, alpha=0.3) # Lighter grid
        self.performance_graph.setMinimumHeight(320) # Slightly more height
        self.performance_graph.getAxis('left').setTextPen('#333333')
        self.performance_graph.getAxis('bottom').setTextPen('#333333')


        # Project progress chart
        self.project_progress_graph = pg.PlotWidget()
        self.project_progress_graph.setBackground('#ffffff')
        self.project_progress_graph.setTitle("Project Progress", color="#2c3e50", size='14pt')
        self.project_progress_graph.showGrid(x=True, y=True, alpha=0.3)
        self.project_progress_graph.setMinimumHeight(320)
        self.project_progress_graph.getAxis('left').setTextPen('#333333')
        self.project_progress_graph.getAxis('bottom').setTextPen('#333333')


        graph_layout.addWidget(self.performance_graph, 1) # Use stretch factor
        graph_layout.addWidget(self.project_progress_graph, 1) # Use stretch factor
        graph_widget_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Allow charts to expand


        # Recent activities
        activities_widget = QGroupBox("Recent Activities")
        # activities_widget.setStyleSheet removed - will inherit global QGroupBox style

        activities_layout = QVBoxLayout(activities_widget)
        activities_layout.setContentsMargins(10, 10, 10, 10) # Padding inside the groupbox
        activities_layout.setSpacing(10)


        self.activities_table = QTableWidget()
        self.activities_table.setColumnCount(4)
        self.activities_table.setHorizontalHeaderLabels(["Date", "Member", "Action", "Details"])
        # self.activities_table.setStyleSheet removed - will inherit global QTableWidget style
        self.activities_table.verticalHeader().setVisible(False)
        self.activities_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.activities_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.activities_table.setSortingEnabled(True)
        self.activities_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) # Stretch last section
        self.activities_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents) # Date
        self.activities_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents) # Member
        self.activities_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents) # Action
        self.activities_table.setAlternatingRowColors(True) # Improved readability


        activities_layout.addWidget(self.activities_table)
        activities_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred) # Allow activities table to take space


        layout.addWidget(header_widget) # Add the container widget
        layout.addWidget(self.kpi_widget)
        layout.addWidget(graph_widget_container) # Add the container widget
        layout.addWidget(activities_widget)

        self.main_content.addWidget(page)

    def setup_team_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0,0,0,0)

        title = QLabel("Team Management")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;")

        self.add_member_btn = QPushButton("Add Member")
        self.add_member_btn.setObjectName("primary_action_button") # Use green primary button style
        self.add_member_btn.setIcon(QIcon(self.resource_path('icons/add_user.png')))
        # self.add_member_btn.setStyleSheet removed - inherits global style
        self.add_member_btn.clicked.connect(self.show_add_member_dialog)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.add_member_btn)
        header_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


        # Filters
        filters_widget = QWidget() # Container for filter elements
        filters_layout = QHBoxLayout(filters_widget)
        filters_layout.setContentsMargins(0, 0, 0, 0) # No internal margins for the layout itself
        filters_layout.setSpacing(10) # Spacing between filter widgets

        self.team_search = QLineEdit()
        self.team_search.setPlaceholderText("Search member by name or email...")
        # self.team_search.setStyleSheet removed - inherits global style
        self.team_search.textChanged.connect(self.filter_team_members)

        self.role_filter = QComboBox()
        self.role_filter.addItems(["All Roles", "Project Manager", "Developer", "Designer", "HR", "Marketing", "Finance", "Other"]) # Added Other
        # self.role_filter.setStyleSheet removed - inherits global style
        self.role_filter.currentIndexChanged.connect(self.filter_team_members)

        self.team_status_filter = QComboBox() # Renamed to avoid conflict with project status filter
        self.team_status_filter.addItems(["All Statuses", "Active", "Inactive"]) # Simplified statuses based on is_active field
        # self.team_status_filter.setStyleSheet removed - inherits global style
        self.team_status_filter.currentIndexChanged.connect(self.filter_team_members)

        filters_layout.addWidget(QLabel("Search:"))
        filters_layout.addWidget(self.team_search, 1) # Add stretch factor
        filters_layout.addWidget(QLabel("Role:"))
        filters_layout.addWidget(self.role_filter, 1) # Add stretch factor
        filters_layout.addWidget(QLabel("Status:"))
        filters_layout.addWidget(self.team_status_filter, 1) # Add stretch factor
        filters_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


        # Team table
        self.team_table = QTableWidget()
        self.team_table.setColumnCount(10)
        self.team_table.setHorizontalHeaderLabels([
            "Name", "Email", "Role/Title", "Department", "Hire Date",
            "Performance", "Skills", "Status", "Tasks", "Actions" # Changed "Active" to "Status"
        ])
        # self.team_table.setStyleSheet removed - inherits global style
        self.team_table.verticalHeader().setVisible(False)
        self.team_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.team_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.team_table.setSortingEnabled(True)
        self.team_table.setAlternatingRowColors(True)

        # Column Resizing and Alignment
        self.team_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive) # Name
        self.team_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive) # Email
        self.team_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents) # Role
        self.team_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents) # Department
        self.team_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents) # Hire Date
        self.team_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents) # Performance
        self.team_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch) # Skills (can be long)
        self.team_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents) # Status
        self.team_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents) # Tasks
        self.team_table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents) # Actions
        self.team_table.setWordWrap(True) # Allow word wrap for long text like skills
        self.team_table.setTextElideMode(Qt.ElideRight) # Elide text if too long even with wrap


        layout.addWidget(header_widget)
        layout.addWidget(filters_widget)
        layout.addWidget(self.team_table)

        self.main_content.addWidget(page)

    def setup_projects_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0,0,0,0)

        title = QLabel("Project Management")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;")

        self.add_project_btn = QPushButton("New Project")
        self.add_project_btn.setObjectName("primary_action_button") # Use green primary button style
        self.add_project_btn.setIcon(QIcon(self.resource_path('icons/add_project.png')))
        # self.add_project_btn.setStyleSheet removed - inherits global style
        self.add_project_btn.clicked.connect(self.show_add_project_dialog)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.add_project_btn)
        header_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Filters
        filters_widget = QWidget()
        filters_layout = QHBoxLayout(filters_widget)
        filters_layout.setContentsMargins(0,0,0,0)
        filters_layout.setSpacing(10)

        self.project_search = QLineEdit()
        self.project_search.setPlaceholderText("Search by project name or manager...")
        # self.project_search.setStyleSheet removed - inherits global style
        self.project_search.textChanged.connect(self.filter_projects)

        self.status_filter_proj = QComboBox()
        # Populate with statuses from DB or keep static if they are fixed
        # Example: self.status_filter_proj.addItems(["All Statuses", "Planning", "In Progress", "Late", "Completed", "Archived"])
        # For dynamic population (better):
        self.status_filter_proj.addItem("All Statuses", None) # UserData is None for all
        project_statuses_from_db = main_db_manager.get_all_status_settings(status_type='Project')
        if project_statuses_from_db:
            for ps_db in project_statuses_from_db:
                self.status_filter_proj.addItem(ps_db['status_name'], ps_db['status_id'])
        else: # Fallback if no statuses in DB
            self.status_filter_proj.addItems(["Planning", "In Progress", "Late", "Completed", "Archived"])
        # self.status_filter_proj.setStyleSheet removed - inherits global style
        self.status_filter_proj.currentIndexChanged.connect(self.filter_projects)


        self.priority_filter = QComboBox()
        self.priority_filter.addItems(["All Priorities", "High", "Medium", "Low"]) # Display text
        # UserData can map to integer values if needed for filtering: High (2), Medium (1), Low (0)
        self.priority_filter.setItemData(1, 2) # High
        self.priority_filter.setItemData(2, 1) # Medium
        self.priority_filter.setItemData(3, 0) # Low
        # self.priority_filter.setStyleSheet removed - inherits global style
        self.priority_filter.currentIndexChanged.connect(self.filter_projects)

        filters_layout.addWidget(QLabel("Search:"))
        filters_layout.addWidget(self.project_search, 1)
        filters_layout.addWidget(QLabel("Status:"))
        filters_layout.addWidget(self.status_filter_proj, 1)
        filters_layout.addWidget(QLabel("Priority:"))
        filters_layout.addWidget(self.priority_filter, 1)
        filters_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Projects table
        self.projects_table = QTableWidget()
        self.projects_table.setColumnCount(8)
        self.projects_table.setHorizontalHeaderLabels(["Name", "Status", "Progress", "Priority", "Deadline", "Budget (€)", "Manager", "Actions"])
        # self.projects_table.setStyleSheet removed - inherits global style
        self.projects_table.verticalHeader().setVisible(False)
        self.projects_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.projects_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.projects_table.setSortingEnabled(True)
        self.projects_table.setAlternatingRowColors(True)
        self.projects_table.setWordWrap(True)
        self.projects_table.setTextElideMode(Qt.ElideRight)


        # Column Resizing and Alignment
        self.projects_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch) # Name
        self.projects_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents) # Status
        self.projects_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive) # Progress (can be wide with text)
        self.projects_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents) # Priority
        self.projects_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents) # Deadline
        self.projects_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Interactive) # Budget
        self.projects_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Interactive) # Manager
        self.projects_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents) # Actions


        layout.addWidget(header_widget)
        layout.addWidget(filters_widget)
        layout.addWidget(self.projects_table)

        self.main_content.addWidget(page)

    def setup_tasks_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0,0,0,0)

        title = QLabel("Task Management")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;")

        self.add_task_btn = QPushButton("New Task")
        self.add_task_btn.setObjectName("primary_action_button") # Use green primary button style
        self.add_task_btn.setIcon(QIcon(self.resource_path('icons/add_task.png')))
        # self.add_task_btn.setStyleSheet removed - inherits global style
        self.add_task_btn.clicked.connect(self.show_add_task_dialog)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.add_task_btn)
        header_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Filters
        filters_widget = QWidget()
        filters_layout = QHBoxLayout(filters_widget)
        filters_layout.setContentsMargins(0,0,0,0)
        filters_layout.setSpacing(10)

        self.task_search = QLineEdit()
        self.task_search.setPlaceholderText("Search by task name or assignee...")
        # self.task_search.setStyleSheet removed - inherits global style
        self.task_search.textChanged.connect(self.filter_tasks)

        self.task_status_filter = QComboBox()
        self.task_status_filter.addItem("All Statuses", None) # UserData is None for all
        task_statuses_from_db = main_db_manager.get_all_status_settings(status_type='Task')
        if task_statuses_from_db:
            for ts_db in task_statuses_from_db:
                self.task_status_filter.addItem(ts_db['status_name'], ts_db['status_id'])
        else: # Fallback if no statuses in DB
            self.task_status_filter.addItems(["To Do", "In Progress", "In Review", "Completed"]) # Static fallback
        # self.task_status_filter.setStyleSheet removed - inherits global style
        self.task_status_filter.currentIndexChanged.connect(self.filter_tasks)


        self.task_priority_filter = QComboBox()
        self.task_priority_filter.addItems(["All Priorities", "High", "Medium", "Low"])
        self.task_priority_filter.setItemData(1, 2) # High
        self.task_priority_filter.setItemData(2, 1) # Medium
        self.task_priority_filter.setItemData(3, 0) # Low
        # self.task_priority_filter.setStyleSheet removed - inherits global style
        self.task_priority_filter.currentIndexChanged.connect(self.filter_tasks)

        self.task_project_filter = QComboBox()
        self.task_project_filter.addItem("All Projects", None) # UserData for "All Projects" is None
        all_projects_for_task_filter = main_db_manager.get_all_projects()
        if all_projects_for_task_filter:
            for proj_tf in all_projects_for_task_filter:
                 # Optionally filter out completed/archived projects here if desired
                self.task_project_filter.addItem(proj_tf['project_name'], proj_tf['project_id'])
        # self.task_project_filter.setStyleSheet removed - inherits global style
        self.task_project_filter.currentIndexChanged.connect(self.filter_tasks)

        filters_layout.addWidget(QLabel("Search:"))
        filters_layout.addWidget(self.task_search, 1)
        filters_layout.addWidget(QLabel("Project:"))
        filters_layout.addWidget(self.task_project_filter, 1)
        filters_layout.addWidget(QLabel("Status:"))
        filters_layout.addWidget(self.task_status_filter, 1)
        filters_layout.addWidget(QLabel("Priority:"))
        filters_layout.addWidget(self.task_priority_filter, 1)
        filters_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


        # Tasks table
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(7)
        self.tasks_table.setHorizontalHeaderLabels(["Name", "Project", "Status", "Priority", "Assigned To", "Deadline", "Actions"])
        # self.tasks_table.setStyleSheet removed - inherits global style
        self.tasks_table.verticalHeader().setVisible(False)
        self.tasks_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tasks_table.setSortingEnabled(True)
        self.tasks_table.setAlternatingRowColors(True)
        self.tasks_table.setWordWrap(True)
        self.tasks_table.setTextElideMode(Qt.ElideRight)

        # Column Resizing and Alignment
        self.tasks_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch) # Name
        self.tasks_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive) # Project
        self.tasks_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents) # Status
        self.tasks_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents) # Priority
        self.tasks_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive) # Assigned To
        self.tasks_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents) # Deadline
        self.tasks_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents) # Actions


        layout.addWidget(header_widget)
        layout.addWidget(filters_widget)
        layout.addWidget(self.tasks_table)

        self.main_content.addWidget(page)

    def setup_reports_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Reports and Analytics")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;") # Consistent title style

        # Report options
        report_options_widget = QWidget() # Container for options
        options_layout = QHBoxLayout(report_options_widget)
        options_layout.setContentsMargins(0,0,0,0) # No internal margins for this layout
        options_layout.setSpacing(10) # Spacing between controls

        self.report_type = QComboBox()
        self.report_type.addItems(["Team Performance", "Project Progress", "Workload", "Key Indicators", "Budget Analysis"])
        # self.report_type.setStyleSheet removed - inherits global style

        self.report_period = QComboBox()
        self.report_period.addItems(["Last 7 Days", "Last 30 Days", "Current Quarter", "Current Year", "Custom..."])
        # self.report_period.setStyleSheet removed - inherits global style

        generate_btn = QPushButton("Generate Report")
        generate_btn.setObjectName("standard_action_button") # Blue button
        generate_btn.setIcon(QIcon(self.resource_path('icons/generate_report.png')))
        # generate_btn.setStyleSheet removed - inherits global style
        generate_btn.clicked.connect(self.generate_report)

        export_btn = QPushButton("Export Data") # Changed to "Export Data" as PDF is not fully implemented
        export_btn.setObjectName("primary_action_button") # Green button, or use default
        export_btn.setIcon(QIcon(self.resource_path('icons/export_excel.png'))) # Changed icon to reflect excel
        # export_btn.setStyleSheet removed - inherits global style
        export_btn.clicked.connect(self.export_report) # This exports to Excel now

        options_layout.addWidget(QLabel("Type:"))
        options_layout.addWidget(self.report_type, 1) # Add stretch factor
        options_layout.addWidget(QLabel("Period:"))
        options_layout.addWidget(self.report_period, 1) # Add stretch factor
        options_layout.addStretch(1) # Add stretch to push buttons to the right or balance
        options_layout.addWidget(generate_btn)
        options_layout.addWidget(export_btn)
        report_options_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


        # Report area
        self.report_view = QTabWidget()
        # self.report_view.setStyleSheet removed - inherits global QTabWidget style

        # Chart tab
        self.graph_tab = QWidget()
        self.graph_layout = QVBoxLayout(self.graph_tab)
        self.graph_layout.setContentsMargins(0,0,0,0) # Remove margins if canvas handles padding
        self.graph_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        # Data tab
        self.data_tab = QWidget()
        self.data_layout = QVBoxLayout(self.data_tab)
        self.data_layout.setContentsMargins(0,0,0,0) # Remove margins, table will have its own

        self.report_data_table = QTableWidget()
        # self.report_data_table.setStyleSheet removed - inherits global QTableWidget style
        self.report_data_table.verticalHeader().setVisible(False)
        self.report_data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.report_data_table.setAlternatingRowColors(True)
        self.report_data_table.setSelectionBehavior(QTableWidget.SelectRows) # Allow row selection
        self.report_data_table.setWordWrap(True)
        self.report_data_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        self.data_layout.addWidget(self.report_data_table)
        self.data_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        self.report_view.addTab(self.graph_tab, "Visualization")
        self.report_view.addTab(self.data_tab, "Data")
        self.report_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Allow tab view to expand


        layout.addWidget(title)
        layout.addWidget(report_options_widget)
        layout.addWidget(self.report_view)

        self.main_content.addWidget(page)

    def setup_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;") # Consistent title style

        # Tabs
        tabs = QTabWidget()
        # tabs.setStyleSheet removed - inherits global QTabWidget style

        # Account tab
        account_tab = QWidget()
        account_layout = QFormLayout(account_tab)
        account_layout.setSpacing(10) # Slightly reduced spacing for forms
        account_layout.setLabelAlignment(Qt.AlignRight) # Align labels to the right

        # Use QGroupBox for sections within the Account tab for better visual separation
        personal_info_group = QGroupBox("Personal Information")
        personal_info_layout = QFormLayout(personal_info_group)
        personal_info_layout.setSpacing(10)
        personal_info_layout.setLabelAlignment(Qt.AlignRight)

        self.name_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        personal_info_layout.addRow("Full Name:", self.name_edit)
        personal_info_layout.addRow("Email:", self.email_edit)
        personal_info_layout.addRow("Phone:", self.phone_edit)
        account_layout.addRow(personal_info_group)


        security_group = QGroupBox("Security")
        security_layout = QFormLayout(security_group)
        security_layout.setSpacing(10)
        security_layout.setLabelAlignment(Qt.AlignRight)

        self.current_pwd_edit = QLineEdit()
        self.current_pwd_edit.setEchoMode(QLineEdit.Password)
        self.new_pwd_edit = QLineEdit()
        self.new_pwd_edit.setEchoMode(QLineEdit.Password)
        self.confirm_pwd_edit = QLineEdit()
        self.confirm_pwd_edit.setEchoMode(QLineEdit.Password)
        security_layout.addRow("Current Password:", self.current_pwd_edit)
        security_layout.addRow("New Password:", self.new_pwd_edit)
        security_layout.addRow("Confirm New Password:", self.confirm_pwd_edit)
        account_layout.addRow(security_group)

        save_btn_account = QPushButton("Save Account Changes") # Renamed for clarity
        save_btn_account.setObjectName("standard_action_button") # Blue button
        # save_btn_account.setStyleSheet removed
        save_btn_account.clicked.connect(self.save_account_settings)
        account_layout.addRow(save_btn_account) # AddRow can take a widget spanning columns

        # Preferences tab
        pref_tab = QWidget()
        pref_layout = QFormLayout(pref_tab)
        pref_layout.setSpacing(10)
        pref_layout.setLabelAlignment(Qt.AlignRight)

        display_group = QGroupBox("Display")
        display_layout = QFormLayout(display_group)
        display_layout.setSpacing(10)
        display_layout.setLabelAlignment(Qt.AlignRight)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Blue", "Automatic"])
        self.density_combo = QComboBox()
        self.density_combo.addItems(["Compact", "Normal", "Large"])
        self.language_combo = QComboBox()
        self.language_combo.addItems(["French", "English", "Spanish"]) # Consider making these dynamic if app supports more
        display_layout.addRow("Theme:", self.theme_combo)
        display_layout.addRow("Density:", self.density_combo)
        display_layout.addRow("Language:", self.language_combo)
        pref_layout.addRow(display_group)

        notifications_group = QGroupBox("Notifications")
        notifications_layout = QFormLayout(notifications_group) # Using QFormLayout for consistency
        notifications_layout.setSpacing(10)
        notifications_layout.setLabelAlignment(Qt.AlignLeft) # Checkboxes usually have labels on the right
        self.email_notif = QCheckBox("Receive Email Notifications")
        self.app_notif = QCheckBox("Show In-App Notifications")
        self.sms_notif = QCheckBox("Receive SMS Notifications (if configured)")
        notifications_layout.addRow(self.email_notif)
        notifications_layout.addRow(self.app_notif)
        notifications_layout.addRow(self.sms_notif)
        pref_layout.addRow(notifications_group)


        save_pref_btn = QPushButton("Save Preferences")
        save_pref_btn.setObjectName("standard_action_button") # Blue button
        # save_pref_btn.setStyleSheet removed
        save_pref_btn.clicked.connect(self.save_preferences)
        pref_layout.addRow(save_pref_btn)

        # Access Management tab (previously team_tab)
        access_mgmt_tab = QWidget() # Renamed variable for clarity
        access_mgmt_layout = QVBoxLayout(access_mgmt_tab) # Using QVBoxLayout for this tab
        access_mgmt_layout.setContentsMargins(10,10,10,10)
        access_mgmt_layout.setSpacing(10)


        access_header_label = QLabel("Manage User Roles and Access Permissions")
        access_header_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #333333; margin-bottom: 5px;")
        access_mgmt_layout.addWidget(access_header_label)


        self.access_table = QTableWidget()
        self.access_table.setColumnCount(4)
        self.access_table.setHorizontalHeaderLabels(["Name", "Role", "Access Level", "Actions"]) # Changed "Access" to "Access Level"
        # self.access_table.setStyleSheet removed - inherits global style
        self.access_table.verticalHeader().setVisible(False)
        self.access_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.access_table.setAlternatingRowColors(True)
        self.access_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.access_table.setSortingEnabled(True)

        self.access_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch) # Name
        self.access_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents) # Role
        self.access_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents) # Access Level
        self.access_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents) # Actions


        access_mgmt_layout.addWidget(self.access_table)
        access_mgmt_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        tabs.addTab(account_tab, "Account")
        tabs.addTab(pref_tab, "Preferences")
        tabs.addTab(access_mgmt_tab, "Access Management") # Changed tab variable name

        layout.addWidget(title)
        layout.addWidget(tabs)
        tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        self.main_content.addWidget(page)

    def show_login_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Login")
        dialog.setFixedSize(350, 250)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                color: #333333;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton#login_btn {
                background-color: #3498db;
                color: white;
            }
            QPushButton#login_btn:hover {
                background-color: #2980b9;
            }
        """)

        layout = QVBoxLayout(dialog)

        logo = QLabel()
        logo.setPixmap(QIcon(self.resource_path('icons/logo.png')).pixmap(80, 80))
        logo.setAlignment(Qt.AlignCenter)

        username_edit = QLineEdit()
        username_edit.setPlaceholderText("Username")

        password_edit = QLineEdit()
        password_edit.setPlaceholderText("Password")
        password_edit.setEchoMode(QLineEdit.Password)

        login_btn = QPushButton("Login")
        login_btn.setObjectName("login_btn")
        login_btn.clicked.connect(lambda: self.handle_login(username_edit.text(), password_edit.text(), dialog))

        layout.addWidget(logo)
        layout.addWidget(QLabel("Username:"))
        layout.addWidget(username_edit)
        layout.addWidget(QLabel("Password:"))
        layout.addWidget(password_edit)
        layout.addItem(QSpacerItem(20, 20))
        layout.addWidget(login_btn)

        dialog.exec_()

    def handle_login(self, username, password, dialog):
        # hashed_pwd = hashlib.sha256(password.encode()).hexdigest() # Old method

        # Use main_db_manager for verification
        user_data = main_db_manager.verify_user_password(username, password)

        if user_data:
            # User data from main_db_manager is a dictionary
            self.current_user = {
                'id': user_data['user_id'], # Assuming 'user_id' is the key in db.py
                'username': user_data['username'],
                'full_name': user_data['full_name'],
                'email': user_data['email'],
                'role': user_data['role']
            }
            # Ensure all necessary keys are present in user_data from db.py
            # For example, if 'phone' is needed: self.current_user['phone'] = user_data.get('phone')

            # Update UI
            self.user_name.setText(self.current_user['full_name'])
            self.user_role.setText(self.current_user['role'].capitalize())

            # Log activity
            self.log_activity(f"Login by {self.current_user['full_name']}")

            # Load data
            self.load_initial_data()

            dialog.accept()
        else:
            QMessageBox.warning(self, "Error", "Incorrect username or password")

    def logout(self):
        if self.current_user:
            self.log_activity(f"Logout by {self.current_user['full_name']}")

        self.current_user = None
        self.user_name.setText("Guest")
        self.user_role.setText("Not logged in")
        self.show_login_dialog()

    def log_activity(self, action, details=None):
        # This function will be refactored later to use main_db_manager.add_activity_log
        # For now, ensure it doesn't crash due to self.db removal.
        # It needs self.current_user['id'] which should be user_id from main_db
        if self.current_user and 'id' in self.current_user:
            main_db_manager.add_activity_log({
                'user_id': self.current_user['id'], # This should be the user_id (TEXT UUID) from Users table
                'action_type': action, # Match ActivityLog schema in db.py
                'details': details
                # Other fields like 'related_entity_type', 'related_entity_id' can be added if available
            })
        else:
            # Log system activity if no user context, or handle as error
            main_db_manager.add_activity_log({
                'user_id': None,
                'action_type': action,
                'details': f"System activity (user not logged in): {details if details else ''}"
            })


    def load_initial_data(self):
        self.load_kpis()
        self.load_team_members()
        self.load_projects()
        self.load_tasks()
        self.load_activities()
        self.load_access_table()
        self.update_project_filter()

        # Set user preferences if logged in
        if self.current_user:
            self.load_user_preferences()

    def load_kpis(self):
        # Clear old KPIs
        for i in reversed(range(self.kpi_layout.count())):
            widget = self.kpi_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        kpis_to_display = []
        # Attempt to load KPIs for the first project found (temporary approach)
        all_projects = main_db_manager.get_all_projects()
        if all_projects and len(all_projects) > 0:
            first_project_id = all_projects[0].get('project_id')
            if first_project_id:
                kpis_to_display = main_db_manager.get_kpis_for_project(first_project_id)
                if kpis_to_display:
                     print(f"Displaying KPIs for project ID: {first_project_id}")

        if not kpis_to_display: # If still no KPIs
            print("No KPIs found for any project, or no projects exist.")
            no_kpi_label = QLabel("No KPIs to display. Add projects and KPIs.")
            no_kpi_label.setAlignment(Qt.AlignCenter)
            self.kpi_layout.addWidget(no_kpi_label)
            return

        for kpi_dict in kpis_to_display: # kpi_dict is a dictionary from db.py
            name = kpi_dict.get('name', 'N/A')
            value = kpi_dict.get('value', 0)
            target = kpi_dict.get('target', 0)
            trend = kpi_dict.get('trend', 'stable') # default trend
            unit = kpi_dict.get('unit', '')

            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 5px;
                    padding: 15px;
                    border: 1px solid #e0e0e0;
                }
                QLabel {
                    font-size: 14px;
                    color: #555555;
                }
                QLabel#kpi_title {
                    font-size: 16px;
                    font-weight: bold;
                    color: #2c3e50;
                }
                QLabel#kpi_value {
                    font-size: 28px;
                    font-weight: bold;
                    color: #3498db;
                }
            """)
            frame.setFixedWidth(220)

            frame_layout = QVBoxLayout(frame)
            frame_layout.setSpacing(5)

            title_label = QLabel(name.capitalize())
            title_label.setObjectName("kpi_title")

            value_label = QLabel(f"{value}{unit}") # Use value and unit from dict
            value_label.setObjectName("kpi_value")

            target_label = QLabel(f"Target: {target}{unit}") # Use target and unit

            trend_icon_label = QLabel()
            if trend == "up":
                trend_icon_label.setPixmap(QIcon(self.resource_path('icons/trend_up.png')).pixmap(16, 16))
            elif trend == "down":
                trend_icon_label.setPixmap(QIcon(self.resource_path('icons/trend_down.png')).pixmap(16, 16))
            else: # "stable" or other
                trend_icon_label.setPixmap(QIcon(self.resource_path('icons/trend_flat.png')).pixmap(16, 16))

            trend_layout = QHBoxLayout()
            trend_layout.addWidget(QLabel("Trend:"))
            trend_layout.addWidget(trend_icon_label)
            trend_layout.addStretch()

            frame_layout.addWidget(title_label)
            frame_layout.addWidget(value_label)
            frame_layout.addWidget(target_label)
            frame_layout.addLayout(trend_layout)

            self.kpi_layout.addWidget(frame)

        # Ensure layout has stretch if few KPIs
        if self.kpi_layout.count() > 0 and self.kpi_layout.count() < 4: # Arbitrary number for adding stretch
            self.kpi_layout.addStretch()


    def load_team_members(self):
        # Uses main_db_manager.get_all_team_members()
        # db.py fields: team_member_id, user_id, full_name, email, role_or_title, department,
        # phone_number, profile_picture_url, is_active, notes, hire_date, performance, skills

        members_data = main_db_manager.get_all_team_members()
        if members_data is None: members_data = []

        self.team_table.setRowCount(len(members_data))

        for row_idx, member in enumerate(members_data):
            self.team_table.setItem(row_idx, 0, QTableWidgetItem(member.get('full_name', 'N/A')))
            self.team_table.setItem(row_idx, 1, QTableWidgetItem(member.get('email', 'N/A')))
            self.team_table.setItem(row_idx, 2, QTableWidgetItem(member.get('role_or_title', 'N/A')))
            self.team_table.setItem(row_idx, 3, QTableWidgetItem(member.get('department', 'N/A')))
            self.team_table.setItem(row_idx, 4, QTableWidgetItem(member.get('hire_date', 'N/A')))

            performance_val = member.get('performance', 0)
            perf_item = QTableWidgetItem(f"{performance_val}%")
            if performance_val >= 90: perf_item.setForeground(QColor('#27ae60'))
            elif performance_val >= 80: perf_item.setForeground(QColor('#f39c12'))
            else: perf_item.setForeground(QColor('#e74c3c'))
            self.team_table.setItem(row_idx, 5, perf_item)

            self.team_table.setItem(row_idx, 6, QTableWidgetItem(member.get('skills', 'N/A')))

            is_active_val = member.get('is_active', False)
            active_item = QTableWidgetItem()
            if is_active_val:
                active_item.setIcon(QIcon(self.resource_path('icons/active.png')))
                active_item.setText("Active")
            else:
                active_item.setIcon(QIcon(self.resource_path('icons/inactive.png')))
                active_item.setText("Inactive")
            self.team_table.setItem(row_idx, 7, active_item)

            # Number of tasks - Placeholder for now, requires task refactoring
            task_count = 0
            # Example of future integration:
            # if member.get('team_member_id'):
            #   tasks_for_member = main_db_manager.get_tasks_by_assignee(member['team_member_id']) # Needs this func in db.py
            #   task_count = len(tasks_for_member) if tasks_for_member else 0
            self.team_table.setItem(row_idx, 8, QTableWidgetItem(str(task_count)))

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0,0,0,0)
            action_layout.setSpacing(5)

            current_member_id = member['team_member_id']

            edit_btn = QPushButton()
            edit_btn.setIcon(QIcon(self.resource_path('icons/edit.png')))
            edit_btn.setToolTip("Edit")
            edit_btn.setFixedSize(30,30)
            edit_btn.setStyleSheet("background-color: transparent;")
            edit_btn.clicked.connect(lambda _, m_id=current_member_id: self.edit_member(m_id))

            delete_btn = QPushButton()
            delete_btn.setIcon(QIcon(self.resource_path('icons/delete.png')))
            delete_btn.setToolTip("Delete")
            delete_btn.setFixedSize(30,30)
            delete_btn.setStyleSheet("background-color: transparent;")
            delete_btn.clicked.connect(lambda _, m_id=current_member_id: self.delete_member(m_id))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(delete_btn)
            self.team_table.setCellWidget(row_idx, 9, action_widget)

        self.team_table.resizeColumnsToContents()

    def load_projects(self):
        # db.py fields: project_id (TEXT PK), client_id, project_name, description, start_date, deadline_date,
        # budget, status_id (FK to StatusSettings), progress_percentage, manager_team_member_id (FK to Users.user_id),
        # priority (INTEGER), created_at, updated_at

        projects_data = main_db_manager.get_all_projects()
        if projects_data is None:
            projects_data = []

        self.projects_table.setRowCount(len(projects_data))

        for row_idx, project_dict in enumerate(projects_data):
            project_id_str = project_dict.get('project_id') # This is TEXT UUID
            self.projects_table.setItem(row_idx, 0, QTableWidgetItem(project_dict.get('project_name', 'N/A')))

            # Status
            status_id = project_dict.get('status_id')
            status_name_display = "Unknown"
            status_color_hex = "#7f8c8d" # Default color (e.g., grey)
            if status_id is not None:
                status_setting = main_db_manager.get_status_setting_by_id(status_id)
                if status_setting:
                    status_name_display = status_setting.get('status_name', 'Unknown')
                    color_from_db = status_setting.get('color_hex')
                    if color_from_db:
                        status_color_hex = color_from_db
                    else:
                        if "completed" in status_name_display.lower(): status_color_hex = '#2ecc71'
                        elif "progress" in status_name_display.lower(): status_color_hex = '#3498db'
                        elif "planning" in status_name_display.lower(): status_color_hex = '#f1c40f'
                        elif "late" in status_name_display.lower() or "overdue" in status_name_display.lower(): status_color_hex = '#e74c3c'
                        elif "archived" in status_name_display.lower(): status_color_hex = '#95a5a6'

            status_item = QTableWidgetItem(status_name_display)
            status_item.setForeground(QColor(status_color_hex))
            self.projects_table.setItem(row_idx, 1, status_item)

            # Progress bar
            progress = project_dict.get('progress_percentage', 0)
            progress_widget = QWidget()
            progress_layout = QHBoxLayout(progress_widget)
            progress_layout.setContentsMargins(5, 5, 5, 5)
            progress_bar = QProgressBar()
            progress_bar.setValue(progress if progress is not None else 0)
            progress_bar.setAlignment(Qt.AlignCenter)
            progress_bar.setFormat(f"{progress if progress is not None else 0}%")
            progress_bar.setStyleSheet("""
                QProgressBar { border: 1px solid #bdc3c7; border-radius: 5px; text-align: center; height: 20px; }
                QProgressBar::chunk { background-color: #3498db; border-radius: 4px; }
            """)
            progress_layout.addWidget(progress_bar)
            self.projects_table.setCellWidget(row_idx, 2, progress_widget)

            # Priority
            priority_val = project_dict.get('priority', 0)
            priority_item = QTableWidgetItem()
            if priority_val == 2: # High
                priority_item.setIcon(QIcon(self.resource_path('icons/priority_high.png')))
                priority_item.setText("High")
            elif priority_val == 1: # Medium
                priority_item.setIcon(QIcon(self.resource_path('icons/priority_medium.png')))
                priority_item.setText("Medium")
            else: # 0 or other = Low
                priority_item.setIcon(QIcon(self.resource_path('icons/priority_low.png')))
                priority_item.setText("Low")
            self.projects_table.setItem(row_idx, 3, priority_item)

            self.projects_table.setItem(row_idx, 4, QTableWidgetItem(project_dict.get('deadline_date', 'N/A')))
            budget_val = project_dict.get('budget', 0.0)
            self.projects_table.setItem(row_idx, 5, QTableWidgetItem(f"€{budget_val:,.2f}" if budget_val is not None else "€0.00"))

            manager_user_id = project_dict.get('manager_team_member_id')
            manager_display_name = "Unassigned"
            if manager_user_id:
                team_member_as_manager_list = main_db_manager.get_all_team_members({'user_id': manager_user_id})
                if team_member_as_manager_list and len(team_member_as_manager_list) > 0:
                    manager_display_name = team_member_as_manager_list[0].get('full_name', manager_user_id)
                else:
                    user_as_manager = main_db_manager.get_user_by_id(manager_user_id)
                    if user_as_manager:
                        manager_display_name = user_as_manager.get('full_name', manager_user_id)
            self.projects_table.setItem(row_idx, 6, QTableWidgetItem(manager_display_name))

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0,0,0,0)
            action_layout.setSpacing(5)

            details_btn = QPushButton()
            details_btn.setIcon(QIcon(self.resource_path('icons/details.png')))
            details_btn.setToolTip("Details")
            details_btn.setFixedSize(30,30)
            details_btn.setStyleSheet("background-color: transparent;")
            details_btn.clicked.connect(lambda _, p_id=project_id_str: self.show_project_details(p_id))

            edit_btn = QPushButton()
            edit_btn.setIcon(QIcon(self.resource_path('icons/edit.png')))
            edit_btn.setToolTip("Edit")
            edit_btn.setFixedSize(30,30)
            edit_btn.setStyleSheet("background-color: transparent;")
            edit_btn.clicked.connect(lambda _, p_id=project_id_str: self.edit_project(p_id))

            delete_btn = QPushButton()
            delete_btn.setIcon(QIcon(self.resource_path('icons/delete.png')))
            delete_btn.setToolTip("Delete")
            delete_btn.setFixedSize(30,30)
            delete_btn.setStyleSheet("background-color: transparent;")
            delete_btn.clicked.connect(lambda _, p_id=project_id_str: self.delete_project(p_id))

            action_layout.addWidget(details_btn)
            action_layout.addWidget(edit_btn)
            action_layout.addWidget(delete_btn)
            self.projects_table.setCellWidget(row_idx, 7, action_widget)

        self.projects_table.resizeColumnsToContents()

    def load_tasks(self):
        self.tasks_table.setRowCount(0) # Clear existing rows
        current_row = 0

        all_projects = main_db_manager.get_all_projects()
        if all_projects is None: all_projects = []

        for project_dict in all_projects:
            project_id = project_dict.get('project_id')
            project_name = project_dict.get('project_name', 'N/A')

            tasks_for_project = main_db_manager.get_tasks_by_project_id(project_id)
            if tasks_for_project is None: tasks_for_project = []

            if not tasks_for_project: continue # Skip if no tasks for this project

            self.tasks_table.setRowCount(self.tasks_table.rowCount() + len(tasks_for_project))

            for task_dict in tasks_for_project:
                task_id = task_dict.get('task_id')
                self.tasks_table.setItem(current_row, 0, QTableWidgetItem(task_dict.get('task_name', 'N/A')))
                self.tasks_table.setItem(current_row, 1, QTableWidgetItem(project_name)) # Use fetched project_name

                # Status
                status_id = task_dict.get('status_id')
                status_name_display = "Unknown"
                status_color_hex = "#7f8c8d" # Default grey
                status_setting_for_task = None # To check for completion status later
                if status_id is not None:
                    status_setting_for_task = main_db_manager.get_status_setting_by_id(status_id)
                    if status_setting_for_task:
                        status_name_display = status_setting_for_task.get('status_name', 'Unknown')
                        color_from_db = status_setting_for_task.get('color_hex')
                        if color_from_db: status_color_hex = color_from_db
                        elif "completed" in status_name_display.lower() or "done" in status_name_display.lower() : status_color_hex = '#2ecc71'
                        elif "progress" in status_name_display.lower(): status_color_hex = '#3498db'
                        elif "todo" in status_name_display.lower() or "to do" in status_name_display.lower(): status_color_hex = '#f39c12'
                        elif "review" in status_name_display.lower(): status_color_hex = '#9b59b6'
                status_item = QTableWidgetItem(status_name_display)
                status_item.setForeground(QColor(status_color_hex))
                self.tasks_table.setItem(current_row, 2, status_item)

                # Priority
                priority_val = task_dict.get('priority', 0)
                priority_item = QTableWidgetItem()
                if priority_val == 2:
                    priority_item.setIcon(QIcon(self.resource_path('icons/priority_high.png')))
                    priority_item.setText("High")
                elif priority_val == 1:
                    priority_item.setIcon(QIcon(self.resource_path('icons/priority_medium.png')))
                    priority_item.setText("Medium")
                else:
                    priority_item.setIcon(QIcon(self.resource_path('icons/priority_low.png')))
                    priority_item.setText("Low")
                self.tasks_table.setItem(current_row, 3, priority_item)

                # Assignee Name
                assignee_name_display = "Unassigned"
                assignee_tm_id = task_dict.get('assignee_team_member_id')
                if assignee_tm_id is not None:
                    team_member_info = main_db_manager.get_team_member_by_id(assignee_tm_id)
                    if team_member_info:
                        assignee_name_display = team_member_info.get('full_name', 'N/A')
                self.tasks_table.setItem(current_row, 4, QTableWidgetItem(assignee_name_display))

                self.tasks_table.setItem(current_row, 5, QTableWidgetItem(task_dict.get('due_date', 'N/A')))

                # Action buttons
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(0,0,0,0)
                action_layout.setSpacing(5)

                complete_btn = QPushButton()
                complete_btn.setIcon(QIcon(self.resource_path('icons/complete.png')))
                complete_btn.setToolTip("Mark as Completed")
                complete_btn.setFixedSize(30,30)
                complete_btn.setStyleSheet("background-color: transparent;")
                complete_btn.clicked.connect(lambda _, t_id=task_id: self.complete_task(t_id))
                if status_setting_for_task and status_setting_for_task.get('is_completion_status'):
                    complete_btn.setEnabled(False)

                edit_btn = QPushButton()
                edit_btn.setIcon(QIcon(self.resource_path('icons/edit.png')))
                edit_btn.setToolTip("Edit")
                edit_btn.setFixedSize(30,30)
                edit_btn.setStyleSheet("background-color: transparent;")
                edit_btn.clicked.connect(lambda _, t_id=task_id: self.edit_task(t_id))

                delete_btn = QPushButton()
                delete_btn.setIcon(QIcon(self.resource_path('icons/delete.png')))
                delete_btn.setToolTip("Delete")
                delete_btn.setFixedSize(30,30)
                delete_btn.setStyleSheet("background-color: transparent;")
                delete_btn.clicked.connect(lambda _, t_id=task_id: self.delete_task(t_id))

                action_layout.addWidget(complete_btn)
                action_layout.addWidget(edit_btn)
                action_layout.addWidget(delete_btn)
                self.tasks_table.setCellWidget(current_row, 6, action_widget)
                current_row += 1

        self.tasks_table.resizeColumnsToContents()

    def load_activities(self):
        activities_data = main_db_manager.get_activity_logs(limit=50)
        if activities_data is None: activities_data = []

        self.activities_table.setRowCount(0) # Clear table before loading
        self.activities_table.setRowCount(len(activities_data))

        for row_idx, log_entry in enumerate(activities_data):
            # Fields from db.py ActivityLog: log_id, user_id, action_type, details,
            # related_entity_type, related_entity_id, related_client_id, ip_address, user_agent, created_at

            # For display, we need user's full_name if user_id is present
            user_name_display = "System"
            if log_entry.get('user_id'):
                user_info = main_db_manager.get_user_by_id(log_entry['user_id'])
                if user_info:
                    user_name_display = user_info.get('full_name', log_entry['user_id'])

            self.activities_table.setItem(row_idx, 0, QTableWidgetItem(log_entry.get('created_at', 'N/A')))
            self.activities_table.setItem(row_idx, 1, QTableWidgetItem(user_name_display))
            self.activities_table.setItem(row_idx, 2, QTableWidgetItem(log_entry.get('action_type', 'N/A')))
            self.activities_table.setItem(row_idx, 3, QTableWidgetItem(log_entry.get('details', '')))

        self.activities_table.resizeColumnsToContents()

    def load_access_table(self):
        users_data = main_db_manager.get_all_users() # Assuming db.py has get_all_users()
        if users_data is None: users_data = []

        self.access_table.setRowCount(len(users_data))

        for row_idx, user_dict in enumerate(users_data):
            user_id_str = user_dict.get('user_id') # This is TEXT UUID
            full_name = user_dict.get('full_name', 'N/A')
            role = user_dict.get('role', 'member') # Default to 'member' or a base role

            self.access_table.setItem(row_idx, 0, QTableWidgetItem(full_name))

            # Map role from db.py (e.g., 'admin', 'manager', 'member') to display name
            role_display_name = role.capitalize()
            access_text = "User" # Default access text
            access_color = QColor('#2ecc71') # Default color (green for User)

            if role == "admin":
                role_display_name = "Administrator"
                access_text = "Administrator"
                access_color = QColor('#e74c3c') # Red
            elif role == "manager":
                role_display_name = "Manager"
                access_text = "Manager"
                access_color = QColor('#3498db') # Blue

            self.access_table.setItem(row_idx, 1, QTableWidgetItem(role_display_name))

            access_item = QTableWidgetItem(access_text)
            access_item.setForeground(access_color)
            self.access_table.setItem(row_idx, 2, access_item)

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0,0,0,0)
            action_layout.setSpacing(5)

            edit_btn = QPushButton()
            edit_btn.setIcon(QIcon(self.resource_path('icons/edit.png')))
            edit_btn.setToolTip("Edit User Access")
            edit_btn.setFixedSize(30,30)
            edit_btn.setStyleSheet("background-color: transparent;")
            # Ensure user_id_str is passed to edit_user_access
            edit_btn.clicked.connect(lambda _, u_id=user_id_str: self.edit_user_access(u_id))

            action_layout.addWidget(edit_btn)
            self.access_table.setCellWidget(row_idx, 3, action_widget)

        self.access_table.resizeColumnsToContents()

    def load_user_preferences(self):
        # Load user preferences from database using main_db_manager
        if not self.current_user or 'id' not in self.current_user:
            return

        user_data = main_db_manager.get_user_by_id(self.current_user['id'])

        if user_data: # user_data is a dict
            self.name_edit.setText(user_data.get('full_name', ''))
            self.email_edit.setText(user_data.get('email', ''))
            self.phone_edit.setText(user_data.get('phone', ''))

    def update_project_filter(self):
        # Refactored to use main_db_manager
        projects = main_db_manager.get_all_projects()

        current_selection_text = self.task_project_filter.currentText()
        current_selection_data = self.task_project_filter.currentData()

        self.task_project_filter.clear()
        self.task_project_filter.addItem("All Projects", None) # UserData for "All Projects" is None

        if projects:
            for project in projects:
                self.task_project_filter.addItem(project['project_name'], project['project_id'])

        # Try to restore previous selection
        if current_selection_data is not None:
            index = self.task_project_filter.findData(current_selection_data)
            if index != -1:
                self.task_project_filter.setCurrentIndex(index)
            else: # Fallback to text if data (id) changed or not found
                index = self.task_project_filter.findText(current_selection_text)
                if index != -1: self.task_project_filter.setCurrentIndex(index)
        elif current_selection_text: # if previous selection was "All Projects" by text
            index = self.task_project_filter.findText(current_selection_text)
            if index != -1: self.task_project_filter.setCurrentIndex(index)


    def filter_team_members(self):
        search_text = self.team_search.text().lower()
        role_filter = self.role_filter.currentText()
        status_filter = self.status_filter.currentText()

        for row in range(self.team_table.rowCount()):
            name = self.team_table.item(row, 0).text().lower()
            role = self.team_table.item(row, 1).text()
            status = self.team_table.item(row, 5).text()

            name_match = search_text in name
            role_match = role_filter == "All Roles" or role == role_filter
            status_match = status_filter == "All Statuses" or status == status_filter

            self.team_table.setRowHidden(row, not (name_match and role_match and status_match))

    def filter_projects(self):
        search_text = self.project_search.text().lower()
        status_filter = self.status_filter_proj.currentText()
        priority_filter = self.priority_filter.currentText()

        for row in range(self.projects_table.rowCount()):
            name_item = self.projects_table.item(row, 0)
            status_item = self.projects_table.item(row, 1)
            priority_item = self.projects_table.item(row, 3)

            name = name_item.text().lower() if name_item else ""
            status = status_item.text() if status_item else ""
            priority = priority_item.text() if priority_item else ""

            name_match = search_text in name
            status_match = status_filter == "All Statuses" or status == status_filter
            priority_match = priority_filter == "All Priorities" or priority == priority_filter

            self.projects_table.setRowHidden(row, not (name_match and status_match and priority_match))

    def filter_tasks(self):
        search_text = self.task_search.text().lower()
        status_filter = self.task_status_filter.currentText()
        priority_filter = self.task_priority_filter.currentText()
        project_filter = self.task_project_filter.currentText()

        for row in range(self.tasks_table.rowCount()):
            name = self.tasks_table.item(row, 0).text().lower()
            project = self.tasks_table.item(row, 1).text()
            status = self.tasks_table.item(row, 2).text()
            priority = self.tasks_table.item(row, 3).text()

            name_match = search_text in name
            project_match = project_filter == "All Projects" or project == project_filter
            status_match = status_filter == "All Statuses" or status == status_filter
            priority_match = priority_filter == "All Priorities" or priority == priority_filter

            self.tasks_table.setRowHidden(row, not (name_match and project_match and status_match and priority_match))

    def update_dashboard(self):
        self.load_kpis()
        self.load_activities()
        self.update_charts()
        self.statusBar().showMessage("Dashboard updated", 3000)

    def update_charts(self):
        # Team performance
        self.performance_graph.clear()
        active_members = main_db_manager.get_all_team_members({'is_active': True})
        if active_members is None: active_members = []

        # Sort by performance for chart
        active_members.sort(key=lambda x: x.get('performance', 0), reverse=True)

        member_names = [m.get('full_name', 'N/A') for m in active_members]
        member_performance = [m.get('performance', 0) for m in active_members]

        if member_names:
            bg1 = pg.BarGraphItem(x=range(len(member_names)), height=member_performance, width=0.6, brush='#3498db')
            self.performance_graph.addItem(bg1)
            self.performance_graph.getAxis('bottom').setTicks([[(i, name) for i, name in enumerate(member_names)]])
        else: # Handle case with no active members
             self.performance_graph.getAxis('bottom').setTicks([[]]) # Clear old ticks

        self.performance_graph.setYRange(0, 100)
        self.performance_graph.setLabel('left', 'Performance (%)')
        self.performance_graph.setTitle("Team Performance (Active Members)")

        # Project progress
        self.project_progress_graph.clear()
        all_projects = main_db_manager.get_all_projects()
        if all_projects is None: all_projects = []

        projects_for_chart = []
        for p_dict in all_projects:
            status_id = p_dict.get('status_id')
            if status_id:
                status_setting = main_db_manager.get_status_setting_by_id(status_id)
                if status_setting and \
                   not status_setting.get('is_completion_status', False) and \
                   not status_setting.get('is_archival_status', False):
                    projects_for_chart.append(p_dict)
            else: # Include projects with no status if that's desired, or filter out
                projects_for_chart.append(p_dict) # Assuming projects with no status are ongoing

        projects_for_chart.sort(key=lambda x: x.get('progress_percentage', 0), reverse=True)

        project_names = [p.get('project_name', 'N/A') for p in projects_for_chart]
        project_progress = [p.get('progress_percentage', 0) for p in projects_for_chart]

        if project_names:
            bg2 = pg.BarGraphItem(x=range(len(project_names)), height=project_progress, width=0.6, brush='#2ecc71')
            self.project_progress_graph.addItem(bg2)
            self.project_progress_graph.getAxis('bottom').setTicks([[(i, name) for i, name in enumerate(project_names)]])
        else: # Handle case with no projects for chart
            self.project_progress_graph.getAxis('bottom').setTicks([[]]) # Clear old ticks

        self.project_progress_graph.setYRange(0, 100)
        self.project_progress_graph.setLabel('left', 'Progress (%)')
        self.project_progress_graph.setTitle("Project Progress (Ongoing)")

    def generate_report(self):
        report_type = self.report_type.currentText()
        period = self.report_period.currentText()

        # Clear previous tabs
        for i in reversed(range(self.graph_layout.count())):
            self.graph_layout.itemAt(i).widget().deleteLater()

        # Clear data table
        self.report_data_table.clear()

        if report_type == "Team Performance":
            self.generate_team_performance_report(period)
        elif report_type == "Project Progress":
            self.generate_project_progress_report(period)
        elif report_type == "Workload":
            self.generate_workload_report(period)
        elif report_type == "Key Indicators":
            self.generate_kpi_report(period)
        elif report_type == "Budget Analysis":
            self.generate_budget_report(period)

        self.statusBar().showMessage(f"Report '{report_type}' generated for period '{period}'", 3000)

    def generate_team_performance_report(self, period):
        # Chart
        fig = plt.figure(figsize=(10, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        # Fetch data using main_db_manager
        active_members_data = main_db_manager.get_all_team_members({'is_active': True})
        if active_members_data is None: active_members_data = []

        # Sort by performance for consistent chart display (optional, but good for reports)
        active_members_data.sort(key=lambda x: x.get('performance', 0), reverse=True)

        names = [member.get('full_name', 'N/A') for member in active_members_data]
        performance = [member.get('performance', 0) for member in active_members_data]

        bars = ax.bar(names, performance, color='#3498db')
        ax.set_title("Team Performance (Active Members)")
        ax.set_ylabel("Performance (%)")
        ax.set_ylim(0, 100)

        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height}%', ha='center', va='bottom')

        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        self.graph_layout.addWidget(canvas)

        # Data for the table view
        self.report_data_table.setColumnCount(2)
        self.report_data_table.setHorizontalHeaderLabels(["Member", "Performance (%)"])
        self.report_data_table.setRowCount(len(active_members_data))

        for row_idx, member_dict in enumerate(active_members_data):
            self.report_data_table.setItem(row_idx, 0, QTableWidgetItem(member_dict.get('full_name', 'N/A')))
            self.report_data_table.setItem(row_idx, 1, QTableWidgetItem(str(member_dict.get('performance', 0))))

        self.report_data_table.resizeColumnsToContents()

    def generate_project_progress_report(self, period):
        # Chart
        fig = plt.figure(figsize=(10, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        projects_data = main_db_manager.get_all_projects()
        if projects_data is None: projects_data = []

        # Filter out projects that might be considered "deleted" or "archived" based on status type
        # This assumes StatusSettings has 'is_archival_status'
        valid_projects_for_report = []
        for p_dict in projects_data:
            status_id = p_dict.get('status_id')
            if status_id:
                status_setting = main_db_manager.get_status_setting_by_id(status_id)
                if status_setting and not status_setting.get('is_archival_status'): # Only include non-archival
                    valid_projects_for_report.append(p_dict)
            else: # Include projects with no status_id for now, or decide to filter them
                valid_projects_for_report.append(p_dict)

        valid_projects_for_report.sort(key=lambda x: x.get('progress_percentage', 0), reverse=True)


        names = [p.get('project_name', 'N/A') for p in valid_projects_for_report]
        progress_values = [p.get('progress_percentage', 0) for p in valid_projects_for_report]

        colors = []
        status_names_for_table = []

        for p_dict in valid_projects_for_report:
            status_id = p_dict.get('status_id')
            status_name = "Unknown"
            color = '#3498db' # Default blue
            if status_id:
                status_setting = main_db_manager.get_status_setting_by_id(status_id)
                if status_setting:
                    status_name = status_setting.get('status_name', 'Unknown')
                    hex_color = status_setting.get('color_hex')
                    if hex_color: color = hex_color
                    elif "completed" in status_name.lower(): color = '#2ecc71'
                    elif "late" in status_name.lower(): color = '#e74c3c'
            colors.append(color)
            status_names_for_table.append(status_name)


        bars = ax.bar(names, progress_values, color=colors)
        ax.set_title("Project Progress")
        ax.set_ylabel("Progress (%)")
        ax.set_ylim(0, 100)

        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height}%', ha='center', va='bottom')

        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        self.graph_layout.addWidget(canvas)

        # Data
        self.report_data_table.setColumnCount(4)
        self.report_data_table.setHorizontalHeaderLabels(["Project", "Progress (%)", "Status", "Budget"])
        self.report_data_table.setRowCount(len(valid_projects_for_report))

        for row_idx, p_dict in enumerate(valid_projects_for_report):
            self.report_data_table.setItem(row_idx, 0, QTableWidgetItem(p_dict.get('project_name', 'N/A')))
            self.report_data_table.setItem(row_idx, 1, QTableWidgetItem(str(p_dict.get('progress_percentage', 0))))

            status_text_for_table = status_names_for_table[row_idx] # Get resolved status name
            self.report_data_table.setItem(row_idx, 2, QTableWidgetItem(status_text_for_table))

            budget = p_dict.get('budget', 0.0)
            self.report_data_table.setItem(row_idx, 3, QTableWidgetItem(f"€{budget:,.2f}"))

        self.report_data_table.resizeColumnsToContents()

    def generate_workload_report(self, period):
        # Chart
        fig = plt.figure(figsize=(10, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        active_team_members = main_db_manager.get_all_team_members({'is_active': True})
        if not active_team_members: active_team_members = []

        member_task_counts = {} # Store as team_member_id: count

        # Aggregate tasks: Iterate through projects, then tasks
        all_projects = main_db_manager.get_all_projects()
        if all_projects:
            for project in all_projects:
                tasks_in_project = main_db_manager.get_tasks_by_project_id(project['project_id'])
                if tasks_in_project:
                    for task in tasks_in_project:
                        assignee_id = task.get('assignee_team_member_id')
                        status_id = task.get('status_id')
                        if assignee_id is not None and status_id is not None:
                            status_setting = main_db_manager.get_status_setting_by_id(status_id)
                            if status_setting and \
                               not status_setting.get('is_completion_status') and \
                               not status_setting.get('is_archival_status'):
                                member_task_counts[assignee_id] = member_task_counts.get(assignee_id, 0) + 1

        report_data_list = []
        for member in active_team_members:
            tm_id = member['team_member_id']
            report_data_list.append({
                'name': member.get('full_name', 'N/A'),
                'task_count': member_task_counts.get(tm_id, 0),
                'performance': member.get('performance', 0)
            })

        # Sort by task_count for the chart
        report_data_list.sort(key=lambda x: x['task_count'], reverse=True)

        names = [item['name'] for item in report_data_list]
        task_counts_values = [item['task_count'] for item in report_data_list]

        bars = ax.bar(names, task_counts_values, color='#9b59b6')
        ax.set_title("Workload by Member (Active Tasks)")
        ax.set_ylabel("Number of Tasks")

        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height}', ha='center', va='bottom')

        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        self.graph_layout.addWidget(canvas)

        # Data for the table view
        self.report_data_table.setColumnCount(3)
        self.report_data_table.setHorizontalHeaderLabels(["Member", "Ongoing Tasks", "Performance"])
        self.report_data_table.setRowCount(len(report_data_list))

        for row_idx, item_data in enumerate(report_data_list):
            self.report_data_table.setItem(row_idx, 0, QTableWidgetItem(item_data['name']))
            self.report_data_table.setItem(row_idx, 1, QTableWidgetItem(str(item_data['task_count'])))

            perf = item_data['performance']
            perf_item = QTableWidgetItem(f"{perf}%")
            if perf >= 90: perf_item.setForeground(QColor('#27ae60'))
            elif perf >= 80: perf_item.setForeground(QColor('#f39c12'))
            else: perf_item.setForeground(QColor('#e74c3c'))
            self.report_data_table.setItem(row_idx, 2, perf_item)

        self.report_data_table.resizeColumnsToContents()

    def generate_kpi_report(self, period):
        # Chart
        fig = plt.figure(figsize=(10, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        kpis_data = []
        # Fetch KPIs for the first project, similar to load_kpis logic
        all_projects = main_db_manager.get_all_projects()
        if all_projects and len(all_projects) > 0:
            first_project_id = all_projects[0].get('project_id')
            if first_project_id:
                kpis_data = main_db_manager.get_kpis_for_project(first_project_id)
        if not kpis_data: kpis_data = []


        names = [kpi.get('name', 'N/A') for kpi in kpis_data]
        values = [kpi.get('value', 0) for kpi in kpis_data]
        targets = [kpi.get('target', 0) for kpi in kpis_data]

        if not names: # If no KPIs, display a message on the chart
            ax.text(0.5, 0.5, "No KPI data available for selected period/project.",
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=12, color='gray')
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            x = range(len(names))
            width = 0.35

            bars1 = ax.bar(x, values, width, label='Current Value', color='#3498db')
            bars2 = ax.bar([p + width for p in x], targets, width, label='Target', color='#e74c3c')

            ax.set_title("Key Performance Indicators")
            ax.set_ylabel("Value")
            ax.set_xticks([p + width/2 for p in x])
            ax.set_xticklabels(names, rotation=45, ha='right')
            ax.legend()

            for bar in bars1:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height}', ha='center', va='bottom')

            for bar in bars2:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height}', ha='center', va='bottom')
            plt.tight_layout()

        self.graph_layout.addWidget(canvas)

        # Data
        self.report_data_table.setColumnCount(4)
        self.report_data_table.setHorizontalHeaderLabels(["KPI", "Value", "Target", "Difference"])
        self.report_data_table.setRowCount(len(kpis_data))

        for row_idx, kpi_dict in enumerate(kpis_data):
            kpi_name = kpi_dict.get('name', 'N/A')
            kpi_value = kpi_dict.get('value', 0)
            kpi_target = kpi_dict.get('target', 0)

            self.report_data_table.setItem(row_idx, 0, QTableWidgetItem(kpi_name.capitalize()))
            self.report_data_table.setItem(row_idx, 1, QTableWidgetItem(str(kpi_value)))
            self.report_data_table.setItem(row_idx, 2, QTableWidgetItem(str(kpi_target)))

            diff = kpi_value - kpi_target
            diff_item = QTableWidgetItem(f"{diff:+.2f}" if isinstance(diff, (int,float)) else str(diff)) # format if number

            if diff >= 0:
                diff_item.setForeground(QColor('#27ae60'))
            else:
                diff_item.setForeground(QColor('#e74c3c'))
            self.report_data_table.setItem(row_idx, 3, diff_item)

        self.report_data_table.resizeColumnsToContents()

    def generate_budget_report(self, period):
        # Chart
        fig = plt.figure(figsize=(10, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        projects_data = main_db_manager.get_all_projects()
        if projects_data is None: projects_data = []

        # Filter out projects that are archived for budget report
        reportable_projects = []
        status_names_for_budget_table = []

        for p_dict in projects_data:
            status_id = p_dict.get('status_id')
            status_name = "Unknown"
            is_archival = False
            if status_id:
                status_setting = main_db_manager.get_status_setting_by_id(status_id)
                if status_setting:
                    status_name = status_setting.get('status_name', 'Unknown')
                    if status_setting.get('is_archival_status'):
                        is_archival = True

            if not is_archival:
                reportable_projects.append(p_dict)
                status_names_for_budget_table.append(status_name)

        reportable_projects.sort(key=lambda x: x.get('budget', 0), reverse=True)

        names = [p.get('project_name', 'N/A') for p in reportable_projects]
        budgets = [p.get('budget', 0.0) for p in reportable_projects]

        if not names:
             ax.text(0.5, 0.5, "No project budget data available.",
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=12, color='gray')
             ax.set_xticks([])
             ax.set_yticks([])
        else:
            bars = ax.bar(names, budgets, color='#f39c12')
            ax.set_title("Budget Distribution by Project (Active/Ongoing)")
            ax.set_ylabel("Budget (€)")

            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'€{height:,.2f}', ha='center', va='bottom')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

        self.graph_layout.addWidget(canvas)

        # Data
        self.report_data_table.setColumnCount(3)
        self.report_data_table.setHorizontalHeaderLabels(["Project", "Budget", "Status"])
        self.report_data_table.setRowCount(len(reportable_projects))

        for row_idx, p_dict in enumerate(reportable_projects):
            self.report_data_table.setItem(row_idx, 0, QTableWidgetItem(p_dict.get('project_name', 'N/A')))
            budget_val = p_dict.get('budget', 0.0)
            self.report_data_table.setItem(row_idx, 1, QTableWidgetItem(f"€{budget_val:,.2f}"))

            # Display the resolved status name
            self.report_data_table.setItem(row_idx, 2, QTableWidgetItem(status_names_for_budget_table[row_idx]))

        self.report_data_table.resizeColumnsToContents()

    def export_report(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Export Report", "", "PDF Files (*.pdf);;Excel Files (*.xlsx)", options=options)

        if file_name:
            try:
                if file_name.endswith('.pdf'):
                    # Export to PDF (simplified implementation)
                    QMessageBox.information(self, "PDF Export", "PDF functionality under development")
                elif file_name.endswith('.xlsx'):
                    # Export to Excel
                    data = []
                    headers = []

                    for col in range(self.report_data_table.columnCount()):
                        headers.append(self.report_data_table.horizontalHeaderItem(col).text())

                    for row in range(self.report_data_table.rowCount()):
                        row_data = []
                        for col in range(self.report_data_table.columnCount()):
                            item = self.report_data_table.item(row, col)
                            row_data.append(item.text() if item else "")
                        data.append(row_data)

                    df = pd.DataFrame(data, columns=headers)
                    df.to_excel(file_name, index=False)

                    self.statusBar().showMessage(f"Report exported to {file_name}", 3000)
                    QMessageBox.information(self, "Export Successful", f"The report has been successfully exported to {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred during export: {str(e)}")

    def show_add_member_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Team Member")
        dialog.setFixedSize(400, 500)

        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        email_edit = QLineEdit() # Added Email field
        role_combo = QComboBox()
        # These roles should ideally come from a configurable source or db.py if they become dynamic
        role_combo.addItems(["Project Manager", "Developer", "Designer", "HR", "Marketing", "Finance", "Other"])

        department_combo = QComboBox()
        department_combo.addItems(["IT", "HR", "Marketing", "Finance", "Management", "Operations", "Sales", "Other"])

        performance_spin = QSpinBox()
        performance_spin.setRange(0, 100) # Assuming performance is 0-100
        performance_spin.setValue(75) # Default value

        hire_date_edit = QDateEdit(QDate.currentDate()) # Renamed for clarity
        hire_date_edit.setCalendarPopup(True)
        hire_date_edit.setDisplayFormat("yyyy-MM-dd")

        active_checkbox = QCheckBox("Active Member") # Changed from status_combo to is_active (boolean)
        active_checkbox.setChecked(True)

        skills_edit = QLineEdit()
        skills_edit.setPlaceholderText("Skills separated by commas (e.g., Python, SQL)")

        notes_edit = QTextEdit()
        notes_edit.setPlaceholderText("Additional notes about the team member...")

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        layout.addRow("Full Name:", name_edit)
        layout.addRow("Email:", email_edit) # Added Email field
        layout.addRow("Role/Title:", role_combo)
        layout.addRow("Department:", department_combo)
        layout.addRow("Performance (%):", performance_spin)
        layout.addRow("Hire Date:", hire_date_edit)
        layout.addRow("Active:", active_checkbox) # Changed from status_combo
        layout.addRow("Skills:", skills_edit)
        layout.addRow("Notes:", notes_edit)
        layout.addRow(button_box)

        if dialog.exec_() == QDialog.Accepted:
            member_data = {
                'full_name': name_edit.text(),
                'email': email_edit.text(),
                'role_or_title': role_combo.currentText(),
                'department': department_combo.currentText(),
                'performance': performance_spin.value(),
                'hire_date': hire_date_edit.date().toString("yyyy-MM-dd"),
                'is_active': active_checkbox.isChecked(),
                'skills': skills_edit.text(),
                'notes': notes_edit.toPlainText()
                # user_id can be added here if linking to a User account, e.g. member_data['user_id'] = selected_user_id
            }

            if member_data['full_name'] and member_data['email']:
                new_member_id = main_db_manager.add_team_member(member_data)
                if new_member_id:
                    self.load_team_members()
                    self.log_activity(f"Added team member: {member_data['full_name']}")
                    self.statusBar().showMessage(f"Team member {member_data['full_name']} added successfully (ID: {new_member_id})", 3000)
                else:
                    QMessageBox.warning(self, "Error", f"Failed to add team member. Check logs. Email might be in use.")
            else:
                QMessageBox.warning(self, "Error", "Full name and email are required.")

    def edit_member(self, member_id_int): # member_id is int from db.py (team_member_id)
        member_data_from_db = main_db_manager.get_team_member_by_id(member_id_int)

        if member_data_from_db: # This is a dict
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Team Member")
            dialog.setFixedSize(400, 500) # Adjusted size if necessary

            layout = QFormLayout(dialog)

            name_edit = QLineEdit(member_data_from_db.get('full_name', ''))
            email_edit = QLineEdit(member_data_from_db.get('email', ''))

            role_combo = QComboBox()
            role_combo.addItems(["Project Manager", "Developer", "Designer", "HR", "Marketing", "Finance", "Other"])
            role_combo.setCurrentText(member_data_from_db.get('role_or_title', 'Other'))

            department_combo = QComboBox()
            department_combo.addItems(["IT", "HR", "Marketing", "Finance", "Management", "Operations", "Sales", "Other"])
            department_combo.setCurrentText(member_data_from_db.get('department', 'Other'))

            performance_spin = QSpinBox()
            performance_spin.setRange(0, 100)
            performance_spin.setValue(member_data_from_db.get('performance', 0))

            hire_date_str = member_data_from_db.get('hire_date', QDate.currentDate().toString("yyyy-MM-dd"))
            hire_date_edit = QDateEdit(QDate.fromString(hire_date_str, "yyyy-MM-dd"))
            hire_date_edit.setCalendarPopup(True)
            hire_date_edit.setDisplayFormat("yyyy-MM-dd")

            active_checkbox = QCheckBox("Active Member")
            active_checkbox.setChecked(member_data_from_db.get('is_active', True))

            skills_edit = QLineEdit(member_data_from_db.get('skills', ''))
            skills_edit.setPlaceholderText("Skills separated by commas")

            notes_edit = QTextEdit(member_data_from_db.get('notes', ''))
            notes_edit.setPlaceholderText("Additional notes...")

            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)

            layout.addRow("Full Name:", name_edit)
            layout.addRow("Email:", email_edit)
            layout.addRow("Role/Title:", role_combo)
            layout.addRow("Department:", department_combo)
            layout.addRow("Performance (%):", performance_spin)
            layout.addRow("Hire Date:", hire_date_edit)
            layout.addRow("Active:", active_checkbox)
            layout.addRow("Skills:", skills_edit)
            layout.addRow("Notes:", notes_edit)
            layout.addRow(button_box)

            if dialog.exec_() == QDialog.Accepted:
                updated_member_data = {
                    'full_name': name_edit.text(),
                    'email': email_edit.text(),
                    'role_or_title': role_combo.currentText(),
                    'department': department_combo.currentText(),
                    'performance': performance_spin.value(),
                    'hire_date': hire_date_edit.date().toString("yyyy-MM-dd"),
                    'is_active': active_checkbox.isChecked(),
                    'skills': skills_edit.text(),
                    'notes': notes_edit.toPlainText()
                }

                if updated_member_data['full_name'] and updated_member_data['email']:
                    success = main_db_manager.update_team_member(member_id_int, updated_member_data)
                    if success:
                        self.load_team_members()
                        self.log_activity(f"Updated team member: {updated_member_data['full_name']}")
                        self.statusBar().showMessage(f"Team member {updated_member_data['full_name']} updated successfully", 3000)
                    else:
                        QMessageBox.warning(self, "Error", f"Failed to update team member. Check logs. Email might be in use by another member.")
                else:
                    QMessageBox.warning(self, "Error", "Full name and email are required.")
            # No specific action if dialog is rejected (e.g. dialog.exec_() != QDialog.Accepted), so no 'else' here.
        else: # This is for: if member_data_from_db:
            QMessageBox.warning(self, "Error", f"Could not find team member with ID {member_id_int} to edit.")

    def delete_member(self, member_id_int): # member_id is int
        # Fetch member name for confirmation dialog, using the new db manager
        member_to_delete = main_db_manager.get_team_member_by_id(member_id_int)

        if not member_to_delete:
            QMessageBox.warning(self, "Error", f"Team member with ID {member_id_int} not found.")
            return

        member_name = member_to_delete.get('full_name', 'Unknown')

        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Are you sure you want to delete the member '{member_name}' (ID: {member_id_int})?\nThis action is permanent.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = main_db_manager.delete_team_member(member_id_int)
            if success:
                self.load_team_members()
                self.log_activity(f"Deleted team member: {member_name} (ID: {member_id_int})")
                self.statusBar().showMessage(f"Team member {member_name} deleted", 3000)
            else:
                QMessageBox.warning(self, "Error", f"Failed to delete team member {member_name}.")

    def show_add_project_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("New Project")
        dialog.setFixedSize(500, 550) # Increased height for client_id (if added) or more spacing

        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        desc_edit = QTextEdit()
        desc_edit.setPlaceholderText("Project description, including notes on key documents or links...")
        desc_edit.setMinimumHeight(100)

        start_date_edit = QDateEdit(QDate.currentDate())
        start_date_edit.setCalendarPopup(True)
        start_date_edit.setDisplayFormat("yyyy-MM-dd")

        deadline_edit = QDateEdit(QDate.currentDate().addMonths(1))
        deadline_edit.setCalendarPopup(True)
        deadline_edit.setDisplayFormat("yyyy-MM-dd")

        budget_spin = QDoubleSpinBox()
        budget_spin.setRange(0, 10000000) # Increased range
        budget_spin.setPrefix("€ ")
        budget_spin.setValue(10000)

        status_combo = QComboBox()
        project_statuses = main_db_manager.get_all_status_settings(status_type='Project')
        if project_statuses:
            for ps in project_statuses:
                status_combo.addItem(ps['status_name'], ps['status_id'])
        else:
            status_combo.addItem("Default Project Status", None) # Fallback

        priority_combo = QComboBox()
        priority_combo.addItems(["Low", "Medium", "High"]) # Display order
        priority_combo.setCurrentIndex(1) # Default to Medium

        manager_combo = QComboBox()
        manager_combo.addItem("Unassigned", None) # Option for no manager
        active_team_members = main_db_manager.get_all_team_members({'is_active': True})
        if active_team_members:
            for tm in active_team_members:
                # Store team_member_id, as we need it to fetch user_id later
                manager_combo.addItem(tm['full_name'], tm['team_member_id'])

        # Client ID handling - This is a new required field from db.py
        # For now, try to get first client, or show error. Ideally, a client selection dialog/combo.
        client_combo = QComboBox()
        all_clients = main_db_manager.get_all_clients()
        if all_clients:
            for client_item in all_clients:
                client_combo.addItem(client_item['client_name'], client_item['client_id'])
        else:
            client_combo.addItem("No Clients Available - Add one first!", None)
            client_combo.setEnabled(False)


        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        layout.addRow("Project Name:", name_edit)
        layout.addRow("Client:", client_combo) # Added Client selection
        layout.addRow("Description:", desc_edit)
        layout.addRow("Start Date:", start_date_edit)
        layout.addRow("Deadline:", deadline_edit)
        layout.addRow("Budget:", budget_spin)
        layout.addRow("Status:", status_combo)
        layout.addRow("Priority:", priority_combo)
        layout.addRow("Manager (Team Member):", manager_combo)
        layout.addRow(button_box)

        if dialog.exec_() == QDialog.Accepted:
            project_name = name_edit.text()
            client_id_selected = client_combo.currentData()

            if not project_name:
                QMessageBox.warning(self, "Error", "Project name is required.")
                return
            if not client_id_selected and client_combo.isEnabled(): # if combo is enabled, a client must be selected
                QMessageBox.warning(self, "Error", "A client must be selected for the project.")
                return
            if not client_id_selected and not client_combo.isEnabled(): # if disabled, means no clients
                 QMessageBox.warning(self, "Error", "Cannot add project: No clients available in the database. Please add a client first.")
                 return


            selected_manager_tm_id = manager_combo.currentData()
            manager_user_id_for_db = None
            if selected_manager_tm_id is not None:
                team_member_manager = main_db_manager.get_team_member_by_id(selected_manager_tm_id)
                if team_member_manager:
                    manager_user_id_for_db = team_member_manager.get('user_id')
                    # If user_id is None for this team_member, manager_user_id_for_db will be None (correct)

            priority_text = priority_combo.currentText()
            priority_for_db = 0 # Low
            if priority_text == "Medium": priority_for_db = 1
            elif priority_text == "High": priority_for_db = 2

            project_data_to_save = {
                'client_id': client_id_selected,
                'project_name': project_name,
                'description': desc_edit.toPlainText(),
                'start_date': start_date_edit.date().toString("yyyy-MM-dd"),
                'deadline_date': deadline_edit.date().toString("yyyy-MM-dd"),
                'budget': budget_spin.value(),
                'status_id': status_combo.currentData(),
                'progress_percentage': 0, # Default for new projects
                'manager_team_member_id': manager_user_id_for_db, # This is user_id or None
                'priority': priority_for_db
                # created_by_user_id could be set here if self.current_user is reliably populated
            }

            new_project_id = main_db_manager.add_project(project_data_to_save)

            if new_project_id:
                self.load_projects()
                self.update_project_filter() # This also needs refactoring later
                self.log_activity(f"Added project: {project_name}")
                self.statusBar().showMessage(f"Project {project_name} added successfully (ID: {new_project_id})", 3000)
            else:
                QMessageBox.warning(self, "Error", "Failed to add project. Check logs.")

    def edit_project(self, project_id_str): # project_id is TEXT from db.py
        project_data_dict = main_db_manager.get_project_by_id(project_id_str)

        if project_data_dict:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit Project: {project_data_dict.get('project_name', '')}")
            dialog.setFixedSize(500, 550)

            layout = QFormLayout(dialog)

            name_edit = QLineEdit(project_data_dict.get('project_name', ''))
            desc_edit = QTextEdit(project_data_dict.get('description', ''))
            desc_edit.setPlaceholderText("Project description...")
            desc_edit.setMinimumHeight(100)

            start_date_edit = QDateEdit(QDate.fromString(project_data_dict.get('start_date', ''), "yyyy-MM-dd"))
            start_date_edit.setCalendarPopup(True)
            start_date_edit.setDisplayFormat("yyyy-MM-dd")

            deadline_edit = QDateEdit(QDate.fromString(project_data_dict.get('deadline_date', ''), "yyyy-MM-dd"))
            deadline_edit.setCalendarPopup(True)
            deadline_edit.setDisplayFormat("yyyy-MM-dd")

            budget_spin = QDoubleSpinBox()
            budget_spin.setRange(0, 10000000)
            budget_spin.setPrefix("€ ")
            budget_spin.setValue(project_data_dict.get('budget', 0.0))

            status_combo = QComboBox()
            project_statuses = main_db_manager.get_all_status_settings(status_type='Project')
            current_status_id = project_data_dict.get('status_id')
            if project_statuses:
                for idx, ps in enumerate(project_statuses):
                    status_combo.addItem(ps['status_name'], ps['status_id'])
                    if ps['status_id'] == current_status_id:
                        status_combo.setCurrentIndex(idx)
            else: # Fallback if no statuses defined
                status_combo.addItem("No Statuses Defined", None)
                status_setting = main_db_manager.get_status_setting_by_id(current_status_id) # try to get current one by id
                if status_setting : status_combo.addItem(status_setting['status_name'], current_status_id)


            priority_combo = QComboBox()
            priority_combo.addItems(["Low", "Medium", "High"])
            db_priority = project_data_dict.get('priority', 0) # 0:Low, 1:Medium, 2:High
            if db_priority == 1: priority_combo.setCurrentText("Medium")
            elif db_priority == 2: priority_combo.setCurrentText("High")
            else: priority_combo.setCurrentText("Low")


            manager_combo = QComboBox()
            manager_combo.addItem("Unassigned", None)
            active_team_members = main_db_manager.get_all_team_members({'is_active': True})
            project_manager_user_id = project_data_dict.get('manager_team_member_id') # This is a user_id
            current_manager_tm_id_to_select = None

            if project_manager_user_id and active_team_members:
                for tm in active_team_members:
                    if tm['user_id'] == project_manager_user_id:
                        current_manager_tm_id_to_select = tm['team_member_id']
                        break

            if active_team_members:
                for idx, tm in enumerate(active_team_members):
                    manager_combo.addItem(tm['full_name'], tm['team_member_id'])
                    if tm['team_member_id'] == current_manager_tm_id_to_select:
                        manager_combo.setCurrentIndex(idx + 1) # +1 because of "Unassigned"

            client_combo = QComboBox()
            all_clients = main_db_manager.get_all_clients()
            current_client_id = project_data_dict.get('client_id')
            if all_clients:
                for idx, client_item in enumerate(all_clients):
                    client_combo.addItem(client_item['client_name'], client_item['client_id'])
                    if client_item['client_id'] == current_client_id:
                        client_combo.setCurrentIndex(idx)
            else: # Should not happen if project has a client_id
                client_combo.addItem("Error: Client not found or No Clients", None)
                client_combo.setEnabled(False)


            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)

            layout.addRow("Project Name:", name_edit)
            layout.addRow("Client:", client_combo)
            layout.addRow("Description:", desc_edit)
            layout.addRow("Start Date:", start_date_edit)
            layout.addRow("Deadline:", deadline_edit)
            layout.addRow("Budget:", budget_spin)
            layout.addRow("Status:", status_combo)
            layout.addRow("Priority:", priority_combo)
            layout.addRow("Manager (Team Member):", manager_combo)
            layout.addRow(button_box)

            if dialog.exec_() == QDialog.Accepted:
                project_name_updated = name_edit.text()
                client_id_updated = client_combo.currentData()

                if not project_name_updated:
                    QMessageBox.warning(self, "Error", "Project name is required.")
                    return
                if not client_id_updated:
                     QMessageBox.warning(self, "Error", "Client is required for the project.")
                     return

                selected_manager_tm_id_updated = manager_combo.currentData()
                manager_user_id_for_db_updated = None
                if selected_manager_tm_id_updated is not None:
                    tm_manager_updated = main_db_manager.get_team_member_by_id(selected_manager_tm_id_updated)
                    if tm_manager_updated:
                        manager_user_id_for_db_updated = tm_manager_updated.get('user_id')

                priority_text_updated = priority_combo.currentText()
                priority_for_db_updated = 0 # Low
                if priority_text_updated == "Medium": priority_for_db_updated = 1
                elif priority_text_updated == "High": priority_for_db_updated = 2

                updated_project_data_to_save = {
                    'client_id': client_id_updated,
                    'project_name': project_name_updated,
                    'description': desc_edit.toPlainText(),
                    'start_date': start_date_edit.date().toString("yyyy-MM-dd"),
                    'deadline_date': deadline_edit.date().toString("yyyy-MM-dd"),
                    'budget': budget_spin.value(),
                    'status_id': status_combo.currentData(),
                    # progress_percentage is not edited in this dialog, keep existing or set default if needed
                    'progress_percentage': project_data_dict.get('progress_percentage', 0),
                    'manager_team_member_id': manager_user_id_for_db_updated,
                    'priority': priority_for_db_updated
                }

                success = main_db_manager.update_project(project_id_str, updated_project_data_to_save)

                if success:
                    self.load_projects()
                    self.update_project_filter()
                    self.log_activity(f"Updated project: {project_name_updated}")
                    self.statusBar().showMessage(f"Project {project_name_updated} updated successfully", 3000)
                else:
                    QMessageBox.warning(self, "Error", "Failed to update project. Check logs.")
        else:
            QMessageBox.warning(self, "Error", f"Could not find project with ID {project_id_str} to edit.")

    def show_project_details(self, project_id_str): # project_id is TEXT
        project_dict = main_db_manager.get_project_by_id(project_id_str)

        if project_dict:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Project Details: {project_dict.get('project_name', 'N/A')}")
            dialog.setFixedSize(600, 500) # Keep or adjust size as needed

            layout = QVBoxLayout(dialog)

            # Basic information
            info_group = QGroupBox("Project Information")
            info_layout = QFormLayout(info_group)

            name_label = QLabel(project_dict.get('project_name', 'N/A'))
            name_label.setStyleSheet("font-size: 16px; font-weight: bold;")

            desc_label = QLabel(project_dict.get('description', "No description"))
            desc_label.setWordWrap(True)

            start_date_label = QLabel(project_dict.get('start_date', 'N/A'))
            deadline_label = QLabel(project_dict.get('deadline_date', 'N/A'))
            budget_label = QLabel(f"€{project_dict.get('budget', 0.0):,.2f}")

            status_id = project_dict.get('status_id')
            status_name_display = "Unknown"
            status_color_hex = "#7f8c8d"
            if status_id is not None:
                status_setting = main_db_manager.get_status_setting_by_id(status_id)
                if status_setting:
                    status_name_display = status_setting.get('status_name', 'Unknown')
                    color_from_db = status_setting.get('color_hex')
                    if color_from_db: status_color_hex = color_from_db
                    else: # Fallback colors
                        if "completed" in status_name_display.lower(): status_color_hex = '#2ecc71'
                        elif "progress" in status_name_display.lower(): status_color_hex = '#3498db'
                        elif "planning" in status_name_display.lower(): status_color_hex = '#f1c40f'
                        elif "late" in status_name_display.lower(): status_color_hex = '#e74c3c'
            status_display_label = QLabel(status_name_display)
            status_display_label.setStyleSheet(f"color: {status_color_hex}; font-weight: bold;")

            priority_val = project_dict.get('priority', 0)
            priority_display_label = QLabel()
            if priority_val == 2: priority_display_label.setText("High")
            elif priority_val == 1: priority_display_label.setText("Medium")
            else: priority_display_label.setText("Low")
            # Priority color can be added here too if desired

            progress_label = QLabel(f"{project_dict.get('progress_percentage', 0)}%")

            manager_user_id = project_dict.get('manager_team_member_id')
            manager_display_name = "Unassigned"
            if manager_user_id:
                tm_list = main_db_manager.get_all_team_members({'user_id': manager_user_id})
                if tm_list: manager_display_name = tm_list[0].get('full_name', manager_user_id)
                else:
                    user = main_db_manager.get_user_by_id(manager_user_id)
                    if user: manager_display_name = user.get('full_name', manager_user_id)
            manager_label = QLabel(manager_display_name)

            info_layout.addRow("Name:", name_label)
            info_layout.addRow("Description:", desc_label)
            info_layout.addRow("Start Date:", start_date_label)
            info_layout.addRow("Deadline:", deadline_label)
            info_layout.addRow("Budget:", budget_label)
            info_layout.addRow("Status:", status_display_label)
            info_layout.addRow("Priority:", priority_display_label)
            info_layout.addRow("Progress:", progress_label)
            info_layout.addRow("Manager:", manager_label)

            # Project tasks - Placeholder until Task management is refactored
            tasks_group = QGroupBox("Associated Tasks (To be refactored)")
            tasks_layout = QVBoxLayout(tasks_group)
            no_tasks_label = QLabel("Task display will be available after Task Management refactoring.")
            no_tasks_label.setAlignment(Qt.AlignCenter)
            tasks_layout.addWidget(no_tasks_label)
            # tasks_table = QTableWidget() ... (Old task loading logic commented out) ...
            # tasks_layout.addWidget(tasks_table)


            button_box = QDialogButtonBox(QDialogButtonBox.Close)
            button_box.rejected.connect(dialog.reject)

            layout.addWidget(info_group)
            layout.addWidget(tasks_group)
            layout.addWidget(button_box)

            dialog.exec_()
        else:
            QMessageBox.warning(self, "Error", f"Could not retrieve details for project ID {project_id_str}.")


    def delete_project(self, project_id_str): # project_id is TEXT
        project_to_delete = main_db_manager.get_project_by_id(project_id_str)

        if not project_to_delete:
            QMessageBox.warning(self, "Error", f"Project with ID {project_id_str} not found.")
            return

        project_name = project_to_delete.get('project_name', 'Unknown Project')

        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Are you sure you want to delete the project '{project_name}' (ID: {project_id_str})?\nThis will also delete all associated tasks and KPIs.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # db.py's delete_project should handle cascading deletes for Tasks and KPIs via FOREIGN KEY ON DELETE CASCADE
            success = main_db_manager.delete_project(project_id_str)
            if success:
                self.load_projects()
                self.update_project_filter() # This also needs refactoring later
                self.log_activity(f"Deleted project: {project_name} (ID: {project_id_str})")
                self.statusBar().showMessage(f"Project {project_name} deleted", 3000)
            else:
                QMessageBox.warning(self, "Error", f"Failed to delete project {project_name}. Check logs.")

    def show_add_task_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("New Task")
        dialog.setFixedSize(450, 450) # Slightly larger for better layout

        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Enter task name...")

        project_combo = QComboBox()
        all_projects = main_db_manager.get_all_projects() # Assuming this returns list of dicts
        if all_projects:
            for p in all_projects:
                # Assuming 'status_id' needs to be checked against 'completed' or 'archived' status types
                # This check might need main_db_manager.get_status_setting_by_id(p['status_id'])
                # For now, let's assume all projects fetched are valid for new tasks or filter simply.
                # A more robust check would involve fetching status details.
                # Simplified: project_combo.addItem(p['project_name'], p['project_id'])
                status_of_project = main_db_manager.get_status_setting_by_id(p['status_id'])
                is_completion = status_of_project.get('is_completion_status', False) if status_of_project else False
                is_archival = status_of_project.get('is_archival_status', False) if status_of_project else False

                if not is_completion and not is_archival : # only add if not completed or archived
                     project_combo.addItem(p['project_name'], p['project_id'])
        if project_combo.count() == 0:
            project_combo.addItem("No Active Projects Available", None)
            project_combo.setEnabled(False)


        desc_edit = QTextEdit()
        desc_edit.setPlaceholderText("Detailed task description...")
        desc_edit.setMinimumHeight(80)

        status_combo = QComboBox()
        task_statuses = main_db_manager.get_all_status_settings(status_type='Task')
        if task_statuses:
            for ts in task_statuses:
                if not ts.get('is_completion_status'): # Don't add "Completed" as initial status
                    status_combo.addItem(ts['status_name'], ts['status_id'])
        if status_combo.count() == 0:
             status_combo.addItem("No Task Statuses Defined", None) # Fallback
             status_combo.setEnabled(False)


        priority_combo = QComboBox()
        priority_combo.addItems(["Low", "Medium", "High"]) # Display order
        priority_combo.setCurrentIndex(1) # Default to Medium

        assignee_combo = QComboBox()
        assignee_combo.addItem("Unassigned", None) # team_member_id will be None
        active_team_members = main_db_manager.get_all_team_members({'is_active': True})
        if active_team_members:
            for tm in active_team_members:
                assignee_combo.addItem(tm['full_name'], tm['team_member_id'])

        deadline_edit = QDateEdit(QDate.currentDate().addDays(7))
        deadline_edit.setCalendarPopup(True)
        deadline_edit.setDisplayFormat("yyyy-MM-dd")

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        layout.addRow("Task Name:", name_edit)
        layout.addRow("Project:", project_combo)
        layout.addRow("Description:", desc_edit)
        layout.addRow("Status:", status_combo)
        layout.addRow("Priority:", priority_combo)
        layout.addRow("Assigned To:", assignee_combo)
        layout.addRow("Deadline:", deadline_edit)
        layout.addRow(button_box)

        if dialog.exec_() == QDialog.Accepted:
            task_name = name_edit.text()
            selected_project_id = project_combo.currentData()

            if not task_name:
                QMessageBox.warning(self, "Input Error", "Task name is required.")
                return
            if selected_project_id is None and project_combo.isEnabled():
                QMessageBox.warning(self, "Input Error", "A project must be selected.")
                return
            if not project_combo.isEnabled():
                 QMessageBox.warning(self, "Input Error", "Cannot add task: No active projects available.")
                 return
            if status_combo.currentData() is None and status_combo.isEnabled():
                 QMessageBox.warning(self, "Input Error", "A task status must be selected.")
                 return
            if not status_combo.isEnabled():
                 QMessageBox.warning(self, "Input Error", "Cannot add task: No task statuses defined.")
                 return


            priority_text = priority_combo.currentText()
            priority_for_db = 0 # Low
            if priority_text == "Medium": priority_for_db = 1
            elif priority_text == "High": priority_for_db = 2

            task_data_to_save = {
                'project_id': selected_project_id,
                'task_name': task_name,
                'description': desc_edit.toPlainText(),
                'status_id': status_combo.currentData(),
                'priority': priority_for_db,
                'assignee_team_member_id': assignee_combo.currentData(), # This is team_member_id or None
                'due_date': deadline_edit.date().toString("yyyy-MM-dd"),
                # 'reporter_team_member_id': self.current_user.get('id') if self.current_user else None
                #   ^ This assumes self.current_user.id is a team_member_id. db.py expects user_id for reporter.
                #   For now, let's get reporter_team_member_id if current_user has a team_member link
            }
            # Add reporter_team_member_id (needs team_member_id of current user)
            # This logic might be complex if current_user is just user info, not directly team_member info.
            # For now, omitting reporter_id or setting to None.
            # if self.current_user and self.current_user.get('id'): # This is user_id
            #    # How to get team_member_id from user_id of current user?
            #    # current_tm_list = main_db_manager.get_all_team_members({'user_id': self.current_user['id']})
            #    # if current_tm_list: task_data_to_save['reporter_team_member_id'] = current_tm_list[0]['team_member_id']
            #    pass


            new_task_id = main_db_manager.add_task(task_data_to_save)

            if new_task_id:
                self.load_tasks()
                self.log_activity(f"Added task: {task_name} (Project ID: {selected_project_id})")
                self.statusBar().showMessage(f"Task '{task_name}' added successfully (ID: {new_task_id})", 3000)
            else:
                QMessageBox.warning(self, "Database Error", "Failed to add task. Check logs.")

    def edit_task(self, task_id_int): # task_id is INT from db.py
        task_data_dict = main_db_manager.get_task_by_id(task_id_int)

        if task_data_dict:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit Task: {task_data_dict.get('task_name', '')}")
            dialog.setFixedSize(450, 450)

            layout = QFormLayout(dialog)

            name_edit = QLineEdit(task_data_dict.get('task_name', ''))

            project_combo = QComboBox()
            all_projects = main_db_manager.get_all_projects()
            current_project_id_for_task = task_data_dict.get('project_id')
            if all_projects:
                for idx, p in enumerate(all_projects):
                    # Similar logic as add_task_dialog for filtering projects if necessary
                    status_of_project = main_db_manager.get_status_setting_by_id(p['status_id'])
                    is_completion = status_of_project.get('is_completion_status', False) if status_of_project else False
                    is_archival = status_of_project.get('is_archival_status', False) if status_of_project else False
                    # Add to combo only if not completed/archived OR if it's the current project for the task
                    if (not is_completion and not is_archival) or p['project_id'] == current_project_id_for_task:
                        project_combo.addItem(p['project_name'], p['project_id'])
                        if p['project_id'] == current_project_id_for_task:
                            project_combo.setCurrentIndex(project_combo.count() -1) # Set current item
            if project_combo.count() == 0: # Fallback if current project is archived/completed
                 project_info = main_db_manager.get_project_by_id(current_project_id_for_task)
                 if project_info : project_combo.addItem(project_info['project_name'], project_info['project_id'])
                 project_combo.setEnabled(False)


            desc_edit = QTextEdit(task_data_dict.get('description', ''))
            desc_edit.setPlaceholderText("Detailed task description...")
            desc_edit.setMinimumHeight(80)

            status_combo = QComboBox()
            task_statuses = main_db_manager.get_all_status_settings(status_type='Task')
            current_status_id_for_task = task_data_dict.get('status_id')
            if task_statuses:
                for idx, ts in enumerate(task_statuses):
                    status_combo.addItem(ts['status_name'], ts['status_id'])
                    if ts['status_id'] == current_status_id_for_task:
                        status_combo.setCurrentIndex(idx)
            if status_combo.count() == 0: status_combo.setEnabled(False)


            priority_combo = QComboBox()
            priority_combo.addItems(["Low", "Medium", "High"])
            db_task_priority = task_data_dict.get('priority', 0)
            if db_task_priority == 1: priority_combo.setCurrentText("Medium")
            elif db_task_priority == 2: priority_combo.setCurrentText("High")
            else: priority_combo.setCurrentText("Low")

            assignee_combo = QComboBox()
            assignee_combo.addItem("Unassigned", None)
            active_team_members = main_db_manager.get_all_team_members({'is_active': True})
            current_assignee_tm_id = task_data_dict.get('assignee_team_member_id')
            if active_team_members:
                for idx, tm in enumerate(active_team_members):
                    assignee_combo.addItem(tm['full_name'], tm['team_member_id'])
                    if tm['team_member_id'] == current_assignee_tm_id:
                        assignee_combo.setCurrentIndex(idx + 1) # +1 for "Unassigned"

            due_date_str = task_data_dict.get('due_date', QDate.currentDate().toString("yyyy-MM-dd"))
            deadline_edit = QDateEdit(QDate.fromString(due_date_str, "yyyy-MM-dd"))
            deadline_edit.setCalendarPopup(True)
            deadline_edit.setDisplayFormat("yyyy-MM-dd")

            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)

            layout.addRow("Task Name:", name_edit)
            layout.addRow("Project:", project_combo)
            layout.addRow("Description:", desc_edit)
            layout.addRow("Status:", status_combo)
            layout.addRow("Priority:", priority_combo)
            layout.addRow("Assigned To:", assignee_combo)
            layout.addRow("Deadline:", deadline_edit)
            layout.addRow(button_box)

            if dialog.exec_() == QDialog.Accepted:
                updated_task_name = name_edit.text()
                updated_project_id = project_combo.currentData()

                if not updated_task_name:
                    QMessageBox.warning(self, "Input Error", "Task name is required.")
                    return
                if updated_project_id is None and project_combo.isEnabled():
                     QMessageBox.warning(self, "Input Error", "A project must be selected.")
                     return
                if status_combo.currentData() is None and status_combo.isEnabled():
                     QMessageBox.warning(self, "Input Error", "A task status must be selected.")
                     return

                updated_priority_text = priority_combo.currentText()
                updated_priority_for_db = 0
                if updated_priority_text == "Medium": updated_priority_for_db = 1
                elif updated_priority_text == "High": updated_priority_for_db = 2

                task_data_to_update = {
                    'project_id': updated_project_id,
                    'task_name': updated_task_name,
                    'description': desc_edit.toPlainText(),
                    'status_id': status_combo.currentData(),
                    'priority': updated_priority_for_db,
                    'assignee_team_member_id': assignee_combo.currentData(),
                    'due_date': deadline_edit.date().toString("yyyy-MM-dd"),
                }
                # Check if status is a completion status to update 'completed_at'
                selected_status_id = status_combo.currentData()
                if selected_status_id:
                    status_details = main_db_manager.get_status_setting_by_id(selected_status_id)
                    if status_details and status_details.get('is_completion_status'):
                        task_data_to_update['completed_at'] = datetime.utcnow().isoformat() + "Z"
                    else: # Not a completion status, ensure completed_at is None (or its existing value if partial updates allowed)
                        task_data_to_update['completed_at'] = None


                success = main_db_manager.update_task(task_id_int, task_data_to_update)

                if success:
                    self.load_tasks()
                    self.log_activity(f"Updated task: {updated_task_name} (ID: {task_id_int})")
                    self.statusBar().showMessage(f"Task '{updated_task_name}' updated successfully", 3000)
                else:
                    QMessageBox.warning(self, "Database Error", f"Failed to update task ID {task_id_int}. Check logs.")
        else:
            QMessageBox.warning(self, "Error", f"Could not find task with ID {task_id_int} to edit.")

    def complete_task(self, task_id_int): # task_id is INT
        task_to_complete = main_db_manager.get_task_by_id(task_id_int)
        if not task_to_complete:
            QMessageBox.warning(self, "Error", f"Task with ID {task_id_int} not found.")
            return

        task_name = task_to_complete.get('task_name', 'Unknown Task')

        # Find a 'completion' status for tasks
        completed_status_id = None
        task_statuses = main_db_manager.get_all_status_settings(status_type='Task')
        if task_statuses:
            for ts in task_statuses:
                if ts.get('is_completion_status'):
                    completed_status_id = ts['status_id']
                    break

        if completed_status_id is None:
            # Fallback: try to find by a common name like "Completed" or "Done" if no explicit flag found
            # This part might need adjustment based on actual status names in db.
            for common_completion_name in ["Completed", "Done"]:
                status_obj = main_db_manager.get_status_setting_by_name(common_completion_name, 'Task')
                if status_obj:
                    completed_status_id = status_obj['status_id']
                    break
            if completed_status_id is None: # Still not found
                QMessageBox.warning(self, "Configuration Error", "No 'completion' status defined for tasks in StatusSettings.")
                return

        update_data = {
            'status_id': completed_status_id,
            'completed_at': datetime.utcnow().isoformat() + "Z"
        }
        success = main_db_manager.update_task(task_id_int, update_data)

        if success:
            self.load_tasks()
            self.log_activity(f"Task marked as completed: {task_name} (ID: {task_id_int})")
            self.statusBar().showMessage(f"Task '{task_name}' marked as completed", 3000)
        else:
            QMessageBox.warning(self, "Database Error", f"Failed to complete task '{task_name}'. Check logs.")


    def delete_task(self, task_id_int): # task_id is INT
        task_to_delete = main_db_manager.get_task_by_id(task_id_int)
        if not task_to_delete:
            QMessageBox.warning(self, "Error", f"Task with ID {task_id_int} not found.")
            return

        task_name = task_to_delete.get('task_name', 'Unknown Task')

        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Are you sure you want to delete the task '{task_name}' (ID: {task_id_int})?\nThis action is permanent.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = main_db_manager.delete_task(task_id_int)
            if success:
                self.load_tasks()
                self.log_activity(f"Deleted task: {task_name} (ID: {task_id_int})")
                self.statusBar().showMessage(f"Task '{task_name}' deleted", 3000)
            else:
                QMessageBox.warning(self, "Database Error", f"Failed to delete task '{task_name}'. Check logs.")

    def edit_user_access(self, user_id_str): # user_id is now a string (UUID) from db.py
        user_data = main_db_manager.get_user_by_id(user_id_str)

        if user_data: # user_data is a dict
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit Access for {user_data.get('full_name', 'N/A')}")
                dialog.setFixedSize(300, 200)

                layout = QFormLayout(dialog)

                username_label = QLabel(user_data.get('username', 'N/A'))
                name_label = QLabel(user_data.get('full_name', 'N/A'))

                role_combo = QComboBox()
                role_combo.addItems(["Administrator", "Manager", "User"]) # These should match roles in db.py
                                                                        # Consider fetching roles if they become dynamic
                role_map = { # Assuming roles in db.py are 'admin', 'manager', 'member' or similar
                    "admin": "Administrator",
                    "manager": "Manager",
                    "member": "User", # Adjust if db.py uses 'user'
                    # Add other roles from db.py if necessary
                }
                # db.py stores roles like 'admin', 'manager', 'member'
                # Need to map them to display names if different, or use db.py roles directly in combo
                current_role_in_db = user_data.get('role', 'member') # Default to 'member' or a base role

                # Find the display name for the current role from db
                display_role = "User" # Default display
                for db_role_val, display_name_val in role_map.items():
                    if db_role_val == current_role_in_db:
                        display_role = display_name_val
                        break
                role_combo.setCurrentText(display_role)


                button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                button_box.accepted.connect(dialog.accept)
                button_box.rejected.connect(dialog.reject)

                layout.addRow("Username:", username_label)
                layout.addRow("Full Name:", name_label)
                layout.addRow("Role:", role_combo)
                layout.addRow(button_box)

                if dialog.exec_() == QDialog.Accepted:
                    selected_display_role = role_combo.currentText()
                    # Convert display role back to db.py role value
                    new_role_for_db = 'member' # default
                    for db_r, disp_r in role_map.items():
                        if disp_r == selected_display_role:
                            new_role_for_db = db_r
                            break

                    update_success = main_db_manager.update_user(user_id_str, {'role': new_role_for_db})

                    if update_success:
                        self.load_access_table() # This will also need refactoring
                        self.log_activity(f"Updated role of {user_data.get('full_name')} to {new_role_for_db}")
                        self.statusBar().showMessage(f"Role of {user_data.get('full_name')} updated", 3000)
                    else:
                        QMessageBox.warning(self, "Error", f"Failed to update role for {user_data.get('full_name')}")


    def save_account_settings(self):
        if not self.current_user or 'id' not in self.current_user:
            QMessageBox.warning(self, "Error", "You must be logged in to modify your settings.")
            return

        user_id_to_update = self.current_user['id']
        current_username = self.current_user['username'] # Needed for password verification

        full_name = self.name_edit.text()
        email = self.email_edit.text()
        phone = self.phone_edit.text()
        current_pwd = self.current_pwd_edit.text()
        new_pwd = self.new_pwd_edit.text()
        confirm_pwd = self.confirm_pwd_edit.text()

        if not full_name or not email:
            QMessageBox.warning(self, "Error", "Full name and email are required.")
            return

        if new_pwd and (new_pwd != confirm_pwd):
            QMessageBox.warning(self, "Error", "New passwords do not match.")
            return

        update_data = {
            'full_name': full_name,
            'email': email,
            'phone': phone if phone else None # Pass None if empty, db.py should handle it
        }

        # Verify current password if a new one is provided
        if new_pwd:
            if not current_pwd:
                QMessageBox.warning(self, "Error", "Current password is required to set a new password.")
                return

            verified_user = main_db_manager.verify_user_password(current_username, current_pwd)
            if not verified_user or verified_user['user_id'] != user_id_to_update:
                QMessageBox.warning(self, "Error", "Current password is incorrect.")
                return
            # If password is correct, add new password to update_data.
            # main_db_manager.update_user will handle hashing.
            update_data['password'] = new_pwd

        # Update user information via main_db_manager
        success = main_db_manager.update_user(user_id_to_update, update_data)

        if success:
            # Update current user information in the session
            self.current_user['full_name'] = full_name
            self.current_user['email'] = email
            # self.current_user['phone'] = phone # If you store it in self.current_user
            self.user_name.setText(full_name) # Update UI

            self.log_activity("Updated account information")
            QMessageBox.information(self, "Success", "Changes have been saved.")

            # Clear password fields
            self.current_pwd_edit.clear()
            self.new_pwd_edit.clear()
            self.confirm_pwd_edit.clear()
        else:
            QMessageBox.warning(self, "Error", "Failed to update account information.")

    def save_preferences(self):
        if not self.current_user or 'id' not in self.current_user: # Check for id too
            QMessageBox.warning(self, "Error", "You must be logged in to modify your preferences.")
            return

        theme = self.theme_combo.currentText()
        density = self.density_combo.currentText()
        language = self.language_combo.currentText()
        email_notif = self.email_notif.isChecked()
        app_notif = self.app_notif.isChecked()
        sms_notif = self.sms_notif.isChecked()

        # Here you could save these preferences to the database
        # For this example, we will just display a message

        QMessageBox.information(
            self,
            "Preferences Saved",
            f"Your preferences have been saved:\n"
            f"Theme: {theme}\n"
            f"Density: {density}\n"
            f"Language: {language}\n"
            f"Notifications: Email {'enabled' if email_notif else 'disabled'}, "
            f"App {'enabled' if app_notif else 'disabled'}, "
            f"SMS {'enabled' if sms_notif else 'disabled'}"
        )

        self.log_activity("Updated user preferences")

    def add_on_page(self):
        from Installsweb.installmodules import InstallerDialog
        installer = InstallerDialog(self)
        installer.exec_()

    def open_facebook(self):
        #self.hide()  # Hide the login module
        tab_name = "FB Robot"  # Name of the tab (matches the label used in add_custom_tab)

        # Check if a tab with this name already exists
        existing_tab_index = self.find_tab_by_name(tab_name)
        if existing_tab_index != -1:
            # If the tab already exists, select it
            self.main_app.tab_widget.setCurrentIndex(existing_tab_index)
            return

        # Otherwise, create a single instance of Nova360ProApp and add a new tab
        if not hasattr(self, 'nova360pro') or self.nova360pro is None:
           # self.nova360pro = Nova360ProApp(main_app=self)  # Create the instance once
            self.face_main = FaceMainWindow()  # Replace this with your home page class

        self.open_new_tab(tab_name,"cool.ico",self.face_main)

        # subprocess.Popen([sys.executable, "main_fb_robot.py"])

    def change_page(self, index):
        self.main_content.setCurrentIndex(index)

        # Update navigation button styles
        for btn in self.nav_buttons:
            btn.setObjectName("")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self.nav_buttons[index].setObjectName("selected")
        self.nav_buttons[index].style().unpolish(self.nav_buttons[index])
        self.nav_buttons[index].style().polish(self.nav_buttons[index])

        # Update data if necessary
        if index == 0:  # Dashboard
            self.update_dashboard()
        elif index == 1:  # Team
            self.load_team_members()
        elif index == 2:  # Projects
            self.load_projects()
        elif index == 3:  # Tasks
            self.load_tasks()
        elif index == 4:  # Reports
            # Reports are generated on demand, but ensure dependencies are loaded if any page change logic was here
            pass
        elif index == 5:  # Settings
            self.load_access_table() # Ensure user data is loaded for settings page

    # closeEvent is typically for QMainWindow. If this widget is embedded,
    # the main application's closeEvent will handle application closure.
    # def closeEvent(self, event):
    #     if self.current_user:
    #         self.log_activity(f"Application closed by {self.current_user['full_name']}")
    #     event.accept()

if __name__ == "__main__":
    # This block is for standalone testing of MainDashboard
    app = QApplication(sys.argv)

    # Global style
    app.setStyle("Fusion")

    # Default font
    font = QFont()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)

    # For standalone testing, create a dummy current_user or trigger login
    # Example: No user passed, MainDashboard might trigger its own login
    # window = MainDashboard()

    # Example: With a dummy user
    dummy_user = {
        'id': 'test_user_uuid',
        'user_id': 'test_user_uuid', # Ensure this matches what db.py expects
        'username': 'testuser',
        'full_name': 'Test User Standalone',
        'email': 'test@example.com',
        'role': 'admin'
    }
    # Initialize db (important for standalone test if db.py relies on it being called)
    main_db_manager.initialize_database()

    # Create a dummy QMainWindow to host the QWidget for testing
    test_host_window = QMainWindow()
    test_host_window.setWindowTitle("Standalone Project Dashboard Test")

    # Pass the dummy user to the dashboard
    dashboard_widget = MainDashboard(parent=test_host_window, current_user=dummy_user)

    test_host_window.setCentralWidget(dashboard_widget) # Host it in a QMainWindow for testing
    test_host_window.setGeometry(100, 100, 1400, 900) # Set geometry on the host window
    test_host_window.show()

    sys.exit(app.exec_())

[end of projectManagement.py]
