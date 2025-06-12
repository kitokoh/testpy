# -*- coding: utf-8 -*-
import sys
import os
import logging

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QDialog, QFormLayout, QComboBox,
    QInputDialog, QCompleter, QTabWidget, QAction, QMenu, QGroupBox,
    QStackedWidget, QDoubleSpinBox, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QTextEdit # Added QTextEdit for SettingsDialog notes
)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont
from PyQt5.QtCore import Qt, QUrl, QTimer, pyqtSlot

import db as db_manager
import icons_rc
from app_setup import APP_ROOT_DIR, CONFIG
from ui_components import StatisticsWidget, StatusDelegate
from document_manager_logic import (
    handle_create_client_execution,
    load_and_display_clients,
    filter_and_display_clients,
    perform_old_clients_check,
    handle_open_edit_client_dialog,
    archive_client_status,
    permanently_delete_client
)
from dialogs import (
    SettingsDialog, TemplateDialog, AddNewClientDialog, # EditClientDialog is called from logic
    ProductEquivalencyDialog, # Added for product equivalency
    ManageProductMasterDialog # Added for global product management
)
from product_list_dialog import ProductListDialog # Import the new dialog

# Dialogs directly instantiated by DocumentManager
from client_widget import ClientWidget # For client tabs
from projectManagement import MainDashboard as ProjectManagementDashboard # For PM tab
from statistics_module import StatisticsDashboard
from utils import save_config
from company_management import CompanyTabWidget
from partners.partner_main_widget import PartnerMainWidget # Partner Management


