# product_edit_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QCheckBox, QListWidget, QListWidgetItem, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QSize # Import QSize
from PyQt5.QtGui import QPixmap, QIcon

# Assuming db.cruds is accessible. Adjust import path if necessary.
# Example: from ..db.cruds import products_crud, product_media_links_crud
# For this subtask, direct import if files are in expected locations.
import db.cruds.products_crud as products_crud
import db.cruds.product_media_links_crud as product_media_links_crud
import media_manager.operations as media_ops
from db.cruds.users_crud import get_user_by_username # To get a placeholder uploader_id
import asyncio # For running async functions
from config import MEDIA_FILES_BASE_PATH # For resolving image paths
import os

class ProductEditDialog(QDialog):
    def __init__(self, product_id, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.setWindowTitle(self.tr("Edit Product"))
        self.setGeometry(150, 150, 700, 500) # Adjusted size

        self.db_product_data = None # To store initially loaded product data
        self.media_links = [] # To store loaded media links

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.description_edit.setFixedHeight(80)
        self.category_edit = QLineEdit()
        self.language_code_edit = QLineEdit()
        self.price_edit = QLineEdit()
        self.unit_edit = QLineEdit()
        self.weight_edit = QLineEdit()
        self.dimensions_edit = QLineEdit()
        self.is_active_check = QCheckBox(self.tr("Is Active"))

        form_layout.addRow(self.tr("Name:"), self.name_edit)
        form_layout.addRow(self.tr("Description:"), self.description_edit)
        form_layout.addRow(self.tr("Category:"), self.category_edit)
        form_layout.addRow(self.tr("Language Code:"), self.language_code_edit)
        form_layout.addRow(self.tr("Base Unit Price:"), self.price_edit)
        form_layout.addRow(self.tr("Unit of Measure:"), self.unit_edit)
        form_layout.addRow(self.tr("Weight:"), self.weight_edit)
        form_layout.addRow(self.tr("Dimensions:"), self.dimensions_edit)
        form_layout.addRow(self.is_active_check)

        main_layout.addLayout(form_layout)

        # Image Gallery Section
        gallery_label = QLabel(self.tr("Product Images:"))
        main_layout.addWidget(gallery_label)
        self.image_gallery_list = QListWidget()
        self.image_gallery_list.setFixedHeight(150) # Placeholder size
        # In a later step, this will show thumbnails. For now, filepaths or titles.
        main_layout.addWidget(self.image_gallery_list)

        # Image Management Buttons
        image_buttons_layout = QHBoxLayout()
        self.add_image_button = QPushButton(self.tr("Add Image..."))
        self.add_image_button.clicked.connect(self._add_image)
        self.remove_image_button = QPushButton(self.tr("Remove Selected Image"))
        # self.remove_image_button.clicked.connect(self._remove_image) # For later
        self.edit_image_button = QPushButton(self.tr("Edit Image Details..."))
        # self.edit_image_button.clicked.connect(self._edit_image_details) # For later
        image_buttons_layout.addWidget(self.add_image_button)
        image_buttons_layout.addWidget(self.remove_image_button)
        image_buttons_layout.addWidget(self.edit_image_button)
        image_buttons_layout.addStretch()
        main_layout.addLayout(image_buttons_layout)

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

        self.load_product_data()

    def load_product_data(self):
        if self.product_id is None:
            self.setWindowTitle(self.tr("Add New Product")) # Or handle as error
            # Potentially initialize fields for a new product
            return

        self.db_product_data = products_crud.get_product_by_id(self.product_id)

        if not self.db_product_data:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Product not found."))
            # self.reject() # Close dialog if product not found
            return

        self.name_edit.setText(self.db_product_data.get('product_name', ''))
        self.description_edit.setPlainText(self.db_product_data.get('description', ''))
        self.category_edit.setText(self.db_product_data.get('category', ''))
        self.language_code_edit.setText(self.db_product_data.get('language_code', ''))
        self.price_edit.setText(str(self.db_product_data.get('base_unit_price', '')))
        self.unit_edit.setText(self.db_product_data.get('unit_of_measure', ''))
        self.weight_edit.setText(str(self.db_product_data.get('weight', '')))
        self.dimensions_edit.setText(self.db_product_data.get('dimensions', ''))
        self.is_active_check.setChecked(self.db_product_data.get('is_active', True))

        self.media_links = self.db_product_data.get('media_links', [])
        self._populate_image_gallery()

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
        # Placeholder for now. Actual save logic will update product and media links.
        updated_data = {
            'product_name': self.name_edit.text(),
            'description': self.description_edit.toPlainText(),
            'category': self.category_edit.text(),
            'language_code': self.language_code_edit.text(),
            'base_unit_price': float(self.price_edit.text()) if self.price_edit.text() else None,
            'unit_of_measure': self.unit_edit.text(),
            'weight': float(self.weight_edit.text()) if self.weight_edit.text() else None,
            'dimensions': self.dimensions_edit.text(),
            'is_active': self.is_active_check.isChecked()
        }
        print(f"Attempting to save product ID {self.product_id} with data: {updated_data}")

        # Call products_crud.update_product(self.product_id, updated_data)
        # Handle media links changes (additions, removals, reordering, alt text updates)
        # This will involve product_media_links_crud functions.

        # QMessageBox.information(self, self.tr("Save"), self.tr("Changes would be saved here."))
        # self.accept() # If save is successful

    # Placeholder for _add_image, _remove_image, _edit_image_details
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

    # def _remove_image(self): print("Remove image clicked")
    # def _edit_image_details(self): print("Edit image details clicked")

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
