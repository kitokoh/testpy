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
    QTextEdit, QSplitter # Added QTextEdit for SettingsDialog notes, QSplitter for layout
)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont
from PyQt5.QtCore import Qt, QUrl, QTimer, pyqtSlot
from PyQt5.QtWebEngineWidgets import QWebEngineView # For integrated map
from PyQt5.QtCore import Qt, QUrl, QTimer, pyqtSlot
from PyQt5.QtWebChannel import QWebChannel

import db as db_manager
import icons_rc
import folium # For map generation
from statistics_module import MapInteractionHandler # For map interaction
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
    SettingsDialog as OriginalSettingsDialog, TemplateDialog, AddNewClientDialog, # EditClientDialog is called from logic
    ProductEquivalencyDialog, # Added for product equivalency
    ManageProductMasterDialog ,# Added for global product management
    TransporterDialog,
    FreightForwarderDialog
)
from product_list_dialog import ProductListDialog # Import the new dialog

# Dialogs directly instantiated by DocumentManager
from client_widget import ClientWidget # For client tabs
from projectManagement import MainDashboard as ProjectManagementDashboard

from client_widget import ClientWidget
from projectManagement import MainDashboard as ProjectManagementDashboard
from statistics_module import StatisticsDashboard # Will be refactored/removed later
from statistics_panel import CollapsibleStatisticsWidget # Import the new widget

