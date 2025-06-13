import unittest
import sys
import os

# Adjust path to import from parent directory if tests are in a subdirectory
# This assumes 'notifications.py' and 'main.py' are in the parent directory of 'tests/'
# or accessible via PYTHONPATH.
# For the sandbox environment, assuming they are in the root or PYTHONPATH is set up.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt5.QtWidgets import QApplication, QMainWindow
from notifications import NotificationManager, NotificationWidget
from main import get_notification_manager # Assuming main.py is in the root

class TestNotificationSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Create a QApplication instance before any tests run."""
        # Ensure a QApplication instance exists. This is crucial for PyQt components.
        # If running tests individually, QApplication.instance() might be None.
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self):
        """Set up for each test."""
        self.main_window = QMainWindow()  # Dummy parent window
        # Instantiate NotificationManager and attach it as if main.py did.
        # This ensures get_notification_manager() can find it.
        self.manager = NotificationManager(parent_window=self.main_window)
        QApplication.instance().notification_manager = self.manager

    def tearDown(self):
        """Clean up after each test."""
        # Close and delete any active notification widgets
        if hasattr(self.manager, 'active_notifications'):
            for widget in list(self.manager.active_notifications): # Iterate over a copy
                widget.close() # This should trigger deletion if WA_DeleteOnClose is set
                # widget.deleteLater() # Explicitly ensure cleanup if needed
            self.manager.active_notifications.clear()

        # Clear the manager instance from QApplication
        if QApplication.instance():
            QApplication.instance().notification_manager = None

        del self.manager
        del self.main_window
        # Important: Process events to allow Qt to clean up deleted widgets
        QApplication.processEvents()


    def test_show_notification_adds_to_active_list(self):
        """Test that showing a notification adds it to the manager's active list."""
        self.manager.show("Test Title", "Test Message")
        self.assertEqual(len(self.manager.active_notifications), 1, "Notification not added to active list.")
        widget = self.manager.active_notifications[0]
        self.assertIsInstance(widget, NotificationWidget, "Active item is not a NotificationWidget instance.")

    def test_notification_widget_properties_set_correctly(self):
        """Test if properties of the NotificationWidget are set as expected."""
        self.manager.show("Info Title", "Info Msg", type='INFO', duration=3000, icon_path="fake/path.png")
        self.assertEqual(len(self.manager.active_notifications), 1)
        widget = self.manager.active_notifications[0]

        self.assertEqual(widget.title_label.text(), "Info Title", "Title not set correctly.")
        self.assertEqual(widget.message_label.text(), "Info Msg", "Message not set correctly.")
        self.assertEqual(widget.duration, 3000, "Duration not set correctly.")
        self.assertEqual(widget.type, 'INFO', "Type not set correctly.")
        self.assertEqual(widget.custom_icon_path, "fake/path.png", "Custom icon path not set correctly.")

    def test_notification_closed_removes_from_list(self):
        """Test that a closed notification is removed from the active list."""
        self.manager.show("Test Close", "Msg to Close")
        self.assertEqual(len(self.manager.active_notifications), 1, "Notification not added before testing close.")

        widget = self.manager.active_notifications[0]

        # Simulate the widget closing.
        # In the actual NotificationWidget, fade_out calls _on_fade_out_finished,
        # which emits closed.emit(self) and then self.close() / self.deleteLater().
        # The manager is connected to closed.emit(self).
        widget.closed.emit(widget)

        # Process events to allow signal handling and potential deleteLater processing
        QApplication.processEvents()

        self.assertEqual(len(self.manager.active_notifications), 0, "Notification not removed from active list after close.")

    def test_multiple_notifications_stack(self):
        """Test adding multiple notifications and calling reposition."""
        self.manager.show("Notification 1", "Message 1")
        self.manager.show("Notification 2", "Message 2")
        self.manager.show("Notification 3", "Message 3")

        self.assertEqual(len(self.manager.active_notifications), 3, "Incorrect number of active notifications.")

        # Call _reposition_notifications to ensure it runs without error
        # Actual visual positioning is hard to test here.
        try:
            self.manager._reposition_notifications()
        except Exception as e:
            self.fail(f"_reposition_notifications raised an exception: {e}")

    def test_get_notification_manager_retrieves_instance(self):
        """Test if the global get_notification_manager function retrieves the correct instance."""
        retrieved_manager = get_notification_manager()
        self.assertIs(retrieved_manager, self.manager, "get_notification_manager did not retrieve the correct instance.")

    def test_notification_widget_default_values(self):
        """Test NotificationWidget default values when not specified."""
        self.manager.show("Default Test", "Default Message")
        self.assertEqual(len(self.manager.active_notifications), 1)
        widget = self.manager.active_notifications[0]

        self.assertEqual(widget.type, 'INFO', "Default type should be INFO.")
        self.assertEqual(widget.duration, 5000, "Default duration should be 5000ms.")
        self.assertIsNone(widget.custom_icon_path, "Default custom_icon_path should be None.")


if __name__ == '__main__':
    # Ensure QApplication is created before running tests, especially if run directly.
    # The setUpClass handles this, but it's good practice for direct script execution.
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    unittest.main()
