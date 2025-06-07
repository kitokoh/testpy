import os
import sys
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QDialog, QTextEdit, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QFileDialog, QStyle, QLabel, QLineEdit, QWidget,
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QFileDialog, QStyle, QLabel, QLineEdit, QWidget,
    QSizePolicy, QSplitter # Removed QCheckBox, Added QSplitter
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebChannel # Added QWebChannel
from PyQt5.QtCore import QUrl, QStandardPaths, Qt, QCoreApplication, pyqtSlot, QObject, pyqtSignal, QFileInfo # Added pyqtSlot, QObject, pyqtSignal, QFileInfo
import functools # For partial
import db # Import the real db module
from db import get_document_context_data, get_default_company
from html_to_pdf_util import render_html_template, convert_html_to_pdf # Added convert_html_to_pdf

# Removed ClientInfoWidget placeholder as it's no longer used in this file

class JsBridge(QObject):
    editorContentReady = pyqtSignal(str)
    tinymceInitialized = pyqtSignal()

    def __init__(self, editor_instance):
        super().__init__()
        self.editor = editor_instance

    @pyqtSlot(str)
    def receiveHtmlContent(self, html):
        self.editor.raw_html_content_from_editor = html
        self.editorContentReady.emit(html)

    @pyqtSlot()
    def onTinymceInitialized(self):
        print("TinyMCE initialized (signal from JS)")
        self.tinymceInitialized.emit()


class HtmlEditor(QDialog):
    def __init__(self, file_path: str, client_data: dict, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.client_data = client_data
        self._current_pdf_export_path = None
        self.raw_html_content_from_editor = ""

        self.web_view = None # Will be QWebEngineView for TinyMCE
        self.bridge = None   # For JS-Python communication
        self.channel = None  # For JS-Python communication

        default_company_obj = get_default_company()
        self.default_company_id = default_company_obj['company_id'] if default_company_obj else None
        if not self.default_company_id:
            print("WARNING: No default company found. Seller details may be missing.")

        self._setup_ui()
        # Connect tinymceInitialized signal to _load_file_content_into_tinymce
        if self.bridge: # Ensure bridge is initialized
            self.bridge.tinymceInitialized.connect(self._load_file_content_into_tinymce)
        # Initial content loading is now handled by _load_file_content_into_tinymce after TinyMCE initializes

    def _setup_ui(self):
        self.setWindowTitle(self.tr("HTML Editor (TinyMCE) - {0}").format(os.path.basename(self.file_path) if self.file_path else "New Document"))
        self.setGeometry(100, 100, 1200, 800)

        main_layout = QVBoxLayout(self)

        # Splitter for draggable resizing between editor and preview
        splitter = QSplitter(Qt.Horizontal)

        self.web_view = QWebEngineView() # This will host TinyMCE
        splitter.addWidget(self.web_view)

        self.preview_pane = QWebEngineView() # For processed HTML preview
        splitter.addWidget(self.preview_pane)

        splitter.setSizes([600, 600]) # Initial equal sizes
        main_layout.addWidget(splitter, 5) # Give most space to editor/preview

        # Setup QWebChannel
        self.bridge = JsBridge(self)
        self.channel = QWebChannel(self.web_view.page())
        self.web_view.page().setWebChannel(self.channel)
        self.channel.registerObject("qt_bridge", self.bridge)

        # Load TinyMCE loader HTML
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Path updated to 'html_editor_assets'
        loader_html_path = os.path.join(current_dir, "html_editor_assets", "tinymce_loader.html")

        if not os.path.exists(loader_html_path):
            error_msg = f"tinymce_loader.html not found at {loader_html_path}. WYSIWYG editor cannot load."
            QMessageBox.critical(self, "Error", error_msg)
            self.web_view.setHtml(f"<h1>{error_msg}</h1>")
        else:
            fi = QFileInfo(loader_html_path) # Use QFileInfo for proper local file URL
            self.web_view.setUrl(QUrl.fromLocalFile(fi.absoluteFilePath()))

        self.web_view.loadFinished.connect(self._on_web_view_load_finished)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton(self.tr("Save"))
        self.save_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.refresh_button = QPushButton(self.tr("Refresh Preview"))
        self.refresh_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.export_pdf_button = QPushButton(self.tr("Export to PDF"))
        self.export_pdf_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogToParent))
        self.close_button = QPushButton(self.tr("Close"))
        self.close_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton))

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.export_pdf_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        main_layout.addLayout(button_layout)

        # Connect signals (save, refresh, export will be connected to JS calls)
        self.save_button.clicked.connect(self.save_content)
        self.refresh_button.clicked.connect(self.refresh_preview)
        self.export_pdf_button.clicked.connect(self.export_to_pdf)
        self.close_button.clicked.connect(self.reject)
        # Connect the bridge signal for receiving content to a handler
        self.bridge.editorContentReady.connect(self._handle_editor_content_callback)


    def _on_web_view_load_finished(self, success):
        if success:
            print("WebEngineView (loader) finished loading.")
            # TinyMCE initialization is triggered by JS in tinymce_loader.html.
            # _load_file_content_into_tinymce() will be called by the 'tinymceInitialized' signal from JsBridge.
        else:
            QMessageBox.critical(self, "Load Error", "Failed to load the TinyMCE loader HTML.")

    def _load_file_content_into_tinymce(self):
        print("TinyMCE ready, loading initial content into editor...")
        if self.file_path and os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Escape content for JavaScript string
                    escaped_content = json.dumps(content)
                    self.web_view.page().runJavaScript(f"setEditorContent({escaped_content});")
                    # Store this initial content. It will be updated if JS calls back or if save/refresh fetches new content.
                    self.raw_html_content_from_editor = content
            except IOError as e:
                QMessageBox.warning(self, self.tr("Load Error"), f"Could not load HTML file: {self.file_path}\n{e}")
                self._set_default_skeleton_in_tinymce() # Load skeleton if file read fails
        else:
            self._set_default_skeleton_in_tinymce() # Load skeleton if no file path or file doesn't exist

        # Trigger an initial preview after attempting to load content
        self.refresh_preview()


    def _set_default_skeleton_in_tinymce(self):
        skeleton_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document</title>
