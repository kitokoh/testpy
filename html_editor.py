import os
import sys
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QDialog, QTextEdit, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QFileDialog, QStyle, QLabel, QLineEdit, QWidget,
    QSizePolicy
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QStandardPaths, Qt, QCoreApplication
import functools # For partial
import db # Import the real db module

# Assuming excel_editor.ClientInfoWidget exists and is importable
# If not, this will need adjustment or a placeholder class
try:
    from excel_editor import ClientInfoWidget
except ImportError:
    # Placeholder if ClientInfoWidget is not yet available or in a different location
    class ClientInfoWidget(QWidget): # Or QGroupBox, depending on its design
        def __init__(self, client_data, parent=None):
            super().__init__(parent)
            self.client_data = client_data
            # Minimal placeholder UI
            layout = QVBoxLayout(self)
            client_name_placeholder = client_data.get('Nom du client', self.tr('N/A'))
            layout.addWidget(QLabel(self.tr("Client Info Placeholder for: {0}").format(client_name_placeholder)))
            self.name_edit = QLineEdit(client_data.get("Nom du client", "")) # Example field
            self.besoin_edit = QLineEdit(client_data.get("Besoin", ""))
            self.price_edit = QLineEdit(str(client_data.get("price", "")))
            self.project_id_edit = QLineEdit(client_data.get("project_identifier", ""))
            layout.addWidget(QLabel(self.tr("Nom:")))
            layout.addWidget(self.name_edit)
            layout.addWidget(QLabel(self.tr("Besoin:")))
            layout.addWidget(self.besoin_edit)
            layout.addWidget(QLabel(self.tr("Prix:")))
            layout.addWidget(self.price_edit)
            layout.addWidget(QLabel(self.tr("Project ID:")))
            layout.addWidget(self.project_id_edit)


        def get_client_data(self):
            # Example: update data from input fields if any
            self.client_data["Nom du client"] = self.name_edit.text()
            self.client_data["Besoin"] = self.besoin_edit.text()
            self.client_data["price"] = self.price_edit.text() # Should be float/int in reality
            self.client_data["project_identifier"] = self.project_id_edit.text()
            return self.client_data

