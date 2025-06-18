"""
Inventory Browser Widget for managing storage locations and product assignments.

This module provides a QWidget that includes:
- A QTreeView for hierarchical display and management of storage locations.
- UI elements for searching products and assigning them to selected locations.
- A QListWidget to display where a selected product is currently stored.
- A QGraphicsView to visually represent storage locations and highlight product placements.
- Dialogs for adding/editing locations (`LocationEditDialog`) and assigning products
  to locations (`AssignProductDialog`).

It interacts with `item_locations_crud` for database operations related to locations
and product-location links, and with `products_crud` for searching products.
"""
import sys
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeView, QDialog, QLineEdit, QComboBox, QTextEdit,
    QMessageBox, QInputDialog, QFormLayout, QLabel, QSplitter,
    QGroupBox, QListWidget, QListWidgetItem, QSpinBox,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor, QPen, QBrush, QPainter
from PyQt5.QtCore import Qt, QModelIndex, QRectF

# CRUD imports
try:
    from db.cruds.item_locations_crud import (
        add_item_location, get_item_location_by_id,
        get_item_locations_by_parent_id, get_all_item_locations,
        update_item_location, delete_item_location,
        link_item_to_location, get_locations_for_item,
        update_item_in_location, get_item_in_specific_location,
        get_full_location_path_str # Added
    )
    from db.cruds.products_crud import get_products_by_name_pattern # Assuming this exists
except ImportError:
    import os
    project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root_path not in sys.path:
        sys.path.insert(0, project_root_path)
    from db.cruds.item_locations_crud import (
        add_item_location, get_item_location_by_id,
        get_item_locations_by_parent_id, get_all_item_locations,
        update_item_location, delete_item_location,
        link_item_to_location, get_locations_for_item,
        update_item_in_location, get_item_in_specific_location,
        get_full_location_path_str # Added
    )
    # Attempt to import products_crud similarly if needed for standalone testing
    try:
        from db.cruds.products_crud import get_products_by_name_pattern
    except ImportError:
        print("Warning: products_crud.get_products_by_name_pattern not found. Product search will not work.")
        def get_products_by_name_pattern(*args, **kwargs): # Dummy function
            return {'success': False, 'error': 'products_crud not available'}


