import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLabel, QLineEdit, QComboBox, QDateEdit,
    QGroupBox, QSizePolicy, QMessageBox, QDialog, QListWidget, QListWidgetItem,
    QDialogButtonBox, QFormLayout, QTextEdit, QCompleter
)
from PyQt5.QtCore import QDate, Qt, QStringListModel
import uuid
import logging

from db.cruds import experience_crud, tags_crud
from db.cruds import clients_crud, projects_crud, products_crud, partners_crud, company_assets_crud
from db.cruds import media_items_crud


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
        self.date_from_edit = QDateEdit(QDate.currentDate().addMonths(-3)); self.date_from_edit.setCalendarPopup(True); self.date_from_edit.setDisplayFormat("yyyy-MM-dd")
        date_filter_layout.addWidget(QLabel("Date From:")); date_filter_layout.addWidget(self.date_from_edit)
        self.date_to_edit = QDateEdit(QDate.currentDate()); self.date_to_edit.setCalendarPopup(True); self.date_to_edit.setDisplayFormat("yyyy-MM-dd")
        date_filter_layout.addWidget(QLabel("Date To:")); date_filter_layout.addWidget(self.date_to_edit)
        date_filter_layout.addStretch(); filter_layout.addLayout(date_filter_layout)
        type_tag_filter_layout = QHBoxLayout()
        self.type_combo = QComboBox(); self.type_combo.addItems(["All Types", "Sale", "Project", "Internal", "Purchase", "Activity", "Other"])
        type_tag_filter_layout.addWidget(QLabel("Type:")); type_tag_filter_layout.addWidget(self.type_combo)
        self.tags_edit = QLineEdit(); self.tags_edit.setPlaceholderText("e.g., important, client-visit")
        type_tag_filter_layout.addWidget(QLabel("Tags (comma-separated):")); type_tag_filter_layout.addWidget(self.tags_edit)
        self.tags_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred); filter_layout.addLayout(type_tag_filter_layout)
        filter_button_layout = QHBoxLayout()
        self.apply_filters_button = QPushButton("Apply Filters"); self.apply_filters_button.clicked.connect(self._on_filter_clicked)
        filter_button_layout.addWidget(self.apply_filters_button)
        self.clear_filters_button = QPushButton("Clear Filters"); self.clear_filters_button.clicked.connect(self._on_clear_filters_clicked)
        filter_button_layout.addWidget(self.clear_filters_button)
        filter_button_layout.addStretch(); filter_layout.addLayout(filter_button_layout)
        filter_groupbox.setLayout(filter_layout); main_layout.addWidget(filter_groupbox)

        self.experiences_table = QTableWidget(0, 4)
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
        self.experiences_table.setRowCount(0); self.experiences_table.clearSelection()
        filters_dict = {}
        try:
            if passed_filters is None:
                date_from = self.date_from_edit.date().toString(Qt.ISODate)
                date_to = self.date_to_edit.date().toString(Qt.ISODate)
                if date_from and date_to and date_from <= date_to: filters_dict["date_from"] = date_from; filters_dict["date_to"] = date_to
                exp_type = self.type_combo.currentText()
                if exp_type != "All Types": filters_dict["type"] = exp_type
                tags_str = self.tags_edit.text().strip()
                if tags_str: filters_dict["tags"] = [t.strip() for t in tags_str.split(',') if t.strip()]
            else: filters_dict = passed_filters

            self.experiences_table.setEnabled(False); self.experiences_table.setPlaceholderText("Loading experiences...")
            experiences_data = experience_crud.get_all_experiences(filters=filters_dict)
            if not experiences_data: self.experiences_table.setPlaceholderText("No experiences found.")
            else: self.experiences_table.setPlaceholderText("")
            for r, exp in enumerate(experiences_data):
                self.experiences_table.insertRow(r)
                self.experiences_table.setItem(r,0,QTableWidgetItem(exp.get("title","")))
                self.experiences_table.setItem(r,1,QTableWidgetItem(exp.get("experience_date","")))
                self.experiences_table.setItem(r,2,QTableWidgetItem(exp.get("type","")))
                desc = exp.get("description",""); self.experiences_table.setItem(r,3,QTableWidgetItem(desc[:97]+"..." if len(desc)>100 else desc))
                self.experiences_table.item(r,0).setData(Qt.UserRole, exp.get("experience_id"))
        except Exception as e:
            logging.error(f"Error loading experiences: {e}", exc_info=True); QMessageBox.critical(self, "Load Error", f"Could not load: {e}")
            self.experiences_table.setPlaceholderText("Error loading experiences.")
        finally: self.experiences_table.setEnabled(True); self._on_experience_selection_changed()

    def _handle_tags(self, experience_id, tags_str):
        if not tags_str: return True
        all_ok = True
        for name in [n.strip() for n in tags_str.split(',') if n.strip()]:
            try:
                tag = tags_crud.get_tag_by_name(name)
                tid = tag['tag_id'] if tag else tags_crud.add_tag({"tag_name": name}) # Assumes add_tag returns ID
                if tid:
                    if not experience_crud.add_experience_tag(experience_id, tid): all_ok = False
                else: # Fallback if add_tag didn't return ID or failed silently
                    tag_check = tags_crud.get_tag_by_name(name)
                    if tag_check:
                        if not experience_crud.add_experience_tag(experience_id, tag_check['tag_id']): all_ok = False
                    else: QMessageBox.warning(self, "Tag Error", f"Could not find/create ID for tag: {name}"); all_ok = False
            except Exception as e: logging.error(f"Error processing tag '{name}': {e}", exc_info=True); all_ok = False
        return all_ok

    def _on_add_experience_clicked(self):
        dialog = AddEditExperienceDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            core_data = {"title":data["title"], "description":data["description"], "experience_date":data["experience_date"], "type":data["type"], "user_id":self.current_user_id}
            new_id = None
            try: new_id = experience_crud.add_experience(core_data); assert new_id
            except Exception as e: logging.error(f"Add exp error: {e}", exc_info=True); QMessageBox.critical(self, "Add Error", f"Failed: {e}"); return

            tags_ok = self._handle_tags(new_id, data.get("tags_str"))
            ents_ok = all(experience_crud.add_experience_related_entity(new_id, el['type'], el['id']) for el in data.get("related_entities",[]))
            media_ok = all(experience_crud.add_experience_media(new_id, mid) for mid in data.get("media_ids",[]))

            if tags_ok and ents_ok and media_ok: QMessageBox.information(self, "Success", "Experience added.")
            else: QMessageBox.warning(self, "Partial Success", "Experience added, but some links may have failed.")
            self._load_experiences()

    def _on_edit_experience_clicked(self):
        sel = self.experiences_table.selectedItems();
        if not sel: QMessageBox.warning(self, "No Selection", "Select experience to edit."); return
        exp_id = self.experiences_table.item(sel[0].row(), 0).data(Qt.UserRole)
        try:
            details = experience_crud.get_experience_by_id(exp_id)
            if not details: QMessageBox.critical(self, "Error", "Cannot retrieve details."); return
            details["tags_list"] = experience_crud.get_tags_for_experience(exp_id)

            raw_ents = experience_crud.get_related_entities_for_experience(exp_id); details["related_entities"] = []
            for e in raw_ents:
                ename = f"{e['entity_type']}:{e['entity_id']}"
                try:
                    if e['entity_type'] == 'Client': ename = clients_crud.get_client_by_id(e['entity_id']).get('client_name', ename)
                    elif e['entity_type'] == 'Project': ename = projects_crud.get_project_by_id(e['entity_id']).get('project_name', ename)
                    elif e['entity_type'] == 'Product': ename = products_crud.get_product_by_id(e['entity_id']).get('product_name', ename)
                    elif e['entity_type'] == 'Partner': ename = partners_crud.get_partner_by_id(e['entity_id']).get('partner_name', ename)
                    elif e['entity_type'] == 'CompanyAsset': ename = company_assets_crud.get_asset_by_id(e['entity_id']).get('asset_name', ename)
                except Exception as fetch_err: logging.warning(f"Name fetch error {e['entity_type']} {e['entity_id']}: {fetch_err}")
                details["related_entities"].append({"type":e["entity_type"], "id":e["entity_id"], "name":ename})

            raw_media = experience_crud.get_media_for_experience(exp_id)
            details["media_links"] = [{"id":m["media_item_id"], "name":m.get("media_title",m["media_item_id"])} for m in raw_media]
        except Exception as e: logging.error(f"Edit fetch error: {e}", exc_info=True); QMessageBox.critical(self, "Fetch Error", f"Failed: {e}"); return

        dialog = AddEditExperienceDialog(parent=self, experience_data=details)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            core_data = {"title":data["title"], "description":data["description"], "experience_date":data["experience_date"], "type":data["type"]}
            try: assert experience_crud.update_experience(exp_id, core_data)
            except Exception as e: logging.error(f"Update exp error {exp_id}: {e}", exc_info=True); QMessageBox.critical(self, "Update Error", f"Failed: {e}"); self._load_experiences(); return

            results = []
            try: experience_crud.remove_all_tags_for_experience(exp_id); results.append(self._handle_tags(exp_id, data.get("tags_str")))
            except Exception as e: results.append(False); logging.error(f"Tag update error: {e}", exc_info=True)
            try:
                experience_crud.remove_all_related_entities_for_experience(exp_id)
                results.append(all(experience_crud.add_experience_related_entity(exp_id,el['type'],el['id']) for el in data.get("related_entities",[])))
            except Exception as e: results.append(False); logging.error(f"Entity update error: {e}", exc_info=True)
            try:
                experience_crud.remove_all_media_for_experience(exp_id)
                results.append(all(experience_crud.add_experience_media(exp_id, mid) for mid in data.get("media_ids",[])))
            except Exception as e: results.append(False); logging.error(f"Media update error: {e}", exc_info=True)

            if all(results): QMessageBox.information(self, "Success", "Experience updated.")
            else: QMessageBox.warning(self, "Partial Success", "Experience updated, but some links may have failed.")
            self._load_experiences()

    def _on_delete_experience_clicked(self):
        sel = self.experiences_table.selectedItems()
        if not sel: QMessageBox.warning(self, "No Selection", "Select experience to delete."); return
        exp_id = self.experiences_table.item(sel[0].row(), 0).data(Qt.UserRole)
        title = self.experiences_table.item(sel[0].row(), 0).text()
        reply = QMessageBox.question(self, "Delete Experience", f"Delete '{title}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if experience_crud.delete_experience(exp_id): QMessageBox.information(self, "Success", "Experience deleted.")
                else: QMessageBox.warning(self, "Delete Failed", "Failed to delete.")
            except Exception as e: logging.error(f"Delete error {exp_id}: {e}", exc_info=True); QMessageBox.critical(self, "Delete Error", f"Error: {e}")
            finally: self._load_experiences()

    def _on_filter_clicked(self): self.experiences_table.clearSelection(); self._load_experiences(None)
    def _on_clear_filters_clicked(self):
        self.date_from_edit.setDate(QDate.currentDate().addMonths(-3)); self.date_to_edit.setDate(QDate.currentDate())
        self.type_combo.setCurrentIndex(0); self.tags_edit.clear(); self.experiences_table.clearSelection()
        self._load_experiences({})
    def _on_experience_selection_changed(self):
        is_selected = bool(self.experiences_table.selectedItems())
        self.edit_experience_button.setEnabled(is_selected); self.delete_experience_button.setEnabled(is_selected)

# --- SelectEntityDialog ---
class SelectEntityDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Related Entity"); self._init_ui()
    def _init_ui(self):
        layout=QVBoxLayout(self); form_layout=QFormLayout()
        self.entity_type_combo=QComboBox(); self.entity_type_combo.addItems(["Client","Project","Product","Partner","CompanyAsset"])
        form_layout.addRow("Entity Type:",self.entity_type_combo)
        self.search_term_edit=QLineEdit(); form_layout.addRow("Search Term:",self.search_term_edit)
        self.search_button=QPushButton("Search"); self.search_button.clicked.connect(self._on_search_clicked); form_layout.addRow(self.search_button)
        self.results_list_widget=QListWidget(); self.results_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addLayout(form_layout); layout.addWidget(QLabel("Search Results:")); layout.addWidget(self.results_list_widget)
        self.button_box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept); self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box); self.setMinimumWidth(350)
    def _on_search_clicked(self):
        self.results_list_widget.clear(); entity_type=self.entity_type_combo.currentText(); search_term=self.search_term_edit.text().strip()
        results=[];
        try:
            filters={'limit':50};
            if search_term: # Apply search term if provided
                name_like_field = f"{entity_type.lower()}_name_like" # e.g. client_name_like
                if entity_type == "CompanyAsset": name_like_field = "asset_name_like" # Adjust for specific cases
                filters[name_like_field] = search_term

            crud_map = {
                "Client": clients_crud.get_all_clients, "Project": projects_crud.get_all_projects,
                "Product": products_crud.get_products, "Partner": partners_crud.get_all_partners,
                "CompanyAsset": company_assets_crud.get_all_assets
            }
            id_field_map = {"Client":"client_id","Project":"project_id","Product":"product_id","Partner":"partner_id","CompanyAsset":"asset_id"}
            name_field_map = {"Client":"client_name","Project":"project_name","Product":"product_name","Partner":"partner_name","CompanyAsset":"asset_name"}

            if entity_type in crud_map: raw = crud_map[entity_type](filters=filters)
            else: raw = []

            for r in raw:
                item_id=r.get(id_field_map[entity_type]); item_name=r.get(name_field_map[entity_type],"N/A")
                if item_id: item=QListWidgetItem(item_name); item.setData(Qt.UserRole,{"type":entity_type,"id":item_id,"name":item_name}); self.results_list_widget.addItem(item)
        except Exception as e: logging.error(f"Search entities error({entity_type}):{e}",exc_info=True); QMessageBox.critical(self,"Search Error",f"Could not search: {e}")
    def get_selected_entity(self): sel=self.results_list_widget.selectedItems(); return sel[0].data(Qt.UserRole) if sel else None

