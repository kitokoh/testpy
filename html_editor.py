import os
import sys
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QDialog, QTextEdit, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QFileDialog, QStyle, QLabel, QLineEdit, QWidget,
    QSizePolicy, QCheckBox # Added QCheckBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QStandardPaths, Qt, QCoreApplication
import functools # For partial
import db # Import the real db module
from db import get_document_context_data, get_default_company # Added
from html_to_pdf_util import render_html_template # Added

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
        self._current_pdf_export_path = None

        default_company_obj = get_default_company() # Use the imported db function
        self.default_company_id = default_company_obj['company_id'] if default_company_obj else None
        if not self.default_company_id:
            # In a real app, use logging. For this example, print is fine.
            print("WARNING: No default company found in database. Some template placeholders (e.g., seller details) may not populate correctly.")
            # Potentially show a QMessageBox.warning to the user if this is critical for editor functionality.

        # Ensure ClientInfoWidget is created before methods that might use it (like _replace_placeholders_html via _load_content)
        # self.client_info_widget = ClientInfoWidget(self.client_data) # Moved to _setup_ui as per standard practice

        self._setup_ui() # This will create self.client_info_widget
        self._load_content() # Now it's safe to call this

    def _setup_ui(self):
        self.setWindowTitle(self.tr("HTML Editor - {0}").format(os.path.basename(self.file_path) if self.file_path else "New Document")) # Handle None file_path
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

        # Options Layout (for checkbox)
        options_layout = QHBoxLayout()
        self.toggle_code_view_checkbox = QCheckBox(self.tr("Show HTML Code Editor"))
        self.toggle_code_view_checkbox.setChecked(False) # Editor is visible by default
        self.html_edit.setVisible(False)
        self.toggle_code_view_checkbox.toggled.connect(self.toggle_code_editor_visibility)
        options_layout.addWidget(self.toggle_code_view_checkbox)
        options_layout.addStretch() # To push checkbox to the left
        # Insert options_layout before the button_layout.
        # If main_layout has other items after client_info_widget and before buttons, adjust index.
        # Current structure: editor_preview_layout, client_info_widget, then buttons.
        # So, index main_layout.count() - 1 might not be right if button_layout is the last one.
        # Let's assume button_layout is added last, so we add options before it.
        # If main_layout structure is [editor_preview_layout, client_info_widget, button_layout],
        # this means index 2 is where button_layout is, so we insert at 2.
        # A safer way if button_layout is always last: main_layout.insertLayout(main_layout.count() -1 , options_layout)
        # For now, assuming button_layout is the last element to be added to main_layout

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

        # Add layouts to main_layout in order
        main_layout.addLayout(options_layout) # Add options layout
        main_layout.addLayout(button_layout)  # Then add button layout

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
            self.refresh_preview() # Ensure content is up-to-date

            self._current_pdf_export_path = file_path # Store for the slot
            page = self.preview_pane.page()

            # Disconnect previous connections if any to avoid multiple calls
            try:
                page.pdfPrintingFinished.disconnect()
            except TypeError: # Signal has no connections
                pass

            page.pdfPrintingFinished.connect(self._handle_pdf_export_signal)
            page.printToPdf(file_path)
            # Inform user that process has started, actual success/failure will be shown by the slot
            QMessageBox.information(self, self.tr("PDF Export Started"),
                                    self.tr("PDF export process has started for: {0}.\nYou will be notified upon completion.").format(file_path))

    def _handle_pdf_export_signal(self, printed_output_path, success):
        # This slot receives the path it printed to and a boolean success status.
        # We use self._current_pdf_export_path as the primary reference for the user message,
        # but printed_output_path is what the engine actually used.

        # Important: Disconnect after use to prevent issues if export_to_pdf is called again
        # for a different file before a previous one finished (though unlikely with modal dialogs).
        try:
            self.preview_pane.page().pdfPrintingFinished.disconnect(self._handle_pdf_export_signal)
        except TypeError:
            pass # No connection to disconnect

        if self._current_pdf_export_path: # Check if an export was initiated
            self.handle_pdf_export_finished(success, self._current_pdf_export_path)
            self._current_pdf_export_path = None # Reset path after handling
        else:
            # This case should ideally not happen if logic is correct
            print(f"Warning: _handle_pdf_export_signal called but _current_pdf_export_path was None. Output path: {printed_output_path}, Success: {success}")


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
        # Ensure client_data and default_company_id are available
        if not self.client_data or 'client_id' not in self.client_data:
            QMessageBox.warning(self, self.tr("Data Error"), self.tr("Client ID is missing. Cannot populate template fully."))
            return html_content # Return original content or minimal processing

        if not self.default_company_id:
            QMessageBox.warning(self, self.tr("Configuration Error"), self.tr("Default company ID is not set. Seller details may be missing."))
            # Proceed, but seller details might be empty if get_document_context_data relies on it.
            # For now, we allow proceeding, get_document_context_data might handle missing company_id gracefully or fail.
            # A better approach for a hard dependency is to prevent this call if default_company_id is None.
            # For now, let it pass to db.get_document_context_data.

        client_id = self.client_data.get('client_id')
        # Determine project_id: 'project_id' might be the direct UUID, 'project_identifier' might be a human-readable one.
        # get_document_context_data expects the UUID form if 'project_id' is used for DB lookups.
        # Let's assume 'project_id' is the correct key if available, otherwise 'project_identifier'
        # The actual key name for project's database ID in client_data should be consistent.
        # For this example, let's prioritize 'project_id' if it exists, then 'project_identifier'.
        # This depends on how client_data is structured when passed to HtmlEditor.
        project_id = self.client_data.get('project_id') or self.client_data.get('project_identifier')

        try:
            # Fetch the comprehensive context
            # Pass project_id only if it's not None or empty string
            context = get_document_context_data(
                client_id=client_id,
                company_id=self.default_company_id, # This could be None if no default company
                project_id=project_id if project_id else None
                # product_ids and additional_context can be added if needed by editor
            )
            # Render the HTML using the new advanced renderer
            return render_html_template(html_content, context)
        except Exception as e:
            # Catch-all for errors during context fetching or rendering
            print(f"Error during placeholder replacement: {e}") # Log this
            QMessageBox.critical(self, self.tr("Template Error"),
                                 self.tr("Could not process template placeholders: {0}").format(e))
            return html_content # Return original on error to avoid breaking editor further

    def refresh_preview(self):
        raw_html = self.html_edit.toPlainText()
        processed_html = self._replace_placeholders_html(raw_html)
        # Provide a base URL for relative paths (e.g., images, CSS)
        # if they are in the same dir as the HTML file or a known assets directory.
        base_url = None
        if self.file_path and os.path.exists(self.file_path):
            base_url = QUrl.fromLocalFile(os.path.dirname(os.path.abspath(self.file_path)) + os.path.sep)
        else:
            # Fallback if file_path is not set (e.g. new document not yet saved)
            # Or use a known global assets directory if applicable.
            # For simplicity, if no file_path, relative local resources might not load in preview.
            # Consider setting base_url to QUrl.fromLocalFile(os.getcwd() + os.path.sep) or similar.
            pass
        self.preview_pane.setHtml(processed_html, baseUrl=base_url if base_url else QUrl())

    def toggle_code_editor_visibility(self, checked):
        self.html_edit.setVisible(checked)

    def save_content(self):
        template_html = self.html_edit.toPlainText() # This is the version with placeholders
        # The current requirement is that save_content saves the *processed* HTML.
        # This means placeholders are filled based on the current client_data and default_company.
        final_html_content = self._replace_placeholders_html(template_html)

        # If self.file_path is None or empty (e.g., new document), prompt for save location.
        if not self.file_path:
            default_save_dir = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
            file_dialog = QFileDialog(self, self.tr("Save HTML File"), default_save_dir, self.tr("HTML Files (*.html *.htm)"))
            file_dialog.setAcceptMode(QFileDialog.AcceptSave)
            if file_dialog.exec_():
                self.file_path = file_dialog.selectedFiles()[0]
            else:
                return # User cancelled save dialog

        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(final_html_content)
            QMessageBox.information(self, self.tr("Success"), self.tr("HTML content saved successfully to {0}.").format(self.file_path))
            self.setWindowTitle(self.tr("HTML Editor - {0}").format(os.path.basename(self.file_path))) # Update window title
            # self.accept() # Uncomment if dialog should close on successful save
        except IOError as e:
            QMessageBox.critical(self, self.tr("Save Error"), self.tr("Could not save HTML file: {0}\n{1}").format(self.file_path, e))

    @staticmethod
    def populate_html_content(html_template_content: str, client_data_dict: dict, # Added default_company_id_static
                              default_company_id_static: str) -> str: # Added default_company_id_static
       # This static method needs to replicate the logic of _replace_placeholders_html
       # but without instance attributes. It needs client_id and default_company_id.

       client_id = client_data_dict.get("client_id")
       project_id = client_data_dict.get("project_id") or client_data_dict.get("project_identifier")

       if not client_id:
           print("Static Populate Error: Client ID missing from client_data_dict.")
           return html_template_content # Or raise error
       if not default_company_id_static:
           print("Static Populate Error: default_company_id_static not provided.")
           # Not returning original, as some placeholders might be from client_data

       try:
            context = get_document_context_data(
                client_id=client_id,
                company_id=default_company_id_static,
                project_id=project_id if project_id else None
            )
            return render_html_template(html_template_content, context)
       except Exception as e:
            print(f"Error in static populate_html_content: {e}")
            return html_template_content


