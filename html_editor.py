import os
import sys
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QDialog, QTextEdit, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QFileDialog, QStyle, QLabel, QLineEdit, QWidget
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QStandardPaths, Qt

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
            layout.addWidget(QLabel(f"Client Info Placeholder for: {client_data.get('Nom du client', 'N/A')}"))
            self.name_edit = QLineEdit(client_data.get("Nom du client", "")) # Example field
            self.besoin_edit = QLineEdit(client_data.get("Besoin", ""))
            self.price_edit = QLineEdit(str(client_data.get("price", "")))
            self.project_id_edit = QLineEdit(client_data.get("project_identifier", ""))
            layout.addWidget(QLabel("Nom:"))
            layout.addWidget(self.name_edit)
            layout.addWidget(QLabel("Besoin:"))
            layout.addWidget(self.besoin_edit)
            layout.addWidget(QLabel("Prix:"))
            layout.addWidget(self.price_edit)
            layout.addWidget(QLabel("Project ID:"))
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
        self.setWindowTitle(f"HTML Editor - {os.path.basename(self.file_path)}")
        self.setGeometry(100, 100, 1000, 700)  # Initial size

        main_layout = QVBoxLayout(self)

        # Editor and Preview Panes
        editor_preview_layout = QHBoxLayout()

        self.html_edit = QTextEdit()
        self.html_edit.setPlaceholderText("Enter HTML content here...")
        editor_preview_layout.addWidget(self.html_edit, 1)

        self.preview_pane = QWebEngineView()
        editor_preview_layout.addWidget(self.preview_pane, 1)

        main_layout.addLayout(editor_preview_layout, 5)

        self.client_info_widget = ClientInfoWidget(self.client_data, self) # parent is self
        main_layout.addWidget(self.client_info_widget, 1)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton)) # Use self.style()
        self.refresh_button = QPushButton("Refresh Preview")
        self.refresh_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload)) # Use self.style()
        self.close_button = QPushButton("Close")
        self.close_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton)) # Use self.style()

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(button_layout)

        # Connect signals
        self.save_button.clicked.connect(self.save_content)
        self.refresh_button.clicked.connect(self.refresh_preview)
        self.close_button.clicked.connect(self.reject) # QDialog's reject for close

    def _load_content(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.html_edit.setPlainText(content)
            except IOError as e:
                QMessageBox.warning(self, "Load Error", f"Could not load HTML file: {self.file_path}\n{e}")
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

        replacements = {
            "{NOM_CLIENT}": current_client_data.get("Nom du client", ""),
            "{BESOIN_CLIENT}": current_client_data.get("Besoin", ""), # Corrected key from "need" to "Besoin"
            "{DATE_CREATION}": datetime.now().strftime("%d/%m/%Y"),
            "{PRIX_FINAL}": str(current_client_data.get("price", "")),
            "{PROJECT_ID}": current_client_data.get("project_identifier", ""),
            # Add other placeholders from client_data as needed
            "{COMPANY_NAME}": current_client_data.get("company_name", ""),
            "{COUNTRY}": current_client_data.get("country", ""),
            "{CITY}": current_client_data.get("city", ""),
        }

        for placeholder, value in replacements.items():
            html_content = html_content.replace(placeholder, str(value)) # Ensure value is string

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
            QMessageBox.information(self, "Success", "HTML content saved successfully.")
            # self.accept() # Uncomment if dialog should close on successful save
        except IOError as e:
            QMessageBox.critical(self, "Save Error", f"Could not save HTML file: {self.file_path}\n{e}")

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

    # Dummy data for testing
    dummy_client_data = {
        "Nom du client": "Test Client HTML",
        "project_identifier": "HTML_PROJ_001",
        "company_name": "HTML Corp",
        "Besoin": "HTML Editing Test Suite", # Matched to placeholder {BESOIN_CLIENT}
        "country": "Cyberspace",
        "city": "Webville",
        "price": 123.45,
        # Ensure all keys used in _replace_placeholders_html are present here for testing
    }
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
    # if not os.path.exists(dummy_file_path): # Check before writing
    with open(dummy_file_path, 'w', encoding='utf-8') as f_dummy:
        f_dummy.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Test Document</title>
</head>
<body>
    <h1>Hello {NOM_CLIENT}</h1>
    <p>Your project ID is: {PROJECT_ID}.</p>
    <p>Your need is: {BESOIN_CLIENT}.</p>
    <p>Price: {PRIX_FINAL} EUR</p>
    <p>Date: {DATE_CREATION}</p>
    <img src="non_existent_image.png" alt="Test Image">
</body>
</html>""")

    editor = HtmlEditor(file_path=dummy_file_path, client_data=dummy_client_data)
    editor.show()

    sys.exit(app.exec_())