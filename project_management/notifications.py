from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap # QIcon and QPixmap might not be directly used by these two classes, but were in original imports. Will keep for now.

from datetime import datetime, timedelta

# Assuming db.py is structured such that these can be imported directly
# If db.py is in the parent directory and not installed as a package, this might need adjustment
# For now, proceeding with the assumption that the import path will be resolved,
# possibly by adding `.` or `..` to sys.path elsewhere or by restructuring.
# Given the context of moving files within the same project, direct imports from `db` (sibling to projectManagement.py)
# will likely require the application's main execution point to handle Python's import path correctly
# (e.g., by running the app from the root directory).
from db import get_all_status_settings, get_all_projects, get_tasks_by_project_id


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
        all_project_statuses = {s['status_id']: s for s in get_all_status_settings(type_filter='Project')}
        all_task_statuses = {s['status_id']: s for s in get_all_status_settings(type_filter='Task')}

        try:
            all_projects_list = get_all_projects() # Use direct import
            if all_projects_list is None: all_projects_list = []

            today_str = datetime.now().strftime('%Y-%m-%d')
            three_days_later = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')

            for p in all_projects_list: # Iterate over the fetched list
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
                tasks_for_project_list = get_tasks_by_project_id(p.get('project_id')) # Use direct import
                if tasks_for_project_list is None: tasks_for_project_list = []

                for t in tasks_for_project_list: # Iterate over the fetched list
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

    def check_notification(self, title, message):
        """Check if a notification with the same title and message already exists."""
        # This is a simple check; you might want to implement a more robust system
        return self.notification_banner.message_label.text() == f"<b>{title}</b><br>{message}"
