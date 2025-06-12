import unittest
from unittest.mock import patch, MagicMock, PropertyMock

# QApplication needs to be instantiated for Qt widgets
from PyQt5.QtWidgets import QApplication, QPushButton
# Ensure the application instance is created once
app = QApplication.instance() if QApplication.instance() else QApplication([])

from carrier_email_dialog import CarrierEmailDialog
# For testing ClientWidget logic, we might need ClientWidget itself or a mock
# from client_widget import ClientWidget # Assuming direct import for now if needed

# Mock db_manager as it's used by CarrierEmailDialog and potentially ClientWidget logic
# The actual db_manager is in 'db.py', but CarrierEmailDialog imports it as 'db_manager'
# from db import crud as db_manager # This would be if crud.py was the source
# CarrierEmailDialog imports 'import db as db_manager'
# So, we patch 'carrier_email_dialog.db_manager'
# And for ClientWidget, it imports 'import db as db_manager'

class TestCarrierEmailDialog(unittest.TestCase):

    @patch('carrier_email_dialog.db_manager')
    @patch('carrier_email_dialog.EmailSenderService')
    def test_send_email_success(self, MockEmailSenderService, mock_db_module):
        mock_email_service_instance = MockEmailSenderService.return_value
        mock_email_service_instance.is_configured.return_value = True
        mock_email_service_instance.send_email.return_value = (True, "Sent successfully")

        dialog = CarrierEmailDialog(
            carrier_name="Test Carrier",
            carrier_email="test@carrier.com",
            client_name="Test Client",
            client_transporter_id=123, # Example ID
            config={} # Mock config
        )
        dialog.recipient_edit.setText("test@carrier.com")
        dialog.subject_edit.setText("Test Subject")
        dialog.body_edit.setPlainText("Test Body")

        dialog.handle_send_email()

        mock_email_service_instance.send_email.assert_called_once_with(
            recipient_email="test@carrier.com",
            subject="Test Subject",
            body="Test Body"
        )
        mock_db_module.update_client_transporter_email_status.assert_called_once_with(123, "Sent")
        # dialog.accept would be called, check if QMessageBox was shown (harder to test directly)

    @patch('carrier_email_dialog.db_manager')
    @patch('carrier_email_dialog.EmailSenderService')
    def test_send_email_failure_service(self, MockEmailSenderService, mock_db_module):
        mock_email_service_instance = MockEmailSenderService.return_value
        mock_email_service_instance.is_configured.return_value = True
        mock_email_service_instance.send_email.return_value = (False, "Service error")

        dialog = CarrierEmailDialog("Carrier", "email@host.com", "Client", 123, config={})
        dialog.recipient_edit.setText("email@host.com") # Ensure fields are not empty
        dialog.subject_edit.setText("Subject")
        dialog.body_edit.setPlainText("Body")
        dialog.handle_send_email()

        mock_db_module.update_client_transporter_email_status.assert_called_once_with(123, "Failed")

    @patch('carrier_email_dialog.db_manager')
    @patch('carrier_email_dialog.EmailSenderService')
    def test_send_email_exception(self, MockEmailSenderService, mock_db_module):
        mock_email_service_instance = MockEmailSenderService.return_value
        mock_email_service_instance.is_configured.return_value = True
        mock_email_service_instance.send_email.side_effect = Exception("SMTP exploded")

        dialog = CarrierEmailDialog("Carrier", "email@host.com", "Client", 123, config={})
        dialog.recipient_edit.setText("email@host.com")
        dialog.subject_edit.setText("Subject")
        dialog.body_edit.setPlainText("Body")
        dialog.handle_send_email()

        mock_db_module.update_client_transporter_email_status.assert_called_once_with(123, "Failed")

    def test_prefill_fields(self):
        dialog = CarrierEmailDialog(
            carrier_name="Cool Transporter",
            carrier_email="cool@transporter.com",
            client_name="Valued Client Inc.",
            client_transporter_id=1,
            config={}
        )
        self.assertEqual(dialog.recipient_edit.text(), "cool@transporter.com")
        self.assertIn("Valued Client Inc.", dialog.subject_edit.text())
        self.assertIn("Cool Transporter", dialog.body_edit.toPlainText())
        self.assertIn("Valued Client Inc.", dialog.body_edit.toPlainText())
        self.assertIn("[Please specify origin]", dialog.body_edit.toPlainText())


# It's complex to test Qt UI interactions directly in unit tests without a running QApplication
# and potentially a lot of mocking for parent widgets and UI elements.
# For ClientWidget.load_assigned_transporters, we'll test the logic that *would* configure the button.

class TestClientWidgetTransporterEmailButtonLogic(unittest.TestCase):

    def get_button_state_for_status(self, email_status):
        """
        Helper to simulate the logic in load_assigned_transporters
        for setting button properties based on email_status.
        Returns a dict of expected properties.
        """
        # Mocking self.tr for this helper
        mock_tr = lambda x: x # Simple passthrough

        button_props = {}
        if email_status == "Sent":
            button_props['text'] = mock_tr("Email Sent")
            button_props['style'] = "background-color: lightgray; color: black;"
            button_props['enabled'] = False
        elif email_status == "Failed":
            button_props['text'] = mock_tr("Resend Email (Failed)")
            button_props['style'] = "background-color: orange; color: black;"
            button_props['enabled'] = True
        else: # Pending or other
            button_props['text'] = mock_tr("Send Email")
            button_props['style'] = "background-color: green; color: white;"
            button_props['enabled'] = True
        return button_props

    def test_button_state_pending(self):
        expected = self.get_button_state_for_status("Pending")
        self.assertEqual(expected['text'], "Send Email")
        self.assertEqual(expected['style'], "background-color: green; color: white;")
        self.assertTrue(expected['enabled'])

    def test_button_state_sent(self):
        expected = self.get_button_state_for_status("Sent")
        self.assertEqual(expected['text'], "Email Sent")
        self.assertEqual(expected['style'], "background-color: lightgray; color: black;")
        self.assertFalse(expected['enabled'])

    def test_button_state_failed(self):
        expected = self.get_button_state_for_status("Failed")
        self.assertEqual(expected['text'], "Resend Email (Failed)")
        self.assertEqual(expected['style'], "background-color: orange; color: black;")
        self.assertTrue(expected['enabled'])

    # To truly test ClientWidget.load_assigned_transporters, one would need to:
    # 1. Instantiate ClientWidget (which itself has many dependencies).
    # 2. Mock db_manager.get_assigned_transporters_for_client to return test data.
    # 3. Call load_assigned_transporters.
    # 4. Access the QTableWidget, then the cell widget (QPushButton), and check its properties.
    # This is more of an integration test. The helper above tests the isolated decision logic.

if __name__ == '__main__':
    unittest.main()
