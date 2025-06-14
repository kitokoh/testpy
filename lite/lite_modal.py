from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QLineEdit, QListView, QListWidget, QListWidgetItem, QRadioButton, QGroupBox,
    QSizePolicy, QSpacerItem, QFrame, QInputDialog # Added QInputDialog
)
from PyQt5.QtCore import Qt
# Placeholder for db access, will be refined
import db as db_manager
import os # Added for sys.path manipulation
from .lite_handler import LiteDocumentHandler # Import LiteDocumentHandler

class LitePDFModal(QDialog):
    def __init__(self, parent=None, current_client_id=None): # Added current_client_id
        super().__init__(parent)
        self.setWindowTitle("Lite PDF Document Generator")
        self.current_client_id = current_client_id # Store current_client_id

        main_layout = QVBoxLayout(self)

        self._init_ui()

        self.setLayout(main_layout)
        self.resize(800, 600)
        self._populate_document_templates_list() # Call after UI is set up
        self._update_available_products_list() # Initial population of products

    def _update_available_products_list(self):
        self.available_products_list.clear()
        search_term = self.product_search_input.text().strip()
        lang_code = self.language_combo.currentData()

        if not lang_code: # Should not happen if languages are populated
            self.available_products_list.addItem("Please select a language.")
            return

        name_pattern = f"%{search_term}%" if search_term else "%"

        try:
            products = db_manager.get_all_products_for_selection_filtered(language_code=lang_code, name_pattern=name_pattern)

            if products:
                for product_data_tuple in products:
                    # Assuming product_data_tuple is (product_id, product_name, ...)
                    # Adapt this based on the actual structure returned by the db_manager function
                    # For now, let's assume it returns dictionaries or objects with attributes
                    if isinstance(product_data_tuple, tuple) and len(product_data_tuple) >=2 :
                         # A common case might be (id, name, price, description, lang_code)
                         # We need to map this to a dictionary for consistency
                         product_data = {
                             'product_id': product_data_tuple[0],
                             'product_name': product_data_tuple[1],
                             # Add other fields if present and needed, e.g.
                             # 'price': product_data_tuple[2] if len(product_data_tuple) > 2 else None
                         }
                    elif isinstance(product_data_tuple, dict):
                        product_data = product_data_tuple
                    else:
                        # Fallback if it's an object with attributes
                        try:
                            product_data = {
                                'product_id': product_data_tuple.product_id,
                                'product_name': product_data_tuple.product_name
                            }
                        except AttributeError:
                            print(f"Skipping unexpected product data format: {product_data_tuple}")
                            continue

                    item_text = product_data.get('product_name', 'Unknown Product')
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, product_data)
                    self.available_products_list.addItem(item)
            else:
                no_products_item = QListWidgetItem("No products found for current filters.")
                no_products_item.setFlags(no_products_item.flags() & ~Qt.ItemIsSelectable)
                self.available_products_list.addItem(no_products_item)
        except Exception as e:
            print(f"Error fetching products: {e}")
            error_item = QListWidgetItem("Error loading products.")
            error_item.setFlags(error_item.flags() & ~Qt.ItemIsSelectable)
            self.available_products_list.addItem(error_item)

    def _add_selected_product(self):
        current_item = self.available_products_list.currentItem()
        if not current_item:
            return

        product_data = current_item.data(Qt.UserRole)
        if not product_data: # Should always have data if added correctly
            return

        quantity = self.product_quantity_spinbox.value()

        # Check if product already in selected list, if so, update quantity (optional, or just add as new line)
        # For simplicity, we'll add as a new line or replace if product_id matches.
        # A more robust way would be to iterate and sum quantities or update.

        # For now, just add, allowing duplicates. A real app might want to prevent this or sum quantities.
        display_text = f"{product_data.get('product_name', 'N/A')} (Qty: {quantity})"

        # Check for existing item by product_id (simple check, could be more complex)
        for i in range(self.selected_products_list.count()):
            item = self.selected_products_list.item(i)
            data = item.data(Qt.UserRole)
            if data and data.get('product_id') == product_data.get('product_id'):
                # Product already exists, ask to update quantity or remove and re-add?
                # For now, let's just remove the old one and add new one.
                # Or, more simply, just add another line. Let's do that to avoid complexity here.
                pass # Fall through to add new item for now

        new_item = QListWidgetItem(display_text)
        selected_product_info = {
            'product_id': product_data.get('product_id'),
            'quantity': quantity,
            'name': product_data.get('product_name'),
            'original_data': product_data # Store the full original data if needed later
        }
        new_item.setData(Qt.UserRole, selected_product_info)
        self.selected_products_list.addItem(new_item)

    def _remove_selected_product(self):
        current_row_index = self.selected_products_list.currentRow()
        if current_row_index >= 0:
            self.selected_products_list.takeItem(current_row_index)


    def _populate_document_templates_list(self):
        self.document_templates_list.clear()
        templates = [] # Initialize templates list

        # Try to get the category ID for "Documents HTML"
        html_category = db_manager.get_template_category_by_name("Documents HTML")

        if html_category and html_category.get('category_id') is not None:
            html_category_id = html_category['category_id']
            print(f"Fetching templates for 'Documents HTML' category ID: {html_category_id}")
            templates_from_category = db_manager.get_templates_by_category_id(html_category_id)
            # Optional: Further filter these templates if needed (e.g., ensure they are HTML)
            # For now, assume all templates in "Documents HTML" category are suitable.
            if templates_from_category: # Check if it's not None or empty
                templates = templates_from_category
            else:
                print(f"No templates found under 'Documents HTML' category ID: {html_category_id}, though category exists.")
        else:
            print("Warning: 'Documents HTML' category not found or category_id is missing. Falling back to broader HTML template search.")
            all_file_templates = db_manager.get_all_file_based_templates()
            if all_file_templates: # Ensure it's not None before list comprehension
                templates = [t for t in all_file_templates if t.get('base_file_name','').endswith('.html')]
            else: # all_file_templates itself might be None or empty
                templates = []

        if templates: # Check if templates list is populated (either from category or fallback)
            for template_data in templates:
                # Ensure template_data is a dictionary, as expected by later code
                if isinstance(template_data, tuple) and hasattr(template_data, '_asdict'): # Check if it's a namedtuple
                    template_data = template_data._asdict()
                elif not isinstance(template_data, dict):
                    print(f"Skipping unexpected template data format: {template_data}")
                    continue

                item_text = f"{template_data.get('template_name', 'Unknown Template')} ({template_data.get('language_code', 'N/A')})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, template_data) # Store full template data
                self.document_templates_list.addItem(item)
        else:
            # If still no templates, display a message
            no_template_item = QListWidgetItem("No suitable HTML document templates found.")
            no_template_item.setFlags(no_template_item.flags() & ~Qt.ItemIsSelectable) # Make it non-selectable
            self.document_templates_list.addItem(no_template_item)


    def _init_ui(self):
        # Filters (Language & Country)
        filters_group = QGroupBox("Filters (Language & Country)")
        filters_main_layout = QVBoxLayout() # Renamed to avoid conflict

        filters_layout = QHBoxLayout()

        # Language Filter
        lang_label = QLabel("Language:")
        self.language_combo = QComboBox()
        languages = [("English", "en"), ("French", "fr"), ("Arabic", "ar"), ("Turkish", "tr"), ("Portuguese", "pt")]
        for lang_name, lang_code in languages:
            self.language_combo.addItem(lang_name, lang_code)

        filters_layout.addWidget(lang_label)
        filters_layout.addWidget(self.language_combo)
        filters_layout.addStretch() # Add stretch to separate language and country

        # Country Filter
        country_label = QLabel("Country:")
        self.country_combo = QComboBox()
        try:
            countries = db_manager.get_all_countries()
            if countries:
                for country_id, country_name in countries:
                    self.country_combo.addItem(country_name, country_id)
            else:
                self.country_combo.addItem("No countries found")
                self.country_combo.setEnabled(False)
        except Exception as e:
            print(f"Error fetching countries: {e}")
            self.country_combo.addItem("Error loading countries")
            self.country_combo.setEnabled(False)

        filters_layout.addWidget(country_label)
        filters_layout.addWidget(self.country_combo)

        filters_main_layout.addLayout(filters_layout) # Add the QHBoxLayout to the group's QVBoxLayout
        filters_group.setLayout(filters_main_layout)
        self.layout().addWidget(filters_group)

        # Product Selection
        product_selection_group = QGroupBox("Product Selection")
        product_selection_main_layout = QVBoxLayout()

        # Top Part (Search and Available Products)
        search_add_layout = QHBoxLayout()
        search_add_layout.addWidget(QLabel("Search Products:"))
        self.product_search_input = QLineEdit()
        self.product_search_input.textChanged.connect(self._update_available_products_list)
        search_add_layout.addWidget(self.product_search_input)

        self.product_quantity_spinbox = QSpinBox()
        self.product_quantity_spinbox.setRange(1, 999)
        self.product_quantity_spinbox.setValue(1)
        search_add_layout.addWidget(QLabel("Qty:"))
        search_add_layout.addWidget(self.product_quantity_spinbox)

        self.add_product_button = QPushButton("Add Product")
        self.add_product_button.clicked.connect(self._add_selected_product)
        search_add_layout.addWidget(self.add_product_button)

        product_selection_main_layout.addLayout(search_add_layout)

        self.available_products_list = QListWidget()
        self.available_products_list.setSelectionMode(QListWidget.SingleSelection) # Corrected enum
        product_selection_main_layout.addWidget(self.available_products_list)

        # Bottom Part (Selected Products)
        product_selection_main_layout.addWidget(QLabel("Selected Products:"))
        self.selected_products_list = QListWidget()
        product_selection_main_layout.addWidget(self.selected_products_list)

        self.remove_product_button = QPushButton("Remove Selected Product")
        self.remove_product_button.clicked.connect(self._remove_selected_product)
        product_selection_main_layout.addWidget(self.remove_product_button, 0, Qt.AlignRight)

        product_selection_group.setLayout(product_selection_main_layout)
        self.layout().addWidget(product_selection_group)

        # Document Template Selection
        document_template_group = QGroupBox("Document Template Selection")
        document_template_layout = QVBoxLayout()
        document_template_layout.addWidget(QLabel("Available Document Templates:"))
        self.document_templates_list = QListWidget()
        self.document_templates_list.setSelectionMode(QListWidget.MultiSelection)
        document_template_layout.addWidget(self.document_templates_list)
        document_template_group.setLayout(document_template_layout)
        self.layout().addWidget(document_template_group)

        # Output Actions
        output_actions_group = QGroupBox("Output Actions")
        output_actions_main_layout = QVBoxLayout()

        # PDF Action Radio Buttons
        pdf_actions_layout = QHBoxLayout()
        self.separate_pdfs_radio = QRadioButton("Generate Separate PDFs")
        self.separate_pdfs_radio.setChecked(True)
        self.combine_pdfs_radio = QRadioButton("Generate and Combine PDFs")
        pdf_actions_layout.addWidget(self.separate_pdfs_radio)
        pdf_actions_layout.addWidget(self.combine_pdfs_radio)
        output_actions_main_layout.addLayout(pdf_actions_layout)

        # Buttons (Visualize, Send, Cancel)
        action_buttons_layout = QHBoxLayout()
        self.visualize_button = QPushButton("Visualize PDF(s)")
        self.visualize_button.clicked.connect(self._handle_visualize_pdfs) # Connect
        self.email_button = QPushButton("Send by Email")
        self.email_button.clicked.connect(self._handle_send_email) # Connect
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        action_buttons_layout.addWidget(self.visualize_button)
        action_buttons_layout.addWidget(self.email_button)
        action_buttons_layout.addStretch()
        action_buttons_layout.addWidget(cancel_button)

        output_actions_main_layout.addLayout(action_buttons_layout) # Add button layout to main layout of group
        output_actions_group.setLayout(output_actions_main_layout)
        self.layout().addWidget(output_actions_group)

    # Getter methods for user selections
    def get_selected_language(self) -> str | None:
        return self.language_combo.currentData()

    def get_selected_country(self) -> dict | None:
        # Assuming country_combo stores {country_id: X, country_name: Y} or similar dict
        # If it stores only country_id, this might need adjustment based on how data is stored
        return self.country_combo.currentData()

    def get_selected_products_with_quantity(self) -> list[dict]:
        selected_products = []
        for i in range(self.selected_products_list.count()):
            item = self.selected_products_list.item(i)
            data = item.data(Qt.UserRole)
            if data: # Ensure data exists
                selected_products.append(data)
        return selected_products

    def get_selected_document_templates(self) -> list[dict]:
        selected_templates = []
        for item in self.document_templates_list.selectedItems():
            template_data = item.data(Qt.UserRole)
            if template_data: # Ensure data exists
                # Check if the "no templates found" message is accidentally selected
                if isinstance(template_data, dict) and 'template_id' in template_data:
                    selected_templates.append(template_data)
                elif isinstance(template_data, str) and template_data == "No suitable HTML document templates found.":
                    # This is the placeholder, ignore it
                    pass
        return selected_templates

    def get_selected_pdf_action(self) -> str:
        if self.separate_pdfs_radio.isChecked():
            return "separate"
        elif self.combine_pdfs_radio.isChecked():
            return "combine"
        return "separate" # Default

    def _handle_visualize_pdfs(self):
        lang_code = self.get_selected_language()
        country_data = self.get_selected_country()
        products = self.get_selected_products_with_quantity()
        templates = self.get_selected_document_templates()
        pdf_action = self.get_selected_pdf_action()

        if not self.current_client_id:
             QMessageBox.warning(self, "Client Error", "No current client context. Cannot generate documents.")
             return

        if not products or not templates:
            QMessageBox.warning(self, "Selection Missing", "Please select at least one product and one document template.")
            return

        handler = LiteDocumentHandler(parent_modal=self)
        handler.generate_and_visualize_pdfs(
            client_id_for_context=self.current_client_id,
            language_code=lang_code,
            country_data=country_data,
            products_with_qty=products,
            templates_data=templates,
            pdf_action=pdf_action
        )

    def _handle_send_email(self):
        lang_code = self.get_selected_language()
        country_data = self.get_selected_country()
        products = self.get_selected_products_with_quantity()
        templates = self.get_selected_document_templates()
        pdf_action = self.get_selected_pdf_action()

        if not self.current_client_id:
             QMessageBox.warning(self, "Client Error", "No current client context. Cannot send email.")
             return

        if not products or not templates:
            QMessageBox.warning(self, "Selection Missing", "Please select at least one product and one document template.")
            return

        recipients_str, ok = QInputDialog.getText(self, "Email Recipients", "Enter recipient email(s) (comma-separated):")
        if not ok or not recipients_str.strip():
            return
        recipients = [r.strip() for r in recipients_str.split(',') if r.strip()]
        if not recipients:
            QMessageBox.warning(self, "Input Error", "No valid recipient emails entered.")
            return

        subject, ok = QInputDialog.getText(self, "Email Subject", "Enter subject:")
        if not ok: # User cancelled or entered empty subject (allow empty subject if desired, but cancel is a clear return)
            return

        body, ok = QInputDialog.getMultiLineText(self, "Email Body", "Enter HTML body content (or plain text):")
        if not ok:
            return

        handler = LiteDocumentHandler(parent_modal=self)
        handler.generate_and_send_email(
            client_id_for_context=self.current_client_id,
            language_code=lang_code,
            country_data=country_data,
            products_with_qty=products,
            templates_data=templates,
            pdf_action=pdf_action,
            recipients=recipients,
            subject=subject,
            body_html=body
        )


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    # Assuming db.py is in the parent directory
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import db as db_manager

    app = QApplication(sys.argv)
    db_manager.initialize_database() # Ensure DB is ready

    all_clients_for_test = db_manager.get_all_clients()
    test_id_client = None
    if all_clients_for_test:
        test_id_client = all_clients_for_test[0]['client_id']
        print(f"Using test client ID: {test_id_client} for modal")
    else:
        print("Warning: No clients in DB. LiteModal test might not function fully for email/viz if client context is strictly needed by handler.")

    dialog = LitePDFModal(current_client_id=test_id_client)
    dialog.show()
    sys.exit(app.exec_())
