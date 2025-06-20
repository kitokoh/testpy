import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLabel, QLineEdit, QComboBox, QDateEdit,
    QGroupBox, QSizePolicy, QMessageBox, QDialog
)
from PyQt5.QtCore import QDate, Qt
import uuid
import logging # Added for logging

from db.cruds import experience_crud
from db.cruds import tags_crud


class ExperienceModuleWidget(QWidget):
    def __init__(self, parent=None, current_user_id=None):
        super().__init__(parent)
        self.setWindowTitle("Experience Management Module")
        self.current_user_id = current_user_id
        self._init_ui()
        self._load_experiences()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        toolbar_layout = QHBoxLayout()
        self.add_experience_button = QPushButton("Add New Experience")
        self.add_experience_button.clicked.connect(self._on_add_experience_clicked)
        toolbar_layout.addWidget(self.add_experience_button)

        self.edit_experience_button = QPushButton("Edit Experience")
        self.edit_experience_button.setEnabled(False)
        self.edit_experience_button.clicked.connect(self._on_edit_experience_clicked)
        toolbar_layout.addWidget(self.edit_experience_button)

        self.delete_experience_button = QPushButton("Delete Experience")
        self.delete_experience_button.setEnabled(False)
        self.delete_experience_button.clicked.connect(self._on_delete_experience_clicked)
        toolbar_layout.addWidget(self.delete_experience_button)
        toolbar_layout.addStretch(1)
        main_layout.addLayout(toolbar_layout)

        filter_groupbox = QGroupBox("Filters")
        filter_layout = QVBoxLayout()

        date_filter_layout = QHBoxLayout()
        self.date_from_edit = QDateEdit()
        self.date_from_edit.setCalendarPopup(True)
        self.date_from_edit.setDate(QDate.currentDate().addMonths(-3))
        self.date_from_edit.setDisplayFormat("yyyy-MM-dd")
        date_filter_layout.addWidget(QLabel("Date From:"))
        date_filter_layout.addWidget(self.date_from_edit)

        self.date_to_edit = QDateEdit()
        self.date_to_edit.setCalendarPopup(True)
        self.date_to_edit.setDate(QDate.currentDate())
        self.date_to_edit.setDisplayFormat("yyyy-MM-dd")
        date_filter_layout.addWidget(QLabel("Date To:"))
        date_filter_layout.addWidget(self.date_to_edit)
        date_filter_layout.addStretch()
        filter_layout.addLayout(date_filter_layout)

        type_tag_filter_layout = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["All Types", "Sale", "Project", "Internal", "Purchase", "Activity", "Other"])
        type_tag_filter_layout.addWidget(QLabel("Type:"))
        type_tag_filter_layout.addWidget(self.type_combo)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("e.g., important, client-visit")
        type_tag_filter_layout.addWidget(QLabel("Tags (comma-separated):"))
        type_tag_filter_layout.addWidget(self.tags_edit)
        self.tags_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        filter_layout.addLayout(type_tag_filter_layout)

        filter_button_layout = QHBoxLayout()
        self.apply_filters_button = QPushButton("Apply Filters")
        self.apply_filters_button.clicked.connect(self._on_filter_clicked)
        filter_button_layout.addWidget(self.apply_filters_button)

        self.clear_filters_button = QPushButton("Clear Filters")
        self.clear_filters_button.clicked.connect(self._on_clear_filters_clicked)
        filter_button_layout.addWidget(self.clear_filters_button)
        filter_button_layout.addStretch()
        filter_layout.addLayout(filter_button_layout)

        filter_groupbox.setLayout(filter_layout)
        main_layout.addWidget(filter_groupbox)

        self.experiences_table = QTableWidget()
        self.experiences_table.setColumnCount(4)
        self.experiences_table.setHorizontalHeaderLabels(["Title", "Date", "Type", "Description (Snippet)"])
        self.experiences_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.experiences_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.experiences_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.experiences_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.experiences_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.experiences_table.itemSelectionChanged.connect(self._on_experience_selection_changed)
        main_layout.addWidget(self.experiences_table)

        self.setLayout(main_layout)

    def _load_experiences(self, passed_filters=None):
        self.experiences_table.setRowCount(0)
        self.experiences_table.clearSelection() # Clear selection when reloading

        filters_dict = {}
        try:
            if passed_filters is None:
                date_from = self.date_from_edit.date().toString(Qt.ISODate)
                date_to = self.date_to_edit.date().toString(Qt.ISODate)
                if date_from and date_to and date_from <= date_to :
                    filters_dict["date_from"] = date_from
                    filters_dict["date_to"] = date_to

                exp_type = self.type_combo.currentText()
                if exp_type != "All Types":
                    filters_dict["type"] = exp_type

                tags_str = self.tags_edit.text().strip()
                if tags_str:
                    filters_dict["tags"] = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            else:
                filters_dict = passed_filters

            self.experiences_table.setEnabled(False)
            self.experiences_table.setPlaceholderText("Loading experiences...")

            experiences_data = experience_crud.get_all_experiences(filters=filters_dict)

            if not experiences_data:
                self.experiences_table.setPlaceholderText("No experiences found for the current filters.")
            else:
                self.experiences_table.setPlaceholderText("")

            for row_num, experience in enumerate(experiences_data):
                self.experiences_table.insertRow(row_num)
                self.experiences_table.setItem(row_num, 0, QTableWidgetItem(experience.get("title", "")))
                self.experiences_table.setItem(row_num, 1, QTableWidgetItem(experience.get("experience_date", "")))
                self.experiences_table.setItem(row_num, 2, QTableWidgetItem(experience.get("type", "")))

                description_snippet = experience.get("description", "")
                if len(description_snippet) > 100:
                    description_snippet = description_snippet[:97] + "..."
                self.experiences_table.setItem(row_num, 3, QTableWidgetItem(description_snippet))

                self.experiences_table.item(row_num, 0).setData(Qt.UserRole, experience.get("experience_id"))

        except Exception as e:
            logging.error(f"Error loading experiences: {e}", exc_info=True)
            QMessageBox.critical(self, "Load Error", f"Could not load experiences: {e}")
            self.experiences_table.setPlaceholderText("Error loading experiences.")
        finally:
            self.experiences_table.setEnabled(True)
            self._on_experience_selection_changed()

    def _handle_tags(self, experience_id, tags_str):
        if not tags_str:
            return True

        tag_names = [name.strip() for name in tags_str.split(',') if name.strip()]
        all_tags_processed_successfully = True

        for tag_name in tag_names:
            try:
                tag = tags_crud.get_tag_by_name(tag_name)
                tag_id_to_link = None
                if not tag:
                    tag_data = {"tag_name": tag_name}
                    created_tag_id = tags_crud.add_tag(tag_data) # Assumes add_tag returns ID
                    if created_tag_id:
                        tag_id_to_link = created_tag_id
                    else: # Fallback if add_tag doesn't return ID
                        newly_created_tag = tags_crud.get_tag_by_name(tag_name)
                        if newly_created_tag: tag_id_to_link = newly_created_tag['tag_id']
                else:
                    tag_id_to_link = tag['tag_id']

                if tag_id_to_link:
                    if not experience_crud.add_experience_tag(experience_id, tag_id_to_link):
                        logging.warning(f"Failed to link tag ID {tag_id_to_link} (Name: {tag_name}) to experience {experience_id}")
                        all_tags_processed_successfully = False
                else:
                    QMessageBox.warning(self, "Tag Error", f"Could not find or create tag ID for: {tag_name}")
                    logging.warning(f"Could not find or create tag ID for: {tag_name} for experience {experience_id}")
                    all_tags_processed_successfully = False
            except Exception as e:
                logging.error(f"Error processing tag '{tag_name}' for exp {experience_id}: {e}", exc_info=True)
                QMessageBox.critical(self, "Tag Processing Error", f"Error processing tag '{tag_name}': {e}")
                all_tags_processed_successfully = False
        return all_tags_processed_successfully

    def _on_add_experience_clicked(self):
        dialog = AddEditExperienceDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            experience_core_data = {
                "title": data["title"], "description": data["description"],
                "experience_date": data["experience_date"], "type": data["type"],
                "user_id": self.current_user_id
            }
            new_experience_id = None
            try:
                new_experience_id = experience_crud.add_experience(experience_core_data)
                if not new_experience_id:
                    raise Exception("add_experience CRUD returned None.")
            except Exception as e:
                logging.error(f"Failed to add core experience: {e}", exc_info=True)
                QMessageBox.critical(self, "Add Error", f"Failed to add experience: {e}")
                return

            tags_ok = self._handle_tags(new_experience_id, data.get("tags_str"))
            entities_ok, media_ok = True, True
            try:
                for entity_link in data.get("related_entities", []):
                    if not experience_crud.add_experience_related_entity(new_experience_id, entity_link['type'], entity_link['id']):
                        entities_ok = False
            except Exception as e: entities_ok = False; logging.error(f"Error adding related entities: {e}", exc_info=True)
            try:
                for media_id in data.get("media_ids", []):
                    if not experience_crud.add_experience_media(new_experience_id, media_id):
                        media_ok = False
            except Exception as e: media_ok = False; logging.error(f"Error adding media links: {e}", exc_info=True)

            if tags_ok and entities_ok and media_ok: QMessageBox.information(self, "Success", "Experience added successfully.")
            else: QMessageBox.warning(self, "Partial Success", "Experience added, but some links may have failed. Please review.")
            self._load_experiences()

    def _on_edit_experience_clicked(self):
        selected_items = self.experiences_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select an experience to edit.")
            return
        experience_id = selected_items[0].row().data(Qt.UserRole) # Assuming ID is in UserRole of first item

        try:
            experience_details = experience_crud.get_experience_by_id(experience_id)
            if not experience_details:
                QMessageBox.critical(self, "Error", "Could not retrieve experience details for editing.")
                return
            experience_details["tags_list"] = experience_crud.get_tags_for_experience(experience_id)
            raw_entities = experience_crud.get_related_entities_for_experience(experience_id)
            experience_details["related_entities"] = [{"type": e["entity_type"], "id": e["entity_id"], "name": f"{e['entity_type']}: {e['entity_id']}"} for e in raw_entities]
            raw_media = experience_crud.get_media_for_experience(experience_id)
            experience_details["media_links"] = [{"id": m["media_item_id"], "name": m.get("media_title", m["media_item_id"])} for m in raw_media]
        except Exception as e:
            logging.error(f"Error fetching details for exp {experience_id} to edit: {e}", exc_info=True)
            QMessageBox.critical(self, "Fetch Error", f"Could not fetch details for editing: {e}")
            return

        dialog = AddEditExperienceDialog(parent=self, experience_data=experience_details)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            update_core_data = {"title": data["title"], "description": data["description"], "experience_date": data["experience_date"], "type": data["type"]}
            update_success = False
            try:
                update_success = experience_crud.update_experience(experience_id, update_core_data)
                if not update_success: raise Exception("update_experience CRUD returned False.")
            except Exception as e:
                logging.error(f"Failed to update core experience {experience_id}: {e}", exc_info=True)
                QMessageBox.critical(self, "Update Error", f"Failed to update core experience: {e}")
                self._load_experiences()
                return

            tags_ok, entities_ok, media_ok = True, True, True
            try: experience_crud.remove_all_tags_for_experience(experience_id); tags_ok = self._handle_tags(experience_id, data.get("tags_str"))
            except Exception as e: tags_ok = False; logging.error(f"Error updating tags: {e}", exc_info=True)
            try:
                experience_crud.remove_all_related_entities_for_experience(experience_id)
                for elink in data.get("related_entities", []):
                    if not experience_crud.add_experience_related_entity(experience_id, elink['type'], elink['id']): entities_ok = False
            except Exception as e: entities_ok = False; logging.error(f"Error updating related entities: {e}", exc_info=True)
            try:
                experience_crud.remove_all_media_for_experience(experience_id)
                for mid in data.get("media_ids", []):
                    if not experience_crud.add_experience_media(experience_id, mid): media_ok = False
            except Exception as e: media_ok = False; logging.error(f"Error updating media links: {e}", exc_info=True)

            if tags_ok and entities_ok and media_ok: QMessageBox.information(self, "Success", "Experience updated successfully.")
            else: QMessageBox.warning(self, "Partial Success", "Experience updated, but some links may have failed. Please review.")
            self._load_experiences()

    def _on_delete_experience_clicked(self):
        selected_items = self.experiences_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select an experience to delete.")
            return
        experience_id = self.experiences_table.item(selected_items[0].row(), 0).data(Qt.UserRole)
        experience_title = self.experiences_table.item(selected_items[0].row(), 0).text()

        reply = QMessageBox.question(self, "Delete Experience",
                                     f"Are you sure you want to delete '{experience_title}'?\nThis will also remove all associated links (CASCADE).",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                success = experience_crud.delete_experience(experience_id)
                if success:
                    QMessageBox.information(self, "Success", "Experience deleted successfully.")
                else:
                    QMessageBox.warning(self, "Delete Failed", "Failed to delete experience. It might have already been deleted or an error occurred.")
            except Exception as e:
                logging.error(f"Error deleting experience {experience_id}: {e}", exc_info=True)
                QMessageBox.critical(self, "Delete Error", f"An error occurred: {e}")
            finally:
                self._load_experiences()

    def _on_filter_clicked(self):
        self.experiences_table.clearSelection()
        self._load_experiences(passed_filters=None)

    def _on_clear_filters_clicked(self):
        self.date_from_edit.setDate(QDate.currentDate().addMonths(-3))
        self.date_to_edit.setDate(QDate.currentDate())
        self.type_combo.setCurrentIndex(0)
        self.tags_edit.clear()
        self.experiences_table.clearSelection()
        self._load_experiences(passed_filters={})

    def _on_experience_selection_changed(self):
        is_selected = bool(self.experiences_table.selectedItems())
        self.edit_experience_button.setEnabled(is_selected)
        self.delete_experience_button.setEnabled(is_selected)

# (The rest of the file including AddEditExperienceDialog, SelectEntityDialog, SelectMediaDialog remains largely the same,
# but with Qt.ISODate for date string conversions and the .accept() override in AddEditExperienceDialog)

# --- SelectEntityDialog (dummy, no changes needed for this refinement step) ---
# ... (as before)

# --- SelectMediaDialog (dummy, no changes needed for this refinement step) ---
# ... (as before)

from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QDialogButtonBox, QFormLayout, QTextEdit

def dummy_search_entities(entity_type, search_term):
    print(f"Dummy search for {entity_type} with term '{search_term}'")
    if entity_type == "Client":
        return [{"id": "client1", "name": "Client Alpha"}, {"id": "client2", "name": "Client Beta"}]
    if entity_type == "Project":
        return [{"id": "proj1", "name": "Project X"}, {"id": "proj2", "name": "Project Y"}]
    return []

def dummy_get_all_media_items():
    print("Dummy get all media items")
    return [
        {"media_item_id": "media1", "title": "Company_Logo.png", "item_type": "image"},
        {"media_item_id": "media2", "title": "Product_Demo.mp4", "item_type": "video"},
        {"media_item_id": "media3", "title": "Datasheet.pdf", "item_type": "document"},
    ]

class SelectEntityDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Related Entity")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.entity_type_combo = QComboBox()
        self.entity_type_combo.addItems(["Client", "Project", "Product", "Partner", "CompanyAsset"])
        form_layout.addRow("Entity Type:", self.entity_type_combo)
        self.search_term_edit = QLineEdit()
        form_layout.addRow("Search Term:", self.search_term_edit)
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self._on_search_clicked)
        form_layout.addRow(self.search_button)
        self.results_list_widget = QListWidget()
        self.results_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addLayout(form_layout)
        layout.addWidget(QLabel("Search Results:"))
        layout.addWidget(self.results_list_widget)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.setMinimumWidth(350)

    def _on_search_clicked(self):
        self.results_list_widget.clear()
        entity_type = self.entity_type_combo.currentText()
        search_term = self.search_term_edit.text().strip()
        try:
            results = dummy_search_entities(entity_type, search_term)
            for item_data in results:
                item = QListWidgetItem(f"{item_data['name']} ({entity_type})")
                item.setData(Qt.UserRole, {"type": entity_type, "id": item_data["id"], "name": item_data["name"]})
                self.results_list_widget.addItem(item)
        except Exception as e:
            logging.error(f"Error in SelectEntityDialog search: {e}", exc_info=True)
            QMessageBox.critical(self, "Search Error", f"Could not perform entity search: {e}")


    def get_selected_entity(self):
        selected_items = self.results_list_widget.selectedItems()
        if selected_items: return selected_items[0].data(Qt.UserRole)
        return None

class SelectMediaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Media")
        self._init_ui()
        self._load_media_items()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.media_list_widget = QListWidget()
        self.media_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(QLabel("Available Media Items:"))
        layout.addWidget(self.media_list_widget)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.setMinimumWidth(400); self.setMinimumHeight(300)

    def _load_media_items(self):
        self.media_list_widget.clear()
        try:
            media_items = dummy_get_all_media_items()
            for media in media_items:
                item = QListWidgetItem(f"{media['title']} ({media.get('item_type', 'N/A')})")
                item.setData(Qt.UserRole, {"id": media["media_item_id"], "name": media["title"]})
                self.media_list_widget.addItem(item)
        except Exception as e:
            logging.error(f"Error loading media items in SelectMediaDialog: {e}", exc_info=True)
            QMessageBox.critical(self, "Load Error", f"Could not load media items: {e}")


    def get_selected_media(self) -> list:
        selected_media = []
        for item in self.media_list_widget.selectedItems():
            selected_media.append(item.data(Qt.UserRole))
        return selected_media

class AddEditExperienceDialog(QDialog):
    def __init__(self, parent=None, experience_data=None):
        super().__init__(parent)
        self.experience_data = experience_data
        if self.experience_data: self.setWindowTitle("Edit Experience")
        else: self.setWindowTitle("Add New Experience")
        self._init_ui()
        if self.experience_data: self._populate_fields(self.experience_data)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.title_edit = QLineEdit()
        form_layout.addRow("Title*:", self.title_edit)
        self.description_edit = QTextEdit(); self.description_edit.setAcceptRichText(False); self.description_edit.setMinimumHeight(100)
        form_layout.addRow("Description:", self.description_edit)
        self.date_edit = QDateEdit(QDate.currentDate()); self.date_edit.setCalendarPopup(True); self.date_edit.setDisplayFormat("yyyy-MM-dd")
        form_layout.addRow("Experience Date:", self.date_edit)
        self.type_combo = QComboBox(); self.type_combo.addItems(["Sale", "Project", "Internal", "Purchase", "Activity", "Other"])
        form_layout.addRow("Type:", self.type_combo)

        entities_group = QGroupBox("Related Entities")
        entities_layout = QVBoxLayout()
        self.related_entities_list_widget = QListWidget()
        self.related_entities_list_widget.itemSelectionChanged.connect(self._on_related_entity_selection_changed)
        entities_buttons_layout = QHBoxLayout()
        self.add_related_entity_button = QPushButton("Add Entity"); self.add_related_entity_button.clicked.connect(self._on_add_related_entity_clicked)
        self.remove_related_entity_button = QPushButton("Remove Selected Entity"); self.remove_related_entity_button.clicked.connect(self._on_remove_related_entity_clicked); self.remove_related_entity_button.setEnabled(False)
        entities_buttons_layout.addWidget(self.add_related_entity_button); entities_buttons_layout.addWidget(self.remove_related_entity_button)
        entities_layout.addWidget(self.related_entities_list_widget); entities_layout.addLayout(entities_buttons_layout)
        entities_group.setLayout(entities_layout); form_layout.addRow(entities_group)

        media_group = QGroupBox("Media Attachments")
        media_layout = QVBoxLayout()
        self.media_list_widget = QListWidget(); self.media_list_widget.itemSelectionChanged.connect(self._on_media_selection_changed)
        media_buttons_layout = QHBoxLayout()
        self.add_media_button = QPushButton("Add Media"); self.add_media_button.clicked.connect(self._on_add_media_clicked)
        self.remove_media_button = QPushButton("Remove Selected Media"); self.remove_media_button.clicked.connect(self._on_remove_media_clicked); self.remove_media_button.setEnabled(False)
        media_buttons_layout.addWidget(self.add_media_button); media_buttons_layout.addWidget(self.remove_media_button)
        media_layout.addWidget(self.media_list_widget); media_layout.addLayout(media_buttons_layout)
        media_group.setLayout(media_layout); form_layout.addRow(media_group)

        self.tags_edit = QLineEdit(); self.tags_edit.setPlaceholderText("Comma-separated, e.g., tag1, tag2")
        form_layout.addRow("Tags:", self.tags_edit)
        layout.addLayout(form_layout)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.setLayout(layout); self.setMinimumWidth(450)

    def _populate_fields(self, data: dict):
        self.title_edit.setText(data.get("title", ""))
        self.description_edit.setPlainText(data.get("description", ""))
        date_str = data.get("experience_date")
        if date_str: self.date_edit.setDate(QDate.fromString(date_str, Qt.ISODate))
        type_str = data.get("type")
        if type_str:
            index = self.type_combo.findText(type_str)
            if index >= 0: self.type_combo.setCurrentIndex(index)

        tags_list = data.get("tags_list", [])
        if tags_list and isinstance(tags_list, list) and len(tags_list) > 0 and isinstance(tags_list[0], dict):
            self.tags_edit.setText(", ".join(t.get("tag_name","") for t in tags_list))
        elif isinstance(tags_list, str): self.tags_edit.setText(tags_list)
        elif "tags_str" in data: self.tags_edit.setText(data.get("tags_str",""))

        related_entities_data = data.get("related_entities", [])
        self.related_entities_list_widget.clear()
        for entity in related_entities_data:
            display_text = entity.get('name', f"{entity['type']}: {entity['id']}")
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, {"type": entity["type"], "id": entity["id"], "name": entity.get('name', '')})
            self.related_entities_list_widget.addItem(item)

        media_links_data = data.get("media_links", [])
        self.media_list_widget.clear()
        for media_data in media_links_data:
            item = QListWidgetItem(media_data.get('name', f"Media ID: {media_data['id']}"))
            item.setData(Qt.UserRole, {"id": media_data["id"], "name": media_data.get('name', '')})
            self.media_list_widget.addItem(item)

    def accept(self):
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Input Error", "Title cannot be empty.")
            self.title_edit.setFocus()
            return
        super().accept()

    def get_data(self) -> dict:
        data = {
            "title": self.title_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "experience_date": self.date_edit.date().toString(Qt.ISODate),
            "type": self.type_combo.currentText(),
            "tags_str": self.tags_edit.text().strip(),
        }
        related_entities = []
        for i in range(self.related_entities_list_widget.count()):
            related_entities.append(self.related_entities_list_widget.item(i).data(Qt.UserRole))
        data["related_entities"] = related_entities
        media_ids = []
        for i in range(self.media_list_widget.count()):
            media_ids.append(self.media_list_widget.item(i).data(Qt.UserRole)['id'])
        data["media_ids"] = media_ids
        if self.experience_data and "experience_id" in self.experience_data:
            data["experience_id"] = self.experience_data["experience_id"]
        return data

    def _on_add_related_entity_clicked(self):
        try:
            dialog = SelectEntityDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                selected_entity = dialog.get_selected_entity()
                if selected_entity:
                    for i in range(self.related_entities_list_widget.count()):
                        item_data = self.related_entities_list_widget.item(i).data(Qt.UserRole)
                        if item_data["type"] == selected_entity["type"] and item_data["id"] == selected_entity["id"]:
                            QMessageBox.information(self, "Duplicate", "This entity is already related.")
                            return
                    item = QListWidgetItem(f"{selected_entity['name']} ({selected_entity['type']})")
                    item.setData(Qt.UserRole, selected_entity)
                    self.related_entities_list_widget.addItem(item)
        except Exception as e:
            logging.error(f"Error in _on_add_related_entity_clicked: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Could not open select entity dialog: {e}")

    def _on_remove_related_entity_clicked(self):
        selected_items = self.related_entities_list_widget.selectedItems()
        if not selected_items: return
        for item in selected_items: self.related_entities_list_widget.takeItem(self.related_entities_list_widget.row(item))
        self._on_related_entity_selection_changed()

    def _on_related_entity_selection_changed(self):
        self.remove_related_entity_button.setEnabled(bool(self.related_entities_list_widget.selectedItems()))

    def _on_add_media_clicked(self):
        try:
            dialog = SelectMediaDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                selected_media_items = dialog.get_selected_media()
                for media_data in selected_media_items:
                    if media_data:
                        is_duplicate = any(self.media_list_widget.item(i).data(Qt.UserRole)["id"] == media_data["id"] for i in range(self.media_list_widget.count()))
                        if is_duplicate: continue
                        item = QListWidgetItem(media_data["name"])
                        item.setData(Qt.UserRole, media_data)
                        self.media_list_widget.addItem(item)
        except Exception as e:
            logging.error(f"Error in _on_add_media_clicked: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Could not open select media dialog: {e}")

    def _on_remove_media_clicked(self):
        selected_items = self.media_list_widget.selectedItems()
        if not selected_items: return
        for item in selected_items: self.media_list_widget.takeItem(self.media_list_widget.row(item))
        self._on_media_selection_changed()

    def _on_media_selection_changed(self):
        self.remove_media_button.setEnabled(bool(self.media_list_widget.selectedItems()))

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    # Example of running the main widget (requires DB setup or more robust dummy data for CRUDs)
    # To test dialogs standalone:
    # dialog = AddEditExperienceDialog()
    # dialog.exec_()
    # entity_dialog = SelectEntityDialog()
    # entity_dialog.exec_()
    # media_dialog = SelectMediaDialog()
    # media_dialog.exec_()
    widget = ExperienceModuleWidget(current_user_id="test_user_uuid") # Provide a dummy user_id
    widget.resize(800, 600)
    widget.show()
    sys.exit(app.exec_())