</head>
<body>
    <h1>New Document</h1>
    <p>Client: {{client.name}}</p>
    <p>Project ID: {{project.id}}</p>
</body>
</html>"""
        escaped_content = json.dumps(skeleton_html)
        self.web_view.page().runJavaScript(f"setEditorContent({escaped_content});")
        self.raw_html_content_from_editor = skeleton_html
        # self.refresh_preview() # Called by _load_file_content_into_tinymce after this

    def _replace_placeholders_html(self, html_content: str) -> str:
        if not self.client_data or 'client_id' not in self.client_data:
            QMessageBox.warning(self, self.tr("Data Error"), self.tr("Client ID is missing. Cannot populate template fully."))
            return html_content

        if not self.default_company_id:
            print("WARNING: Default company ID is not set. Seller details may be missing in preview.")

        client_id = self.client_data.get('client_id')
        project_id_for_context = self.client_data.get('project_id_db_uuid') or self.client_data.get('project_identifier')

        try:
            context = get_document_context_data(
                client_id=client_id,
                company_id=self.default_company_id,
                project_id=project_id_for_context if project_id_for_context else None,
                additional_context=self.client_data
            )
            return render_html_template(html_content, context)
        except Exception as e:
            print(f"Error during placeholder replacement: {e}")
            QMessageBox.critical(self, self.tr("Template Error"),
                                 self.tr("Could not process template placeholders: {0}").format(e))
            return html_content

    _save_pending = False
    _preview_pending = False
    _export_pdf_pending = False # Added flag for PDF export

    def _handle_editor_content_callback(self, html_content):
        # This method is now the central callback for content received from JS.
        self.raw_html_content_from_editor = html_content # Update our Python-side copy

        if self._save_pending:
            self._save_pending = False
            if not self.file_path:
                default_save_dir = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
                file_dialog = QFileDialog(self, self.tr("Save HTML File"), default_save_dir, self.tr("HTML Files (*.html *.htm)"))
                file_dialog.setAcceptMode(QFileDialog.AcceptSave)
                if file_dialog.exec_():
                    self.file_path = file_dialog.selectedFiles()[0]
                else:
                    return
            try:
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    f.write(self.raw_html_content_from_editor)
                QMessageBox.information(self, self.tr("Success"), self.tr("HTML content saved successfully to {0}.").format(self.file_path))
                self.setWindowTitle(self.tr("HTML Editor (TinyMCE) - {0}").format(os.path.basename(self.file_path)))
                self.accept()
            except IOError as e:
                QMessageBox.critical(self, self.tr("Save Error"), self.tr("Could not save HTML file: {0}\n{1}").format(self.file_path, e))

        elif self._preview_pending:
            self._preview_pending = False
            processed_html = self._replace_placeholders_html(self.raw_html_content_from_editor)
            base_url = None
            if self.file_path and os.path.exists(self.file_path):
                 base_url = QUrl.fromLocalFile(os.path.dirname(os.path.abspath(self.file_path)) + os.path.sep)
            self.preview_pane.setHtml(processed_html, baseUrl=base_url if base_url else QUrl())

        elif self._export_pdf_pending: # Check the new flag
            self._export_pdf_pending = False
            self._actual_export_to_pdf() # Call the actual export logic


    def save_content(self):
        self._save_pending = True
        self._preview_pending = False
        self._export_pdf_pending = False
        self.web_view.page().runJavaScript("qt_bridge.receiveHtmlContent(getEditorContent());")

    def refresh_preview(self):
        self._preview_pending = True
        self._save_pending = False
        self._export_pdf_pending = False
        self.web_view.page().runJavaScript("qt_bridge.receiveHtmlContent(getEditorContent());")


    def export_to_pdf(self):
        self._export_pdf_pending = True # Set the flag
        self._save_pending = False
        self._preview_pending = False
        self.web_view.page().runJavaScript("qt_bridge.receiveHtmlContent(getEditorContent());")
        # The actual PDF export will happen in _handle_editor_content_callback when _export_pdf_pending is true.

    # This method contains the actual PDF export logic, called by the callback
    def _actual_export_to_pdf(self):
        if not self.raw_html_content_from_editor:
            QMessageBox.warning(self, self.tr("No Content"), self.tr("Editor content is empty. Cannot export PDF."))
            return

        default_file_name = os.path.splitext(os.path.basename(self.file_path or "document"))[0] + ".pdf"
        default_path = os.path.join(QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation), default_file_name)

        file_path_pdf, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save PDF As"), default_path, self.tr("PDF Files (*.pdf)")
        )

        if file_path_pdf:
            processed_html_for_pdf = self._replace_placeholders_html(self.raw_html_content_from_editor)
            base_url_for_pdf = None
            if self.file_path and os.path.exists(self.file_path): # Use original HTML file path for base URL
                 base_url_for_pdf = QUrl.fromLocalFile(os.path.dirname(os.path.abspath(self.file_path)) + os.path.sep).toString()

            pdf_bytes = convert_html_to_pdf(processed_html_for_pdf, base_url=base_url_for_pdf)
            if pdf_bytes:
                try:
                    with open(file_path_pdf, 'wb') as f:
                        f.write(pdf_bytes)
                    QMessageBox.information(self, self.tr("PDF Export"), self.tr("PDF exported successfully to: {0}").format(file_path_pdf))
                except IOError as e:
                    QMessageBox.critical(self, self.tr("PDF Export Error"), self.tr("Could not save PDF file: {0}\n{1}").format(file_path_pdf, e))
            else:
                 QMessageBox.warning(self, self.tr("PDF Export Error"), self.tr("Failed to generate PDF content."))


    # _handle_pdf_export_signal and handle_pdf_export_finished are no longer needed
    # as PDF export is now synchronous after getting content from JS.

    @staticmethod
    def populate_html_content(html_template_content: str, client_data_dict: dict,
                              default_company_id_static: str) -> str:
       client_id = client_data_dict.get("client_id")
       # project_id in client_data_dict might be the human-readable project_identifier
       # or the actual project_uuid. get_document_context_data expects project_id (UUID).
       # This mapping needs to be robust based on what's in client_data_dict.
       # Assuming client_data_dict from ClientWidget will have 'client_id' (UUID) and 'project_identifier' (text).
       # If a 'project_db_id' (UUID) is also available in client_data_dict, prefer that.
       project_id_for_context = client_data_dict.get('project_id_db_uuid') or client_data_dict.get('project_identifier') # Fallback

       if not client_id:
           print("Static Populate Error: Client ID missing from client_data_dict.")
           return html_template_content
       if not default_company_id_static:
           print("Static Populate Error: default_company_id_static not provided for seller context.")

       try:
            context = get_document_context_data(
                client_id=client_id,
                company_id=default_company_id_static, # For seller details
                project_id=project_id_for_context if project_id_for_context else None,
                additional_context=client_data_dict
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
