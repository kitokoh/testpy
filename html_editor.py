import os
import sys
import json # For escaping strings for JavaScript
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QFileDialog, QStyle, QLabel, QLineEdit, QWidget,
    QSizePolicy, QSplitter
)
from PyQt5.QtWebChannel import QWebChannel

from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebChannel
from PyQt5.QtCore import QUrl, QStandardPaths, Qt, QCoreApplication, pyqtSlot, QObject, pyqtSignal, QFileInfo
import db as db_manager
from db import get_document_context_data, get_default_company
from html_to_pdf_util import render_html_template, convert_html_to_pdf

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

        self.web_view = None
        self.bridge = None
        self.channel = None

        default_company_obj = get_default_company()
        self.default_company_id = default_company_obj['company_id'] if default_company_obj else None
        if not self.default_company_id:
            print("WARNING: No default company found. Seller details may be missing.")

        self._setup_ui()
        if self.bridge:
            self.bridge.tinymceInitialized.connect(self._load_file_content_into_tinymce)

    def _setup_ui(self):
        self.setWindowTitle(self.tr("HTML Editor (TinyMCE) - {0}").format(os.path.basename(self.file_path) if self.file_path else "New Document"))
        self.setGeometry(100, 100, 1200, 800)

        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)

        self.web_view = QWebEngineView()
        splitter.addWidget(self.web_view)

        self.preview_pane = QWebEngineView()
        splitter.addWidget(self.preview_pane)

        splitter.setSizes([700, 500])
        main_layout.addWidget(splitter, 1)

        self.bridge = JsBridge(self)
        self.channel = QWebChannel(self.web_view.page())
        self.web_view.page().setWebChannel(self.channel)
        self.channel.registerObject("qt_bridge", self.bridge)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        loader_html_path = os.path.join(current_dir, "html_editor_assets", "tinymce_loader.html")

        if not os.path.exists(loader_html_path):
            error_msg = f"tinymce_loader.html not found at {loader_html_path}. WYSIWYG editor cannot load."
            QMessageBox.critical(self, "Error", error_msg)
            self.web_view.setHtml(f"<h1>{error_msg}</h1>")
        else:
            fi = QFileInfo(loader_html_path)
            self.web_view.setUrl(QUrl.fromLocalFile(fi.absoluteFilePath()))

        self.web_view.loadFinished.connect(self._on_web_view_load_finished)

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

        self.save_button.clicked.connect(self.save_content)
        self.refresh_button.clicked.connect(self.refresh_preview)
        self.export_pdf_button.clicked.connect(self.export_to_pdf)
        self.close_button.clicked.connect(self.reject)
        self.bridge.editorContentReady.connect(self._handle_editor_content_callback)

    def _on_web_view_load_finished(self, success):
        if success:
            print("WebEngineView (loader) finished loading.")
        else:
            QMessageBox.critical(self, "Load Error", "Failed to load the TinyMCE loader HTML.")

    def _load_file_content_into_tinymce(self):
        print("Attempting to load content into TinyMCE...")
        content_to_load = ""
        if self.file_path and os.path.exists(self.file_path):  # 8 spaces
            try:  # 12 spaces
                with open(self.file_path, 'r', encoding='utf-8') as f:  # 16 spaces
                    content_to_load = f.read()  # 20 spaces
            except IOError as e:  # 12 spaces
                QMessageBox.warning(self, self.tr("Load Error"), f"Could not load HTML file: {self.file_path}\n{e}")  # 16 spaces
                content_to_load = self._get_default_skeleton_html()  # 16 spaces
        else:  # 8 spaces
            content_to_load = self._get_default_skeleton_html()  # 12 spaces

        escaped_content = json.dumps(content_to_load)
        self.web_view.page().runJavaScript(f"setEditorContent({escaped_content});")
        self.raw_html_content_from_editor = content_to_load
        self.refresh_preview()


    def _get_default_skeleton_html(self):
        return """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Document</title></head>
<body><h1>New Document</h1><p>Client: {{client.name}}</p></body>
</html>"""

    def _replace_placeholders_html(self, html_content: str) -> str:
        if not self.client_data or 'client_id' not in self.client_data:
            QMessageBox.warning(self, self.tr("Data Error"), self.tr("Client ID is missing. Cannot populate template fully."))
            return html_content
        if not self.default_company_id:
            print("WARNING: Default company ID is not set. Seller details may be missing.")

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
            QMessageBox.critical(self, self.tr("Template Error"), self.tr("Could not process template placeholders: {0}").format(e))
            return html_content

    _save_pending = False
    _preview_pending = False
    _export_pdf_pending = False

    def _handle_editor_content_callback(self, html_content):
        self.raw_html_content_from_editor = html_content

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
            base_url = QUrl.fromLocalFile(QFileInfo(self.file_path).absolutePath()) if self.file_path and os.path.exists(self.file_path) else QUrl()
            self.preview_pane.setHtml(processed_html, baseUrl=base_url)

        elif self._export_pdf_pending:
            self._export_pdf_pending = False
            self._actual_export_to_pdf()

    def save_content(self):
        self._save_pending = True
        self._preview_pending = False
        self._export_pdf_pending = False
        self.web_view.page().runJavaScript("getEditorContent();")

    def refresh_preview(self):
        self._preview_pending = True
        self._save_pending = False
        self._export_pdf_pending = False
        self.web_view.page().runJavaScript("getEditorContent();")

    def export_to_pdf(self):
        self._export_pdf_pending = True
        self._save_pending = False
        self._preview_pending = False
        self.web_view.page().runJavaScript("getEditorContent();")

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
            base_url_for_pdf = QUrl.fromLocalFile(QFileInfo(self.file_path).absolutePath()).toString() if self.file_path and os.path.exists(self.file_path) else None

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

    @staticmethod
    def populate_html_content(html_template_content: str, client_data_dict: dict,
                              default_company_id_static: str) -> str:
       client_id = client_data_dict.get("client_id")
       project_id_for_context = client_data_dict.get('project_id_db_uuid') or client_data_dict.get('project_identifier')

       if not client_id:
           print("Static Populate Error: Client ID missing from client_data_dict.")
           return html_template_content
       if not default_company_id_static:
           print("Static Populate Error: default_company_id_static not provided for seller context.")

       try:
            context = get_document_context_data(
                client_id=client_id,
                company_id=default_company_id_static,
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
        "client_id": "dummy_client_uuid_123",
        "Nom du client": "Client Test Main",
        "project_identifier": "MAIN_PROJ_001",
        "Besoin": "Testing Main Application Flow",
        "price": 123.45,
    }

    class MockDBForMain:
        def __init__(self):
            print("Using MockDBForMain for html_editor.py's __main__ block.")

        def get_default_company(self):
            print("MockDB: get_default_company called")
            return {"company_id": "dummy_company_uuid_456", "company_name": "Mock Default Corp"}

        def get_document_context_data(self, client_id, company_id, project_id=None, product_ids=None, additional_context=None):
            print(f"MockDB: get_document_context_data called with client_id={client_id}, company_id={company_id}, project_id={project_id}")
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
                    "logo_path_absolute": None
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
                ] if project_id else [],
                "additional": {}
            }
            if additional_context:
                mock_context["additional"].update(additional_context)
            return mock_context

        def get_setting(self, key, default=""):
            print(f"MockDB: get_setting called for {key}")
            return f"MockSetting: {key}"


    original_db_module = sys.modules['db']
    mock_db_instance = MockDBForMain()

    original_get_default_company = db_manager.get_default_company
    original_get_document_context_data = db_manager.get_document_context_data

    db_manager.get_default_company = mock_db_instance.get_default_company
    db_manager.get_document_context_data = mock_db_instance.get_document_context_data

    temp_dir = QStandardPaths.writableLocation(QStandardPaths.TemporaryLocation)
    os.makedirs(temp_dir, exist_ok=True)
    dummy_file_name = f"test_editor_doc_{datetime.now().strftime('%Y%m%d%H%M%S')}.html"
    dummy_file_path = os.path.join(temp_dir, dummy_file_name)
    print(f"Test HTML file will be at: {dummy_file_path}")

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

    db_manager.get_default_company = original_get_default_company
    db_manager.get_document_context_data = original_get_document_context_data

    sys.exit(app_exit_code)
