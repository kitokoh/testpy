# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QComboBox,
    QHeaderView, QMessageBox, QFileDialog, QCheckBox
)
from PyQt5.QtCore import Qt
# import db as db_manager # No longer needed for product functions
from db.cruds.products_crud import products_crud_instance
import html_to_pdf_util # Import the PDF utility

class ProductListDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Product List Management"))
        self.setGeometry(200, 200, 900, 700) # Increased size for more controls

        self.current_offset = 0
        self.limit_per_page = 50 # Example, can be configurable

        main_layout = QVBoxLayout(self)

        # Title Input
        title_layout = QHBoxLayout()
        title_label = QLabel(self.tr("Title:"))
        self.title_edit = QLineEdit(self.tr("Product List")) # Simplified default title
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_edit)
        main_layout.addLayout(title_layout)

        # Filters (Language, Category, Search, Deleted)
        filter_group_box = QGroupBox(self.tr("Filters"))
        filter_form_layout = QFormLayout(filter_group_box)

        self.language_combo = QComboBox()
        # Populate with actual languages from DB or a predefined list
        # For now, placeholder. Real population would be dynamic.
        self.language_combo.addItems([self.tr("All Languages"), "fr", "en", "ar", "tr", "pt"])
        self.language_combo.setCurrentIndex(0)
        self.language_combo.currentIndexChanged.connect(self.apply_filters_and_reload)
        filter_form_layout.addRow(self.tr("Language:"), self.language_combo)

        self.category_filter_input = QLineEdit()
        self.category_filter_input.setPlaceholderText(self.tr("Filter by category..."))
        self.category_filter_input.textChanged.connect(self.apply_filters_and_reload)
        filter_form_layout.addRow(self.tr("Category:"), self.category_filter_input)

        self.search_product_input = QLineEdit()
        self.search_product_input.setPlaceholderText(self.tr("Search by product name..."))
        self.search_product_input.textChanged.connect(self.apply_filters_and_reload)
        filter_form_layout.addRow(self.tr("Search Name:"), self.search_product_input)

        self.include_deleted_checkbox = QCheckBox(self.tr("Include Deleted Products"))
        self.include_deleted_checkbox.stateChanged.connect(self.apply_filters_and_reload)
        filter_form_layout.addRow(self.include_deleted_checkbox)

        main_layout.addWidget(filter_group_box)


        # Product Table
        self.product_table = QTableWidget()
        self.product_table.setColumnCount(4) # Added ID column (hidden)
        self.product_table.setHorizontalHeaderLabels([
            "ID", self.tr("Product Name"), self.tr("Description"), self.tr("Price")
        ])
        self.product_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) # Name
        self.product_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch) # Description
        self.product_table.hideColumn(0) # Hide ID
        self.product_table.itemChanged.connect(self.handle_price_change)
        main_layout.addWidget(self.product_table)

        # Pagination controls
        pagination_layout = QHBoxLayout()
        self.prev_page_button = QPushButton(self.tr("Précédent"))
        self.prev_page_button.clicked.connect(self.prev_page)
        self.page_info_label = QLabel(self.tr("Page 1"))
        self.next_page_button = QPushButton(self.tr("Suivant"))
        self.next_page_button.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.prev_page_button)
        pagination_layout.addWidget(self.page_info_label)
        pagination_layout.addWidget(self.next_page_button)
        main_layout.addLayout(pagination_layout)

        self.load_products_to_table()

        # Action Buttons
        button_layout = QHBoxLayout()
        # Add/Edit/Delete buttons can be added here if direct product management is desired from this dialog
        # For now, keeping it as a list display and export tool.
        self.export_pdf_button = QPushButton(self.tr("Export to PDF"))
        self.export_pdf_button.clicked.connect(self.export_to_pdf_placeholder)
        button_layout.addStretch()
        button_layout.addWidget(self.export_pdf_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def apply_filters_and_reload(self):
        self.current_offset = 0 # Reset to first page when filters change
        self.load_products_to_table()

    def load_products_to_table(self):
        self.product_table.blockSignals(True)
        self.product_table.setRowCount(0)

        lang_text = self.language_combo.currentText()
        language_code = None
        if lang_text != self.tr("All Languages"):
            # This mapping should be more robust or dynamic if languages change
            lang_map = {"English": "en", "French": "fr", "Arabic": "ar", "Turkish": "tr", "Portuguese": "pt"}
            language_code = lang_map.get(lang_text)

        category_filter = self.category_filter_input.text().strip()
        search_name_filter = self.search_product_input.text().strip()
        include_deleted = self.include_deleted_checkbox.isChecked()

        filters = {}
        if language_code:
            filters['language_code'] = language_code
        if category_filter:
            filters['category'] = category_filter # Assuming exact match for category for now
        if search_name_filter:
            filters['product_name'] = f"%{search_name_filter}%" # For LIKE search

        try:
            products = products_crud_instance.get_all_products(
                filters=filters,
                limit=self.limit_per_page,
                offset=self.current_offset,
                include_deleted=include_deleted
            )
            # products is already a list of dicts
            if products:
                self.product_table.setRowCount(len(products))
                for row, product_data in enumerate(products):
                    id_item = QTableWidgetItem(str(product_data.get("product_id")))
                    id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
                    self.product_table.setItem(row, 0, id_item) # Hidden ID col

                    name_item = QTableWidgetItem(product_data.get("product_name"))
                    name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                    name_item.setData(Qt.UserRole, product_data.get("product_id"))
                    self.product_table.setItem(row, 1, name_item) # Name col (index 1)

                    desc_item = QTableWidgetItem(product_data.get("description"))
                    desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
                    self.product_table.setItem(row, 2, desc_item) # Description col (index 2)

                    price_val = product_data.get("base_unit_price")
                    price_str = f"{price_val:.2f}" if isinstance(price_val, (float, int)) else str(price_val)
                    price_item = QTableWidgetItem(price_str)
                    # Price column is editable by default, flags are fine
                    self.product_table.setItem(row, 3, price_item) # Price col (index 3)

            self.update_pagination_controls(len(products))

        except Exception as e:
            print(f"Error loading products to table: {e}")
            QMessageBox.critical(self, self.tr("Load Error"), self.tr(f"Failed to load products: {e}"))
        finally:
            self.product_table.blockSignals(False)

    def update_pagination_controls(self, current_page_item_count: int):
        self.prev_page_button.setEnabled(self.current_offset > 0)
        self.next_page_button.setEnabled(current_page_item_count == self.limit_per_page)
        self.page_info_label.setText(self.tr("Page {0}").format((self.current_offset // self.limit_per_page) + 1))

    def prev_page(self):
        if self.current_offset > 0:
            self.current_offset -= self.limit_per_page
            self.load_products_to_table()

    def next_page(self):
        # Check if current page was full to enable next
        # This is a basic check; a more robust check involves total item count.
        if self.product_table.rowCount() == self.limit_per_page:
            self.current_offset += self.limit_per_page
            self.load_products_to_table()


    def handle_price_change(self, item):
        if item.column() == 3:  # Price column is now index 3
            row = item.row()
            id_item = self.product_table.item(row, 0) # ID is in hidden column 0
            if not id_item:
                print(f"Error: Product ID item not found at row {row}.")
                return
            product_id = id_item.data(Qt.UserRole) # Product ID from UserRole of hidden ID item
            if product_id is None:
                print(f"Error: product_id not found in UserRole for row {row}.")
                return

            new_price_str = item.text()
            try:
                new_price_float = float(new_price_str)
                if new_price_float < 0: raise ValueError(self.tr("Price cannot be negative."))
                self.product_table.blockSignals(True)

                update_result = products_crud_instance.update_product_price(product_id, new_price_float)

                if update_result['success']:
                    print(f"Price for product_id {product_id} updated to {new_price_float:.2f}")
                    item.setText(f"{new_price_float:.2f}") # Reformat
                else:
                    QMessageBox.warning(self, self.tr("Update Failed"),
                                        update_result.get('error', self.tr(f"Failed to update price for product ID {product_id}.")))
                    self.apply_filters_and_reload() # Reload to show actual DB state
            except ValueError as ve:
                QMessageBox.warning(self, self.tr("Invalid Price"), self.tr(f"The entered price '{new_price_str}' is not valid: {ve}"))
                self.apply_filters_and_reload() # Reload to discard invalid entry
            finally:
                self.product_table.blockSignals(False)

    def export_to_pdf_placeholder(self):
        dialog_title = self.title_edit.text()
        # For PDF export, we might want all products matching filters, not just current page
        # Or make it an option. For now, using current filters but without pagination.
        lang_text = self.language_combo.currentText()
        language_code = None
        if lang_text != self.tr("All Languages"):
            lang_map = {"English": "en", "French": "fr", "Arabic": "ar", "Turkish": "tr", "Portuguese": "pt"}
            language_code = lang_map.get(lang_text)

        category_filter = self.category_filter_input.text().strip()
        search_name_filter = self.search_product_input.text().strip()
        include_deleted = self.include_deleted_checkbox.isChecked()

        filters = {}
        if language_code: filters['language_code'] = language_code
        if category_filter: filters['category'] = category_filter
        if search_name_filter: filters['product_name'] = f"%{search_name_filter}%"

        try:
            product_list = products_crud_instance.get_all_products(filters=filters, include_deleted=include_deleted)
            if not product_list:
                QMessageBox.information(self, self.tr("No Products"), self.tr("No products found for the selected criteria."))
                return

            # Basic HTML structure for the PDF
            html_template_string = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>{{ title }}</title>
                <style>
                    body { font-family: sans-serif; }
                    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                    h1 { text-align: center; }
                </style>
            </head>
            <body>
                <h1>{{ title }}</h1>
                <table>
                    <thead>
                        <tr>
                            <th>Product Name</th>
                            <th>Description</th>
                            <th>Price</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{#each products}}
                        <tr>
                            <td>{{ this.product_name }}</td>
                            <td>{{ this.description }}</td>
                            <td>{{ this.base_unit_price }}</td> {# Assuming base_unit_price is directly usable #}
                        </tr>
                        {{/each}}
                        {{#if products_empty}} {# A way to show if list is empty, though get_products might return empty list handled above #}
                        <tr>
                            <td colspan="3" style="text-align: center;">No products to display for the selected language.</td>
                        </tr>
                        {{/if}}
                    </tbody>
                </table>
            </body>
            </html>
            """

            context = {
                'title': dialog_title,
                'products': product_list,
                'products_empty': not bool(product_list) # For {{#if products_empty}}
            }

            rendered_html = html_to_pdf_util.render_html_template(html_template_string, context)

            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            file_path, _ = QFileDialog.getSaveFileName(self, self.tr("Save PDF"), "",
                                                       self.tr("PDF Files (*.pdf);;All Files (*)"), options=options)

            if file_path:
                if not file_path.lower().endswith(".pdf"):
                    file_path += ".pdf"

                pdf_bytes = html_to_pdf_util.convert_html_to_pdf(rendered_html)
                if pdf_bytes:
                    with open(file_path, "wb") as f:
                        f.write(pdf_bytes)
                    QMessageBox.information(self, self.tr("Export Successful"),
                                            self.tr(f"Product list exported successfully to: {file_path}"))
                else:
                    QMessageBox.critical(self, self.tr("Export Failed"),
                                         self.tr("Failed to generate PDF content."))
            else:
                # User cancelled the dialog
                pass

        except Exception as e:
            print(f"Error during PDF export: {e}") # Log to console
            QMessageBox.critical(self, self.tr("Export Error"),
                                 self.tr(f"An error occurred during PDF export: {e}"))


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    dialog = ProductListDialog()
    dialog.show()
    sys.exit(app.exec_())
