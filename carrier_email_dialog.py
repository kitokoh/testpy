# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt
from email_service import EmailSenderService
import db as db_manager # Import the db module

class CarrierEmailDialog(QDialog):
    def __init__(self, carrier_name, carrier_email, client_name, client_transporter_id, parent=None, config=None):
        super().__init__(parent)
        self.carrier_name = carrier_name
        self.carrier_email = carrier_email
        self.client_name = client_name
        self.client_transporter_id = client_transporter_id # Store this ID
        self.config = config # For EmailSenderService

        self.setWindowTitle(self.tr("Send Email to Carrier"))
        self.setMinimumWidth(500)

        self.setup_ui()
        self.prefill_fields()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Recipient
        recipient_layout = QHBoxLayout()
        recipient_label = QLabel(self.tr("Recipient Email:"))
        self.recipient_edit = QLineEdit()
        self.recipient_edit.setReadOnly(False) # Or True if it should not be editable
        recipient_layout.addWidget(recipient_label)
        recipient_layout.addWidget(self.recipient_edit)
        layout.addLayout(recipient_layout)

        # Subject
        subject_layout = QHBoxLayout()
        subject_label = QLabel(self.tr("Subject:"))
        self.subject_edit = QLineEdit()
        subject_layout.addWidget(subject_label)
        subject_layout.addWidget(self.subject_edit)
        layout.addLayout(subject_layout)

        # Body
        body_label = QLabel(self.tr("Body:"))
        layout.addWidget(body_label)
        self.body_edit = QTextEdit()
        self.body_edit.setAcceptRichText(False) # Plain text for now
        layout.addWidget(self.body_edit)

        # Buttons
        button_layout = QHBoxLayout()
        self.send_button = QPushButton(self.tr("Send"))
        self.send_button.clicked.connect(self.handle_send_email)
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

    def prefill_fields(self):
        self.recipient_edit.setText(self.carrier_email)

        default_subject = self.tr("Price Quote Request - {client_name}").format(client_name=self.client_name)
        self.subject_edit.setText(default_subject)

        # Placeholders:
        # - Carrier Name
        # - Client Name
        # - Origin (Point A)
        # - Destination (Point B)
        # - Goods Description

        body_template = self.tr(
            "Dear {carrier_name},\n\n"
            "Our client, {client_name}, requires a price quote for transportation services.\n\n"
            "Details:\n"
            "- Origin (Point A): [Please specify origin]\n"
            "- Destination (Point B): [Please specify destination]\n"
            "- Goods Description: [Please specify goods, e.g., 'General Cargo', 'Palletized Goods']\n\n"
            "Could you please provide us with a quotation at your earliest convenience?\n\n"
            "Thank you,\n"
            "[Your Company Name]"
        ).format(carrier_name=self.carrier_name, client_name=self.client_name)
        self.body_edit.setPlainText(body_template)

    def handle_send_email(self):
        recipient = self.recipient_edit.text()
        subject = self.subject_edit.text()
        body = self.body_edit.toPlainText()

        if not recipient or not subject or not body:
            QMessageBox.warning(self, self.tr("Missing Information"),
                                self.tr("Recipient, Subject, and Body cannot be empty."))
            return

        # Initialize EmailSenderService
        # It might require SMTP configuration from self.config
        # For now, assuming default SMTP config is handled by EmailSenderService if no config_id is passed
        # Or, if your app uses a specific SMTP config, pass its ID.
        # Example: smtp_config_id = self.config.get('default_smtp_config_id') if self.config else None
        # email_service = EmailSenderService(smtp_config_id=smtp_config_id)

        try:
            # Assuming EmailSenderService can be instantiated without explicit config if a default is set up
            email_service = EmailSenderService() # Uses default SMTP from DB or settings

            # Check if the service was initialized correctly (e.g., has a valid configuration)
            if not email_service.is_configured(): # Add an is_configured() method to EmailSenderService
                QMessageBox.critical(self, self.tr("Email Service Error"),
                                     self.tr("Email service is not configured. Please check SMTP settings."))
                return

            success, message = email_service.send_email(
                recipient_email=recipient,
                subject=subject,
                body=body,
                # attachments=None, # Add attachments if needed
                # high_priority=False
            )

            if success:
                QMessageBox.information(self, self.tr("Email Sent"),
                                        self.tr("Email successfully sent to {0}.").format(recipient))
                # Update email status to "Sent"
                if self.client_transporter_id:
                    db_manager.update_client_transporter_email_status(self.client_transporter_id, "Sent")
                self.accept()
            else:
                QMessageBox.critical(self, self.tr("Email Error"),
                                     self.tr("Failed to send email: {0}").format(message))
                # Update email status to "Failed"
                if self.client_transporter_id:
                    db_manager.update_client_transporter_email_status(self.client_transporter_id, "Failed")
        except Exception as e:
            QMessageBox.critical(self, self.tr("Email Sending Error"),
                                 self.tr("An unexpected error occurred while sending the email: {0}").format(str(e)))
            # Update email status to "Failed" on unexpected error
            if self.client_transporter_id:
                db_manager.update_client_transporter_email_status(self.client_transporter_id, "Failed")
            # Log the full error for debugging: logging.error(f"Email sending failed: {e}", exc_info=True)

if __name__ == '__main__':
    import sys
    # This example needs db.py and email_service.py in the same directory or Python path
    # and a valid app_data.db with necessary tables for db_manager functions to work.
    # For standalone testing, you might need to mock db_manager and EmailSenderService.
    app = QApplication(sys.argv)

    # Mock db_manager for standalone testing if db is not set up
    class MockDbManager:
        def update_client_transporter_email_status(self, ct_id, status):
            print(f"Mock DB: update_client_transporter_email_status called with ID {ct_id}, Status: {status}")
            return True

    # Replace real db_manager with mock for testing this dialog in isolation
    # db_manager = MockDbManager() # Uncomment to use mock

    dialog = CarrierEmailDialog(
        carrier_name="Test Carrier",
        carrier_email="carrier@example.com",
        client_name="Test Client",
        client_transporter_id=1 # Example ID
    )
    if dialog.exec_() == QDialog.Accepted:
        print("Dialog accepted (simulated send)")
    else:
        print("Dialog cancelled")
    sys.exit(app.exec_())
