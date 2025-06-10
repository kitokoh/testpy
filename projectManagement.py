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
from PyQt5.QtCore import QSize, QRect
from PyQt5.QtWidgets import QLabel, QPushButton, QFrame, QHBoxLayout, QVBoxLayout, QSpacerItem, QSizePolicy, QAbstractItemView
import db as db_manager # Standardized to db_manager
from db import get_status_setting_by_id, get_all_status_settings # For NotificationManager status checks
from PyQt5.QtWidgets import QAbstractItemView # Ensure this is imported
import math # Added for pagination
import json # For CoverPageEditorDialog style_config_json
import os # For CoverPageEditorDialog logo_name
from dashboard_extensions import ProjectTemplateManager # Added for Project Templates


class CustomNotificationBanner(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel) # or QFrame.Box, QFrame.Panel
        self.setObjectName("customNotificationBanner")

        # Initial styling - MOVED to style.qss

        self.setFixedHeight(50)
        self.setFixedWidth(350)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5) # Adjust margins as needed

        self.icon_label = QLabel("ℹ️") # Default icon
        self.icon_label.setObjectName("notificationIconLabel")
        self.icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        self.message_label = QLabel("Notification message will appear here.")
        self.message_label.setObjectName("notificationMessageLabel")
        self.message_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.message_label.setWordWrap(True)

        self.close_button = QPushButton("X")
        self.close_button.setObjectName("notificationCloseButton")
        self.close_button.setToolTip("Close")
        self.close_button.setFixedSize(25, 25) # Small fixed size for 'X' button
        # Stylesheet MOVED to style.qss
        self.close_button.clicked.connect(self.hide)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.message_label)
        layout.addStretch()
        layout.addWidget(self.close_button)

        self.hide() # Hidden by default

    def set_message(self, title, message):
        full_message = f"<b>{title}</b><br>{message}"
        self.message_label.setText(full_message)

        # Update icon based on title (simple emoji logic)
        if "error" in title.lower() or "alert" in title.lower():
            self.icon_label.setText("⚠️")
        elif "success" in title.lower():
            self.icon_label.setText("✅")
        elif "urgent" in title.lower() or "reminder" in title.lower():
            self.icon_label.setText("🔔") # Bell for urgent/reminder
        else:
            self.icon_label.setText("ℹ️") # Default info icon


class NotificationManager:
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.timer = QTimer(parent_window)
        self.notification_banner = CustomNotificationBanner(parent_window)
        # Ensure the banner is raised to be on top of other widgets within its parent
        self.notification_banner.raise_()

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
            all_projects = db_manager.get_all_projects() # Changed main_db_manager to db_manager
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
                tasks_for_project = db_manager.get_tasks_by_project_id(p.get('project_id')) # Changed main_db_manager
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
        self.notification_banner.set_message(title, message)

        if self.parent_window:
            parent_width = self.parent_window.width()
            banner_width = self.notification_banner.width()

            # Position banner at top-right with 10px margin
            x = parent_width - banner_width - 10
            y = 10
            self.notification_banner.move(x, y)

        self.notification_banner.show()
        self.notification_banner.raise_() # Ensure it's on top of other widgets

        # Auto-hide after 7 seconds
        QTimer.singleShot(7000, self.notification_banner.hide)
        print(f"Showing custom notification: {title} - {message}") # For debugging


