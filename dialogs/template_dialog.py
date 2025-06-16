# -*- coding: utf-8 -*-
import os
import shutil
import logging
import pandas as pd
from docx import Document

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, # QWidget for tab, if any, not directly here but common
    QLineEdit, QPushButton, QComboBox, QDialogButtonBox, # QLineEdit, QDialogButtonBox not directly in TemplateDialog but often part of complex dialogs
    QFileDialog, QTreeWidget, QTreeWidgetItem, QHeaderView, QTextEdit,
    QInputDialog, QMessageBox, QLabel
)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont
from PyQt5.QtCore import Qt, QUrl

import db as db_manager
from db.cruds.template_categories_crud import get_all_template_categories
from db.cruds.templates_crud import get_distinct_template_languages, get_distinct_template_types, get_filtered_templates
# templates_crud_instance is not used directly by TemplateDialog
import icons_rc # Import for Qt resource file

# Local import for get_notification_manager will be kept inside methods as per plan.

class TemplateDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Gestion des Modèles"))
        self.setMinimumSize(800, 500)
        self.config = config
        self.setup_ui()

    def setup_ui(self):
        main_hbox_layout = QHBoxLayout(self); left_vbox_layout = QVBoxLayout(); left_vbox_layout.setSpacing(10)

        # Filter UI Elements
        filter_layout = QGridLayout()
        filter_layout.setSpacing(10)

        self.category_filter_label = QLabel(self.tr("Category:"))
        self.category_filter_combo = QComboBox()
        filter_layout.addWidget(self.category_filter_label, 0, 0)
        filter_layout.addWidget(self.category_filter_combo, 0, 1)

        self.language_filter_label = QLabel(self.tr("Language:"))
        self.language_filter_combo = QComboBox()
        filter_layout.addWidget(self.language_filter_label, 0, 2)
        filter_layout.addWidget(self.language_filter_combo, 0, 3)

        self.doc_type_filter_label = QLabel(self.tr("Document Type:"))
        self.doc_type_filter_combo = QComboBox()
        filter_layout.addWidget(self.doc_type_filter_label, 0, 4)
        filter_layout.addWidget(self.doc_type_filter_combo, 0, 5)

        # Add some stretch to push filters to the left if needed, or set column stretch factors
        filter_layout.setColumnStretch(6, 1) # Add stretch to the right of filters

        left_vbox_layout.addLayout(filter_layout)

        self.template_list = QTreeWidget(); self.template_list.setColumnCount(4)
        self.template_list.setHeaderLabels([self.tr("Name"), self.tr("Type"), self.tr("Language"), self.tr("Default Status")])
        header = self.template_list.header(); header.setSectionResizeMode(0, QHeaderView.Stretch); header.setSectionResizeMode(1, QHeaderView.ResizeToContents); header.setSectionResizeMode(2, QHeaderView.ResizeToContents); header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.template_list.setAlternatingRowColors(True); font = self.template_list.font(); font.setPointSize(font.pointSize() + 1); self.template_list.setFont(font)
        left_vbox_layout.addWidget(self.template_list)
        btn_layout = QHBoxLayout(); btn_layout.setSpacing(8)
        self.add_btn = QPushButton(self.tr("Ajouter")); self.add_btn.setIcon(QIcon(":/icons/plus.svg")); self.add_btn.setToolTip(self.tr("Ajouter un nouveau modèle")); self.add_btn.setObjectName("primaryButton"); self.add_btn.clicked.connect(self.add_template); btn_layout.addWidget(self.add_btn)
        self.edit_btn = QPushButton(self.tr("Modifier")); self.edit_btn.setIcon(QIcon(":/icons/pencil.svg")); self.edit_btn.setToolTip(self.tr("Modifier le modèle sélectionné (ouvre le fichier externe)")); self.edit_btn.clicked.connect(self.edit_template); self.edit_btn.setEnabled(False); btn_layout.addWidget(self.edit_btn)
        self.delete_btn = QPushButton(self.tr("Supprimer")); self.delete_btn.setIcon(QIcon(":/icons/trash.svg")); self.delete_btn.setToolTip(self.tr("Supprimer le modèle sélectionné")); self.delete_btn.setObjectName("dangerButton"); self.delete_btn.clicked.connect(self.delete_template); self.delete_btn.setEnabled(False); btn_layout.addWidget(self.delete_btn)
        self.default_btn = QPushButton(self.tr("Par Défaut")); self.default_btn.setIcon(QIcon.fromTheme("emblem-default")); self.default_btn.setToolTip(self.tr("Définir le modèle sélectionné comme modèle par défaut pour sa catégorie et langue")); self.default_btn.clicked.connect(self.set_default_template); self.default_btn.setEnabled(False); btn_layout.addWidget(self.default_btn) # emblem-default not in list yet
        left_vbox_layout.addLayout(btn_layout); main_hbox_layout.addLayout(left_vbox_layout, 1)
        self.preview_area = QTextEdit(); self.preview_area.setReadOnly(True); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu."))
        self.preview_area.setObjectName("templatePreviewArea")
        main_hbox_layout.addWidget(self.preview_area, 3); main_hbox_layout.setContentsMargins(15,15,15,15)

        self.populate_category_filter()
        self.populate_language_filter()
        self.populate_doc_type_filter()

        # Connect filter signals
        self.category_filter_combo.currentIndexChanged.connect(self.handle_filter_changed)
        self.language_filter_combo.currentIndexChanged.connect(self.handle_filter_changed)
        self.doc_type_filter_combo.currentIndexChanged.connect(self.handle_filter_changed)

        self.load_templates(); self.template_list.currentItemChanged.connect(self.handle_tree_item_selection)

    def handle_filter_changed(self):
        category_id = self.category_filter_combo.currentData()
        language_code = self.language_filter_combo.currentData()
        doc_type = self.doc_type_filter_combo.currentData() # This is the DB value

        self.load_templates(category_filter=category_id, language_filter=language_code, type_filter=doc_type)

    def populate_category_filter(self):
        self.category_filter_combo.addItem(self.tr("All Categories"), "all")
        try:
            categories = get_all_template_categories()
            if not categories:
                logging.critical("TemplateDialog: populate_category_filter: No template categories found in the database. This is unexpected as categories should be seeded. Check database initialization and seeding process.")
                QMessageBox.critical(self, self.tr("Critical Error"),
                                     self.tr("No template categories could be loaded. This is essential for managing templates. Please check the application logs and ensure the database is correctly initialized. The template management dialog may not function correctly."))
                self.category_filter_combo.setEnabled(False)
                return

            for category in categories:
                self.category_filter_combo.addItem(category['category_name'], category['category_id'])

        except Exception as e:
            logging.error(f"TemplateDialog: populate_category_filter: Failed to load template categories: {e}")
            QMessageBox.warning(self, self.tr("Filter Error"),
                                self.tr("An error occurred while trying to load template categories for filtering. Please check logs for details."))

    def populate_language_filter(self):
        self.language_filter_combo.addItem(self.tr("All Languages"), "all")
        try:
            languages = get_distinct_template_languages()
            if languages:
                for lang_code_tuple in languages:
                    lang_code = lang_code_tuple[0]
                    self.language_filter_combo.addItem(lang_code, lang_code)
        except Exception as e:
            logging.error(f"Error populating language filter: {e}")
            QMessageBox.warning(self, self.tr("Filter Error"), self.tr("Could not load template languages for filtering."))

    def populate_doc_type_filter(self):
        self.doc_type_filter_combo.addItem(self.tr("All Types"), "all")
        self.doc_type_map = {
            "document_excel": self.tr("Excel"),
            "document_word": self.tr("Word"),
            "document_html": self.tr("HTML"),
            "document_other": self.tr("Other"),
        }
        try:
            doc_types = get_distinct_template_types()
            if doc_types:
                for type_tuple in doc_types:
                    db_type = type_tuple[0]
                    display_name = self.doc_type_map.get(db_type, db_type)
                    self.doc_type_filter_combo.addItem(display_name, db_type)
        except Exception as e:
            logging.error(f"Error populating document type filter: {e}")
            QMessageBox.warning(self, self.tr("Filter Error"), self.tr("Could not load template document types for filtering."))

    def handle_tree_item_selection(self,current_item,previous_item):
        if current_item is not None and current_item.parent() is not None: self.show_template_preview(current_item); self.edit_btn.setEnabled(True); self.delete_btn.setEnabled(True); self.default_btn.setEnabled(True)
        else: self.preview_area.clear(); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu.")); self.edit_btn.setEnabled(False); self.delete_btn.setEnabled(False); self.default_btn.setEnabled(False)

    def show_template_preview(self, item):
        if not item: self.preview_area.clear(); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu.")); return
        template_id=item.data(0,Qt.UserRole);
        if template_id is None: self.preview_area.clear(); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu.")); return
        try:
            details=db_manager.get_template_details_for_preview(template_id)
            if details:
                base_file_name=details['base_file_name']; language_code=details['language_code']; template_file_path=os.path.join(self.config["templates_dir"],language_code,base_file_name)
                self.preview_area.clear()
                if os.path.exists(template_file_path):
                    _,file_extension=os.path.splitext(template_file_path); file_extension=file_extension.lower()
                    if file_extension==".xlsx":
                        try:
                            df=pd.read_excel(template_file_path,sheet_name=0); html_content=f"""<style>table {{ border-collapse: collapse; width: 95%; font-family: Arial, sans-serif; margin: 10px; }} th, td {{ border: 1px solid #cccccc; padding: 6px; text-align: left; }} th {{ background-color: #e0e0e0; font-weight: bold; }} td {{ text-align: right; }} tr:nth-child(even) {{ background-color: #f9f9f9; }} tr:hover {{ background-color: #e6f7ff; }}</style>{df.to_html(escape=False,index=False,border=0)}"""; self.preview_area.setHtml(html_content)
                        except Exception as e: self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier Excel:\n{0}").format(str(e)))
                    elif file_extension==".docx":
                        try: doc=Document(template_file_path); full_text=[para.text for para in doc.paragraphs]; self.preview_area.setPlainText("\n".join(full_text))
                        except Exception as e: self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier Word:\n{0}").format(str(e)))
                    elif file_extension==".html":
                        try:
                            with open(template_file_path,"r",encoding="utf-8") as f: self.preview_area.setHtml(f.read())
                        except Exception as e: self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier HTML:\n{0}").format(str(e)))
                    else: self.preview_area.setPlainText(self.tr("Aperçu non disponible pour ce type de fichier."))
                else: self.preview_area.setPlainText(self.tr("Fichier modèle introuvable."))
            else: self.preview_area.setPlainText(self.tr("Détails du modèle non trouvés dans la base de données."))
        except Exception as e_general: self.preview_area.setPlainText(self.tr("Une erreur est survenue lors de la récupération des détails du modèle:\n{0}").format(str(e_general)))

    def load_templates(self, category_filter=None, language_filter=None, type_filter=None):
        self.template_list.clear()
        self.preview_area.clear()
        self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu."))

        effective_category_id = category_filter if category_filter != "all" else None
        effective_language_code = language_filter if language_filter != "all" else None
        effective_template_type = type_filter if type_filter != "all" else None

        all_templates_from_db = get_filtered_templates(
            category_id=effective_category_id,
            language_code=effective_language_code,
            template_type=effective_template_type
        )

        if not all_templates_from_db:
            self.template_list.expandAll()
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.default_btn.setEnabled(False)
            return

        if effective_category_id is not None:
            category_details = db_manager.get_template_category_details(effective_category_id)
            if category_details:
                category_item = QTreeWidgetItem(self.template_list, [category_details['category_name']])
                for template_dict in all_templates_from_db:
                    template_name = template_dict['template_name']
                    template_db_type = template_dict.get('template_type', 'N/A')
                    display_type_name = self.doc_type_map.get(template_db_type, template_db_type)
                    language = template_dict['language_code']
                    is_default = self.tr("Yes") if template_dict.get('is_default_for_type_lang') else self.tr("No")
                    template_item = QTreeWidgetItem(category_item, [template_name, display_type_name, language, is_default])
                    template_item.setData(0, Qt.UserRole, template_dict['template_id'])
        else:
            all_db_categories = db_manager.get_all_template_categories()
            if not all_db_categories:
                self.template_list.expandAll()
                self.edit_btn.setEnabled(False); self.delete_btn.setEnabled(False); self.default_btn.setEnabled(False)
                return

            categories_map = {cat['category_id']: cat for cat in all_db_categories}
            templates_by_category = {}
            for template in all_templates_from_db:
                cat_id = template.get('category_id')
                if cat_id not in templates_by_category:
                    templates_by_category[cat_id] = []
                templates_by_category[cat_id].append(template)

            for cat_id, category_details_dict in categories_map.items():
                if cat_id in templates_by_category:
                    category_item = QTreeWidgetItem(self.template_list, [category_details_dict['category_name']])
                    for template_dict in templates_by_category[cat_id]:
                        template_name = template_dict['template_name']
                        template_db_type = template_dict.get('template_type', 'N/A')
                        display_type_name = self.doc_type_map.get(template_db_type, template_db_type)
                        language = template_dict['language_code']
                        is_default = self.tr("Yes") if template_dict.get('is_default_for_type_lang') else self.tr("No")
                        template_item = QTreeWidgetItem(category_item, [template_name, display_type_name, language, is_default])
                        template_item.setData(0, Qt.UserRole, template_dict['template_id'])

        self.template_list.expandAll()
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.default_btn.setEnabled(False)

    def add_template(self):
        file_path,_=QFileDialog.getOpenFileName(self,self.tr("Sélectionner un modèle"),self.config["templates_dir"],self.tr("Fichiers Modèles (*.xlsx *.docx *.html);;Tous les fichiers (*)"))
        if not file_path:return
        name,ok=QInputDialog.getText(self,self.tr("Nom du Modèle"),self.tr("Entrez un nom pour ce modèle:"))
        if not ok or not name.strip():return
        existing_categories=db_manager.get_all_template_categories(); existing_categories=existing_categories if existing_categories else []
        category_display_list=[cat['category_name'] for cat in existing_categories]; create_new_option=self.tr("[Create New Category...]"); category_display_list.append(create_new_option)
        selected_category_name,ok=QInputDialog.getItem(self,self.tr("Select Template Category"),self.tr("Category:"),category_display_list,0,False)
        if not ok:return
        final_category_id=None
        if selected_category_name==create_new_option:
            new_category_text,ok_new=QInputDialog.getText(self,self.tr("New Category"),self.tr("Enter name for new category:"))
            if ok_new and new_category_text.strip(): final_category_id=db_manager.add_template_category(new_category_text.strip());
            if not final_category_id:QMessageBox.warning(self,self.tr("Error"),self.tr("Could not create or find category: {0}").format(new_category_text.strip()));return
            # Original code had 'else: return' here, which seems like a bug. If category is created, it should proceed.
            # Corrected: remove 'else: return' or ensure it's logically sound.
            # For now, assuming if new category created, it should proceed to use it.
            # If `add_template_category` returns None on failure, the `if not final_category_id` handles it.
        else:
            found_cat=next((cat for cat in existing_categories if cat['category_name']==selected_category_name),None)
            if found_cat:final_category_id=found_cat['category_id']
            else:QMessageBox.critical(self,self.tr("Error"),self.tr("Selected category not found internally."));return

        if final_category_id is None: # Ensure category ID was obtained
             QMessageBox.warning(self,self.tr("Error"),self.tr("Category ID could not be determined. Aborting template add."))
             return

        languages=["fr","en","ar","tr","pt"]; lang,ok=QInputDialog.getItem(self,self.tr("Langue du Modèle"),self.tr("Sélectionnez la langue:"),languages,0,False)
        if not ok:return
        target_dir=os.path.join(self.config["templates_dir"],lang); os.makedirs(target_dir,exist_ok=True)
        base_file_name=os.path.basename(file_path); target_path=os.path.join(target_dir,base_file_name)
        file_ext=os.path.splitext(base_file_name)[1].lower(); template_type_for_db="document_other"
        if file_ext==".xlsx":template_type_for_db="document_excel"
        elif file_ext==".docx":template_type_for_db="document_word"
        elif file_ext==".html":template_type_for_db="document_html"
        template_metadata={'template_name':name.strip(),'template_type':template_type_for_db,'language_code':lang,'base_file_name':base_file_name,'description':f"Modèle {name.strip()} en {lang} ({base_file_name})",'category_id':final_category_id,'is_default_for_type_lang':False}
        try:
            shutil.copy(file_path,target_path); new_template_id=db_manager.add_template(template_metadata)
            if new_template_id:
                self.load_templates()
                from main import get_notification_manager # Local import
                get_notification_manager().show(title=self.tr("Modèle Ajouté"), message=self.tr("Modèle '{0}' ajouté avec succès.").format(name.strip()), type='SUCCESS')
            else:
                from main import get_notification_manager # Local import
                get_notification_manager().show(title=self.tr("Erreur Ajout Modèle DB"), message=self.tr("Erreur DB lors de l'ajout du modèle '{0}'.").format(name.strip()), type='ERROR')
        except Exception as e:
            from main import get_notification_manager # Local import
            get_notification_manager().show(title=self.tr("Erreur Ajout Modèle"), message=self.tr("Erreur lors de l'ajout du modèle '{0}' (fichier ou DB): {1}").format(name.strip(), str(e)), type='ERROR')

    def edit_template(self):
        current_item=self.template_list.currentItem()
        if not current_item or not current_item.parent():QMessageBox.warning(self,self.tr("Sélection Requise"),self.tr("Veuillez sélectionner un modèle à modifier."));return
        template_id=current_item.data(0,Qt.UserRole);
        if template_id is None:return
        try:
            path_info=db_manager.get_template_path_info(template_id)
            if path_info:template_file_path=os.path.join(self.config["templates_dir"],path_info['language'],path_info['file_name']); QDesktopServices.openUrl(QUrl.fromLocalFile(template_file_path))
            else:QMessageBox.warning(self,self.tr("Erreur"),self.tr("Impossible de récupérer les informations du modèle."))
        except Exception as e:QMessageBox.warning(self,self.tr("Erreur"),self.tr("Erreur lors de l'ouverture du modèle:\n{0}").format(str(e)))

    def delete_template(self):
        current_item=self.template_list.currentItem()
        if not current_item or not current_item.parent():QMessageBox.warning(self,self.tr("Sélection Requise"),self.tr("Veuillez sélectionner un modèle à supprimer."));return
        template_id=current_item.data(0,Qt.UserRole);
        if template_id is None:return
        reply=QMessageBox.question(self,self.tr("Confirmer Suppression"),self.tr("Êtes-vous sûr de vouloir supprimer ce modèle ?"),QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
        if reply==QMessageBox.Yes:
            try:
                file_info=db_manager.delete_template_and_get_file_info(template_id)
                if file_info:
                    file_path_to_delete=os.path.join(self.config["templates_dir"],file_info['language'],file_info['file_name'])
                    if os.path.exists(file_path_to_delete):os.remove(file_path_to_delete)
                    self.load_templates()
                    from main import get_notification_manager # Local import
                    get_notification_manager().show(title=self.tr("Modèle Supprimé"), message=self.tr("Modèle supprimé avec succès."), type='SUCCESS')
                else:
                    from main import get_notification_manager # Local import
                    get_notification_manager().show(title=self.tr("Erreur Suppression Modèle"), message=self.tr("Erreur de suppression du modèle."), type='ERROR')
            except Exception as e:
                from main import get_notification_manager # Local import
                get_notification_manager().show(title=self.tr("Erreur Suppression Modèle"), message=self.tr("Erreur de suppression du modèle: {0}").format(str(e)), type='ERROR')

    def set_default_template(self):
        current_item=self.template_list.currentItem()
        if not current_item or not current_item.parent():QMessageBox.warning(self,self.tr("Sélection Requise"),self.tr("Veuillez sélectionner un modèle à définir par défaut."));return
        template_id=current_item.data(0,Qt.UserRole);
        if template_id is None:return
        try:
            success=db_manager.set_default_template_by_id(template_id)
            if success:
                self.load_templates()
                from main import get_notification_manager # Local import
                get_notification_manager().show(title=self.tr("Modèle par Défaut Mis à Jour"), message=self.tr("Modèle défini comme modèle par défaut."), type='SUCCESS')
            else:
                from main import get_notification_manager # Local import
                get_notification_manager().show(title=self.tr("Erreur Modèle par Défaut"), message=self.tr("Erreur de mise à jour du modèle par défaut."), type='ERROR')
        except Exception as e:
            from main import get_notification_manager # Local import
            get_notification_manager().show(title=self.tr("Erreur Modèle par Défaut"), message=self.tr("Erreur lors de la définition du modèle par défaut: {0}").format(str(e)), type='ERROR')