class LocationEditDialog(QDialog):
    def __init__(self, location_data=None, parent_id=None, existing_locations=None, parent_widget=None):
        """
        Initializes the LocationEditDialog.

        Args:
            location_data (dict, optional): Data of an existing location to edit. Defaults to None (for adding).
            parent_id (str, optional): ID of the parent location if adding a child. Defaults to None.
            existing_locations (list, optional): List of (name, id) tuples of all locations, used for parent selection.
            parent_widget (QWidget, optional): Parent widget for the dialog.
        """
        super().__init__(parent_widget)
        self.location_data = location_data # Stores data of location being edited, if any
        self.parent_id = parent_id         # Suggested parent_id when adding a new location
        self.existing_locations = existing_locations if existing_locations else []

        self.setWindowTitle(self.tr("Edit Location") if location_data else self.tr("Add Location"))
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        # Form layout for input fields
        form_layout = QFormLayout()

        self.name_edit = QLineEdit(location_data.get('location_name', '') if location_data else '')
        self.type_combo = QComboBox()
        self.type_combo.addItems([self.tr("Area"), self.tr("Cupboard"), self.tr("Shelf"), self.tr("Bin"),
                                  self.tr("Room"), self.tr("Building"), self.tr("Other")])
        if location_data and location_data.get('location_type'):
            self.type_combo.setCurrentText(location_data.get('location_type'))

        self.description_edit = QTextEdit(location_data.get('description', '') if location_data else '')
        self.description_edit.setFixedHeight(80) # Set a reasonable default height

        # Parent location selection
        self.parent_combo = QComboBox()
        self.parent_combo.addItem(self.tr("None (Top Level)"), None) # Option for no parent
        current_parent_id_to_select = self.parent_id # Default to passed parent_id for new locations
        if location_data and location_data.get('parent_location_id'): # If editing, use existing parent
            current_parent_id_to_select = location_data.get('parent_location_id')

        for loc_name, loc_id in self.existing_locations:
            # Prevent a location from being its own parent during editing
            if self.location_data and self.location_data.get('location_id') == loc_id:
                continue
            self.parent_combo.addItem(loc_name, loc_id)
            if loc_id == current_parent_id_to_select:
                self.parent_combo.setCurrentIndex(self.parent_combo.count() - 1) # Select this parent

        # If no specific parent was selected (e.g. adding top-level or parent_id was None)
        if current_parent_id_to_select is None and self.parent_combo.count() > 0:
             self.parent_combo.setCurrentIndex(0) # Default to "None (Top Level)"

        # Visual coordinates input
        self.visual_coords_edit = QLineEdit(location_data.get('visual_coordinates', '') if location_data else '')
        self.visual_coords_edit.setPlaceholderText(self.tr('e.g., {"x":0, "y":0, "width":100, "height":50, "color":"#aabbcc"}'))
        self.visual_coords_edit.setToolTip(
            self.tr('JSON format: {"x": int, "y": int, "width": int, "height": int, "color": "#RRGGBB" (optional)}')
        )

        form_layout.addRow(self.tr("Name:"), self.name_edit)
        form_layout.addRow(self.tr("Type:"), self.type_combo)
        form_layout.addRow(self.tr("Parent Location:"), self.parent_combo)
        form_layout.addRow(self.tr("Description:"), self.description_edit)
        form_layout.addRow(self.tr("Visual Coordinates (JSON):"), self.visual_coords_edit)

        layout.addLayout(form_layout)

        # Standard OK and Cancel buttons
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton(self.tr("OK"))
        self.cancel_button = QPushButton(self.tr("Cancel"))
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)

        layout.addLayout(buttons_layout)

        self.ok_button.clicked.connect(self.accept_data)
        self.cancel_button.clicked.connect(self.reject)

    def accept_data(self):
        """
        Validates input data and attempts to save the location (add new or update existing)
        using the item_locations_crud functions. Closes dialog on success.
        """
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, self.tr("Input Error"), self.tr("Location name cannot be empty."))
            return

        visual_coords_str = self.visual_coords_edit.text().strip()
        if visual_coords_str: # Validate JSON format if provided
            try:
                json.loads(visual_coords_str)
            except json.JSONDecodeError:
                QMessageBox.warning(self, self.tr("Input Error"), self.tr("Visual coordinates must be a valid JSON string."))
                return

        selected_parent_index = self.parent_combo.currentIndex()
        # Get the data associated with the selected parent item (which is the parent_location_id or None)
        parent_id_val = self.parent_combo.itemData(selected_parent_index) if selected_parent_index >=0 else None

        # Prepare data payload for CRUD operation
        data = {
            'location_name': name,
            'location_type': self.type_combo.currentText(),
            'parent_location_id': parent_id_val,
            'description': self.description_edit.toPlainText().strip(),
            'visual_coordinates': visual_coords_str if visual_coords_str else None, # Store as string
        }

        if self.location_data: # Editing an existing location
            result = update_item_location(self.location_data['location_id'], data)
        else: # Adding a new location
            result = add_item_location(data)

        if result.get('success'):
            QMessageBox.information(self, self.tr("Success"), self.tr("Location saved successfully."))
            self.accept() # Close dialog with QDialog.Accepted result
        else:
            QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to save location: {0}").format(result.get('error', 'Unknown error')))