class MainDashboard(QWidget): # Changed from QMainWindow to QWidget
    def __init__(self, parent=None, current_user=None): # Added current_user parameter
        super().__init__(parent)
        self.current_user = current_user # Use passed-in user
        self.template_manager = ProjectTemplateManager() # Initialize ProjectTemplateManager

        # Task Page Pagination state
        self.current_task_offset = 0
        self.TASK_PAGE_LIMIT = 30  # Or a suitable default
        self.total_tasks_count = 0

        # Stylesheet moved to global style.qss or specific object names
        # self.setStyleSheet(""" ... """) # Removed

        self._main_layout = QVBoxLayout(self) # Set layout directly on QWidget
        self._main_layout.setContentsMargins(0,0,0,0)
        self._main_layout.setSpacing(0)

        self.init_ui() # Initialize UI components

        if self.current_user: # If user is passed, update UI and load data
            self.user_name.setText(self.current_user.get('full_name', "N/A"))
            self.user_role.setText(self.current_user.get('role', "N/A").capitalize())
            self.load_initial_data()
        else: # No user passed, potentially show internal login or a message
            self.user_name.setText("Guest (No User Context)")
            self.user_role.setText("Limited Functionality")

        self.notification_manager = NotificationManager(self) # Pass self (dashboard) as parent
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
        self.topbar.setObjectName("mainDashboardTopbar") # Added object name for QSS
        self._main_layout.addWidget(self.topbar) # Add topbar to self._main_layout

        # Main content
        self.main_content = QStackedWidget()
        self.main_content.setObjectName("mainDashboardContentArea") # Added object name for QSS
        # self.main_content.setStyleSheet("""
            # QStackedWidget {
                # background-color: #ffffff;
            # }
        # """) # Moved to QSS

        # Pages
        self.setup_dashboard_page()
        self.setup_team_page()
        self.setup_projects_page()
        self.setup_tasks_page()
        self.setup_reports_page()
        self.setup_settings_page()
        self.setup_cover_page_management_page() # New page

        # Add main content below the topbar
        self._main_layout.addWidget(self.main_content) # Add main_content to self._main_layout

        # Status bar removed - self.statusBar().showMessage("Ready")

        # Check if user is logged in - Handled in __init__ now
        # if not self.current_user:
        #     # This might be shown if __init__ doesn't receive a user.
        #     # self.show_login_dialog()
        #     pass


    def setup_topbar(self):
        self.topbar = QFrame() # Object name set in init_ui
        self.topbar.setFixedHeight(70)
        # self.topbar.setStyleSheet(""" ... """) # Styles moved to QSS via #mainDashboardTopbar

        topbar_layout = QHBoxLayout(self.topbar)
        topbar_layout.setContentsMargins(15, 10, 15, 10)
        topbar_layout.setSpacing(20)

        # Logo and title - Left side
        logo_container = QHBoxLayout()
        logo_container.setSpacing(10)

        logo_icon = QLabel()
        logo_icon.setPixmap(QIcon(":/icons/logo.svg").pixmap(45, 45))

        logo_text = QLabel("Management Pro")
        logo_text.setObjectName("dashboardLogoText")
        # logo_text.setStyleSheet(""" ... """) # Moved to QSS

        logo_container.addWidget(logo_icon)
        logo_container.addWidget(logo_text)
        topbar_layout.addLayout(logo_container)

        # Central space for menus
        topbar_layout.addStretch(1)

        # Main Menu - Center
        self.nav_buttons = []

        # Dashboard button (single)
        dashboard_btn = QPushButton("Dashboard")
        dashboard_btn.setIcon(QIcon(":/icons/dashboard.svg"))
        dashboard_btn.clicked.connect(lambda: self.change_page(0))
        self.nav_buttons.append(dashboard_btn)
        topbar_layout.addWidget(dashboard_btn)

        # Management Menu (Team + Settings)
        management_menu = QMenu()
        management_menu.addAction(
            QIcon(":/icons/team.svg"),
            "Team",
            lambda: self.change_page(1)
        )
        management_menu.addAction(
            QIcon(":/icons/settings.svg"),
            "Settings",
            lambda: self.change_page(5)
        )

        management_menu.addAction(
            QIcon(":/icons/bell.svg"),
            "Notifications",
            lambda: self.gestion_notification()
        )
        management_menu.addAction(
            QIcon(":/icons/help-circle.svg"),
            "Client Support",
            lambda: self.gestion_sav()
        )
        management_menu.addAction(
            QIcon(":/icons/users.svg"),
            "Prospect",
            lambda: self.gestion_prospects()
        )
        management_menu.addAction(
            QIcon(":/icons/file-text.svg"),
            "Documents",
            lambda: self.gestion_documents()
        )
        management_menu.addAction(
            QIcon(":/icons/book.svg"),
            "Contacts",
            lambda: self.gestion_contacts()
        )

        management_btn = QPushButton("Management")
        management_btn.setIcon(QIcon(":/icons/briefcase.svg"))
        management_btn.setMenu(management_menu)
        management_btn.setObjectName("menu_button")
        self.nav_buttons.append(management_btn)
        topbar_layout.addWidget(management_btn)

        # Projects Menu (Projects + Tasks + Reports)
        projects_menu = QMenu()
        projects_menu.addAction(
            QIcon(":/icons/folder.svg"),
            "Projects",
            lambda: self.change_page(2)
        )
        projects_menu.addAction(
            QIcon(":/icons/check-square.svg"),
            "Tasks",
            lambda: self.change_page(3)
        )
        projects_menu.addAction(
            QIcon(":/icons/bar-chart-2.svg"),
            "Reports",
            lambda: self.change_page(4)
        )
        projects_menu.addAction(
            QIcon(":/icons/layout.svg"),
            "Cover Pages",
            lambda: self.change_page(6)
        )

        projects_btn = QPushButton("Activities")
        projects_btn.setIcon(QIcon(":/icons/activity.svg"))
        projects_btn.setMenu(projects_menu)
        projects_btn.setObjectName("menu_button")
        self.nav_buttons.append(projects_btn)
        topbar_layout.addWidget(projects_btn)

        # Add-on button (single)
        add_on_btn = QPushButton("Add-on")
        add_on_btn.setIcon(QIcon(":/icons/plus-circle.svg"))
        add_on_btn.clicked.connect(lambda: self.add_on_page())
        self.nav_buttons.append(add_on_btn)
        topbar_layout.addWidget(add_on_btn)

        topbar_layout.addStretch(1)

        # User section - Right side
        user_container = QHBoxLayout()
        user_container.setSpacing(10)

        # User avatar
        user_avatar = QLabel()
        user_avatar.setPixmap(QIcon(":/icons/user.svg").pixmap(35, 35))
        user_avatar.setObjectName("userAvatarLabel")
        # user_avatar.setStyleSheet("border-radius: 17px; border: 2px solid #3498db;") # Moved to QSS

        # User info
        user_info = QVBoxLayout()
        user_info.setSpacing(0)

        self.user_name = QLabel("Guest")
        self.user_name.setObjectName("UserFullNameLabel")
        # self.user_name.setStyleSheet("""...""") # Moved to QSS

        self.user_role = QLabel("Not logged in")
        self.user_role.setObjectName("UserRoleLabel")
        # self.user_role.setStyleSheet("""...""") # Moved to QSS

        user_info.addWidget(self.user_name)
        user_info.addWidget(self.user_role)

        user_container.addWidget(user_avatar)
        user_container.addLayout(user_info)

        # Logout button
        logout_btn = QPushButton()
        logout_btn.setIcon(QIcon(":/icons/log-out.svg"))
        logout_btn.setIconSize(QSize(20, 20))
        logout_btn.setToolTip("Logout")
        logout_btn.setFixedSize(35, 35)
        logout_btn.setObjectName("logoutButtonTopbar")
        # logout_btn.setStyleSheet(""" ... """) # Moved to QSS
        logout_btn.clicked.connect(self.logout)

        user_container.addWidget(logout_btn)

        user_widget = QWidget()
        user_widget.setLayout(user_container)
        topbar_layout.addWidget(user_widget)

        # Mark dashboard as selected by default
        self.nav_buttons[0].setObjectName("selected")

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

        # Heajjjder
        header = QWidget()
        header_layout = QHBoxLayout(header)

        title = QLabel("Management Dashboard")
        title.setObjectName("pageTitleLabel")

        self.date_picker = QDateEdit(QDate.currentDate())
        self.date_picker.setCalendarPopup(True)
        # Global style applies
        self.date_picker.dateChanged.connect(self.update_dashboard)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setIcon(QIcon(":/icons/refresh-cw.svg"))
        refresh_btn.setObjectName("primaryButton")
        # Global style applies
        refresh_btn.clicked.connect(self.update_dashboard)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.date_picker)
        header_layout.addWidget(refresh_btn)

        # KPIs
        self.kpi_widget = QWidget()
        self.kpi_layout = QHBoxLayout(self.kpi_widget)
        self.kpi_layout.setSpacing(15)

        # Charts
        graph_widget = QWidget()
        graph_layout = QHBoxLayout(graph_widget)
        graph_layout.setSpacing(15)

        # Performance chart
        self.performance_graph = pg.PlotWidget()
        self.performance_graph.setBackground('w')
        self.performance_graph.setTitle("Team Performance", color='#333333', size='12pt')
        self.performance_graph.showGrid(x=True, y=True)
        self.performance_graph.setMinimumHeight(300)

        # Project progress chart
        self.project_progress_graph = pg.PlotWidget()
        self.project_progress_graph.setBackground('w')
        self.project_progress_graph.setTitle("Project Progress", color='#333333', size='12pt')
        self.project_progress_graph.showGrid(x=True, y=True)
        self.project_progress_graph.setMinimumHeight(300)

        graph_layout.addWidget(self.performance_graph, 1)
        graph_layout.addWidget(self.project_progress_graph, 1)

        # Recent activities
        activities_widget = QGroupBox("Recent Activities")
        # Removed specific QGroupBox stylesheet, global style applies

        activities_layout = QVBoxLayout(activities_widget)
        activities_layout.setContentsMargins(10, 10, 10, 10) # Padding inside groupbox

        self.activities_table = QTableWidget()
        self.activities_table.setColumnCount(4)
        self.activities_table.setHorizontalHeaderLabels(["Date", "Member", "Action", "Details"])
        # Removed specific QTableWidget stylesheet, global style applies
        self.activities_table.verticalHeader().setVisible(False)
        self.activities_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.activities_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.activities_table.setSortingEnabled(True)

        activities_layout.addWidget(self.activities_table)

        layout.addWidget(header)
        layout.addWidget(self.kpi_widget)
        layout.addWidget(graph_widget)
        layout.addWidget(activities_widget)

        self.main_content.addWidget(page)

    def setup_team_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)

        title = QLabel("Team Management")
        title.setObjectName("pageTitleLabel")

        self.add_member_btn = QPushButton("Add Member")
        self.add_member_btn.setIcon(QIcon(":/icons/user-plus.svg"))
        self.add_member_btn.setObjectName("primaryButton")
        # Global style applies
        self.add_member_btn.clicked.connect(self.show_add_member_dialog)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.add_member_btn)

        # Filters
        filters = QWidget()
        filters_layout = QHBoxLayout(filters)

        self.team_search = QLineEdit()
        self.team_search.setPlaceholderText("Search a member...")
        # Removed specific QLineEdit stylesheet, global style applies
        self.team_search.textChanged.connect(self.filter_team_members)

        self.role_filter = QComboBox()
        self.role_filter.addItems(["All Roles", "Project Manager", "Developer", "Designer", "HR", "Marketing", "Finance"])
        # Removed specific QComboBox stylesheet, global style applies
        self.role_filter.currentIndexChanged.connect(self.filter_team_members)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Statuses", "Active", "Inactive", "On Leave"])
        # Removed specific QComboBox stylesheet, global style applies
        self.status_filter.currentIndexChanged.connect(self.filter_team_members)

        filters_layout.addWidget(self.team_search)
        filters_layout.addWidget(self.role_filter)
        filters_layout.addWidget(self.status_filter)

        # Team table
        self.team_table = QTableWidget()
        # Adjusted column count and labels for new fields
        self.team_table.setColumnCount(10)
        self.team_table.setHorizontalHeaderLabels([
            "Name", "Email", "Role/Title", "Department", "Hire Date",
            "Performance", "Skills", "Active", "Tasks", "Actions"
        ])
        # Removed specific QTableWidget stylesheet, global style applies
        self.team_table.verticalHeader().setVisible(False)
        self.team_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.team_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.team_table.setSortingEnabled(True)
        self.team_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        layout.addWidget(header)
        layout.addWidget(filters)
        layout.addWidget(self.team_table)

        self.main_content.addWidget(page)

    def setup_projects_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)

        title = QLabel("Project Management")
        title.setObjectName("pageTitleLabel")

        self.add_project_btn = QPushButton("New Project")
        self.add_project_btn.setIcon(QIcon(":/icons/plus-square.svg"))
        self.add_project_btn.setObjectName("primaryButton")
        # Global style applies
        self.add_project_btn.clicked.connect(self.show_add_project_dialog)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.add_project_btn)

        # Filters
        filters = QWidget()
        filters_layout = QHBoxLayout(filters)

        self.project_search = QLineEdit()
        self.project_search.setPlaceholderText("Search a project...")
        # Removed specific QLineEdit stylesheet, global style applies
        self.project_search.textChanged.connect(self.filter_projects)

        self.status_filter_proj = QComboBox()
        self.status_filter_proj.addItems(["All Statuses", "Planning", "In Progress", "Late", "Completed", "Archived"])
        # Removed specific QComboBox stylesheet, global style applies
        self.status_filter_proj.currentIndexChanged.connect(self.filter_projects)

        self.priority_filter = QComboBox()
        self.priority_filter.addItems(["All Priorities", "High", "Medium", "Low"])
        # Removed specific QComboBox stylesheet, global style applies
        self.priority_filter.currentIndexChanged.connect(self.filter_projects)

        filters_layout.addWidget(self.project_search)
        filters_layout.addWidget(self.status_filter_proj)
        filters_layout.addWidget(self.priority_filter)

        # Projects table
        self.projects_table = QTableWidget()
        self.projects_table.setColumnCount(8)
        self.projects_table.setHorizontalHeaderLabels(["Name", "Status", "Progress", "Priority", "Deadline", "Budget", "Manager", "Actions"])
        # QProgressBar styling is now handled by the global style.qss: QTableWidget QProgressBar
        # Global QTableWidget and QHeaderView styles will apply.
        # Removed inline self.projects_table.setStyleSheet(...)
        self.projects_table.verticalHeader().setVisible(False)
        self.projects_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.projects_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.projects_table.setSortingEnabled(True)
        self.projects_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        layout.addWidget(header)
        layout.addWidget(filters)
        layout.addWidget(self.projects_table)

        self.main_content.addWidget(page)

    def setup_tasks_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)

        title = QLabel("Task Management")
        title.setObjectName("pageTitleLabel")

        self.add_task_btn = QPushButton("New Task")
        self.add_task_btn.setIcon(QIcon(":/icons/plus.svg"))
        self.add_task_btn.setObjectName("primaryButton")
        # Global style applies
        self.add_task_btn.clicked.connect(self.show_add_task_dialog)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.add_task_btn)

        # Filters
        filters = QWidget()
        filters_layout = QHBoxLayout(filters)

        self.task_search = QLineEdit()
        self.task_search.setPlaceholderText("Search a task...")
        # Removed specific QLineEdit stylesheet, global style applies
        self.task_search.textChanged.connect(self.filter_tasks)

        self.task_status_filter = QComboBox()
        self.task_status_filter.addItems(["All Statuses", "To Do", "In Progress", "In Review", "Completed"])
        # Removed specific QComboBox stylesheet, global style applies
        self.task_status_filter.currentIndexChanged.connect(self.filter_tasks)

        self.task_priority_filter = QComboBox()
        self.task_priority_filter.addItems(["All Priorities", "High", "Medium", "Low"])
        # Removed specific QComboBox stylesheet, global style applies
        self.task_priority_filter.currentIndexChanged.connect(self.filter_tasks)

        self.task_project_filter = QComboBox()
        self.task_project_filter.addItem("All Projects")
        # Removed specific QComboBox stylesheet, global style applies
        self.task_project_filter.currentIndexChanged.connect(self.filter_tasks)

        filters_layout.addWidget(self.task_search)
        filters_layout.addWidget(self.task_status_filter)
        filters_layout.addWidget(self.task_priority_filter)
        filters_layout.addWidget(self.task_project_filter)

        # Tasks table
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(7)
        self.tasks_table.setHorizontalHeaderLabels(["Name", "Project", "Status", "Priority", "Assigned To", "Deadline", "Actions"])
        # Removed specific QTableWidget stylesheet, global style applies
        self.tasks_table.verticalHeader().setVisible(False)
        self.tasks_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tasks_table.setSortingEnabled(True)
        self.tasks_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        layout.addWidget(header)
        layout.addWidget(filters)
        layout.addWidget(self.tasks_table)

        # Pagination controls for Tasks
        tasks_pagination_layout = QHBoxLayout()
        self.prev_task_button = QPushButton("<< Précédent")
        self.prev_task_button.setObjectName("paginationButton")
        self.prev_task_button.clicked.connect(self.prev_task_page)
        self.task_page_info_label = QLabel("Page 1 / 1")
        self.task_page_info_label.setObjectName("paginationLabel")
        self.next_task_button = QPushButton("Suivant >>")
        self.next_task_button.setObjectName("paginationButton")
        self.next_task_button.clicked.connect(self.next_task_page)

        tasks_pagination_layout.addStretch()
        tasks_pagination_layout.addWidget(self.prev_task_button)
        tasks_pagination_layout.addWidget(self.task_page_info_label)
        tasks_pagination_layout.addWidget(self.next_task_button)
        tasks_pagination_layout.addStretch()
        layout.addLayout(tasks_pagination_layout)

        self.main_content.addWidget(page)

    def setup_reports_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Reports and Analytics")
        title.setObjectName("pageTitleLabel")

        # Report options
        report_options = QWidget()
        options_layout = QHBoxLayout(report_options)

        self.report_type = QComboBox()
        self.report_type.addItems(["Team Performance", "Project Progress", "Workload", "Key Indicators", "Budget Analysis"])
        # Removed specific QComboBox stylesheet, global style applies

        self.report_period = QComboBox()
        self.report_period.addItems(["Last 7 Days", "Last 30 Days", "Current Quarter", "Current Year", "Custom..."])
        # Removed specific QComboBox stylesheet, global style applies
        self.report_period.currentIndexChanged.connect(self.generate_report) # Corrected connection

        generate_btn = QPushButton("Generate Report")
        generate_btn.setIcon(QIcon(":/icons/bar-chart.svg"))
        generate_btn.setObjectName("primaryButton")
        generate_btn.clicked.connect(self.generate_report)

        export_btn = QPushButton("Export PDF")
        export_btn.setIcon(QIcon(":/icons/download.svg"))
        export_btn.setObjectName("secondaryButton") # Changed to use secondary button style
        export_btn.clicked.connect(self.export_report)

        options_layout.addWidget(QLabel("Type:"))
        options_layout.addWidget(self.report_type)
        options_layout.addWidget(QLabel("Period:"))
        options_layout.addWidget(self.report_period)
        options_layout.addWidget(generate_btn)
        options_layout.addWidget(export_btn)

        # Report area
        self.report_view = QTabWidget()
        # Removed specific QTabWidget stylesheet, global style applies

        # Chart tab
        self.graph_tab = QWidget()
        self.graph_layout = QVBoxLayout(self.graph_tab)

        # Data tab
        self.data_tab = QWidget()
        self.data_layout = QVBoxLayout(self.data_tab)

        self.report_data_table = QTableWidget()
        # Removed specific QTableWidget stylesheet, global style applies
        self.report_data_table.verticalHeader().setVisible(False)
        self.report_data_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.data_layout.addWidget(self.report_data_table)

        self.report_view.addTab(self.graph_tab, "Visualization")
        self.report_view.addTab(self.data_tab, "Data")

        layout.addWidget(title)
        layout.addWidget(report_options)
        layout.addWidget(self.report_view)

        self.main_content.addWidget(page)

    def setup_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Settings")
        title.setObjectName("pageTitleLabel")

        # Tabs
        tabs = QTabWidget()
        # Removed specific QTabWidget stylesheet, global style applies

        # General style for input fields and combo boxes in settings
        # This will be inherited from the global stylesheet or can be removed if not needed
        # settings_input_style = """
        #     QLineEdit, QComboBox, QDateEdit { /* Keep if specific adjustments needed, else remove */
        #          min-height: 20px;
        #     }
        # """ # Minimal example, may not be needed if global is sufficient.

        # Account tab
        account_tab = QWidget()
        # account_tab.setStyleSheet(settings_input_style) # Global styles should apply.
        account_layout = QFormLayout(account_tab)
        account_layout.setSpacing(15)
        account_layout.setLabelAlignment(Qt.AlignRight)


        account_layout.addRow(QLabel("<b>Personal Information</b>"))

        self.name_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.phone_edit = QLineEdit()

        account_layout.addRow("Full Name:", self.name_edit)
        account_layout.addRow("Email:", self.email_edit)
        account_layout.addRow("Phone:", self.phone_edit)

        account_layout.addItem(QSpacerItem(20, 20))
        account_layout.addRow(QLabel("<b>Security</b>"))

        self.current_pwd_edit = QLineEdit()
        self.current_pwd_edit.setEchoMode(QLineEdit.Password)
        self.new_pwd_edit = QLineEdit()
        self.new_pwd_edit.setEchoMode(QLineEdit.Password)
        self.confirm_pwd_edit = QLineEdit()
        self.confirm_pwd_edit.setEchoMode(QLineEdit.Password)

        account_layout.addRow("Current Password:", self.current_pwd_edit)
        account_layout.addRow("New Password:", self.new_pwd_edit)
        account_layout.addRow("Confirm:", self.confirm_pwd_edit)

        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("primaryButton") # Use global primary style
        # Removed specific setStyleSheet
        save_btn.clicked.connect(self.save_account_settings)
        account_layout.addRow(save_btn)

        # Preferences tab
        pref_tab = QWidget()
        # pref_tab.setStyleSheet(settings_input_style) # Global styles should apply
        pref_layout = QFormLayout(pref_tab)
        pref_layout.setSpacing(15)
        pref_layout.setLabelAlignment(Qt.AlignRight)

        pref_layout.addRow(QLabel("<b>Display</b>"))

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Blue", "Automatic"])

        self.density_combo = QComboBox()
        self.density_combo.addItems(["Compact", "Normal", "Large"])

        self.language_combo = QComboBox()
        self.language_combo.addItems(["French", "English", "Spanish"])

        pref_layout.addRow("Theme:", self.theme_combo)
        pref_layout.addRow("Density:", self.density_combo)
        pref_layout.addRow("Language:", self.language_combo)

        pref_layout.addItem(QSpacerItem(20, 20))
        pref_layout.addRow(QLabel("<b>Notifications</b>"))

        self.email_notif = QCheckBox("Email")
        self.app_notif = QCheckBox("Application")
        self.sms_notif = QCheckBox("SMS")

        pref_layout.addRow(self.email_notif)
        pref_layout.addRow(self.app_notif)
        pref_layout.addRow(self.sms_notif)

        save_pref_btn = QPushButton("Save Preferences")
        save_pref_btn.setObjectName("primaryButton") # Use global primary style
        # Removed specific setStyleSheet
        save_pref_btn.clicked.connect(self.save_preferences)
        pref_layout.addRow(save_pref_btn)

        # Team tab
        team_tab = QWidget()
        team_layout = QVBoxLayout(team_tab)

        self.access_table = QTableWidget()
        self.access_table.setColumnCount(4)
        self.access_table.setHorizontalHeaderLabels(["Name", "Role", "Access", "Actions"])
        # Removed specific QTableWidget stylesheet, global style applies
        self.access_table.verticalHeader().setVisible(False)
        self.access_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.access_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        team_layout.addWidget(self.access_table)

        tabs.addTab(account_tab, "Account")
        tabs.addTab(pref_tab, "Preferences")
        tabs.addTab(team_tab, "Access Management")

        layout.addWidget(title)
        layout.addWidget(tabs)

        self.main_content.addWidget(page)

    def show_login_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Login")
        dialog.setFixedSize(350, 250)
        dialog.setObjectName("loginDialog") # Added object name
        # Stylesheet removed

        layout = QVBoxLayout(dialog)

        logo_label = QLabel() # Renamed
        logo_label.setPixmap(QIcon(":/icons/logo.svg").pixmap(80, 80)) # Use resource
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setObjectName("loginLogoLabel")


        username_edit = QLineEdit()
        username_edit.setPlaceholderText("Username")
        username_edit.setObjectName("loginUsernameEdit")


        password_edit = QLineEdit()
        password_edit.setPlaceholderText("Password")
        password_edit.setEchoMode(QLineEdit.Password)
        password_edit.setObjectName("loginPasswordEdit")


        login_btn = QPushButton("Login")
        login_btn.setObjectName("loginDialogButton") # More specific name
        login_btn.clicked.connect(lambda: self.handle_login(username_edit.text(), password_edit.text(), dialog))

        layout.addWidget(logo_label)
        layout.addWidget(QLabel("Username:")) # General QLabel style applies
        layout.addWidget(username_edit)
        layout.addWidget(QLabel("Password:")) # General QLabel style applies
        layout.addWidget(password_edit)
        layout.addItem(QSpacerItem(20, 20))
        layout.addWidget(login_btn)

        dialog.exec_()

    def handle_login(self, username, password, dialog):
        # hashed_pwd = hashlib.sha256(password.encode()).hexdigest() # Old method

        # Use db_manager for verification (changed from main_db_manager)
        user_data_from_db = db_manager.verify_user_password(username, password)

        if user_data_from_db: # This is a dict from db.py's row_factory
            # Directly use the dictionary returned by verify_user_password as self.current_user
            # Ensure all keys needed by the UI (e.g., 'full_name', 'role') are present in the dict from db.py
            self.current_user = dict(user_data_from_db) # Convert sqlite3.Row to dict if not already

            # Update UI
            self.user_name.setText(self.current_user.get('full_name', "N/A"))
            self.user_role.setText(self.current_user.get('role', "N/A").capitalize())

            # Log activity - ensure self.current_user['id'] maps to user_id for log_activity
            # db.py's Users table has user_id as PK. verify_user_password returns this.
            # log_activity expects 'id' key in self.current_user for user_id.
            # So, ensure self.current_user['id'] is set correctly, or adjust log_activity.
            # For now, assuming log_activity will be adapted or current_user dict has 'id' as user_id.
            # To be safe, let's prepare a dict for log_activity if needed, or ensure 'id' exists.
            # The log_activity expects self.current_user['id']. Let's make sure it's there.
            # If user_data_from_db has 'user_id', we can map it to 'id' in self.current_user for log_activity,
            # or better, adjust log_activity to use 'user_id'.
            # For now, let's assume self.current_user (which is user_data_from_db) will be used by log_activity directly.

            self.log_activity(f"Login by {self.current_user.get('full_name', username)}")

            # Load data
            self.load_initial_data()

            dialog.accept()
        else:
            QMessageBox.warning(self, "Error", "Incorrect username or password, or user is inactive.")

    def logout(self):
        if self.current_user:
            self.log_activity(f"Logout by {self.current_user.get('full_name', 'Unknown user')}")

        self.current_user = None
        self.user_name.setText("Guest")
        self.user_role.setText("Not logged in")
        self.show_login_dialog()

    def log_activity(self, action, details=None):
        user_id_for_log = None
        if self.current_user and self.current_user.get('user_id'):
            user_id_for_log = self.current_user.get('user_id')

        db_manager.add_activity_log({ # Changed main_db_manager to db_manager
            'user_id': user_id_for_log,
            'action_type': action,
            'details': details
            # Other fields like 'related_entity_type', 'related_entity_id' can be added if available
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
        # Attempt to load KPIs for the first project found
        # In a more advanced dashboard, this would come from a selected project context
        all_projects = db_manager.get_all_projects() # Changed main_db_manager to db_manager
        if all_projects and len(all_projects) > 0:
            # For simplicity, let's try to find the first project that is not archived or completed
            first_active_project_id = None
            for proj in all_projects:
                status_id = proj.get('status_id')
                if status_id:
                    status_setting = db_manager.get_status_setting_by_id(status_id)
                    if status_setting and not status_setting.get('is_completion_status') and not status_setting.get('is_archival_status'):
                        first_active_project_id = proj.get('project_id')
                        break
                else: # If no status, assume it's active for KPI display
                    first_active_project_id = proj.get('project_id')
                    break

            if first_active_project_id:
                kpis_to_display = db_manager.get_kpis_for_project(first_active_project_id) # Changed main_db_manager
                if kpis_to_display:
                     print(f"Displaying KPIs for project ID: {first_active_project_id}")
                else:
                    print(f"No KPIs found for project ID: {first_active_project_id}")
            else:
                print("No active projects found to display KPIs for.")
        else:
            print("No projects found in the database.")


        if not kpis_to_display:
            # Do not create example KPIs. Just display a message.
            no_kpi_label = QLabel("No KPIs to display for the current project context.")
            no_kpi_label.setAlignment(Qt.AlignCenter)
            self.kpi_layout.addWidget(no_kpi_label)
            return

        for kpi_dict in kpis_to_display: # kpi_dict is a dictionary from db.py
            name = kpi_dict.get('name', 'N/A')
            value = kpi_dict.get('value', 0)
            target = kpi_dict.get('target', 0)
            trend = kpi_dict.get('trend', 'stable')
            unit = kpi_dict.get('unit', '')

            frame = QFrame()
            frame.setObjectName("kpiFrame") # Added object name
            # Removed inline stylesheet, will be moved to style.qss
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
                trend_icon_label.setPixmap(QIcon(":/icons/trend_up.svg").pixmap(16, 16))
            elif trend == "down":
                trend_icon_label.setPixmap(QIcon(":/icons/trend_down.svg").pixmap(16, 16))
            else: # "stable" or other
                trend_icon_label.setPixmap(QIcon(":/icons/trend_stable.svg").pixmap(16, 16))

            trend_layout = QHBoxLayout()
            trend_layout.addWidget(QLabel(self.tr("Trend:"))) # Added self.tr for "Trend:"
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
        # Uses db_manager.get_all_team_members() (changed from main_db_manager)
        # db.py fields: team_member_id, user_id, full_name, email, role_or_title, department,
        # phone_number, profile_picture_url, is_active, notes, hire_date, performance, skills

        members_data = db_manager.get_all_team_members() # Changed main_db_manager
        if members_data is None: members_data = []

        self.team_table.setRowCount(len(members_data))

        for row_idx, member in enumerate(members_data): # member is a dict
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

            is_active_val = member.get('is_active', False) # In db.py, is_active is BOOLEAN (0 or 1)
            active_item = QTableWidgetItem()
            if bool(is_active_val): # Ensure it's treated as boolean
                active_item.setIcon(QIcon(":/icons/active.svg"))
                active_item.setText("Active")
            else:
                active_item.setIcon(QIcon(":/icons/inactive.svg"))
                active_item.setText("Inactive")
            self.team_table.setItem(row_idx, 7, active_item)

            task_count = 0
            member_id_for_tasks = member.get('team_member_id')
            if member_id_for_tasks is not None:
                # Use the new helper function, fetching only active tasks
                tasks_for_member = db_manager.get_tasks_by_assignee_id(member_id_for_tasks, active_only=True)
                if tasks_for_member:
                    task_count = len(tasks_for_member)
            self.team_table.setItem(row_idx, 8, QTableWidgetItem(str(task_count)))

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0,0,0,0)
            action_layout.setSpacing(5)

            current_member_id = member['team_member_id']

            edit_btn = QPushButton("")
            edit_btn.setIcon(QIcon(":/icons/pencil.svg"))
            edit_btn.setToolTip("Edit")
            edit_btn.setFixedSize(30,30)
            edit_btn.setStyleSheet(self.get_table_action_button_style())
            edit_btn.clicked.connect(lambda _, m_id=current_member_id: self.edit_member(m_id))

            delete_btn = QPushButton("")
            delete_btn.setIcon(QIcon(":/icons/trash.svg"))
            delete_btn.setToolTip("Delete")
            delete_btn.setFixedSize(30,30)
            delete_btn.setStyleSheet(self.get_table_action_button_style())
            delete_btn.clicked.connect(lambda _, m_id=current_member_id: self.delete_member(m_id))

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(delete_btn)
            self.team_table.setCellWidget(row_idx, 9, action_widget)

        self.team_table.resizeColumnsToContents()

    def load_projects(self):
        # db.py fields: project_id (TEXT PK), client_id, project_name, description, start_date, deadline_date,
        # budget, status_id (FK to StatusSettings), progress_percentage, manager_team_member_id (FK to Users.user_id),
        # priority (INTEGER), created_at, updated_at

        projects_data = db_manager.get_all_projects() # Changed main_db_manager
        if projects_data is None:
            projects_data = []

        self.projects_table.setRowCount(len(projects_data))

        for row_idx, project_dict in enumerate(projects_data): # project_dict is a dict
            project_id_str = project_dict.get('project_id')
            name_item = QTableWidgetItem(project_dict.get('project_name', 'N/A'))
            name_item.setData(Qt.UserRole, project_id_str) # Store project_id in UserRole
            self.projects_table.setItem(row_idx, 0, name_item)

            # Status
            status_id = project_dict.get('status_id')
            status_name_display = "Unknown"
            status_color_hex = "#7f8c8d" # Default color
            if status_id is not None:
                status_setting = db_manager.get_status_setting_by_id(status_id) # Changed main_db_manager
                if status_setting:
                    status_name_display = status_setting.get('status_name', 'Unknown')
                    color_from_db = status_setting.get('color_hex')
                    if color_from_db:
                        status_color_hex = color_from_db
                    else: # Fallback colors based on name if hex not in DB
                        if "completed" in status_name_display.lower(): status_color_hex = '#2ecc71' # Green
                        elif "progress" in status_name_display.lower(): status_color_hex = '#3498db' # Blue
                        elif "planning" in status_name_display.lower(): status_color_hex = '#f1c40f' # Yellow
                        elif "late" in status_name_display.lower() or "overdue" in status_name_display.lower(): status_color_hex = '#e74c3c' # Red
                        elif "archived" in status_name_display.lower(): status_color_hex = '#95a5a6' # Grey

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
            # Removed inline progress_bar.setStyleSheet(...). Will use global QTableWidget QProgressBar style.
            progress_layout.addWidget(progress_bar)
            self.projects_table.setCellWidget(row_idx, 2, progress_widget)

            # Priority
            priority_val = project_dict.get('priority', 0)
            priority_item = QTableWidgetItem()
            if priority_val == 2: # High
                priority_item.setIcon(QIcon(":/icons/priority-high.svg"))
                priority_item.setText("High")
            elif priority_val == 1: # Medium
                priority_item.setIcon(QIcon(":/icons/priority-medium.svg"))
                priority_item.setText("Medium")
            else: # 0 or other = Low
                priority_item.setIcon(QIcon(":/icons/priority-low.svg"))
                priority_item.setText("Low")
            self.projects_table.setItem(row_idx, 3, priority_item)

            self.projects_table.setItem(row_idx, 4, QTableWidgetItem(project_dict.get('deadline_date', 'N/A')))
            budget_val = project_dict.get('budget', 0.0)
            self.projects_table.setItem(row_idx, 5, QTableWidgetItem(f"€{budget_val:,.2f}" if budget_val is not None else "€0.00"))

            manager_user_id = project_dict.get('manager_team_member_id') # This is a user_id (TEXT from Users table)
            manager_display_name = "Unassigned"
            if manager_user_id:
                # First, try to find a TeamMember linked to this user_id
                team_members_list = db_manager.get_all_team_members(filters={'user_id': manager_user_id})
                if team_members_list and len(team_members_list) > 0:
                    manager_display_name = team_members_list[0].get('full_name', manager_user_id)
                else:
                    # If no direct TeamMember link, fall back to User's full_name
                    user_as_manager = db_manager.get_user_by_id(manager_user_id) # Changed main_db_manager
                    if user_as_manager:
                        manager_display_name = user_as_manager.get('full_name', manager_user_id) # Use user_id as last resort
            self.projects_table.setItem(row_idx, 6, QTableWidgetItem(manager_display_name))

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0,0,0,0)
            action_layout.setSpacing(5)

            details_btn = QPushButton(""); details_btn.setIcon(QIcon.fromTheme("dialog-information", QIcon(":/icons/eye.svg")))
            details_btn.setToolTip("Details")
            details_btn.setFixedSize(30,30)
            details_btn.setObjectName("tableActionButton")
            details_btn.clicked.connect(lambda _, p_id=project_id_str: self.show_project_details(p_id))

            edit_btn = QPushButton(""); edit_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg")))
            edit_btn.setToolTip("Edit")
            edit_btn.setFixedSize(30,30)
            edit_btn.setObjectName("tableActionButton")
            edit_btn.clicked.connect(lambda _, p_id=project_id_str: self.edit_project(p_id))

            delete_btn = QPushButton(""); delete_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon(":/icons/trash.svg")))
            delete_btn.setToolTip("Delete")
            delete_btn.setFixedSize(30,30)
            delete_btn.setObjectName("dangerButtonTable") # Specific for potential red color
            delete_btn.clicked.connect(lambda _, p_id=project_id_str: self.delete_project(p_id))

            action_layout.addWidget(details_btn)
            action_layout.addWidget(edit_btn)
            action_layout.addWidget(delete_btn)
            self.projects_table.setCellWidget(row_idx, 7, action_widget)

        self.projects_table.resizeColumnsToContents()

    def load_access_table(self):
        users_data = db_manager.get_all_users() # Already changed to db_manager, this is just a confirmation
        if users_data is None: users_data = []

        self.access_table.setRowCount(len(users_data))

        for row_idx, user_dict in enumerate(users_data): # user_dict is a dict
            user_id_str = user_dict.get('user_id')
            full_name = user_dict.get('full_name', 'N/A')
            role = user_dict.get('role', 'member')

            self.access_table.setItem(row_idx, 0, QTableWidgetItem(full_name))

            role_display_name = role.capitalize()
            access_text = "User"
            access_color = QColor('#2ecc71')

            if role == "admin":
                role_display_name = "Administrator"
                access_text = "Administrator"
                access_color = QColor('#e74c3c')
            elif role == "manager":
                role_display_name = "Manager"
                access_text = "Manager"
                access_color = QColor('#3498db')

            self.access_table.setItem(row_idx, 1, QTableWidgetItem(role_display_name))

            access_item = QTableWidgetItem(access_text)
            access_item.setForeground(access_color)
            self.access_table.setItem(row_idx, 2, access_item)

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0,0,0,0)
            action_layout.setSpacing(5)

            edit_btn = QPushButton(""); edit_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg")))
            edit_btn.setToolTip("Edit User Access")
            edit_btn.setFixedSize(30,30)
            edit_btn.setObjectName("tableActionButton")
            edit_btn.clicked.connect(lambda _, u_id=user_id_str: self.edit_user_access(u_id))

            action_layout.addWidget(edit_btn)
            self.access_table.setCellWidget(row_idx, 3, action_widget)

        self.access_table.resizeColumnsToContents()

    def load_user_preferences(self):
        # Load user preferences from database using db_manager (changed from main_db_manager)
        if not self.current_user or not self.current_user.get('user_id'): # check for user_id specifically
            return

        user_data = db_manager.get_user_by_id(self.current_user['user_id']) # use user_id

        if user_data: # user_data is a dict
            self.name_edit.setText(user_data.get('full_name', ''))
            self.email_edit.setText(user_data.get('email', ''))
            # 'phone' is not a standard field in Users table in db.py, it's in TeamMembers.
            # If phone is needed here, logic to fetch from TeamMembers based on user_id would be required.
            # For now, remove direct phone access from user_data for Users table.
            # self.phone_edit.setText(user_data.get('phone', ''))

    def update_project_filter(self):
        # Confirmed: Uses db_manager.get_all_projects()
        projects = db_manager.get_all_projects()

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

    def prev_task_page(self):
        if self.current_task_offset > 0:
            self.current_task_offset -= self.TASK_PAGE_LIMIT
            self.load_tasks()

    def next_task_page(self):
        if (self.current_task_offset + self.TASK_PAGE_LIMIT) < self.total_tasks_count:
            self.current_task_offset += self.TASK_PAGE_LIMIT
            self.load_tasks()

    def update_task_pagination_controls(self):
        if self.total_tasks_count == 0:
            total_pages = 1
            current_page = 1
        else:
            total_pages = math.ceil(self.total_tasks_count / self.TASK_PAGE_LIMIT)
            current_page = (self.current_task_offset // self.TASK_PAGE_LIMIT) + 1

        self.task_page_info_label.setText(f"Page {current_page} / {total_pages}")
        self.prev_task_button.setEnabled(self.current_task_offset > 0)
        self.next_task_button.setEnabled((self.current_task_offset + self.TASK_PAGE_LIMIT) < self.total_tasks_count)

    def filter_tasks(self):
        # Server-side filtering: reset offset and reload tasks
        self.current_task_offset = 0
        self.load_tasks()

    def update_dashboard(self):
        self.load_kpis()
        self.load_activities()
        self.update_charts()
        print("Dashboard updated")

    def update_charts(self):
        # Team performance
        self.performance_graph.clear()
        active_members = db_manager.get_all_team_members({'is_active': True})
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
        all_projects = db_manager.get_all_projects()
        if all_projects is None: all_projects = []

        projects_for_chart = []
        for p_dict in all_projects:
            status_id = p_dict.get('status_id')
            if status_id:
                status_setting = db_manager.get_status_setting_by_id(status_id)
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

    def load_activities(self):
        try:
            logs = db_manager.get_activity_logs(limit=20) # Fetch recent logs
            if logs is None:
                logs = []

            self.activities_table.setSortingEnabled(False) # Disable sorting before clearing/repopulating
            self.activities_table.setRowCount(0) # Clear existing rows
            self.activities_table.setRowCount(len(logs))

            for row_idx, log_entry in enumerate(logs):
                # Date (Column 0)
                created_at_str = log_entry.get('created_at', '')
                display_date = 'N/A'
                if created_at_str:
                    try:
                        # Handle potential 'Z' for UTC and microseconds if present
                        if 'Z' in created_at_str:
                            created_at_str = created_at_str.replace('Z', '+00:00')

                        if '.' in created_at_str: # Contains microseconds
                            dt_obj = datetime.fromisoformat(created_at_str)
                        else: # No microseconds
                             # Ensure timezone info if it was '+00:00'
                            if '+' in created_at_str:
                                dt_obj = datetime.fromisoformat(created_at_str)
                            else: # Assume it's naive, treat as local or parse differently
                                dt_obj = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S') # Example if no TZ info

                        display_date = dt_obj.strftime('%Y-%m-%d %H:%M')
                    except ValueError as ve_date:
                        print(f"Date parsing error for '{created_at_str}': {ve_date}")
                        display_date = created_at_str # Show as is if parsing fails

                self.activities_table.setItem(row_idx, 0, QTableWidgetItem(display_date))

                # Member (Column 1)
                user_id = log_entry.get('user_id')
                member_name = "System/Unknown"
                if user_id:
                    user = db_manager.get_user_by_id(user_id)
                    if user:
                        member_name = user.get('full_name', user.get('username', 'User ' + str(user_id)))
                self.activities_table.setItem(row_idx, 1, QTableWidgetItem(member_name))

                # Action (Column 2)
                action_type = log_entry.get('action_type', 'N/A')
                self.activities_table.setItem(row_idx, 2, QTableWidgetItem(action_type))

                # Details (Column 3)
                details = log_entry.get('details', '')
                details_item = QTableWidgetItem(details)
                if details and len(details) > 70: # Tooltip for long details
                    details_item.setToolTip(details)
                self.activities_table.setItem(row_idx, 3, details_item)

            self.activities_table.resizeColumnsToContents()
            self.activities_table.setSortingEnabled(True) # Re-enable sorting
        except Exception as e:
            print(f"Error loading activities into table: {e}")
            # Optionally, display an error in the table or a QMessageBox
            # For example, clear the table and show one row with the error:
            # self.activities_table.setRowCount(1)
            # error_item = QTableWidgetItem(f"Error loading activities: {e}")
            # self.activities_table.setItem(0, 0, error_item)
            # self.activities_table.setSpan(0, 0, 1, self.activities_table.columnCount())


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

        print(f"Report '{report_type}' generated for period '{period}'")

    def generate_team_performance_report(self, period):
        # Chart
        fig = plt.figure(figsize=(10, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        # Fetch data using db_manager
        active_members_data = db_manager.get_all_team_members({'is_active': True})
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

        projects_data = db_manager.get_all_projects()
        if projects_data is None: projects_data = []

        # Filter out projects that might be considered "deleted" or "archived" based on status type
        # This assumes StatusSettings has 'is_archival_status'
        valid_projects_for_report = []
        for p_dict in projects_data:
            status_id = p_dict.get('status_id')
            if status_id:
                status_setting = db_manager.get_status_setting_by_id(status_id)
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
                status_setting = db_manager.get_status_setting_by_id(status_id)
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

        active_team_members = db_manager.get_all_team_members({'is_active': True})
        if not active_team_members: active_team_members = []

        member_task_counts = {} # Store as team_member_id: count

        # Aggregate tasks: Iterate through projects, then tasks
        all_projects = db_manager.get_all_projects()
        if all_projects:
            for project in all_projects:
                tasks_in_project = db_manager.get_tasks_by_project_id(project['project_id'])
                if tasks_in_project:
                    for task in tasks_in_project:
                        assignee_id = task.get('assignee_team_member_id')
                        status_id = task.get('status_id')
                        if assignee_id is not None and status_id is not None:
                            status_setting = db_manager.get_status_setting_by_id(status_id)
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
        all_projects = db_manager.get_all_projects()
        if all_projects and len(all_projects) > 0:
            first_project_id = all_projects[0].get('project_id')
            if first_project_id:
                kpis_data = db_manager.get_kpis_for_project(first_project_id)
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

        projects_data = db_manager.get_all_projects()
        if projects_data is None: projects_data = []

        # Filter out projects that are archived for budget report
        reportable_projects = []
        status_names_for_budget_table = []

        for p_dict in projects_data:
            status_id = p_dict.get('status_id')
            status_name = "Unknown"
            is_archival = False
            if status_id:
                status_setting = db_manager.get_status_setting_by_id(status_id)
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

                    print(f"Report exported to {file_name}")
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
                new_member_id = db_manager.add_team_member(member_data) # Changed main_db_manager
                if new_member_id:
                    self.load_team_members()
                    self.log_activity(f"Added team member: {member_data['full_name']}")
                    # self.statusBar().showMessage(f"Team member {member_data['full_name']} added successfully (ID: {new_member_id})", 3000) # statusBar not available on QWidget
                    print(f"Team member {member_data['full_name']} added successfully (ID: {new_member_id})")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to add team member. Check logs. Email might be in use.")
            else:
                QMessageBox.warning(self, "Error", "Full name and email are required.")

    def edit_member(self, member_id_int): # member_id is int from db.py (team_member_id)
        member_data_from_db = db_manager.get_team_member_by_id(member_id_int) # Changed main_db_manager

        if member_data_from_db: # This is a dict
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Team Member")
            dialog.setFixedSize(400, 500)

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
            active_checkbox.setChecked(bool(member_data_from_db.get('is_active', True))) # Ensure boolean

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
                    success = db_manager.update_team_member(member_id_int, updated_member_data) # Changed main_db_manager
                    if success:
                        self.load_team_members()
                        self.log_activity(f"Updated team member: {updated_member_data['full_name']}")
                        # self.statusBar().showMessage(f"Team member {updated_member_data['full_name']} updated successfully", 3000)
                        print(f"Team member {updated_member_data['full_name']} updated successfully")
                    else:
                        QMessageBox.warning(self, "Error", f"Failed to update team member. Check logs. Email might be in use by another member.")
                else:
                    QMessageBox.warning(self, "Error", "Full name and email are required.")
        else:
            QMessageBox.warning(self, "Error", f"Could not find team member with ID {member_id_int} to edit.")

    def delete_member(self, member_id_int): # member_id is int
        member_to_delete = db_manager.get_team_member_by_id(member_id_int) # Changed main_db_manager

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
            success = db_manager.delete_team_member(member_id_int) # Changed main_db_manager
            if success:
                self.load_team_members()
                self.log_activity(f"Deleted team member: {member_name} (ID: {member_id_int})")
                # self.statusBar().showMessage(f"Team member {member_name} deleted", 3000)
                print(f"Team member {member_name} deleted")
            else:
                QMessageBox.warning(self, "Error", f"Failed to delete team member {member_name}.")

    def show_add_project_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("New Project")
        dialog.setFixedSize(500, 550)

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
        budget_spin.setRange(0, 10000000)
        budget_spin.setPrefix("€ ")
        budget_spin.setValue(10000)

        status_combo = QComboBox()
        project_statuses = db_manager.get_all_status_settings(status_type='Project') # Changed main_db_manager
        if project_statuses:
            for ps in project_statuses:
                status_combo.addItem(ps['status_name'], ps['status_id'])
        else:
            status_combo.addItem("Default Project Status", None)

        priority_combo = QComboBox()
        priority_combo.addItems(["Low", "Medium", "High"])
        priority_combo.setCurrentIndex(1)

        manager_combo = QComboBox()
        manager_combo.addItem("Unassigned", None)
        active_team_members = db_manager.get_all_team_members({'is_active': True}) # Changed main_db_manager
        if active_team_members:
            for tm in active_team_members:
                manager_combo.addItem(tm['full_name'], tm['team_member_id'])

        client_combo = QComboBox()
        all_clients = db_manager.get_all_clients() # Changed main_db_manager
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
        layout.addRow("Client:", client_combo)
        layout.addRow("Description:", desc_edit)
        layout.addRow("Start Date:", start_date_edit)
        layout.addRow("Deadline:", deadline_edit)
        layout.addRow("Budget:", budget_spin)
        layout.addRow("Status:", status_combo)
        layout.addRow("Priority:", priority_combo)
        layout.addRow("Manager (Team Member):", manager_combo)

        layout.addRow(QLabel("--- Optional: Start from Template ---")) # Visually separate
        template_combo = QComboBox()
        template_combo.addItem("None (Blank Project)", None)
        available_templates = self.template_manager.get_templates()
        for tpl in available_templates:
            template_combo.addItem(tpl.name, tpl.name) # Store template name as data
        layout.addRow(self.tr("Project Template:"), template_combo)

        layout.addRow(button_box)

        if dialog.exec_() == QDialog.Accepted:
            project_name = name_edit.text()
            client_id_selected = client_combo.currentData()

            if not project_name:
                QMessageBox.warning(self, "Error", "Project name is required.")
                return
            if not client_id_selected and client_combo.isEnabled():
                QMessageBox.warning(self, "Error", "A client must be selected for the project.")
                return
            if not client_id_selected and not client_combo.isEnabled():
                 QMessageBox.warning(self, "Error", "Cannot add project: No clients available in the database. Please add a client first.")
                 return


            selected_manager_tm_id = manager_combo.currentData()
            manager_user_id_for_db = None
            if selected_manager_tm_id is not None:
                team_member_manager = db_manager.get_team_member_by_id(selected_manager_tm_id) # Changed main_db_manager
                if team_member_manager:
                    manager_user_id_for_db = team_member_manager.get('user_id')

            priority_text = priority_combo.currentText()
            priority_for_db = 0
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
                'progress_percentage': 0,
                'manager_team_member_id': manager_user_id_for_db,
                'priority': priority_for_db
            }

            new_project_id = db_manager.add_project(project_data_to_save) # Changed main_db_manager

            if new_project_id:
                self.load_projects()
                self.update_project_filter()
                self.log_activity(f"Added project: {project_name}")
                # self.statusBar().showMessage(f"Project {project_name} added successfully (ID: {new_project_id})", 3000)
                print(f"Project {project_name} added successfully (ID: {new_project_id})")

                # Add tasks from template if selected
                selected_template_name = template_combo.currentData()
                if selected_template_name:
                    template = self.template_manager.get_template_by_name(selected_template_name)
                    if template:
                        task_status_todo_obj = db_manager.get_status_setting_by_name("To Do", "Task")
                        default_task_status_id = task_status_todo_obj['status_id'] if task_status_todo_obj else None
                        if not default_task_status_id:
                            QMessageBox.warning(self, self.tr("Configuration Error"), self.tr("Default 'To Do' status for tasks not found. Template tasks will not have a status."))

                        for task_def in template.tasks:
                            task_data_for_db = {
                                'project_id': new_project_id,
                                'task_name': task_def['name'],
                                'description': task_def.get('description', ''),
                                'status_id': default_task_status_id,
                                'priority': task_def.get('priority', 0),
                            }
                            if self.current_user and self.current_user.get('user_id'):
                                current_user_as_tm_list = db_manager.get_all_team_members(filters={'user_id': self.current_user.get('user_id')})
                                if current_user_as_tm_list:
                                    task_data_for_db['reporter_team_member_id'] = current_user_as_tm_list[0].get('team_member_id')

                            db_manager.add_task(task_data_for_db)
                        print(f"Added {len(template.tasks)} tasks from template '{template.name}' to project {new_project_id}")
                        self.load_tasks() # Refresh task list if it's visible or might become visible
            else:
                QMessageBox.warning(self, "Error", "Failed to add project. Check logs.")

    def edit_project(self, project_id_str):
        project_data_dict = db_manager.get_project_by_id(project_id_str) # Changed main_db_manager

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
            project_statuses = db_manager.get_all_status_settings(status_type='Project') # Changed main_db_manager
            current_status_id = project_data_dict.get('status_id')
            if project_statuses:
                for idx, ps in enumerate(project_statuses):
                    status_combo.addItem(ps['status_name'], ps['status_id'])
                    if ps['status_id'] == current_status_id:
                        status_combo.setCurrentIndex(idx)
            else:
                status_combo.addItem("No Statuses Defined", None)
                status_setting = db_manager.get_status_setting_by_id(current_status_id) # Changed main_db_manager
                if status_setting : status_combo.addItem(status_setting['status_name'], current_status_id)


            priority_combo = QComboBox()
            priority_combo.addItems(["Low", "Medium", "High"])
            db_priority = project_data_dict.get('priority', 0)
            if db_priority == 1: priority_combo.setCurrentText("Medium")
            elif db_priority == 2: priority_combo.setCurrentText("High")
            else: priority_combo.setCurrentText("Low")


            manager_combo = QComboBox()
            manager_combo.addItem("Unassigned", None)
            active_team_members = db_manager.get_all_team_members({'is_active': True}) # Changed main_db_manager
            project_manager_user_id = project_data_dict.get('manager_team_member_id')
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
                        manager_combo.setCurrentIndex(idx + 1)

            client_combo = QComboBox()
            all_clients = db_manager.get_all_clients() # Changed main_db_manager
            current_client_id = project_data_dict.get('client_id')
            if all_clients:
                for idx, client_item in enumerate(all_clients):
                    client_combo.addItem(client_item['client_name'], client_item['client_id'])
                    if client_item['client_id'] == current_client_id:
                        client_combo.setCurrentIndex(idx)
            else:
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
                    tm_manager_updated = db_manager.get_team_member_by_id(selected_manager_tm_id_updated) # Changed main_db_manager
                    if tm_manager_updated:
                        manager_user_id_for_db_updated = tm_manager_updated.get('user_id')

                priority_text_updated = priority_combo.currentText()
                priority_for_db_updated = 0
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
                    'progress_percentage': project_data_dict.get('progress_percentage', 0),
                    'manager_team_member_id': manager_user_id_for_db_updated,
                    'priority': priority_for_db_updated
                }

                success = db_manager.update_project(project_id_str, updated_project_data_to_save) # Changed main_db_manager

                if success:
                    self.load_projects()
                    self.update_project_filter()
                    self.log_activity(f"Updated project: {project_name_updated}")
                    # self.statusBar().showMessage(f"Project {project_name_updated} updated successfully", 3000)
                    print(f"Project {project_name_updated} updated successfully")
                else:
                    QMessageBox.warning(self, "Error", "Failed to update project. Check logs.")
        else:
            QMessageBox.warning(self, "Error", f"Could not find project with ID {project_id_str} to edit.")

    def show_project_details(self, project_id_str):
        project_dict = db_manager.get_project_by_id(project_id_str)

        if project_dict:
            dialog = QDialog(self)
            dialog.setWindowTitle(self.tr("Project Details: {0}").format(project_dict.get('project_name', 'N/A')))
            dialog.setMinimumSize(700, 600) # Adjusted size for tabs

            dialog_main_layout = QVBoxLayout(dialog)
            details_tab_widget = QTabWidget()
            dialog_main_layout.addWidget(details_tab_widget)

            # --- Tab 1: Details & Tasks (Existing Content Adaptation) ---
            details_tasks_page = QWidget()
            details_tasks_layout = QVBoxLayout(details_tasks_page)

            info_group = QGroupBox(self.tr("Project Information"))
            info_layout = QFormLayout(info_group)
            # ... (Populate info_layout as before, using project_dict) ...
            name_label = QLabel(project_dict.get('project_name', 'N/A'))
            name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
            desc_label = QLabel(project_dict.get('description', "No description"))
            desc_label.setWordWrap(True)
            start_date_label = QLabel(project_dict.get('start_date', 'N/A'))
            deadline_label = QLabel(project_dict.get('deadline_date', 'N/A'))
            budget_label = QLabel(f"€{project_dict.get('budget', 0.0):,.2f}")
            status_id = project_dict.get('status_id')
            status_name_display = "Unknown"; status_color_hex = "#7f8c8d"
            if status_id is not None:
                status_setting = db_manager.get_status_setting_by_id(status_id)
                if status_setting:
                    status_name_display = status_setting.get('status_name', 'Unknown')
                    color_from_db = status_setting.get('color_hex')
                    if color_from_db: status_color_hex = color_from_db
            status_display_label = QLabel(status_name_display)
            status_display_label.setStyleSheet(f"color: {status_color_hex}; font-weight: bold;")
            priority_val = project_dict.get('priority', 0)
            priority_display_label = QLabel("Low" if priority_val == 0 else "Medium" if priority_val == 1 else "High")
            progress_label = QLabel(f"{project_dict.get('progress_percentage', 0)}%")
            manager_user_id = project_dict.get('manager_team_member_id')
            manager_display_name = "Unassigned"
            if manager_user_id:
                tm_list = db_manager.get_all_team_members({'user_id': manager_user_id})
                if tm_list: manager_display_name = tm_list[0].get('full_name', manager_user_id)
                else:
                    user = db_manager.get_user_by_id(manager_user_id)
                    if user: manager_display_name = user.get('full_name', manager_user_id)
            manager_label = QLabel(manager_display_name)

            info_layout.addRow(self.tr("Name:"), name_label)
            info_layout.addRow(self.tr("Description:"), desc_label)
            info_layout.addRow(self.tr("Start Date:"), start_date_label)
            info_layout.addRow(self.tr("Deadline:"), deadline_label)
            info_layout.addRow(self.tr("Budget:"), budget_label)
            info_layout.addRow(self.tr("Status:"), status_display_label)
            info_layout.addRow(self.tr("Priority:"), priority_display_label)
            info_layout.addRow(self.tr("Progress:"), progress_label)
            info_layout.addRow(self.tr("Manager:"), manager_label)
            details_tasks_layout.addWidget(info_group)

            tasks_group = QGroupBox(self.tr("Associated Tasks"))
            tasks_layout_inner = QVBoxLayout(tasks_group) # Renamed to avoid conflict
            tasks_table_details = QTableWidget() # Renamed to avoid conflict
            tasks_table_details.setColumnCount(4)
            tasks_table_details.setHorizontalHeaderLabels([self.tr("Task Name"), self.tr("Assigned To"), self.tr("Status"), self.tr("Deadline")])
            project_tasks = db_manager.get_tasks_by_project_id(project_id_str)
            if project_tasks:
                tasks_table_details.setRowCount(len(project_tasks))
                for r_idx, task_item in enumerate(project_tasks):
                    tasks_table_details.setItem(r_idx, 0, QTableWidgetItem(task_item.get('task_name')))
                    assignee_tm_id_detail = task_item.get('assignee_team_member_id')
                    assignee_name_detail = "Unassigned"
                    if assignee_tm_id_detail:
                        assignee_tm = db_manager.get_team_member_by_id(assignee_tm_id_detail)
                        if assignee_tm: assignee_name_detail = assignee_tm.get('full_name')
                    tasks_table_details.setItem(r_idx, 1, QTableWidgetItem(assignee_name_detail))
                    status_id_detail = task_item.get('status_id')
                    status_name_detail = "N/A"
                    if status_id_detail:
                        status_obj_detail = db_manager.get_status_setting_by_id(status_id_detail)
                        if status_obj_detail: status_name_detail = status_obj_detail.get('status_name')
                    tasks_table_details.setItem(r_idx, 2, QTableWidgetItem(status_name_detail))
                    tasks_table_details.setItem(r_idx, 3, QTableWidgetItem(task_item.get('due_date')))
            else:
                tasks_table_details.setRowCount(1)
                tasks_table_details.setItem(0,0, QTableWidgetItem(self.tr("No tasks found for this project.")))
                tasks_table_details.setSpan(0,0,1,4)
            tasks_table_details.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            tasks_layout_inner.addWidget(tasks_table_details)
            details_tasks_layout.addWidget(tasks_group)
            details_tab_widget.addTab(details_tasks_page, self.tr("Details & Tasks"))

            # --- Tab 2: Milestones ---
            milestones_page = QWidget()
            milestones_layout = QVBoxLayout(milestones_page)

            self.milestones_table_details_dialog = QTableWidget()
            self.milestones_table_details_dialog.setColumnCount(5)
            self.milestones_table_details_dialog.setHorizontalHeaderLabels([
                self.tr("Name"), self.tr("Description"), self.tr("Due Date"), self.tr("Status"), self.tr("Actions")
            ])
            self.milestones_table_details_dialog.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.milestones_table_details_dialog.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.milestones_table_details_dialog.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.milestones_table_details_dialog.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            milestones_layout.addWidget(self.milestones_table_details_dialog)

            milestone_btn_layout = QHBoxLayout()
            add_milestone_btn = QPushButton(self.tr("Add Milestone"))
            add_milestone_btn.clicked.connect(lambda: self._handle_add_milestone(project_id_str, dialog))
            edit_milestone_btn = QPushButton(self.tr("Edit Milestone"))
            edit_milestone_btn.clicked.connect(lambda: self._handle_edit_milestone(project_id_str, dialog))
            delete_milestone_btn = QPushButton(self.tr("Delete Milestone"))
            delete_milestone_btn.clicked.connect(lambda: self._handle_delete_milestone(project_id_str, dialog))

            add_milestone_btn.setStyleSheet(self.get_primary_button_style())
            edit_milestone_btn.setStyleSheet(self.get_secondary_button_style())
            delete_milestone_btn.setStyleSheet(self.get_danger_button_style())

            milestone_btn_layout.addWidget(add_milestone_btn)
            milestone_btn_layout.addWidget(edit_milestone_btn)
            milestone_btn_layout.addWidget(delete_milestone_btn)
            milestones_layout.addLayout(milestone_btn_layout)

            details_tab_widget.addTab(milestones_page, self.tr("Milestones"))

            self._load_milestones_into_table(project_id_str, self.milestones_table_details_dialog)

            button_box = QDialogButtonBox(QDialogButtonBox.Close)
            button_box.rejected.connect(dialog.reject)
            dialog_main_layout.addWidget(button_box)

            dialog.exec_()
        else:
            QMessageBox.warning(self, "Error", f"Could not retrieve details for project ID {project_id_str}.")

    def delete_project(self, project_id_str): # project_id is TEXT
        project_to_delete = db_manager.get_project_by_id(project_id_str) # Changed main_db_manager

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
            success = db_manager.delete_project(project_id_str) # Changed main_db_manager
            if success:
                self.load_projects()
                self.update_project_filter()
                self.log_activity(f"Deleted project: {project_name} (ID: {project_id_str})")
                # self.statusBar().showMessage(f"Project {project_name} deleted", 3000)
                print(f"Project {project_name} deleted")
            else:
                QMessageBox.warning(self, "Error", f"Failed to delete project {project_name}. Check logs.")

    def show_add_task_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("New Task")
        dialog.setFixedSize(450, 450)

        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Enter task name...")

        project_combo = QComboBox()
        all_projects = db_manager.get_all_projects() # Changed main_db_manager
        if all_projects:
            for p in all_projects:
                status_of_project_id = p.get('status_id')
                is_completion = False
                is_archival = False
                if status_of_project_id:
                    status_of_project = db_manager.get_status_setting_by_id(status_of_project_id) # Changed main_db_manager
                    is_completion = status_of_project.get('is_completion_status', False) if status_of_project else False
                    is_archival = status_of_project.get('is_archival_status', False) if status_of_project else False

                if not is_completion and not is_archival :
                     project_combo.addItem(p['project_name'], p['project_id'])
        if project_combo.count() == 0:
            project_combo.addItem("No Active Projects Available", None)
            project_combo.setEnabled(False)


        desc_edit = QTextEdit()
        desc_edit.setPlaceholderText("Detailed task description...")
        desc_edit.setMinimumHeight(80)

        status_combo = QComboBox()
        task_statuses = db_manager.get_all_status_settings(status_type='Task') # Changed main_db_manager
        if task_statuses:
            for ts in task_statuses:
                if not ts.get('is_completion_status') and not ts.get('is_archival_status'): # Do not allow setting to completed/archived initially
                    status_combo.addItem(ts['status_name'], ts['status_id'])
        if status_combo.count() == 0:
             status_combo.addItem("No Task Statuses Defined", None)
             status_combo.setEnabled(False)


        priority_combo = QComboBox()
        priority_combo.addItems(["Low", "Medium", "High"])
        priority_combo.setCurrentIndex(1)

        assignee_combo = QComboBox()
        assignee_combo.addItem("Unassigned", None)
        active_team_members = db_manager.get_all_team_members({'is_active': True}) # Changed main_db_manager
        if active_team_members:
            for tm in active_team_members:
                assignee_combo.addItem(tm['full_name'], tm['team_member_id'])

        # Predecessor Task ComboBox
        predecessor_task_combo = QComboBox()
        predecessor_task_combo.addItem("None", None)
        # Predecessor tasks will be populated when a project is selected or if editing.
        # For new tasks, project_combo.currentIndexChanged can trigger populating this.

        deadline_edit = QDateEdit(QDate.currentDate().addDays(7))
        deadline_edit.setCalendarPopup(True)
        deadline_edit.setDisplayFormat("yyyy-MM-dd")

        # Function to populate predecessors based on selected project
        def populate_predecessors_for_add_dialog():
            predecessor_task_combo.clear()
            predecessor_task_combo.addItem("None", None)
            selected_project_id_for_pred = project_combo.currentData()
            if selected_project_id_for_pred:
                project_tasks = db_manager.get_tasks_by_project_id(selected_project_id_for_pred)
                if project_tasks:
                    for pt in project_tasks:
                        predecessor_task_combo.addItem(pt['task_name'], pt['task_id'])

        project_combo.currentIndexChanged.connect(populate_predecessors_for_add_dialog)
        if project_combo.count() > 0 : populate_predecessors_for_add_dialog() # Initial population if project already selected

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        layout.addRow("Task Name:", name_edit)
        layout.addRow("Project:", project_combo)
        layout.addRow("Description:", desc_edit)
        layout.addRow("Status:", status_combo)
        layout.addRow("Priority:", priority_combo)
        layout.addRow("Assigned To:", assignee_combo)
        layout.addRow(self.tr("Predecessor Task:"), predecessor_task_combo) # Add to layout
        layout.addRow("Deadline:", deadline_edit)
        layout.addRow(button_box)

        if dialog.exec_() == QDialog.Accepted:
            task_name = name_edit.text()
            selected_project_id = project_combo.currentData()
            selected_predecessor_id = predecessor_task_combo.currentData()

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
            priority_for_db = 0
            if priority_text == "Medium": priority_for_db = 1
            elif priority_text == "High": priority_for_db = 2

            task_data_to_save = {
                'project_id': selected_project_id,
                'task_name': task_name,
                'description': desc_edit.toPlainText(),
                'status_id': status_combo.currentData(),
                'priority': priority_for_db,
                'assignee_team_member_id': assignee_combo.currentData(),
                'due_date': deadline_edit.date().toString("yyyy-MM-dd"),
            }

            # Set reporter_team_member_id if current_user is a team member
            if self.current_user and self.current_user.get('user_id'):
                # Find team_member_id for the current user_id
                current_user_as_tm_list = db_manager.get_all_team_members(filters={'user_id': self.current_user.get('user_id')})
                if current_user_as_tm_list:
                    task_data_to_save['reporter_team_member_id'] = current_user_as_tm_list[0].get('team_member_id')


            new_task_id = db_manager.add_task(task_data_to_save) # Changed main_db_manager

            if new_task_id:
                if selected_predecessor_id:
                    db_manager.add_task_dependency({'task_id': new_task_id, 'predecessor_task_id': selected_predecessor_id})
                self.load_tasks()
                self.log_activity(f"Added task: {task_name} (Project ID: {selected_project_id})")
                # self.statusBar().showMessage(f"Task '{task_name}' added successfully (ID: {new_task_id})", 3000)
                print(f"Task '{task_name}' added successfully (ID: {new_task_id})")
            else:
                QMessageBox.warning(self, "Database Error", "Failed to add task. Check logs.")

    def edit_task(self, task_id_int):
        task_data_dict = db_manager.get_task_by_id(task_id_int) # Changed main_db_manager

        if task_data_dict:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit Task: {task_data_dict.get('task_name', '')}")
            dialog.setFixedSize(450, 450)

            layout = QFormLayout(dialog)

            name_edit = QLineEdit(task_data_dict.get('task_name', ''))

            project_combo = QComboBox()
            all_projects = db_manager.get_all_projects() # Changed main_db_manager
            current_project_id_for_task = task_data_dict.get('project_id')
            if all_projects:
                for idx, p in enumerate(all_projects):
                    status_of_project_id = p.get('status_id')
                    is_completion = False
                    is_archival = False
                    if status_of_project_id:
                        status_of_project = db_manager.get_status_setting_by_id(status_of_project_id) # Changed main_db_manager
                        is_completion = status_of_project.get('is_completion_status', False) if status_of_project else False
                        is_archival = status_of_project.get('is_archival_status', False) if status_of_project else False
                    if (not is_completion and not is_archival) or p['project_id'] == current_project_id_for_task:
                        project_combo.addItem(p['project_name'], p['project_id'])
                        if p['project_id'] == current_project_id_for_task:
                            project_combo.setCurrentIndex(project_combo.count() -1)
            if project_combo.count() == 0:
                 project_info = db_manager.get_project_by_id(current_project_id_for_task) # Changed main_db_manager
                 if project_info : project_combo.addItem(project_info['project_name'], project_info['project_id'])
                 project_combo.setEnabled(False)


            desc_edit = QTextEdit(task_data_dict.get('description', ''))
            desc_edit.setPlaceholderText("Detailed task description...")
            desc_edit.setMinimumHeight(80)

            status_combo = QComboBox()
            task_statuses = db_manager.get_all_status_settings(status_type='Task') # Changed main_db_manager
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
            active_team_members = db_manager.get_all_team_members({'is_active': True}) # Changed main_db_manager
            current_assignee_tm_id = task_data_dict.get('assignee_team_member_id')
            if active_team_members:
                for idx, tm in enumerate(active_team_members):
                    assignee_combo.addItem(tm['full_name'], tm['team_member_id'])
                    if tm['team_member_id'] == current_assignee_tm_id:
                        assignee_combo.setCurrentIndex(idx + 1)

            # Predecessor Task ComboBox for Edit Dialog
            predecessor_task_combo_edit = QComboBox()
            predecessor_task_combo_edit.addItem("None", None)
            current_project_id_for_task_edit = task_data_dict.get('project_id')
            if current_project_id_for_task_edit:
                project_tasks_edit = db_manager.get_tasks_by_project_id(current_project_id_for_task_edit)
                if project_tasks_edit:
                    for pt_edit in project_tasks_edit:
                        if pt_edit['task_id'] != task_id_int: # Exclude self
                            predecessor_task_combo_edit.addItem(pt_edit['task_name'], pt_edit['task_id'])

            # Load existing dependency for edit
            predecessors_edit = db_manager.get_predecessor_tasks(task_id_int) # Conceptual
            if predecessors_edit: # Assuming returns a list, take the first for Phase 1
                index_edit = predecessor_task_combo_edit.findData(predecessors_edit[0]['task_id'])
                if index_edit != -1:
                    predecessor_task_combo_edit.setCurrentIndex(index_edit)


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
            layout.addRow(self.tr("Predecessor Task:"), predecessor_task_combo_edit) # Add to layout
            layout.addRow("Deadline:", deadline_edit)
            layout.addRow(button_box)

            if dialog.exec_() == QDialog.Accepted:
                updated_task_name = name_edit.text()
                updated_project_id = project_combo.currentData()
                selected_predecessor_id_edit = predecessor_task_combo_edit.currentData()

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
                selected_status_id = status_combo.currentData()
                if selected_status_id:
                    status_details = db_manager.get_status_setting_by_id(selected_status_id) # Changed main_db_manager
                    if status_details and status_details.get('is_completion_status'):
                        task_data_to_update['completed_at'] = datetime.utcnow().isoformat() + "Z"
                    else:
                        task_data_to_update['completed_at'] = None


                success = db_manager.update_task(task_id_int, task_data_to_update) # Changed main_db_manager

                if success:
                    # Update dependencies: Remove old (if any, for Phase 1 simplicity) and add new
                    existing_predecessors = db_manager.get_predecessor_tasks(task_id_int) # Conceptual
                    if existing_predecessors:
                        for pred in existing_predecessors: # Remove all old ones
                            db_manager.remove_task_dependency(task_id_int, pred['task_id']) # Conceptual

                    if selected_predecessor_id_edit:
                        db_manager.add_task_dependency({'task_id': task_id_int, 'predecessor_task_id': selected_predecessor_id_edit}) # Conceptual

                    self.load_tasks() # Refresh to show changes and dependency states
                    self.log_activity(f"Updated task: {updated_task_name} (ID: {task_id_int})")
                    # self.statusBar().showMessage(f"Task '{updated_task_name}' updated successfully", 3000)
                    print(f"Task '{updated_task_name}' updated successfully")
                else:
                    QMessageBox.warning(self, "Database Error", f"Failed to update task ID {task_id_int}. Check logs.")
        else:
            QMessageBox.warning(self, "Error", f"Could not find task with ID {task_id_int} to edit.")

    def complete_task(self, task_id_int): # task_id is INT
        task_to_complete = db_manager.get_task_by_id(task_id_int) # Changed main_db_manager
        if not task_to_complete:
            QMessageBox.warning(self, "Error", f"Task with ID {task_id_int} not found.")
            return

        task_name = task_to_complete.get('task_name', 'Unknown Task')

        completed_status_id = None
        task_statuses = db_manager.get_all_status_settings(status_type='Task') # Changed main_db_manager
        if task_statuses:
            for ts in task_statuses:
                if ts.get('is_completion_status'):
                    completed_status_id = ts['status_id']
                    break

        if completed_status_id is None:
            for common_completion_name in ["Completed", "Done"]:
                status_obj = db_manager.get_status_setting_by_name(common_completion_name, 'Task') # Changed main_db_manager
                if status_obj:
                    completed_status_id = status_obj['status_id']
                    break
            if completed_status_id is None:
                QMessageBox.warning(self, "Configuration Error", "No 'completion' status defined for tasks in StatusSettings.")
                return

        update_data = {
            'status_id': completed_status_id,
            'completed_at': datetime.utcnow().isoformat() + "Z"
        }
        success = db_manager.update_task(task_id_int, update_data) # Changed main_db_manager

        if success:
            self.load_tasks() # Refresh to update UI of dependent tasks
            self.log_activity(f"Task marked as completed: {task_name} (ID: {task_id_int})")
            # self.statusBar().showMessage(f"Task '{task_name}' marked as completed", 3000)
            print(f"Task '{task_name}' marked as completed")
        else:
            QMessageBox.warning(self, "Database Error", f"Failed to complete task '{task_name}'. Check logs.")


    def delete_task(self, task_id_int): # task_id is INT
        task_to_delete = db_manager.get_task_by_id(task_id_int) # Changed main_db_manager
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
            success = db_manager.delete_task(task_id_int) # Changed main_db_manager
            if success:
                self.load_tasks()
                self.log_activity(f"Deleted task: {task_name} (ID: {task_id_int})")
                # self.statusBar().showMessage(f"Task '{task_name}' deleted", 3000)
                print(f"Task '{task_name}' deleted")
            else:
                QMessageBox.warning(self, "Database Error", f"Failed to delete task '{task_name}'. Check logs.")

    def edit_user_access(self, user_id_str): # user_id is now a string (UUID) from db.py
        user_data = db_manager.get_user_by_id(user_id_str) # Changed main_db_manager

        if user_data: # user_data is a dict
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit Access for {user_data.get('full_name', 'N/A')}")
            dialog.setFixedSize(300, 200) # Indentation fixed

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

                    update_success = db_manager.update_user(user_id_str, {'role': new_role_for_db}) # Changed main_db_manager

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

            verified_user = db_manager.verify_user_password(current_username, current_pwd)
            if not verified_user or verified_user['user_id'] != user_id_to_update:
                QMessageBox.warning(self, "Error", "Current password is incorrect.")
                return
            # If password is correct, add new password to update_data.
            # db_manager.update_user will handle hashing.
            update_data['password'] = new_pwd

        # Update user information via db_manager
        success = db_manager.update_user(user_id_to_update, update_data)

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

        # Determine which top-level button to highlight
        # self.nav_buttons indices:
        # 0: Dashboard
        # 1: Management (Team, Settings, Notifications, Client Support, Prospect, Documents, Contacts)
        # 2: Activities (Projects, Tasks, Reports, Cover Pages)
        # 3: Add-on

        button_to_select_index = -1
        if index == 0: # Dashboard
            button_to_select_index = 0
        elif index == 1: # Team (under Management)
            button_to_select_index = 1
        elif index == 2: # Projects (under Activities)
            button_to_select_index = 2
        elif index == 3: # Tasks (under Activities)
            button_to_select_index = 2
        elif index == 4: # Reports (under Activities)
            button_to_select_index = 2
        elif index == 5: # Settings (under Management)
            button_to_select_index = 1
        elif index == 6: # Cover Page Management (under Activities)
            button_to_select_index = 2
        # Add other mappings if new pages/buttons are added.
        # The "Add-on" button (self.nav_buttons[3]) calls a different function,
        # so it's not handled by change_page's index logic directly.

        if 0 <= button_to_select_index < len(self.nav_buttons):
            selected_button = self.nav_buttons[button_to_select_index]
            selected_button.setObjectName("selected")
            selected_button.style().unpolish(selected_button)
            selected_button.style().polish(selected_button)
        else:
            # This case should ideally not be reached if all page indices are mapped.
            # If it is, it means an unmapped page index was called.
            print(f"Warning: change_page called with index {index}, but no corresponding top-level button found to highlight.")


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
            # Reports are generated on demand
            pass
        elif index == 5:  # Settings
            self.load_access_table()
            if self.current_user: # Also load user preferences if a user is logged in
                self.load_user_preferences()
        elif index == 6: # Cover Page Management
            self.load_clients_into_cp_combo() # Load/refresh clients
            self.load_cover_pages_for_selected_client() # Load cover pages for current selection

    def resizeEvent(self, event):
        super().resizeEvent(event) # Call parent's resizeEvent
        if hasattr(self, 'notification_manager') and hasattr(self.notification_manager, 'notification_banner') and self.notification_manager.notification_banner.isVisible():
            # Recalculate and move the banner to keep it in the top-right
            banner = self.notification_manager.notification_banner
            x = self.width() - banner.width() - 10
            y = 10 # 10px margin from top
            banner.move(x, y)

    # closeEvent is typically for QMainWindow. If this widget is embedded,
    # the main application's closeEvent will handle application closure.
    # def closeEvent(self, event):
    #     if self.current_user:
    #         self.log_activity(f"Application closed by {self.current_user['full_name']}")
    #     event.accept()

    # Helper style methods removed as styles are now in QSS
    # def get_table_action_button_style(self):
    # def get_generic_input_style(self):
    # def get_primary_button_style(self):
    # def get_secondary_button_style(self):
    # def get_danger_button_style(self):
    # def get_table_style(self):
    # def get_page_title_style(self):

    def setup_cover_page_management_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        title_label = QLabel("Cover Page Management")
        title_label.setObjectName("pageTitleLabel") # Style via QSS
        layout.addWidget(title_label)

        # Client Selection Area
        client_selection_layout = QHBoxLayout()
        client_selection_layout.addWidget(QLabel("Select Client:")) # General QLabel style applies
        self.cp_client_combo = QComboBox()
        self.cp_client_combo.setObjectName("coverPageClientCombo") # Specific styling if needed
        self.cp_client_combo.setMinimumWidth(250)
        self.cp_client_combo.currentIndexChanged.connect(self.load_cover_pages_for_selected_client)
        client_selection_layout.addWidget(self.cp_client_combo)
        client_selection_layout.addStretch()
        layout.addLayout(client_selection_layout)

        # Action Buttons Bar
        action_buttons_layout = QHBoxLayout()
        action_buttons_layout.setSpacing(10)

        self.cp_create_new_btn = QPushButton("Create New Cover Page")
        self.cp_create_new_btn.setObjectName("primaryButtonGreen")
        self.cp_create_new_btn.setIcon(QIcon(":/icons/file-plus.svg"))
        self.cp_create_new_btn.clicked.connect(self.create_new_cover_page_dialog)
        action_buttons_layout.addWidget(self.cp_create_new_btn)

        self.cp_edit_selected_btn = QPushButton("View/Edit Selected")
        self.cp_edit_selected_btn.setObjectName("secondaryButtonBlue")
        self.cp_edit_selected_btn.setIcon(QIcon(":/icons/edit-2.svg"))
        self.cp_edit_selected_btn.clicked.connect(self.edit_selected_cover_page_dialog)
        self.cp_edit_selected_btn.setEnabled(False) # Initially disabled
        action_buttons_layout.addWidget(self.cp_edit_selected_btn)

        self.cp_delete_selected_btn = QPushButton("Delete Selected")
        self.cp_delete_selected_btn.setObjectName("dangerButton")
        self.cp_delete_selected_btn.setIcon(QIcon(":/icons/trash.svg"))
        self.cp_delete_selected_btn.clicked.connect(self.delete_selected_cover_page)
        self.cp_delete_selected_btn.setEnabled(False) # Initially disabled
        action_buttons_layout.addWidget(self.cp_delete_selected_btn)
        action_buttons_layout.addStretch()
        layout.addLayout(action_buttons_layout)

        # Cover Page List Table
        self.cp_table = QTableWidget()
        self.cp_table.setColumnCount(4) # Name, Title, Last Modified, Actions
        self.cp_table.setHorizontalHeaderLabels(["Name", "Title", "Last Modified", "Actions"])
        # self.cp_table.setStyleSheet(self.get_table_style()) # Global style applies
        self.cp_table.verticalHeader().setVisible(False)
        self.cp_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.cp_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.cp_table.setSelectionMode(QTableWidget.SingleSelection)
        self.cp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cp_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.cp_table.itemSelectionChanged.connect(self.update_cover_page_action_buttons_state)
        layout.addWidget(self.cp_table)

        self.main_content.addWidget(page)

    def get_generic_input_style(self): # Helper for consistent input styling
        return """
            QComboBox {
                padding: 8px 10px; border: 1px solid #ced4da; border-radius: 4px; background-color: white;
            }
            QComboBox:focus { border-color: #80bdff; }
            QComboBox::drop-down {
                subcontrol-origin: padding; subcontrol-position: top right; width: 20px;
                border-left-width: 1px; border-left-color: #ced4da; border-left-style: solid;
                border-top-right-radius: 3px; border-bottom-right-radius: 3px;
            }
            QLineEdit, QTextEdit { padding: 8px 10px; border: 1px solid #ced4da; border-radius: 4px; background-color: white; }
            QLineEdit:focus, QTextEdit:focus { border-color: #80bdff; }
        """
    def get_primary_button_style(self):
        return """
            QPushButton { padding: 10px 18px; background-color: #28a745; color: white; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #218838; } QPushButton:pressed { background-color: #1e7e34; }
        """
    def get_secondary_button_style(self):
        return """
            QPushButton { padding: 10px 18px; background-color: #007bff; color: white; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #0069d9; } QPushButton:pressed { background-color: #005cbf; }
        """
    def get_danger_button_style(self):
        return """
            QPushButton { padding: 10px 18px; background-color: #dc3545; color: white; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #c82333; } QPushButton:pressed { background-color: #bd2130; }
        """
    def get_table_style(self):
        return """
            QTableWidget { background-color: white; border: 1px solid #dee2e6; border-radius: 5px; gridline-color: #e9ecef; }
            QHeaderView::section { background-color: #e9ecef; color: #495057; padding: 10px; font-weight: bold; border: none; border-bottom: 2px solid #dee2e6; }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:selected { background-color: #007bff; color: white; }
        """

    def get_page_title_style(self): # Helper for consistent page titles
        return "font-size: 22pt; font-weight: bold; color: #343a40; padding-bottom: 10px;"

    def load_clients_into_cp_combo(self):
        current_client_id = self.cp_client_combo.currentData()
        self.cp_client_combo.clear()
        self.cp_client_combo.addItem("Select a Client...", None)
        clients = db_manager.get_all_clients()
        if clients:
            for client in clients:
                self.cp_client_combo.addItem(f"{client['client_name']} ({client['client_id']})", client['client_id'])

        if current_client_id:
            index = self.cp_client_combo.findData(current_client_id)
            if index != -1:
                self.cp_client_combo.setCurrentIndex(index)
            else: # If previously selected client is gone, select "Select a Client..."
                 self.cp_client_combo.setCurrentIndex(0)


    def load_cover_pages_for_selected_client(self):
        client_id = self.cp_client_combo.currentData()
        self.cp_table.setRowCount(0) # Clear table
        self.update_cover_page_action_buttons_state() # Disable buttons if no client

        if client_id:
            cover_pages = db_manager.get_cover_pages_for_client(client_id)
            if cover_pages:
                self.cp_table.setRowCount(len(cover_pages))
                for row, cp_data in enumerate(cover_pages):
                    self.cp_table.setItem(row, 0, QTableWidgetItem(cp_data.get('cover_page_name', 'N/A')))
                    self.cp_table.setItem(row, 1, QTableWidgetItem(cp_data.get('title', 'N/A')))
                    self.cp_table.setItem(row, 2, QTableWidgetItem(cp_data.get('updated_at', 'N/A')))

                    # Actions column
                    edit_action_btn = QPushButton(""); edit_action_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg")))
                    edit_action_btn.setToolTip("Edit Cover Page")
                    edit_action_btn.setObjectName("tableActionButton")
                    # Use a partial or a helper to capture current cp_data for the lambda
                    edit_action_btn.clicked.connect(lambda checked=False, r_data=cp_data: self.edit_selected_cover_page_dialog(row_data=r_data))

                    delete_action_btn = QPushButton(""); delete_action_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon(":/icons/trash.svg")))
                    delete_action_btn.setToolTip("Delete Cover Page")
                    delete_action_btn.setObjectName("dangerButtonTable")
                    delete_action_btn.clicked.connect(lambda checked=False, r_data=cp_data: self.delete_selected_cover_page(row_data=r_data))

                    action_widget = QWidget()
                    action_layout = QHBoxLayout(action_widget)
                    action_layout.addWidget(edit_action_btn)
                    action_layout.addWidget(delete_action_btn)
                    action_layout.setContentsMargins(0,0,0,0)
                    action_layout.addStretch() # Optional: to push buttons to left if desired
                    self.cp_table.setCellWidget(row, 3, action_widget)

                    # Store cover_page_id in the first item for easy retrieval (if needed, or directly use from row_data)
                    self.cp_table.item(row, 0).setData(Qt.UserRole, cp_data['cover_page_id'])
            self.cp_table.resizeColumnsToContents()


    def update_cover_page_action_buttons_state(self):
        selected_items = self.cp_table.selectedItems()
        has_selection = bool(selected_items)
        self.cp_edit_selected_btn.setEnabled(has_selection)
        self.cp_delete_selected_btn.setEnabled(has_selection)

    def create_new_cover_page_dialog(self):
        client_id = self.cp_client_combo.currentData()
        if not client_id:
            QMessageBox.warning(self, "No Client Selected", "Please select a client before creating a new cover page.")
            return

        if not self.current_user or not self.current_user.get('user_id'):
            QMessageBox.warning(self, "User Error", "No logged-in user found. Cannot create cover page.")
            return
        user_id = self.current_user['user_id']

        dialog = CoverPageEditorDialog(mode="create", client_id=client_id, user_id=user_id, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_cover_pages_for_selected_client()
            self.log_activity(f"Created new cover page for client {client_id}")

    def edit_selected_cover_page_dialog(self, row_data=None): # row_data can be passed from action button click
        if not row_data:
            selected_items = self.cp_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "No Selection", "Please select a cover page to edit.")
                return
            cover_page_id = selected_items[0].data(Qt.UserRole) # Assuming ID is in UserRole of first item
        else:
            cover_page_id = row_data.get('cover_page_id')

        if not cover_page_id:
            QMessageBox.warning(self, "Error", "Could not determine cover page ID for editing.")
            return

        cover_page_full_data = db_manager.get_cover_page_by_id(cover_page_id)
        if not cover_page_full_data:
            QMessageBox.critical(self, "Error", f"Could not retrieve cover page data for ID: {cover_page_id}")
            return

        dialog = CoverPageEditorDialog(mode="edit", cover_page_data=cover_page_full_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_cover_pages_for_selected_client()
            self.log_activity(f"Edited cover page ID: {cover_page_id}")

    # --- Milestone Management Helper Methods ---
    def _load_milestones_into_table(self, project_id, table_widget):
        table_widget.setRowCount(0)
        milestones = db_manager.get_milestones_for_project(project_id)
        if not milestones:
            return

        for row_idx, milestone in enumerate(milestones):
            table_widget.insertRow(row_idx)
            table_widget.setItem(row_idx, 0, QTableWidgetItem(milestone.get('milestone_name', 'N/A')))

            desc_item = QTableWidgetItem(milestone.get('description', ''))
            # desc_item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft) # Optional: if you want multi-line text to align top
            table_widget.setItem(row_idx, 1, desc_item)

            table_widget.setItem(row_idx, 2, QTableWidgetItem(milestone.get('due_date', 'N/A')))

            status_name = milestone.get('status_name', self.tr('N/A'))
            status_color_hex = milestone.get('color_hex', '#000000') # Default to black if no color
            status_item = QTableWidgetItem(status_name)
            status_item.setForeground(QColor(status_color_hex))
            table_widget.setItem(row_idx, 3, status_item)

            # Store milestone_id in the first item of the row for easy access
            table_widget.item(row_idx, 0).setData(Qt.UserRole, milestone.get('milestone_id'))

            # Actions - For Phase 1, main buttons below table are used. In-row actions can be added later.
            # For now, this column can be empty or show a placeholder / be hidden.
            # If hidden: table_widget.setColumnCount(4) and remove "Actions" header.
            # For now, let it be, can be enhanced.
            # Example placeholder:
            edit_action_btn_placeholder = QPushButton("...")
            edit_action_btn_placeholder.setEnabled(False)
            # Removed styleSheet call
            action_widget_placeholder = QWidget()
            action_layout_placeholder = QHBoxLayout(action_widget_placeholder)
            action_layout_placeholder.addWidget(edit_action_btn_placeholder)
            action_layout_placeholder.setContentsMargins(0,0,0,0)
            table_widget.setCellWidget(row_idx, 4, action_widget_placeholder)


        table_widget.resizeColumnsToContents()
        table_widget.resizeRowsToContents() # For multi-line descriptions

    def _handle_add_milestone(self, project_id, parent_dialog_ref): # parent_dialog_ref can be used to keep dialog on top
        dialog = AddEditMilestoneDialog(project_id, parent=parent_dialog_ref if parent_dialog_ref else self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if data:
                milestone_id = db_manager.add_milestone(data)
                if milestone_id:
                    self.log_activity(f"Added milestone '{data['milestone_name']}' to project {project_id}")
                    self._load_milestones_into_table(project_id, self.milestones_table_details_dialog)
                else:
                    QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to add milestone."))

    def _handle_edit_milestone(self, project_id, parent_dialog_ref): # Added project_id for logging
        selected_items = self.milestones_table_details_dialog.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("No Selection"), self.tr("Please select a milestone to edit."))
            return

        milestone_id_to_edit = selected_items[0].data(Qt.UserRole) # Assumes ID is in UserRole of first item of selected row
        if milestone_id_to_edit is None: # Fallback if UserRole not set on first item, check other items in row.
            for item in selected_items: # Check all items in the selected row
                 if item.data(Qt.UserRole) is not None:
                      milestone_id_to_edit = item.data(Qt.UserRole)
                      break
        if milestone_id_to_edit is None:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Could not retrieve milestone ID for editing."))
            return

        milestone_data_to_edit = db_manager.get_milestone_by_id(milestone_id_to_edit)
        if not milestone_data_to_edit:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Could not fetch milestone data for editing."))
            return

        dialog = AddEditMilestoneDialog(project_id, milestone_data=milestone_data_to_edit, parent=parent_dialog_ref if parent_dialog_ref else self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if data:
                success = db_manager.update_milestone(milestone_id_to_edit, data)
                if success:
                    self.log_activity(f"Updated milestone ID {milestone_id_to_edit} for project {project_id}")
                    self._load_milestones_into_table(project_id, self.milestones_table_details_dialog)
                else:
                    QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to update milestone."))

    def _handle_delete_milestone(self, project_id, parent_dialog_ref):
        selected_items = self.milestones_table_details_dialog.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("No Selection"), self.tr("Please select a milestone to delete."))
            return

        milestone_id_to_delete = selected_items[0].data(Qt.UserRole)
        if milestone_id_to_delete is None:
             for item in selected_items:
                 if item.data(Qt.UserRole) is not None:
                      milestone_id_to_delete = item.data(Qt.UserRole)
                      break
        if milestone_id_to_delete is None:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Could not retrieve milestone ID for deletion."))
            return

        milestone_name_to_delete = self.milestones_table_details_dialog.item(selected_items[0].row(), 0).text()

        reply = QMessageBox.question(self, self.tr("Confirm Deletion"),
                                     self.tr("Are you sure you want to delete milestone '{0}'?").format(milestone_name_to_delete),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            success = db_manager.delete_milestone(milestone_id_to_delete)
            if success:
                self.log_activity(f"Deleted milestone ID {milestone_id_to_delete} from project {project_id}")
                self._load_milestones_into_table(project_id, self.milestones_table_details_dialog)
            else:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to delete milestone."))

    def delete_selected_cover_page(self, row_data=None):
        if not row_data:
            selected_items = self.cp_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "No Selection", "Please select a cover page to delete.")
                return
            cover_page_id = selected_items[0].data(Qt.UserRole)
            cover_page_name = selected_items[0].text()
        else:
            cover_page_id = row_data.get('cover_page_id')
            cover_page_name = row_data.get('cover_page_name', 'this item')

        if not cover_page_id:
            QMessageBox.warning(self, "Error", "Could not determine cover page ID for deletion.")
            return

        reply = QMessageBox.question(self, "Confirm Deletion",
                                     f"Are you sure you want to delete the cover page '{cover_page_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if db_manager.delete_cover_page(cover_page_id):
                self.load_cover_pages_for_selected_client()
                self.log_activity(f"Deleted cover page ID: {cover_page_id}")
                QMessageBox.information(self, "Success", f"Cover page '{cover_page_name}' deleted.")
            else:
                QMessageBox.critical(self, "Error", f"Failed to delete cover page '{cover_page_name}'.")


# Cover Page Editor Dialog
class CoverPageEditorDialog(QDialog):
    def __init__(self, mode, client_id=None, user_id=None, cover_page_data=None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.client_id = client_id
        self.user_id = user_id
        self.cover_page_data = cover_page_data or {} # Ensure it's a dict
        self.current_logo_bytes = self.cover_page_data.get('logo_data')
        self.current_logo_name = self.cover_page_data.get('logo_name')


        self.setWindowTitle(f"{'Edit' if mode == 'edit' else 'Create New'} Cover Page")
        self.setMinimumSize(600, 750) # Increased size for more fields & placeholder

        main_layout = QVBoxLayout(self)

        # Consistent styling for inputs within the dialog - MOVED to global QSS
        # self.setStyleSheet(dialog_input_style) # Apply to the whole dialog

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setSpacing(10)

        # Cover Page Instance Name
        self.cp_name_edit = QLineEdit(self.cover_page_data.get('cover_page_name', ''))
        form_layout.addRow("Cover Page Name:", self.cp_name_edit)

        # Template Selection
        self.cp_template_combo = QComboBox()
        self.populate_templates_combo()
        self.cp_template_combo.currentIndexChanged.connect(self.on_template_selected)
        form_layout.addRow("Use Template (Optional):", self.cp_template_combo)

        # Document Info Group
        doc_info_group = QGroupBox("Document Information")
        doc_info_form_layout = QFormLayout(doc_info_group)

        self.title_edit = QLineEdit(self.cover_page_data.get('title', ''))
        self.subtitle_edit = QLineEdit(self.cover_page_data.get('subtitle', ''))
        self.author_text_edit = QLineEdit(self.cover_page_data.get('author_text', '')) # Consider renaming to 'author' in db if this is main author field
        self.institution_text_edit = QLineEdit(self.cover_page_data.get('institution_text', ''))
        self.department_text_edit = QLineEdit(self.cover_page_data.get('department_text', ''))
        self.document_type_text_edit = QLineEdit(self.cover_page_data.get('document_type_text', ''))
        self.document_date_edit = QDateEdit(QDate.fromString(self.cover_page_data.get('document_date', QDate.currentDate().toString(Qt.ISODate)), Qt.ISODate))
        self.document_date_edit.setCalendarPopup(True)
        self.document_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.document_version_edit = QLineEdit(self.cover_page_data.get('document_version', ''))

        doc_info_form_layout.addRow("Title:", self.title_edit)
        doc_info_form_layout.addRow("Subtitle:", self.subtitle_edit)
        doc_info_form_layout.addRow("Author:", self.author_text_edit) # Changed label for clarity
        doc_info_form_layout.addRow("Institution:", self.institution_text_edit) # Changed label
        doc_info_form_layout.addRow("Department:", self.department_text_edit) # Changed label
        doc_info_form_layout.addRow("Document Type:", self.document_type_text_edit) # Changed label
        doc_info_form_layout.addRow("Document Date:", self.document_date_edit)
        doc_info_form_layout.addRow("Version:", self.document_version_edit) # Changed label
        form_layout.addRow(doc_info_group)

        # Logo Section
        logo_group = QGroupBox("Logo")
        logo_layout = QHBoxLayout(logo_group)
        self.logo_preview_label = QLabel("No logo selected.")
        self.logo_preview_label.setFixedSize(150,150) # Slightly larger preview
        self.logo_preview_label.setAlignment(Qt.AlignCenter)
        self.logo_preview_label.setStyleSheet("border: 1px dashed #ccc;") # Keeping this specific one for now
        self.update_logo_preview()

        browse_logo_btn = QPushButton("Browse...")
        browse_logo_btn.setObjectName("secondaryButton") # Use object name
        browse_logo_btn.setIcon(QIcon.fromTheme("document-open", QIcon(":/icons/eye.svg")))
        browse_logo_btn.clicked.connect(self.browse_logo)

        clear_logo_btn = QPushButton("Clear Logo")
        clear_logo_btn.setObjectName("dangerButton") # Use object name
        clear_logo_btn.setIcon(QIcon.fromTheme("edit-clear", QIcon(":/icons/trash.svg")))
        clear_logo_btn.clicked.connect(self.clear_logo)

        logo_btn_layout = QVBoxLayout()
        logo_btn_layout.addWidget(browse_logo_btn)
        logo_btn_layout.addWidget(clear_logo_btn)
        logo_btn_layout.addStretch()

        logo_layout.addWidget(self.logo_preview_label)
        logo_layout.addLayout(logo_btn_layout)
        form_layout.addRow(logo_group)

        # Style Configuration
        style_group = QGroupBox("Advanced Style Configuration (JSON)")
        style_layout = QVBoxLayout(style_group)

        style_info_label = QLabel("Edit advanced style properties (e.g., fonts, colors, positions). Refer to documentation for available keys.")
        style_info_label.setWordWrap(True)
        style_layout.addWidget(style_info_label)

        self.style_config_json_edit = QTextEdit()
        detailed_placeholder = """{
    "title_font_family": "Arial", "title_font_size": 30, "title_color": "#000000",
    "subtitle_font_family": "Arial", "subtitle_font_size": 20, "subtitle_color": "#555555",
    "author_font_family": "Arial", "author_font_size": 12, "author_color": "#555555",
    "logo_width_mm": 50, "logo_height_mm": 50, "logo_x_mm": 80, "logo_y_mm": 200,
    "show_page_border": true, "page_border_color": "#000000", "page_border_width_pt": 1,
    "show_horizontal_line": true, "horizontal_line_y_mm": 140, "horizontal_line_color": "#000000",
    "text_alignment_title": "center", "text_alignment_subtitle": "center", "text_alignment_author": "center"
}"""
        self.style_config_json_edit.setPlaceholderText(detailed_placeholder)
        self.style_config_json_edit.setMinimumHeight(200) # Increased height

        style_json_str = self.cover_page_data.get('style_config_json', '{}')
        if isinstance(style_json_str, dict):
            style_json_str = json.dumps(style_json_str, indent=4) # Use 4 spaces for placeholder consistency
        elif isinstance(style_json_str, str):
            try:
                parsed_json = json.loads(style_json_str)
                style_json_str = json.dumps(parsed_json, indent=4)
            except json.JSONDecodeError:
                style_json_str = json.dumps({}, indent=4) # Default to empty formatted JSON
        self.style_config_json_edit.setText(style_json_str)

        style_layout.addWidget(self.style_config_json_edit)
        form_layout.addRow(style_group)

        main_layout.addLayout(form_layout)

        # Dialog Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.on_save)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        if self.mode == 'edit' and self.cover_page_data.get('template_id'):
            template_id_to_select = self.cover_page_data['template_id']
            index = self.cp_template_combo.findData(template_id_to_select)
            if index != -1:
                self.cp_template_combo.setCurrentIndex(index)
            # Field values are already set from cover_page_data, template only pre-fills on change
        elif self.mode == 'create': # If creating, and a default template exists, select it
            default_template_index = self.cp_template_combo.findData("DEFAULT_TEMPLATE_PLACEHOLDER", Qt.UserRole + 1) # Check if a default was marked
            if default_template_index != -1:
                self.cp_template_combo.setCurrentIndex(default_template_index)
                self.on_template_selected(default_template_index) # Trigger pre-fill


    def populate_templates_combo(self):
        self.cp_template_combo.addItem("None (Custom)", None)
        templates = db_manager.get_all_cover_page_templates()
        if templates:
            for tpl in templates:
                self.cp_template_combo.addItem(tpl['template_name'], tpl['template_id'])
                if tpl.get('is_default_template'):
                    # Mark this item specially if needed, e.g. by setting a special UserRole
                    # For now, just pre-select if mode is 'create'
                    self.cp_template_combo.setItemData(self.cp_template_combo.count() -1, "DEFAULT_TEMPLATE_PLACEHOLDER", Qt.UserRole + 1)


    def on_template_selected(self, index):
        template_id = self.cp_template_combo.itemData(index)
        if not template_id: # "None" selected
            # Optionally clear fields or revert to initial_data if that's desired
            # For now, user changes are kept unless a specific template is chosen
            if self.mode == 'create': # For create mode, "None" means truly blank slate
                self.title_edit.setText("")
                self.subtitle_edit.setText("")
                self.author_text_edit.setText("")
                self.institution_text_edit.setText("")
                self.department_text_edit.setText("")
                self.document_type_text_edit.setText("")
                self.document_date_edit.setDate(QDate.currentDate())
                self.document_version_edit.setText("")
                self.style_config_json_edit.setText("{\n  \n}")
                self.current_logo_bytes = None
                self.current_logo_name = None
                self.update_logo_preview()
            return

        template_data = db_manager.get_cover_page_template_by_id(template_id)
        if template_data:
            self.title_edit.setText(template_data.get('default_title', ''))
            self.subtitle_edit.setText(template_data.get('default_subtitle', ''))
            self.author_text_edit.setText(template_data.get('default_author_text', ''))
            self.institution_text_edit.setText(template_data.get('default_institution_text', ''))
            self.department_text_edit.setText(template_data.get('default_department_text', ''))
            self.document_type_text_edit.setText(template_data.get('default_document_type_text', ''))

            doc_date_str = template_data.get('default_document_date', '')
            if doc_date_str:
                 self.document_date_edit.setDate(QDate.fromString(doc_date_str, Qt.ISODate))
            else: # If template has no date, use current
                 self.document_date_edit.setDate(QDate.currentDate())

            self.document_version_edit.setText(template_data.get('default_document_version', ''))

            style_json = template_data.get('style_config_json', '{}')
            try: # Ensure it's nicely formatted
                parsed = json.loads(style_json)
                self.style_config_json_edit.setText(json.dumps(parsed, indent=2))
            except json.JSONDecodeError:
                self.style_config_json_edit.setText(style_json) # Show as is if not valid JSON for some reason

            self.current_logo_bytes = template_data.get('default_logo_data')
            self.current_logo_name = template_data.get('default_logo_name')
            self.update_logo_preview()


    def browse_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Logo Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    self.current_logo_bytes = f.read()
                self.current_logo_name = os.path.basename(file_path)
                self.update_logo_preview()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load logo: {e}")
                self.current_logo_bytes = None
                self.current_logo_name = None
                self.update_logo_preview()

    def clear_logo(self):
        self.current_logo_bytes = None
        self.current_logo_name = None
        self.update_logo_preview()

    def update_logo_preview(self):
        if self.current_logo_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(self.current_logo_bytes)
            self.logo_preview_label.setPixmap(pixmap.scaled(self.logo_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.logo_preview_label.setText("No logo")


    def on_save(self):
        cp_name = self.cp_name_edit.text().strip()
        if not cp_name:
            QMessageBox.warning(self, "Validation Error", "Cover Page Name is required.")
            return

        style_config_str = self.style_config_json_edit.toPlainText()
        try:
            json.loads(style_config_str) # Validate JSON
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "Invalid JSON", f"Style Configuration is not valid JSON: {e}")
            return

        data_to_save = {
            'cover_page_name': cp_name,
            'client_id': self.client_id if self.mode == 'create' else self.cover_page_data.get('client_id'),
            'created_by_user_id': self.user_id if self.mode == 'create' else self.cover_page_data.get('created_by_user_id', self.user_id), # Align with db.py
            'template_id': self.cp_template_combo.currentData(),
            'title': self.title_edit.text(),
            'subtitle': self.subtitle_edit.text(),
            'author_text': self.author_text_edit.text(),
            'institution_text': self.institution_text_edit.text(),
            'department_text': self.department_text_edit.text(),
            'document_type_text': self.document_type_text_edit.text(),
            'creation_date': self.document_date_edit.date().toString(Qt.ISODate), # Align with db.py
            'document_version': self.document_version_edit.text(),
            'logo_data': self.current_logo_bytes,
            'logo_name': self.current_logo_name,
            'style_config_json': style_config_str
        }

        # Ensure created_by_user_id is present for edit mode if it was missing from original data
        if self.mode == 'edit' and not data_to_save.get('created_by_user_id') and self.user_id:
             data_to_save['created_by_user_id'] = self.user_id


        if self.mode == 'create':
            if not data_to_save.get('created_by_user_id'): # Final check for creator ID in create mode
                QMessageBox.critical(self, "Error", "User ID for creation is missing.")
                return

            new_id = db_manager.add_cover_page(data_to_save)
            if new_id:
                self.cover_page_data['cover_page_id'] = new_id
                QMessageBox.information(self, "Success", "Cover page created successfully.")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to create cover page.")
        elif self.mode == 'edit':
            if db_manager.update_cover_page(self.cover_page_data['cover_page_id'], data_to_save):
                QMessageBox.information(self, "Success", "Cover page updated successfully.")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to update cover page.")


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
    db_manager.initialize_database()

    # Create a dummy QMainWindow to host the QWidget for testing
    test_host_window = QMainWindow()
    test_host_window.setWindowTitle("Standalone Project Dashboard Test")

    # Pass the dummy user to the dashboard
    dashboard_widget = MainDashboard(parent=test_host_window, current_user=dummy_user)

    test_host_window.setCentralWidget(dashboard_widget) # Host it in a QMainWindow for testing
    test_host_window.setGeometry(100, 100, 1400, 900) # Set geometry on the host window
    test_host_window.show()

    sys.exit(app.exec_())

    def focus_on_project(self, project_id_to_focus):
        # Switch to the projects page/tab
        self.change_page(2) # Assuming index 2 is 'Projects' page

        # Find the row for the project_id in self.projects_table
        for row in range(self.projects_table.rowCount()):
            item = self.projects_table.item(row, 0) # Name item where project_id is stored
            if item and item.data(Qt.UserRole) == project_id_to_focus:
                self.projects_table.selectRow(row)
                self.projects_table.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                # Optional: directly open project details dialog
                # self.show_project_details(project_id_to_focus)
                break
        else: # Project not found in table
            print(f"Project ID {project_id_to_focus} not found in projects table for focusing.")
            # Optionally, show a message to the user
            if hasattr(self, 'show_notification'): # Check if notification system exists
                 self.show_notification(self.tr("Project Not Found"),
                                        self.tr("Could not find project {0} in the list.").format(project_id_to_focus),
                                        duration=7000)
            elif hasattr(self, 'notification_manager'): # Check if legacy notification manager exists
                 self.notification_manager.show_notification(self.tr("Project Not Found"),
                                        self.tr("Could not find project {0} in the list.").format(project_id_to_focus))
            else: # Fallback
                QMessageBox.information(self, self.tr("Project Not Found"), self.tr("Could not find project {0} in the list.").format(project_id_to_focus))



                