# --- SelectMediaDialog ---
class SelectMediaDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowTitle("Select Media Item(s)"); self._init_ui()
    def _init_ui(self):
        layout=QVBoxLayout(self); search_layout=QHBoxLayout()
        self.search_media_edit=QLineEdit(); self.search_media_edit.setPlaceholderText("Search media by title...")
        search_layout.addWidget(self.search_media_edit)
        self.search_media_button=QPushButton("Search/Refresh"); self.search_media_button.clicked.connect(self._load_media_items)
        search_layout.addWidget(self.search_media_button); layout.addLayout(search_layout)
        self.media_list_widget=QListWidget(); self.media_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(QLabel("Available Media Items:")); layout.addWidget(self.media_list_widget)
        self.button_box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept); self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box); self.setMinimumWidth(450); self.setMinimumHeight(350); self._load_media_items()
    def _load_media_items(self):
        self.media_list_widget.clear(); search_term=self.search_media_edit.text().strip(); filters={}
        if search_term: filters['title_like']=search_term
        try:
            all_media = media_items_crud.get_all_media_items(filters=filters) if media_items_crud else []
            if not all_media and search_term: self.media_list_widget.addItem("No media found matching search.")
            elif not all_media: self.media_list_widget.addItem("No media items available.")
            for media in all_media:
                title=media.get('title','Untitled'); item_type=media.get('item_type','N/A'); item_id=media.get('media_item_id')
                if not item_id: continue
                item=QListWidgetItem(f"{title} ({item_type})"); item.setData(Qt.UserRole,{"id":item_id,"name":title}); self.media_list_widget.addItem(item)
        except Exception as e: logging.error(f"Error loading media items: {e}",exc_info=True); QMessageBox.critical(self,"Load Error",f"Could not load media: {e}")
    def get_selected_media(self) -> list: return [item.data(Qt.UserRole) for item in self.media_list_widget.selectedItems()]

