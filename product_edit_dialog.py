# product_edit_dialog.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QCheckBox, QListWidget, QListWidgetItem, QMessageBox, QFileDialog,
    QInputDialog # Add QInputDialog
)
from PyQt5.QtCore import Qt, QSize
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
        image_buttons_layout.addSpacing(20) # Add some space before move buttons
        image_buttons_layout.addWidget(self.move_image_up_button)
        image_buttons_layout.addWidget(self.move_image_down_button)
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
        # --- Gather data from UI fields ---
        try:
            product_name = self.name_edit.text().strip()
            if not product_name:
                QMessageBox.warning(self, self.tr("Validation Error"), self.tr("Product name cannot be empty."))
                return

            description = self.description_edit.toPlainText().strip()
            category = self.category_edit.text().strip()
            language_code = self.language_code_edit.text().strip()

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

            dimensions = self.dimensions_edit.text().strip()
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
            'dimensions': dimensions,
            'is_active': is_active
        }

        # Remove keys with None values if the CRUD update function handles partial updates
        # based on key presence rather than None values, or if None means "set to NULL".
        # products_crud.update_product is designed to only update fields present in the data dict.
        # However, explicit None might try to set DB to NULL.
        # For safety, let's filter out Nones if the intent is "no change" for that field.
        # But if the field was cleared in UI, None *should* be passed to clear it in DB.
        # The current products_crud.update_product builds SET clauses for keys present in `data`.
        # So, if a field is cleared in UI and results in None, and we want to set it to NULL in DB,
        # it should be included. If it means "no change", it should be excluded.
        # For this implementation, we'll pass the data as is.
        # If a field is optional in DB and user clears it, it should become NULL.

        if self.product_id is not None: # Editing existing product
            try:
                success = products_crud.update_product(product_id=self.product_id, data=updated_product_data)
                if success:
                    QMessageBox.information(self, self.tr("Success"), self.tr("Product details saved successfully."))
                    self.accept() # Close the dialog
                else:
                    # Check if product still exists, maybe it was deleted by another user?
                    check_prod = products_crud.get_product_by_id(self.product_id)
                    if not check_prod:
                         QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to save product details. The product may have been deleted."))
                    else:
                         QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to save product details. Please check data and try again."))
            except Exception as e:
                print(f"Error updating product {self.product_id}: {e}")
                QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"An error occurred while saving: {e}"))
        else:
            # This is "Add New Product" mode.
            # The current dialog is designed for editing an existing product_id.
            # To support "Add New", the dialog would need to be opened with product_id=None.
            # And then, after adding, self.product_id should be set to the new ID.
            # Image management buttons would typically be disabled until product is first saved.
            try:
                new_id = products_crud.add_product(product_data=updated_product_data)
                if new_id:
                    self.product_id = new_id # Store the new ID
                    self.setWindowTitle(self.tr("Edit Product") + f" (ID: {new_id})") # Update title
                    QMessageBox.information(self, self.tr("Success"),
                                            self.tr(f"Product '{product_name}' added successfully with ID {new_id}. You can now add images."))
                    # Dialog remains open, image buttons would now be enabled if they depend on self.product_id
                    self.load_product_data() # Reload to ensure consistency and enable image ops if any
                    # Or self.accept() if we want to close after adding.
                    # For now, let's assume we want to keep it open to add images.
                else:
                    QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to add new product."))
            except Exception as e:
                print(f"Error adding new product: {e}")
                QMessageBox.critical(self, self.tr("Database Error"), self.tr(f"An error occurred while adding product: {e}"))

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