class SettingsDialog(OriginalSettingsDialog):
    def __init__(self, main_config, parent=None):
        super().__init__(main_config, parent)

        self._add_transporters_tab()
        self._add_freight_forwarders_tab()

        self.load_transporters_table()
        self.load_forwarders_table()

    def _add_transporters_tab(self):
        transporters_tab = QWidget()
        transporters_layout = QVBoxLayout(transporters_tab)

        self.transporters_table = QTableWidget()
        self.transporters_table.setColumnCount(6)
        self.transporters_table.setHorizontalHeaderLabels([
            "ID", self.tr("Nom"), self.tr("Contact"), self.tr("Téléphone"),
            self.tr("Email"), self.tr("Zone de Service")
        ])
        self.transporters_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.transporters_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.transporters_table.horizontalHeader().setStretchLastSection(True)
        self.transporters_table.hideColumn(0)
        self.transporters_table.itemSelectionChanged.connect(self.update_transporter_button_states)
        transporters_layout.addWidget(self.transporters_table)

        transporter_buttons_layout = QHBoxLayout()
        self.add_transporter_btn = QPushButton(self.tr("Ajouter Transporteur"))
        self.add_transporter_btn.setIcon(QIcon.fromTheme("list-add", QIcon(":/icons/plus.svg")))
        self.add_transporter_btn.clicked.connect(self.handle_add_transporter)

        self.edit_transporter_btn = QPushButton(self.tr("Modifier Transporteur"))
        self.edit_transporter_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg")))
        self.edit_transporter_btn.clicked.connect(self.handle_edit_transporter)
        self.edit_transporter_btn.setEnabled(False)

        self.delete_transporter_btn = QPushButton(self.tr("Supprimer Transporteur"))
        self.delete_transporter_btn.setIcon(QIcon.fromTheme("list-remove", QIcon(":/icons/trash.svg")))
        self.delete_transporter_btn.setObjectName("dangerButton")
        self.delete_transporter_btn.clicked.connect(self.handle_delete_transporter)
        self.delete_transporter_btn.setEnabled(False)

        transporter_buttons_layout.addWidget(self.add_transporter_btn)
        transporter_buttons_layout.addWidget(self.edit_transporter_btn)
        transporter_buttons_layout.addWidget(self.delete_transporter_btn)
        transporters_layout.addLayout(transporter_buttons_layout)

        self.tabs_widget.addTab(transporters_tab, self.tr("Transporteurs"))

    def _add_freight_forwarders_tab(self):
        forwarders_tab = QWidget()
        forwarders_layout = QVBoxLayout(forwarders_tab)

        self.forwarders_table = QTableWidget()
        self.forwarders_table.setColumnCount(6)
        self.forwarders_table.setHorizontalHeaderLabels([
            "ID", self.tr("Nom"), self.tr("Contact"), self.tr("Téléphone"),
            self.tr("Email"), self.tr("Services Offerts")
        ])
        self.forwarders_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.forwarders_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.forwarders_table.horizontalHeader().setStretchLastSection(True)
        self.forwarders_table.hideColumn(0)
        self.forwarders_table.itemSelectionChanged.connect(self.update_forwarder_button_states)
        forwarders_layout.addWidget(self.forwarders_table)

        forwarder_buttons_layout = QHBoxLayout()
        self.add_forwarder_btn = QPushButton(self.tr("Ajouter Transitaire"))
        self.add_forwarder_btn.setIcon(QIcon.fromTheme("list-add", QIcon(":/icons/plus.svg")))
        self.add_forwarder_btn.clicked.connect(self.handle_add_forwarder)

        self.edit_forwarder_btn = QPushButton(self.tr("Modifier Transitaire"))
        self.edit_forwarder_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg")))
        self.edit_forwarder_btn.clicked.connect(self.handle_edit_forwarder)
        self.edit_forwarder_btn.setEnabled(False)

        self.delete_forwarder_btn = QPushButton(self.tr("Supprimer Transitaire"))
        self.delete_forwarder_btn.setIcon(QIcon.fromTheme("list-remove", QIcon(":/icons/trash.svg")))
        self.delete_forwarder_btn.setObjectName("dangerButton")
        self.delete_forwarder_btn.clicked.connect(self.handle_delete_forwarder)
        self.delete_forwarder_btn.setEnabled(False)

        forwarder_buttons_layout.addWidget(self.add_forwarder_btn)
        forwarder_buttons_layout.addWidget(self.edit_forwarder_btn)
        forwarder_buttons_layout.addWidget(self.delete_forwarder_btn)
        forwarders_layout.addLayout(forwarder_buttons_layout)

        self.tabs_widget.addTab(forwarders_tab, self.tr("Transitaires"))

    def load_transporters_table(self):
        self.transporters_table.setRowCount(0)
        self.transporters_table.setSortingEnabled(False)
        try:
            transporters = db_manager.get_all_transporters()
            for row, transporter in enumerate(transporters):
                self.transporters_table.insertRow(row)
                id_item = QTableWidgetItem(transporter.get('transporter_id'))
                self.transporters_table.setItem(row, 0, id_item) # Hidden ID

                name_item = QTableWidgetItem(transporter.get('name'))
                name_item.setData(Qt.UserRole, transporter.get('transporter_id'))
                self.transporters_table.setItem(row, 1, name_item)
                self.transporters_table.setItem(row, 2, QTableWidgetItem(transporter.get('contact_person')))
                self.transporters_table.setItem(row, 3, QTableWidgetItem(transporter.get('phone')))
                self.transporters_table.setItem(row, 4, QTableWidgetItem(transporter.get('email')))
                self.transporters_table.setItem(row, 5, QTableWidgetItem(transporter.get('service_area')))
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des transporteurs: {0}").format(str(e)))
        self.transporters_table.setSortingEnabled(True)
        self.update_transporter_button_states()

    def handle_add_transporter(self):
        dialog = TransporterDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_transporters_table()

    def handle_edit_transporter(self):
        selected_items = self.transporters_table.selectedItems()
        if not selected_items: return
        selected_row = self.transporters_table.currentRow()
        transporter_id = self.transporters_table.item(selected_row, 0).text() # Get ID from hidden col 0
        transporter_data = db_manager.get_transporter_by_id(transporter_id)
        if transporter_data:
            dialog = TransporterDialog(transporter_data=transporter_data, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                self.load_transporters_table()

    def handle_delete_transporter(self):
        selected_items = self.transporters_table.selectedItems()
        if not selected_items: return
        selected_row = self.transporters_table.currentRow()
        transporter_id = self.transporters_table.item(selected_row, 0).text()
        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"),
                                     self.tr("Êtes-vous sûr de vouloir supprimer ce transporteur ?"),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if db_manager.delete_transporter(transporter_id):
                self.load_transporters_table()
            else:
                QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Impossible de supprimer le transporteur."))

    def update_transporter_button_states(self):
        has_selection = bool(self.transporters_table.selectedItems())
        self.edit_transporter_btn.setEnabled(has_selection)
        self.delete_transporter_btn.setEnabled(has_selection)

    def load_forwarders_table(self):
        self.forwarders_table.setRowCount(0)
        self.forwarders_table.setSortingEnabled(False)
        try:
            forwarders = db_manager.get_all_freight_forwarders()
            for row, forwarder in enumerate(forwarders):
                self.forwarders_table.insertRow(row)
                id_item = QTableWidgetItem(forwarder.get('forwarder_id'))
                self.forwarders_table.setItem(row, 0, id_item) # Hidden ID

                name_item = QTableWidgetItem(forwarder.get('name'))
                name_item.setData(Qt.UserRole, forwarder.get('forwarder_id'))
                self.forwarders_table.setItem(row, 1, name_item)
                self.forwarders_table.setItem(row, 2, QTableWidgetItem(forwarder.get('contact_person')))
                self.forwarders_table.setItem(row, 3, QTableWidgetItem(forwarder.get('phone')))
                self.forwarders_table.setItem(row, 4, QTableWidgetItem(forwarder.get('email')))
                self.forwarders_table.setItem(row, 5, QTableWidgetItem(forwarder.get('services_offered')))
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des transitaires: {0}").format(str(e)))
        self.forwarders_table.setSortingEnabled(True)
        self.update_forwarder_button_states()

    def handle_add_forwarder(self):
        dialog = FreightForwarderDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_forwarders_table()

    def handle_edit_forwarder(self):
        selected_items = self.forwarders_table.selectedItems()
        if not selected_items: return
        selected_row = self.forwarders_table.currentRow()
        forwarder_id = self.forwarders_table.item(selected_row, 0).text()
        forwarder_data = db_manager.get_freight_forwarder_by_id(forwarder_id)
        if forwarder_data:
            dialog = FreightForwarderDialog(forwarder_data=forwarder_data, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                self.load_forwarders_table()

    def handle_delete_forwarder(self):
        selected_items = self.forwarders_table.selectedItems()
        if not selected_items: return
        selected_row = self.forwarders_table.currentRow()
        forwarder_id = self.forwarders_table.item(selected_row, 0).text()
        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"),
                                     self.tr("Êtes-vous sûr de vouloir supprimer ce transitaire ?"),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if db_manager.delete_freight_forwarder(forwarder_id):
                self.load_forwarders_table()
            else:
                QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Impossible de supprimer le transitaire."))

    def update_forwarder_button_states(self):
        has_selection = bool(self.forwarders_table.selectedItems())
        self.edit_forwarder_btn.setEnabled(has_selection)
        self.delete_forwarder_btn.setEnabled(has_selection)


class DocumentManager(QMainWindow):
    def __init__(self, app_root_dir):
        super().__init__()
        self.app_root_dir = app_root_dir
        self.setWindowTitle(self.tr("Gestionnaire de Documents Client")); self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon.fromTheme("folder-documents"))
        
        self.config = CONFIG 
        db_google_maps_url = db_manager.get_setting('google_maps_review_url')
        if db_google_maps_url is not None:
            self.config['google_maps_review_url'] = db_google_maps_url
        elif 'google_maps_review_url' not in self.config:
            self.config['google_maps_review_url'] = 'https://maps.google.com/?cid=YOUR_CID_HERE'

        self.clients_data_map = {} 
        
        self.setup_ui_main() 

        self.project_management_widget_instance = ProjectManagementDashboard(parent=self, current_user=None)
        self.main_area_stack.addWidget(self.project_management_widget_instance)

        self.statistics_dashboard_instance = StatisticsDashboard(parent=self)
        self.main_area_stack.addWidget(self.statistics_dashboard_instance)

        self.partner_management_widget_instance = PartnerMainWidget(parent=self)
        self.main_area_stack.addWidget(self.partner_management_widget_instance)

        self.main_area_stack.setCurrentWidget(self.documents_page_widget)

        self.create_actions_main() 
        self.create_menus_main()

        if hasattr(self, 'statistics_dashboard_instance') and self.statistics_dashboard_instance:
            if hasattr(self.statistics_dashboard_instance, 'country_selected_for_new_client'):
                self.statistics_dashboard_instance.country_selected_for_new_client.connect(self.prepare_new_client_for_country)
                print("Connected statistics_dashboard_instance.country_selected_for_new_client to prepare_new_client_for_country")
            else:
                print("Error: statistics_dashboard_instance does not have 'country_selected_for_new_client' signal.")
        else:
            print("Error: statistics_dashboard_instance not found for signal connection.")
        
        load_and_display_clients(self) 
        if self.stats_widget:
            self.stats_widget.update_stats() 
        
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_old_clients_routine_slot)
        self.check_timer.start(3600000)
        
    def setup_ui_main(self): 
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget); main_layout.setContentsMargins(10,10,10,10); main_layout.setSpacing(10)
        
        self.stats_widget = StatisticsWidget(); main_layout.addWidget(self.stats_widget)

        self.main_area_stack = QStackedWidget()
        main_layout.addWidget(self.main_area_stack)

        self.documents_page_widget = QWidget()
        content_layout = QHBoxLayout(self.documents_page_widget)
        
        left_panel = QWidget(); left_layout = QVBoxLayout(left_panel); left_layout.setContentsMargins(5,5,5,5)
        filter_search_layout = QHBoxLayout() 
        self.status_filter_combo = QComboBox(); self.status_filter_combo.addItem(self.tr("Tous les statuts"))
        self.load_statuses_into_filter_combo() 
        self.status_filter_combo.currentIndexChanged.connect(self.filter_client_list_display_slot) 
        filter_search_layout.addWidget(QLabel(self.tr("Filtrer par statut:")))
        filter_search_layout.addWidget(self.status_filter_combo)

        self.client_archive_filter_combo = QComboBox()
        self.client_archive_filter_combo.addItem(self.tr("Afficher Actifs (et sans statut)"), "active_including_null")
        self.client_archive_filter_combo.addItem(self.tr("Afficher Actifs (avec statut assigné)"), "active_only_with_status")
        self.client_archive_filter_combo.addItem(self.tr("Afficher Archivés Uniquement"), "archived_only")
        self.client_archive_filter_combo.addItem(self.tr("Afficher Tout"), "all")
        self.client_archive_filter_combo.setCurrentIndex(0)
        self.client_archive_filter_combo.currentIndexChanged.connect(self.filter_client_list_display_slot)
        filter_search_layout.addWidget(QLabel(self.tr("Filtre Archive:")))
        filter_search_layout.addWidget(self.client_archive_filter_combo)

        self.search_input_field = QLineEdit(); self.search_input_field.setPlaceholderText(self.tr("Rechercher client..."))
        self.search_input_field.textChanged.connect(self.filter_client_list_display_slot) 
        filter_search_layout.addWidget(self.search_input_field); left_layout.addLayout(filter_search_layout)
        
        self.client_list_widget = QListWidget(); self.client_list_widget.setAlternatingRowColors(True) 
        self.client_list_widget.setItemDelegate(StatusDelegate(self.client_list_widget))
        self.client_list_widget.itemClicked.connect(self.handle_client_list_click) 
        self.client_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.client_list_widget.customContextMenuRequested.connect(self.show_client_context_menu)
        left_layout.addWidget(self.client_list_widget)
        
        self.add_new_client_button = QPushButton(self.tr("Ajouter un Nouveau Client"))
        self.add_new_client_button.setIcon(QIcon(":/icons/modern/user-add.svg"))
        self.add_new_client_button.setObjectName("primaryButton")
        self.add_new_client_button.clicked.connect(self.open_add_new_client_dialog)
        left_layout.addWidget(self.add_new_client_button)

        self.form_group_box = QGroupBox(self.tr("Ajouter un Nouveau Client"))
        form_vbox_layout = QVBoxLayout(self.form_group_box)

        self.form_container_widget = QWidget()
        creation_form_layout = QFormLayout(self.form_container_widget)
        creation_form_layout.setLabelAlignment(Qt.AlignRight)
        creation_form_layout.setSpacing(10)
        
        self.client_name_input = QLineEdit(); self.client_name_input.setPlaceholderText(self.tr("Nom du client"))
        creation_form_layout.addRow(self.tr("Nom Client:"), self.client_name_input)
        self.company_name_input = QLineEdit(); self.company_name_input.setPlaceholderText(self.tr("Nom entreprise (optionnel)"))
        creation_form_layout.addRow(self.tr("Nom Entreprise:"), self.company_name_input)
        self.client_need_input = QLineEdit(); self.client_need_input.setPlaceholderText(self.tr("Besoin principal du client"))
        creation_form_layout.addRow(self.tr("Besoin Client:"), self.client_need_input)
        
        country_hbox_layout = QHBoxLayout(); self.country_select_combo = QComboBox() 
        self.country_select_combo.setEditable(True); self.country_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.country_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.country_select_combo.completer().setFilterMode(Qt.MatchContains)
        # self.country_select_combo.currentTextChanged.connect(self.load_cities_for_country) 
        country_hbox_layout.addWidget(self.country_select_combo)
        self.add_country_button = QPushButton("+"); self.add_country_button.setFixedSize(30,30) 
        self.add_country_button.setToolTip(self.tr("Ajouter un nouveau pays"))
        # self.add_country_button.clicked.connect(self.add_new_country_dialog) 
        country_hbox_layout.addWidget(self.add_country_button); creation_form_layout.addRow(self.tr("Pays Client:"), country_hbox_layout)
        
        city_hbox_layout = QHBoxLayout(); self.city_select_combo = QComboBox() 
        self.city_select_combo.setEditable(True); self.city_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.city_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.city_select_combo.completer().setFilterMode(Qt.MatchContains)
        city_hbox_layout.addWidget(self.city_select_combo)
        self.add_city_button = QPushButton("+"); self.add_city_button.setFixedSize(30,30) 
        self.add_city_button.setToolTip(self.tr("Ajouter une nouvelle ville"))
        # self.add_city_button.clicked.connect(self.add_new_city_dialog) 
        city_hbox_layout.addWidget(self.add_city_button); creation_form_layout.addRow(self.tr("Ville Client:"), city_hbox_layout)
        
        self.project_id_input_field = QLineEdit(); self.project_id_input_field.setPlaceholderText(self.tr("Identifiant unique du projet"))
        creation_form_layout.addRow(self.tr("ID Projet:"), self.project_id_input_field)
        
        self.final_price_input = QDoubleSpinBox(); self.final_price_input.setPrefix("€ ") 
        self.final_price_input.setRange(0, 10000000); self.final_price_input.setValue(0)
        self.final_price_input.setReadOnly(True)
        creation_form_layout.addRow(self.tr("Prix Final:"), self.final_price_input)
        price_info_label = QLabel(self.tr("Le prix final est calculé automatiquement à partir des produits ajoutés."))
        price_info_label.setObjectName("priceInfoLabel")
        creation_form_layout.addRow("", price_info_label)
        
        self.language_select_combo = QComboBox()
        self.language_select_combo.addItems([
            self.tr("English only (en)"), self.tr("French only (fr)"),
            self.tr("Arabic only (ar)"), self.tr("Turkish only (tr)"),
            self.tr("Portuguese only (pt)"), self.tr("All supported languages (en, fr, ar, tr, pt)")
        ])
        creation_form_layout.addRow(self.tr("Langues:"), self.language_select_combo)
        
        self.create_client_button = QPushButton(self.tr("Créer Client")); self.create_client_button.setIcon(QIcon(":/icons/modern/user-add.svg"))
        self.create_client_button.setObjectName("primaryButton")
        self.create_client_button.clicked.connect(self.execute_create_client_slot) 
        creation_form_layout.addRow(self.create_client_button)

        form_vbox_layout.addWidget(self.form_container_widget)
        self.form_group_box.setCheckable(True)
        self.form_group_box.toggled.connect(self.form_container_widget.setVisible)
        self.form_group_box.setChecked(False)
        left_layout.addWidget(self.form_group_box)
        content_layout.addWidget(left_panel, 1)
        
        self.client_tabs_widget = QTabWidget(); self.client_tabs_widget.setTabsClosable(True) 
        self.client_tabs_widget.tabCloseRequested.connect(self.close_client_tab) 
        content_layout.addWidget(self.client_tabs_widget, 2)

        self.main_area_stack.addWidget(self.documents_page_widget)
        
    def open_add_new_client_dialog(self):
        dialog = AddNewClientDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            client_data = dialog.get_data()
            if client_data:
                handle_create_client_execution(self, client_data_dict=client_data)

    def create_actions_main(self): 
        self.settings_action = QAction(QIcon(":/icons/modern/settings.svg"), self.tr("Paramètres"), self); self.settings_action.triggered.connect(self.open_settings_dialog)
        self.template_action = QAction(QIcon(":/icons/modern/templates.svg"), self.tr("Gérer les Modèles"), self); self.template_action.triggered.connect(self.open_template_manager_dialog)
        self.status_action = QAction(QIcon(":/icons/check-square.svg"), self.tr("Gérer les Statuts"), self); self.status_action.triggered.connect(self.open_status_manager_dialog)
        self.status_action.setEnabled(False)
        self.status_action.setToolTip(self.tr("Fonctionnalité de gestion des statuts prévue pour une future version."))
        self.exit_action = QAction(QIcon(":/icons/log-out.svg"), self.tr("Quitter"), self); self.exit_action.setShortcut("Ctrl+Q"); self.exit_action.triggered.connect(self.close)
        self.project_management_action = QAction(QIcon(":/icons/modern/dashboard.svg"), self.tr("Gestion de Projet"), self)
        self.project_management_action.triggered.connect(self.show_project_management_view)
        self.documents_view_action = QAction(QIcon(":/icons/modern/folder-docs.svg"), self.tr("Gestion Documents"), self)
        self.documents_view_action.triggered.connect(self.show_documents_view)
        
        self.statistics_action = QAction(QIcon(":/icons/bar-chart.svg"), self.tr("Statistiques Détaillées"), self)
        self.statistics_action.triggered.connect(self.show_statistics_view)

        self.product_equivalency_action = QAction(QIcon.fromTheme("document-properties", QIcon(":/icons/modern/link.svg")), self.tr("Gérer Équivalences Produits"), self)
        self.product_equivalency_action.triggered.connect(self.open_product_equivalency_dialog)

        self.product_list_action = QAction(QIcon(":/icons/book.svg"), self.tr("Product List"), self) # Using a generic book icon for now
        self.product_list_action.triggered.connect(self.open_product_list_placeholder)

        self.partner_management_action = QAction(QIcon(":/icons/team.svg"), self.tr("Partner Management"), self)
        self.partner_management_action.triggered.connect(self.show_partner_management_view)


    def create_menus_main(self): 
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu(self.tr("Fichier"))
        file_menu.addAction(self.settings_action); file_menu.addAction(self.template_action); file_menu.addAction(self.status_action)
        file_menu.addAction(self.product_equivalency_action)
        file_menu.addSeparator(); file_menu.addAction(self.exit_action)
        modules_menu = menu_bar.addMenu(self.tr("Modules"))
        modules_menu.addAction(self.documents_view_action)
        modules_menu.addAction(self.project_management_action)
        modules_menu.addAction(self.statistics_action)
        modules_menu.addAction(self.product_list_action) # Add new action here
        modules_menu.addAction(self.partner_management_action) # Add Partner Management action
        help_menu = menu_bar.addMenu(self.tr("Aide"))
        about_action = QAction(QIcon(":/icons/help-circle.svg"), self.tr("À propos"), self); about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_project_management_view(self):
        self.main_area_stack.setCurrentWidget(self.project_management_widget_instance)

    def show_documents_view(self):
        self.main_area_stack.setCurrentWidget(self.documents_page_widget)
        
    def show_statistics_view(self):
        self.main_area_stack.setCurrentWidget(self.statistics_dashboard_instance)

    def show_partner_management_view(self):
        self.main_area_stack.setCurrentWidget(self.partner_management_widget_instance)

    def show_about_dialog(self): 
        QMessageBox.about(self, self.tr("À propos"), self.tr("<b>Gestionnaire de Documents Client</b><br><br>Version 4.0<br>Application de gestion de documents clients avec templates Excel.<br><br>Développé par Saadiya Management (Concept)"))
        
    def execute_create_client_slot(self, client_data_dict=None):
        handle_create_client_execution(self, client_data_dict=client_data_dict)

    def load_clients_from_db_slot(self): load_and_display_clients(self)
    def filter_client_list_display_slot(self): filter_and_display_clients(self)
    def check_old_clients_routine_slot(self): perform_old_clients_check(self)
    def open_edit_client_dialog_slot(self, client_id): handle_open_edit_client_dialog(self, client_id)
    def set_client_status_archived_slot(self, client_id): archive_client_status(self, client_id)
    def delete_client_permanently_slot(self, client_id): permanently_delete_client(self, client_id)

    def execute_create_client(self, client_data_dict=None): self.execute_create_client_slot(client_data_dict=client_data_dict)
    def load_clients_from_db(self): self.load_clients_from_db_slot()
    def filter_client_list_display(self): self.filter_client_list_display_slot()
    def check_old_clients_routine(self): self.check_old_clients_routine_slot()
    def open_edit_client_dialog(self, client_id): self.open_edit_client_dialog_slot(client_id)
    def set_client_status_archived(self, client_id): self.set_client_status_archived_slot(client_id)
    def delete_client_permanently(self, client_id): self.delete_client_permanently_slot(client_id)

    def add_client_to_list_widget(self, client_dict_data): 
        item = QListWidgetItem(client_dict_data["client_name"])
        item.setData(Qt.UserRole, client_dict_data)
        self.client_list_widget.addItem(item)
            
    def load_statuses_into_filter_combo(self): 
        current_selection_data = self.status_filter_combo.currentData()
        self.status_filter_combo.clear()
        self.status_filter_combo.addItem(self.tr("Tous les statuts"), None)
        try:
            client_statuses = db_manager.get_all_status_settings(status_type='Client')
            if client_statuses is None: client_statuses = []
            for status_dict in client_statuses:
                self.status_filter_combo.addItem(status_dict['status_name'], status_dict.get('status_id'))
            index = self.status_filter_combo.findData(current_selection_data)
            if index != -1: self.status_filter_combo.setCurrentIndex(index)
        except Exception as e:
            print(self.tr("Erreur chargement statuts pour filtre: {0}").format(str(e)))
            
    def handle_client_list_click(self, item): 
        client_data = item.data(Qt.UserRole)
        if client_data and client_data.get("client_id"):
            self.open_client_tab_by_id(client_data["client_id"])
        
    def open_client_tab_by_id(self, client_id_to_open): 
        client_data_to_show = self.clients_data_map.get(client_id_to_open)
        if not client_data_to_show:
            client_data_to_show = db_manager.get_client_by_id(client_id_to_open)
            if not client_data_to_show:
                QMessageBox.warning(self, self.tr("Erreur"), self.tr("Données client non trouvées pour ID: {0}").format(client_id_to_open))
                return
            self.clients_data_map[client_id_to_open] = client_data_to_show

        for i in range(self.client_tabs_widget.count()):
            tab_widget_ref = self.client_tabs_widget.widget(i) 
            if hasattr(tab_widget_ref, 'client_info') and tab_widget_ref.client_info["client_id"] == client_id_to_open:
                self.client_tabs_widget.setCurrentIndex(i)
                return

        client_detail_widget = ClientWidget(client_data_to_show, self.config, self.app_root_dir, parent=self)
        tab_idx = self.client_tabs_widget.addTab(client_detail_widget, client_data_to_show["client_name"]) 
        self.client_tabs_widget.setCurrentIndex(tab_idx)
            
    def close_client_tab(self, index): 
        widget_to_close = self.client_tabs_widget.widget(index) 
        if widget_to_close: widget_to_close.deleteLater()
        self.client_tabs_widget.removeTab(index)
        
    def show_client_context_menu(self, pos):
        list_item = self.client_list_widget.itemAt(pos) 
        if not list_item: return
        client_data = list_item.data(Qt.UserRole)
        client_id_val = client_data.get("client_id") if client_data else None
        if not client_id_val: return

        menu = QMenu()
        open_action = menu.addAction(QIcon(":/icons/eye.svg"), self.tr("Ouvrir Fiche Client")); open_action.triggered.connect(lambda: self.open_client_tab_by_id(client_id_val))
        edit_action = menu.addAction(QIcon(":/icons/pencil.svg"), self.tr("Modifier Client")); edit_action.triggered.connect(lambda: self.open_edit_client_dialog_slot(client_id_val))
        open_folder_action = menu.addAction(QIcon(":/icons/folder.svg"), self.tr("Ouvrir Dossier Client")); open_folder_action.triggered.connect(lambda: self.open_client_folder_fs(client_id_val))
        menu.addSeparator()
        archive_action = menu.addAction(QIcon(":/icons/briefcase.svg"), self.tr("Archiver Client")); archive_action.triggered.connect(lambda: self.set_client_status_archived_slot(client_id_val))
        delete_action = menu.addAction(QIcon(":/icons/trash.svg"), self.tr("Supprimer Client")); delete_action.triggered.connect(lambda: self.delete_client_permanently_slot(client_id_val))
        menu.exec_(self.client_list_widget.mapToGlobal(pos))
        
    def open_client_folder_fs(self, client_id_val): 
        client_info = self.clients_data_map.get(client_id_val)
        if client_info and client_info.get("base_folder_path"):
            QDesktopServices.openUrl(QUrl.fromLocalFile(client_info["base_folder_path"]))
        else:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Chemin du dossier non trouvé pour ce client."))
            
    def open_settings_dialog(self): 
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            new_conf = dialog.get_config() 

            google_maps_url_from_dialog = new_conf.get("google_maps_review_url")
            if google_maps_url_from_dialog is not None:
                db_manager.set_setting('google_maps_review_url', google_maps_url_from_dialog)
                self.config['google_maps_review_url'] = google_maps_url_from_dialog

            self.config.update(new_conf)
            save_config(self.config)

            new_language_code = self.config.get('language')
            if new_language_code:
                try:
                    db_manager.set_setting('user_selected_language', new_language_code)
                    logging.info(f"User language preference '{new_language_code}' saved to database.")
                except Exception as e:
                    logging.error(f"Error saving language preference to database: {e}", exc_info=True)
                    QMessageBox.warning(self, self.tr("Erreur Base de Données"), self.tr("Impossible d'enregistrer la préférence linguistique dans la base de données : {0}").format(str(e)))

            os.makedirs(self.config["templates_dir"], exist_ok=True) 
            os.makedirs(self.config["clients_dir"], exist_ok=True)
            QMessageBox.information(self, self.tr("Paramètres Sauvegardés"), self.tr("Nouveaux paramètres enregistrés."))
            
    def open_template_manager_dialog(self): TemplateDialog(self.config, self).exec_()
        
    def open_status_manager_dialog(self): 
        QMessageBox.information(self, self.tr("Gestion des Statuts"), self.tr("Fonctionnalité de gestion des statuts personnalisés à implémenter."))
            
    def open_product_equivalency_dialog(self):
        dialog = ProductEquivalencyDialog(self)
        dialog.exec_()

    def open_product_list_placeholder(self):
        # print("Product List button clicked - Placeholder function")
        # QMessageBox.information(self, self.tr("Product List"), self.tr("This feature is not yet implemented."))
        dialog = ProductListDialog(self)
        dialog.exec_()

    def closeEvent(self, event): 
        save_config(self.config)
        super().closeEvent(event)

    @pyqtSlot(str)
    def prepare_new_client_for_country(self, country_name_str):
        print(f"[MainWindow] prepare_new_client_for_country called for: {country_name_str}")
        self.show_documents_view()
        if hasattr(self, 'form_group_box') and self.form_group_box:
            self.form_group_box.setChecked(True)
            if hasattr(self, 'form_container_widget'):
                 self.form_container_widget.setVisible(True)
        else:
            print("Warning: 'form_group_box' not found in MainWindow. Cannot expand new client form.")
            return

        country_successfully_selected = False
        if hasattr(self, 'country_select_combo') and self.country_select_combo:
            for i in range(self.country_select_combo.count()):
                if self.country_select_combo.itemText(i).lower() == country_name_str.lower():
                    self.country_select_combo.setCurrentIndex(i)
                    print(f"Country '{country_name_str}' found and selected in combobox.")
                    country_successfully_selected = True
                    break

            if not country_successfully_selected:
                print(f"Country '{country_name_str}' not initially found in combobox. Attempting to add/verify in DB.")
                try:
                    country_data = db_manager.get_or_add_country(country_name_str)
                    if country_data and country_data.get('country_id') is not None:
                        new_country_id = country_data.get('country_id')
                        new_country_name = country_data.get('country_name', country_name_str)
                        print(f"Country '{new_country_name}' (ID: {new_country_id}) confirmed/added in DB.")
                        self.load_countries_into_combo()
                        index_to_select = -1
                        for i in range(self.country_select_combo.count()):
                            item_id = self.country_select_combo.itemData(i)
                            if item_id is not None and item_id == new_country_id:
                                index_to_select = i
                                break
                            elif self.country_select_combo.itemText(i).lower() == new_country_name.lower():
                                index_to_select = i
                        if index_to_select != -1:
                            self.country_select_combo.setCurrentIndex(index_to_select)
                            print(f"Country '{new_country_name}' selected in combobox after DB add/verify and reload.")
                            country_successfully_selected = True
                        else:
                            print(f"Error: Country '{new_country_name}' was added/found in DB, but NOT found in combobox after reload.")
                            if self.country_select_combo.isEditable():
                                self.country_select_combo.lineEdit().setText(new_country_name)
                                print(f"Set combobox text to '{new_country_name}' as a fallback.")
                    else:
                        print(f"Error: Country '{country_name_str}' could not be added to or found in the database via get_or_add_country.")
                except Exception as e:
                    print(f"An exception occurred while trying to add/select country '{country_name_str}': {e}")
        else:
            print("Warning: 'country_select_combo' not found in MainWindow. Cannot pre-fill country.")

        if hasattr(self, 'client_name_input') and self.client_name_input:
            QTimer.singleShot(0, self.client_name_input.setFocus)
            if country_successfully_selected:
                 print(f"Focus set to client name input for country '{country_name_str}'.")
            else:
                 print(f"Focus set to client name input. Country '{country_name_str}' was not selected in combobox.")
        else:
            print("Warning: 'client_name_input' not found. Cannot set focus.")

    def load_countries_into_combo(self):
        if hasattr(self, 'country_select_combo'):
            self.country_select_combo.clear()
            try:
                countries = db_manager.get_all_countries()
                if countries is None: countries = []
                for country_dict in countries:
                    self.country_select_combo.addItem(country_dict['country_name'], country_dict.get('country_id'))
            except Exception as e:
                QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des pays:\n{0}").format(str(e)))

    def load_cities_for_country(self, country_name_str):
        if hasattr(self, 'city_select_combo'):
            self.city_select_combo.clear()
            if not country_name_str: return
            selected_country_id = self.country_select_combo.currentData()
            if selected_country_id is None:
                country_obj_by_name = db_manager.get_country_by_name(country_name_str)
                if country_obj_by_name: selected_country_id = country_obj_by_name['country_id']
                else: return
            try:
                cities = db_manager.get_all_cities(country_id=selected_country_id)
                if cities is None: cities = []
                for city_dict in cities:
                    self.city_select_combo.addItem(city_dict['city_name'], city_dict.get('city_id'))
            except Exception as e:
                QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des villes:\n{0}").format(str(e)))

    def add_new_country_dialog(self):
        country_text, ok = QInputDialog.getText(self, self.tr("Nouveau Pays"), self.tr("Entrez le nom du nouveau pays:"))
        if ok and country_text.strip():
            try:
                returned_country_id = db_manager.add_country({'country_name': country_text.strip()})
                if returned_country_id is not None:
                    self.load_countries_into_combo()
                    index = self.country_select_combo.findText(country_text.strip())
                    if index >= 0: self.country_select_combo.setCurrentIndex(index)
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du pays. Vérifiez les logs."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur inattendue est survenue:\n{0}").format(str(e)))

    def add_new_city_dialog(self):
        current_country_name = self.country_select_combo.currentText()
        current_country_id = self.country_select_combo.currentData()
        if not current_country_id:
            QMessageBox.warning(self, self.tr("Pays Requis"), self.tr("Veuillez d'abord sélectionner un pays valide."))
            return
        city_text, ok = QInputDialog.getText(self, self.tr("Nouvelle Ville"), self.tr("Entrez le nom de la nouvelle ville pour {0}:").format(current_country_name))
        if ok and city_text.strip():
            try:
                returned_city_id = db_manager.add_city({'country_id': current_country_id, 'city_name': city_text.strip()})
                if returned_city_id is not None:
                    self.load_cities_for_country(current_country_name)
                    index = self.city_select_combo.findText(city_text.strip())
                    if index >= 0: self.city_select_combo.setCurrentIndex(index)
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout de la ville. Vérifiez les logs."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur inattendue est survenue:\n{0}").format(str(e)))

# If main() and other app setup logic is moved to main.py, this file should only contain DocumentManager
# and its necessary imports.