if __name__ == '__main__':
    # Required for QWebEngineView
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    dummy_client_data = {
        "client_id": "dummy_client_uuid_123", # Added client_id
        "Nom du client": "Client Test Main", # Used by ClientInfoWidget directly
        "project_identifier": "MAIN_PROJ_001", # Used by _replace_placeholders and ClientInfoWidget
        "Besoin": "Testing Main Application Flow", # Used by ClientInfoWidget
        "price": 123.45, # Used by ClientInfoWidget
    }

    class MockDBForMain:
        def __init__(self):
            print("Using MockDBForMain for html_editor.py's __main__ block.")

        def get_default_company(self):
            print("MockDB: get_default_company called")
            return {"company_id": "dummy_company_uuid_456", "company_name": "Mock Default Corp"}

        def get_document_context_data(self, client_id, company_id, project_id=None, product_ids=None, additional_context=None):
            print(f"MockDB: get_document_context_data called with client_id={client_id}, company_id={company_id}, project_id={project_id}")
            # Return a simplified context for the __main__ test template
            mock_context = {
                "doc": {
                    "current_date": datetime.now().strftime("%Y-%m-%d"),
                    "current_year": str(datetime.now().year),
                    "currency_symbol": "$",
                    "show_products": True
                },
                "client": {
                    "name": dummy_client_data.get("Nom du client", "N/A Client from Mock"),
                    "id": client_id,
                    "full_address": "Mock Client Address, Mock City, Mock Country",
                    "contact_name": "Mock Client Contact"
                },
                "seller": {
                    "name": "Mock Default Corp from Mock",
                    "address_raw": "Mock Seller St, Seller City",
                    "logo_path_absolute": None # No logo for this mock
                },
                "seller_personnel": {
                    "sales_person_name": "Mock Sales Person"
                },
                "project": {
                    "name": project_id if project_id else "N/A Project from Mock",
                    "id": project_id
                },
                "products": [
                    {"name": "Mock Product A", "price_formatted": "$100", "description": "Desc A"},
                    {"name": "Mock Product B", "price_formatted": "$200", "description": "Desc B"}
                ] if project_id else [], # Only show products if project_id is present for this mock
                "additional": {}
            }
            if additional_context:
                mock_context["additional"].update(additional_context)
            return mock_context

        # Add other db functions that *might* be directly called by HtmlEditor or its components,
        # though with the new _replace_placeholders_html, most data comes via get_document_context_data.
        # db.get_setting was used before, if any part of UI still uses it, it might need mocking.
        # For now, assume these are not directly called by the parts being tested in __main__.
        def get_setting(self, key, default=""):
            print(f"MockDB: get_setting called for {key}")
            return f"MockSetting: {key}"


    original_db_module = sys.modules['db']
    mock_db_instance = MockDBForMain()

    # Monkey patch functions in the actual 'db' module namespace that HtmlEditor imports from
    # This is more targeted than replacing sys.modules['db']
    original_get_default_company = db.get_default_company
    original_get_document_context_data = db.get_document_context_data

    db.get_default_company = mock_db_instance.get_default_company
    db.get_document_context_data = mock_db_instance.get_document_context_data
    # If HtmlEditor directly calls db.get_setting, mock that too:
    # original_get_setting = db.get_setting
    # db.get_setting = mock_db_instance.get_setting


    temp_dir = QStandardPaths.writableLocation(QStandardPaths.TemporaryLocation)
    os.makedirs(temp_dir, exist_ok=True)
    dummy_file_name = f"test_editor_doc_{datetime.now().strftime('%Y%m%d%H%M%S')}.html"
    dummy_file_path = os.path.join(temp_dir, dummy_file_name)
    print(f"Test HTML file will be at: {dummy_file_path}")

    # Updated HTML for __main__ to use {{ }} and new context structure
    with open(dummy_file_path, 'w', encoding='utf-8') as f_dummy:
        f_dummy.write("""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>{{doc.current_date}} - {{client.name}}</title>
</head>
<body>
    <h1>Client: {{client.name}}</h1>
    <p>Address: {{client.full_address}}</p>
    <p>Contact: {{client.contact_name}}</p>
    <hr>
    <h2>Vendeur: {{seller.name}}</h2>
    <p>Vendeur (Commercial): {{seller_personnel.sales_person_name}}</p>
    <p>Projet: {{project.name}} (ID: {{project.id}})</p>

    {{#if doc.show_products}}
        <h3>Produits:</h3>
        <ul>
            {{#each products}}
            <li>{{this.name}} - {{this.price_formatted}} -- {{this.description}}</li>
            {{/each}}
        </ul>
    {{/if}}
    <p>Document généré le: {{doc.current_date}}. Année: {{doc.current_year}}.</p>
</body>
</html>""")

    editor = HtmlEditor(file_path=dummy_file_path, client_data=dummy_client_data)
    editor.show()
    app_exit_code = app.exec_()

    # Restore original db functions
    db.get_default_company = original_get_default_company
    db.get_document_context_data = original_get_document_context_data
    # if 'original_get_setting' in locals(): db.get_setting = original_get_setting

    sys.exit(app_exit_code)
