class ClientWidget(QWidget):
    def __init__(self, client_info, config, parent=None): 
        super().__init__(parent)
        self.client_info = client_info
        self.config = config 
        self.setup_ui()

    def _toggle_notes_section(self):
        # Ensure self.notes_group is used, which is defined in setup_ui
        if hasattr(self, 'notes_group'):
            is_visible = self.notes_group.isVisible()
            self.notes_group.setVisible(not is_visible)
            if not is_visible:
                self.toggle_notes_btn.setText(self.tr("Masquer les Notes"))
                self.toggle_notes_btn.setIcon(QIcon.fromTheme("view-conceal"))
            else:
                self.toggle_notes_btn.setText(self.tr("Afficher les Notes"))
                self.toggle_notes_btn.setIcon(QIcon.fromTheme("view-reveal"))
        else:
            print("Error: notes_group not found on ClientWidget instance.")
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15) 
        layout.setSpacing(15) 
        
        self.header_label = QLabel(f"<h2>{self.client_info['client_name']}</h2>")
        self.header_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(self.header_label)
        
        action_layout = QHBoxLayout()
        
        self.compile_pdf_btn = QPushButton(self.tr("Compiler PDF"))
        self.compile_pdf_btn.setIcon(QIcon.fromTheme("document-export"))
        self.compile_pdf_btn.setProperty("primary", True)
        self.compile_pdf_btn.clicked.connect(self.open_compile_pdf_dialog)
        action_layout.addWidget(self.compile_pdf_btn)

        self.send_email_btn = QPushButton(self.tr("Envoyer Mail"))
        self.send_email_btn.setIcon(QIcon.fromTheme("mail-send"))
        self.send_email_btn.setObjectName("primaryButton")
        self.send_email_btn.clicked.connect(self.open_email_dialog)
        action_layout.addWidget(self.send_email_btn)
        
        layout.addLayout(action_layout)
        
        status_layout = QHBoxLayout()
        status_label = QLabel(self.tr("Statut:"))
        status_layout.addWidget(status_label)
        self.status_combo = QComboBox()
        self.load_statuses()
        self.status_combo.setCurrentText(self.client_info.get("status", self.tr("En cours")))
        self.status_combo.currentTextChanged.connect(self.update_client_status)
        status_layout.addWidget(self.status_combo)
        layout.addLayout(status_layout)
        
        self.details_layout = QFormLayout()
        self.details_layout.setLabelAlignment(Qt.AlignRight)
        self.details_layout.setSpacing(8)

        self.detail_value_labels = {}
        self.populate_details_layout()

        self.category_label = QLabel(self.tr("Catégorie:"))
        self.category_value_label = QLabel(self.client_info.get("category", self.tr("N/A")))
        self.details_layout.addRow(self.category_label, self.category_value_label)
        self.detail_value_labels["category"] = self.category_value_label

        layout.addLayout(self.details_layout)
        
        # Create Toggle Button for Notes
        self.toggle_notes_btn = QPushButton(self.tr("Afficher les Notes"))
        self.toggle_notes_btn.setIcon(QIcon.fromTheme("view-reveal"))
        # self.toggle_notes_btn.setMaximumWidth(200) # Optional
        self.toggle_notes_btn.clicked.connect(self._toggle_notes_section)

        notes_toggle_layout = QHBoxLayout()
        notes_toggle_layout.addWidget(self.toggle_notes_btn)
        notes_toggle_layout.addStretch()
        layout.addLayout(notes_toggle_layout)

        # Notes Section (make it self.notes_group)
        self.notes_group = QGroupBox(self.tr("Notes")) # Changed to self.notes_group
        notes_layout_inner = QVBoxLayout(self.notes_group) # Use a different variable name
        self.notes_edit = QTextEdit(self.client_info.get("notes", ""))
        self.notes_edit.setPlaceholderText(self.tr("Ajoutez des notes sur ce client..."))
        self.notes_edit.textChanged.connect(self.save_client_notes) 
        notes_layout_inner.addWidget(self.notes_edit)
        self.notes_group.setVisible(False) # Hide by default
        layout.addWidget(self.notes_group)
        
        self.tab_widget = QTabWidget()
        
        docs_tab = QWidget()
        docs_layout = QVBoxLayout(docs_tab)
        
        self.doc_table = QTableWidget()
        self.doc_table.setColumnCount(5)
        self.doc_table.setHorizontalHeaderLabels([
            self.tr("Nom"), self.tr("Type"), self.tr("Langue"),
            self.tr("Date"), self.tr("Actions")
        ])
        self.doc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.doc_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.doc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        docs_layout.addWidget(self.doc_table)
        
        doc_btn_layout = QHBoxLayout()
        
        self.add_document_tab_btn = QPushButton(self.tr("Ajouter Document"))
        self.add_document_tab_btn.setIcon(QIcon.fromTheme("document-new"))
        self.add_document_tab_btn.clicked.connect(self.open_create_docs_dialog)
        self.add_document_tab_btn.setObjectName("primaryButton")
        doc_btn_layout.addWidget(self.add_document_tab_btn)

        refresh_btn = QPushButton(self.tr("Actualiser"))
        refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        refresh_btn.clicked.connect(self.populate_doc_table)
        doc_btn_layout.addWidget(refresh_btn)
        
        open_btn = QPushButton(self.tr("Ouvrir"))
        open_btn.setIcon(QIcon.fromTheme("document-open"))
        open_btn.clicked.connect(self.open_selected_doc)
        doc_btn_layout.addWidget(open_btn)
        
        docs_layout.addLayout(doc_btn_layout)
        self.tab_widget.addTab(docs_tab, self.tr("Documents"))
        
        contacts_tab = QWidget()
        contacts_layout = QVBoxLayout(contacts_tab)
        self.contacts_list = QListWidget()
        self.contacts_list.setAlternatingRowColors(True)
        self.contacts_list.itemDoubleClicked.connect(self.edit_contact)
        contacts_layout.addWidget(self.contacts_list)
        
        contacts_btn_layout = QHBoxLayout()
        self.add_contact_btn = QPushButton(self.tr("➕ Ajouter"))
        self.add_contact_btn.setIcon(QIcon.fromTheme("contact-new", QIcon.fromTheme("list-add")))
        self.add_contact_btn.setToolTip(self.tr("Ajouter un nouveau contact pour ce client"))
        self.add_contact_btn.clicked.connect(self.add_contact)
        contacts_btn_layout.addWidget(self.add_contact_btn)
        
        self.edit_contact_btn = QPushButton(self.tr("✏️ Modifier"))
        self.edit_contact_btn.setIcon(QIcon.fromTheme("document-edit"))
        self.edit_contact_btn.setToolTip(self.tr("Modifier le contact sélectionné"))
        self.edit_contact_btn.clicked.connect(self.edit_contact)
        contacts_btn_layout.addWidget(self.edit_contact_btn)
        
        self.remove_contact_btn = QPushButton(self.tr("🗑️ Supprimer"))
        self.remove_contact_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.remove_contact_btn.setToolTip(self.tr("Supprimer le lien vers le contact sélectionné pour ce client"))
        self.remove_contact_btn.setObjectName("dangerButton")
        self.remove_contact_btn.clicked.connect(self.remove_contact)
        contacts_btn_layout.addWidget(self.remove_contact_btn)
        
        contacts_layout.addLayout(contacts_btn_layout)
        self.tab_widget.addTab(contacts_tab, self.tr("Contacts"))

        products_tab = QWidget()
        products_layout = QVBoxLayout(products_tab)
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(6)
        self.products_table.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Nom Produit"), self.tr("Description"),
            self.tr("Qté"), self.tr("Prix Unitaire"), self.tr("Prix Total")
        ])
        self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.hideColumn(0)
        products_layout.addWidget(self.products_table)
        
        products_btn_layout = QHBoxLayout()
        self.add_product_btn = QPushButton(self.tr("➕ Ajouter"))
        self.add_product_btn.setIcon(QIcon.fromTheme("list-add"))
        self.add_product_btn.setToolTip(self.tr("Ajouter un produit pour ce client/projet"))
        self.add_product_btn.clicked.connect(self.add_product)
        products_btn_layout.addWidget(self.add_product_btn)
        
        self.edit_product_btn = QPushButton(self.tr("✏️ Modifier"))
        self.edit_product_btn.setIcon(QIcon.fromTheme("document-edit"))
        self.edit_product_btn.setToolTip(self.tr("Modifier le produit sélectionné"))
        self.edit_product_btn.clicked.connect(self.edit_product)
        products_btn_layout.addWidget(self.edit_product_btn)
        
        self.remove_product_btn = QPushButton(self.tr("🗑️ Supprimer"))
        self.remove_product_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.remove_product_btn.setToolTip(self.tr("Supprimer le produit sélectionné de ce client/projet"))
        self.remove_product_btn.setObjectName("dangerButton")
        self.remove_product_btn.clicked.connect(self.remove_product)
        products_btn_layout.addWidget(self.remove_product_btn)
        
        products_layout.addLayout(products_btn_layout)
        self.tab_widget.addTab(products_tab, self.tr("Produits"))
        
        layout.addWidget(self.tab_widget)
        
        self.populate_doc_table()
        self.load_contacts()
        self.load_products()

    def _handle_open_pdf_action(self, file_path):
        print(f"Action: Open PDF for {file_path}")
        if not self.client_info or 'client_id' not in self.client_info:
            QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("Les informations du client ne sont pas disponibles."))
            return

        generated_pdf_path = generate_pdf_for_document(file_path, self.client_info, self)
        if generated_pdf_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(generated_pdf_path))

    def populate_details_layout(self):
        while self.details_layout.rowCount() > 0:
            self.details_layout.removeRow(0)
        self.detail_value_labels.clear()
        details_data_map = {
            "project_identifier": (self.tr("ID Projet:"), self.client_info.get("project_identifier", self.tr("N/A"))),
            "country": (self.tr("Pays:"), self.client_info.get("country", self.tr("N/A"))),
            "city": (self.tr("Ville:"), self.client_info.get("city", self.tr("N/A"))),
            "need": (self.tr("Besoin Principal:"), self.client_info.get("need", self.tr("N/A"))),
            "price": (self.tr("Prix Final:"), f"{self.client_info.get('price', 0)} €"),
            "creation_date": (self.tr("Date Création:"), self.client_info.get("creation_date", self.tr("N/A"))),
            "base_folder_path": (self.tr("Chemin Dossier:"), f"<a href='file:///{self.client_info.get('base_folder_path','')}'>{self.client_info.get('base_folder_path','')}</a>")
        }
        for key, (label_text, value_text) in details_data_map.items():
            label_widget = QLabel(label_text)
            value_widget = QLabel(value_text)
            if key == "base_folder_path":
                value_widget.setOpenExternalLinks(True)
                value_widget.setTextInteractionFlags(Qt.TextBrowserInteraction)
            self.details_layout.addRow(label_widget, value_widget)
            self.detail_value_labels[key] = value_widget

    def refresh_display(self, new_client_info):
        self.client_info = new_client_info
        self.header_label.setText(f"<h2>{self.client_info.get('client_name', '')}</h2>")
        self.status_combo.setCurrentText(self.client_info.get("status", self.tr("En cours")))
        if hasattr(self, 'detail_value_labels'):
            self.detail_value_labels["project_identifier"].setText(self.client_info.get("project_identifier", self.tr("N/A")))
            self.detail_value_labels["country"].setText(self.client_info.get("country", self.tr("N/A")))
            self.detail_value_labels["city"].setText(self.client_info.get("city", self.tr("N/A")))
            self.detail_value_labels["need"].setText(self.client_info.get("need", self.tr("N/A")))
            self.detail_value_labels["price"].setText(f"{self.client_info.get('price', 0)} €")
            self.detail_value_labels["creation_date"].setText(self.client_info.get("creation_date", self.tr("N/A")))
            folder_path = self.client_info.get('base_folder_path','')
            self.detail_value_labels["base_folder_path"].setText(f"<a href='file:///{folder_path}'>{folder_path}</a>")
            if "category" in self.detail_value_labels:
                 self.detail_value_labels["category"].setText(self.client_info.get("category", self.tr("N/A")))
            elif hasattr(self, 'category_value_label'):
                 self.category_value_label.setText(self.client_info.get("category", self.tr("N/A")))
        else:
            self.populate_details_layout()
            if hasattr(self, 'category_value_label'):
                 self.category_value_label.setText(self.client_info.get("category", self.tr("N/A")))
        self.notes_edit.setText(self.client_info.get("notes", ""))

    def load_statuses(self):
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT status_name FROM StatusSettings")
            for status_row in cursor.fetchall(): 
                self.status_combo.addItem(status_row[0])
        except sqlite3.Error as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des statuts:\n{0}").format(str(e)))
        finally:
            if conn: conn.close()
            
    def update_client_status(self, status_text): 
        try:
            status_setting = db_manager.get_status_setting_by_name(status_text, 'Client')
            if status_setting and status_setting.get('status_id') is not None:
                status_id_to_set = status_setting['status_id']
                client_id_to_update = self.client_info["client_id"]
                if db_manager.update_client(client_id_to_update, {'status_id': status_id_to_set}):
                    self.client_info["status"] = status_text
                    self.client_info["status_id"] = status_id_to_set
                    print(f"Client {client_id_to_update} status_id updated to {status_id_to_set} ({status_text})")
                else:
                    QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la mise à jour du statut du client dans la DB."))
            else:
                QMessageBox.warning(self, self.tr("Erreur Configuration"), self.tr("Statut '{0}' non trouvé ou invalide. Impossible de mettre à jour.").format(status_text))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Erreur de mise à jour du statut:\n{0}").format(str(e)))
            
    def save_client_notes(self): 
        notes = self.notes_edit.toPlainText()
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE Clients SET notes = ? WHERE client_id = ?", (notes, self.client_info["client_id"]))
            conn.commit()
            self.client_info["notes"] = notes 
        except sqlite3.Error as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de sauvegarde des notes:\n{0}").format(str(e)))
        finally:
            if conn: conn.close()
            
    def populate_doc_table(self):
        self.doc_table.setRowCount(0)
        client_path = self.client_info["base_folder_path"] 
        if not os.path.exists(client_path):
            return
        row = 0
        for lang in self.client_info.get("selected_languages", ["fr"]):
            lang_dir = os.path.join(client_path, lang)
            if not os.path.exists(lang_dir):
                continue
            for file_name in os.listdir(lang_dir):
                if file_name.endswith(('.xlsx', '.pdf', '.docx', '.html')):
                    file_path = os.path.join(lang_dir, file_name)
                    name_item = QTableWidgetItem(file_name)
                    name_item.setData(Qt.UserRole, file_path)
                    file_type_str = ""
                    if file_name.lower().endswith('.xlsx'): file_type_str = self.tr("Excel")
                    elif file_name.lower().endswith('.docx'): file_type_str = self.tr("Word")
                    elif file_name.lower().endswith('.html'): file_type_str = self.tr("HTML")
                    else: file_type_str = self.tr("PDF")
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')
                    self.doc_table.insertRow(row)
                    self.doc_table.setItem(row, 0, name_item)
                    self.doc_table.setItem(row, 1, QTableWidgetItem(file_type_str))
                    self.doc_table.setItem(row, 2, QTableWidgetItem(lang))
                    self.doc_table.setItem(row, 3, QTableWidgetItem(mod_time))
                    action_widget = QWidget()
                    action_layout = QHBoxLayout(action_widget)
                    action_layout.setContentsMargins(2, 2, 2, 2)
                    action_layout.setSpacing(5)
                    pdf_btn = QPushButton("PDF")
                    pdf_btn.setIcon(QIcon.fromTheme("application-pdf", QIcon("📄")))
                    pdf_btn.setToolTip(self.tr("Ouvrir PDF du document"))
                    pdf_btn.setFixedSize(30, 30)
                    pdf_btn.clicked.connect(lambda _, p=file_path: self._handle_open_pdf_action(p))
                    action_layout.addWidget(pdf_btn)
                    source_btn = QPushButton("👁️")
                    source_btn.setIcon(QIcon.fromTheme("document-properties", QIcon("👁️")))
                    source_btn.setToolTip(self.tr("Afficher le fichier source"))
                    source_btn.setFixedSize(30, 30)
                    source_btn.clicked.connect(lambda _, p=file_path: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
                    action_layout.addWidget(source_btn)
                    if file_name.lower().endswith(('.xlsx', '.html')):
                        edit_btn = QPushButton("✏️")
                        edit_btn.setIcon(QIcon.fromTheme("document-edit", QIcon("✏️")))
                        edit_btn.setToolTip(self.tr("Modifier le contenu du document"))
                        edit_btn.setFixedSize(30, 30)
                        edit_btn.clicked.connect(lambda _, p=file_path: self.open_document(p))
                        action_layout.addWidget(edit_btn)
                    else:
                        spacer_widget = QWidget()
                        spacer_widget.setFixedSize(30,30)
                        action_layout.addWidget(spacer_widget)
                    delete_btn = QPushButton("🗑️")
                    delete_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon("🗑️")))
                    delete_btn.setToolTip(self.tr("Supprimer le document"))
                    delete_btn.setFixedSize(30, 30)
                    delete_btn.clicked.connect(lambda _, p=file_path: self.delete_document(p))
                    action_layout.addWidget(delete_btn)
                    action_layout.addStretch()
                    action_widget.setLayout(action_layout)
                    self.doc_table.setCellWidget(row, 4, action_widget)
                    row += 1

    def open_create_docs_dialog(self):
        dialog = CreateDocumentDialog(self.client_info, self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            self.populate_doc_table()
            
    def open_compile_pdf_dialog(self):
        dialog = CompilePdfDialog(self.client_info, self)
        dialog.exec_()

    def open_email_dialog(self):
        dialog = EmailDialog(client_info=self.client_info, parent=self)
        dialog.exec_()
            
    def open_selected_doc(self):
        selected_row = self.doc_table.currentRow()
        if selected_row >= 0:
            file_path_item = self.doc_table.item(selected_row, 0)
            if file_path_item:
                file_path = file_path_item.data(Qt.UserRole)
                if file_path and os.path.exists(file_path):
                    self.open_document(file_path)
                
    def delete_selected_doc(self):
        selected_row = self.doc_table.currentRow()
        if selected_row >= 0:
            file_path_item = self.doc_table.item(selected_row, 0)
            if file_path_item:
                file_path = file_path_item.data(Qt.UserRole)
                if file_path and os.path.exists(file_path):
                    self.delete_document(file_path)
                
    def open_document(self, file_path):
        if os.path.exists(file_path):
            try:
                editor_client_data = {
                    "client_id": self.client_info.get("client_id"),
                    "Nom du client": self.client_info.get("client_name", ""),
                    "client_name": self.client_info.get("client_name", ""),
                    "company_name": self.client_info.get("company_name", ""),
                    "Besoin": self.client_info.get("need", ""),
                    "primary_need_description": self.client_info.get("need", ""),
                    "project_identifier": self.client_info.get("project_identifier", ""),
                    "country": self.client_info.get("country", ""),
                    "country_id": self.client_info.get("country_id"),
                    "city": self.client_info.get("city", ""),
                    "city_id": self.client_info.get("city_id"),
                    "price": self.client_info.get("price", 0),
                    "status": self.client_info.get("status"),
                    "status_id": self.client_info.get("status_id"),
                    "selected_languages": self.client_info.get("selected_languages"),
                    "notes": self.client_info.get("notes"),
                    "creation_date": self.client_info.get("creation_date"),
                    "category": self.client_info.get("category"),
                    "base_folder_path": self.client_info.get("base_folder_path")
                }
                if file_path.lower().endswith('.xlsx'):
                    editor = ExcelEditor(file_path, parent=self)
                    if editor.exec_() == QDialog.Accepted:
                        expected_pdf_basename = os.path.splitext(os.path.basename(file_path))[0] + "_" + datetime.now().strftime('%Y%m%d') + ".pdf"
                        expected_pdf_path = os.path.join(os.path.dirname(file_path), expected_pdf_basename)
                        if os.path.exists(expected_pdf_path):
                            archive_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                            archive_pdf_name = os.path.splitext(expected_pdf_path)[0] + f"_archive_{archive_timestamp}.pdf"
                            try:
                                os.rename(expected_pdf_path, os.path.join(os.path.dirname(expected_pdf_path), archive_pdf_name))
                                print(f"Archived existing PDF to: {archive_pdf_name}")
                            except OSError as e_archive:
                                print(f"Error archiving PDF {expected_pdf_path}: {e_archive}")
                        generate_pdf_for_document(file_path, self.client_info, self)
                    self.populate_doc_table()
                elif file_path.lower().endswith('.html'):
                    html_editor_dialog = HtmlEditor(file_path, client_data=editor_client_data, parent=self)
                    if html_editor_dialog.exec_() == QDialog.Accepted:
                        expected_pdf_basename = os.path.splitext(os.path.basename(file_path))[0] + "_" + datetime.now().strftime('%Y%m%d') + ".pdf"
                        expected_pdf_path = os.path.join(os.path.dirname(file_path), expected_pdf_basename)
                        if os.path.exists(expected_pdf_path):
                            archive_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                            archive_pdf_name = os.path.splitext(expected_pdf_path)[0] + f"_archive_{archive_timestamp}.pdf"
                            try:
                                os.rename(expected_pdf_path, os.path.join(os.path.dirname(expected_pdf_path), archive_pdf_name))
                                print(f"Archived existing PDF to: {archive_pdf_name}")
                            except OSError as e_archive:
                                print(f"Error archiving PDF {expected_pdf_path}: {e_archive}")
                        generated_pdf_path = generate_pdf_for_document(file_path, self.client_info, self)
                        if generated_pdf_path:
                             print(f"Updated PDF generated at: {generated_pdf_path}")
                    self.populate_doc_table()
                elif file_path.lower().endswith(('.docx', '.pdf')):
                    QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
                else:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            except Exception as e:
                QMessageBox.warning(self, self.tr("Erreur Ouverture Fichier"), self.tr("Impossible d'ouvrir le fichier:\n{0}").format(str(e)))
        else:
            QMessageBox.warning(self, self.tr("Fichier Introuvable"), self.tr("Le fichier n'existe plus."))
            self.populate_doc_table()
            
    def delete_document(self, file_path):
        if not os.path.exists(file_path):
            return
        reply = QMessageBox.question(
            self, 
            self.tr("Confirmer la suppression"),
            self.tr("Êtes-vous sûr de vouloir supprimer le fichier {0} ?").format(os.path.basename(file_path)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                os.remove(file_path)
                self.populate_doc_table()
                QMessageBox.information(self, self.tr("Fichier supprimé"), self.tr("Le fichier a été supprimé avec succès."))
            except Exception as e:
                QMessageBox.warning(self, self.tr("Erreur"), self.tr("Impossible de supprimer le fichier:\n{0}").format(str(e)))
    
    def load_contacts(self):
        self.contacts_list.clear()
        client_uuid = self.client_info.get("client_id")
        if not client_uuid: return
        try:
            contacts = db_manager.get_contacts_for_client(client_uuid)
            if contacts is None: contacts = []
            for contact in contacts:
                contact_text = f"{contact.get('name', 'N/A')}"
                if contact.get('phone'): contact_text += f" ({contact.get('phone')})"
                if contact.get('is_primary_for_client'): contact_text += f" [{self.tr('Principal')}]"
                item = QListWidgetItem(contact_text)
                item.setData(Qt.UserRole, {'contact_id': contact.get('contact_id'),
                                           'client_contact_id': contact.get('client_contact_id'),
                                           'is_primary': contact.get('is_primary_for_client')})
                self.contacts_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des contacts:\n{0}").format(str(e)))
            
    def add_contact(self):
        client_uuid = self.client_info.get("client_id")
        if not client_uuid: return
        dialog = ContactDialog(client_uuid, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            contact_form_data = dialog.get_data()
            try:
                existing_contact = db_manager.get_contact_by_email(contact_form_data['email'])
                contact_id_to_link = None
                if existing_contact:
                    contact_id_to_link = existing_contact['contact_id']
                    update_data = {k: v for k, v in contact_form_data.items() if k in ['name', 'phone', 'position'] and v != existing_contact.get(k)}
                    if update_data : db_manager.update_contact(contact_id_to_link, update_data)
                else:
                    new_contact_id = db_manager.add_contact({
                        'name': contact_form_data['name'], 'email': contact_form_data['email'],
                        'phone': contact_form_data['phone'], 'position': contact_form_data['position']
                    })
                    if new_contact_id:
                        contact_id_to_link = new_contact_id
                    else:
                        QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de créer le nouveau contact global."))
                        return
                if contact_id_to_link:
                    if contact_form_data['is_primary']:
                        client_contacts = db_manager.get_contacts_for_client(client_uuid)
                        if client_contacts:
                            for cc in client_contacts:
                                if cc['is_primary_for_client']:
                                    db_manager.update_client_contact_link(cc['client_contact_id'], {'is_primary_for_client': False})
                    link_id = db_manager.link_contact_to_client(
                        client_uuid, contact_id_to_link,
                        is_primary=contact_form_data['is_primary']
                    )
                    if link_id:
                        self.load_contacts()
                    else:
                        QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de lier le contact au client. Le lien existe peut-être déjà."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du contact:\n{0}").format(str(e)))
                
    def edit_contact(self):
        item = self.contacts_list.currentItem()
        if not item: return
        item_data = item.data(Qt.UserRole)
        contact_id = item_data.get('contact_id')
        client_contact_id = item_data.get('client_contact_id')
        client_uuid = self.client_info.get("client_id")
        if not contact_id or not client_uuid: return
        try:
            contact_details = db_manager.get_contact_by_id(contact_id)
            if contact_details:
                current_link_info = None
                client_contacts_for_client = db_manager.get_contacts_for_client(client_uuid)
                if client_contacts_for_client:
                    for cc_link in client_contacts_for_client:
                        if cc_link['contact_id'] == contact_id:
                            current_link_info = cc_link
                            break
                is_primary_for_this_client = current_link_info['is_primary_for_client'] if current_link_info else False
                dialog_data = {
                    "name": contact_details.get('name'), "email": contact_details.get('email'),
                    "phone": contact_details.get('phone'), "position": contact_details.get('position'),
                    "is_primary": is_primary_for_this_client
                }
                dialog = ContactDialog(client_uuid, dialog_data, parent=self)
                if dialog.exec_() == QDialog.Accepted:
                    new_form_data = dialog.get_data()
                    db_manager.update_contact(contact_id, {
                        'name': new_form_data['name'], 'email': new_form_data['email'],
                        'phone': new_form_data['phone'], 'position': new_form_data['position']
                    })
                    if new_form_data['is_primary'] and not is_primary_for_this_client:
                        if client_contacts_for_client:
                            for cc in client_contacts_for_client:
                                if cc['contact_id'] != contact_id and cc['is_primary_for_client']:
                                    db_manager.update_client_contact_link(cc['client_contact_id'], {'is_primary_for_client': False})
                        db_manager.update_client_contact_link(client_contact_id, {'is_primary_for_client': True})
                    elif not new_form_data['is_primary'] and is_primary_for_this_client:
                        db_manager.update_client_contact_link(client_contact_id, {'is_primary_for_client': False})
                    self.load_contacts()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de modification du contact:\n{0}").format(str(e)))
            
    def remove_contact(self):
        item = self.contacts_list.currentItem()
        if not item: return
        item_data = item.data(Qt.UserRole)
        contact_id = item_data.get('contact_id')
        client_contact_id = item_data.get('client_contact_id')
        client_uuid = self.client_info.get("client_id")
        if not client_contact_id or not client_uuid or not contact_id: return
        contact_name = db_manager.get_contact_by_id(contact_id)['name'] if db_manager.get_contact_by_id(contact_id) else "Inconnu"
        reply = QMessageBox.question(self, self.tr("Confirmer Suppression Lien"),
                                     self.tr("Êtes-vous sûr de vouloir supprimer le lien vers ce contact ({0}) pour ce client ?\nLe contact global ne sera pas supprimé.").format(contact_name),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                unlinked = db_manager.unlink_contact_from_client(client_uuid, contact_id)
                if unlinked:
                    self.load_contacts()
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de suppression du lien contact-client."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de suppression du lien contact:\n{0}").format(str(e)))
                
    def add_product(self):
        client_uuid = self.client_info.get("client_id")
        if not client_uuid: return
        dialog = ProductDialog(client_uuid, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            products_list_data = dialog.get_data()
            products_added_count = 0
            for product_item_data in products_list_data:
                try:
                    global_product = db_manager.get_product_by_name(product_item_data['name'])
                    global_product_id = None
                    current_base_unit_price = None
                    if global_product:
                        global_product_id = global_product['product_id']
                        current_base_unit_price = global_product.get('base_unit_price')
                    else:
                        new_global_product_id = db_manager.add_product({
                            'product_name': product_item_data['name'],
                            'description': product_item_data['description'],
                            'base_unit_price': product_item_data['unit_price']
                        })
                        if new_global_product_id:
                            global_product_id = new_global_product_id
                            current_base_unit_price = product_item_data['unit_price']
                        else:
                            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de créer le produit global '{0}'.").format(product_item_data['name']))
                            continue
                    if global_product_id:
                        unit_price_override_val = None
                        if current_base_unit_price is None or product_item_data['unit_price'] != current_base_unit_price:
                            unit_price_override_val = product_item_data['unit_price']
                        link_data = {
                            'client_id': client_uuid,
                            'project_id': None,
                            'product_id': global_product_id,
                            'quantity': product_item_data['quantity'],
                            'unit_price_override': unit_price_override_val
                        }
                        cpp_id = db_manager.add_product_to_client_or_project(link_data)
                        if cpp_id:
                            products_added_count +=1
                        else:
                            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Impossible de lier le produit '{0}' au client.").format(product_item_data['name']))
                except Exception as e:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du produit '{0}':\n{1}").format(product_item_data.get('name', 'Inconnu'), str(e)))
            if products_added_count > 0:
                self.load_products()
            if products_added_count < len(products_list_data) and len(products_list_data) > 0 :
                 QMessageBox.information(self, self.tr("Information"), self.tr("Certains produits n'ont pas pu être ajoutés. Veuillez vérifier les messages d'erreur."))

    def edit_product(self):
        selected_row = self.products_table.currentRow()
        if selected_row < 0:
            QMessageBox.information(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un produit à modifier."))
            return
        cpp_id_item = self.products_table.item(selected_row, 0)
        if not cpp_id_item:
            QMessageBox.critical(self, self.tr("Erreur Données"), self.tr("ID du produit lié introuvable dans la table."))
            return
        client_project_product_id = cpp_id_item.data(Qt.UserRole)
        try:
            linked_product_details = db_manager.get_client_project_product_by_id(client_project_product_id)
            if not linked_product_details:
                QMessageBox.warning(self, self.tr("Erreur"), self.tr("Détails du produit lié introuvables dans la base de données."))
                return
            effective_unit_price = linked_product_details.get('unit_price_override', linked_product_details.get('base_unit_price', 0.0))
            dialog_data_for_edit = {
                "name": linked_product_details.get('product_name', ''),
                "description": linked_product_details.get('product_description', ''),
                "quantity": linked_product_details.get('quantity', 1.0),
                "unit_price": effective_unit_price,
                "product_id": linked_product_details.get('product_id'),
                "client_project_product_id": client_project_product_id,
                "original_base_unit_price": linked_product_details.get('base_unit_price', 0.0)
            }
            dialog = EditProductLineDialog(product_data=dialog_data_for_edit, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                updated_data_from_dialog = dialog.get_data()
                global_product_update_payload = {}
                if updated_data_from_dialog['name'] != linked_product_details.get('product_name'):
                    global_product_update_payload['product_name'] = updated_data_from_dialog['name']
                if updated_data_from_dialog['description'] != linked_product_details.get('product_description'):
                    global_product_update_payload['description'] = updated_data_from_dialog['description']
                if global_product_update_payload:
                     global_product_update_payload['base_unit_price'] = updated_data_from_dialog['unit_price']
                if global_product_update_payload:
                    db_manager.update_product(updated_data_from_dialog['product_id'], global_product_update_payload)
                current_global_product_info = db_manager.get_product_by_id(updated_data_from_dialog['product_id'])
                current_global_base_price = current_global_product_info.get('base_unit_price', 0.0) if current_global_product_info else 0.0
                unit_price_override_val = None
                if float(updated_data_from_dialog['unit_price']) != float(current_global_base_price):
                    unit_price_override_val = updated_data_from_dialog['unit_price']
                link_update_payload = {
                    'quantity': updated_data_from_dialog['quantity'],
                    'unit_price_override': unit_price_override_val
                }
                if db_manager.update_client_project_product(client_project_product_id, link_update_payload):
                    self.load_products()
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Ligne de produit mise à jour avec succès."))
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Échec de la mise à jour de la ligne de produit liée."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Erreur lors de la modification du produit:\n{0}").format(str(e)))
            print(f"Error in edit_product: {e}")

    def remove_product(self):
        selected_row = self.products_table.currentRow()
        if selected_row < 0: return
        cpp_id_item = self.products_table.item(selected_row, 0)
        if not cpp_id_item: return
        client_project_product_id = cpp_id_item.data(Qt.UserRole)
        product_name_item = self.products_table.item(selected_row, 1)
        product_name = product_name_item.text() if product_name_item else self.tr("Inconnu")
        reply = QMessageBox.question(
            self, 
            self.tr("Confirmer Suppression"),
            self.tr("Êtes-vous sûr de vouloir supprimer le produit '{0}' de ce client/projet?").format(product_name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                if db_manager.remove_product_from_client_or_project(client_project_product_id):
                    self.load_products()
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de suppression du produit lié."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de suppression du produit lié:\n{0}").format(str(e)))

    def load_products(self):
        self.products_table.setRowCount(0)
        client_uuid = self.client_info.get("client_id")
        if not client_uuid: return
        try:
            linked_products = db_manager.get_products_for_client_or_project(client_uuid, project_id=None)
            if linked_products is None: linked_products = []
            for row_idx, prod_link_data in enumerate(linked_products):
                self.products_table.insertRow(row_idx)
                id_item = QTableWidgetItem(str(prod_link_data.get('client_project_product_id')))
                id_item.setData(Qt.UserRole, prod_link_data.get('client_project_product_id'))
                self.products_table.setItem(row_idx, 0, id_item)
                self.products_table.setItem(row_idx, 1, QTableWidgetItem(prod_link_data.get('product_name', 'N/A')))
                self.products_table.setItem(row_idx, 2, QTableWidgetItem(prod_link_data.get('product_description', '')))
                qty_item = QTableWidgetItem(str(prod_link_data.get('quantity', 0)))
                qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.products_table.setItem(row_idx, 3, qty_item)
                effective_unit_price = prod_link_data.get('unit_price_override', prod_link_data.get('base_unit_price', 0.0))
                unit_price_item = QTableWidgetItem(f"€ {effective_unit_price:.2f}")
                unit_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.products_table.setItem(row_idx, 4, unit_price_item)
                total_price_item = QTableWidgetItem(f"€ {prod_link_data.get('total_price_calculated', 0.0):.2f}")
                total_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.products_table.setItem(row_idx, 5, total_price_item)
            self.products_table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des produits:\n{0}").format(str(e)))

# End of ClientWidget Class (Ensure this comment is accurate based on where EmailDialog ends and ClientWidget begins)
# If EmailDialog is defined *before* ClientWidget, this comment should be above EmailDialog.
# For now, assuming EmailDialog is the last major class before ClientWidget or other top-level functions.