class HtmlEditor(QDialog):
    def __init__(self, file_path: str, client_data: dict, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.client_data = client_data

        # Ensure ClientInfoWidget is created before methods that might use it (like _replace_placeholders_html via _load_content)
        # self.client_info_widget = ClientInfoWidget(self.client_data) # Moved to _setup_ui as per standard practice

        self._setup_ui() # This will create self.client_info_widget
        self._load_content() # Now it's safe to call this

    def _setup_ui(self):
        self.setWindowTitle(self.tr("HTML Editor - {0}").format(os.path.basename(self.file_path)))
        self.setGeometry(100, 100, 1000, 700)  # Initial size

        main_layout = QVBoxLayout(self)

        # Editor and Preview Panes
        editor_preview_layout = QHBoxLayout()

        self.html_edit = QTextEdit()
        self.html_edit.setPlaceholderText(self.tr("Enter HTML content here..."))
        editor_preview_layout.addWidget(self.html_edit, 1)

        self.preview_pane = QWebEngineView()
        editor_preview_layout.addWidget(self.preview_pane, 1)

        main_layout.addLayout(editor_preview_layout, 5)

        self.client_info_widget = ClientInfoWidget(self.client_data, self) # parent is self
        main_layout.addWidget(self.client_info_widget, 1)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton(self.tr("Save"))
        self.save_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton)) # Use self.style()
        self.refresh_button = QPushButton(self.tr("Refresh Preview"))
        self.refresh_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload)) # Use self.style()
        self.close_button = QPushButton(self.tr("Close"))
        self.close_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton)) # Use self.style()

        self.export_pdf_button = QPushButton(self.tr("Export to PDF"))
        self.export_pdf_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogToParent)) # Example icon

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.export_pdf_button) # Add new button
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(button_layout)

        # Connect signals
        self.save_button.clicked.connect(self.save_content)
        self.refresh_button.clicked.connect(self.refresh_preview)
        self.export_pdf_button.clicked.connect(self.export_to_pdf) # Connect new button
        self.close_button.clicked.connect(self.reject) # QDialog's reject for close

    def export_to_pdf(self):
        default_file_name = os.path.splitext(os.path.basename(self.file_path))[0] + ".pdf"
        default_path = os.path.join(QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation), default_file_name)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save PDF As"),
            default_path,
            self.tr("PDF Files (*.pdf)")
        )

        if file_path:
            # Ensure the preview is up-to-date before printing
            self.refresh_preview()

            page = self.preview_pane.page()
            # Use functools.partial to pass file_path to the callback
            callback = functools.partial(self.handle_pdf_export_finished, file_path_ref=file_path)
            page.printToPdf(file_path, callback)
            # If the above line with callback causes issues (e.g. specific Qt version compatibility):
            # page.printToPdf(file_path)
            # self.handle_pdf_export_finished(True, file_path_ref=file_path) # Assume success for simplicity
            # QMessageBox.information(self, self.tr("PDF Export"),
            #                         self.tr("PDF export process started for: {0}.\nNotification of completion depends on system setup.").format(file_path))


    def handle_pdf_export_finished(self, success, file_path_ref): # file_path_ref is passed by functools.partial
        if success:
            QMessageBox.information(self, self.tr("PDF Export"),
                                    self.tr("PDF exported successfully to: {0}").format(file_path_ref))
        else:
            QMessageBox.warning(self, self.tr("PDF Export"),
                                self.tr("Failed to export PDF to: {0}").format(file_path_ref))

    def _load_content(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.html_edit.setPlainText(content)
            except IOError as e:
                QMessageBox.warning(self, self.tr("Load Error"), self.tr("Could not load HTML file: {0}\n{1}").format(self.file_path, e))
                # Fallback to default skeleton if load fails
                self._set_default_skeleton()
        else:
            self._set_default_skeleton()
        self.refresh_preview()

    def _set_default_skeleton(self):
        skeleton_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document</title>
</head>
<body>
    <h1>New Document</h1>
    <p>Client: {NOM_CLIENT}</p>
    <p>Project ID: {PROJECT_ID}</p>
</body>
</html>"""
        self.html_edit.setPlainText(skeleton_html)

    def _replace_placeholders_html(self, html_content: str) -> str:
        current_client_data = self.client_info_widget.get_client_data()

        # Existing replacements from client_info_widget (using {...} style)
        replacements = {
            "{NOM_CLIENT}": current_client_data.get("Nom du client", ""),
            "{BESOIN_CLIENT}": current_client_data.get("Besoin", ""),
            "{DATE_CREATION}": datetime.now().strftime("%d/%m/%Y"),
            "{PRIX_FINAL}": str(current_client_data.get("price", "")),
            "{PROJECT_ID}": current_client_data.get("project_identifier", ""),
            # Example of other client-specific data that might be in client_info_widget
            # "{CLIENT_SPECIFIC_FIELD}": current_client_data.get("some_client_field", ""),
        }

        for placeholder, value in replacements.items():
            html_content = html_content.replace(placeholder, str(value))

        # New replacements from db settings (using {{...}} style)
        company_legal_name = db.get_setting('company_legal_name') or ""
        company_address_line1 = db.get_setting('company_address_line1') or ""
        company_city = db.get_setting('company_city') or ""
        company_postal_code = db.get_setting('company_postal_code') or ""
        company_country = db.get_setting('company_country') or ""
        company_email = db.get_setting('company_email') or ""
        # Add other company settings as needed
        # company_phone = db.get_setting('company_phone') or ""
        # company_vat_number = db.get_setting('company_vat_number') or ""
        # company_logo_path = db.get_setting('company_logo_path') or "" # For image tags if used

        html_content = html_content.replace("{{company_legal_name}}", company_legal_name)
        html_content = html_content.replace("{{company_address_line1}}", company_address_line1)
        html_content = html_content.replace("{{company_city}}", company_city)
        html_content = html_content.replace("{{company_postal_code}}", company_postal_code)
        html_content = html_content.replace("{{company_country}}", company_country)
        html_content = html_content.replace("{{company_email}}", company_email)
        # html_content = html_content.replace("{{company_phone}}", company_phone)
        # html_content = html_content.replace("{{company_vat_number}}", company_vat_number)
        # html_content = html_content.replace("{{seller_logo_url}}", company_logo_path) # Example for logo

        # Generic placeholders that might be common and can be sourced from company profile or app settings
        html_content = html_content.replace("{{current_year}}", datetime.now().strftime("%Y"))


        # It's important to handle placeholders that might not be filled to avoid showing them.
        # For example, if a db.get_setting() returns None or empty string, it's handled by `or ""`.
        # However, if a placeholder like `{{some_unfilled_placeholder}}` remains, it will appear literally.
        # A more robust system might involve regex to find all `{{...}}` and remove those not found in data.

        return html_content

    def refresh_preview(self):
        raw_html = self.html_edit.toPlainText()
        processed_html = self._replace_placeholders_html(raw_html)
        # Provide a base URL for relative paths (e.g., images, CSS) if they are in the same dir as the HTML file
        base_url = QUrl.fromLocalFile(os.path.dirname(os.path.abspath(self.file_path)) + os.path.sep)
        self.preview_pane.setHtml(processed_html, baseUrl=base_url)


    def save_content(self):
        template_html = self.html_edit.toPlainText() # This is the version with placeholders
        # If you want to save the version processed for the current client:
        # final_html_content = self._replace_placeholders_html(template_html)
        # However, typically templates are saved with placeholders.
        # For this implementation, let's assume we save the client-specific version.
        final_html_content = self._replace_placeholders_html(template_html)


        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(final_html_content)
            QMessageBox.information(self, self.tr("Success"), self.tr("HTML content saved successfully."))
            # self.accept() # Uncomment if dialog should close on successful save
        except IOError as e:
            QMessageBox.critical(self, self.tr("Save Error"), self.tr("Could not save HTML file: {0}\n{1}").format(self.file_path, e))

    @staticmethod
    def populate_html_content(html_template_content: str, client_data_dict: dict) -> str:
       # This method will be similar to _replace_placeholders_html but callable statically.
       # It won't have access to self.client_info_widget directly.
       # It needs client_data_dict passed in.

       # Minimal client data for direct use (adapt if ClientInfoWidget provides more complex structure)
       replacements = {
           "{NOM_CLIENT}": client_data_dict.get("client_name", ""), # Note: key change from "Nom du client"
           "{BESOIN_CLIENT}": client_data_dict.get("need", ""),    # Note: key change
           "{DATE_CREATION}": datetime.now().strftime("%d/%m/%Y"),
           "{PRIX_FINAL}": str(client_data_dict.get("price", "")),
           "{PROJECT_ID}": client_data_dict.get("project_identifier", "")
           # Add any other direct client_data fields needed
       }

       processed_html = html_template_content
       for placeholder, value in replacements.items():
           processed_html = processed_html.replace(placeholder, str(value))
       return processed_html

if __name__ == '__main__':
    # Required for QWebEngineView
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Dummy data for testing ClientInfoWidget
    # These should ideally not conflict with company profile keys fetched from db.get_setting
    dummy_client_data = {
        "Nom du client": "Client Test Widget",
        "project_identifier": "WIDGET_PROJ_007",
        "Besoin": "Testing Widget Integration",
        "price": 99.99,
        # Keys like "company_name", "country", "city" that were previously in dummy_client_data
        # for direct replacement should be removed if they are now intended to be fetched
        # via db.get_setting for {{company_...}} placeholders.
        # If they are meant for client-specific fields like {COMPANY_NAME}, they can remain.
        # The current _replace_placeholders_html uses current_client_data.get("company_name", "") for {COMPANY_NAME}
        # and db.get_setting('company_legal_name') for {{company_legal_name}}. This is fine.
    }

    # Mock db operations for __main__ if db.py is not fully set up or for isolated testing
    # This is a local mock, not replacing the global `db` import for the class itself.
    class MockDBForMain:
        def __init__(self):
            self._settings = {
                'company_legal_name': "Main Test Corp.",
                'company_address_line1': "123 Main St",
                'company_city': "Testville",
                'company_postal_code': "12345",
                'company_country': "Testland",
                'company_email': "main_contact@testcorp.com"
            }
            print("Using MockDBForMain for html_editor.py's __main__ block.")

        def get_setting(self, key, default=""):
            return self._settings.get(key, default)

        def initialize_database(self): # Add if db.initialize_database() is called in main
            print("MockDBForMain: Database initialized.")

    # Replace the global db object with the mock FOR THE DURATION OF __main__
    # This is generally not ideal, but for a simple script test it can work.
    # A better approach would be dependency injection for HtmlEditor if db access needs to be mocked.
    original_db = db
    db = MockDBForMain()
    if hasattr(db, 'initialize_database'): # Check if initialize_database is needed by main's usage of db
        db.initialize_database()


    # Create a dummy file path in a writable temporary location
    temp_dir = QStandardPaths.writableLocation(QStandardPaths.GenericTempLocation) # More generic temp
    if not temp_dir: # Fallback if generic temp is not found
        temp_dir = "."

    # Ensure temp_dir exists
    os.makedirs(temp_dir, exist_ok=True)

    dummy_file_name = f"test_document_{datetime.now().strftime('%Y%m%d%H%M%S')}.html"
    dummy_file_path = os.path.join(temp_dir, dummy_file_name)

    print(f"Test HTML file will be at: {dummy_file_path}") # For debugging test setup

    # Optional: Create a dummy HTML file for testing loading, with correct placeholders
    # This template should now use {{company_...}} placeholders for company data
    # and {...} for client-specific data.
    with open(dummy_file_path, 'w', encoding='utf-8') as f_dummy:
        f_dummy.write("""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Test Document</title>
    <style> body { font-family: sans-serif; } .seller-details h2 {color: blue;} </style>
</head>
<body>
    <div class="seller-details">
        <h2>{{company_legal_name}}</h2>
        <p>{{company_address_line1}}</p>
        <p>{{company_city}} {{company_postal_code}} {{company_country}}</p>
        <p>Email: {{company_email}}</p>
    </div>
    <hr>
    <h1>Facture pour {NOM_CLIENT}</h1>
    <p>ID Projet: {PROJECT_ID}</p>
    <p>Besoin: {BESOIN_CLIENT}</p>
    <p>Prix: {PRIX_FINAL} EUR</p>
    <p>Date de création: {DATE_CREATION}</p>
    <p>Année en cours pour le pied de page: {{current_year}}</p>
    <img src="non_existent_image.png" alt="Test Image">
</body>
</html>""")

    editor = HtmlEditor(file_path=dummy_file_path, client_data=dummy_client_data)
    editor.show()

    app_exit_code = app.exec_()

    # Restore original db object if it was mocked for main
    db = original_db

    sys.exit(app_exit_code)
