import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QMessageBox, QApplication, QDialogButtonBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

# Attempt to import WhatsAppService from the same directory
try:
    from .whatsapp_service import WhatsAppService
except ImportError:
    # Fallback for direct execution of this file (e.g., for testing)
    # This might happen if you run this file directly without the package context
    from whatsapp_service import WhatsAppService

class SendWhatsAppDialog(QDialog):
    def __init__(self, phone_number: str = "", client_name: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Send WhatsApp Message"))
        # Assuming a generic icon path, replace if you have a specific one
        # For example, if your icons are in 'resources/icons/logo.svg'
        # self.setWindowIcon(QIcon(":/icons/logo.svg")) # Or QIcon("path/to/your/icon.png")
        self.setMinimumWidth(450) # Increased width slightly

        self.phone_number = phone_number
        self.client_name = client_name
        self.whatsapp_service = WhatsAppService()

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Phone Number
        phone_layout = QHBoxLayout()
        phone_label = QLabel(self.tr("Phone Number:"))
        self.phone_edit = QLineEdit(self.phone_number)
        self.phone_edit.setPlaceholderText(self.tr("Enter phone number with country code (e.g., +1234567890)"))
        phone_layout.addWidget(phone_label)
        phone_layout.addWidget(self.phone_edit)
        layout.addLayout(phone_layout)

        # Message
        message_label = QLabel(self.tr("Message:"))
        layout.addWidget(message_label)
        self.message_edit = QTextEdit()
        default_message = ""
        if self.client_name:
            default_message = self.tr(f"Hello {self.client_name},\n\n")
        # You can add more to the default message, e.g., a standard closing
        # default_message += self.tr("Sent via My Application.")
        self.message_edit.setPlainText(default_message)
        self.message_edit.setAcceptRichText(False) # Ensure plain text for WhatsApp
        self.message_edit.setMinimumHeight(120) # Increased height slightly
        layout.addWidget(self.message_edit)

        # Info Label
        info_label = QLabel(
            self.tr("<b>Note:</b> WhatsApp Web will open in your default browser. "
                    "You may need to scan a QR code if you are not already logged in. "
                    "The browser tab should close automatically after the message is sent (this behavior depends on pywhatkit).")
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 9pt; color: grey; margin-top: 5px; margin-bottom: 5px;")
        layout.addWidget(info_label)

        # Buttons
        self.button_box = QDialogButtonBox()
        # Using standard roles for buttons for better cross-platform look and feel
        self.send_button = self.button_box.addButton(self.tr("Send Message"), QDialogButtonBox.AcceptRole)
        self.cancel_button = self.button_box.addButton(QDialogButtonBox.Cancel)

        layout.addWidget(self.button_box, alignment=Qt.AlignRight) # Align buttons to the right

        # Connect signals
        self.send_button.clicked.connect(self.handle_send_message)
        self.cancel_button.clicked.connect(self.reject) # QDialog's reject slot

    def handle_send_message(self):
        phone_number_to_send = self.phone_edit.text().strip()
        message_to_send = self.message_edit.toPlainText().strip()

        if not phone_number_to_send:
            QMessageBox.warning(self, self.tr("Input Error"), self.tr("Phone number cannot be empty."))
            self.phone_edit.setFocus() # Set focus to phone edit
            return

        # Basic check for '+' prefix, though pywhatkit might handle various formats
        if not phone_number_to_send.startswith('+'):
            QMessageBox.warning(self, self.tr("Input Error"), self.tr("Phone number should start with a country code (e.g., +1...)."))
            self.phone_edit.setFocus()
            return

        if not message_to_send:
            QMessageBox.warning(self, self.tr("Input Error"), self.tr("Message cannot be empty."))
            self.message_edit.setFocus() # Set focus to message edit
            return

        self.send_button.setEnabled(False)
        self.cancel_button.setEnabled(False) # Also disable cancel during send
        QApplication.setOverrideCursor(Qt.WaitCursor)

        # Using default wait_time, tab_close, close_time from WhatsAppService
        success, status_message = self.whatsapp_service.send_message(
            phone_number=phone_number_to_send,
            message=message_to_send
        )

        QApplication.restoreOverrideCursor()
        self.send_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

        if success:
            # Using f-string for more direct formatting
            QMessageBox.information(self, self.tr("Message Status"),
                                    self.tr(f"WhatsApp message sending process initiated.\nDetails: {status_message}"))
            self.accept()  # Close the dialog on success (QDialog's accept slot)
        else:
            QMessageBox.critical(self, self.tr("Sending Failed"),
                                 self.tr(f"Failed to send WhatsApp message.\nError: {status_message}"))
            # Keep dialog open on failure for user to retry, copy message, or correct input.

    def tr(self, text):
        # Simple pass-through for translation.
        # For a real application with multi-language support, you'd use QTranslator.
        return QApplication.translate("SendWhatsAppDialog", text)

if __name__ == '__main__':
    # This block allows testing the dialog independently.
    app = QApplication(sys.argv)

    # In a real application, you would set up QTranslator here if you need i18n
    # For example:
    # translator = QTranslator()
    # if translator.load("myapp_" + QLocale.system().name(), "translations/"):
    #    app.installTranslator(translator)

    # To use a specific icon, ensure the path is correct or use Qt's resource system.
    # For now, we'll rely on the system's default window icon.
    # If you have an icon like "whatsapp_icon.png" in the same directory:
    # app_icon = QIcon("whatsapp_icon.png")
    # app.setWindowIcon(app_icon) # Sets icon for all windows of the app

    print("Starting WhatsApp Dialog Test...")

    # Test 1: Dialog with pre-filled number and name
    dialog1 = SendWhatsAppDialog(phone_number="+19876543210", client_name="Test Client Inc.")
    dialog1.setWindowTitle(dialog1.tr("Test 1: Pre-filled Dialog"))
    # You can set an icon for individual dialogs too if needed
    # dialog1.setWindowIcon(QIcon("path/to/specific_icon.png"))

    print("Showing dialog with pre-filled info (phone: +19876543210, client: Test Client Inc.)...")
    result1 = dialog1.exec_()
    if result1 == QDialog.Accepted:
        print("Dialog 1: Accepted (message sending process initiated).")
    else:
        print(f"Dialog 1: Rejected or Cancelled (Code: {result1}).")

    print("\n-----------------------------------\n")

    # Test 2: Dialog with empty initial values
    dialog2 = SendWhatsAppDialog()
    dialog2.setWindowTitle(dialog2.tr("Test 2: Empty Dialog"))
    print("Showing dialog with empty info...")
    result2 = dialog2.exec_()
    if result2 == QDialog.Accepted:
        print("Dialog 2: Accepted (message sending process initiated).")
    else:
        print(f"Dialog 2: Rejected or Cancelled (Code: {result2}).")

    print("\nTest finished. Exiting application.")
    # sys.exit(app.exec_()) # This is usually for the main application loop.
    # For a script that just runs dialogs and exits, exiting directly might be fine
    # or let it fall through if no other Qt events are pending.
    # If app.exec_() was called, it should be the last line.
    # However, since we might not have a continuous event loop after dialogs close in a test script,
    # we might not need sys.exit(app.exec_()) here if the script is meant to end.
    # For interactive testing where you want the app to stay alive for other potential windows, it's needed.
    # Let's assume the script ends after tests.
    sys.exit(0) # Clean exit
```
