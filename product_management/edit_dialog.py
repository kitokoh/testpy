# product_edit_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QCheckBox, QListWidget, QListWidgetItem, QMessageBox, QFileDialog,
    QInputDialog, QGroupBox, QScrollArea, QGridLayout, QComboBox, QWidget
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

SUPPORTED_LANGUAGES = [
    ("English", "en"),
    ("French", "fr"),
    ("Arabic", "ar"),
    ("Turkish", "tr"),
    ("Spanish", "es")
]

class ProductEditDialog(QDialog):
    def __init__(self, product_id, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.setWindowTitle(self.tr("Edit Product"))
        self.setGeometry(150, 150, 750, 800) # Adjusted size for new sections

        self.db_product_data = None # To store initially loaded product data
        self.db_tech_specs_data = None # To store technical specifications
        self.equivalent_products = [] # To store equivalent products
        self.media_links = [] # To store loaded media links

        # Main scroll area
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        main_widget_for_scroll = QWidget()
        main_layout = QVBoxLayout(main_widget_for_scroll) # Main layout is inside the scrollable widget

        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
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
        form_layout.addRow(self.tr("Description:"), self.description_edit)
        form_layout.addRow(self.tr("Category:"), self.category_edit)
        form_layout.addRow(self.tr("Base Unit Price:"), self.price_edit)
        form_layout.addRow(self.tr("Unit of Measure:"), self.unit_edit)
        form_layout.addRow(self.tr("Weight:"), self.weight_edit)
        form_layout.addRow(self.tr("Dimensions:"), self.dimensions_edit)
        form_layout.addRow(self.is_active_check)

        main_layout.addLayout(form_layout)

        # Image Gallery Section
        gallery_group = QGroupBox(self.tr("Product Images"))
        gallery_layout = QVBoxLayout(gallery_group)
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
        main_layout.addWidget(gallery_group)

        # Technical Specifications Section
        tech_specs_group = QGroupBox(self.tr("Technical Specifications"))
        tech_specs_layout = QFormLayout(tech_specs_group) # Using QFormLayout for consistency
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
        tech_specs_layout.addRow("Dimension A:", self.dim_A_edit)
        tech_specs_layout.addRow("Dimension B:", self.dim_B_edit)
        tech_specs_layout.addRow("Dimension C:", self.dim_C_edit)
        tech_specs_layout.addRow("Dimension D:", self.dim_D_edit)
        tech_specs_layout.addRow("Dimension E:", self.dim_E_edit)
        tech_specs_layout.addRow("Dimension F:", self.dim_F_edit)
        tech_specs_layout.addRow("Dimension G:", self.dim_G_edit)
        tech_specs_layout.addRow("Dimension H:", self.dim_H_edit)
        tech_specs_layout.addRow("Dimension I:", self.dim_I_edit)
        tech_specs_layout.addRow("Dimension J:", self.dim_J_edit)

        tech_image_layout = QHBoxLayout()
        self.tech_image_path_edit = QLineEdit()
        self.tech_image_path_edit.setReadOnly(True)
        self.browse_tech_image_button = QPushButton(self.tr("Browse..."))
        self.browse_tech_image_button.clicked.connect(self._browse_technical_image)
        tech_image_layout.addWidget(self.tech_image_path_edit)
        tech_image_layout.addWidget(self.browse_tech_image_button)
        tech_specs_layout.addRow(self.tr("Technical Image:"), tech_image_layout)
        main_layout.addWidget(tech_specs_group)

        # Product Equivalencies (Translations) Section
        equivalencies_group = QGroupBox(self.tr("Translations / Equivalent Products"))
        equivalencies_main_layout = QVBoxLayout(equivalencies_group)
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
        main_layout.addWidget(equivalencies_group)


        # Dialog Action Buttons
        action_buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(self.tr("Save Changes"))
        self.save_button.clicked.connect(self._save_changes)
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.clicked.connect(self.reject)
        action_buttons_layout.addStretch()
        action_buttons_layout.addWidget(self.save_button)
        action_buttons_layout.addWidget(self.cancel_button)
        main_layout.addLayout(action_buttons_layout)

        scroll_area.setWidget(main_widget_for_scroll)
        outer_layout = QVBoxLayout(self) # This is the dialog's actual layout
        outer_layout.addWidget(scroll_area)
        self.setLayout(outer_layout) # Set the dialog's layout

        self.load_product_data()
        self._update_ui_for_product_id_state()


    def _update_ui_for_product_id_state(self):
        """Enable/disable sections based on whether product_id exists."""
        has_product_id = self.product_id is not None
        # Image gallery, tech specs, and equivalencies should be enabled only if product exists
        # Assuming gallery_group, tech_specs_group, equivalencies_group are defined
        if hasattr(self, 'gallery_group'): self.gallery_group.setEnabled(has_product_id)
        if hasattr(self, 'tech_specs_group'): self.tech_specs_group.setEnabled(has_product_id)
        if hasattr(self, 'equivalencies_group'): self.equivalencies_group.setEnabled(has_product_id)


    def load_product_data(self):
        if self.product_id is None:
            self.setWindowTitle(self.tr("Add New Product"))
            # Clear fields for new product entry
            self.name_edit.clear()
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
            self._update_ui_for_product_id_state() # Disable sections
            return

        self.db_product_data = products_crud.get_product_by_id(self.product_id)

        if not self.db_product_data:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Product not found."))
            self.reject() # Close dialog if product not found
            return

        self.name_edit.setText(self.db_product_data.get('product_name', ''))
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
                else:
                    print(f"Warning: Could not load QPixmap for {path_to_try}")
            # else:
                # print(f"Warning: Image/Thumbnail file not found at {path_to_try}")
                # Optionally set a "file not found" icon
                # icon_to_set = QIcon("path/to/your/file_not_found_icon.png")

            list_item.setIcon(icon_to_set)
            list_item.setToolTip(f"Path: {link.get('media_filepath', 'N/A')}\nAlt: {link.get('alt_text', 'None')}")
            self.image_gallery_list.addItem(list_item)

    def _save_changes(self):
        # --- Gather data from UI fields ---
        try:
            product_name = self.name_edit.text().strip()
            if not product_name:
                QMessageBox.warning(self, self.tr("Validation Error"), self.tr("Product name cannot be empty."))
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
                print(f"Error updating product {self.product_id}: {e}")
                QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"An error occurred while saving: {e}"))
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
                    if self.language_code_combo: # Switch from ComboBox to read-only QLineEdit
                        current_lang_code = self.language_code_combo.currentData()
                        # Find the form layout row for language_code_combo and replace widget
                        # This is a bit tricky as QFormLayout doesn't have a simple replaceWidgetAtRow
                        # For simplicity, we might just inform user and rely on reload.
                        # Or, better, reconstruct that part of the form if essential.
                        # For now, we'll rely on load_product_data to fix UI if it's called.
                        # The __init__ logic for language_code_edit vs combo handles this on next open.
                        pass

                    self.load_product_data() # Reload to ensure consistency and enable other sections
                    self._update_ui_for_product_id_state() # Enable sections
                else:
                    QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to add new product."))
            except Exception as e:
                print(f"Error adding new product: {e}")
                QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"An error occurred while adding product: {e}"))

        if product_saved_successfully and self.product_id is not None:
            # Save Technical Specifications
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
                if tech_spec_success:
                    # Optional: specific success message for tech specs
                    print(f"Technical specifications for product ID {self.product_id} saved.")
                else:
                    QMessageBox.warning(self, self.tr("Tech Spec Save Warning"), self.tr("Could not save technical specifications."))
            except Exception as e:
                print(f"Error saving technical specifications for product {self.product_id}: {e}")
                QMessageBox.critical(self, self.tr("Tech Spec Error"), self.tr(f"An error occurred while saving technical specifications: {e}"))

            # Equivalencies are handled by their own buttons directly.
            # No explicit save step here for equivalencies.

            if new_product_created_id: # If it was a new product
                 QMessageBox.information(self, self.tr("Product Added"),
                                        self.tr(f"Product '{updated_product_data['product_name']}' (ID: {new_product_created_id}) and its details have been saved."))
                 # Keep dialog open for further edits (images, etc.)
            else: # Existing product updated
                 QMessageBox.information(self, self.tr("Product Updated"), self.tr("Product and its details have been updated successfully."))
                 self.accept() # Close dialog only if an existing product was updated.

        elif product_saved_successfully and new_product_created_id is None:
             # This case should ideally not be hit if logic is correct (product_id should be set)
             print("Warning: Product saved but product_id is still None.")

        # The old print and placeholder comments are removed as full save logic is above.


    def _browse_technical_image(self):
        if self.product_id is None: # Should be disabled if no product_id
            QMessageBox.warning(self, self.tr("Save Product First"), self.tr("Please save the product before adding a technical image."))
            return

        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, self.tr("Select Technical Image"), "",
                                                  self.tr("Images (*.png *.jpg *.jpeg *.bmp *.gif)"), options=options)
        if fileName:
            # For now, just set the path. Actual copy to media folder is a TODO.
            # Ideally, this would copy the file to a managed location and store a relative path.
            # e.g., target_folder = os.path.join(MEDIA_FILES_BASE_PATH, "technical_schematics", str(self.product_id))
            # And then copy file there, store "technical_schematics/product_id/filename.ext"
            # This is complex due to potential for media_manager interaction.
            # For subtask: display selected path. Actual saving of this path happens in _save_changes.

            # Simplification: Assume MEDIA_FILES_BASE_PATH is the root for these too.
            # Try to make it relative if it's under MEDIA_FILES_BASE_PATH, otherwise store absolute (not ideal)
            try:
                relative_path = os.path.relpath(fileName, MEDIA_FILES_BASE_PATH)
                # If relpath starts with '..', it's outside, so use absolute or handle error
                if relative_path.startswith(".."):
                    # For now, let's store the absolute path if outside MEDIA_FILES_BASE_PATH.
                    # This is not robust. A copy operation is needed.
                    QMessageBox.warning(self, self.tr("Path Warning"),
                                        self.tr("Image is outside the media base path. Storing absolute path. Consider moving it to the media library."))
                    self.tech_image_path_edit.setText(fileName)
                else:
                    self.tech_image_path_edit.setText(relative_path)
            except ValueError: # Handles case where paths are on different drives (Windows)
                QMessageBox.warning(self, self.tr("Path Warning"),
                                    self.tr("Image is on a different drive from the media base path. Storing absolute path. Consider moving it."))
                self.tech_image_path_edit.setText(fileName)


    def _add_product_equivalence(self):
        if self.product_id is None:
            QMessageBox.warning(self, self.tr("Save Product First"), self.tr("Please save the main product before adding equivalencies."))
            return

        equivalent_product_id, ok = QInputDialog.getInt(self, self.tr("Add Equivalent Product"),
                                                        self.tr("Enter the Product ID of the equivalent product:"))
        if ok and equivalent_product_id:
            if equivalent_product_id == self.product_id:
                QMessageBox.warning(self, self.tr("Invalid ID"), self.tr("Cannot link a product to itself."))
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
                print(f"Error removing product equivalence: {e}")
                QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"An error occurred: {e}"))

    def _get_placeholder_uploader_id(self):
        # Attempt to get 'admin' user_id as a placeholder
        # This assumes an 'admin' user exists as per db_config or schema seeding.
        admin_user = get_user_by_username("admin") # Or use db_config.DEFAULT_ADMIN_USERNAME
        if admin_user and 'user_id' in admin_user:
            return admin_user['user_id']
        # Fallback if admin user not found or doesn't have user_id
        # This should ideally not happen in a configured system.
        # A more robust solution might involve a dedicated system user ID.
        print("Warning: Could not retrieve 'admin' user_id. Uploads may fail or use None.")
        return None


    def _add_image(self):
        if self.product_id is None:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Product must be saved first before adding images."))
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
                            print(f"Failed to link media_item {new_media_item.id} to product {self.product_id}")
                    else:
                        failed_uploads += 1
                        print(f"Failed to add image '{filepath}' to media manager.")
                except Exception as e:
                    failed_uploads += 1
                    print(f"Error processing file {filepath}: {e}")
                    QMessageBox.warning(self, self.tr("Upload Error"),
                                        self.tr(f"Could not process file {filepath}:\n{e}"))

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
                print(f"Error during image unlinking: {e}")
                QMessageBox.critical(self, self.tr("Error"),
                                     self.tr(f"An unexpected error occurred while unlinking the image: {e}"))

    def _edit_image_details(self):
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
                    print(f"Error updating alt text: {e}")
                    QMessageBox.critical(self, self.tr("Error"),
                                         self.tr(f"An unexpected error occurred while updating alt text: {e}"))
            # else: No change in alt text, do nothing.

    def _move_image_up(self):
        current_row = self.image_gallery_list.currentRow()
        if current_row > 0: # Can move up if not the first item
            current_item = self.image_gallery_list.takeItem(current_row)
            self.image_gallery_list.insertItem(current_row - 1, current_item)
            self.image_gallery_list.setCurrentRow(current_row - 1) # Keep selection on moved item
            self._save_current_image_order()

    def _move_image_down(self):
        current_row = self.image_gallery_list.currentRow()
        # Check if it's not the last item
        if current_row >= 0 and current_row < self.image_gallery_list.count() - 1:
            current_item = self.image_gallery_list.takeItem(current_row)
            self.image_gallery_list.insertItem(current_row + 1, current_item)
            self.image_gallery_list.setCurrentRow(current_row + 1) # Keep selection on moved item
            self._save_current_image_order()

    def _save_current_image_order(self):
        if self.product_id is None:
            # Should not happen if buttons are enabled only for existing product
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
                    # For robustness, one might skip or log this.
                    print(f"Warning: Item at index {i} in gallery list has missing or invalid link_data.")


        if not ordered_media_item_ids and self.image_gallery_list.count() > 0:
            # If count > 0 but list is empty, it means all items had bad data.
            # This could happen if the "No images linked" placeholder was not handled correctly when items are added.
            # However, _populate_image_gallery clears and adds "No images..." if self.media_links is empty.
            # If self.media_links is populated, it adds actual items.
            # This path should ideally not be hit if _populate_image_gallery is correct.
             pass # No valid media IDs to save order for.

        try:
            success = product_media_links_crud.update_product_media_display_orders(
                product_id=self.product_id,
                ordered_media_item_ids=ordered_media_item_ids
            )
            if success:
                # Optionally, provide subtle feedback or simply rely on visual order.
                # For robustness, reload data to ensure self.media_links and tooltips
                # (if they show display_order from link_data) are updated.
                print("Image order saved successfully.")
                self.load_product_data() # Reload to refresh all data based on new order
            else:
                QMessageBox.critical(self, self.tr("Reorder Failed"),
                                     self.tr("Could not save the new image order to the database."))
                # Potentially revert visual changes or reload to be safe, though load_product_data will fix it.
        except Exception as e:
            print(f"Error saving image order: {e}")
            QMessageBox.critical(self, self.tr("Error"),
                                 self.tr(f"An unexpected error occurred while saving image order: {e}"))
            # self.load_product_data() # Revert to last known good state from DB


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    # This is a basic test. Requires a product with product_id=1 in the DB.
    # Or pass None to test "Add New Product" mode if implemented.
    TEST_PRODUCT_ID = 1

    # Setup a dummy db for testing if needed, or ensure your dev DB has product 1
    # For subtask testing, it's okay if this part doesn't fully run if DB isn't perfectly set up.
    # The core is creating the file structure.

    app = QApplication(sys.argv)

    # Ensure db_config.DATABASE_PATH is correctly set for CRUDs to work
    # Example: You might need to initialize db_config if it's not auto-done
    # import db_config
    # db_config.DATABASE_PATH = "path/to/your/dev.db"

    try:
        # Check if product exists for testing
        if products_crud.get_product_by_id(TEST_PRODUCT_ID) is None:
            print(f"Test Product ID {TEST_PRODUCT_ID} not found. Add it to your database for full dialog testing.")
            # Optionally, create a dummy product for testing this dialog
            # products_crud.add_product({'product_name': 'Test Product 1', 'base_unit_price': 10.0, 'product_id': TEST_PRODUCT_ID}) # If ID can be set
            # Or just proceed and let the dialog show "Product not found"
    except Exception as e:
        print(f"Error checking for test product: {e}. Ensure DB is accessible and schema is initialized.")


    dialog = ProductEditDialog(product_id=TEST_PRODUCT_ID) # Pass a product ID
    if dialog.db_product_data: # Only show if product loaded
        dialog.show()
        sys.exit(app.exec_())
    else:
        print(f"Could not load product {TEST_PRODUCT_ID} for dialog. Exiting test.")
        # Potentially show a message if dialog itself handles this.
        # If ProductEditDialog calls reject() on load failure, app might exit quietly.