from utils import save_config
from company_management import CompanyTabWidget
from partners.partner_main_widget import PartnerMainWidget # Partner Management
# from main import get_notification_manager # For notifications - Removed global import


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
        # db_google_maps_url = db_manager.get_setting('google_maps_review_url')
        db_google_maps_url = "https://maps.google.com/?cid=YOUR_CID_HERE" 
        if db_google_maps_url is not None:
            self.config['google_maps_review_url'] = db_google_maps_url
        elif 'google_maps_review_url' not in self.config:
            self.config['google_maps_review_url'] = 'https://maps.google.com/?cid=YOUR_CID_HERE'

        self.clients_data_map = {}
        
        # Integrated map components
        self.map_view_integrated = QWebEngineView()
        self.map_interaction_handler_integrated = MapInteractionHandler(self) # MapInteractionHandler might need new signal
        self.map_interaction_handler_integrated.country_clicked_signal.connect(self.prepare_new_client_for_country)
        self.map_interaction_handler_integrated.client_clicked_on_map_signal.connect(self.process_client_map_selection) # Changed to new method
        self.web_channel_integrated = QWebChannel(self.map_view_integrated.page())
        self.map_view_integrated.page().setWebChannel(self.web_channel_integrated)
        self.web_channel_integrated.registerObject("pyMapConnector", self.map_interaction_handler_integrated)

        self.setup_ui_main()

        self.project_management_widget_instance = ProjectManagementDashboard(parent=self, current_user=None)
        self.main_area_stack.addWidget(self.project_management_widget_instance)

        # StatisticsDashboard might still be used for non-map stats, or its contents moved.
        self.statistics_dashboard_instance = StatisticsDashboard(parent=self)
        self.main_area_stack.addWidget(self.statistics_dashboard_instance)

        self.partner_management_widget_instance = PartnerMainWidget(parent=self)
        self.main_area_stack.addWidget(self.partner_management_widget_instance)

        self.main_area_stack.setCurrentWidget(self.documents_page_widget)

        self.create_actions_main()
        self.create_menus_main()

        # The old connection from statistics_dashboard_instance is no longer needed here
        # as the map is now integrated directly. The new connection is above.
        
        load_and_display_clients(self)
        if self.stats_widget: # This is the top global stats widget, not the new placeholder
            self.stats_widget.update_stats()
        
        self.update_integrated_map() # Initial map load

        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_old_clients_routine_slot)
        self.check_timer.start(3600000)

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
        from main import get_notification_manager # For notifications - Moved import here
        manager = get_notification_manager()
        if manager:
            manager.show(title, message, type=type, duration=duration, icon_path=icon_path)
        else:
            # Fallback or log an error if manager is not found
            logging.warning(f"Notification Manager not found. Notification: {title} - {message}")
            # As a basic fallback, show a QMessageBox - though this is modal and not ideal for notifications
            # QMessageBox.information(self, title, message) # Consider if this fallback is desired

    def setup_ui_main(self): 
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget); main_layout.setContentsMargins(10,10,10,10); main_layout.setSpacing(10)
        
        self.stats_widget = StatisticsWidget(); main_layout.addWidget(self.stats_widget)

        self.main_area_stack = QStackedWidget()
        main_layout.addWidget(self.main_area_stack)

        self.documents_page_widget = QWidget()
        # Use QSplitter for the main layout of documents_page_widget
        main_splitter = QSplitter(Qt.Horizontal, self.documents_page_widget)

        # Left Pane: Client List and Map
        left_pane_widget = QWidget()
        left_pane_layout = QVBoxLayout(left_pane_widget)
        left_pane_layout.setContentsMargins(0,0,0,0) # No margins for the splitter pane's direct child

        # Client search and filter bar
        filter_search_group = QGroupBox(self.tr("Filtres et Recherche Clients"))
        filter_search_layout = QFormLayout(filter_search_group) # Using QFormLayout for better alignment
        
        self.status_filter_combo = QComboBox(); self.status_filter_combo.addItem(self.tr("Tous les statuts"))
        self.load_statuses_into_filter_combo() 
        self.status_filter_combo.currentIndexChanged.connect(self.filter_client_list_display_slot) 
        filter_search_layout.addRow(self.tr("Statut:"), self.status_filter_combo)

        self.client_archive_filter_combo = QComboBox()
        self.client_archive_filter_combo.addItem(self.tr("Actifs (et sans statut)"), "active_including_null")
        self.client_archive_filter_combo.addItem(self.tr("Actifs (avec statut)"), "active_only_with_status")
        self.client_archive_filter_combo.addItem(self.tr("Archivés"), "archived_only")
        self.client_archive_filter_combo.addItem(self.tr("Tout"), "all")
        self.client_archive_filter_combo.setCurrentIndex(0)
        self.client_archive_filter_combo.currentIndexChanged.connect(self.filter_client_list_display_slot)
        filter_search_layout.addRow(self.tr("Archive:"), self.client_archive_filter_combo)

        self.search_input_field = QLineEdit(); self.search_input_field.setPlaceholderText(self.tr("Rechercher client..."))
        self.search_input_field.textChanged.connect(self.filter_client_list_display_slot) 
        filter_search_layout.addRow(self.tr("Recherche:"), self.search_input_field)
        left_pane_layout.addWidget(filter_search_group)
        
        self.client_list_widget = QListWidget(); self.client_list_widget.setAlternatingRowColors(True) 
        self.client_list_widget.setItemDelegate(StatusDelegate(self.client_list_widget))
        self.client_list_widget.itemClicked.connect(self.handle_client_list_click) 
        self.client_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.client_list_widget.customContextMenuRequested.connect(self.show_client_context_menu)
        left_pane_layout.addWidget(self.client_list_widget) # Client list takes remaining space above map
        
        # Add New Client Button (remains under the list)
        self.add_new_client_button = QPushButton(self.tr("Ajouter un Nouveau Client"))
        self.add_new_client_button.setIcon(QIcon(":/icons/modern/user-add.svg"))
        self.add_new_client_button.setObjectName("primaryButton")
        self.add_new_client_button.clicked.connect(self.open_add_new_client_dialog)
        left_pane_layout.addWidget(self.add_new_client_button)

        # Integrated Map View
        map_group_box = QGroupBox(self.tr("Carte des Présences Client"))
        map_layout = QVBoxLayout(map_group_box)
        map_layout.addWidget(self.map_view_integrated)
        map_group_box.setMinimumHeight(200) # Ensure map has some initial height
        left_pane_layout.addWidget(map_group_box, 1) # Map takes space below list, with stretch factor 1

        left_pane_widget.setLayout(left_pane_layout)
        main_splitter.addWidget(left_pane_widget)

        # Right Pane: Client Tabs and Statistics Placeholder
        right_pane_splitter = QSplitter(Qt.Vertical)
        
        self.client_tabs_widget = QTabWidget(); self.client_tabs_widget.setTabsClosable(True) 
        self.client_tabs_widget.tabCloseRequested.connect(self.close_client_tab) 
        right_pane_splitter.addWidget(self.client_tabs_widget)

        # Replace placeholder with CollapsibleStatisticsWidget
        # self.collapsible_stats_widget = CollapsibleStatisticsWidget(self)
        # right_pane_splitter.addWidget(self.collapsible_stats_widget)

        # right_pane_splitter.setSizes([int(self.height() * 0.7), int(self.height() * 0.3)]) # Initial sizes for tabs/stats
        # With only one widget, setSizes might not be necessary or could be adjusted.
        # For now, let's remove it. The splitter should give all space to the single widget.

        main_splitter.addWidget(right_pane_splitter)
        main_splitter.setSizes([int(self.width() * 0.35), int(self.width() * 0.65)]) # Initial sizes for left/right panes

        # The main_documents_page_widget needs a layout to contain the main_splitter
        documents_page_main_layout = QVBoxLayout(self.documents_page_widget)
        documents_page_main_layout.addWidget(main_splitter)
        documents_page_main_layout.setContentsMargins(0,0,0,0) # No margins for the splitter to take full space
        self.documents_page_widget.setLayout(documents_page_main_layout)

        self.main_area_stack.addWidget(self.documents_page_widget)
        
        # Remove the old form_group_box and its related widgets as they are replaced by AddNewClientDialog
        if hasattr(self, 'form_group_box'):
            self.form_group_box.deleteLater()
            del self.form_group_box
        if hasattr(self, 'form_container_widget'): # And its container
             self.form_container_widget.deleteLater()
             del self.form_container_widget
        # And individual input fields if they were direct members of self
        # For example: self.client_name_input.deleteLater() etc.
        # However, they were part of form_container_widget, so they should be deleted with it.

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
        
        # self.statistics_action = QAction(QIcon(":/icons/bar-chart.svg"), self.tr("Statistiques Détaillées"), self)
        # # self.statistics_action.triggered.connect(self.show_statistics_view) # Old connection
        # self.statistics_action.triggered.connect(self.toggle_collapsible_statistics_panel) # New connection

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
        # modules_menu.addAction(self.statistics_action)
        modules_menu.addAction(self.product_list_action) # Add new action here
        modules_menu.addAction(self.partner_management_action) # Add Partner Management action
        help_menu = menu_bar.addMenu(self.tr("Aide"))
        about_action = QAction(QIcon(":/icons/help-circle.svg"), self.tr("À propos"), self); about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_project_management_view(self):
        self.main_area_stack.setCurrentWidget(self.project_management_widget_instance)

    def show_documents_view(self):
        self.main_area_stack.setCurrentWidget(self.documents_page_widget)

    # def toggle_collapsible_statistics_panel(self):
    #     if hasattr(self, 'collapsible_stats_widget'):
    #         # Ensure the documents page is visible first, as the stats panel is part of it
    #         self.show_documents_view()
    #
    #         # Toggle the button's checked state which in turn calls show_and_expand or hides
    #         current_state = self.collapsible_stats_widget.toggle_button.isChecked()
    #         self.collapsible_stats_widget.toggle_button.setChecked(not current_state)
    #         # If we want to ensure it always expands when menu is clicked:
    #         # self.collapsible_stats_widget.show_and_expand()
    #     else:
    #         QMessageBox.warning(self, self.tr("Erreur"), self.tr("Le panneau de statistiques n'est pas initialisé."))
        
    # def show_statistics_view(self):
    #     # This method might become obsolete or repurposed.
    #     # For now, ensure it doesn't try to show the old StatisticsDashboard in the stack
    #     # if that instance is being dismantled.
    #     # Option 1: Do nothing / Log deprecation
    #     # print("show_statistics_view is being phased out. Use toggle_collapsible_statistics_panel.")
    #     # Option 2: Redirect to the new toggle functionality
    #     self.toggle_collapsible_statistics_panel()
    #     # Option 3: If StatisticsDashboard still holds other views for a dedicated page, keep:
    #     # self.main_area_stack.setCurrentWidget(self.statistics_dashboard_instance)


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

            self.config.update(new_conf)
            save_config(self.config)

            new_language_code = self.config.get('language')
            if new_language_code:
                try:
                    db_manager.set_setting('user_selected_language', new_language_code)
                    logging.info(f"User language preference '{new_language_code}' saved to database.")
                except Exception as e:
                    logging.error(f"Error saving language preference to database: {e}", exc_info=True)
                    self.notify(title=self.tr("Erreur Sauvegarde Langue"),
                                message=self.tr("Impossible d'enregistrer la préférence linguistique."),
                                type='ERROR')
                    # QMessageBox.warning(self, self.tr("Erreur Base de Données"), self.tr("Impossible d'enregistrer la préférence linguistique dans la base de données : {0}").format(str(e)))


            os.makedirs(self.config["templates_dir"], exist_ok=True) 
            os.makedirs(self.config["clients_dir"], exist_ok=True)
            # QMessageBox.information(self, self.tr("Paramètres Sauvegardés"), self.tr("Nouveaux paramètres enregistrés."))
            self.notify(title=self.tr("Paramètres Sauvegardés"),
                        message=self.tr("Les nouveaux paramètres de l'application ont été enregistrés avec succès."),
                        type='SUCCESS')
            
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

    def process_client_map_selection(self, client_id, client_name):
        """Handles client selection from the integrated map."""
        print(f"[DocumentManager] Processing map selection for client: ID={client_id}, Name={client_name}")
        if hasattr(self, 'collapsible_stats_widget'):
            self.collapsible_stats_widget.collapse_panel()
        self.open_client_tab_by_id(client_id)

    def update_integrated_map(self):
        try:
            clients_by_country_counts = db_manager.get_client_counts_by_country()
            if clients_by_country_counts is None: clients_by_country_counts = []

            active_clients_map = db_manager.get_active_clients_per_country() # Fetch active clients

            data_for_map = {"country_name": [], "client_count": []}
            for entry in clients_by_country_counts:
                data_for_map["country_name"].append(entry["country_name"])
                data_for_map["client_count"].append(entry["client_count"])

            geojson_path = os.path.join(self.app_root_dir, "assets", "world_countries.geojson")
            if not os.path.exists(geojson_path):
                logging.error(f"GeoJSON file not found at {geojson_path}")
                m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodb positron")
                self.map_view_integrated.setHtml(m.get_root().render())
                return

            m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodb positron")

            if data_for_map["country_name"]:
                import pandas as pd # Local import for this method
                country_data_df = pd.DataFrame(data_for_map)

                choropleth = folium.Choropleth(
                    geo_data=geojson_path,
                    name="choropleth",
                    data=country_data_df,
                    columns=["country_name", "client_count"],
                    key_on="feature.properties.name",
                    fill_color="YlGnBu",
                    fill_opacity=0.7,
                    line_opacity=0.2,
                    legend_name=self.tr("Nombre de Clients par Pays"),
                    highlight=True,
                ).add_to(m)
                # Simplified tooltip for choropleth layer itself, detailed info in GeoJson popups
                folium.features.GeoJsonTooltip(fields=['name'], aliases=['Pays:'], localize=True).add_to(choropleth.geojson)


            # Layer for popups with client lists
            popup_layer = folium.GeoJson(
                geojson_path,
                name=self.tr("Informations Clients"),
                style_function=lambda x: {'fillColor': 'transparent', 'color': 'transparent', 'weight': 0},
                tooltip=None # Disable default tooltip for this layer to avoid overlap
            )

            for feature in popup_layer.data.get('features', []):
                country_name = feature.get('properties', {}).get('name')
                if not country_name: continue

                total_clients_in_country = 0
                for entry in clients_by_country_counts:
                    if entry['country_name'] == country_name:
                        total_clients_in_country = entry['client_count']
                        break

                active_clients_in_country = active_clients_map.get(country_name, [])

                popup_html = f"<b>{country_name}</b><br>{self.tr('Clients (Total)')}: {total_clients_in_country}<br>"

                if active_clients_in_country:
                    popup_html += f"<br><b>{self.tr('Clients Actifs')}:</b><ul>"
                    for client in active_clients_in_country:
                        # Basic JS escaping for client name
                        js_safe_client_name = client['client_name'].replace("'", "\\'").replace('"', '\\"')
                        popup_html += f"<li><a href='#' onclick='onClientClick(\"{client['client_id']}\", \"{js_safe_client_name}\")'>{client['client_name']}</a></li>"
                    popup_html += "</ul>"

            country_name_js_escaped = country_name.replace("'", "\\'")
            js_onclick_call = f'onCountryFeatureClick("{country_name_js_escaped}")'
            button_text = self.tr('Ajouter Client Ici')
            popup_html += f"<br><button onclick='{js_onclick_call}'>{button_text}</button>"
            feature['properties']['popup_content'] = popup_html

            # Add popups using the 'popup_content' property
            popup_layer.add_child(folium.features.GeoJsonPopup(fields=['popup_content']))
            popup_layer.add_to(m)

            if data_for_map["country_name"]: # Only add LayerControl if choropleth was added
                 folium.LayerControl().add_to(m)

            # JavaScript for interaction
            js_script = f"""
            <script>
            var pyMapConnectorInstance = null;
            function initializeQWebChannel() {{
                if (typeof QWebChannel !== 'undefined') {{
                    new QWebChannel(qt.webChannelTransport, function(channel) {{
                        pyMapConnectorInstance = channel.objects.pyMapConnector;
                        if(pyMapConnectorInstance) {{ console.log("pyMapConnector bound successfully."); }}
                        else {{ console.error("Failed to bind pyMapConnector."); }}
                    }});
                }} else {{ console.error("QWebChannel.js not loaded."); }}
            }}

            // Call initialization function after document is loaded
            if (document.readyState === 'complete' || document.readyState === 'interactive') {{
                 setTimeout(initializeQWebChannel, 0); // Use timeout to ensure page elements are ready
            }} else {{
                 document.addEventListener('DOMContentLoaded', initializeQWebChannel);
            }}

            function onCountryFeatureClick(countryName) {{
                if (pyMapConnectorInstance) {{
                    pyMapConnectorInstance.countryClicked(countryName);
                }} else {{
                    console.error("pyMapConnectorInstance not available for country click.");
                }}
            }}
            function onClientClick(clientId, clientName) {{
                if (pyMapConnectorInstance) {{
                    console.log("JS: onClientClick called with Client ID: " + clientId + ", Name: " + clientName);
                    pyMapConnectorInstance.clientClickedOnMap(clientId, clientName);
                }} else {{
                    console.error("JS: pyMapConnectorInstance is not available for client click.");
                }}
            }}
            </script>
            """
            html_map = m.get_root().render() + js_script
            self.map_view_integrated.setHtml(html_map)
            logging.info("Integrated presence map updated with client lists.")

        except Exception as e:
            logging.error(f"Error updating integrated presence map: {e}", exc_info=True)
            # Fallback: display a simple map or error message in map_view_integrated
            error_map = folium.Map(location=[0,0], zoom_start=1)
            folium.Marker([0,0], popup=f"Error loading map: {e}").add_to(error_map)
            self.map_view_integrated.setHtml(error_map.get_root().render())


    @pyqtSlot(str)
    def prepare_new_client_for_country(self, country_name_str):
        print(f"[MainWindow] prepare_new_client_for_country called for: {country_name_str}")
        # self.show_documents_view() # Already on documents view
        dialog = AddNewClientDialog(initial_country_name=country_name_str, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            client_data = dialog.get_data()
            if client_data:
                # The dialog now handles country/city IDs, so client_data should be ready
                handle_create_client_execution(self, client_data_dict=client_data)
            else:
                QMessageBox.warning(self, self.tr("Données Incomplètes"),
                                    self.tr("Le dialogue a été accepté mais n'a pas renvoyé de données client valides."))
        else:
            print(f"Client creation cancelled for country: {country_name_str}")

    def load_countries_into_combo(self):
        # This method might still be used by the old form_group_box or other parts,
        # so it's kept unless confirmed otherwise.
        # If AddNewClientDialog is the ONLY place needing countries, this could be moved/removed.
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
