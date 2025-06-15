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
    QTextEdit, QSplitter, QApplication # Added QTextEdit for SettingsDialog notes, QSplitter for layout, QApplication

)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont
from PyQt5.QtCore import Qt, QUrl, QTimer, pyqtSlot
from PyQt5.QtWebEngineWidgets import QWebEngineView # Retain for ClientWidget if it uses it, or remove if not. Map is removed from DocMan.
from PyQt5.QtWebChannel import QWebChannel # Retain for ClientWidget if it uses it.

import db as db_manager
from db.cruds.clients_crud import clients_crud_instance
from db.cruds.products_crud import products_crud_instance
from db.cruds.products_crud import products_crud_instance # Import products instance
from db.cruds.transporters_crud import get_all_transporters # Added import
from db.cruds.freight_forwarders_crud import get_all_freight_forwarders # Added import
import icons_rc
# import folium # No longer used directly by DocumentManager for its own map
# from statistics_module import MapInteractionHandler # DocumentManager no longer has its own map handler instance
from app_setup import APP_ROOT_DIR, CONFIG
# from ui_components import StatisticsWidget # StatisticsWidget removed from main_layout
from ui_components import StatusDelegate # Still used for QListWidget
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
    SettingsDialog as OriginalSettingsDialog, TemplateDialog, AddNewClientDialog,
    ProductEquivalencyDialog,
    ManageProductMasterDialog,
    TransporterDialog,
    FreightForwarderDialog
)
from product_list_dialog import ProductListDialog

