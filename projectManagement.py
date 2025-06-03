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
from imports import DB_PATH_management

class DatabaseManager:
    def __init__(self, db_name=DB_PATH_management):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL,
                    phone TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Team members table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS team_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    department TEXT NOT NULL,
                    hire_date TEXT NOT NULL,
                    performance INTEGER DEFAULT 0,
                    skills TEXT,
                    notes TEXT,
                    status TEXT DEFAULT 'active'
                )
            ''')

            # Projects table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    start_date TEXT NOT NULL,
                    deadline TEXT NOT NULL,
                    budget REAL NOT NULL,
                    status TEXT DEFAULT 'planning',
                    progress INTEGER DEFAULT 0,
                    manager_id INTEGER,
                    priority TEXT DEFAULT 'medium',
                    FOREIGN KEY (manager_id) REFERENCES team_members(id)
                )
            ''')

            # Tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    assignee_id INTEGER,
                    status TEXT DEFAULT 'todo',
                    priority TEXT DEFAULT 'medium',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    deadline TEXT,
                    completed_at TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (assignee_id) REFERENCES team_members(id)
                )
            ''')

            # KPIs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS kpis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    target REAL NOT NULL,
                    trend TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Activities table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')

            # Insert default admin if necessary
            cursor.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
            if cursor.fetchone()[0] == 0:
                hashed_pwd = hashlib.sha256('admin123'.encode()).hexdigest()
                cursor.execute('''
                    INSERT INTO users (username, password, full_name, email, role)
                    VALUES (?, ?, ?, ?, ?)
                ''', ('admin', hashed_pwd, 'Administrator', 'admin@company.com', 'admin'))

            conn.commit()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

class NotificationManager:
    def __init__(self, parent_window, db_manager):
        self.parent_window = parent_window
        self.db_manager = db_manager
        self.timer = QTimer(parent_window)

    def setup_timer(self, interval_ms=300000):  # Default 5 minutes
        self.timer.timeout.connect(self.check_notifications)
        self.timer.start(interval_ms)
        print(f"Notification timer started with interval: {interval_ms}ms") # For debugging

    def check_notifications(self):
        print(f"Checking notifications at {datetime.now()}") # For debugging
        notifications_found = []
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Urgent Projects: priority = 'high' and status NOT IN ('completed', 'archived', 'deleted')
                cursor.execute("""
                    SELECT id, name FROM projects
                    WHERE priority = 'high' AND status NOT IN ('completed', 'archived', 'deleted')
                """)
                urgent_projects = cursor.fetchall()
                for p_id, name in urgent_projects:
                    notifications_found.append({
                        "title": "Urgent Project Reminder",
                        "message": f"Project '{name}' (ID: {p_id}) is marked as high priority and requires attention.",
                        "project_id": p_id
                    })

                # Tasks Nearing Deadline: priority = 'high' and status NOT IN ('completed', 'deleted') and deadline within next 3 days
                three_days_later = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
                today_str = datetime.now().strftime('%Y-%m-%d')
                cursor.execute("""
                    SELECT t.id, t.name, p.name AS project_name, t.deadline
                    FROM tasks t
                    JOIN projects p ON t.project_id = p.id
                    WHERE t.priority = 'high' AND t.status NOT IN ('completed', 'deleted')
                    AND t.deadline >= ? AND t.deadline <= ?
                """, (today_str, three_days_later))
                tasks_nearing_deadline_high_priority = cursor.fetchall()
                for t_id, name, project_name, deadline in tasks_nearing_deadline_high_priority:
                    notifications_found.append({
                        "title": "High Priority Task Nearing Deadline",
                        "message": f"Task '{name}' for project '{project_name}' (Deadline: {deadline}) is high priority and approaching its deadline.",
                        "task_id": t_id
                    })

                # Overdue Projects: deadline passed and status NOT IN ('completed', 'archived', 'deleted')
                cursor.execute("""
                    SELECT id, name, deadline FROM projects
                    WHERE deadline < ? AND status NOT IN ('completed', 'archived', 'deleted')
                """, (today_str,))
                overdue_projects = cursor.fetchall()
                for p_id, name, deadline in overdue_projects:
                    notifications_found.append({
                        "title": "Overdue Project Alert",
                        "message": f"Project '{name}' (ID: {p_id}) was due on {deadline} and is not completed or archived.",
                        "project_id": p_id
                    })

                # Overdue Tasks: deadline passed and status NOT IN ('completed', 'deleted')
                cursor.execute("""
                    SELECT t.id, t.name, p.name AS project_name, t.deadline
                    FROM tasks t
                    JOIN projects p ON t.project_id = p.id
                    WHERE t.deadline < ? AND t.status NOT IN ('completed', 'deleted')
                """, (today_str,))
                overdue_tasks = cursor.fetchall()
                for t_id, name, project_name, deadline in overdue_tasks:
                    notifications_found.append({
                        "title": "Overdue Task Alert",
                        "message": f"Task '{name}' for project '{project_name}' was due on {deadline} and is not completed.",
                        "task_id": t_id
                    })

        except sqlite3.Error as e:
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


class MainDashboard(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.db = DatabaseManager()
        self.current_user = None

        self.setWindowTitle("Management Dashboard Pro")
        self.setWindowIcon(QIcon(self.resource_path('icons/app_icon.png')))
        self.setGeometry(100, 100, 1400, 900)

        # Global style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f7fa;
            }
            QLabel {
                color: #333333;
            }
        """)

        self.init_ui()
        self.load_initial_data()

        # Notification System Initialization
        self.notification_manager = NotificationManager(self, self.db) # self.db is DatabaseManager instance
        self.notification_manager.setup_timer() # Default interval is 5 minutes

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
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Use vertical layout now (topbar above main content)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Topbar (replaces sidebar)
        self.setup_topbar()  # Replaces setup_sidebar()
        main_layout.addWidget(self.topbar)

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
        main_layout.addWidget(self.main_content)

        # Status bar
        self.statusBar().showMessage("Ready")

        # Check if user is logged in
        if not self.current_user:
            pass
            # self.show_login_dialog()

    def setup_topbar(self):
        self.topbar = QFrame()
        self.topbar.setFixedHeight(70)  # Slightly taller for more elegance
        self.topbar.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                color: white;
                border-bottom: 1px solid #3498db;
            }
            QPushButton {
                background-color: transparent;
                color: white;
                padding: 10px 15px;
                border: none;
                font-size: 14px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #34495e;
            }
            QPushButton#selected {
                background-color: #3498db;
                font-weight: bold;
                border-left: 3px solid white;
            }
            QPushButton#menu_button {
                padding-right: 25px;
                position: relative;
            }
            QPushButton#menu_button::after {
                content: "▼";
                position: absolute;
                right: 8px;
                top: 50%;
                transform: translateY(-50%);
                font-size: 10px;
            }
            QLabel {
                color: white;
            }
            QMenu {
                background-color: #34495e;
                color: white;
                border: 1px solid #3498db;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 25px 8px 15px;
            }
            QMenu::item:selected {
                background-color: #3498db;
            }
            QMenu::icon {
                padding-left: 10px;
            }
        """)

        topbar_layout = QHBoxLayout(self.topbar)
        topbar_layout.setContentsMargins(15, 10, 15, 10)
        topbar_layout.setSpacing(20)

        # Logo and title - Left side
        logo_container = QHBoxLayout()
        logo_container.setSpacing(10)

        logo_icon = QLabel()
        logo_icon.setPixmap(QIcon(self.resource_path('icons/logo.png')).pixmap(45, 45))

        logo_text = QLabel("Management Pro")
        logo_text.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #3498db;
            font-family: 'Segoe UI', Arial, sans-serif;
        """)

        logo_container.addWidget(logo_icon)
        logo_container.addWidget(logo_text)
        topbar_layout.addLayout(logo_container)

        # Central space for menus
        topbar_layout.addStretch(1)

        # Main Menu - Center
        self.nav_buttons = []

        # Dashboard button (single)
        dashboard_btn = QPushButton("Dashboard")
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
        management_btn.setIcon(QIcon(self.resource_path('icons/management.png')))
        management_btn.setMenu(management_menu)
        management_btn.setObjectName("menu_button")
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
        projects_btn.setIcon(QIcon(self.resource_path('icons/activities.png')))
        projects_btn.setMenu(projects_menu)
        projects_btn.setObjectName("menu_button")
        self.nav_buttons.append(projects_btn)
        topbar_layout.addWidget(projects_btn)

        # Add-on button (single)
        add_on_btn = QPushButton("Add-on")
        add_on_btn.setIcon(QIcon(self.resource_path('icons/add_on.png')))
        add_on_btn.clicked.connect(lambda: self.add_on_page())
        self.nav_buttons.append(add_on_btn)
        topbar_layout.addWidget(add_on_btn)

        topbar_layout.addStretch(1)

        # User section - Right side
        user_container = QHBoxLayout()
        user_container.setSpacing(10)

        # User avatar
        user_avatar = QLabel()
        user_avatar.setPixmap(QIcon(self.resource_path('icons/user.png')).pixmap(35, 35))
        user_avatar.setStyleSheet("border-radius: 17px; border: 2px solid #3498db;")

        # User info
        user_info = QVBoxLayout()
        user_info.setSpacing(0)

        self.user_name = QLabel("Guest")
        self.user_name.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
        """)

        self.user_role = QLabel("Not logged in")
        self.user_role.setStyleSheet("""
            font-size: 11px;
            color: #bdc3c7;
            font-style: italic;
        """)

        user_info.addWidget(self.user_name)
        user_info.addWidget(self.user_role)

        user_container.addWidget(user_avatar)
        user_container.addLayout(user_info)

        # Logout button
        logout_btn = QPushButton()
        logout_btn.setIcon(QIcon(self.resource_path('icons/logout.png')))
        logout_btn.setIconSize(QSize(20, 20))
        logout_btn.setToolTip("Logout")
        logout_btn.setFixedSize(35, 35)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(231, 76, 60, 0.2);
                border-radius: 17px;
            }
            QPushButton:hover {
                background-color: rgba(231, 76, 60, 0.8);
            }
        """)
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

        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)

        title = QLabel("Management Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")

        self.date_picker = QDateEdit(QDate.currentDate())
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setStyleSheet("""
            QDateEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        self.date_picker.dateChanged.connect(self.update_dashboard)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setIcon(QIcon(self.resource_path('icons/refresh.png')))
        refresh_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #3498db;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
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
        activities_widget.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)

        activities_layout = QVBoxLayout(activities_widget)

        self.activities_table = QTableWidget()
        self.activities_table.setColumnCount(4)
        self.activities_table.setHorizontalHeaderLabels(["Date", "Member", "Action", "Details"])
        self.activities_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: none;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """)
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
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")

        self.add_member_btn = QPushButton("Add Member")
        self.add_member_btn.setIcon(QIcon(self.resource_path('icons/add_user.png')))
        self.add_member_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #27ae60;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #219653;
            }
        """)
        self.add_member_btn.clicked.connect(self.show_add_member_dialog)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.add_member_btn)

        # Filters
        filters = QWidget()
        filters_layout = QHBoxLayout(filters)

        self.team_search = QLineEdit()
        self.team_search.setPlaceholderText("Search a member...")
        self.team_search.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        self.team_search.textChanged.connect(self.filter_team_members)

        self.role_filter = QComboBox()
        self.role_filter.addItems(["All Roles", "Project Manager", "Developer", "Designer", "HR", "Marketing", "Finance"])
        self.role_filter.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        self.role_filter.currentIndexChanged.connect(self.filter_team_members)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Statuses", "Active", "Inactive", "On Leave"])
        self.status_filter.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        self.status_filter.currentIndexChanged.connect(self.filter_team_members)

        filters_layout.addWidget(self.team_search)
        filters_layout.addWidget(self.role_filter)
        filters_layout.addWidget(self.status_filter)

        # Team table
        self.team_table = QTableWidget()
        self.team_table.setColumnCount(8)
        self.team_table.setHorizontalHeaderLabels(["Name", "Role", "Department", "Performance", "Hire Date", "Status", "Tasks", "Actions"])
        self.team_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """)
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
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")

        self.add_project_btn = QPushButton("New Project")
        self.add_project_btn.setIcon(QIcon(self.resource_path('icons/add_project.png')))
        self.add_project_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #27ae60;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #219653;
            }
        """)
        self.add_project_btn.clicked.connect(self.show_add_project_dialog)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.add_project_btn)

        # Filters
        filters = QWidget()
        filters_layout = QHBoxLayout(filters)

        self.project_search = QLineEdit()
        self.project_search.setPlaceholderText("Search a project...")
        self.project_search.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        self.project_search.textChanged.connect(self.filter_projects)

        self.status_filter_proj = QComboBox()
        self.status_filter_proj.addItems(["All Statuses", "Planning", "In Progress", "Late", "Completed", "Archived"])
        self.status_filter_proj.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        self.status_filter_proj.currentIndexChanged.connect(self.filter_projects)

        self.priority_filter = QComboBox()
        self.priority_filter.addItems(["All Priorities", "High", "Medium", "Low"])
        self.priority_filter.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        self.priority_filter.currentIndexChanged.connect(self.filter_projects)

        filters_layout.addWidget(self.project_search)
        filters_layout.addWidget(self.status_filter_proj)
        filters_layout.addWidget(self.priority_filter)

        # Projects table
        self.projects_table = QTableWidget()
        self.projects_table.setColumnCount(8)
        self.projects_table.setHorizontalHeaderLabels(["Name", "Status", "Progress", "Priority", "Deadline", "Budget", "Manager", "Actions"])
        self.projects_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """)
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
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")

        self.add_task_btn = QPushButton("New Task")
        self.add_task_btn.setIcon(QIcon(self.resource_path('icons/add_task.png')))
        self.add_task_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #27ae60;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #219653;
            }
        """)
        self.add_task_btn.clicked.connect(self.show_add_task_dialog)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.add_task_btn)

        # Filters
        filters = QWidget()
        filters_layout = QHBoxLayout(filters)

        self.task_search = QLineEdit()
        self.task_search.setPlaceholderText("Search a task...")
        self.task_search.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        self.task_search.textChanged.connect(self.filter_tasks)

        self.task_status_filter = QComboBox()
        self.task_status_filter.addItems(["All Statuses", "To Do", "In Progress", "In Review", "Completed"])
        self.task_status_filter.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        self.task_status_filter.currentIndexChanged.connect(self.filter_tasks)

        self.task_priority_filter = QComboBox()
        self.task_priority_filter.addItems(["All Priorities", "High", "Medium", "Low"])
        self.task_priority_filter.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        self.task_priority_filter.currentIndexChanged.connect(self.filter_tasks)

        self.task_project_filter = QComboBox()
        self.task_project_filter.addItem("All Projects")
        self.task_project_filter.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        self.task_project_filter.currentIndexChanged.connect(self.filter_tasks)

        filters_layout.addWidget(self.task_search)
        filters_layout.addWidget(self.task_status_filter)
        filters_layout.addWidget(self.task_priority_filter)
        filters_layout.addWidget(self.task_project_filter)

        # Tasks table
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(7)
        self.tasks_table.setHorizontalHeaderLabels(["Name", "Project", "Status", "Priority", "Assigned To", "Deadline", "Actions"])
        self.tasks_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """)
        self.tasks_table.verticalHeader().setVisible(False)
        self.tasks_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tasks_table.setSortingEnabled(True)
        self.tasks_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        layout.addWidget(header)
        layout.addWidget(filters)
        layout.addWidget(self.tasks_table)

        self.main_content.addWidget(page)

    def setup_reports_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Reports and Analytics")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")

        # Report options
        report_options = QWidget()
        options_layout = QHBoxLayout(report_options)

        self.report_type = QComboBox()
        self.report_type.addItems(["Team Performance", "Project Progress", "Workload", "Key Indicators", "Budget Analysis"])
        self.report_type.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)

        self.report_period = QComboBox()
        self.report_period.addItems(["Last 7 Days", "Last 30 Days", "Current Quarter", "Current Year", "Custom..."])
        self.report_period.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)

        generate_btn = QPushButton("Generate Report")
        generate_btn.setIcon(QIcon(self.resource_path('icons/generate_report.png')))
        generate_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #3498db;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        generate_btn.clicked.connect(self.generate_report)

        export_btn = QPushButton("Export PDF")
        export_btn.setIcon(QIcon(self.resource_path('icons/export_pdf.png')))
        export_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #e74c3c;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        export_btn.clicked.connect(self.export_report)

        options_layout.addWidget(QLabel("Type:"))
        options_layout.addWidget(self.report_type)
        options_layout.addWidget(QLabel("Period:"))
        options_layout.addWidget(self.report_period)
        options_layout.addWidget(generate_btn)
        options_layout.addWidget(export_btn)

        # Report area
        self.report_view = QTabWidget()
        self.report_view.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QTabBar::tab {
                padding: 8px 15px;
                background: #f1f1f1;
                border: 1px solid #ddd;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #3498db;
                color: white;
            }
        """)

        # Chart tab
        self.graph_tab = QWidget()
        self.graph_layout = QVBoxLayout(self.graph_tab)

        # Data tab
        self.data_tab = QWidget()
        self.data_layout = QVBoxLayout(self.data_tab)

        self.report_data_table = QTableWidget()
        self.report_data_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: none;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """)
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
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")

        # Tabs
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QTabBar::tab {
                padding: 8px 15px;
                background: #f1f1f1;
                border: 1px solid #ddd;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #3498db;
                color: white;
            }
        """)

        # Account tab
        account_tab = QWidget()
        account_layout = QFormLayout(account_tab)
        account_layout.setSpacing(15)

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
        save_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #3498db;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        save_btn.clicked.connect(self.save_account_settings)
        account_layout.addRow(save_btn)

        # Preferences tab
        pref_tab = QWidget()
        pref_layout = QFormLayout(pref_tab)
        pref_layout.setSpacing(15)

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
        save_pref_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #3498db;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        save_pref_btn.clicked.connect(self.save_preferences)
        pref_layout.addRow(save_pref_btn)

        # Team tab
        team_tab = QWidget()
        team_layout = QVBoxLayout(team_tab)

        self.access_table = QTableWidget()
        self.access_table.setColumnCount(4)
        self.access_table.setHorizontalHeaderLabels(["Name", "Role", "Access", "Actions"])
        self.access_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """)
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
        hashed_pwd = hashlib.sha256(password.encode()).hexdigest()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_pwd))
            user = cursor.fetchone()

            if user:
                self.current_user = {
                    'id': user[0],
                    'username': user[1],
                    'full_name': user[3],
                    'email': user[4],
                    'role': user[5]
                }

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
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            user_id = self.current_user['id'] if self.current_user else None
            cursor.execute('''
                INSERT INTO activities (user_id, action, details)
                VALUES (?, ?, ?)
            ''', (user_id, action, details))
            conn.commit()

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

        # Load KPIs from database
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, value, target, trend, unit FROM kpis")
            kpis = cursor.fetchall()

            for name, value, target, trend, unit in kpis:
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

                title = QLabel(name.capitalize())
                title.setObjectName("kpi_title")

                value_label = QLabel(f"{value}{unit}")
                value_label.setObjectName("kpi_value")

                target_label = QLabel(f"Target: {target}{unit}")

                trend_icon = QLabel()
                if trend == "up":
                    trend_icon.setPixmap(QIcon(self.resource_path('icons/trend_up.png')).pixmap(16, 16))
                elif trend == "down":
                    trend_icon.setPixmap(QIcon(self.resource_path('icons/trend_down.png')).pixmap(16, 16))
                else:
                    trend_icon.setPixmap(QIcon(self.resource_path('icons/trend_flat.png')).pixmap(16, 16))

                trend_layout = QHBoxLayout()
                trend_layout.addWidget(QLabel("Trend:"))
                trend_layout.addWidget(trend_icon)
                trend_layout.addStretch()

                frame_layout.addWidget(title)
                frame_layout.addWidget(value_label)
                frame_layout.addWidget(target_label)
                frame_layout.addLayout(trend_layout)

                self.kpi_layout.addWidget(frame)

            # If no KPIs, create examples
            if not kpis:
                example_kpis = [
                    ("Productivity", 78, 85, "up", "%"),
                    ("Quality", 92, 90, "stable", "%"),
                    ("Efficiency", 81, 80, "up", "%"),
                    ("Satisfaction", 88, 85, "down", "%")
                ]

                for name, value, target, trend, unit in example_kpis:
                    cursor.execute('''
                        INSERT INTO kpis (name, value, target, trend, unit)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (name, value, target, trend, unit))

                conn.commit()
                # Reload KPIs
                self.load_kpis()

    def load_team_members(self):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, role, department, performance, hire_date, status FROM team_members WHERE status != 'deleted'")
            members = cursor.fetchall()

            self.team_table.setRowCount(len(members))

            for row, (id, name, role, department, performance, hire_date, status) in enumerate(members):
                self.team_table.setItem(row, 0, QTableWidgetItem(name))
                self.team_table.setItem(row, 1, QTableWidgetItem(role))
                self.team_table.setItem(row, 2, QTableWidgetItem(department))

                # Performance with color
                perf_item = QTableWidgetItem(f"{performance}%")
                if performance >= 90:
                    perf_item.setForeground(QColor('#27ae60'))
                elif performance >= 80:
                    perf_item.setForeground(QColor('#f39c12'))
                else:
                    perf_item.setForeground(QColor('#e74c3c'))
                self.team_table.setItem(row, 3, perf_item)

                self.team_table.setItem(row, 4, QTableWidgetItem(hire_date))

                # Status with icon
                status_item = QTableWidgetItem()
                if status == "active":
                    status_item.setIcon(QIcon(self.resource_path('icons/active.png')))
                    status_item.setText("Active")
                elif status == "inactive":
                    status_item.setIcon(QIcon(self.resource_path('icons/inactive.png')))
                    status_item.setText("Inactive")
                else:
                    status_item.setIcon(QIcon(self.resource_path('icons/leave.png')))
                    status_item.setText("On Leave")
                self.team_table.setItem(row, 5, status_item)

                # Number of tasks
                cursor.execute("SELECT COUNT(*) FROM tasks WHERE assignee_id=?", (id,))
                task_count = cursor.fetchone()[0]
                self.team_table.setItem(row, 6, QTableWidgetItem(str(task_count)))

                # Action buttons
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(0, 0, 0, 0)
                action_layout.setSpacing(5)

                edit_btn = QPushButton()
                edit_btn.setIcon(QIcon(self.resource_path('icons/edit.png')))
                edit_btn.setToolTip("Edit")
                edit_btn.setFixedSize(30, 30)
                edit_btn.setStyleSheet("background-color: transparent;")
                edit_btn.clicked.connect(lambda _, member_id=id: self.edit_member(member_id))

                delete_btn = QPushButton()
                delete_btn.setIcon(QIcon(self.resource_path('icons/delete.png')))
                delete_btn.setToolTip("Delete")
                delete_btn.setFixedSize(30, 30)
                delete_btn.setStyleSheet("background-color: transparent;")
                delete_btn.clicked.connect(lambda _, member_id=id: self.delete_member(member_id))

                action_layout.addWidget(edit_btn)
                action_layout.addWidget(delete_btn)

                self.team_table.setCellWidget(row, 7, action_widget)

            self.team_table.resizeColumnsToContents()

    def load_projects(self):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id, p.name, p.status, p.progress, p.priority, p.deadline, p.budget, t.name
                FROM projects p
                LEFT JOIN team_members t ON p.manager_id = t.id
                WHERE p.status != 'deleted'
            ''')
            projects = cursor.fetchall()

            self.projects_table.setRowCount(len(projects))

            for row, (id, name, status, progress, priority, deadline, budget, manager) in enumerate(projects):
                self.projects_table.setItem(row, 0, QTableWidgetItem(name))

                # Status with color
                status_item = QTableWidgetItem(status.capitalize())
                if status == "completed":
                    status_item.setForeground(QColor('#27ae60'))
                elif status == "late":
                    status_item.setForeground(QColor('#e74c3c'))
                elif status == "in_progress":
                    status_item.setForeground(QColor('#3498db'))
                self.projects_table.setItem(row, 1, status_item)

                # Progress bar
                progress_widget = QWidget()
                progress_layout = QHBoxLayout(progress_widget)
                progress_layout.setContentsMargins(5, 5, 5, 5)

                progress_bar = QProgressBar()
                progress_bar.setValue(progress)
                progress_bar.setAlignment(Qt.AlignCenter)
                progress_bar.setFormat(f"{progress}%")
                progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #bdc3c7;
                        border-radius: 5px;
                        text-align: center;
                        height: 20px;
                    }
                    QProgressBar::chunk {
                        background-color: #3498db;
                        border-radius: 4px;
                    }
                """)

                progress_layout.addWidget(progress_bar)
                self.projects_table.setCellWidget(row, 2, progress_widget)

                # Priority with icon
                priority_item = QTableWidgetItem()
                if priority == "high":
                    priority_item.setIcon(QIcon(self.resource_path('icons/priority_high.png')))
                    priority_item.setText("High")
                elif priority == "medium":
                    priority_item.setIcon(QIcon(self.resource_path('icons/priority_medium.png')))
                    priority_item.setText("Medium")
                else:
                    priority_item.setIcon(QIcon(self.resource_path('icons/priority_low.png')))
                    priority_item.setText("Low")
                self.projects_table.setItem(row, 3, priority_item)

                self.projects_table.setItem(row, 4, QTableWidgetItem(deadline))
                self.projects_table.setItem(row, 5, QTableWidgetItem(f"€{budget:,.2f}"))
                self.projects_table.setItem(row, 6, QTableWidgetItem(manager if manager else "Unassigned"))

                # Action buttons
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(0, 0, 0, 0)
                action_layout.setSpacing(5)

                details_btn = QPushButton()
                details_btn.setIcon(QIcon(self.resource_path('icons/details.png')))
                details_btn.setToolTip("Details")
                details_btn.setFixedSize(30, 30)
                details_btn.setStyleSheet("background-color: transparent;")
                details_btn.clicked.connect(lambda _, project_id=id: self.show_project_details(project_id))

                edit_btn = QPushButton()
                edit_btn.setIcon(QIcon(self.resource_path('icons/edit.png')))
                edit_btn.setToolTip("Edit")
                edit_btn.setFixedSize(30, 30)
                edit_btn.setStyleSheet("background-color: transparent;")
                edit_btn.clicked.connect(lambda _, project_id=id: self.edit_project(project_id))

                delete_btn = QPushButton()
                delete_btn.setIcon(QIcon(self.resource_path('icons/delete.png')))
                delete_btn.setToolTip("Delete")
                delete_btn.setFixedSize(30, 30)
                delete_btn.setStyleSheet("background-color: transparent;")
                delete_btn.clicked.connect(lambda _, project_id=id: self.delete_project(project_id))

                action_layout.addWidget(details_btn)
                action_layout.addWidget(edit_btn)
                action_layout.addWidget(delete_btn)

                self.projects_table.setCellWidget(row, 7, action_widget)

            self.projects_table.resizeColumnsToContents()

    def load_tasks(self):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.id, t.name, p.name, t.status, t.priority, m.name, t.deadline
                FROM tasks t
                LEFT JOIN projects p ON t.project_id = p.id
                LEFT JOIN team_members m ON t.assignee_id = m.id
                WHERE t.status != 'deleted'
            ''')
            tasks = cursor.fetchall()

            self.tasks_table.setRowCount(len(tasks))

            for row, (id, name, project, status, priority, assignee, deadline) in enumerate(tasks):
                self.tasks_table.setItem(row, 0, QTableWidgetItem(name))
                self.tasks_table.setItem(row, 1, QTableWidgetItem(project))

                # Status
                status_item = QTableWidgetItem()
                if status == "completed":
                    status_item.setText("Completed")
                    status_item.setForeground(QColor('#27ae60'))
                elif status == "in_progress":
                    status_item.setText("In Progress")
                    status_item.setForeground(QColor('#3498db'))
                elif status == "in_review":
                    status_item.setText("In Review")
                    status_item.setForeground(QColor('#f39c12'))
                else:
                    status_item.setText("To Do")
                self.tasks_table.setItem(row, 2, status_item)

                # Priority
                priority_item = QTableWidgetItem()
                if priority == "high":
                    priority_item.setIcon(QIcon(self.resource_path('icons/priority_high.png')))
                    priority_item.setText("High")
                elif priority == "medium":
                    priority_item.setIcon(QIcon(self.resource_path('icons/priority_medium.png')))
                    priority_item.setText("Medium")
                else:
                    priority_item.setIcon(QIcon(self.resource_path('icons/priority_low.png')))
                    priority_item.setText("Low")
                self.tasks_table.setItem(row, 3, priority_item)

                self.tasks_table.setItem(row, 4, QTableWidgetItem(assignee if assignee else "Unassigned"))
                self.tasks_table.setItem(row, 5, QTableWidgetItem(deadline if deadline else "-"))

                # Action buttons
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(0, 0, 0, 0)
                action_layout.setSpacing(5)

                complete_btn = QPushButton()
                complete_btn.setIcon(QIcon(self.resource_path('icons/complete.png')))
                complete_btn.setToolTip("Mark as Completed")
                complete_btn.setFixedSize(30, 30)
                complete_btn.setStyleSheet("background-color: transparent;")
                complete_btn.clicked.connect(lambda _, task_id=id: self.complete_task(task_id))

                edit_btn = QPushButton()
                edit_btn.setIcon(QIcon(self.resource_path('icons/edit.png')))
                edit_btn.setToolTip("Edit")
                edit_btn.setFixedSize(30, 30)
                edit_btn.setStyleSheet("background-color: transparent;")
                edit_btn.clicked.connect(lambda _, task_id=id: self.edit_task(task_id))

                delete_btn = QPushButton()
                delete_btn.setIcon(QIcon(self.resource_path('icons/delete.png')))
                delete_btn.setToolTip("Delete")
                delete_btn.setFixedSize(30, 30)
                delete_btn.setStyleSheet("background-color: transparent;")
                delete_btn.clicked.connect(lambda _, task_id=id: self.delete_task(task_id))

                action_layout.addWidget(complete_btn)
                action_layout.addWidget(edit_btn)
                action_layout.addWidget(delete_btn)

                self.tasks_table.setCellWidget(row, 6, action_widget)

            self.tasks_table.resizeColumnsToContents()

    def load_activities(self):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.timestamp, u.full_name, a.action, a.details
                FROM activities a
                LEFT JOIN users u ON a.user_id = u.id
                ORDER BY a.timestamp DESC
                LIMIT 50
            ''')
            activities = cursor.fetchall()

            self.activities_table.setRowCount(len(activities))

            for row, (timestamp, user, action, details) in enumerate(activities):
                self.activities_table.setItem(row, 0, QTableWidgetItem(timestamp))
                self.activities_table.setItem(row, 1, QTableWidgetItem(user if user else "System"))
                self.activities_table.setItem(row, 2, QTableWidgetItem(action))
                self.activities_table.setItem(row, 3, QTableWidgetItem(details if details else ""))

            self.activities_table.resizeColumnsToContents()

    def load_access_table(self):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, full_name, role FROM users")
            users = cursor.fetchall()

            self.access_table.setRowCount(len(users))

            for row, (id, username, full_name, role) in enumerate(users):
                self.access_table.setItem(row, 0, QTableWidgetItem(full_name))
                self.access_table.setItem(row, 1, QTableWidgetItem(role.capitalize()))

                # Access level
                access_item = QTableWidgetItem()
                if role == "admin":
                    access_item.setText("Administrator")
                    access_item.setForeground(QColor('#e74c3c'))
                elif role == "manager":
                    access_item.setText("Manager")
                    access_item.setForeground(QColor('#3498db'))
                else:
                    access_item.setText("User")
                self.access_table.setItem(row, 2, access_item)

                # Action buttons
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(0, 0, 0, 0)
                action_layout.setSpacing(5)

                edit_btn = QPushButton()
                edit_btn.setIcon(QIcon(self.resource_path('icons/edit.png')))
                edit_btn.setToolTip("Edit")
                edit_btn.setFixedSize(30, 30)
                edit_btn.setStyleSheet("background-color: transparent;")
                edit_btn.clicked.connect(lambda _, user_id=id: self.edit_user_access(user_id))

                action_layout.addWidget(edit_btn)
                self.access_table.setCellWidget(row, 3, action_widget)

            self.access_table.resizeColumnsToContents()

    def load_user_preferences(self):
        # Load user preferences from database
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT full_name, email, phone FROM users WHERE id=?", (self.current_user['id'],))
            user_data = cursor.fetchone()

            if user_data:
                self.name_edit.setText(user_data[0])
                self.email_edit.setText(user_data[1])
                self.phone_edit.setText(user_data[2] if user_data[2] else "")

    def update_project_filter(self):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM projects WHERE status != 'deleted'")
            projects = cursor.fetchall()

            self.task_project_filter.clear()
            self.task_project_filter.addItem("All Projects")

            for id, name in projects:
                self.task_project_filter.addItem(name, id)

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

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, performance FROM team_members WHERE status='active' ORDER BY performance DESC")
            members = cursor.fetchall()

            names = [m[0] for m in members]
            performance = [m[1] for m in members]

            bg = pg.BarGraphItem(x=range(len(names)), height=performance, width=0.6, brush='#3498db')
            self.performance_graph.addItem(bg)

            self.performance_graph.getAxis('bottom').setTicks([[(i, name) for i, name in enumerate(names)]])
            self.performance_graph.setYRange(0, 100)
            self.performance_graph.setLabel('left', 'Performance (%)')
            self.performance_graph.setTitle("Team Performance")

        # Project progress
        self.project_progress_graph.clear()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, progress FROM projects WHERE status NOT IN ('completed', 'deleted', 'archived') ORDER BY progress DESC")
            projects = cursor.fetchall()

            names = [p[0] for p in projects]
            progress = [p[1] for p in projects]

            bg = pg.BarGraphItem(x=range(len(names)), height=progress, width=0.6, brush='#2ecc71')
            self.project_progress_graph.addItem(bg)

            self.project_progress_graph.getAxis('bottom').setTicks([[(i, name) for i, name in enumerate(names)]])
            self.project_progress_graph.setYRange(0, 100)
            self.project_progress_graph.setLabel('left', 'Progress (%)')
            self.project_progress_graph.setTitle("Project Progress")

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

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, performance FROM team_members WHERE status='active' ORDER BY performance DESC")
            data = cursor.fetchall()

            names = [d[0] for d in data]
            performance = [d[1] for d in data]

            bars = ax.bar(names, performance, color='#3498db')
            ax.set_title("Team Performance")
            ax.set_ylabel("Performance (%)")
            ax.set_ylim(0, 100)

            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height}%', ha='center', va='bottom')

            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            self.graph_layout.addWidget(canvas)

            # Data
            self.report_data_table.setColumnCount(2)
            self.report_data_table.setHorizontalHeaderLabels(["Member", "Performance (%)"])
            self.report_data_table.setRowCount(len(data))

            for row, (name, perf) in enumerate(data):
                self.report_data_table.setItem(row, 0, QTableWidgetItem(name))
                self.report_data_table.setItem(row, 1, QTableWidgetItem(str(perf)))

            self.report_data_table.resizeColumnsToContents()

    def generate_project_progress_report(self, period):
        # Chart
        fig = plt.figure(figsize=(10, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, progress, status FROM projects WHERE status != 'deleted' ORDER BY progress DESC")
            data = cursor.fetchall()

            names = [d[0] for d in data]
            progress = [d[1] for d in data]
            statuses = [d[2] for d in data]

            colors = []
            for status in statuses:
                if status == "completed":
                    colors.append('#2ecc71')
                elif status == "late":
                    colors.append('#e74c3c')
                else:
                    colors.append('#3498db')

            bars = ax.bar(names, progress, color=colors)
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
            self.report_data_table.setRowCount(len(data))

            for row, (name, progress, status, _) in enumerate(data):
                self.report_data_table.setItem(row, 0, QTableWidgetItem(name))
                self.report_data_table.setItem(row, 1, QTableWidgetItem(str(progress)))

                status_item = QTableWidgetItem()
                if status == "completed":
                    status_item.setText("Completed")
                elif status == "late":
                    status_item.setText("Late")
                elif status == "in_progress":
                    status_item.setText("In Progress")
                else:
                    status_item.setText("Planning")

                self.report_data_table.setItem(row, 2, status_item)

                # Add budget (additional query)
                cursor.execute("SELECT budget FROM projects WHERE name=?", (name,))
                budget = cursor.fetchone()[0]
                self.report_data_table.setItem(row, 3, QTableWidgetItem(f"€{budget:,.2f}"))

            self.report_data_table.resizeColumnsToContents()

    def generate_workload_report(self, period):
        # Chart
        fig = plt.figure(figsize=(10, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.name, COUNT(t.id)
                FROM team_members m
                LEFT JOIN tasks t ON m.id = t.assignee_id AND t.status != 'completed' AND t.status != 'deleted'
                WHERE m.status = 'active'
                GROUP BY m.id
                ORDER BY COUNT(t.id) DESC
            ''')
            data = cursor.fetchall()

            names = [d[0] for d in data]
            task_counts = [d[1] for d in data]

            bars = ax.bar(names, task_counts, color='#9b59b6')
            ax.set_title("Workload by Member")
            ax.set_ylabel("Number of Tasks")

            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height}', ha='center', va='bottom')

            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            self.graph_layout.addWidget(canvas)

            # Data
            self.report_data_table.setColumnCount(3)
            self.report_data_table.setHorizontalHeaderLabels(["Member", "Ongoing Tasks", "Performance"])
            self.report_data_table.setRowCount(len(data))

            for row, (name, task_count) in enumerate(data):
                self.report_data_table.setItem(row, 0, QTableWidgetItem(name))
                self.report_data_table.setItem(row, 1, QTableWidgetItem(str(task_count)))

                # Add performance
                cursor.execute("SELECT performance FROM team_members WHERE name=?", (name,))
                perf = cursor.fetchone()[0]
                perf_item = QTableWidgetItem(f"{perf}%")

                if perf >= 90:
                    perf_item.setForeground(QColor('#27ae60'))
                elif perf >= 80:
                    perf_item.setForeground(QColor('#f39c12'))
                else:
                    perf_item.setForeground(QColor('#e74c3c'))

                self.report_data_table.setItem(row, 2, perf_item)

            self.report_data_table.resizeColumnsToContents()

    def generate_kpi_report(self, period):
        # Chart
        fig = plt.figure(figsize=(10, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, value, target FROM kpis")
            data = cursor.fetchall()

            names = [d[0] for d in data]
            values = [d[1] for d in data]
            targets = [d[2] for d in data]

            x = range(len(names))
            width = 0.35

            bars1 = ax.bar(x, values, width, label='Current Value', color='#3498db')
            bars2 = ax.bar([p + width for p in x], targets, width, label='Target', color='#e74c3c')

            ax.set_title("Key Performance Indicators")
            ax.set_ylabel("Value")
            ax.set_xticks([p + width/2 for p in x])
            ax.set_xticklabels(names)
            ax.legend()

            for bar in bars1:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height}', ha='center', va='bottom')

            for bar in bars2:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height}', ha='center', va='bottom')

            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            self.graph_layout.addWidget(canvas)

            # Data
            self.report_data_table.setColumnCount(4)
            self.report_data_table.setHorizontalHeaderLabels(["KPI", "Value", "Target", "Difference"])
            self.report_data_table.setRowCount(len(data))

            for row, (name, value, target) in enumerate(data):
                self.report_data_table.setItem(row, 0, QTableWidgetItem(name.capitalize()))
                self.report_data_table.setItem(row, 1, QTableWidgetItem(str(value)))
                self.report_data_table.setItem(row, 2, QTableWidgetItem(str(target)))

                diff = value - target
                diff_item = QTableWidgetItem(f"{diff:+}")

                if diff >= 0:
                    diff_item.setForeground(QColor('#27ae60'))
                else:
                    diff_item.setForeground(QColor('#e74c3c'))

                self.report_data_table.setItem(row, 3, diff_item)

            self.report_data_table.resizeColumnsToContents()

    def generate_budget_report(self, period):
        # Chart
        fig = plt.figure(figsize=(10, 5))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, budget FROM projects WHERE status != 'deleted' ORDER BY budget DESC")
            data = cursor.fetchall()

            names = [d[0] for d in data]
            budgets = [d[1] for d in data]

            bars = ax.bar(names, budgets, color='#f39c12')
            ax.set_title("Budget Distribution by Project")
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
            self.report_data_table.setRowCount(len(data))

            for row, (name, budget) in enumerate(data):
                self.report_data_table.setItem(row, 0, QTableWidgetItem(name))
                self.report_data_table.setItem(row, 1, QTableWidgetItem(f"€{budget:,.2f}"))

                # Add status
                cursor.execute("SELECT status FROM projects WHERE name=?", (name,))
                status = cursor.fetchone()[0]

                status_item = QTableWidgetItem()
                if status == "completed":
                    status_item.setText("Completed")
                elif status == "late":
                    status_item.setText("Late")
                elif status == "in_progress":
                    status_item.setText("In Progress")
                else:
                    status_item.setText("Planning")

                self.report_data_table.setItem(row, 2, status_item)

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
        role_combo = QComboBox()
        role_combo.addItems(["Project Manager", "Developer", "Designer", "HR", "Marketing", "Finance"])

        department_combo = QComboBox()
        department_combo.addItems(["IT", "HR", "Marketing", "Finance", "Management"])

        performance_spin = QSpinBox()
        performance_spin.setRange(0, 100)
        performance_spin.setValue(80)

        hire_date = QDateEdit(QDate.currentDate())
        hire_date.setCalendarPopup(True)

        status_combo = QComboBox()
        status_combo.addItems(["Active", "Inactive", "On Leave"])

        skills_edit = QLineEdit()
        skills_edit.setPlaceholderText("Skills separated by commas")

        notes_edit = QTextEdit()
        notes_edit.setPlaceholderText("Additional notes...")

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        layout.addRow("Full Name:", name_edit)
        layout.addRow("Role:", role_combo)
        layout.addRow("Department:", department_combo)
        layout.addRow("Initial Performance (%):", performance_spin)
        layout.addRow("Hire Date:", hire_date)
        layout.addRow("Status:", status_combo)
        layout.addRow("Skills:", skills_edit)
        layout.addRow("Notes:", notes_edit)
        layout.addRow(button_box)

        if dialog.exec_() == QDialog.Accepted:
            name = name_edit.text()
            role = role_combo.currentText()
            department = department_combo.currentText()
            performance = performance_spin.value()
            hire_date_str = hire_date.date().toString("yyyy-MM-dd")
            status = status_combo.currentText().lower().replace(" ", "_")
            skills = skills_edit.text()
            notes = notes_edit.toPlainText()

            if name:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO team_members (name, role, department, performance, hire_date, status, skills, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (name, role, department, performance, hire_date_str, status, skills, notes))
                    conn.commit()

                self.load_team_members()
                self.log_activity(f"Added team member: {name}")
                self.statusBar().showMessage(f"Team member {name} added successfully", 3000)
            else:
                QMessageBox.warning(self, "Error", "Member name is required")

    def edit_member(self, member_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, role, department, performance, hire_date, status, skills, notes FROM team_members WHERE id=?", (member_id,))
            member = cursor.fetchone()

            if member:
                dialog = QDialog(self)
                dialog.setWindowTitle("Edit Team Member")
                dialog.setFixedSize(400, 500)

                layout = QFormLayout(dialog)

                name_edit = QLineEdit(member[0])
                role_combo = QComboBox()
                role_combo.addItems(["Project Manager", "Developer", "Designer", "HR", "Marketing", "Finance"])
                role_combo.setCurrentText(member[1])

                department_combo = QComboBox()
                department_combo.addItems(["IT", "HR", "Marketing", "Finance", "Management"])
                department_combo.setCurrentText(member[2])

                performance_spin = QSpinBox()
                performance_spin.setRange(0, 100)
                performance_spin.setValue(member[3])

                hire_date = QDateEdit(QDate.fromString(member[4], "yyyy-MM-dd"))
                hire_date.setCalendarPopup(True)

                status_combo = QComboBox()
                status_combo.addItems(["Active", "Inactive", "On Leave"])
                status_map = {"active": "Active", "inactive": "Inactive", "on_leave": "On Leave"}
                status_combo.setCurrentText(status_map.get(member[5], "Active"))

                skills_edit = QLineEdit(member[6] if member[6] else "")
                skills_edit.setPlaceholderText("Skills separated by commas")

                notes_edit = QTextEdit(member[7] if member[7] else "")
                notes_edit.setPlaceholderText("Additional notes...")

                button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                button_box.accepted.connect(dialog.accept)
                button_box.rejected.connect(dialog.reject)

                layout.addRow("Full Name:", name_edit)
                layout.addRow("Role:", role_combo)
                layout.addRow("Department:", department_combo)
                layout.addRow("Performance (%):", performance_spin)
                layout.addRow("Hire Date:", hire_date)
                layout.addRow("Status:", status_combo)
                layout.addRow("Skills:", skills_edit)
                layout.addRow("Notes:", notes_edit)
                layout.addRow(button_box)

                if dialog.exec_() == QDialog.Accepted:
                    name = name_edit.text()
                    role = role_combo.currentText()
                    department = department_combo.currentText()
                    performance = performance_spin.value()
                    hire_date_str = hire_date.date().toString("yyyy-MM-dd")
                    status = status_combo.currentText().lower().replace(" ", "_")
                    skills = skills_edit.text()
                    notes = notes_edit.toPlainText()

                    if name:
                        cursor.execute('''
                            UPDATE team_members
                            SET name=?, role=?, department=?, performance=?, hire_date=?, status=?, skills=?, notes=?
                            WHERE id=?
                        ''', (name, role, department, performance, hire_date_str, status, skills, notes, member_id))
                        conn.commit()

                        self.load_team_members()
                        self.log_activity(f"Updated team member: {name}")
                        self.statusBar().showMessage(f"Team member {name} updated successfully", 3000)
                    else:
                        QMessageBox.warning(self, "Error", "Member name is required")

    def delete_member(self, member_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM team_members WHERE id=?", (member_id,))
            member_name = cursor.fetchone()[0]

            reply = QMessageBox.question(
                self,
                "Confirmation",
                f"Are you sure you want to delete the member {member_name}?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Mark as deleted rather than actually deleting
                cursor.execute("UPDATE team_members SET status='deleted' WHERE id=?", (member_id,))
                conn.commit()

                self.load_team_members()
                self.log_activity(f"Deleted team member: {member_name}")
                self.statusBar().showMessage(f"Team member {member_name} deleted", 3000)

    def show_add_project_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("New Project")
        dialog.setFixedSize(500, 500)

        layout = QFormLayout(dialog)

        name_edit = QLineEdit()
        desc_edit = QTextEdit()
        desc_edit.setPlaceholderText("Project description, including notes on key documents or links...")
        desc_edit.setMinimumHeight(100)

        start_date = QDateEdit(QDate.currentDate())
        start_date.setCalendarPopup(True)

        deadline = QDateEdit(QDate.currentDate().addMonths(1))
        deadline.setCalendarPopup(True)

        budget_spin = QDoubleSpinBox()
        budget_spin.setRange(0, 1000000)
        budget_spin.setPrefix("€ ")
        budget_spin.setValue(10000)

        status_combo = QComboBox()
        status_combo.addItems(["Planning", "In Progress", "Late", "Completed", "Archived"])

        priority_combo = QComboBox()
        priority_combo.addItems(["High", "Medium", "Low"])

        manager_combo = QComboBox()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM team_members WHERE status='active'")
            managers = cursor.fetchall()

            for id, name in managers:
                manager_combo.addItem(name, id)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        layout.addRow("Project Name:", name_edit)
        layout.addRow("Description:", desc_edit)
        layout.addRow("Start Date:", start_date)
        layout.addRow("Deadline:", deadline)
        layout.addRow("Budget:", budget_spin)
        layout.addRow("Status:", status_combo)
        layout.addRow("Priority:", priority_combo)
        layout.addRow("Manager:", manager_combo)
        layout.addRow(button_box)

        if dialog.exec_() == QDialog.Accepted:
            name = name_edit.text()
            description = desc_edit.toPlainText()
            start_date_str = start_date.date().toString("yyyy-MM-dd")
            deadline_str = deadline.date().toString("yyyy-MM-dd")
            budget = budget_spin.value()
            status = status_combo.currentText().lower().replace(" ", "_")
            priority = priority_combo.currentText().lower()
            manager_id = manager_combo.currentData()

            if name:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO projects (name, description, start_date, deadline, budget, status, priority, manager_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (name, description, start_date_str, deadline_str, budget, status, priority, manager_id))
                    conn.commit()

                self.load_projects()
                self.update_project_filter()
                self.log_activity(f"Added project: {name}")
                self.statusBar().showMessage(f"Project {name} added successfully", 3000)
            else:
                QMessageBox.warning(self, "Error", "Project name is required")

    def edit_project(self, project_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.name, p.description, p.start_date, p.deadline, p.budget, p.status, p.priority, p.manager_id, t.name
                FROM projects p
                LEFT JOIN team_members t ON p.manager_id = t.id
                WHERE p.id=?
            ''', (project_id,))
            project = cursor.fetchone()

            if project:
                dialog = QDialog(self)
                dialog.setWindowTitle("Edit Project")
                dialog.setFixedSize(500, 500)

                layout = QFormLayout(dialog)

                name_edit = QLineEdit(project[0])
                desc_edit = QTextEdit(project[1] if project[1] else "")
                desc_edit.setPlaceholderText("Project description, including notes on key documents or links...")
                desc_edit.setMinimumHeight(100)

                start_date = QDateEdit(QDate.fromString(project[2], "yyyy-MM-dd"))
                start_date.setCalendarPopup(True)

                deadline = QDateEdit(QDate.fromString(project[3], "yyyy-MM-dd"))
                deadline.setCalendarPopup(True)

                budget_spin = QDoubleSpinBox()
                budget_spin.setRange(0, 1000000)
                budget_spin.setPrefix("€ ")
                budget_spin.setValue(project[4])

                status_combo = QComboBox()
                status_combo.addItems(["Planning", "In Progress", "Late", "Completed", "Archived"])
                status_map = {
                    "planning": "Planning",
                    "in_progress": "In Progress",
                    "late": "Late",
                    "completed": "Completed",
                    "archived": "Archived"
                }
                status_combo.setCurrentText(status_map.get(project[5], "Planning"))

                priority_combo = QComboBox()
                priority_combo.addItems(["High", "Medium", "Low"])
                priority_map = {
                    "high": "High",
                    "medium": "Medium",
                    "low": "Low"
                }
                priority_combo.setCurrentText(priority_map.get(project[6], "Medium"))

                manager_combo = QComboBox()
                cursor.execute("SELECT id, name FROM team_members WHERE status='active'")
                managers = cursor.fetchall()

                current_manager_index = 0
                for idx, (id, name) in enumerate(managers):
                    manager_combo.addItem(name, id)
                    if id == project[7]:
                        current_manager_index = idx

                manager_combo.setCurrentIndex(current_manager_index)

                button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                button_box.accepted.connect(dialog.accept)
                button_box.rejected.connect(dialog.reject)

                layout.addRow("Project Name:", name_edit)
                layout.addRow("Description:", desc_edit)
                layout.addRow("Start Date:", start_date)
                layout.addRow("Deadline:", deadline)
                layout.addRow("Budget:", budget_spin)
                layout.addRow("Status:", status_combo)
                layout.addRow("Priority:", priority_combo)
                layout.addRow("Manager:", manager_combo)
                layout.addRow(button_box)

                if dialog.exec_() == QDialog.Accepted:
                    name = name_edit.text()
                    description = desc_edit.toPlainText()
                    start_date_str = start_date.date().toString("yyyy-MM-dd")
                    deadline_str = deadline.date().toString("yyyy-MM-dd")
                    budget = budget_spin.value()
                    status = status_combo.currentText().lower().replace(" ", "_")
                    priority = priority_combo.currentText().lower()
                    manager_id = manager_combo.currentData()

                    if name:
                        cursor.execute('''
                            UPDATE projects
                            SET name=?, description=?, start_date=?, deadline=?, budget=?, status=?, priority=?, manager_id=?
                            WHERE id=?
                        ''', (name, description, start_date_str, deadline_str, budget, status, priority, manager_id, project_id))
                        conn.commit()

                        self.load_projects()
                        self.update_project_filter()
                        self.log_activity(f"Updated project: {name}")
                        self.statusBar().showMessage(f"Project {name} updated successfully", 3000)
                    else:
                        QMessageBox.warning(self, "Error", "Project name is required")

    def show_project_details(self, project_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.name, p.description, p.start_date, p.deadline, p.budget, p.status, p.priority, p.progress,
                       t.name, p.manager_id
                FROM projects p
                LEFT JOIN team_members t ON p.manager_id = t.id
                WHERE p.id=?
            ''', (project_id,))
            project = cursor.fetchone()

            if project:
                dialog = QDialog(self)
                dialog.setWindowTitle(f"Project Details: {project[0]}")
                dialog.setFixedSize(600, 500)

                layout = QVBoxLayout(dialog)

                # Basic information
                info_group = QGroupBox("Project Information")
                info_layout = QFormLayout(info_group)

                name_label = QLabel(project[0])
                name_label.setStyleSheet("font-size: 16px; font-weight: bold;")

                desc_label = QLabel(project[1] if project[1] else "No description")
                desc_label.setWordWrap(True)

                start_date = QLabel(project[2])
                deadline = QLabel(project[3])
                budget = QLabel(f"€{project[4]:,.2f}")

                status = QLabel()
                status_map = {
                    "planning": ("Planning", "#3498db"),
                    "in_progress": ("In Progress", "#2ecc71"),
                    "late": ("Late", "#e74c3c"),
                    "completed": ("Completed", "#9b59b6")
                }
                status_text, status_color = status_map.get(project[5], ("Unknown", "#000000"))
                status.setText(status_text)
                status.setStyleSheet(f"color: {status_color}; font-weight: bold;")

                priority = QLabel()
                priority_map = {
                    "high": ("High", "#e74c3c"),
                    "medium": ("Medium", "#f39c12"),
                    "low": ("Low", "#2ecc71")
                }
                priority_text, priority_color = priority_map.get(project[6], ("Unknown", "#000000"))
                priority.setText(priority_text)
                priority.setStyleSheet(f"color: {priority_color}; font-weight: bold;")

                progress = QLabel(f"{project[7]}%")

                manager = QLabel(project[8] if project[8] else "Unassigned")

                info_layout.addRow("Name:", name_label)
                info_layout.addRow("Description:", desc_label)
                info_layout.addRow("Start Date:", start_date)
                info_layout.addRow("Deadline:", deadline)
                info_layout.addRow("Budget:", budget)
                info_layout.addRow("Status:", status)
                info_layout.addRow("Priority:", priority)
                info_layout.addRow("Progress:", progress)
                info_layout.addRow("Manager:", manager)

                # Project tasks
                tasks_group = QGroupBox("Associated Tasks")
                tasks_layout = QVBoxLayout(tasks_group)

                tasks_table = QTableWidget()
                tasks_table.setColumnCount(5)
                tasks_table.setHorizontalHeaderLabels(["Name", "Status", "Priority", "Assigned To", "Deadline"])
                tasks_table.setEditTriggers(QTableWidget.NoEditTriggers)
                tasks_table.verticalHeader().setVisible(False)

                cursor.execute('''
                    SELECT t.name, t.status, t.priority, m.name, t.deadline
                    FROM tasks t
                    LEFT JOIN team_members m ON t.assignee_id = m.id
                    WHERE t.project_id=? AND t.status != 'deleted'
                ''', (project_id,))
                tasks = cursor.fetchall()

                tasks_table.setRowCount(len(tasks))

                for row, (name, status, priority, assignee, deadline) in enumerate(tasks):
                    tasks_table.setItem(row, 0, QTableWidgetItem(name))

                    # Status
                    status_item = QTableWidgetItem()
                    if status == "completed":
                        status_item.setText("Completed")
                        status_item.setForeground(QColor('#2ecc71'))
                    elif status == "in_progress":
                        status_item.setText("In Progress")
                        status_item.setForeground(QColor('#3498db'))
                    elif status == "in_review":
                        status_item.setText("In Review")
                        status_item.setForeground(QColor('#f39c12'))
                    else:
                        status_item.setText("To Do")
                    tasks_table.setItem(row, 1, status_item)

                    # Priority
                    priority_item = QTableWidgetItem()
                    if priority == "high":
                        priority_item.setText("High")
                        priority_item.setForeground(QColor('#e74c3c'))
                    elif priority == "medium":
                        priority_item.setText("Medium")
                        priority_item.setForeground(QColor('#f39c12'))
                    else:
                        priority_item.setText("Low")
                        priority_item.setForeground(QColor('#2ecc71'))
                    tasks_table.setItem(row, 2, priority_item)

                    tasks_table.setItem(row, 3, QTableWidgetItem(assignee if assignee else "Unassigned"))
                    tasks_table.setItem(row, 4, QTableWidgetItem(deadline if deadline else "-"))

                tasks_table.resizeColumnsToContents()
                tasks_layout.addWidget(tasks_table)

                # Buttons
                button_box = QDialogButtonBox(QDialogButtonBox.Close)
                button_box.rejected.connect(dialog.reject)

                layout.addWidget(info_group)
                layout.addWidget(tasks_group)
                layout.addWidget(button_box)

                dialog.exec_()

    def delete_project(self, project_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM projects WHERE id=?", (project_id,))
            project_name = cursor.fetchone()[0]

            reply = QMessageBox.question(
                self,
                "Confirmation",
                f"Are you sure you want to delete the project {project_name}?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Mark as deleted rather than actually deleting
                cursor.execute("UPDATE projects SET status='deleted' WHERE id=?", (project_id,))
                conn.commit()

                self.load_projects()
                self.update_project_filter()
                self.log_activity(f"Deleted project: {project_name}")
                self.statusBar().showMessage(f"Project {project_name} deleted", 3000)

    def show_add_task_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("New Task")
        dialog.setFixedSize(400, 400)

        layout = QFormLayout(dialog)

        name_edit = QLineEdit()

        project_combo = QComboBox()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM projects WHERE status != 'completed' AND status != 'deleted'")
            projects = cursor.fetchall()

            for id, name in projects:
                project_combo.addItem(name, id)

        desc_edit = QTextEdit()
        desc_edit.setPlaceholderText("Task description...")

        status_combo = QComboBox()
        status_combo.addItems(["To Do", "In Progress", "In Review"])

        priority_combo = QComboBox()
        priority_combo.addItems(["High", "Medium", "Low"])

        assignee_combo = QComboBox()
        assignee_combo.addItem("Unassigned", None)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM team_members WHERE status='active'")
            members = cursor.fetchall()

            for id, name in members:
                assignee_combo.addItem(name, id)

        deadline_edit = QDateEdit(QDate.currentDate().addDays(7))
        deadline_edit.setCalendarPopup(True)

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
            name = name_edit.text()
            project_id = project_combo.currentData()
            description = desc_edit.toPlainText()
            status = status_combo.currentText().lower().replace(" ", "_")
            priority = priority_combo.currentText().lower()
            assignee_id = assignee_combo.currentData()
            deadline = deadline_edit.date().toString("yyyy-MM-dd")

            if name and project_id:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO tasks (project_id, name, description, status, priority, assignee_id, deadline)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (project_id, name, description, status, priority, assignee_id, deadline))
                    conn.commit()

                self.load_tasks()
                self.log_activity(f"Added task: {name}")
                self.statusBar().showMessage(f"Task {name} added successfully", 3000)
            else:
                QMessageBox.warning(self, "Error", "Task name and project are required")

    def edit_task(self, task_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.name, t.project_id, p.name, t.description, t.status, t.priority,
                       t.assignee_id, m.name, t.deadline
                FROM tasks t
                LEFT JOIN projects p ON t.project_id = p.id
                LEFT JOIN team_members m ON t.assignee_id = m.id
                WHERE t.id=?
            ''', (task_id,))
            task = cursor.fetchone()

            if task:
                dialog = QDialog(self)
                dialog.setWindowTitle("Edit Task")
                dialog.setFixedSize(400, 400)

                layout = QFormLayout(dialog)

                name_edit = QLineEdit(task[0])

                project_combo = QComboBox()
                cursor.execute("SELECT id, name FROM projects WHERE status != 'completed' AND status != 'deleted'")
                projects = cursor.fetchall()

                current_project_index = 0
                for idx, (id, name) in enumerate(projects):
                    project_combo.addItem(name, id)
                    if id == task[1]:
                        current_project_index = idx

                project_combo.setCurrentIndex(current_project_index)

                desc_edit = QTextEdit(task[3] if task[3] else "")
                desc_edit.setPlaceholderText("Task description...")

                status_combo = QComboBox()
                status_combo.addItems(["To Do", "In Progress", "In Review", "Completed"])
                status_map = {
                    "todo": "To Do",
                    "in_progress": "In Progress",
                    "in_review": "In Review",
                    "completed": "Completed"
                }
                status_combo.setCurrentText(status_map.get(task[4], "To Do"))

                priority_combo = QComboBox()
                priority_combo.addItems(["High", "Medium", "Low"])
                priority_map = {
                    "high": "High",
                    "medium": "Medium",
                    "low": "Low"
                }
                priority_combo.setCurrentText(priority_map.get(task[5], "Medium"))

                assignee_combo = QComboBox()
                assignee_combo.addItem("Unassigned", None)
                cursor.execute("SELECT id, name FROM team_members WHERE status='active'")
                members = cursor.fetchall()

                current_assignee_index = 0
                for idx, (id, name) in enumerate(members):
                    assignee_combo.addItem(name, id)
                    if id == task[6]:
                        current_assignee_index = idx + 1  # +1 for "Unassigned"

                assignee_combo.setCurrentIndex(current_assignee_index)

                deadline_edit = QDateEdit(QDate.fromString(task[8], "yyyy-MM-dd") if task[8] else QDate.currentDate())
                deadline_edit.setCalendarPopup(True)

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
                    name = name_edit.text()
                    project_id = project_combo.currentData()
                    description = desc_edit.toPlainText()
                    status = status_combo.currentText().lower().replace(" ", "_")
                    priority = priority_combo.currentText().lower()
                    assignee_id = assignee_combo.currentData()
                    deadline = deadline_edit.date().toString("yyyy-MM-dd")

                    if name and project_id:
                        cursor.execute('''
                            UPDATE tasks
                            SET name=?, project_id=?, description=?, status=?, priority=?, assignee_id=?, deadline=?
                            WHERE id=?
                        ''', (name, project_id, description, status, priority, assignee_id, deadline, task_id))
                        conn.commit()

                        self.load_tasks()
                        self.log_activity(f"Updated task: {name}")
                        self.statusBar().showMessage(f"Task {name} updated successfully", 3000)
                    else:
                        QMessageBox.warning(self, "Error", "Task name and project are required")

    def complete_task(self, task_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM tasks WHERE id=?", (task_id,))
            task_name = cursor.fetchone()[0]

            cursor.execute('''
                UPDATE tasks
                SET status='completed', completed_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (task_id,))
            conn.commit()

            self.load_tasks()
            self.log_activity(f"Task marked as completed: {task_name}")
            self.statusBar().showMessage(f"Task {task_name} marked as completed", 3000)

    def delete_task(self, task_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM tasks WHERE id=?", (task_id,))
            task_name = cursor.fetchone()[0]

            reply = QMessageBox.question(
                self,
                "Confirmation",
                f"Are you sure you want to delete the task {task_name}?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Mark as deleted rather than actually deleting
                cursor.execute("UPDATE tasks SET status='deleted' WHERE id=?", (task_id,))
                conn.commit()

                self.load_tasks()
                self.log_activity(f"Deleted task: {task_name}")
                self.statusBar().showMessage(f"Task {task_name} deleted", 3000)

    def edit_user_access(self, user_id):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, full_name, role FROM users WHERE id=?", (user_id,))
            user = cursor.fetchone()

            if user:
                dialog = QDialog(self)
                dialog.setWindowTitle(f"Edit Access for {user[1]}")
                dialog.setFixedSize(300, 200)

                layout = QFormLayout(dialog)

                username_label = QLabel(user[0])
                name_label = QLabel(user[1])

                role_combo = QComboBox()
                role_combo.addItems(["Administrator", "Manager", "User"])
                role_map = {
                    "admin": "Administrator",
                    "manager": "Manager",
                    "user": "User"
                }
                role_combo.setCurrentText(role_map.get(user[2], "User"))

                button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                button_box.accepted.connect(dialog.accept)
                button_box.rejected.connect(dialog.reject)

                layout.addRow("Username:", username_label)
                layout.addRow("Full Name:", name_label)
                layout.addRow("Role:", role_combo)
                layout.addRow(button_box)

                if dialog.exec_() == QDialog.Accepted:
                    role = role_combo.currentText().lower()

                    cursor.execute('''
                        UPDATE users
                        SET role=?
                        WHERE id=?
                    ''', (role, user_id))
                    conn.commit()

                    self.load_access_table()
                    self.log_activity(f"Updated role of {user[1]} to {role}")
                    self.statusBar().showMessage(f"Role of {user[1]} updated", 3000)

    def save_account_settings(self):
        if not self.current_user:
            QMessageBox.warning(self, "Error", "You must be logged in to modify your settings")
            return

        full_name = self.name_edit.text()
        email = self.email_edit.text()
        phone = self.phone_edit.text()
        current_pwd = self.current_pwd_edit.text()
        new_pwd = self.new_pwd_edit.text()
        confirm_pwd = self.confirm_pwd_edit.text()

        if not full_name or not email:
            QMessageBox.warning(self, "Error", "Full name and email are required")
            return

        if new_pwd and (new_pwd != confirm_pwd):
            QMessageBox.warning(self, "Error", "New passwords do not match")
            return

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Check current password if a new one is provided
            if new_pwd:
                cursor.execute("SELECT password FROM users WHERE id=?", (self.current_user['id'],))
                db_pwd = cursor.fetchone()[0]
                hashed_current = hashlib.sha256(current_pwd.encode()).hexdigest()

                if hashed_current != db_pwd:
                    QMessageBox.warning(self, "Error", "Current password is incorrect")
                    return

            # Update information
            update_fields = []
            update_values = []

            update_fields.append("full_name=?")
            update_values.append(full_name)

            update_fields.append("email=?")
            update_values.append(email)

            if phone:
                update_fields.append("phone=?")
                update_values.append(phone)
            else:
                update_fields.append("phone=NULL")

            if new_pwd:
                hashed_new = hashlib.sha256(new_pwd.encode()).hexdigest()
                update_fields.append("password=?")
                update_values.append(hashed_new)

            update_values.append(self.current_user['id'])

            query = f"UPDATE users SET {', '.join(update_fields)} WHERE id=?"
            cursor.execute(query, update_values)
            conn.commit()

            # Update current user
            self.current_user['full_name'] = full_name
            self.current_user['email'] = email
            self.user_name.setText(full_name)

            self.log_activity("Updated account information")
            QMessageBox.information(self, "Success", "Changes have been saved")

            # Clear password fields
            self.current_pwd_edit.clear()
            self.new_pwd_edit.clear()
            self.confirm_pwd_edit.clear()

    def save_preferences(self):
        if not self.current_user:
            QMessageBox.warning(self, "Error", "You must be logged in to modify your preferences")
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
            pass  # Reports are generated on demand
        elif index == 5:  # Settings
            self.load_access_table()

    def closeEvent(self, event):
        if self.current_user:
            self.log_activity(f"Application closed by {self.current_user['full_name']}")

        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Global style
    app.setStyle("Fusion")

    # Default font
    font = QFont()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)

    window = MainDashboard()
    window.show()
    sys.exit(app.exec_())
