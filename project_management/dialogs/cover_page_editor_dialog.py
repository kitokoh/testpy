import os
import json
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
                             QGroupBox, QHBoxLayout, QLabel, QPushButton, QTextEdit,
                             QDateEdit, QDialogButtonBox, QFileDialog, QMessageBox)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QPixmap

# Assuming db.py is discoverable
from db import (
    get_all_file_based_templates,
    get_cover_page_template_by_id,
    add_cover_page,
    update_cover_page
)

class CoverPageEditorDialog(QDialog):
    def __init__(self, mode, client_id=None, user_id=None, cover_page_data=None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.client_id = client_id # Used in 'create' mode
        self.user_id = user_id # Used for 'created_by_user_id'
        self.cover_page_data = cover_page_data or {}
        self.current_logo_bytes = self.cover_page_data.get('logo_data')
        self.current_logo_name = self.cover_page_data.get('logo_name')

        self.setWindowTitle(f"{'Edit' if mode == 'edit' else 'Create New'} Cover Page")
        self.setMinimumSize(600, 750)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setSpacing(10)

        self.cp_name_edit = QLineEdit(self.cover_page_data.get('cover_page_name', ''))
        form_layout.addRow("Cover Page Name*:", self.cp_name_edit)

        self.cp_template_combo = QComboBox()
        self.populate_templates_combo()
        self.cp_template_combo.currentIndexChanged.connect(self.on_template_selected)
        form_layout.addRow("Use Template (Optional):", self.cp_template_combo)

        doc_info_group = QGroupBox("Document Information")
        doc_info_form_layout = QFormLayout(doc_info_group)

        self.title_edit = QLineEdit(self.cover_page_data.get('title', ''))
        self.subtitle_edit = QLineEdit(self.cover_page_data.get('subtitle', ''))
        self.author_text_edit = QLineEdit(self.cover_page_data.get('author_text', ''))
        self.institution_text_edit = QLineEdit(self.cover_page_data.get('institution_text', ''))
        self.department_text_edit = QLineEdit(self.cover_page_data.get('department_text', ''))
        self.document_type_text_edit = QLineEdit(self.cover_page_data.get('document_type_text', ''))

        # Handle document_date (creation_date in DB)
        doc_date_str = self.cover_page_data.get('creation_date', QDate.currentDate().toString(Qt.ISODate))
        self.document_date_edit = QDateEdit(QDate.fromString(doc_date_str, Qt.ISODate))
        self.document_date_edit.setCalendarPopup(True)
        self.document_date_edit.setDisplayFormat("yyyy-MM-dd")

        self.document_version_edit = QLineEdit(self.cover_page_data.get('document_version', ''))

        doc_info_form_layout.addRow("Title:", self.title_edit)
        doc_info_form_layout.addRow("Subtitle:", self.subtitle_edit)
        doc_info_form_layout.addRow("Author:", self.author_text_edit)
        doc_info_form_layout.addRow("Institution:", self.institution_text_edit)
        doc_info_form_layout.addRow("Department:", self.department_text_edit)
        doc_info_form_layout.addRow("Document Type:", self.document_type_text_edit)
        doc_info_form_layout.addRow("Document Date:", self.document_date_edit)
        doc_info_form_layout.addRow("Version:", self.document_version_edit)
        form_layout.addRow(doc_info_group)

        logo_group = QGroupBox("Logo")
        logo_layout = QHBoxLayout(logo_group)
        self.logo_preview_label = QLabel("No logo selected.")
        self.logo_preview_label.setFixedSize(150,150)
        self.logo_preview_label.setAlignment(Qt.AlignCenter)
        self.logo_preview_label.setStyleSheet("border: 1px dashed #ccc;")
        self.update_logo_preview()

        browse_logo_btn = QPushButton("Browse...")
        browse_logo_btn.clicked.connect(self.browse_logo)

        clear_logo_btn = QPushButton("Clear Logo")
        clear_logo_btn.clicked.connect(self.clear_logo)

        logo_btn_layout = QVBoxLayout()
        logo_btn_layout.addWidget(browse_logo_btn)
        logo_btn_layout.addWidget(clear_logo_btn)
        logo_btn_layout.addStretch()

        logo_layout.addWidget(self.logo_preview_label)
        logo_layout.addLayout(logo_btn_layout)
        form_layout.addRow(logo_group)

        style_group = QGroupBox("Advanced Style Configuration (JSON)")
        style_layout = QVBoxLayout(style_group)
        style_info_label = QLabel("Edit advanced style properties. Refer to documentation for keys.")
        style_info_label.setWordWrap(True)
        style_layout.addWidget(style_info_label)
        self.style_config_json_edit = QTextEdit()
        detailed_placeholder = """{
    "title_font_family": "Arial", "title_font_size": 30, "title_color": "#000000",
    "subtitle_font_family": "Arial", "subtitle_font_size": 20, "subtitle_color": "#555555",
    "logo_width_mm": 50, "logo_height_mm": 50, "logo_x_mm": 80, "logo_y_mm": 200
}"""
        self.style_config_json_edit.setPlaceholderText(detailed_placeholder)
        self.style_config_json_edit.setMinimumHeight(150) # Adjusted height

        style_json_str = self.cover_page_data.get('style_config_json', '{}')
        try:
            parsed_json = json.loads(style_json_str if isinstance(style_json_str, str) else '{}')
            style_json_str = json.dumps(parsed_json, indent=4)
        except json.JSONDecodeError:
            style_json_str = json.dumps({}, indent=4)
        self.style_config_json_edit.setText(style_json_str)

        style_layout.addWidget(self.style_config_json_edit)
        form_layout.addRow(style_group)
        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.on_save)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        if self.mode == 'edit' and self.cover_page_data.get('template_id'):
            index = self.cp_template_combo.findData(self.cover_page_data['template_id'])
            if index != -1: self.cp_template_combo.setCurrentIndex(index)
        elif self.mode == 'create':
            default_idx = self.cp_template_combo.findData("DEFAULT_TEMPLATE_PLACEHOLDER", Qt.UserRole + 1)
            if default_idx != -1:
                self.cp_template_combo.setCurrentIndex(default_idx)
                self.on_template_selected(default_idx)

    def populate_templates_combo(self):
        self.cp_template_combo.addItem("None (Custom)", None)
        templates = get_all_file_based_templates()
        if templates:
            for tpl in templates:
                self.cp_template_combo.addItem(tpl['template_name'], tpl['template_id'])
                if tpl.get('is_default_template'):
                    self.cp_template_combo.setItemData(self.cp_template_combo.count() -1,
                                                       "DEFAULT_TEMPLATE_PLACEHOLDER",
                                                       Qt.UserRole + 1)

    def on_template_selected(self, index):
        template_id = self.cp_template_combo.itemData(index)
        if not template_id:
            if self.mode == 'create': # Clear fields for "None" in create mode
                self.title_edit.clear()
                self.subtitle_edit.clear()
                self.author_text_edit.clear()
                self.institution_text_edit.clear()
                self.department_text_edit.clear()
                self.document_type_text_edit.clear()
                self.document_date_edit.setDate(QDate.currentDate())
                self.document_version_edit.clear()
                self.style_config_json_edit.setText(json.dumps({}, indent=4))
                self.current_logo_bytes = None
                self.current_logo_name = None
                self.update_logo_preview()
            return

        template_data = get_cover_page_template_by_id(template_id)
        if template_data:
            self.title_edit.setText(template_data.get('default_title', ''))
            self.subtitle_edit.setText(template_data.get('default_subtitle', ''))
            self.author_text_edit.setText(template_data.get('default_author_text', ''))
            self.institution_text_edit.setText(template_data.get('default_institution_text', ''))
            self.department_text_edit.setText(template_data.get('default_department_text', ''))
            self.document_type_text_edit.setText(template_data.get('default_document_type_text', ''))

            doc_date_str = template_data.get('default_document_date', QDate.currentDate().toString(Qt.ISODate))
            self.document_date_edit.setDate(QDate.fromString(doc_date_str, Qt.ISODate))

            self.document_version_edit.setText(template_data.get('default_document_version', ''))

            style_json = template_data.get('style_config_json', '{}')
            try:
                parsed = json.loads(style_json)
                self.style_config_json_edit.setText(json.dumps(parsed, indent=4))
            except json.JSONDecodeError:
                self.style_config_json_edit.setText(json.dumps({}, indent=4))

            self.current_logo_bytes = template_data.get('default_logo_data')
            self.current_logo_name = template_data.get('default_logo_name')
            self.update_logo_preview()

    def browse_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Logo Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    self.current_logo_bytes = f.read()
                self.current_logo_name = os.path.basename(file_path)
                self.update_logo_preview()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load logo: {e}")
                self.clear_logo()

    def clear_logo(self):
        self.current_logo_bytes = None
        self.current_logo_name = None
        self.update_logo_preview()

    def update_logo_preview(self):
        if self.current_logo_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(self.current_logo_bytes)
            self.logo_preview_label.setPixmap(pixmap.scaled(self.logo_preview_label.size(),
                                                             Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.logo_preview_label.setText("No logo")

    def on_save(self):
        cp_name = self.cp_name_edit.text().strip()
        if not cp_name:
            QMessageBox.warning(self, "Validation Error", "Cover Page Name is required.")
            return

        style_config_str = self.style_config_json_edit.toPlainText()
        try:
            json.loads(style_config_str)
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "Invalid JSON", f"Style Configuration is not valid JSON: {e}")
            return

        data_to_save = {
            'cover_page_name': cp_name,
            'client_id': self.client_id if self.mode == 'create' else self.cover_page_data.get('client_id'),
            'created_by_user_id': self.user_id, # Always use current user_id passed to dialog
            'template_id': self.cp_template_combo.currentData(),
            'title': self.title_edit.text(),
            'subtitle': self.subtitle_edit.text(),
            'author_text': self.author_text_edit.text(),
            'institution_text': self.institution_text_edit.text(),
            'department_text': self.department_text_edit.text(),
            'document_type_text': self.document_type_text_edit.text(),
            # DB schema uses 'creation_date' for this field in CoverPages table
            'creation_date': self.document_date_edit.date().toString(Qt.ISODate),
            'document_version': self.document_version_edit.text(),
            'logo_data': self.current_logo_bytes,
            'logo_name': self.current_logo_name,
            'style_config_json': style_config_str
        }

        if self.mode == 'edit' and 'cover_page_id' not in self.cover_page_data:
             QMessageBox.critical(self, "Error", "Cover page ID is missing for an update operation.")
             return
        if not data_to_save['created_by_user_id']:
             QMessageBox.critical(self, "Error", "User ID is missing. Cannot save cover page.")
             return


        if self.mode == 'create':
            new_id = add_cover_page(data_to_save)
            if new_id:
                self.cover_page_data['cover_page_id'] = new_id # Store ID for reference if needed
                QMessageBox.information(self, "Success", "Cover page created successfully.")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to create cover page.")
        elif self.mode == 'edit':
            if update_cover_page(self.cover_page_data['cover_page_id'], data_to_save):
                QMessageBox.information(self, "Success", "Cover page updated successfully.")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to update cover page.")
