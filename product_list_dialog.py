# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QComboBox,
    QHeaderView, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt
import db as db_manager # Import db and alias as db_manager
import html_to_pdf_util # Import the PDF utility

class ProductListDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Product List Management"))
        self.setGeometry(200, 200, 800, 600)

        main_layout = QVBoxLayout(self)

        # Title Input
        title_layout = QHBoxLayout()
        title_label = QLabel(self.tr("Title:"))
        self.title_edit = QLineEdit(self.tr("Product List 2025"))
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_edit)
        main_layout.addLayout(title_layout)

        # Language Filter
        lang_layout = QHBoxLayout()
        lang_label = QLabel(self.tr("Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItems([self.tr("All Languages"), "English", "French", "Arabic"]) # Sample languages + All
        self.language_combo.setCurrentIndex(0) # Default to "All Languages"
        self.language_combo.currentIndexChanged.connect(self.language_filter_changed_placeholder)
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.language_combo)
        lang_layout.addStretch()
        main_layout.addLayout(lang_layout)

        # Product Table
        self.product_table = QTableWidget()
        self.product_table.setColumnCount(3)
        self.product_table.setHorizontalHeaderLabels([
            self.tr("Product Name"), self.tr("Description"), self.tr("Price")
        ])
        self.product_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Make price column editable - itemChanged signal will handle edits.
        self.product_table.itemChanged.connect(self.handle_price_change) # Connect to the new handler
        main_layout.addWidget(self.product_table)

        self.load_products_to_table() # Load initial products (replacing load_sample_data)

        # Action Buttons
        button_layout = QHBoxLayout()
        self.export_pdf_button = QPushButton(self.tr("Export to PDF"))
        self.export_pdf_button.clicked.connect(self.export_to_pdf_placeholder)
        button_layout.addStretch()
        button_layout.addWidget(self.export_pdf_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def load_products_to_table(self, language_code=None):
        self.product_table.blockSignals(True) # Block signals during table population
        self.product_table.setRowCount(0) # Clear table
        try:
            products = db_manager.get_products(language_code=language_code)
            if products:
                self.product_table.setRowCount(len(products))
                for row, product_data in enumerate(products):
                    name_item = QTableWidgetItem(product_data.get("product_name"))
                    name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                    name_item.setData(Qt.UserRole, product_data.get("product_id")) # Store product_id

                    desc_item = QTableWidgetItem(product_data.get("description"))
                    desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)

                    price_val = product_data.get("base_unit_price")
                    price_str = f"{price_val:.2f}" if isinstance(price_val, (float, int)) else str(price_val)
                    price_item = QTableWidgetItem(price_str)
                    # Price column is editable by default

                    self.product_table.setItem(row, 0, name_item)
                    self.product_table.setItem(row, 1, desc_item)
                    self.product_table.setItem(row, 2, price_item)
            # else: # Optional: handle case of no products
            #    pass
        except Exception as e:
            print(f"Error loading products to table: {e}")
            QMessageBox.critical(self, self.tr("Load Error"), self.tr(f"Failed to load products: {e}"))
        finally:
            self.product_table.blockSignals(False) # Unblock signals

    def language_filter_changed_placeholder(self, index):
        language_full_name = self.language_combo.itemText(index)
        language_code = None
        if language_full_name != self.tr("All Languages"):
            lang_code_map = {"English": "en", "French": "fr", "Arabic": "ar"}
            language_code = lang_code_map.get(language_full_name)

        print(f"Language filter changed to: {language_full_name} (code: {language_code})")
        self.load_products_to_table(language_code)

    def handle_price_change(self, item):
        if item.column() == 2:  # Price column
            row = item.row()

            # Retrieve product_id from UserRole data of the item in column 0
            product_name_item = self.product_table.item(row, 0)
            if not product_name_item:
                print(f"Error: Product name item not found at row {row}, cannot get product_id.")
                return

            product_id = product_name_item.data(Qt.UserRole)
            if product_id is None:
                print(f"Error: product_id not found in UserRole for row {row}.")
                # This might happen if the row is a placeholder (e.g., "No products found")
                return

            new_price_str = item.text()
            try:
                new_price_float = float(new_price_str)
                if new_price_float < 0:
                    raise ValueError(self.tr("Price cannot be negative."))

                # Block signals before potential programmatic changes to the table item
                self.product_table.blockSignals(True)

                success = db_manager.update_product_price(product_id, new_price_float)

                if success:
                    print(f"Price for product_id {product_id} updated to {new_price_float:.2f}")
                    # Optional: Re-format the cell to ensure it has 2 decimal places.
                    # This is a programmatic change, so signals should be blocked.
                    item.setText(f"{new_price_float:.2f}")
                else:
                    QMessageBox.warning(self, self.tr("Update Failed"),
                                        self.tr(f"Failed to update price for product ID {product_id} in the database."))
                    # Attempt to revert the cell text to the old price.
                    # This requires fetching the current price again.
                    # For simplicity, we could just reload the data for that row or the whole table.
                    # However, to avoid losing context or scroll position, fetching old value is better.
                    # This part can be complex, for now, we just warn.
                    # A simple revert might be to re-run load_products_to_table, but that's heavy.
                    # A more robust solution would be to store the original value before edit or re-fetch.
                    # For now, if DB update fails, the UI might show the user's new text, but DB has old. This is not ideal.
                    # Let's try to reload the table to reflect actual DB state.
                    current_lang_full = self.language_combo.currentText()
                    lang_code_map_revert = {"English": "en", "French": "fr", "Arabic": "ar", self.tr("All Languages"): None}
                    current_lang_code_revert = lang_code_map_revert.get(current_lang_full)
                    self.load_products_to_table(current_lang_code_revert)


            except ValueError as ve:
                QMessageBox.warning(self, self.tr("Invalid Price"),
                                    self.tr(f"The entered price '{new_price_str}' is not valid: {ve}"))
                # Revert to old state by reloading current view if validation fails
                # This is important because the item in the table already reflects the invalid user input.
                current_lang_full = self.language_combo.currentText()
                lang_code_map_revert_val = {"English": "en", "French": "fr", "Arabic": "ar", self.tr("All Languages"): None}
                current_lang_code_revert_val = lang_code_map_revert_val.get(current_lang_full)
                self.load_products_to_table(current_lang_code_revert_val) # Reload to discard invalid entry

            finally:
                # Always unblock signals
                self.product_table.blockSignals(False)

    def export_to_pdf_placeholder(self):
        dialog_title = self.title_edit.text()
        selected_language_full_name = self.language_combo.currentText()

        # Map full language name to code
        lang_code_map = {
            "English": "en",
            "French": "fr",
            "Arabic": "ar"
            # Add other mappings if necessary
        }
        language_code = lang_code_map.get(selected_language_full_name)

        if not language_code:
            QMessageBox.warning(self, self.tr("Language Not Supported"),
                                self.tr(f"PDF export for '{selected_language_full_name}' is not yet supported or code mapping is missing."))
            return

        try:
            product_list = db_manager.get_products(language_code=language_code)
            if not product_list:
                QMessageBox.information(self, self.tr("No Products"),
                                        self.tr(f"No products found for the selected language: {selected_language_full_name}."))
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
