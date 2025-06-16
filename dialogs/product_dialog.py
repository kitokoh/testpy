# -*- coding: utf-8 -*-
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QDialogButtonBox, QMessageBox, QLabel, QListWidget, QListWidgetItem,
    QDoubleSpinBox, QGroupBox, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QComboBox, QFrame # Added QTextEdit, QFrame for completeness from original structure
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

import db as db_manager # Keep for now, direct calls like db_manager.get_all_products_for_selection_filtered
from db.cruds.clients_crud import clients_crud_instance

# Anticipated import, will be resolved when ProductDimensionUIDialog is moved
from .product_dimension_ui_dialog import ProductDimensionUIDialog
import icons_rc # Import for Qt resource file


class ProductDialog(QDialog):
    def __init__(self,client_id, app_root_dir, product_data=None,parent=None): # Added app_root_dir
        super().__init__(parent)
        self.client_id=client_id
        self.app_root_dir = app_root_dir # Store app_root_dir
        if not self.app_root_dir or not isinstance(self.app_root_dir, str) or not self.app_root_dir.strip():
            logging.warning("ProductDialog initialized with invalid or empty app_root_dir: %s", self.app_root_dir)
        self.current_selected_global_product_id = None
        self.setWindowTitle(self.tr("Ajouter Produits au Client"))
        self.setMinimumSize(900,800)
        try:
            self.client_info = clients_crud_instance.get_client_by_id(self.client_id)
        except Exception as e:
            logging.error(f"Error fetching client_info in ProductDialog: {e}") # Use logging
            self.client_info = {} # Fallback to empty dict
        self.setup_ui()
        self._set_initial_language_filter()
        self._filter_products_by_language_and_search()

    def _set_initial_language_filter(self):
        client_langs = None
        primary_language=None
        if self.client_info:client_langs=self.client_info.get('selected_languages');
        if client_langs:primary_language=client_langs.split(',')[0].strip()
        if primary_language:
            for i in range(self.product_language_filter_combo.count()):
                if self.product_language_filter_combo.itemText(i)==primary_language:self.product_language_filter_combo.setCurrentText(primary_language);break

    def _filter_products_by_language_and_search(self):
        self.existing_products_list.clear();selected_language=self.product_language_filter_combo.currentText();language_code_for_db=None if selected_language==self.tr("All") else selected_language;search_text=self.search_existing_product_input.text().lower();name_pattern_for_db=f"%{search_text}%" if search_text else None
        try:
            products=db_manager.get_all_products_for_selection_filtered(language_code=language_code_for_db,name_pattern=name_pattern_for_db)
            if products is None:products=[]
            for product_data in products:
                product_name=product_data.get('product_name','N/A');description=product_data.get('description','');base_unit_price=product_data.get('base_unit_price',0.0)
                if base_unit_price is None:base_unit_price=0.0
                desc_snippet=(description[:30]+'...') if len(description)>30 else description;display_text=f"{product_name} (Desc: {desc_snippet}, Prix: {base_unit_price:.2f} €)"
                item=QListWidgetItem(display_text);item.setData(Qt.UserRole,product_data);self.existing_products_list.addItem(item)
        except Exception as e:
            logging.error(f"Error loading existing products: {e}") # Use logging
            QMessageBox.warning(self,self.tr("Erreur Chargement Produits"),self.tr("Impossible de charger la liste des produits existants:\n{0}").format(str(e)))

    def _populate_form_from_selected_product(self,item):
        product_data=item.data(Qt.UserRole)
        if product_data:
            self.name_input.setText(product_data.get('product_name',''));self.description_input.setPlainText(product_data.get('description',''));base_price=product_data.get('base_unit_price',0.0)
            try:self.unit_price_input.setValue(float(base_price))
            except(ValueError,TypeError):self.unit_price_input.setValue(0.0)
            self.quantity_input.setValue(1.0)
            self.quantity_input.setFocus()

            product_weight = product_data.get('weight', 0.0)
            self.weight_input.setValue(float(product_weight) if product_weight is not None else 0.0)
            product_dimensions = product_data.get('dimensions', '')
            self.dimensions_input.setText(product_dimensions if product_dimensions is not None else "")
            self.global_weight_display_label.setText(f"{product_weight} kg" if product_weight is not None else self.tr("N/A"))
            self.global_dimensions_display_label.setText(product_dimensions if product_dimensions else self.tr("N/A"))

            self._update_current_line_total_preview()
            self.current_selected_global_product_id = product_data.get('product_id')
            self.view_detailed_dimensions_button.setEnabled(bool(self.current_selected_global_product_id))
        else:
            self.current_selected_global_product_id = None
            self.view_detailed_dimensions_button.setEnabled(False)
            self.weight_input.setValue(0.0)
            self.dimensions_input.clear()
            self.global_weight_display_label.setText(self.tr("N/A"))
            self.global_dimensions_display_label.setText(self.tr("N/A"))

    def _create_icon_label_widget(self,icon_name,label_text):

        from PyQt5.QtWidgets import QWidget

        widget=QWidget();layout=QHBoxLayout(widget);layout.setContentsMargins(0,0,0,0);layout.setSpacing(5)
        icon_label=QLabel();icon_label.setPixmap(QIcon.fromTheme(icon_name).pixmap(16,16));layout.addWidget(icon_label);layout.addWidget(QLabel(label_text));return widget

    def setup_ui(self):
        main_layout=QVBoxLayout(self);main_layout.setSpacing(15);header_label=QLabel(self.tr("Ajouter Lignes de Produits")); header_label.setObjectName("dialogHeaderLabel"); main_layout.addWidget(header_label)
        two_columns_layout=QHBoxLayout();search_group_box=QGroupBox(self.tr("Rechercher Produit Existant"));search_layout=QVBoxLayout(search_group_box)
        self.product_language_filter_label=QLabel(self.tr("Filtrer par langue:"));search_layout.addWidget(self.product_language_filter_label);self.product_language_filter_combo=QComboBox();self.product_language_filter_combo.addItems([self.tr("All"),"fr","en","ar","tr","pt"]);self.product_language_filter_combo.currentTextChanged.connect(self._filter_products_by_language_and_search);search_layout.addWidget(self.product_language_filter_combo)
        self.search_existing_product_input=QLineEdit();self.search_existing_product_input.setPlaceholderText(self.tr("Tapez pour rechercher..."));self.search_existing_product_input.textChanged.connect(self._filter_products_by_language_and_search);search_layout.addWidget(self.search_existing_product_input)
        self.existing_products_list=QListWidget();self.existing_products_list.setMinimumHeight(150);self.existing_products_list.itemDoubleClicked.connect(self._populate_form_from_selected_product);search_layout.addWidget(self.existing_products_list);two_columns_layout.addWidget(search_group_box,1)

        input_group_box=QGroupBox(self.tr("Détails de la Ligne de Produit Actuelle (ou Produit Sélectionné)"));form_layout=QFormLayout(input_group_box);form_layout.setSpacing(10);
        self.name_input=QLineEdit();form_layout.addRow(self._create_icon_label_widget("package-x-generic",self.tr("Nom du Produit:")),self.name_input)
        self.description_input=QTextEdit();self.description_input.setFixedHeight(80);form_layout.addRow(self.tr("Description:"),self.description_input) # QTextEdit was missing from plan
        self.quantity_input=QDoubleSpinBox();self.quantity_input.setRange(0,1000000);self.quantity_input.setValue(0.0);self.quantity_input.valueChanged.connect(self._update_current_line_total_preview);form_layout.addRow(self._create_icon_label_widget("format-list-numbered",self.tr("Quantité:")),self.quantity_input)
        self.unit_price_input=QDoubleSpinBox();self.unit_price_input.setRange(0,10000000);self.unit_price_input.setPrefix("€ ");self.unit_price_input.setValue(0.0);self.unit_price_input.valueChanged.connect(self._update_current_line_total_preview);form_layout.addRow(self._create_icon_label_widget("cash",self.tr("Prix Unitaire:")),self.unit_price_input)

        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(0.0, 10000.0); self.weight_input.setSuffix(" kg"); self.weight_input.setDecimals(2); self.weight_input.setValue(0.0)
        form_layout.addRow(self.tr("Poids (Ligne):"), self.weight_input)
        self.dimensions_input = QLineEdit()
        self.dimensions_input.setPlaceholderText(self.tr("LxlxH cm"))
        form_layout.addRow(self.tr("Dimensions (Ligne):"), self.dimensions_input)
        self.global_weight_display_label = QLabel(self.tr("N/A"))
        form_layout.addRow(self.tr("Poids (Global Produit):"), self.global_weight_display_label)
        self.global_dimensions_display_label = QLabel(self.tr("N/A"))
        form_layout.addRow(self.tr("Dimensions (Global Produit):"), self.global_dimensions_display_label)
        self.view_detailed_dimensions_button = QPushButton(self.tr("Voir Dimensions Détaillées (Global Produit)"))
        self.view_detailed_dimensions_button.setIcon(QIcon.fromTheme("view-fullscreen"))
        self.view_detailed_dimensions_button.setEnabled(False)
        self.view_detailed_dimensions_button.clicked.connect(self.on_view_detailed_dimensions)
        form_layout.addRow(self.view_detailed_dimensions_button)

        current_line_total_title_label=QLabel(self.tr("Total Ligne Actuelle:"));self.current_line_total_label=QLabel("€ 0.00");font=self.current_line_total_label.font();font.setBold(True);self.current_line_total_label.setFont(font);form_layout.addRow(current_line_total_title_label,self.current_line_total_label);two_columns_layout.addWidget(input_group_box,2);main_layout.addLayout(two_columns_layout)
        self.add_line_btn=QPushButton(self.tr("Ajouter Produit à la Liste"));self.add_line_btn.setIcon(QIcon(":/icons/plus-circle.svg"));self.add_line_btn.setObjectName("primaryButton");self.add_line_btn.clicked.connect(self._add_current_line_to_table);main_layout.addWidget(self.add_line_btn)
        self.products_table=QTableWidget();self.products_table.setColumnCount(5);self.products_table.setHorizontalHeaderLabels([self.tr("Nom Produit"),self.tr("Description"),self.tr("Qté"),self.tr("Prix Unitaire"),self.tr("Total Ligne")]);self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows);self.products_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);self.products_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch);self.products_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeToContents);self.products_table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeToContents);self.products_table.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeToContents);main_layout.addWidget(self.products_table)
        self.remove_line_btn=QPushButton(self.tr("Supprimer Produit Sélectionné"));self.remove_line_btn.setIcon(QIcon(":/icons/trash.svg")); self.remove_line_btn.setObjectName("removeProductLineButton"); self.remove_line_btn.clicked.connect(self._remove_selected_line_from_table);main_layout.addWidget(self.remove_line_btn)
        self.overall_total_label=QLabel(self.tr("Total Général: € 0.00")); font=self.overall_total_label.font();font.setPointSize(font.pointSize()+3);font.setBold(True);self.overall_total_label.setFont(font); self.overall_total_label.setObjectName("overallTotalLabel"); self.overall_total_label.setAlignment(Qt.AlignRight);main_layout.addWidget(self.overall_total_label);main_layout.addStretch()

        button_frame=QFrame(self);button_frame.setObjectName("buttonFrame"); button_frame_layout=QHBoxLayout(button_frame);button_frame_layout.setContentsMargins(0,0,0,0) # QFrame was missing from plan
        button_box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);ok_button=button_box.button(QDialogButtonBox.Ok);ok_button.setText(self.tr("OK"));ok_button.setIcon(QIcon(":/icons/dialog-ok-apply.svg"));ok_button.setObjectName("primaryButton");cancel_button=button_box.button(QDialogButtonBox.Cancel);cancel_button.setText(self.tr("Annuler"));cancel_button.setIcon(QIcon(":/icons/dialog-cancel.svg"));button_box.accepted.connect(self.accept);button_box.rejected.connect(self.reject);button_frame_layout.addWidget(button_box);main_layout.addWidget(button_frame)

    def _update_current_line_total_preview(self):
        quantity=self.quantity_input.value();unit_price=self.unit_price_input.value();current_quantity=quantity if isinstance(quantity,(int,float)) else 0.0;current_unit_price=unit_price if isinstance(unit_price,(int,float)) else 0.0;line_total=current_quantity*current_unit_price;self.current_line_total_label.setText(f"€ {line_total:.2f}")

    def _add_current_line_to_table(self):
        name=self.name_input.text().strip();description=self.description_input.toPlainText().strip();quantity=self.quantity_input.value();unit_price=self.unit_price_input.value()
        current_weight = self.weight_input.value()
        current_dimensions = self.dimensions_input.text().strip()

        if not name:QMessageBox.warning(self,self.tr("Champ Requis"),self.tr("Le nom du produit est requis."));self.name_input.setFocus();return
        if quantity<=0:QMessageBox.warning(self,self.tr("Quantité Invalide"),self.tr("La quantité doit être supérieure à zéro."));self.quantity_input.setFocus();return
        line_total=quantity*unit_price;row_position=self.products_table.rowCount();self.products_table.insertRow(row_position);name_item=QTableWidgetItem(name);current_lang_code=self.product_language_filter_combo.currentText()
        if current_lang_code==self.tr("All"):current_lang_code="fr"
        name_item.setData(Qt.UserRole+1,current_lang_code)
        name_item.setData(Qt.UserRole+2, current_weight)
        name_item.setData(Qt.UserRole+3, current_dimensions)
        if self.current_selected_global_product_id is not None:
            name_item.setData(Qt.UserRole + 4, self.current_selected_global_product_id)
        else:
            name_item.setData(Qt.UserRole + 4, None)

        self.products_table.setItem(row_position,0,name_item);self.products_table.setItem(row_position,1,QTableWidgetItem(description));qty_item=QTableWidgetItem(f"{quantity:.2f}");qty_item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter);self.products_table.setItem(row_position,2,qty_item);price_item=QTableWidgetItem(f"€ {unit_price:.2f}");price_item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter);self.products_table.setItem(row_position,3,price_item);total_item=QTableWidgetItem(f"€ {line_total:.2f}");total_item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter);self.products_table.setItem(row_position,4,total_item)

        self.name_input.clear();self.description_input.clear();self.quantity_input.setValue(0.0);self.unit_price_input.setValue(0.0)
        self.weight_input.setValue(0.0); self.dimensions_input.clear()
        self.current_selected_global_product_id = None
        self.view_detailed_dimensions_button.setEnabled(False)
        self.global_weight_display_label.setText(self.tr("N/A"))
        self.global_dimensions_display_label.setText(self.tr("N/A"))
        self._update_current_line_total_preview();self._update_overall_total();self.name_input.setFocus()

    def on_view_detailed_dimensions(self):
        if self.current_selected_global_product_id is not None:
            # Pass app_root_dir to ProductDimensionUIDialog constructor
            dialog = ProductDimensionUIDialog(self.current_selected_global_product_id, self.app_root_dir, self, read_only=True)
            dialog.exec_()
        else:
            QMessageBox.information(self, self.tr("Aucun Produit Sélectionné"), self.tr("Veuillez d'abord sélectionner un produit dans la liste de recherche."))

    def _remove_selected_line_from_table(self):
        selected_rows = self.products_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, self.tr("Aucune Sélection"), self.tr("Veuillez sélectionner une ligne à supprimer."))
            return
        for index in sorted(selected_rows, reverse=True):
            self.products_table.removeRow(index.row())
        self._update_overall_total()

    def _update_overall_total(self):
        total_sum=0.0
        for row in range(self.products_table.rowCount()):
            item=self.products_table.item(row,4)
            if item and item.text():
                try:value_str=item.text().replace("€","").replace(",",".").strip();total_sum+=float(value_str)
                except ValueError: logging.warning(f"Could not parse float from table cell: {item.text()}") # Use logging
        self.overall_total_label.setText(self.tr("Total Général: € {0:.2f}").format(total_sum))

    def get_data(self):
        products_list=[]
        for row in range(self.products_table.rowCount()):
            name_item=self.products_table.item(row,0)
            name=name_item.text()
            description=self.products_table.item(row,1).text()
            qty_str=self.products_table.item(row,2).text().replace(",",".");quantity=float(qty_str) if qty_str else 0.0
            unit_price_str=self.products_table.item(row,3).text().replace("€","").replace(",",".").strip();unit_price=float(unit_price_str) if unit_price_str else 0.0
            line_total_str=self.products_table.item(row,4).text().replace("€","").replace(",",".").strip();line_total=float(line_total_str) if line_total_str else 0.0

            language_code=name_item.data(Qt.UserRole+1) if name_item else "fr"
            retrieved_weight = name_item.data(Qt.UserRole+2)
            retrieved_dimensions = name_item.data(Qt.UserRole+3)
            retrieved_global_product_id = name_item.data(Qt.UserRole+4)

            products_list.append({
                "client_id":self.client_id, "name":name, "description":description,
                "quantity":quantity, "unit_price":unit_price, "total_price":line_total,
                "language_code":language_code,
                "weight": float(retrieved_weight) if retrieved_weight is not None else 0.0,
                "dimensions": str(retrieved_dimensions) if retrieved_dimensions is not None else "",
                "product_id": retrieved_global_product_id,
                "client_country_id": self.client_info.get('country_id') if self.client_info else None,
                "client_city_id": self.client_info.get('city_id') if self.client_info else None
            })
        return products_list
