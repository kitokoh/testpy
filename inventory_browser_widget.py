import sys
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeView, QDialog, QLineEdit, QComboBox, QTextEdit,
    QMessageBox, QInputDialog, QFormLayout, QLabel, QSplitter,
    QGroupBox, QListWidget, QListWidgetItem, QSpinBox,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor, QPen, QBrush
from PyQt5.QtCore import Qt, QModelIndex, QRectF

# CRUD imports
try:
    from db.cruds.item_locations_crud import (
        add_item_location, get_item_location_by_id,
        get_item_locations_by_parent_id, get_all_item_locations,
        update_item_location, delete_item_location,
        link_product_to_location, get_locations_for_product,
        update_product_in_location, get_product_in_specific_location,
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
        link_product_to_location, get_locations_for_product,
        update_product_in_location, get_product_in_specific_location,
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
        super().__init__(parent_widget)
        self.location_data = location_data
        self.parent_id = parent_id
        self.existing_locations = existing_locations if existing_locations else [] # List of (name, id) tuples

        self.setWindowTitle("Edit Location" if location_data else "Add Location")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_edit = QLineEdit(location_data.get('location_name', '') if location_data else '')
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Area", "Cupboard", "Shelf", "Bin", "Room", "Building", "Other"])
        if location_data and location_data.get('location_type'):
            self.type_combo.setCurrentText(location_data.get('location_type'))

        self.description_edit = QTextEdit(location_data.get('description', '') if location_data else '')
        self.description_edit.setFixedHeight(80)

        self.parent_combo = QComboBox()
        self.parent_combo.addItem("None (Top Level)", None)
        current_parent_id_to_select = self.parent_id
        if location_data and location_data.get('parent_location_id'):
            current_parent_id_to_select = location_data.get('parent_location_id')

        for loc_name, loc_id in self.existing_locations:
            # Prevent setting a location as its own parent if editing
            if self.location_data and self.location_data.get('location_id') == loc_id:
                continue
            self.parent_combo.addItem(loc_name, loc_id)
            if loc_id == current_parent_id_to_select:
                self.parent_combo.setCurrentIndex(self.parent_combo.count() - 1)

        if current_parent_id_to_select is None and self.parent_combo.count() > 0:
             self.parent_combo.setCurrentIndex(0)


        self.visual_coords_edit = QLineEdit(location_data.get('visual_coordinates', '') if location_data else '')
        self.visual_coords_edit.setPlaceholderText('e.g., {"x":0, "y":0, "width":100, "height":50, "color":"#aabbcc"}')
        self.visual_coords_edit.setToolTip(
            'JSON format: {"x": int, "y": int, "width": int, "height": int, "color": "#RRGGBB" (optional)}'
        )

        form_layout.addRow("Name:", self.name_edit)
        form_layout.addRow("Type:", self.type_combo)
        form_layout.addRow("Parent Location:", self.parent_combo)
        form_layout.addRow("Description:", self.description_edit)
        form_layout.addRow("Visual Coordinates (JSON):", self.visual_coords_edit)

        layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)

        layout.addLayout(buttons_layout)

        self.ok_button.clicked.connect(self.accept_data)
        self.cancel_button.clicked.connect(self.reject)

    def accept_data(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Input Error", "Location name cannot be empty.")
            return

        visual_coords_str = self.visual_coords_edit.text().strip()
        if visual_coords_str:
            try:
                json.loads(visual_coords_str) # Validate JSON
            except json.JSONDecodeError:
                QMessageBox.warning(self, "Input Error", "Visual coordinates must be a valid JSON string.")
                return

        selected_parent_index = self.parent_combo.currentIndex()
        parent_id_val = self.parent_combo.itemData(selected_parent_index) if selected_parent_index >=0 else None


        data = {
            'location_name': name,
            'location_type': self.type_combo.currentText(),
            'parent_location_id': parent_id_val,
            'description': self.description_edit.toPlainText().strip(),
            'visual_coordinates': visual_coords_str if visual_coords_str else None,
        }

        if self.location_data: # Editing existing location
            result = update_item_location(self.location_data['location_id'], data)
        else: # Adding new location
            result = add_item_location(data)

        if result.get('success'):
            QMessageBox.information(self, "Success", "Location saved successfully.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", f"Failed to save location: {result.get('error', 'Unknown error')}")


class InventoryBrowserWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Inventory Browser")
        self.setMinimumSize(800, 600) # Increased size

        # Main layout
        main_layout = QHBoxLayout(self) # Changed to QHBoxLayout for splitter

        # Splitter for resizable sections
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left Panel: Location Hierarchy
        location_panel = QWidget()
        location_layout = QVBoxLayout(location_panel)

        self.tree_view = QTreeView()
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(['Location Name', 'Type', 'ID'])
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setColumnWidth(0, 200) # Adjusted width
        self.tree_view.setColumnWidth(1, 80)
        self.tree_view.setEditTriggers(QTreeView.NoEditTriggers)
        location_layout.addWidget(self.tree_view)

        location_buttons_layout = QHBoxLayout()
        self.add_loc_button = QPushButton("Add Location")
        self.edit_loc_button = QPushButton("Edit Location")
        self.delete_loc_button = QPushButton("Delete Location")
        self.refresh_loc_button = QPushButton("Refresh Tree")
        location_buttons_layout.addWidget(self.add_loc_button)
        location_buttons_layout.addWidget(self.edit_loc_button)
        location_buttons_layout.addWidget(self.delete_loc_button)
        location_buttons_layout.addStretch()
        location_buttons_layout.addWidget(self.refresh_loc_button)
        location_layout.addLayout(location_buttons_layout)

        splitter.addWidget(location_panel)

        # Right Panel: Product Management
        product_panel = QWidget()
        product_layout = QVBoxLayout(product_panel)

        # Product Search Group
        product_search_group = QGroupBox("Product Search & Assignment")
        search_group_layout = QVBoxLayout(product_search_group)

        self.product_search_input = QLineEdit()
        self.product_search_input.setPlaceholderText("Enter product name or code...")
        search_group_layout.addWidget(self.product_search_input)

        self.search_product_button = QPushButton("Search Product")
        search_group_layout.addWidget(self.search_product_button)

        self.product_search_results_list = QListWidget()
        search_group_layout.addWidget(QLabel("Search Results:"))
        search_group_layout.addWidget(self.product_search_results_list)

        self.assign_product_button = QPushButton("Assign Selected Product to Selected Location")
        self.assign_product_button.setEnabled(False) # Disabled by default
        search_group_layout.addWidget(self.assign_product_button)

        product_layout.addWidget(product_search_group)

        # Product Locations Display Group
        product_locations_group = QGroupBox("Product Locations")
        locations_group_layout = QVBoxLayout(product_locations_group)
        self.product_locations_display_list = QListWidget()
        locations_group_layout.addWidget(self.product_locations_display_list)
        product_layout.addWidget(product_locations_group)

        # Visual Display Group (QGraphicsView)
        visual_display_group = QGroupBox("Visual Location Map")
        visual_display_layout = QVBoxLayout(visual_display_group)
        self.graphics_view = QGraphicsView()
        self.graphics_scene = QGraphicsScene(self)
        self.graphics_view.setScene(self.graphics_scene)
        self.graphics_view.setRenderHint(QColor.Antialiasing, True) # Corrected QPainter import
        visual_display_layout.addWidget(self.graphics_view)
        product_layout.addWidget(visual_display_group)

        splitter.addWidget(product_panel)
        # Adjust splitter sizes to accommodate the new visual panel, or make product_panel wider
        splitter.setSizes([300, 500])


        # Instance variable to keep track of drawn graphics items by location_id
        self.scene_items = {} # {location_id: QGraphicsRectItem}
        self.highlighted_scene_items = []


        # Connect signals
        self.add_loc_button.clicked.connect(self.open_add_location_dialog)
        self.edit_loc_button.clicked.connect(self.open_edit_location_dialog)
        self.delete_loc_button.clicked.connect(self.delete_selected_location)
        self.refresh_loc_button.clicked.connect(self.load_locations_into_tree)
        self.tree_view.doubleClicked.connect(self.open_edit_location_dialog)
        self.tree_view.selectionModel().selectionChanged.connect(self.on_tree_location_selected) # For visual sync
        self.tree_view.selectionModel().selectionChanged.connect(self.update_assign_button_state)


        self.search_product_button.clicked.connect(self.search_products)
        self.product_search_results_list.itemSelectionChanged.connect(self.on_product_selection_changed)
        self.assign_product_button.clicked.connect(self.open_assign_product_dialog)

        self.load_locations_into_tree() # This will also trigger draw_locations_on_scene

    def update_assign_button_state(self):
        product_selected = bool(self.product_search_results_list.currentItem())
        location_selected = bool(self.tree_view.selectedIndexes())
        self.assign_product_button.setEnabled(product_selected and location_selected)

    def _get_all_locations_for_parent_combo(self):
        """Fetches all locations as a flat list of (name, id) for parent selection."""
        response = get_all_item_locations()
        if response['success']:
            return [(loc['location_name'], loc['location_id']) for loc in response['data']]
        else:
            QMessageBox.critical(self, "Error", f"Could not load locations for parent selection: {response.get('error')}")
            return []

    def load_locations_into_tree(self):
        self.tree_model.removeRows(0, self.tree_model.rowCount())
        response = get_item_locations_by_parent_id(parent_location_id=None)
        if response['success']:
            top_level_locations = response['data']
            for location in top_level_locations:
                parent_item_for_tree = self.tree_model.invisibleRootItem()
                self._add_location_to_tree(parent_item_for_tree, location)
        else:
            QMessageBox.critical(self, "Error Loading Locations",
                                 f"Failed to load top-level locations: {response.get('error', 'Unknown error')}")
        self.tree_view.expandAll()
        self.draw_locations_on_scene() # Draw after loading tree

    def _add_location_to_tree(self, parent_item_for_tree: QStandardItem, location_data: dict):
        item_name = QStandardItem(location_data.get('location_name', 'N/A'))
        item_name.setData(location_data.get('location_id'), Qt.UserRole) # Store ID
        item_name.setData(location_data.get('location_name'), Qt.UserRole + 1) # Store name for dialog

        item_type = QStandardItem(location_data.get('location_type', 'N/A'))
        item_id_display = QStandardItem(location_data.get('location_id', 'N/A'))

        parent_item_for_tree.appendRow([item_name, item_type, item_id_display])

        children_response = get_item_locations_by_parent_id(location_data['location_id'])
        if children_response['success']:
            for child_location in children_response['data']:
                self._add_location_to_tree(item_name, child_location)
        elif children_response.get('error'):
             QMessageBox.warning(self, "Error Loading Child Locations",
                                f"Failed to load children for {location_data.get('location_name')}: {children_response.get('error')}")

    def get_selected_location_data_from_tree(self) -> (dict | None, QStandardItem | None):
        selected_indexes = self.tree_view.selectedIndexes()
        if not selected_indexes:
            return None, None

        selected_item = self.tree_model.itemFromIndex(selected_indexes[0]) # Get item from first column
        if not selected_item:
             return None, None

        location_id = selected_item.data(Qt.UserRole)
        if location_id:
            # Fetch full data for consistency, though name is also stored
            response = get_item_location_by_id(location_id)
            if response['success']:
                return response['data'], selected_item
            else:
                QMessageBox.warning(self, "Error", f"Could not fetch details for location ID {location_id}: {response.get('error')}")
        return None, selected_item

    def open_add_location_dialog(self):
        parent_id_for_dialog = None
        _, selected_tree_item = self.get_selected_location_data_from_tree()

        if selected_tree_item:
            parent_id_for_dialog = selected_tree_item.data(Qt.UserRole)
            parent_name_for_dialog = selected_tree_item.data(Qt.UserRole + 1) # Name stored
            reply = QMessageBox.question(self, 'Select Parent Context',
                                       f"Add new location under '{parent_name_for_dialog}'?\n"
                                       "Select 'No' to add as a new top-level location.",
                                       QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Cancel: return
            if reply == QMessageBox.No: parent_id_for_dialog = None

        all_locs = self._get_all_locations_for_parent_combo()
        dialog = LocationEditDialog(parent_id=parent_id_for_dialog, existing_locations=all_locs, parent_widget=self)
        if dialog.exec_():
            self.load_locations_into_tree() # This will also redraw scene

    def open_edit_location_dialog(self, index: QModelIndex = None):
        location_to_edit, _ = self.get_selected_location_data_from_tree()
        if not location_to_edit:
            QMessageBox.information(self, "Edit Location", "Please select a location from the tree to edit.")
            return
        all_locs = self._get_all_locations_for_parent_combo()
        dialog = LocationEditDialog(location_data=location_to_edit, existing_locations=all_locs, parent_widget=self)
        if dialog.exec_():
            self.load_locations_into_tree() # This will also redraw scene

    def delete_selected_location(self):
        location_to_delete, _ = self.get_selected_location_data_from_tree()
        if not location_to_delete:
            QMessageBox.information(self, "Delete Location", "Please select a location to delete.")
            return

        loc_id = location_to_delete['location_id']
        loc_name = location_to_delete['location_name']
        reply = QMessageBox.warning(self, "Confirm Delete",
                                    f"Delete '{loc_name}' (ID: {loc_id})?\n"
                                    "Products in this location will be unlinked (due to ON DELETE CASCADE in DB schema for ProductStorageLocations). "
                                    "Child locations may cause issues if not handled by DB (this UI checks).",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            children_resp = get_item_locations_by_parent_id(loc_id)
            if children_resp['success'] and children_resp['data']:
                QMessageBox.warning(self, "Deletion Blocked", f"'{loc_name}' has child locations. Delete or re-parent them first.")
                return

            del_result = delete_item_location(loc_id)
            if del_result.get('success'):
                QMessageBox.information(self, "Success", f"Location '{loc_name}' deleted.")
                self.load_locations_into_tree() # This will also redraw scene
            else:
                QMessageBox.critical(self, "Error", f"Delete failed: {del_result.get('error', 'Unknown error')}")

    def draw_locations_on_scene(self):
        self.graphics_scene.clear()
        self.scene_items.clear()
        # Reset highlights as the items are being redrawn
        self.highlighted_scene_items.clear()


        all_locs_response = get_all_item_locations()
        if not all_locs_response['success']:
            QMessageBox.critical(self, "Error Drawing Locations", f"Could not fetch all locations: {all_locs_response.get('error')}")
            return

        for loc in all_locs_response['data']:
            coords_str = loc.get('visual_coordinates')
            if coords_str:
                try:
                    coords = json.loads(coords_str)
                    x, y, w, h = coords.get('x'), coords.get('y'), coords.get('width'), coords.get('height')
                    color_hex = coords.get('color', "#cccccc") # Default color

                    if None not in [x, y, w, h]:
                        rect_item = QGraphicsRectItem(x, y, w, h)
                        rect_item.setBrush(QColor(color_hex))
                        rect_item.setData(0, loc['location_id']) # Store location_id

                        # Basic click handling
                        rect_item.setFlag(QGraphicsRectItem.ItemIsSelectable) # Allow selection for visual feedback
                        # To connect click to tree selection, a custom QGraphicsRectItem or event filter is better.
                        # For now, this just makes it selectable on scene.

                        self.graphics_scene.addItem(rect_item)
                        self.scene_items[loc['location_id']] = rect_item

                        text_item = QGraphicsTextItem(loc.get('location_name', 'N/A'), rect_item)
                        # Center text within the rect item, roughly
                        text_rect = text_item.boundingRect()
                        text_item.setPos(x + w/2 - text_rect.width()/2, y + h/2 - text_rect.height()/2)
                        # self.graphics_scene.addItem(text_item) # Added as child of rect_item

                except json.JSONDecodeError:
                    print(f"Warning: Invalid JSON for visual_coordinates in location {loc.get('location_id')}: {coords_str}")
                except Exception as e:
                    print(f"Warning: Could not draw location {loc.get('location_id')} due to error: {e}")

        # Adjust scene rect to fit all items
        # self.graphics_scene.setSceneRect(self.graphics_scene.itemsBoundingRect())
        # Or set a fixed large scene rect if items are spread out
        self.graphics_view.setSceneRect(self.graphics_scene.itemsBoundingRect().adjusted(-20, -20, 20, 20))


    def search_products(self):
        search_term = self.product_search_input.text().strip()
        if not search_term:
            QMessageBox.information(self, "Search Product", "Please enter a product name or code to search.")
            return

        # Assuming get_products_by_name_pattern exists and works as expected
        result = get_products_by_name_pattern(search_term)
        self.product_search_results_list.clear()
        if result['success']:
            products = result['data']
            if not products:
                self.product_search_results_list.addItem("No products found.")
            for prod in products:
                # Ensure product_id, product_name, product_code are present
                item_text = f"{prod.get('product_name', 'N/A')} (Code: {prod.get('product_code', 'N/A')})"
                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.UserRole, prod.get('product_id')) # Store product_id
                list_item.setData(Qt.UserRole + 1, prod.get('product_name')) # Store name
                self.product_search_results_list.addItem(list_item)
        else:
            QMessageBox.critical(self, "Search Error", f"Failed to search products: {result.get('error', 'Unknown error')}")
        self.update_assign_button_state()
        self.product_locations_display_list.clear()
        self.update_visual_highlights() # Clear highlights from previous search

    def on_product_selection_changed(self):
        self.update_assign_button_state()
        self.display_product_locations() # This will also call update_visual_highlights

    def on_tree_location_selected(self):
        # This is a basic way to sync tree selection to visual map (e.g. by re-applying highlights)
        # More advanced would be to center view on selected, etc.
        self.update_visual_highlights(highlight_tree_selection=True)


    def display_product_locations(self):
        self.product_locations_display_list.clear()
        selected_product_item = self.product_search_results_list.currentItem()
        # Reset previous highlights first
        for item in self.highlighted_scene_items:
            if isinstance(item, QGraphicsRectItem): # Ensure it's a rect item
                original_pen = item.data(1) # Assuming original pen stored at key 1
                original_brush = item.data(2) # Assuming original brush stored at key 2
                if original_pen: item.setPen(original_pen)
                else: item.setPen(QPen(Qt.black)) # Default
                if original_brush: item.setBrush(original_brush)
                else: item.setBrush(QBrush(Qt.lightGray)) # Default
        self.highlighted_scene_items.clear()

        if not selected_product_item:
            self.update_visual_highlights() # Call to ensure highlights are cleared
            return

        product_id = selected_product_item.data(Qt.UserRole)
        if not product_id:
            self.update_visual_highlights()
            return

        product_name = selected_product_item.data(Qt.UserRole + 1)

        result = get_locations_for_product(product_id)
        found_locations_ids = []
        if result['success']:
            locations_data = result['data']
            if not locations_data:
                self.product_locations_display_list.addItem(f"'{product_name}' is not currently stored in any location.")
            else:
                self.product_locations_display_list.addItem(f"Locations for '{product_name}':")
                for loc_info in locations_data:
                    psl_location_id = loc_info.get('location_id')
                    found_locations_ids.append(psl_location_id)
                    path_result = get_full_location_path_str(psl_location_id)
                    path_str = path_result['data'] if path_result['success'] else loc_info.get('location_name', 'Unknown Location')
                    quantity = loc_info.get('quantity', 'N/A')
                    notes = loc_info.get('notes', '')
                    display_text = f"- {path_str} (Qty: {quantity})"
                    if notes: display_text += f" [Notes: {notes}]"
                    self.product_locations_display_list.addItem(display_text)
        else:
            QMessageBox.critical(self, "Error", f"Failed to get locations for product: {result.get('error', 'Unknown error')}")

        self.update_visual_highlights(product_locations_ids=found_locations_ids)


    def update_visual_highlights(self, product_locations_ids=None, highlight_tree_selection=False):
        # Reset previous product highlights if not handling tree selection highlight
        if not highlight_tree_selection:
            for item in self.highlighted_scene_items:
                original_pen = item.data(1)
                original_brush = item.data(2)
                if original_pen: item.setPen(original_pen)
                else: item.setPen(QPen(Qt.black))
                if original_brush: item.setBrush(original_brush)
                else: item.setBrush(QBrush(Qt.lightGray))
            self.highlighted_scene_items.clear()

        # Highlight locations for the current product
        if product_locations_ids:
            for loc_id in product_locations_ids:
                scene_item = self.scene_items.get(loc_id)
                if scene_item:
                    if scene_item not in self.highlighted_scene_items: # Store original only once
                        scene_item.setData(1, scene_item.pen())
                        scene_item.setData(2, scene_item.brush())
                    scene_item.setPen(QPen(QColor("red"), 2)) # Highlight with red border
                    scene_item.setBrush(QBrush(QColor(255, 0, 0, 50))) # Semi-transparent red fill
                    self.highlighted_scene_items.append(scene_item)

        # Highlight based on tree selection (can be additive or exclusive)
        if highlight_tree_selection:
            selected_loc_data, _ = self.get_selected_location_data_from_tree()
            if selected_loc_data:
                tree_selected_loc_id = selected_loc_data.get('location_id')
                scene_item = self.scene_items.get(tree_selected_loc_id)
                if scene_item:
                    if scene_item not in self.highlighted_scene_items:
                         scene_item.setData(1, scene_item.pen())
                         scene_item.setData(2, scene_item.brush())
                    scene_item.setPen(QPen(QColor("blue"), 3, Qt.DashLine)) # Different highlight for tree selection
                    # scene_item.setBrush(QBrush(QColor(0,0,255,30))) # Optional: different fill
                    if scene_item not in self.highlighted_scene_items: # Avoid duplicates if also a product location
                        self.highlighted_scene_items.append(scene_item)


    def open_assign_product_dialog(self):
        selected_product_item = self.product_search_results_list.currentItem()
        selected_location_data, selected_tree_item = self.get_selected_location_data_from_tree()

        if not selected_product_item or not selected_location_data:
            QMessageBox.information(self, "Assign Product", "Please select both a product and a location.")
            return

        product_id = selected_product_item.data(Qt.UserRole)
        product_name = selected_product_item.data(Qt.UserRole+1) # Name stored in item

        location_id = selected_location_data['location_id']
        location_name = selected_location_data['location_name']

        # Check if product is already in this location to prefill data or decide action
        existing_link_response = get_product_in_specific_location(product_id, location_id)
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
            # update_product_in_location only takes quantity and notes in update_data
            update_payload = {'quantity': data['quantity'], 'notes': data['notes']}
            result = update_product_in_location(psl_id, update_payload)
        else: # Create new link
            result = link_product_to_location(data)

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
