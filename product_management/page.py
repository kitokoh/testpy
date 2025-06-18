from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,                                     QTableWidget, QTableWidgetItem, QPushButton, QComboBox,                                     QHeaderView, QMessageBox, QFileDialog, QCheckBox,                                     QGroupBox, QFormLayout, QDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from .edit_dialog import ProductEditDialog
from db.cruds.products_crud import products_crud_instance
import html_to_pdf_util

class ProductManagementPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._setup_ui()

    def _setup_ui(self):
        # self.setWindowTitle(self.tr("Product Management")) # QWidget doesn't have setWindowTitle, usually set on parent QMainWindow or QDialog

        self.current_offset = 0
        self.limit_per_page = 50

        main_layout = QVBoxLayout(self)

        title_layout = QHBoxLayout()
        title_label = QLabel(self.tr("Product Database Management"))
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        # Top Controls (Add, Edit, Delete, Export)
        self.add_product_button = QPushButton(self.tr("Add Product"))
        self.add_product_button.clicked.connect(self._open_add_product_dialog)
        self.edit_product_button = QPushButton(self.tr("Edit Product"))
        self.edit_product_button.clicked.connect(self._open_edit_product_dialog)
        self.edit_product_button.setEnabled(False)
        self.delete_product_button = QPushButton(self.tr("Delete Product"))
        self.delete_product_button.clicked.connect(self._delete_selected_product)
        self.delete_product_button.setEnabled(False)
        self.export_pdf_button = QPushButton(self.tr("Export to PDF"))
        self.export_pdf_button.clicked.connect(self.export_to_pdf_placeholder)

        top_controls_layout = QHBoxLayout()
        top_controls_layout.addWidget(self.add_product_button)
        top_controls_layout.addSpacing(5)
        top_controls_layout.addWidget(self.edit_product_button)
        top_controls_layout.addSpacing(5)
        top_controls_layout.addWidget(self.delete_product_button)
        top_controls_layout.addStretch()
        top_controls_layout.addWidget(self.export_pdf_button)
        main_layout.addLayout(top_controls_layout)
        main_layout.addSpacing(10) # Spacing after top_controls_layout

        # Filter Toggle Button
        filter_toggle_layout = QHBoxLayout()
        self.toggle_filters_button = QPushButton(self.tr("Hide Filters"))
        self.toggle_filters_button.setObjectName("toggleFiltersButton")
        self.toggle_filters_button.clicked.connect(self._toggle_filter_visibility)
        filter_toggle_layout.addWidget(self.toggle_filters_button)
        filter_toggle_layout.addStretch()
        main_layout.addLayout(filter_toggle_layout)
        # main_layout.addSpacing(5) # Optional spacing between toggle button and filter box

        # Filters Group Box
        self.filter_group_box = QGroupBox(self.tr("Filters")) # Changed to self.filter_group_box
        # self.filter_group_box.setContentsMargins(10, 15, 10, 10) # QSS already provides padding: 10px. Adjust top for title.
        filter_group_main_layout = QVBoxLayout(self.filter_group_box) # Main layout for the group box

        # filter_group_main_layout.setContentsMargins(5, 5, 5, 5) # Margins for the layout within the groupbox

        filter_search_layout = QHBoxLayout() # Layout for language, category, search

        # Language ComboBox
        self.language_combo = QComboBox()
        self.language_combo.addItems([self.tr("All Languages"), "fr", "en", "ar", "tr", "pt"])
        self.language_combo.setCurrentIndex(0)
        self.language_combo.currentIndexChanged.connect(self.apply_filters_and_reload)
        filter_search_layout.addWidget(QLabel(self.tr("Language:")))
        filter_search_layout.addWidget(self.language_combo)
        filter_search_layout.addSpacing(10)

        # Category Filter Input
        self.category_filter_input = QLineEdit()
        self.category_filter_input.setPlaceholderText(self.tr("Filter by category..."))
        self.category_filter_input.textChanged.connect(self.apply_filters_and_reload)
        filter_search_layout.addWidget(QLabel(self.tr("Category:")))
        filter_search_layout.addWidget(self.category_filter_input)
        filter_search_layout.addSpacing(10)

        # Search Product Input
        self.search_product_input = QLineEdit()
        self.search_product_input.setPlaceholderText(self.tr("Search by product name..."))
        self.search_product_input.textChanged.connect(self.apply_filters_and_reload)
        filter_search_layout.addWidget(QLabel(self.tr("Search Name:")))
        filter_search_layout.addWidget(self.search_product_input)

        filter_search_layout.addStretch()

        filter_group_main_layout.addLayout(filter_search_layout)
        filter_group_main_layout.addSpacing(5) # Spacing between filter_search_layout and checkbox

        # Include Deleted Checkbox
        self.include_deleted_checkbox = QCheckBox(self.tr("Include Deleted Products"))
        self.include_deleted_checkbox.stateChanged.connect(self.apply_filters_and_reload)
        filter_group_main_layout.addWidget(self.include_deleted_checkbox)

        main_layout.addWidget(self.filter_group_box) # Changed to self.filter_group_box

        main_layout.addSpacing(10) # Spacing after filter_group_box

        self.product_table = QTableWidget()
        self.product_table.setColumnCount(7)
        self.product_table.setHorizontalHeaderLabels([
            "ID", self.tr("Product Name"), self.tr("Description"), self.tr("Price"),
            self.tr("Language"), self.tr("Tech Specs"), self.tr("Translations")
        ])
        self.product_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.product_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.product_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.product_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.product_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.product_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.product_table.hideColumn(0)
        self.product_table.itemChanged.connect(self.handle_price_change)
        self.product_table.itemSelectionChanged.connect(self._update_button_states)
        self.product_table.itemDoubleClicked.connect(self._open_edit_product_dialog_from_item)
        main_layout.addWidget(self.product_table)

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

        # Removed old button_layout as buttons are now in top_controls_layout
        # main_layout.addLayout(button_layout) # This line is removed

        self.setLayout(main_layout)
        self.load_products_to_table()
        self._update_button_states()

    def _toggle_filter_visibility(self):
        if self.filter_group_box.isVisible():
            self.filter_group_box.setVisible(False)
            self.toggle_filters_button.setText(self.tr("Show Filters"))
            # Optionally, set icon for "show" state
            # self.toggle_filters_button.setIcon(QIcon(":/icons/chevron-right.svg")) # Example
        else:
            self.filter_group_box.setVisible(True)
            self.toggle_filters_button.setText(self.tr("Hide Filters"))
            # Optionally, set icon for "hide" state
            # self.toggle_filters_button.setIcon(QIcon(":/icons/chevron-down.svg")) # Example

    def _open_add_product_dialog(self):
        # Pass self as parent if ProductEditDialog expects a QWidget parent for modality or window management
        add_dialog = ProductEditDialog(product_id=None, parent=self)
        if add_dialog.exec_() == QDialog.Accepted:
            self.apply_filters_and_reload()

    def _open_edit_product_dialog(self):
        current_row = self.product_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, self.tr("No Selection"), self.tr("Please select a product to edit."))
            return
        product_id_item = self.product_table.item(current_row, 0)
        if product_id_item:
            try:
                product_id = int(product_id_item.text())
                edit_dialog = ProductEditDialog(product_id=product_id, parent=self)
                if edit_dialog.exec_() == QDialog.Accepted:
                    self.apply_filters_and_reload()
            except ValueError:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Invalid product ID format."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Error"), self.tr(f"An error occurred: {e}"))
        else:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Could not retrieve product ID for the selected row."))

    def _open_edit_product_dialog_from_item(self, item):
        if item: # Check if a valid item was double-clicked
            self._open_edit_product_dialog()

    def _update_button_states(self):
        has_selection = bool(self.product_table.selectedItems())
        self.edit_product_button.setEnabled(has_selection)
        self.delete_product_button.setEnabled(has_selection)

    def _delete_selected_product(self):
        current_row = self.product_table.currentRow()
        if current_row < 0: return # Should not happen if button state is managed
        product_id_item = self.product_table.item(current_row, 0)
        product_name_item = self.product_table.item(current_row, 1)
        if product_id_item and product_name_item:
            try:
                product_id = int(product_id_item.text())
                product_name = product_name_item.text()
                reply = QMessageBox.question(self, self.tr("Confirm Delete"),
                                             self.tr(f"Are you sure you want to delete product '{product_name}' (ID: {product_id})? This action will mark the product as deleted."),
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    delete_result = products_crud_instance.delete_product(product_id=product_id) # Using instance
                    if delete_result.get('success'):
                        QMessageBox.information(self, self.tr("Product Deleted"), self.tr("Product has been marked as deleted."))
                        self.apply_filters_and_reload()
                    else:
                        QMessageBox.critical(self, self.tr("Delete Failed"), delete_result.get('error', self.tr("Unknown error occurred.")))
            except ValueError: QMessageBox.critical(self, self.tr("Error"), self.tr("Invalid product ID format."))
            except Exception as e: QMessageBox.critical(self, self.tr("Error"), str(e))
        else: QMessageBox.warning(self, self.tr("Error"), self.tr("Could not retrieve product details for deletion."))

    def apply_filters_and_reload(self):
        self.current_offset = 0
        self.load_products_to_table()

    def load_products_to_table(self):
        self.product_table.blockSignals(True)
        self.product_table.setRowCount(0)
        lang_text = self.language_combo.currentText()
        language_code = None
        # Assuming language_combo stores "fr", "en" etc. in itemData if display text is translated
        if lang_text != self.tr("All Languages"):
            # A more robust way to get the code if display names are translated:
            # current_idx = self.language_combo.currentIndex()
            # language_code = self.language_combo.itemData(current_idx) if current_idx > 0 else None
            # For simplicity, using direct map if display names are fixed like "French", "English"
            lang_map = {"English": "en", "French": "fr", "Arabic": "ar", "Turkish": "tr", "Portuguese": "pt"}
            language_code = lang_map.get(lang_text) # Fallback if using direct text
            if not language_code and self.language_combo.currentIndex() > 0 : # if not found in map and not "All Languages"
                 language_code = self.language_combo.currentText() # assume "fr", "en" are directly in combo after "All"

        category_filter = self.category_filter_input.text().strip()
        search_name_filter = self.search_product_input.text().strip()
        include_deleted = self.include_deleted_checkbox.isChecked()
        filters = {}
        if language_code: filters['language_code'] = language_code
        if category_filter: filters['category'] = category_filter
        if search_name_filter: filters['product_name'] = f"%{search_name_filter}%"
        try:
            products = products_crud_instance.get_all_products(
                filters=filters, limit=self.limit_per_page, offset=self.current_offset, include_deleted=include_deleted
            )
            if products:
                self.product_table.setRowCount(len(products))
                for row, product_data in enumerate(products):
                    product_id = product_data.get("product_id")
                    id_item = QTableWidgetItem(str(product_id)); id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
                    self.product_table.setItem(row, 0, id_item)
                    name_item = QTableWidgetItem(product_data.get("product_name")); name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable); name_item.setData(Qt.UserRole, product_id)
                    self.product_table.setItem(row, 1, name_item)
                    desc_item = QTableWidgetItem(product_data.get("description")); desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
                    self.product_table.setItem(row, 2, desc_item)
                    price_val = product_data.get("base_unit_price"); price_str = f"{price_val:.2f}" if isinstance(price_val, (float, int)) else str(price_val)
                    price_item = QTableWidgetItem(price_str)
                    self.product_table.setItem(row, 3, price_item)
                    lang_code_val = product_data.get("language_code", ""); lang_item = QTableWidgetItem(lang_code_val); lang_item.setFlags(lang_item.flags() & ~Qt.ItemIsEditable)
                    self.product_table.setItem(row, 4, lang_item)
                    tech_specs_data = products_crud_instance.get_product_dimension(product_id)
                    has_tech_specs_bool = bool(tech_specs_data and (tech_specs_data.get('technical_image_path') or any(str(tech_specs_data.get(f'dim_{chr(ord("A")+i)}','')).strip() for i in range(10))))
                    tech_specs_indicator = self.tr("Yes") if has_tech_specs_bool else self.tr("No")
                    tech_specs_item = QTableWidgetItem(tech_specs_indicator); tech_specs_item.setFlags(tech_specs_item.flags() & ~Qt.ItemIsEditable)
                    self.product_table.setItem(row, 5, tech_specs_item)
                    equivalent_products = products_crud_instance.get_equivalent_products(product_id, include_deleted=False)
                    translations_count = len(equivalent_products) if equivalent_products else 0
                    translations_indicator = str(translations_count) if translations_count > 0 else self.tr("No")
                    translations_item = QTableWidgetItem(translations_indicator); translations_item.setFlags(translations_item.flags() & ~Qt.ItemIsEditable)
                    self.product_table.setItem(row, 6, translations_item)
            self.update_pagination_controls(len(products) if products else 0)
        except Exception as e:
            print(f"Error loading products to table: {e}")
            QMessageBox.critical(self, self.tr("Load Error"), self.tr(f"Failed to load products: {e}"))
        finally:
            self.product_table.blockSignals(False)
            self._update_button_states()

    def update_pagination_controls(self, current_page_item_count: int):
        self.prev_page_button.setEnabled(self.current_offset > 0)
        self.next_page_button.setEnabled(current_page_item_count == self.limit_per_page)
        self.page_info_label.setText(self.tr("Page {0}").format((self.current_offset // self.limit_per_page) + 1))

    def prev_page(self):
        if self.current_offset > 0:
            self.current_offset -= self.limit_per_page
            self.load_products_to_table()

    def next_page(self):
        if self.product_table.rowCount() == self.limit_per_page:
            self.current_offset += self.limit_per_page
            self.load_products_to_table()

    def handle_price_change(self, item):
        if item.column() == 3:
            row = item.row()
            # Try to get product_id from hidden ID column first
            id_item = self.product_table.item(row, 0)
            product_id = None
            if id_item:
                product_id = id_item.text() # ID is stored as text
                try:
                    product_id = int(product_id)
                except ValueError:
                    print(f"Invalid product_id in hidden column: {product_id}")
                    product_id = None

            if product_id is None: # Fallback to UserRole data on name item if ID column failed
                name_item_check = self.product_table.item(row,1) # Name column
                if name_item_check : product_id = name_item_check.data(Qt.UserRole)
                if product_id is None:
                    QMessageBox.warning(self, self.tr("Error"), self.tr("Could not determine product ID for price update."))
                    return

            new_price_str = item.text()
            try:
                new_price_float = float(new_price_str)
                if new_price_float < 0: raise ValueError(self.tr("Price cannot be negative."))
                self.product_table.blockSignals(True)
                update_result = products_crud_instance.update_product_price(product_id, new_price_float)
                if update_result['success']: item.setText(f"{new_price_float:.2f}")
                else:
                    QMessageBox.warning(self, self.tr("Update Failed"), update_result.get('error', self.tr("Failed to update price.")))
                    self.apply_filters_and_reload()
            except ValueError as ve:
                QMessageBox.warning(self, self.tr("Invalid Price"), str(ve))
                self.apply_filters_and_reload()
            finally:
                self.product_table.blockSignals(False)

    def export_to_pdf_placeholder(self):
        # Use self.title_edit.text() if it was kept, otherwise a fixed title or from parent.
        # For a page, title is often managed by the main window.
        # page_title = self.parent_window.windowTitle() if self.parent_window else self.tr("Product List")
        page_title_text = self.tr("Product List") # Default if self.title_edit was removed
        if hasattr(self, 'title_edit') and self.title_edit.text():
            page_title_text = self.title_edit.text()

        lang_text = self.language_combo.currentText(); language_code = None
        if lang_text != self.tr("All Languages"):
            lang_map = {"English": "en", "French": "fr", "Arabic": "ar", "Turkish": "tr", "Portuguese": "pt"}
            language_code = lang_map.get(lang_text)
            if not language_code and self.language_combo.currentIndex() > 0 :
                 language_code = self.language_combo.currentText()

        category_filter = self.category_filter_input.text().strip()
        search_name_filter = self.search_product_input.text().strip()
        include_deleted = self.include_deleted_checkbox.isChecked()
        filters = {};
        if language_code: filters['language_code'] = language_code
        if category_filter: filters['category'] = category_filter
        if search_name_filter: filters['product_name'] = f"%{search_name_filter}%"
        try:
            product_list_for_pdf = products_crud_instance.get_all_products(filters=filters, include_deleted=include_deleted, limit=None, offset=0) # Get all for PDF
            if not product_list_for_pdf:
                QMessageBox.information(self, self.tr("No Products"), self.tr("No products found for PDF export with current filters."))
                return

            for p_data in product_list_for_pdf:
                pid = p_data.get("product_id")
                p_data['language_code_display'] = p_data.get("language_code", "")
                tech_s_data = products_crud_instance.get_product_dimension(pid)
                has_tech_s_bool = bool(tech_s_data and (tech_s_data.get('technical_image_path') or any(str(tech_s_data.get(f'dim_{chr(ord("A")+i)}','')).strip() for i in range(10))))
                p_data['tech_specs_indicator'] = self.tr("Yes") if has_tech_s_bool else self.tr("No")
                equiv_prods = products_crud_instance.get_equivalent_products(pid, include_deleted=False)
                trans_count = len(equiv_prods) if equiv_prods else 0
                p_data['translations_indicator'] = str(trans_count) if trans_count > 0 else self.tr("No")

            html_template_string = '''
            <!DOCTYPE html><html><head><meta charset="UTF-8"><title>{{ title }}</title>
            <style>body{font-family:sans-serif;}table{width:100%;border-collapse:collapse;margin-top:20px;}th,td{border:1px solid #ddd;padding:8px;text-align:left;}th{background-color:#f2f2f2;}h1{text-align:center;}</style>
            </head><body><h1>{{ title }}</h1><table><thead><tr><th>Product Name</th><th>Description</th><th>Price</th><th>Language</th><th>Tech Specs</th><th>Translations</th></tr></thead>
            <tbody>{{#each products}}<tr><td>{{this.product_name}}</td><td>{{this.description}}</td><td>{{this.base_unit_price}}</td><td>{{this.language_code_display}}</td><td>{{this.tech_specs_indicator}}</td><td>{{this.translations_indicator}}</td></tr>{{/each}}
            {{#if products_empty}}<tr><td colspan="6" style="text-align:center;">No products to display.</td></tr>{{/if}}
            </tbody></table></body></html>'''
            context = {'title': page_title_text, 'products': product_list_for_pdf, 'products_empty': not bool(product_list_for_pdf)}
            rendered_html = html_to_pdf_util.render_html_template(html_template_string, context)
            # Use QFileDialog.getSaveFileName from self, not QFileDialog directly if possible for parent linkage
            file_path, _ = QFileDialog.getSaveFileName(self, self.tr("Save PDF"), "", self.tr("PDF Files (*.pdf);;All Files (*)"), options=QFileDialog.DontUseNativeDialog)
            if file_path:
                if not file_path.lower().endswith(".pdf"): file_path += ".pdf"
                pdf_bytes = html_to_pdf_util.convert_html_to_pdf(rendered_html)
                if pdf_bytes:
                    with open(file_path, "wb") as f: f.write(pdf_bytes)
                    QMessageBox.information(self, self.tr("Export Successful"), self.tr(f"Product list exported successfully to: {file_path}"))
                else: QMessageBox.critical(self, self.tr("Export Failed"), self.tr("Failed to generate PDF content."))
        except Exception as e:
            print(f"Error during PDF export: {e}") # Log to console
            QMessageBox.critical(self, self.tr("Export Error"), self.tr(f"An error occurred during PDF export: {e}"))

    def refresh_view(self):
        """Public method to refresh the product list, callable from main window if needed."""
        self.apply_filters_and_reload()
        print("ProductManagementPage view refreshed.")