class InventoryBrowserWidget(QWidget):
    """
    Main widget for browsing and managing inventory locations and product assignments.
    It features a tree view for location hierarchy, product search capabilities,
    and a visual map of locations using QGraphicsScene.
    """
    def __init__(self, parent=None):
        """
        Initializes the InventoryBrowserWidget.

        Args:
            parent (QWidget, optional): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle(self.tr("Inventory Browser"))
        self.setMinimumSize(900, 700) # Increased size for better layout with graphics view

        # Main layout structure using a splitter
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # --- Left Panel: Location Hierarchy ---
        location_panel = QWidget()
        location_layout = QVBoxLayout(location_panel)

        # Tree view for displaying locations
        self.tree_view = QTreeView()
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels([self.tr('Location Name'), self.tr('Type'), self.tr('ID')])
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setColumnWidth(0, 220)
        self.tree_view.setColumnWidth(1, 100)
        self.tree_view.setEditTriggers(QTreeView.NoEditTriggers) # Disable direct editing
        location_layout.addWidget(self.tree_view)

        # Buttons for location management
        location_buttons_layout = QHBoxLayout()
        self.add_loc_button = QPushButton(self.tr("Add Location"))
        self.edit_loc_button = QPushButton(self.tr("Edit Location"))
        self.delete_loc_button = QPushButton(self.tr("Delete Location"))
        self.refresh_loc_button = QPushButton(self.tr("Refresh Tree"))
        location_buttons_layout.addWidget(self.add_loc_button)
        location_buttons_layout.addWidget(self.edit_loc_button)
        location_buttons_layout.addWidget(self.delete_loc_button)
        location_buttons_layout.addStretch()
        location_buttons_layout.addWidget(self.refresh_loc_button)
        location_layout.addLayout(location_buttons_layout)

        splitter.addWidget(location_panel)

        # --- Right Panel: Product Management & Visuals ---
        right_panel_splitter = QSplitter(Qt.Vertical) # Split right panel for product info and visuals

        # Top-Right: Product Search and Assignment
        product_management_widget = QWidget()
        product_management_layout = QVBoxLayout(product_management_widget)

        product_search_group = QGroupBox(self.tr("Product Search & Assignment"))
        search_group_layout = QVBoxLayout(product_search_group)
        self.product_search_input = QLineEdit()
        self.product_search_input.setPlaceholderText(self.tr("Enter product name or code..."))
        search_group_layout.addWidget(self.product_search_input)
        self.search_product_button = QPushButton(self.tr("Search Product"))
        search_group_layout.addWidget(self.search_product_button)
        search_group_layout.addWidget(QLabel(self.tr("Search Results:")))
        self.product_search_results_list = QListWidget()
        search_group_layout.addWidget(self.product_search_results_list)
        self.assign_product_button = QPushButton(self.tr("Assign Selected Product to Selected Location"))
        self.assign_product_button.setEnabled(False)
        search_group_layout.addWidget(self.assign_product_button)
        product_management_layout.addWidget(product_search_group)

        product_locations_group = QGroupBox(self.tr("Product Locations"))
        locations_group_layout = QVBoxLayout(product_locations_group)
        self.product_locations_display_list = QListWidget() # Displays text of where product is
        locations_group_layout.addWidget(self.product_locations_display_list)
        product_management_layout.addWidget(product_locations_group)
        right_panel_splitter.addWidget(product_management_widget)

        # Bottom-Right: Visual Location Map
        visual_display_group = QGroupBox(self.tr("Visual Location Map"))
        visual_display_layout = QVBoxLayout(visual_display_group)
        self.graphics_view = QGraphicsView()
        self.graphics_scene = QGraphicsScene(self) # Scene to draw on
        self.graphics_view.setScene(self.graphics_scene)
        self.graphics_view.setRenderHint(QPainter.Antialiasing, True) # Smoother rendering
        visual_display_layout.addWidget(self.graphics_view)
        right_panel_splitter.addWidget(visual_display_group)

        splitter.addWidget(right_panel_splitter)
        splitter.setSizes([350, 550]) # Initial sizes for left and right panels
        right_panel_splitter.setSizes([350, 350]) # Initial sizes for top and bottom of right panel


        # --- Instance Variables for State ---
        self.scene_items = {}  # Maps location_id to its QGraphicsRectItem
        self.highlighted_scene_items = [] # List of currently highlighted QGraphicsRectItems


        # --- Connect Signals to Slots ---
        self.add_loc_button.clicked.connect(self.open_add_location_dialog)
        self.edit_loc_button.clicked.connect(self.open_edit_location_dialog)
        self.delete_loc_button.clicked.connect(self.delete_selected_location)
        self.refresh_loc_button.clicked.connect(self.load_locations_into_tree)
        self.tree_view.doubleClicked.connect(self.open_edit_location_dialog)

        self.search_product_button.clicked.connect(self.search_products)
        # Ensure on_product_selection_changed handles both button state and displaying locations
        self.product_search_results_list.itemSelectionChanged.connect(self.on_product_selection_changed)
        self.assign_product_button.clicked.connect(self.open_assign_product_dialog)

        # Initial population of the location tree and visual map
        self.load_locations_into_tree()

    def open_add_location_dialog(self):
        # TODO: Implement the dialog to add a new location.
        # For now, this is a placeholder to prevent AttributeError.
        print(f"Placeholder: {self.__class__.__name__}.open_add_location_dialog() called.")
        # Consider raising NotImplementedError or showing a QMessageBox if appropriate
        # QMessageBox.information(self, "Not Implemented", "This feature is not yet implemented.")
        pass

    def open_edit_location_dialog(self):
        # TODO: Implement the dialog to edit an existing location.
        # For now, this is a placeholder to prevent AttributeError.
        print(f"Placeholder: {self.__class__.__name__}.open_edit_location_dialog() called.")
        # Consider raising NotImplementedError or showing a QMessageBox if appropriate
        # QMessageBox.information(self, "Not Implemented", "This feature (edit location) is not yet implemented.")
        pass

    def update_assign_button_state(self):
        """
        Enables or disables the 'Assign Product to Selected Location' button.
        The button is enabled only if an item is selected in both the product search results
        list and the location tree view.
        """
        product_selected = bool(self.product_search_results_list.currentItem())
        selected_location_data, selected_tree_item = self.get_selected_location_data_from_tree()

        if not selected_product_item or not selected_location_data:
            QMessageBox.information(self, "Assign Product", "Please select both a product and a location.")
            return

        product_id = selected_product_item.data(Qt.UserRole)
        product_name = selected_product_item.data(Qt.UserRole+1) # Name stored in item

        # Fetch and display locations for the selected product
        response = get_locations_for_item(item_id=product_id)

        if response['success']:
            locations = response['data']
            if locations:
                for loc_detail in locations:
                    # Assuming get_full_location_path_str is available and works as intended
                    full_path = get_full_location_path_str(loc_detail['location_id'])
                    display_text = f"{full_path} (Qty: {loc_detail.get('quantity', 'N/A')})"
                    if loc_detail.get('notes'):
                        display_text += f" - Notes: {loc_detail['notes']}"

                    item = QListWidgetItem(display_text)
                    item.setData(Qt.UserRole, loc_detail['location_id']) # Store location_id for map interaction
                    self.product_locations_display_list.addItem(item)

                    # Highlight this location on the map
                    self.highlight_location_on_map(loc_detail['location_id']) # Assuming this method exists
            else:
                self.product_locations_display_list.addItem(self.tr(f"No assigned locations found for {product_name}."))
        else:
            QMessageBox.warning(self, self.tr("Error"),
                                self.tr("Could not retrieve locations for {0}: {1}").format(product_name, response.get('error', 'Unknown error')))

        location_id = selected_location_data['location_id']
        location_name = selected_location_data['location_name']

        # Check if product is already in this location to prefill data or decide action
        existing_link_response = get_item_in_specific_location(product_id, location_id)
        existing_link_data = None
        if existing_link_response['success'] and existing_link_response['data']:
            existing_link_data = existing_link_response['data']
        elif not existing_link_response['success']:
            QMessageBox.critical(self, "Error", f"Could not check existing product link: {existing_link_response['error']}")
            return


        dialog = AssignProductDialog(product_id, product_name, location_id, location_name,
                                     existing_link_data=existing_link_data, parent_widget=self)
        if dialog.exec_():
            self.display_product_locations() # Refresh the list for the current product


class AssignProductDialog(QDialog):
    def __init__(self, product_id, product_name, location_id, location_name,
                 existing_link_data=None, parent_widget=None):
        super().__init__(parent_widget)
        self.product_id = product_id
        self.location_id = location_id
        self.existing_link_data = existing_link_data # This is ProductStorageLocation entry if exists

        action = "Update" if existing_link_data else "Assign"
        self.setWindowTitle(f"{action} Product to Location")
        self.setModal(True)
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        form_layout.addRow(QLabel(f"Product: {product_name} (ID: {product_id})"))
        form_layout.addRow(QLabel(f"Location: {location_name} (ID: {location_id})"))

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(0, 999999) # Max quantity
        self.quantity_spin.setValue(existing_link_data.get('quantity', 1) if existing_link_data else 1)
        form_layout.addRow("Quantity:", self.quantity_spin)

        self.notes_edit = QLineEdit(existing_link_data.get('notes', '') if existing_link_data else '')
        form_layout.addRow("Notes:", self.notes_edit)

        layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.ok_button.clicked.connect(self.accept_assignment)
        self.cancel_button.clicked.connect(self.reject)

    def accept_assignment(self):
        data = {
            'product_id': self.product_id,
            'location_id': self.location_id,
            'quantity': self.quantity_spin.value(),
            'notes': self.notes_edit.text().strip()
        }

        if self.existing_link_data: # Update existing link
            psl_id = self.existing_link_data['product_storage_location_id']
            # update_item_in_location only takes quantity and notes in update_data
            update_payload = {'quantity': data['quantity'], 'notes': data['notes']}
            result = update_item_in_location(psl_id, update_payload)
        else: # Create new link
            result = link_item_to_location(data)

        if result.get('success'):
            QMessageBox.information(self, "Success", "Product assignment saved.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", f"Failed: {result.get('error', 'Unknown error')}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Placeholder for DB path configuration as in previous version
    # from db.connection import DB_PATH, set_db_path
    # import os
    # if not os.path.exists(DB_PATH):
    #     test_db_path = os.path.join(os.path.dirname(__file__), "..", "app_data_test.db")
    #     print(f"Using test DB path: {test_db_path}")
    #     set_db_path(test_db_path)
    #     from db.init_schema import initialize_database
    #     initialize_database()

    main_window = InventoryBrowserWidget()
    main_window.show()
    sys.exit(app.exec_())