from client_widget import ClientWidget
from projectManagement import MainDashboard as ProjectManagementDashboard
from statistics_module import StatisticsDashboard
from statistics_panel import CollapsibleStatisticsWidget

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
        self.transporters_table.setHorizontalHeaderLabels(["ID", self.tr("Nom"), self.tr("Contact"), self.tr("Téléphone"), self.tr("Email"), self.tr("Zone de Service")])
        self.transporters_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.transporters_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.transporters_table.horizontalHeader().setStretchLastSection(True); self.transporters_table.hideColumn(0)
        self.transporters_table.itemSelectionChanged.connect(self.update_transporter_button_states)
        transporters_layout.addWidget(self.transporters_table)
        btns_layout = QHBoxLayout()
        self.add_transporter_btn = QPushButton(self.tr("Ajouter Transporteur")); self.add_transporter_btn.setIcon(QIcon.fromTheme("list-add", QIcon(":/icons/plus.svg"))); self.add_transporter_btn.clicked.connect(self.handle_add_transporter)
        self.edit_transporter_btn = QPushButton(self.tr("Modifier Transporteur")); self.edit_transporter_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg"))); self.edit_transporter_btn.clicked.connect(self.handle_edit_transporter); self.edit_transporter_btn.setEnabled(False)
        self.delete_transporter_btn = QPushButton(self.tr("Supprimer Transporteur")); self.delete_transporter_btn.setIcon(QIcon.fromTheme("list-remove", QIcon(":/icons/trash.svg"))); self.delete_transporter_btn.setObjectName("dangerButton"); self.delete_transporter_btn.clicked.connect(self.handle_delete_transporter); self.delete_transporter_btn.setEnabled(False)
        btns_layout.addWidget(self.add_transporter_btn); btns_layout.addWidget(self.edit_transporter_btn); btns_layout.addWidget(self.delete_transporter_btn)
        transporters_layout.addLayout(btns_layout)
        self.tabs_widget.addTab(transporters_tab, self.tr("Transporteurs"))

    def _add_freight_forwarders_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        self.forwarders_table = QTableWidget(); self.forwarders_table.setColumnCount(6)
        self.forwarders_table.setHorizontalHeaderLabels(["ID", self.tr("Nom"), self.tr("Contact"), self.tr("Téléphone"), self.tr("Email"), self.tr("Services Offerts")])
        self.forwarders_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.forwarders_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.forwarders_table.horizontalHeader().setStretchLastSection(True); self.forwarders_table.hideColumn(0)
        self.forwarders_table.itemSelectionChanged.connect(self.update_forwarder_button_states); layout.addWidget(self.forwarders_table)
        btns_layout = QHBoxLayout()
        self.add_forwarder_btn = QPushButton(self.tr("Ajouter Transitaire")); self.add_forwarder_btn.setIcon(QIcon.fromTheme("list-add", QIcon(":/icons/plus.svg"))); self.add_forwarder_btn.clicked.connect(self.handle_add_forwarder)
        self.edit_forwarder_btn = QPushButton(self.tr("Modifier Transitaire")); self.edit_forwarder_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg"))); self.edit_forwarder_btn.clicked.connect(self.handle_edit_forwarder); self.edit_forwarder_btn.setEnabled(False)
        self.delete_forwarder_btn = QPushButton(self.tr("Supprimer Transitaire")); self.delete_forwarder_btn.setIcon(QIcon.fromTheme("list-remove", QIcon(":/icons/trash.svg"))); self.delete_forwarder_btn.setObjectName("dangerButton"); self.delete_forwarder_btn.clicked.connect(self.handle_delete_forwarder); self.delete_forwarder_btn.setEnabled(False)
        btns_layout.addWidget(self.add_forwarder_btn); btns_layout.addWidget(self.edit_forwarder_btn); btns_layout.addWidget(self.delete_forwarder_btn)
        layout.addLayout(btns_layout)
        self.tabs_widget.addTab(tab, self.tr("Transitaires"))

    def load_transporters_table(self):
        self.transporters_table.setRowCount(0); self.transporters_table.setSortingEnabled(False)
        try:
            for r, t in enumerate(get_all_transporters() or []):
                self.transporters_table.insertRow(r)
                id_item = QTableWidgetItem(t.get('transporter_id')); self.transporters_table.setItem(r,0,id_item)
                name_item = QTableWidgetItem(t.get('name')); name_item.setData(Qt.UserRole, t.get('transporter_id')); self.transporters_table.setItem(r,1,name_item)
                self.transporters_table.setItem(r,2,QTableWidgetItem(t.get('contact_person'))); self.transporters_table.setItem(r,3,QTableWidgetItem(t.get('phone'))); self.transporters_table.setItem(r,4,QTableWidgetItem(t.get('email'))); self.transporters_table.setItem(r,5,QTableWidgetItem(t.get('service_area')))
        except Exception as e: QMessageBox.warning(self,self.tr("Erreur DB"),self.tr("Erreur de chargement des transporteurs: {0}").format(str(e)))
        self.transporters_table.setSortingEnabled(True); self.update_transporter_button_states()
    def handle_add_transporter(self):
        if TransporterDialog(parent=self).exec_()==QDialog.Accepted: self.load_transporters_table()
    def handle_edit_transporter(self):
        if not self.transporters_table.selectedItems(): return
        t_id=self.transporters_table.item(self.transporters_table.currentRow(),0).text()
        if db_manager.get_transporter_by_id(t_id) and TransporterDialog(db_manager.get_transporter_by_id(t_id),self).exec_()==QDialog.Accepted: self.load_transporters_table()
    def handle_delete_transporter(self):
        if not self.transporters_table.selectedItems(): return
        t_id=self.transporters_table.item(self.transporters_table.currentRow(),0).text()
        if QMessageBox.question(self,self.tr("Confirmer Suppression"),self.tr("Supprimer ce transporteur?"),QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes and db_manager.delete_transporter(t_id): self.load_transporters_table()
        else: QMessageBox.warning(self,self.tr("Erreur DB"),self.tr("Impossible de supprimer."))
    def update_transporter_button_states(self): en=bool(self.transporters_table.selectedItems()); self.edit_transporter_btn.setEnabled(en); self.delete_transporter_btn.setEnabled(en)
    def load_forwarders_table(self):
        self.forwarders_table.setRowCount(0); self.forwarders_table.setSortingEnabled(False)
        try:
            for r,f in enumerate(get_all_freight_forwarders() or []):
                self.forwarders_table.insertRow(r)
                id_item=QTableWidgetItem(f.get('forwarder_id')); self.forwarders_table.setItem(r,0,id_item)
                name_item=QTableWidgetItem(f.get('name')); name_item.setData(Qt.UserRole,f.get('forwarder_id')); self.forwarders_table.setItem(r,1,name_item)
                self.forwarders_table.setItem(r,2,QTableWidgetItem(f.get('contact_person'))); self.forwarders_table.setItem(r,3,QTableWidgetItem(f.get('phone'))); self.forwarders_table.setItem(r,4,QTableWidgetItem(f.get('email'))); self.forwarders_table.setItem(r,5,QTableWidgetItem(f.get('services_offered')))
        except Exception as e: QMessageBox.warning(self,self.tr("Erreur DB"),self.tr("Erreur de chargement des transitaires: {0}").format(str(e)))
        self.forwarders_table.setSortingEnabled(True); self.update_forwarder_button_states()
    def handle_add_forwarder(self):
        if FreightForwarderDialog(parent=self).exec_()==QDialog.Accepted: self.load_forwarders_table()
    def handle_edit_forwarder(self):
        if not self.forwarders_table.selectedItems(): return
        f_id=self.forwarders_table.item(self.forwarders_table.currentRow(),0).text()
        if db_manager.get_freight_forwarder_by_id(f_id) and FreightForwarderDialog(db_manager.get_freight_forwarder_by_id(f_id),self).exec_()==QDialog.Accepted: self.load_forwarders_table()
    def handle_delete_forwarder(self):
        if not self.forwarders_table.selectedItems(): return
        f_id=self.forwarders_table.item(self.forwarders_table.currentRow(),0).text()
        if QMessageBox.question(self,self.tr("Confirmer Suppression"),self.tr("Supprimer ce transitaire?"),QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes and db_manager.delete_freight_forwarder(f_id): self.load_forwarders_table()
        else: QMessageBox.warning(self,self.tr("Erreur DB"),self.tr("Impossible de supprimer."))
    def update_forwarder_button_states(self): en=bool(self.forwarders_table.selectedItems()); self.edit_forwarder_btn.setEnabled(en); self.delete_forwarder_btn.setEnabled(en)

class DocumentManager(QMainWindow):
    def __init__(self, app_root_dir, current_user_id):
        super().__init__()
        self.app_root_dir = app_root_dir
        self.current_user_id = current_user_id
        self.setWindowTitle(self.tr("Gestionnaire de Documents Client")); self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon.fromTheme("folder-documents"))
        
        self.config = CONFIG
        # Use get_setting with default, falling back to config, then to a hardcoded default.
        self.config['google_maps_review_url'] = db_manager.get_setting(
            'google_maps_review_url',
            default=self.config.get('google_maps_review_url', 'https://maps.google.com/?cid=YOUR_CID_HERE_FALLBACK_CONFIG')
        )

        self.clients_data_map = {}
        self.current_offset = 0
        self.limit_per_page = 50
        
        # Removed map_view_integrated, map_interaction_handler_integrated, and web_channel_integrated

        self.setup_ui_main()
        self.project_management_widget_instance = ProjectManagementDashboard(parent=self, current_user=None)
        self.main_area_stack.addWidget(self.project_management_widget_instance)

        self.statistics_dashboard_instance = StatisticsDashboard(parent=self)
        # Connect signals from StatisticsDashboard
        self.statistics_dashboard_instance.request_add_client_for_country.connect(self.handle_add_client_from_stats_map)
        self.statistics_dashboard_instance.request_view_client_details.connect(self.handle_view_client_from_stats_map)
        self.main_area_stack.addWidget(self.statistics_dashboard_instance)

        self.partner_management_widget_instance = PartnerMainWidget(parent=self)
        self.main_area_stack.addWidget(self.partner_management_widget_instance)

        self.main_area_stack.setCurrentWidget(self.documents_page_widget)
        self.create_actions_main(); self.create_menus_main()
        
        self.load_clients_from_db_slot() # Initial load
        # if self.stats_widget: self.stats_widget.update_stats() # self.stats_widget removed
        # self.update_integrated_map() # Method removed
        self.check_timer = QTimer(self); self.check_timer.timeout.connect(self.check_old_clients_routine_slot); self.check_timer.start(3600000)

    @pyqtSlot(str)
    def handle_add_client_from_stats_map(self, country_name_str):
        logging.info(f"Handling request to add client for country: {country_name_str} from statistics map.")
        dialog = AddNewClientDialog(initial_country_name=country_name_str, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            client_data = dialog.get_data()
            if client_data:
                # Assuming handle_create_client_execution is available and appropriate
                handle_create_client_execution(self, client_data_dict=client_data)
                # self.load_clients_from_db_slot() # Refresh client list after adding

    @pyqtSlot(str)
    def handle_view_client_from_stats_map(self, client_id_str):
        logging.info(f"Handling request to view client ID: {client_id_str} from statistics map.")
        self.main_area_stack.setCurrentWidget(self.documents_page_widget)
        self.open_client_tab_by_id(client_id_str)

    def notify(self, title, message, type='INFO', duration=5000, icon_path=None):

        """
        Convenience method to show a notification via the global NotificationManager.

        This method provides an easy way for parts of the DocumentManager (or its children,
        if they have a reference to it) to display notifications without needing to
        directly import or manage the NotificationManager.

        Args:
            title (str): The title of the notification.
            message (str): The main message content of the notification.
            type (str, optional): Type of notification ('INFO', 'SUCCESS', 'WARNING', 'ERROR').
                                  Defaults to 'INFO'.
            duration (int, optional): Duration in milliseconds before the notification auto-closes.
                                      Defaults to 5000ms.
            icon_path (str, optional): Path to a custom icon. If None, a default icon based
                                       on the 'type' will be used. Defaults to None.
        """
        from main import get_notification_manager # Local import

        manager = get_notification_manager()
        if manager: manager.show(title, message, type=type, duration=duration, icon_path=icon_path)
        else: logging.warning(f"Notification Manager not found. Notification: {title} - {message}")

    def setup_ui_main(self): 
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget); main_layout.setContentsMargins(10,10,10,10); main_layout.setSpacing(10)
        # self.stats_widget = StatisticsWidget(); main_layout.addWidget(self.stats_widget) # Removed

        self.main_area_stack = QStackedWidget(); main_layout.addWidget(self.main_area_stack)
        
        self.documents_page_widget = QWidget()
        main_splitter = QSplitter(Qt.Horizontal, self.documents_page_widget) # This splitter is for client list and client details view

        left_pane_widget = QWidget()
        left_pane_layout = QVBoxLayout(left_pane_widget)
        left_pane_layout.setContentsMargins(0,0,0,0)

        # Filter Search Group - Re-layout to QHBoxLayout
        filter_search_group = QGroupBox(self.tr("Filtres et Recherche Clients"))
        filter_search_main_layout = QHBoxLayout(filter_search_group) # Changed to QHBoxLayout

        # Status Filter
        status_filter_layout = QVBoxLayout() # Using QVBoxLayout for label on top
        status_label = QLabel(self.tr("Statut:"))
        self.status_filter_combo = QComboBox(); self.status_filter_combo.addItem(self.tr("Tous les statuts"), None)
        self.load_statuses_into_filter_combo(); self.status_filter_combo.currentIndexChanged.connect(self.filter_client_list_display_slot)
        status_filter_layout.addWidget(status_label)
        status_filter_layout.addWidget(self.status_filter_combo)
        filter_search_main_layout.addLayout(status_filter_layout)

        # Archive Filter
        archive_filter_layout = QVBoxLayout()
        archive_label = QLabel(self.tr("Filtre Archive:"))
        self.client_archive_filter_combo = QComboBox()
        self.client_archive_filter_combo.addItem(self.tr("Clients Actifs"), False)
        self.client_archive_filter_combo.addItem(self.tr("Clients Archivés (supprimés logiquement)"), True)
        self.client_archive_filter_combo.addItem(self.tr("Tout"), "all_status_types")
        self.client_archive_filter_combo.setCurrentIndex(0); self.client_archive_filter_combo.currentIndexChanged.connect(self.filter_client_list_display_slot)
        archive_filter_layout.addWidget(archive_label)
        archive_filter_layout.addWidget(self.client_archive_filter_combo)
        filter_search_main_layout.addLayout(archive_filter_layout)

        # Search Input
        search_layout = QVBoxLayout()
        search_label = QLabel(self.tr("Recherche:"))
        self.search_input_field = QLineEdit(); self.search_input_field.setPlaceholderText(self.tr("Rechercher client..."))
        self.search_input_field.textChanged.connect(self.filter_client_list_display_slot) 
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input_field)
        filter_search_main_layout.addLayout(search_layout)

        filter_search_main_layout.addStretch(1) # Add stretch to push filters to the left
        left_pane_layout.addWidget(filter_search_group)
        
        self.client_list_widget = QListWidget(); self.client_list_widget.setAlternatingRowColors(True) 
        self.client_list_widget.setItemDelegate(StatusDelegate(self.client_list_widget))
        self.client_list_widget.itemClicked.connect(self.handle_client_list_click); self.client_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.client_list_widget.customContextMenuRequested.connect(self.show_client_context_menu); left_pane_layout.addWidget(self.client_list_widget)
        
        pagination_layout = QHBoxLayout()
        self.prev_page_button = QPushButton(self.tr("Précédent")); self.prev_page_button.clicked.connect(self.prev_page)
        self.next_page_button = QPushButton(self.tr("Suivant")); self.next_page_button.clicked.connect(self.next_page)
        self.page_info_label = QLabel(self.tr("Page 1")); pagination_layout.addWidget(self.prev_page_button); pagination_layout.addWidget(self.page_info_label); pagination_layout.addWidget(self.next_page_button)
        left_pane_layout.addLayout(pagination_layout)
        
        self.add_new_client_button = QPushButton(self.tr("Ajouter un Nouveau Client")); self.add_new_client_button.setIcon(QIcon(":/icons/user-add.svg")); self.add_new_client_button.setObjectName("primaryButton"); self.add_new_client_button.clicked.connect(self.open_add_new_client_dialog); left_pane_layout.addWidget(self.add_new_client_button)

        # map_group_box removed from here
        left_pane_widget.setLayout(left_pane_layout)
        main_splitter.addWidget(left_pane_widget)

        # Right pane for client tabs (no change here, it's a QSplitter itself)
        right_pane_splitter = QSplitter(Qt.Vertical) # This was already a QSplitter, good.
        self.client_tabs_widget = QTabWidget(); self.client_tabs_widget.setTabsClosable(True); self.client_tabs_widget.tabCloseRequested.connect(self.close_client_tab)
        right_pane_splitter.addWidget(self.client_tabs_widget) # Add client tabs to the right_pane_splitter
        main_splitter.addWidget(right_pane_splitter) # Add the right_pane_splitter to the main_splitter

        main_splitter.setSizes([int(self.width()*0.35), int(self.width()*0.65)]) # Adjust as needed

        docs_page_layout = QVBoxLayout(self.documents_page_widget)
        docs_page_layout.addWidget(main_splitter)
        docs_page_layout.setContentsMargins(0,0,0,0)
        self.documents_page_widget.setLayout(docs_page_layout)

        self.main_area_stack.addWidget(self.documents_page_widget)

    def open_add_new_client_dialog(self):
        dialog = AddNewClientDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            client_data = dialog.get_data()
            if client_data: handle_create_client_execution(self, client_data_dict=client_data)

    def create_actions_main(self): 
        self.settings_action = QAction(QIcon(":/icons/modern/settings.svg"), self.tr("Paramètres"), self); self.settings_action.triggered.connect(self.open_settings_dialog)
        self.template_action = QAction(QIcon(":/icons/modern/templates.svg"), self.tr("Gérer les Modèles"), self); self.template_action.triggered.connect(self.open_template_manager_dialog)
        self.status_action = QAction(QIcon(":/icons/check-square.svg"), self.tr("Gérer les Statuts"), self); self.status_action.triggered.connect(self.open_status_manager_dialog); self.status_action.setEnabled(False); self.status_action.setToolTip(self.tr("Fonctionnalité de gestion des statuts prévue pour une future version."))
        self.exit_action = QAction(QIcon(":/icons/log-out.svg"), self.tr("Quitter"), self); self.exit_action.setShortcut("Ctrl+Q"); self.exit_action.triggered.connect(self.close)
        self.project_management_action = QAction(QIcon(":/icons/modern/dashboard.svg"), self.tr("Gestion de Projet"), self); self.project_management_action.triggered.connect(self.show_project_management_view)
        self.documents_view_action = QAction(QIcon(":/icons/modern/folder-docs.svg"), self.tr("Gestion Documents"), self); self.documents_view_action.triggered.connect(self.show_documents_view)
        self.product_equivalency_action = QAction(QIcon.fromTheme("document-properties", QIcon(":/icons/modern/link.svg")), self.tr("Gérer Équivalences Produits"), self); self.product_equivalency_action.triggered.connect(self.open_product_equivalency_dialog)
        self.product_list_action = QAction(QIcon(":/icons/book.svg"), self.tr("Product List"), self); self.product_list_action.triggered.connect(self.open_product_list_placeholder)
        self.partner_management_action = QAction(QIcon(":/icons/team.svg"), self.tr("Partner Management"), self); self.partner_management_action.triggered.connect(self.show_partner_management_view)
        self.statistics_action = QAction(QIcon(":/icons/bar-chart.svg"), self.tr("Statistiques"), self); self.statistics_action.triggered.connect(self.show_statistics_view)

    def create_menus_main(self): 
        menu_bar = self.menuBar(); file_menu = menu_bar.addMenu(self.tr("Fichier")); file_menu.addAction(self.settings_action); file_menu.addAction(self.template_action); file_menu.addAction(self.status_action); file_menu.addAction(self.product_equivalency_action); file_menu.addSeparator(); file_menu.addAction(self.exit_action)
        modules_menu = menu_bar.addMenu(self.tr("Modules")); modules_menu.addAction(self.documents_view_action); modules_menu.addAction(self.project_management_action); modules_menu.addAction(self.product_list_action); modules_menu.addAction(self.partner_management_action); modules_menu.addAction(self.statistics_action)
        help_menu = menu_bar.addMenu(self.tr("Aide")); about_action = QAction(QIcon(":/icons/help-circle.svg"), self.tr("À propos"), self); about_action.triggered.connect(self.show_about_dialog); help_menu.addAction(about_action)

    def show_project_management_view(self): self.main_area_stack.setCurrentWidget(self.project_management_widget_instance)
    def show_documents_view(self): self.main_area_stack.setCurrentWidget(self.documents_page_widget)
    def show_partner_management_view(self): self.main_area_stack.setCurrentWidget(self.partner_management_widget_instance)
    def show_statistics_view(self): self.main_area_stack.setCurrentWidget(self.statistics_dashboard_instance)
    def show_about_dialog(self): QMessageBox.about(self, self.tr("À propos"), self.tr("<b>Gestionnaire de Documents Client</b><br><br>Version 4.0<br>Application de gestion de documents clients avec templates Excel.<br><br>Développé par Saadiya Management (Concept)"))
        
    def execute_create_client_slot(self, client_data_dict=None):
        handle_create_client_execution(self, client_data_dict=client_data_dict)
        self.load_clients_from_db_slot()

    def load_clients_from_db_slot(self):
        status_id_filter = self.status_filter_combo.currentData()
        archive_filter_data = self.client_archive_filter_combo.currentData()
        include_deleted_filter = False
        if archive_filter_data == "all_status_types": include_deleted_filter = True
        elif isinstance(archive_filter_data, bool): include_deleted_filter = archive_filter_data
        filters_for_crud = {};
        if status_id_filter is not None: filters_for_crud['status_id'] = status_id_filter
        load_and_display_clients(self, filters=filters_for_crud, limit=self.limit_per_page, offset=self.current_offset, include_deleted=include_deleted_filter)
        self.update_pagination_controls()
        filter_and_display_clients(self)

    def filter_client_list_display_slot(self):
        self.current_offset = 0
        self.load_clients_from_db_slot()

    def update_pagination_controls(self):
        self.prev_page_button.setEnabled(self.current_offset > 0)
        # A more robust check for 'next' would involve total count if available
        # For now, assume if fewer items than limit_per_page loaded into client_list_widget, it's the last page.
        # This depends on load_and_display_clients correctly filling self.clients_data_map for the current page
        # and filter_and_display_clients then rendering it to client_list_widget.
        # A simple heuristic:
        is_last_page_heuristic = self.client_list_widget.count() < self.limit_per_page
        self.next_page_button.setEnabled(not is_last_page_heuristic)
        self.page_info_label.setText(self.tr("Page {0}").format((self.current_offset // self.limit_per_page) + 1))

    def prev_page(self):
        if self.current_offset > 0:
            self.current_offset -= self.limit_per_page
            self.load_clients_from_db_slot()

    def next_page(self):
        # Only advance if we think there might be more items.
        # This heuristic relies on the list widget count after filtering.
        # If the list widget has a full page, there *might* be more.
        if self.client_list_widget.count() == self.limit_per_page:
            self.current_offset += self.limit_per_page
            self.load_clients_from_db_slot()
        else:
             # If current view has less than limit_per_page, likely no more pages.
             self.next_page_button.setEnabled(False)


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
            client_statuses = db_manager.get_all_status_settings(type_filter='Client')
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
            client_data_from_db = clients_crud_instance.get_client_by_id(client_id_to_open, include_deleted=False)
            if not client_data_from_db:
                QMessageBox.warning(self, self.tr("Erreur"), self.tr("Données client non trouvées ou client archivé (ID: {0}).").format(client_id_to_open))
                return
            client_data_to_show = client_data_from_db

        if 'country' not in client_data_to_show and client_data_to_show.get('country_id'):
            country_obj = db_manager.get_country_by_id(client_data_to_show['country_id'])
            client_data_to_show['country'] = country_obj.get('country_name', "N/A") if country_obj else "N/A"
        if 'city' not in client_data_to_show and client_data_to_show.get('city_id'):
            city_obj = db_manager.get_city_by_id(client_data_to_show['city_id'])
            client_data_to_show['city'] = city_obj.get('city_name', "N/A") if city_obj else "N/A"
        if 'status' not in client_data_to_show and client_data_to_show.get('status_id'):
            status_obj = db_manager.get_status_setting_by_id(client_data_to_show['status_id'])
            client_data_to_show['status'] = status_obj.get('status_name', "N/A") if status_obj else "N/A"

        # Ensure selected_languages is a list, even if it's null/empty from DB
        selected_languages_str = client_data_to_show.get('selected_languages')
        if isinstance(selected_languages_str, str) and selected_languages_str.strip():
            client_data_to_show['selected_languages'] = [lang.strip() for lang in selected_languages_str.split(',') if lang.strip()]
        elif not isinstance(client_data_to_show.get('selected_languages'), list): # If it's not a list already (e.g. None or empty string from .get())
            client_data_to_show['selected_languages'] = []


        for i in range(self.client_tabs_widget.count()):
            tab_widget_ref = self.client_tabs_widget.widget(i) 
            if hasattr(tab_widget_ref, 'client_info') and tab_widget_ref.client_info["client_id"] == client_id_to_open:
                self.client_tabs_widget.setCurrentIndex(i)
                if hasattr(tab_widget_ref, 'refresh_display'):
                    tab_widget_ref.refresh_display(client_data_to_show)
                return

        notification_manager = QApplication.instance().notification_manager
        client_detail_widget = ClientWidget(client_data_to_show, self.config, self.app_root_dir, notification_manager, parent=self)
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
            self.notify(title=self.tr("Accès Dossier Échoué"),
                        message=self.tr("Chemin du dossier non trouvé pour le client '{0}'.").format(client_info.get('client_name', 'N/A') if client_info else 'N/A'),
                        type='WARNING')
            
    def open_settings_dialog(self): 
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            new_conf = dialog.get_config() 
            google_maps_url_from_dialog = new_conf.get("google_maps_review_url")
            if google_maps_url_from_dialog is not None:
                db_manager.set_setting('google_maps_review_url', google_maps_url_from_dialog)
                self.config['google_maps_review_url'] = google_maps_url_from_dialog
            self.config.update(new_conf); save_config(self.config)
            new_language_code = self.config.get('language')
            if new_language_code:
                try: db_manager.set_setting('user_selected_language', new_language_code)
                except Exception as e: logging.error(f"Error saving language preference: {e}", exc_info=True); self.notify(title=self.tr("Erreur Sauvegarde Langue"),message=self.tr("Impossible d'enregistrer la préférence linguistique."),type='ERROR')
            os.makedirs(self.config["templates_dir"], exist_ok=True); os.makedirs(self.config["clients_dir"], exist_ok=True)
            self.notify(title=self.tr("Paramètres Sauvegardés"), message=self.tr("Les nouveaux paramètres ont été enregistrés."), type='SUCCESS')
            
    def open_template_manager_dialog(self): TemplateDialog(self.config, self).exec_()
    def open_status_manager_dialog(self): QMessageBox.information(self, self.tr("Gestion des Statuts"), self.tr("Fonctionnalité à implémenter."))
    def open_product_equivalency_dialog(self): ProductEquivalencyDialog(self).exec_()
    def open_product_list_placeholder(self): ProductListDialog(self).exec_()
    def closeEvent(self, event): save_config(self.config); super().closeEvent(event)

    # process_client_map_selection and prepare_new_client_for_country removed as they were for the integrated map.
    # update_integrated_map method also removed.

    def load_countries_into_combo(self):
        if hasattr(self,'country_select_combo'): self.country_select_combo.clear(); # ... (rest of method unchanged) # This combo is part of AddNewClientDialog now.
    def load_cities_for_country(self, country_name_str):
        if hasattr(self,'city_select_combo'): self.city_select_combo.clear(); # ... (rest of method unchanged)
    def add_new_country_dialog(self): # ... (unchanged)
        pass
    def add_new_city_dialog(self): # ... (unchanged)
        pass
