# product_edit_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QCheckBox, QListWidget, QListWidgetItem, QMessageBox, QFileDialog,
    QInputDialog, QGroupBox, QScrollArea, QGridLayout, QComboBox, QWidget, QTabWidget
)
from PyQt5.QtCore import Qt, QSize

from PyQt5.QtGui import QPixmap, QIcon

# Assuming db.cruds is accessible. Adjust import path if necessary.
# Example: from ..db.cruds import products_crud, product_media_links_crud
# For this subtask, direct import if files are in expected locations.
from db.cruds import products_crud
from db.cruds import product_media_links_crud
from media_manager import operations as media_ops
from db.cruds.users_crud import get_user_by_username # To get a placeholder uploader_id
import asyncio # For running async functions
from config import MEDIA_FILES_BASE_PATH # For resolving image paths
import os
import shutil # Added for file copying

SUPPORTED_LANGUAGES = [
    ("English", "en"),
    ("French", "fr"),
    ("Arabic", "ar"),
    ("Turkish", "tr"),
    ("Spanish", "es")
]


class SelectProductDialog(QDialog):
    """
    A dialog for searching and selecting a product.
    Used for linking equivalent products.
    """
    def __init__(self, current_product_id, parent=None):
        super().__init__(parent)
        self.current_product_id = current_product_id # To exclude from search results
        self.setWindowTitle(self.tr("Select Equivalent Product"))
        self.setGeometry(200, 200, 500, 400) # Initial size, can be adjusted
        self.selected_product_id = None

        layout = QVBoxLayout(self)

        # Search area
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Search by Name, ID, or Category..."))
        self.search_input.returnPressed.connect(self._perform_search)
        search_layout.addWidget(self.search_input)
        search_button = QPushButton(self.tr("Search"))
        search_button.clicked.connect(self._perform_search)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)

        # Results list
        self.results_list = QListWidget()
        self.results_list.setSelectionMode(QListWidget.SingleSelection)
        self.results_list.itemSelectionChanged.connect(self._update_ok_button_state)
        self.results_list.itemDoubleClicked.connect(self._confirm_selection)
        layout.addWidget(self.results_list)

        # Action buttons
        action_buttons = QHBoxLayout()
        self.ok_button = QPushButton(self.tr("OK"))
        self.ok_button.setEnabled(False) # Disabled until an item is selected
        self.ok_button.clicked.connect(self._confirm_selection)
        cancel_button = QPushButton(self.tr("Cancel"))
        cancel_button.clicked.connect(self.reject)
        action_buttons.addStretch()
        action_buttons.addWidget(self.ok_button)
        action_buttons.addWidget(cancel_button)
        layout.addLayout(action_buttons)

        self.setLayout(layout)

    def _perform_search(self):
        search_term = self.search_input.text().strip()
        self.results_list.clear()
        self.ok_button.setEnabled(False) # Disable OK button during search

        if not search_term:
            # self.results_list.addItem(self.tr("Enter a search term to find products."))
            return

        try:
            # Attempt to search by ID if term is an integer
            search_filter = {}
            try:
                potential_id = int(search_term)
                search_filter = {'product_id': potential_id, 'is_active': True}
            except ValueError:
                 # If not an integer, search by name or category (assuming CRUD supports this)
                 # For simplicity, using product_name for now. A more complex filter may be needed.
                search_filter = {'product_name_like': f"%{search_term}%", 'is_active': True}


            # products = products_crud.get_all_products(filters={'product_name': f"%{search_term}%", 'is_active': True}, limit=100)
            # The filter key 'product_name_like' is hypothetical.
            # Adjust based on actual products_crud.get_all_products capabilities.
            # For now, let's assume get_all_products can take a general search term
            # and the CRUD implementation handles how to search (e.g. name, category)
            # This is a simplification. A robust solution might need specific filter keys.

            # Let's try a more generic approach if product_name_like isn't standard
            # We will fetch based on name and then ID if search term is numeric

            products_found = []
            if search_filter.get('product_id'):
                prod_by_id = products_crud.get_product_by_id(search_filter['product_id'])
                if prod_by_id and prod_by_id.get('is_active'): # Check is_active for consistency
                    products_found.append(prod_by_id)

            # Search by name (could be refined to also search category etc. by products_crud)
            # Assuming get_all_products with `product_name` filter does a LIKE search.
            # If not, this needs adjustment or a new CRUD method.
            name_filter = {'product_name': f"%{search_term}%", 'is_active': True}
            products_by_name = products_crud.get_all_products(filters=name_filter, limit=50)
            if products_by_name:
                # Avoid duplicates if ID search already found it
                ids_found_by_id_search = {p['product_id'] for p in products_found}
                for p_name in products_by_name:
                    if p_name['product_id'] not in ids_found_by_id_search:
                        products_found.append(p_name)


            if not products_found:
                self.results_list.addItem(self.tr("No products found matching your search."))
                return

            for product in products_found:
                if product.get('product_id') == self.current_product_id: # Exclude current product
                    continue
                display_text = f"{product.get('product_name', 'N/A')} (ID: {product.get('product_id')}, Lang: {product.get('language_code', 'N/A')})"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, product.get('product_id'))
                self.results_list.addItem(item)
        except Exception as e:
            print(f"Error during product search: {e}")
            QMessageBox.critical(self, self.tr("Search Error"), self.tr(f"An error occurred during search: {e}"))
            # Using print for server-side/console logging of the error is acceptable here.
            # The QMessageBox handles user-facing feedback.
            # print(f"Error during product search: {e}")
            self.results_list.addItem(self.tr("Error during search. Check logs."))


    def _update_ok_button_state(self):
        """Enables or disables the OK button based on item selection in the results list."""
        self.ok_button.setEnabled(bool(self.results_list.selectedItems()))

    def _confirm_selection(self):
        """Confirms the selection of a product from the list and closes the dialog."""
        selected_items = self.results_list.selectedItems()
        if selected_items:
            self.selected_product_id = selected_items[0].data(Qt.UserRole)
            self.accept()
        else:
            # This case should ideally not be reached if OK button is properly disabled by _update_ok_button_state
            QMessageBox.warning(self, self.tr("No Selection"), self.tr("Please select a product from the list."))