class AddEditExperienceDialog(QDialog):
    def __init__(self,parent=None,experience_data=None):
        super().__init__(parent); self.experience_data=experience_data
        if self.experience_data: self.setWindowTitle("Edit Experience")
        else: self.setWindowTitle("Add New Experience")
        self._init_ui();
        if self.experience_data: self._populate_fields(self.experience_data)

    def _init_ui(self):
        layout=QVBoxLayout(self); form_layout=QFormLayout()
        self.title_edit=QLineEdit(); form_layout.addRow("Title*:",self.title_edit)
        self.description_edit=QTextEdit(); self.description_edit.setAcceptRichText(False); self.description_edit.setMinimumHeight(100)
        form_layout.addRow("Description:",self.description_edit)
        self.date_edit=QDateEdit(QDate.currentDate()); self.date_edit.setCalendarPopup(True); self.date_edit.setDisplayFormat("yyyy-MM-dd")
        form_layout.addRow("Experience Date:",self.date_edit)
        self.type_combo=QComboBox(); self.type_combo.addItems(["Sale","Project","Internal","Purchase","Activity","Other"])
        form_layout.addRow("Type:",self.type_combo)

        entities_group=QGroupBox("Related Entities"); ents_layout=QVBoxLayout()
        self.related_entities_list_widget=QListWidget(); self.related_entities_list_widget.itemSelectionChanged.connect(self._on_related_entity_selection_changed)
        ents_btns_layout=QHBoxLayout()
        self.add_related_entity_button=QPushButton("Add Entity"); self.add_related_entity_button.clicked.connect(self._on_add_related_entity_clicked)
        self.remove_related_entity_button=QPushButton("Remove Selected"); self.remove_related_entity_button.clicked.connect(self._on_remove_related_entity_clicked); self.remove_related_entity_button.setEnabled(False)
        ents_btns_layout.addWidget(self.add_related_entity_button); ents_btns_layout.addWidget(self.remove_related_entity_button)
        ents_layout.addWidget(self.related_entities_list_widget); ents_layout.addLayout(ents_btns_layout)
        entities_group.setLayout(ents_layout); form_layout.addRow(entities_group)

        media_group=QGroupBox("Media Attachments"); media_layout_main=QVBoxLayout()
        self.media_list_widget=QListWidget(); self.media_list_widget.itemSelectionChanged.connect(self._on_media_selection_changed)
        media_btns_layout=QHBoxLayout()
        self.add_media_button=QPushButton("Add Media"); self.add_media_button.clicked.connect(self._on_add_media_clicked)
        self.remove_media_button=QPushButton("Remove Selected"); self.remove_media_button.clicked.connect(self._on_remove_media_clicked); self.remove_media_button.setEnabled(False)
        media_btns_layout.addWidget(self.add_media_button); media_btns_layout.addWidget(self.remove_media_button)
        media_layout_main.addWidget(self.media_list_widget); media_layout_main.addLayout(media_btns_layout)
        media_group.setLayout(media_layout_main); form_layout.addRow(media_group)

        self.tags_input = QLineEdit(); self.tags_input.setPlaceholderText("Comma-separated e.g. project_alpha, urgent") # Changed name
        # Setup completer for tags
        self.all_tags_model = QStringListModel()
        self.tag_completer = QCompleter(self.all_tags_model, self)
        self.tag_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.tag_completer.setFilterMode(Qt.MatchContains) # Or Qt.MatchStartsWith
        self.tags_input.setCompleter(self.tag_completer)
        self._load_all_tags_for_completer() # Load tags on init
        form_layout.addRow("Tags:", self.tags_input) # Use new name

        layout.addLayout(form_layout)
        self.button_box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept); self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box); self.setLayout(layout); self.setMinimumWidth(450)

    def _load_all_tags_for_completer(self):
        try:
            all_tags_data = tags_crud.get_all_tags() # Assumes this returns list of dicts like [{'tag_id': 1, 'tag_name': 'urgent'}, ...]
            if all_tags_data:
                tag_names_list = [tag['tag_name'] for tag in all_tags_data if 'tag_name' in tag]
                self.all_tags_model.setStringList(tag_names_list)
            else:
                self.all_tags_model.setStringList([]) # Ensure empty if no data
        except Exception as e:
            logging.error(f"Failed to load tags for autocompleter: {e}", exc_info=True)
            self.all_tags_model.setStringList([]) # Ensure empty on error


    def _populate_fields(self,data:dict):
        self.title_edit.setText(data.get("title",""))
        self.description_edit.setPlainText(data.get("description",""))
        date_str=data.get("experience_date");
        if date_str: self.date_edit.setDate(QDate.fromString(date_str,Qt.ISODate))
        type_str=data.get("type");
        if type_str: idx=self.type_combo.findText(type_str); _ = self.type_combo.setCurrentIndex(idx) if idx >=0 else None

        tags=data.get("tags_list",[])
        if tags and isinstance(tags[0],dict): self.tags_input.setText(", ".join(t.get("tag_name","") for t in tags))
        elif isinstance(tags,str): self.tags_input.setText(tags)
        elif "tags_str" in data : self.tags_input.setText(data.get("tags_str",""))

        self.related_entities_list_widget.clear()
        for entity in data.get("related_entities",[]):
            item=QListWidgetItem(entity.get('name',f"{entity['type']}:{entity['id']}"))
            item.setData(Qt.UserRole,entity); self.related_entities_list_widget.addItem(item)
        self.media_list_widget.clear()
        for media in data.get("media_links",[]):
            item=QListWidgetItem(media.get('name',f"ID:{media['id']}"))
            item.setData(Qt.UserRole,media); self.media_list_widget.addItem(item)

    def accept(self):
        if not self.title_edit.text().strip():
            QMessageBox.warning(self,"Input Error","Title is required."); self.title_edit.setFocus(); return
        super().accept()

    def get_data(self) -> dict:
        data={"title":self.title_edit.text().strip(),"description":self.description_edit.toPlainText().strip(),
              "experience_date":self.date_edit.date().toString(Qt.ISODate),"type":self.type_combo.currentText(),
              "tags_str":self.tags_input.text().strip()} # Use new name
        data["related_entities"]=[self.related_entities_list_widget.item(i).data(Qt.UserRole) for i in range(self.related_entities_list_widget.count())]
        data["media_ids"]=[self.media_list_widget.item(i).data(Qt.UserRole)['id'] for i in range(self.media_list_widget.count())]
        if self.experience_data and "experience_id" in self.experience_data: data["experience_id"]=self.experience_data["experience_id"]
        return data

    def _on_add_related_entity_clicked(self):
        try:
            dialog=SelectEntityDialog(self)
            if dialog.exec_()==QDialog.Accepted:
                selected=dialog.get_selected_entity()
                if selected:
                    is_dup=any(self.related_entities_list_widget.item(i).data(Qt.UserRole)["id"]==selected["id"] and
                                 self.related_entities_list_widget.item(i).data(Qt.UserRole)["type"]==selected["type"]
                                 for i in range(self.related_entities_list_widget.count()))
                    if is_dup: QMessageBox.information(self,"Duplicate","Entity already linked."); return
                    item=QListWidgetItem(f"{selected['name']} ({selected['type']})"); item.setData(Qt.UserRole,selected)
                    self.related_entities_list_widget.addItem(item)
        except Exception as e: logging.error(f"Add related entity dialog error: {e}",exc_info=True); QMessageBox.critical(self,"Error",f"Dialog error: {e}")

    def _on_remove_related_entity_clicked(self):
        for item in self.related_entities_list_widget.selectedItems(): self.related_entities_list_widget.takeItem(self.related_entities_list_widget.row(item))
    def _on_related_entity_selection_changed(self): self.remove_related_entity_button.setEnabled(bool(self.related_entities_list_widget.selectedItems()))

    def _on_add_media_clicked(self):
        try:
            dialog=SelectMediaDialog(self)
            if dialog.exec_()==QDialog.Accepted:
                for media_data in dialog.get_selected_media():
                    if media_data:
                        is_dup=any(self.media_list_widget.item(i).data(Qt.UserRole)["id"]==media_data["id"] for i in range(self.media_list_widget.count()))
                        if is_dup: continue
                        item=QListWidgetItem(media_data["name"]); item.setData(Qt.UserRole,media_data)
                        self.media_list_widget.addItem(item)
        except Exception as e: logging.error(f"Add media dialog error: {e}",exc_info=True); QMessageBox.critical(self,"Error",f"Dialog error: {e}")

    def _on_remove_media_clicked(self):
        for item in self.media_list_widget.selectedItems(): self.media_list_widget.takeItem(self.media_list_widget.row(item))
    def _on_media_selection_changed(self): self.remove_media_button.setEnabled(bool(self.media_list_widget.selectedItems()))

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    widget = ExperienceModuleWidget(current_user_id="test_user_uuid")
    widget.resize(800,600); widget.show(); sys.exit(app.exec_())
