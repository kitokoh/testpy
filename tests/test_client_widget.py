import unittest
from unittest.mock import MagicMock, patch

# Assuming client_widget.py is in the parent directory or accessible via PYTHONPATH
from client_widget import ClientWidget
from PyQt5.QtWidgets import QApplication, QWidget

# Required for QApplication instance
import sys
app = None

def setUpModule():
    global app
    # QApplication instance is required for PyQt widgets
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

def tearDownModule():
    global app
    app.quit()
    app = None


class TestClientWidgetPopulateDocTable(unittest.TestCase):

    def setUp(self):
        # Basic client_info
        self.client_info = {
            "client_id": "test_client_id",
            "client_name": "Test Client",
            "base_folder_path": "/fake/base/path", # Needs to be a valid-looking path for os.path.isdir
            "category": "Standard", # Default category
            "selected_languages": ["en", "fr"]
        }
        # Mock config and notification_manager
        self.mock_config = MagicMock()
        self.mock_config.get.return_value = "/fake/app_root" # for app_root_dir
        self.mock_notification_manager = MagicMock()

        # Mock parent widget
        self.mock_parent = QWidget()

        # Patch os.path.isdir to avoid issues with fake base_folder_path
        self.patcher_isdir = patch('os.path.isdir', return_value=True)
        self.mock_isdir = self.patcher_isdir.start()

    def tearDown(self):
        self.patcher_isdir.stop()
        self.mock_parent.deleteLater() # Clean up the mock parent

    @patch('db_manager.get_distinct_purchase_confirmed_at_for_client')
    @patch('db_manager.get_documents_for_client')
    def test_show_order_filter_boolean_conversion(self, mock_get_documents, mock_get_distinct_purchase):
        '''
        Test that show_order_filter is correctly converted to a boolean,
        especially when it might evaluate to an empty list.
        '''
        # Setup mocks for DB calls within populate_doc_table
        mock_get_documents.return_value = [] # No documents

        # Test scenarios for show_order_filter
        scenarios = [
            # (is_distributor_type, order_events_return, expected_bool_for_setVisible)
            (False, [], False),              # Bug case: [] or False -> False
            (True,  [], True),               # True or [] -> True
            (False, ['event1'], False),      # False or (['event1'] and False) -> False (len is 1, not > 1)
            (True,  ['event1'], True),       # True or (...) -> True
            (False, ['e1', 'e2'], True),     # False or (['e1','e2'] and True) -> True
            (True,  ['e1', 'e2'], True),     # True or (...) -> True
            (False, None, False),            # Simulating DB returning None
        ]

        for is_distributor, order_events, expected_visibility in scenarios:
            with self.subTest(is_distributor=is_distributor, order_events=order_events, expected_visibility=expected_visibility):
                self.client_info['category'] = 'Distributeur' if is_distributor else 'Standard'
                mock_get_distinct_purchase.return_value = order_events

                # Instantiate ClientWidget - this will call setup_ui which calls populate_doc_table
                # We need to ensure all necessary UI elements are mocked or ClientWidget is structured
                # to allow testing populate_doc_table in isolation if possible.
                # For this test, we'll focus on the setVisible call.

                # Mock the doc_filter_layout_widget and its setVisible method specifically
                mock_doc_filter_widget = MagicMock()

                # Create a ClientWidget instance
                # Need to pass app_root_dir
                widget = ClientWidget(self.client_info, self.mock_config, "/fake/app_root", self.mock_notification_manager, parent=self.mock_parent)

                # Replace the actual doc_filter_layout_widget with our mock AFTER instantiation
                # This is because setup_ui creates the widget.
                widget.doc_filter_layout_widget = mock_doc_filter_widget

                # Call populate_doc_table directly to test its logic
                widget.populate_doc_table()

                # Assert that setVisible was called with the expected boolean value
                mock_doc_filter_widget.setVisible.assert_called_once_with(expected_visibility)

                # Reset mock for the next subtest
                mock_doc_filter_widget.reset_mock()
                mock_get_distinct_purchase.reset_mock() # Ensure fresh mock for each scenario run
                mock_get_documents.reset_mock()

                # Clean up widget to avoid issues with subsequent tests
                widget.deleteLater()

if __name__ == '__main__':
    unittest.main()
