import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QFileDialog, QMessageBox,
    QSizePolicy
)
from PyQt5.QtCore import QObject, pyqtSignal, QCoreApplication

try:
    import db as db_manager
    # Ensure db.py has these functions, or adjust accordingly
    if not all(hasattr(db_manager, func_name) for func_name in ['get_setting', 'set_setting', 'initialize_database']):
        raise ImportError("db module does not have all required functions.")
except ImportError:
    print("Critical: db_manager module not found or is missing required functions. Application may not work correctly.")
    # Fallback or error handling can be more sophisticated here
    # For now, let it fail if db_manager is not correctly set up.
    # If a mock is absolutely needed for some standalone test, it should be explicitly injected.
    sys.exit("Database module misconfiguration - exiting.") # Or raise an exception


COMPANY_PROFILE_KEYS = [
    "company_legal_name", "company_trading_name", "company_address_line1",
    "company_address_line2", "company_city", "company_postal_code", "company_country",
    "company_phone", "company_email", "company_website", "company_vat_number",
    "company_siret_siren", "company_rcs", "company_bank_name", "company_bank_address",
    "company_bank_iban", "company_bank_swift_bic", "company_logo_path",
    "company_trade_document_footer_notes", "company_trade_document_declaration"
]

# For self.tr() to work
class CompanyProfileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ = QCoreApplication.translate # Helper for tr
        self.setWindowTitle(self._("CompanyProfileDialog", "Company Profile"))
        self.setMinimumWidth(600)

        self.fields = {}
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form_layout.setLabelAlignment(QSizePolicy.AlignRight)


        for key in COMPANY_PROFILE_KEYS:
            label_text = self._("CompanyProfileDialog", key.replace("company_", "").replace("_", " ").title() + ":")

            if key in ["company_address_line1", "company_address_line2",
                       "company_bank_address",
                       "company_trade_document_footer_notes",
                       "company_trade_document_declaration"]:
                widget = QTextEdit()
                widget.setMinimumHeight(60) # Adjust as needed
            else:
                widget = QLineEdit()

            if key == "company_logo_path":
                logo_layout = QHBoxLayout()
                self.fields[key] = QLineEdit() # Path display
                logo_layout.addWidget(self.fields[key])
                browse_button = QPushButton(self._("CompanyProfileDialog", "Browse..."))
                browse_button.clicked.connect(self.select_logo_path)
                logo_layout.addWidget(browse_button)
                form_layout.addRow(QLabel(label_text), logo_layout)
            else:
                self.fields[key] = widget
                form_layout.addRow(QLabel(label_text), widget)

        main_layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton(self._("CompanyProfileDialog", "Save"))
        save_button.clicked.connect(self.save_settings)
        cancel_button = QPushButton(self._("CompanyProfileDialog", "Cancel"))
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

    def load_settings(self):
        for key, widget in self.fields.items():
            value = db_manager.get_setting(key)
            if isinstance(widget, QLineEdit):
                widget.setText(value if value is not None else "")
            elif isinstance(widget, QTextEdit):
                widget.setPlainText(value if value is not None else "")

    def save_settings(self):
        try:
            for key, widget in self.fields.items():
                value = ""
                if isinstance(widget, QLineEdit):
                    value = widget.text()
                elif isinstance(widget, QTextEdit):
                    value = widget.toPlainText()
                db_manager.set_setting(key, value)

            QMessageBox.information(self,
                                    self._("CompanyProfileDialog", "Success"),
                                    self._("CompanyProfileDialog", "Company profile settings saved successfully."))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self,
                                 self._("CompanyProfileDialog", "Error"),
                                 self._("CompanyProfileDialog", f"Could not save settings: {str(e)}"))

    def select_logo_path(self):
        # Assuming self.fields["company_logo_path"] is the QLineEdit for the logo path
        current_path = self.fields["company_logo_path"].text()
        file_name, _ = QFileDialog.getOpenFileName(self,
                                                   self._("CompanyProfileDialog", "Select Logo Image"),
                                                   current_path,
                                                   self._("CompanyProfileDialog", "Images (*.png *.jpg *.jpeg *.bmp)"))
        if file_name:
            self.fields["company_logo_path"].setText(file_name)

    # Make tr available if not running in a full QApplication context with translations loaded
    def tr(self, text, context="CompanyProfileDialog"):
        return QCoreApplication.translate(context, text)

if __name__ == '__main__':
    # Ensure QApplication instance exists for QCoreApplication.translate
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    # Initialize database (important for settings table)
    # This might create the db file if it doesn't exist or set up tables
    db_manager.initialize_database()

    dialog = CompanyProfileDialog()

    # Example of setting a value programmatically (for testing)
    # db_manager.set_setting("company_legal_name", "Test Corp Ltd.")
    # dialog.load_settings() # Reload to see the change

    if dialog.exec_() == QDialog.Accepted:
        print("Dialog accepted. Settings should be saved.")
        # You can retrieve and print all settings to verify
        # for key in COMPANY_PROFILE_KEYS:
        #     print(f"{key}: {db_manager.get_setting(key)}")
    else:
        print("Dialog cancelled.")

    # Proper cleanup if using a real DB connection pool or similar
    # db_manager itself does not have a close_connection method, connections are managed per function.
    # if hasattr(db_manager, 'close_connection'):
    #     db_manager.close_connection()

    # sys.exit(app.exec_()) # Not needed if only dialog.exec_() is used for the main loop
    # If the app should continue running after the dialog, then app.exec_() is needed.
    # For this simple test, exiting after dialog is fine.
    sys.exit(0)