class ProductEditDialog(QDialog):
    """
    Dialog for adding a new product or editing an existing one.
    Manages product details, images, technical specifications, and equivalencies.
    """
    def __init__(self, product_id, parent=None):
        super().__init__(parent)
        self.product_id = product_id # None for new product, existing ID for edit
        self.setWindowTitle(self.tr("Edit Product")) # Title will be updated if it's a new product
        self.setGeometry(150, 150, 750, 800)

        self.db_product_data = None # Stores initially loaded product data for comparison or reference
        self.db_tech_specs_data = None # Stores initially loaded tech specs data
        self.equivalent_products = [] # To store equivalent products
        self.media_links = [] # To store loaded media links

        # Main scroll area
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        main_widget_for_scroll = QWidget()
        layout_on_main_widget = QVBoxLayout(main_widget_for_scroll) # Renamed main_layout for clarity

        # --- Create TabWidget and Tab Pages ---
        self.tab_widget = QTabWidget()

        # Basic Information Tab
        self.basic_info_tab = QWidget()
        basic_info_layout = QVBoxLayout(self.basic_info_tab)
        form_layout = QFormLayout() # This is for basic product data
        self.name_edit = QLineEdit()
        self.product_code_edit = QLineEdit() # Added product_code field
        self.description_edit = QTextEdit()
        self.description_edit.setFixedHeight(80)
        self.category_edit = QLineEdit()

        if self.product_id is None: # New product
            self.language_code_combo = QComboBox()
            for lang_name, lang_code in SUPPORTED_LANGUAGES:
                self.language_code_combo.addItem(self.tr(lang_name), lang_code)
            form_layout.addRow(self.tr("Language Code:"), self.language_code_combo)
            self.language_code_edit = None # No QLineEdit if new
        else: # Existing product
            self.language_code_edit = QLineEdit()
            self.language_code_edit.setReadOnly(True)
            form_layout.addRow(self.tr("Language Code:"), self.language_code_edit)
            self.language_code_combo = None # No QComboBox if editing

        self.price_edit = QLineEdit()
        self.unit_edit = QLineEdit()
        self.weight_edit = QLineEdit()
        self.dimensions_edit = QLineEdit()
        self.is_active_check = QCheckBox(self.tr("Is Active"))

        form_layout.addRow(self.tr("Name:"), self.name_edit)
        form_layout.addRow(self.tr("Product Code (SDK):"), self.product_code_edit) # Added product_code field
        form_layout.addRow(self.tr("Description:"), self.description_edit)
        form_layout.addRow(self.tr("Category:"), self.category_edit)
        form_layout.addRow(self.tr("Base Unit Price:"), self.price_edit)
        form_layout.addRow(self.tr("Unit of Measure:"), self.unit_edit)
        form_layout.addRow(self.tr("Weight:"), self.weight_edit)
        form_layout.addRow(self.tr("Dimensions:"), self.dimensions_edit)
        form_layout.addRow(self.is_active_check)
        basic_info_layout.addLayout(form_layout) # Add form_layout to basic_info_tab's layout

        # Images Tab
        self.images_tab = QWidget()
        images_layout = QVBoxLayout(self.images_tab)
        self.gallery_group = QGroupBox(self.tr("Product Images")) # Changed to self.gallery_group
        gallery_layout = QVBoxLayout(self.gallery_group)
        self.image_gallery_list = QListWidget()
        self.image_gallery_list.setFixedHeight(150)
        gallery_layout.addWidget(self.image_gallery_list)
        image_buttons_layout = QHBoxLayout()
        self.add_image_button = QPushButton(self.tr("Add Image..."))
        self.add_image_button.clicked.connect(self._add_image)
        self.remove_image_button = QPushButton(self.tr("Remove Selected Image"))
        self.remove_image_button.clicked.connect(self._remove_image)
        self.edit_image_button = QPushButton(self.tr("Edit Image Details..."))
        self.edit_image_button.clicked.connect(self._edit_image_details)

        self.move_image_up_button = QPushButton(self.tr("Move Up"))
        self.move_image_up_button.clicked.connect(self._move_image_up)
        self.move_image_down_button = QPushButton(self.tr("Move Down"))
        self.move_image_down_button.clicked.connect(self._move_image_down)

        image_buttons_layout = QHBoxLayout()
        self.add_image_button = QPushButton(self.tr("Add Image..."))
        self.add_image_button.clicked.connect(self._add_image)
        self.remove_image_button = QPushButton(self.tr("Remove Selected Image"))
        self.remove_image_button.clicked.connect(self._remove_image)
        self.edit_image_button = QPushButton(self.tr("Edit Image Details..."))
        self.edit_image_button.clicked.connect(self._edit_image_details)
        self.move_image_up_button = QPushButton(self.tr("Move Up"))
        self.move_image_up_button.clicked.connect(self._move_image_up)
        self.move_image_down_button = QPushButton(self.tr("Move Down"))
        self.move_image_down_button.clicked.connect(self._move_image_down)
        image_buttons_layout.addWidget(self.add_image_button)
        image_buttons_layout.addWidget(self.remove_image_button)
        image_buttons_layout.addWidget(self.edit_image_button)
        image_buttons_layout.addSpacing(20)
        image_buttons_layout.addWidget(self.move_image_up_button)
        image_buttons_layout.addWidget(self.move_image_down_button)
        image_buttons_layout.addStretch()
        gallery_layout.addLayout(image_buttons_layout)
        images_layout.addWidget(self.gallery_group) # Add to images_tab's layout

        # Technical Specifications Tab
        self.tech_specs_tab = QWidget()
        tech_specs_layout_for_tab = QVBoxLayout(self.tech_specs_tab) # Use QVBoxLayout for the tab page
        self.tech_specs_group = QGroupBox(self.tr("Technical Specifications")) # Changed to self.tech_specs_group
        tech_specs_form_layout = QFormLayout(self.tech_specs_group) # Original QFormLayout for the group's content
        self.dim_A_edit = QLineEdit()
        self.dim_B_edit = QLineEdit()
        self.dim_C_edit = QLineEdit()
        self.dim_D_edit = QLineEdit()
        self.dim_E_edit = QLineEdit()
        self.dim_F_edit = QLineEdit()
        self.dim_G_edit = QLineEdit()
        self.dim_H_edit = QLineEdit()
        self.dim_I_edit = QLineEdit()
        self.dim_J_edit = QLineEdit()
        tech_specs_form_layout.addRow("Dimension A:", self.dim_A_edit)
        tech_specs_form_layout.addRow("Dimension B:", self.dim_B_edit)
        tech_specs_form_layout.addRow("Dimension C:", self.dim_C_edit)
        tech_specs_form_layout.addRow("Dimension D:", self.dim_D_edit)
        tech_specs_form_layout.addRow("Dimension E:", self.dim_E_edit)
        tech_specs_form_layout.addRow("Dimension F:", self.dim_F_edit)
        tech_specs_form_layout.addRow("Dimension G:", self.dim_G_edit)
        tech_specs_form_layout.addRow("Dimension H:", self.dim_H_edit)
        tech_specs_form_layout.addRow("Dimension I:", self.dim_I_edit)
        tech_specs_form_layout.addRow("Dimension J:", self.dim_J_edit)

        tech_image_layout = QHBoxLayout()
        self.tech_image_path_edit = QLineEdit()
        self.tech_image_path_edit.setReadOnly(True)
        self.browse_tech_image_button = QPushButton(self.tr("Browse..."))
        self.browse_tech_image_button.clicked.connect(self._browse_technical_image)
        tech_image_layout.addWidget(self.tech_image_path_edit)
        tech_image_layout.addWidget(self.browse_tech_image_button)
        tech_specs_form_layout.addRow(self.tr("Technical Image:"), tech_image_layout)
        tech_specs_layout_for_tab.addWidget(self.tech_specs_group) # Add to tech_specs_tab's layout

        # Translations/Equivalencies Tab
        self.translations_tab = QWidget()
        translations_layout = QVBoxLayout(self.translations_tab)
        self.equivalencies_group = QGroupBox(self.tr("Translations / Equivalent Products")) # Changed to self.equivalencies_group
        equivalencies_main_layout = QVBoxLayout(self.equivalencies_group)
        self.equivalencies_list = QListWidget()
        self.equivalencies_list.setFixedHeight(100)
        equivalencies_main_layout.addWidget(self.equivalencies_list)
        equiv_buttons_layout = QHBoxLayout()
        self.add_equivalence_button = QPushButton(self.tr("Add Translation..."))
        self.add_equivalence_button.clicked.connect(self._add_product_equivalence)
        self.remove_equivalence_button = QPushButton(self.tr("Remove Selected Translation"))
        self.remove_equivalence_button.clicked.connect(self._remove_product_equivalence)
        equiv_buttons_layout.addWidget(self.add_equivalence_button)
        equiv_buttons_layout.addWidget(self.remove_equivalence_button)
        equiv_buttons_layout.addStretch()
        equivalencies_main_layout.addLayout(equiv_buttons_layout)
        translations_layout.addWidget(self.equivalencies_group) # Add to translations_tab's layout

        # Add Tabs to TabWidget
        self.tab_widget.addTab(self.basic_info_tab, self.tr("Basic Information"))
        self.tab_widget.addTab(self.images_tab, self.tr("Images"))
        self.tab_widget.addTab(self.tech_specs_tab, self.tr("Technical Specifications"))
        self.tab_widget.addTab(self.translations_tab, self.tr("Translations"))

        layout_on_main_widget.addWidget(self.tab_widget) # Add tab_widget to the layout on main_widget_for_scroll

        # Dialog Action Buttons (remain outside the tab_widget and scroll area)
        self.action_buttons_layout = QHBoxLayout() # Make it self. for consistent access if needed
        self.save_button = QPushButton(self.tr("Save Changes"))
        self.save_button.clicked.connect(self._save_changes)
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.clicked.connect(self.reject)
        self.action_buttons_layout.addStretch()
        self.action_buttons_layout.addWidget(self.save_button)
        self.action_buttons_layout.addWidget(self.cancel_button)
        # main_layout.addLayout(self.action_buttons_layout) # This was added to layout_on_main_widget before

        scroll_area.setWidget(main_widget_for_scroll)

        outer_layout = QVBoxLayout(self) # This is the dialog's actual layout
        outer_layout.addWidget(scroll_area)
        outer_layout.addLayout(self.action_buttons_layout) # Action buttons are part of outer_layout now
        self.setLayout(outer_layout) # Set the dialog's layout

        self.load_product_data() # This will set initial button text and combo state
        self._update_ui_for_product_id_state() # This will set tab enabled states

        if self.product_id is None:
            # self.save_button.setText(self.tr("Save and Continue")) # Already handled by load_product_data
            self.tab_widget.setCurrentWidget(self.basic_info_tab)
        else:
            self.save_button.setText(self.tr("Save Changes"))


    def _update_ui_for_product_id_state(self):
        """Enable/disable tabs based on whether product_id exists."""
        has_product_id = self.product_id is not None
        # Tab indices: Basic Info (0), Images (1), Tech Specs (2), Translations (3)
        # Basic Info tab (index 0) is always enabled.
        self.tab_widget.setTabEnabled(1, has_product_id)  # Images tab
        self.tab_widget.setTabEnabled(2, has_product_id)  # Tech Specs tab
        self.tab_widget.setTabEnabled(3, has_product_id)  # Translations tab

        # Also ensure the group boxes themselves are enabled/disabled if they are not part of the tab's own enabled state
        # However, setTabEnabled should handle this for child widgets.
        # If direct control is still needed (e.g., for visual cues not handled by tab disabling):
        if hasattr(self, 'gallery_group'): self.gallery_group.setEnabled(has_product_id)
        if hasattr(self, 'tech_specs_group'): self.tech_specs_group.setEnabled(has_product_id)
        if hasattr(self, 'equivalencies_group'): self.equivalencies_group.setEnabled(has_product_id)


    def load_product_data(self):
        """
        Loads product data into the dialog fields.
        If self.product_id is None, sets up the dialog for a new product.
        Otherwise, fetches and displays data for the existing product.
        """
        if self.product_id is None: # New product mode
            self.setWindowTitle(self.tr("Add New Product"))
            self.save_button.setText(self.tr("Save and Continue"))
            if self.language_code_combo:
                self.language_code_combo.setEnabled(True)
            # Clear fields for new product entry
            self.name_edit.clear()
            self.product_code_edit.clear() # Added product_code field
            self.description_edit.clear()
            self.category_edit.clear()
            if self.language_code_combo: # If it's a new product, combo is used
                self.language_code_combo.setCurrentIndex(0) # Default to first language
            elif self.language_code_edit: # Should not happen if product_id is None
                 self.language_code_edit.clear()
            self.price_edit.clear()
            self.unit_edit.clear()
            self.weight_edit.clear()
            self.dimensions_edit.clear()
            self.is_active_check.setChecked(True) # Default to active

            # Clear tech specs fields
            self.dim_A_edit.clear(); self.dim_B_edit.clear(); self.dim_C_edit.clear(); self.dim_D_edit.clear();
            self.dim_E_edit.clear(); self.dim_F_edit.clear(); self.dim_G_edit.clear(); self.dim_H_edit.clear();
            self.dim_I_edit.clear(); self.dim_J_edit.clear();
            self.tech_image_path_edit.clear();

            self.media_links = []
            self._populate_image_gallery()
            self.equivalent_products = []
            self._populate_equivalencies_list()
            # _update_ui_for_product_id_state() will be called after this in __init__
            return

        # Existing product
        self.save_button.setText(self.tr("Save Changes"))
        if self.language_code_combo: # Should not exist for existing, but good practice
            self.language_code_combo.setEnabled(False)

        self.db_product_data = products_crud.get_product_by_id(self.product_id)

        if not self.db_product_data:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Product not found."))
            self.reject() # Close dialog if product not found
            return

        self.name_edit.setText(self.db_product_data.get('product_name', ''))
        self.product_code_edit.setText(self.db_product_data.get('product_code', '')) # Added product_code field
        self.description_edit.setPlainText(self.db_product_data.get('description', ''))
        self.category_edit.setText(self.db_product_data.get('category', ''))

        # Handle language_code display based on whether it's a QLineEdit or QComboBox scenario
        # This method is called for existing products, so language_code_edit should be active
        if self.language_code_edit:
            self.language_code_edit.setText(self.db_product_data.get('language_code', ''))
        # If it were a combo (which it isn't for existing products as per current __init__ logic):
        # elif self.language_code_combo:
        #     lang_code_to_set = self.db_product_data.get('language_code', '')
        #     index = self.language_code_combo.findData(lang_code_to_set)
        #     if index >= 0:
        #         self.language_code_combo.setCurrentIndex(index)

        self.price_edit.setText(str(self.db_product_data.get('base_unit_price', '')))
        self.unit_edit.setText(self.db_product_data.get('unit_of_measure', ''))
        self.weight_edit.setText(str(self.db_product_data.get('weight', '')))
        self.dimensions_edit.setText(self.db_product_data.get('dimensions', '')) # This is general dimensions
        self.is_active_check.setChecked(self.db_product_data.get('is_active', True))

        self.media_links = self.db_product_data.get('media_links', []) # Assuming media_links are part of product data
        self._populate_image_gallery()

        # Load Technical Specifications
        self.db_tech_specs_data = products_crud.get_product_dimension(self.product_id) # conn=None is default
        if self.db_tech_specs_data:
            self.dim_A_edit.setText(str(self.db_tech_specs_data.get('dim_A', '')))
            self.dim_B_edit.setText(str(self.db_tech_specs_data.get('dim_B', '')))
            self.dim_C_edit.setText(str(self.db_tech_specs_data.get('dim_C', '')))
            self.dim_D_edit.setText(str(self.db_tech_specs_data.get('dim_D', '')))
            self.dim_E_edit.setText(str(self.db_tech_specs_data.get('dim_E', '')))
            self.dim_F_edit.setText(str(self.db_tech_specs_data.get('dim_F', '')))
            self.dim_G_edit.setText(str(self.db_tech_specs_data.get('dim_G', '')))
            self.dim_H_edit.setText(str(self.db_tech_specs_data.get('dim_H', '')))
            self.dim_I_edit.setText(str(self.db_tech_specs_data.get('dim_I', '')))
            self.dim_J_edit.setText(str(self.db_tech_specs_data.get('dim_J', '')))
            self.tech_image_path_edit.setText(self.db_tech_specs_data.get('technical_image_path', ''))
        else:
            # Clear fields if no tech specs found
            self.dim_A_edit.clear(); self.dim_B_edit.clear(); self.dim_C_edit.clear(); self.dim_D_edit.clear();
            self.dim_E_edit.clear(); self.dim_F_edit.clear(); self.dim_G_edit.clear(); self.dim_H_edit.clear();
            self.dim_I_edit.clear(); self.dim_J_edit.clear();
            self.tech_image_path_edit.clear();

        # Load Product Equivalencies
        # We need equivalence_id for removal, so get_all_product_equivalencies is better
        all_equivalencies = products_crud.get_all_product_equivalencies(product_id_filter=self.product_id)
        self.equivalent_products = [] # Reset
        if all_equivalencies:
            for eq_link in all_equivalencies:
                # Determine the "other" product ID in the link
                other_product_id = None
                if eq_link.get('product_id_a') == self.product_id:
                    other_product_id = eq_link.get('product_id_b')
                elif eq_link.get('product_id_b') == self.product_id:
                    other_product_id = eq_link.get('product_id_a')

                if other_product_id:
                    # Fetch details of the other product
                    eq_prod_details = products_crud.get_product_by_id(other_product_id)
                    if eq_prod_details:
                        # Add the equivalence_id to the details for use in removal
                        eq_prod_details['equivalence_id'] = eq_link.get('equivalence_id')
                        self.equivalent_products.append(eq_prod_details)

        self._populate_equivalencies_list()
        self._update_ui_for_product_id_state() # Ensure sections are enabled

    def _populate_equivalencies_list(self):
        self.equivalencies_list.clear()
        if not self.equivalent_products:
            self.equivalencies_list.addItem(self.tr("No equivalent products linked."))
            return

        for eq_prod in self.equivalent_products:
            display_text = f"{eq_prod.get('product_name', 'N/A')} ({eq_prod.get('language_code', 'N/A')}) - ID: {eq_prod.get('product_id')}"
            item = QListWidgetItem(display_text)
            # Store both product_id of the equivalent and the equivalence_id for removal
            item.setData(Qt.UserRole, {"equivalent_product_id": eq_prod.get('product_id'),
                                       "equivalence_id": eq_prod.get('equivalence_id')})
            self.equivalencies_list.addItem(item)

    def _populate_image_gallery(self):
        self.image_gallery_list.clear()

        # Configure QListWidget for icon display
        self.image_gallery_list.setViewMode(QListWidget.IconMode)
        self.image_gallery_list.setIconSize(QSize(100, 100)) # Thumbnail size
        self.image_gallery_list.setResizeMode(QListWidget.Adjust) # Adjust layout on resize
        self.image_gallery_list.setMovement(QListWidget.Static) # Prevent dragging by default, can change if reordering via D&D
        self.image_gallery_list.setSpacing(10) # Spacing between items

        if not self.media_links:
            # Create a placeholder item if no images
            placeholder_item = QListWidgetItem(self.tr("No images linked."))
            # placeholder_item.setIcon(QIcon("path/to/default/no_image_icon.png")) # Optional: set a default icon
            self.image_gallery_list.addItem(placeholder_item)
            return

        for link in sorted(self.media_links, key=lambda x: x.get('display_order', 0)):
            item_text = f"{link.get('media_title', os.path.basename(link.get('media_filepath', 'N/A')))}"
            # Optionally add alt text or order to item_text if needed under icon
            # item_text += f"\nOrder: {link.get('display_order')}" # Example if text under icon is desired

            list_item = QListWidgetItem(item_text)
            list_item.setData(Qt.UserRole, link) # Store the whole link dict for later use

            icon_to_set = QIcon() # Default empty icon

            path_to_try = None
            if link.get('media_thumbnail_path'):
                path_to_try = os.path.join(MEDIA_FILES_BASE_PATH, link['media_thumbnail_path'])
            elif link.get('media_filepath'): # Fallback to main image if no thumbnail
                path_to_try = os.path.join(MEDIA_FILES_BASE_PATH, link['media_filepath'])

            if path_to_try and os.path.exists(path_to_try):
                pixmap = QPixmap(path_to_try)
                if not pixmap.isNull():
                    # Scale pixmap to fit icon size while maintaining aspect ratio for IconMode
                    # This is mostly handled by setIconSize, but for QListWidget.IconMode,
                    # text is often below. If using custom delegate, more control is possible.
                    icon_to_set = QIcon(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                # else: # Debugging print, remove for production
                    # print(f"Warning: Could not load QPixmap for {path_to_try}")
            # else: # Debugging print, remove for production
                # print(f"Warning: Image/Thumbnail file not found at {path_to_try}")
                # Optionally set a "file not found" or placeholder icon
                # icon_to_set = QIcon(":/icons/placeholder_icon.svg") # Example

            list_item.setIcon(icon_to_set)
            list_item.setToolTip(f"Path: {link.get('media_filepath', self.tr('N/A'))}\nAlt: {link.get('alt_text', self.tr('None'))}")
            self.image_gallery_list.addItem(list_item)

    def _save_changes(self):
        # --- Gather data from UI fields ---
        try:
            product_name = self.name_edit.text().strip()
            if not product_name:
                QMessageBox.warning(self, self.tr("Validation Error"), self.tr("Product name cannot be empty."))
                return

            product_code = self.product_code_edit.text().strip() # Added product_code field
            if not product_code: # Added product_code field validation
                QMessageBox.warning(self, self.tr("Validation Error"), self.tr("Product code cannot be empty."))
                return

            description = self.description_edit.toPlainText().strip()
            category = self.category_edit.text().strip()

            if self.product_id is None and self.language_code_combo: # New product
                language_code = self.language_code_combo.currentData()
            elif self.language_code_edit : # Existing product
                language_code = self.language_code_edit.text().strip()
            else: # Fallback or error
                QMessageBox.critical(self, self.tr("Error"), self.tr("Could not determine language code."))
                return


            base_unit_price_str = self.price_edit.text().strip()
            base_unit_price = None
            if base_unit_price_str:
                try:
                    base_unit_price = float(base_unit_price_str)
                    if base_unit_price < 0:
                        QMessageBox.warning(self, self.tr("Validation Error"), self.tr("Base unit price cannot be negative."))
                        return
                except ValueError:
                    QMessageBox.warning(self, self.tr("Validation Error"), self.tr("Invalid base unit price format."))
                    return

            unit_of_measure = self.unit_edit.text().strip()

            weight_str = self.weight_edit.text().strip()
            weight = None
            if weight_str:
                try:
                    weight = float(weight_str)
                    if weight < 0:
                         QMessageBox.warning(self, self.tr("Validation Error"), self.tr("Weight cannot be negative."))
                         return
                except ValueError:
                    QMessageBox.warning(self, self.tr("Validation Error"), self.tr("Invalid weight format."))
                    return

            dimensions = self.dimensions_edit.text().strip() # General dimensions
            is_active = self.is_active_check.isChecked()

        except Exception as e:
            QMessageBox.critical(self, self.tr("Error Reading Input"), self.tr(f"An error occurred while reading product data: {e}"))
            return

        updated_product_data = {
            'product_name': product_name,
            'product_code': product_code, # Added product_code field
            'description': description,
            'category': category,
            'language_code': language_code,
            'base_unit_price': base_unit_price,
            'unit_of_measure': unit_of_measure,
            'weight': weight,
            'dimensions': dimensions, # General dimensions
            'is_active': is_active
        }

        product_saved_successfully = False
        new_product_created_id = None

        if self.product_id is not None: # Editing existing product
            try:
                success = products_crud.update_product(product_id=self.product_id, data=updated_product_data)
                if success:
                    # QMessageBox.information(self, self.tr("Success"), self.tr("Product details saved successfully."))
                    product_saved_successfully = True
                    # self.accept() # Close the dialog - moved to end
                else:
                    check_prod = products_crud.get_product_by_id(self.product_id)
                    if not check_prod:
                         QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to save product details. The product may have been deleted."))
                    else:
                         QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to save product details. Please check data and try again."))
            except Exception as e:
                # print(f"Error updating product {self.product_id}: {e}") # Debugging
                QMessageBox.critical(self, self.tr("Database Error"), self.tr("An error occurred while saving product details: {str(e)}"))
        else: # Adding new product
            try:
                new_id = products_crud.add_product(product_data=updated_product_data)
                if new_id:
                    self.product_id = new_id
                    new_product_created_id = new_id # Keep track of new ID
                    self.setWindowTitle(self.tr("Edit Product") + f" (ID: {new_id})")
                    # QMessageBox.information(self, self.tr("Success"),
                    #                         self.tr(f"Product '{product_name}' added successfully with ID {new_id}. You can now manage other details."))
                    product_saved_successfully = True
                    self.save_button.setText(self.tr("Save Changes"))
                    if self.language_code_combo:
                        self.language_code_combo.setEnabled(False)
                        # The visual change from QComboBox to QLineEdit for language
                        # is complex to do dynamically here. The current __init__ logic
                        # handles this based on product_id presence, so a re-instantiation
                        # or a more complex UI rebuild for that specific row would be needed.
                        # For now, disabling the combo is the key functional change.

                    self.load_product_data() # Reload to ensure consistency
                    self._update_ui_for_product_id_state() # Enable tabs
                    self.tab_widget.setCurrentWidget(self.images_tab)
                else:
                    QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to add new product."))
            except Exception as e:
                # print(f"Error adding new product: {e}") # Debugging
                QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"An error occurred while adding product: {str(e)}"))

        if product_saved_successfully and self.product_id is not None:
            # Save Technical Specifications (if product was saved or newly created)
            tech_spec_data = {
                'dim_A': self.dim_A_edit.text() or None, 'dim_B': self.dim_B_edit.text() or None,
                'dim_C': self.dim_C_edit.text() or None, 'dim_D': self.dim_D_edit.text() or None,
                'dim_E': self.dim_E_edit.text() or None, 'dim_F': self.dim_F_edit.text() or None,
                'dim_G': self.dim_G_edit.text() or None, 'dim_H': self.dim_H_edit.text() or None,
                'dim_I': self.dim_I_edit.text() or None, 'dim_J': self.dim_J_edit.text() or None,
                'technical_image_path': self.tech_image_path_edit.text() or None
            }
            # Filter out keys where value is None if CRUD expects only changed fields
            # For add_or_update, sending None should be fine to clear fields

            try:
                tech_spec_success = products_crud.add_or_update_product_dimension(self.product_id, tech_spec_data)
                if not tech_spec_success:
                    QMessageBox.warning(self, self.tr("Tech Spec Save Warning"), self.tr("Could not save technical specifications. Product core data was saved."))
                # else: # Debugging print, remove for production
                    # print(f"Technical specifications for product ID {self.product_id} saved.")
            except Exception as e:
                # print(f"Error saving technical specifications for product {self.product_id}: {e}") # Debugging
                QMessageBox.critical(self, self.tr("Tech Spec Error"), self.tr(f"An error occurred while saving technical specifications: {str(e)}"))

            # Equivalencies (Translations) are handled by their own buttons directly through the UI.
            # No explicit save step here for equivalencies.

            if new_product_created_id: # If it was a new product
                 QMessageBox.information(self, self.tr("Product Added"),
                                        self.tr(f"Product '{updated_product_data['product_name']}' (ID: {new_product_created_id}) and its details have been saved."))
                 # Keep dialog open for further edits (images, etc.)
            else: # Existing product updated
                 QMessageBox.information(self, self.tr("Product Updated"), self.tr("Product and its details have been updated successfully."))
                 self.accept()

        # elif product_saved_successfully and new_product_created_id is None: # Debugging, remove for production
             # print("Warning: Product saved but product_id is still None (in existing product update path).")


    def _browse_technical_image(self):
        """Browses for a technical image, copies it to a managed folder, and sets the relative path."""
        if self.product_id is None: # Should be disabled if no product_id
            QMessageBox.warning(self, self.tr("Save Product First"), self.tr("Please save the product before adding a technical image."))
            return

        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, self.tr("Select Technical Image"), "",
                                                  self.tr("Images (*.png *.jpg *.jpeg *.bmp *.gif)"), options=options)
        if fileName:
            try:
                # Determine Target Path
                product_media_folder = os.path.join(MEDIA_FILES_BASE_PATH, "tech_specs", str(self.product_id))
                os.makedirs(product_media_folder, exist_ok=True)
                base_filename = os.path.basename(fileName)
                target_filepath_absolute = os.path.join(product_media_folder, base_filename)

                # Copy File
                shutil.copy2(fileName, target_filepath_absolute)

                # Store Relative Path
                relative_path = os.path.join("tech_specs", str(self.product_id), base_filename)
                self.tech_image_path_edit.setText(relative_path)
                QMessageBox.information(self, self.tr("Image Selected"),
                                        self.tr(f"Image '{base_filename}' copied to product's technical specification folder. Path will be saved with product details."))
            except FileNotFoundError:
                QMessageBox.critical(self, self.tr("File Not Found"), self.tr(f"The selected file '{fileName}' was not found."))
            except PermissionError:
                QMessageBox.critical(self, self.tr("Permission Error"), self.tr(f"Permission denied to access or copy the file '{fileName}'."))
            except IOError as e:
                QMessageBox.critical(self, self.tr("File Error"), self.tr(f"An error occurred while copying the file: {e}"))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Unexpected Error"), self.tr(f"An unexpected error occurred while selecting technical image: {str(e)}"))


    def _add_product_equivalence(self):
        """Opens a dialog to select and add an equivalent product (translation)."""
        if self.product_id is None:
            QMessageBox.warning(self, self.tr("Save Product First"), self.tr("Please save the main product before adding equivalencies."))
            return

        select_dialog = SelectProductDialog(current_product_id=self.product_id, parent=self)
        if select_dialog.exec_() == QDialog.Accepted and select_dialog.selected_product_id is not None:
            equivalent_product_id = select_dialog.selected_product_id

            # No need to check if equivalent_product_id == self.product_id, SelectProductDialog handles this
            # if equivalent_product_id == self.product_id: # This check is now redundant
            #     QMessageBox.warning(self, self.tr("Invalid ID"), self.tr("Cannot link a product to itself."))
            #     return

            try:
                # Check if the target product exists (already implicitly checked by SelectProductDialog if it shows up)
                # target_prod = products_crud.get_product_by_id(equivalent_product_id)
                # if not target_prod: # Should not happen if SelectProductDialog worked correctly
                #     QMessageBox.warning(self, self.tr("Not Found"), self.tr(f"Product with ID {equivalent_product_id} not found."))
                #     return

                # Check if this equivalence already exists
                existing_equivalencies = products_crud.get_all_product_equivalencies(product_id_filter=self.product_id)
                is_already_linked = False
                if existing_equivalencies:
                    for eq_link in existing_equivalencies:
                        if (eq_link['product_id_a'] == equivalent_product_id and eq_link['product_id_b'] == self.product_id) or \
                           (eq_link['product_id_b'] == equivalent_product_id and eq_link['product_id_a'] == self.product_id):
                            is_already_linked = True
                            break
                if is_already_linked:
                    QMessageBox.information(self, self.tr("Already Linked"), self.tr(f"This product is already linked with product ID {equivalent_product_id}."))
                    return

                link_id = products_crud.add_product_equivalence(self.product_id, equivalent_product_id)
                if link_id:
                    QMessageBox.information(self, self.tr("Success"), self.tr("Product equivalence added successfully."))
                    self.load_product_data()  # Refresh list
                else:
                    QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to add product equivalence."))
            except Exception as e:
                # print(f"Error adding product equivalence: {e}") # Debugging
                QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"An error occurred while adding equivalence: {str(e)}"))
        # else: # Dialog was cancelled or no product selected (handled by select_dialog logic or user simply closing it)
            # if select_dialog.selected_product_id is None and select_dialog.result() == QDialog.Accepted :
                 # QMessageBox.information(self, self.tr("No Product Selected"), self.tr("No product was selected from the dialog."))
                 # This case is unlikely if OK button is properly managed by selection.


    def _remove_product_equivalence(self):
        """Removes the selected product equivalence link."""
        if self.product_id is None: return # Should be disabled (UI should prevent this)
                return

            try:
                # Check if the target product exists
                target_prod = products_crud.get_product_by_id(equivalent_product_id)
                if not target_prod:
                    QMessageBox.warning(self, self.tr("Not Found"), self.tr(f"Product with ID {equivalent_product_id} not found."))
                    return

                # Check if this equivalence already exists
                # get_all_product_equivalencies returns list of dicts like {'equivalence_id': X, 'product_id_a': Y, 'product_id_b': Z}
                existing_equivalencies = products_crud.get_all_product_equivalencies(product_id_filter=self.product_id)
                is_already_linked = False
                if existing_equivalencies:
                    for eq_link in existing_equivalencies:
                        if (eq_link['product_id_a'] == equivalent_product_id and eq_link['product_id_b'] == self.product_id) or \
                           (eq_link['product_id_b'] == equivalent_product_id and eq_link['product_id_a'] == self.product_id):
                            is_already_linked = True
                            break
                if is_already_linked:
                    QMessageBox.information(self, self.tr("Already Linked"), self.tr(f"This product is already linked with product ID {equivalent_product_id}."))
                    return

                link_id = products_crud.add_product_equivalence(self.product_id, equivalent_product_id)
                if link_id:
                    QMessageBox.information(self, self.tr("Success"), self.tr("Product equivalence added successfully."))
                    self.load_product_data()  # Refresh list
                else:
                    QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to add product equivalence."))
            except Exception as e:
                print(f"Error adding product equivalence: {e}")
                QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"An error occurred: {e}"))

    def _remove_product_equivalence(self):
        if self.product_id is None: return # Should be disabled

        selected_items = self.equivalencies_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("No Selection"), self.tr("Please select an equivalent product to remove."))
            return

        selected_item = selected_items[0]
        data = selected_item.data(Qt.UserRole)
        equivalence_id_to_remove = data.get("equivalence_id")

        if equivalence_id_to_remove is None:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Could not find equivalence ID for selected item."))
            return

        product_name_display = selected_item.text().split(" - ID:")[0] # Get name part for message

        reply = QMessageBox.question(self, self.tr("Confirm Removal"),
                                     self.tr(f"Are you sure you want to remove the equivalence with '{product_name_display}'?"),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                success = products_crud.remove_product_equivalence(equivalence_id_to_remove)
                if success:
                    QMessageBox.information(self, self.tr("Success"), self.tr("Equivalence removed successfully."))
                    self.load_product_data() # Refresh list
                else:
                    QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to remove equivalence."))
            except Exception as e:
                # print(f"Error removing product equivalence: {e}") # Debugging
                QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"An error occurred while removing equivalence: {str(e)}"))

    def _get_placeholder_uploader_id(self):
        """
        Retrieves a placeholder uploader ID.
        Attempts to use 'admin' user or falls back.
        Note: This is a placeholder; a robust system would use the logged-in user's ID.
        """
        admin_user = get_user_by_username("admin")
        if admin_user and 'user_id' in admin_user:
            return admin_user['user_id']

        # Fallback if admin user not found. This might indicate a setup issue.
        QMessageBox.warning(self, self.tr("Configuration Warning"),
                            self.tr("Could not retrieve 'admin' user_id for uploads. Please ensure an 'admin' user exists."))
        return None


    def _add_image(self):
        """Adds one or more images to the product gallery after saving them via media_ops."""
        if self.product_id is None:
            QMessageBox.warning(self, self.tr("Save Product First"), self.tr("Product must be saved first before adding images."))
            return

        # Get a placeholder uploader_id
        uploader_id = self._get_placeholder_uploader_id()
        if not uploader_id:
            QMessageBox.critical(self, self.tr("Upload Error"),
                                 self.tr("Cannot determine uploader. Please ensure an 'admin' user exists or a default uploader is configured."))
            return

        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter(self.tr("Images (*.png *.jpg *.jpeg *.bmp *.gif)"))
        file_dialog.setFileMode(QFileDialog.ExistingFiles) # Allow multiple file selection

        if file_dialog.exec_():
            selected_filepaths = file_dialog.selectedFiles()
            if not selected_filepaths:
                return

            successful_uploads = 0
            failed_uploads = 0

            for filepath in selected_filepaths:
                try:
                    # Derive a title from filename, remove extension
                    base_filename = os.path.basename(filepath)
                    title = os.path.splitext(base_filename)[0]

                    # Run the async add_image function
                    # This will block the UI thread. For true async, QThread would be needed.
                    new_media_item = asyncio.run(media_ops.add_image(
                        title=title,
                        description="", # Or prompt user
                        filepath=filepath,
                        uploader_user_id=uploader_id
                        # metadata can be passed if needed
                    ))

                    if new_media_item and hasattr(new_media_item, 'id'):
                        # Link this new media item to the current product
                        # Determine next display_order
                        next_display_order = len(self.media_links) # Simple append
                        if self.media_links: # More robust: find max existing order + 1
                           max_order = max(link.get('display_order', -1) for link in self.media_links)
                           next_display_order = max_order + 1

                        link_id = product_media_links_crud.link_media_to_product(
                            product_id=self.product_id,
                            media_item_id=new_media_item.id,
                            display_order=next_display_order,
                            alt_text=title # Use title as initial alt_text
                        )
                        if link_id:
                            successful_uploads += 1
                        else:
                            failed_uploads += 1
                            # print(f"Failed to link media_item {new_media_item.id} to product {self.product_id}") # Debugging
                    else:
                        failed_uploads += 1
                        # print(f"Failed to add image '{filepath}' to media manager.") # Debugging
                except Exception as e:
                    failed_uploads += 1
                    # print(f"Error processing file {filepath}: {e}") # Debugging
                    QMessageBox.warning(self, self.tr("Upload Error"),
                                        self.tr(f"Could not process file {os.path.basename(filepath)}:\n{str(e)}"))

            summary_message = []
            if successful_uploads > 0:
                summary_message.append(self.tr(f"{successful_uploads} image(s) added successfully."))
            if failed_uploads > 0:
                summary_message.append(self.tr(f"{failed_uploads} image(s) failed to add."))

            if summary_message:
                QMessageBox.information(self, self.tr("Upload Summary"), "\n".join(summary_message))

            if successful_uploads > 0:
                self.load_product_data() # Reload to refresh gallery and media_links list

    def _remove_image(self):
        selected_item = self.image_gallery_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, self.tr("No Image Selected"),
                                self.tr("Please select an image from the gallery to remove."))
            return

        link_data = selected_item.data(Qt.UserRole)
        if not link_data or 'link_id' not in link_data:
            QMessageBox.critical(self, self.tr("Error"),
                                 self.tr("Could not retrieve image link details for selected item."))
            return

        link_id = link_data['link_id']
        image_title = link_data.get('media_title', os.path.basename(link_data.get('media_filepath', 'this image')))

        reply = QMessageBox.question(self, self.tr("Confirm Removal"),
                                     self.tr(f"Are you sure you want to remove the link to '{image_title}' from this product?\n(The image will remain in the media library.)"),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                success = product_media_links_crud.unlink_media_from_product(link_id=link_id)
                if success:
                    QMessageBox.information(self, self.tr("Image Unlinked"),
                                            self.tr(f"The image '{image_title}' has been successfully unlinked from this product."))
                    # Refresh product data and gallery
                    self.load_product_data()
                else:
                    QMessageBox.critical(self, self.tr("Unlink Failed"),
                                         self.tr(f"Could not unlink the image '{image_title}'. It might have already been removed or an error occurred."))
            except Exception as e:
                # print(f"Error during image unlinking: {e}") # Debugging
                QMessageBox.critical(self, self.tr("Error"),
                                     self.tr(f"An unexpected error occurred while unlinking the image: {str(e)}"))

    def _edit_image_details(self):
        """Allows editing details (like alt text) for a selected gallery image."""
        selected_item = self.image_gallery_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, self.tr("No Image Selected"),
                                self.tr("Please select an image from the gallery to edit its details."))
            return

        link_data = selected_item.data(Qt.UserRole)
        if not link_data or 'link_id' not in link_data:
            QMessageBox.critical(self, self.tr("Error"),
                                 self.tr("Could not retrieve image link details for the selected item."))
            return

        link_id = link_data['link_id']
        current_alt_text = link_data.get('alt_text', '') # Default to empty string if None
        image_title = link_data.get('media_title', os.path.basename(link_data.get('media_filepath', 'Selected Image')))

        new_alt_text, ok = QInputDialog.getText(self,
                                                self.tr("Edit Alt Text"),
                                                self.tr(f"Alt text for '{image_title}':"),
                                                QLineEdit.Normal,
                                                current_alt_text)

        if ok: # User clicked OK
            if new_alt_text != current_alt_text:
                try:
                    success = product_media_links_crud.update_media_link(
                        link_id=link_id,
                        alt_text=new_alt_text
                        # display_order is not changed here, so pass None or omit
                    )
                    if success:
                        QMessageBox.information(self, self.tr("Alt Text Updated"),
                                                self.tr(f"Alt text for '{image_title}' has been updated."))
                        # Refresh product data and gallery to reflect change (e.g., in tooltip)
                        self.load_product_data()
                    else:
                        QMessageBox.critical(self, self.tr("Update Failed"),
                                             self.tr("Could not update the alt text for the image."))
                except Exception as e:
                    # print(f"Error updating alt text: {e}") # Debugging
                    QMessageBox.critical(self, self.tr("Error"),
                                         self.tr(f"An unexpected error occurred while updating alt text: {str(e)}"))
            # else: No change in alt text, do nothing.

    def _move_image_up(self):
        """Moves the selected gallery image up in the display order."""
        current_row = self.image_gallery_list.currentRow()
        if current_row > 0:
            current_item = self.image_gallery_list.takeItem(current_row)
            self.image_gallery_list.insertItem(current_row - 1, current_item)
            self.image_gallery_list.setCurrentRow(current_row - 1)
            self._save_current_image_order()

    def _move_image_down(self):
        """Moves the selected gallery image down in the display order."""
        current_row = self.image_gallery_list.currentRow()
        if current_row >= 0 and current_row < self.image_gallery_list.count() - 1:
            current_item = self.image_gallery_list.takeItem(current_row)
            self.image_gallery_list.insertItem(current_row + 1, current_item)
            self.image_gallery_list.setCurrentRow(current_row + 1)
            self._save_current_image_order()

    def _save_current_image_order(self):
        """Saves the current visual order of images in the gallery to the database."""
        if self.product_id is None:
            # This should ideally not be reached if UI correctly disables reordering for non-saved products.
            return

        ordered_media_item_ids = []
        for i in range(self.image_gallery_list.count()):
            item = self.image_gallery_list.item(i)
            if item: # Should always be true in this loop
                link_data = item.data(Qt.UserRole)
                if link_data and 'media_item_id' in link_data:
                    ordered_media_item_ids.append(link_data['media_item_id'])
                else:
                    # This case indicates an item in the list without proper data.
                    # This might happen if the "No images" placeholder item is not cleared correctly
                    # or if an item failed to load its data.
                    # This is primarily a debugging concern or indicates an issue with data population.
                    # print(f"Warning: Item at index {i} in gallery list has missing or invalid link_data.") # Debugging
                    pass


        if not ordered_media_item_ids and self.image_gallery_list.count() > 0:
             # This situation (items in list but no valid IDs extracted) suggests a data integrity issue
             # with how items are added to the list or their UserRole data.
             # It's not expected if the "No images linked" placeholder is the only item without UserRole data.
             pass # No valid media IDs to save order for.

        try:
            success = product_media_links_crud.update_product_media_display_orders(
                product_id=self.product_id,
                ordered_media_item_ids=ordered_media_item_ids
            )
            if success:
                # print("Image order saved successfully.") # Debugging, user sees visual change
                self.load_product_data() # Reload to refresh all data, including link_data in items
            else:
                QMessageBox.critical(self, self.tr("Reorder Failed"),
                                     self.tr("Could not save the new image order to the database."))
        except Exception as e:
            # print(f"Error saving image order: {e}") # Debugging
            QMessageBox.critical(self, self.tr("Error"),
                                 self.tr(f"An unexpected error occurred while saving image order: {str(e)}"))


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    # This is a basic test. Requires a product with product_id=1 in the DB.
    # Or pass None to test "Add New Product" mode if implemented.
    TEST_PRODUCT_ID = 1

    # Setup a dummy db for testing if needed, or ensure your dev DB has product 1
    # This __main__ block is for basic testing of the dialog independently.
    # It requires a valid database connection and potentially pre-existing data.

    app = QApplication(sys.argv)

    # --- Database Setup (Example - adjust as per your project's actual setup) ---
    # This section might need to replicate parts of your main app's DB initialization
    # if `db_config` or `products_crud` rely on a global connection object.
    # For instance, if products_crud uses a global 'conn':
    # from db.connection import get_db_connection, close_db_connection
    # from db.init_schema import initialize_database
    # import db_config
    # db_config.DATABASE_PATH = "client_docs_app.db" # Or your test DB
    # conn = get_db_connection()
    # initialize_database(conn) # Ensure schema exists
    # products_crud.conn = conn # If CRUDs expect a connection object set this way

    TEST_PRODUCT_ID = 1 # Try to load an existing product for testing
    # TEST_PRODUCT_ID = None # To test "Add New Product" mode

    product_exists = False
    try:
        if TEST_PRODUCT_ID is not None:
            if products_crud.get_product_by_id(TEST_PRODUCT_ID):
                product_exists = True
            else:
                # print(f"Test Product ID {TEST_PRODUCT_ID} not found. Consider adding it or using TEST_PRODUCT_ID = None.")
                # For testing, let's try to create a dummy product if it doesn't exist
                try:
                    dummy_data = {
                        'product_name': 'Test Product for Dialog', 'language_code': 'en',
                        'category': 'Test', 'base_unit_price': 19.99
                    }
                    # If your add_product allows specifying ID, use it, otherwise let it auto-generate
                    # For now, assume auto-generate if TEST_PRODUCT_ID was not found
                    # new_id = products_crud.add_product(dummy_data)
                    # print(f"Created dummy product with ID {new_id} for testing.")
                    # TEST_PRODUCT_ID = new_id # Use this new ID
                    # product_exists = True
                    pass # For now, just note if it's not found.
                except Exception as create_e:
                    # print(f"Could not create dummy product for testing: {create_e}")
                    pass # Fall through to TEST_PRODUCT_ID = None if creation fails

    except Exception as db_e:
        # print(f"Database error during test setup: {db_e}. Ensure DB is accessible and schema initialized.")
        # QMessageBox.critical(None, "DB Error", f"Could not connect to or query database for testing: {db_e}")
        # sys.exit(1) # Exit if DB is not usable for test
        pass # Allow dialog to open in "new" mode or handle error internally


    # If TEST_PRODUCT_ID was set, but product doesn't exist, switch to "Add New" mode for testing.
    # Or, the dialog itself will handle the "Product not found" case.
    # For a smoother test if product 1 doesn't exist, one might default to None:
    # effective_test_id = TEST_PRODUCT_ID if product_exists else None
    effective_test_id = TEST_PRODUCT_ID # Let dialog handle "not found" for existing ID test

    dialog = ProductEditDialog(product_id=effective_test_id)

    # For testing "Add New" mode, dialog should show immediately.
    # For "Edit" mode, it might reject if product_id is invalid and not loaded.
    # Check if dialog rejected itself during init (e.g. product not found)
    # A better way is to check dialog.isVisible() after show() or connect to finished signal.
    # For this simple test, we'll just show it.
    dialog.show()
    exit_code = app.exec_()

    # if products_crud.conn: # If global connection was set for CRUDs
    #     close_db_connection(products_crud.conn)
    sys.exit(exit_code)
