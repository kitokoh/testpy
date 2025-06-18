# -*- coding: utf-8 -*-
import sys
import os
# import logging # logging is already imported
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
from PyQt5.QtCore import Qt, QUrl, QTimer, pyqtSlot, QByteArray # Added QByteArray
# QWebEngineView might still be used by ClientWidget or other parts, so keep for now unless confirmed unused.
from PyQt5.QtWebEngineWidgets import QWebEngineView
# from PyQt5.QtWebChannel import QWebChannel # QWebChannel removed as DocumentManager no longer uses its own map.

import db as db_manager
from db.cruds.clients_crud import clients_crud_instance
from db.cruds.products_crud import products_crud_instance

import icons_rc
# import folium # No longer used directly by DocumentManager for its own map
# from statistics_module import MapInteractionHandler # DocumentManager no longer has its own map handler instance
from app_setup import APP_ROOT_DIR, CONFIG
# from ui_components import StatisticsWidget # StatisticsWidget removed from main_layout
from ui_components import StatusDelegate # Still used for QListWidget
from map_client_dialog import MapClientDialog # Added for new client from map
# The get_country_by_name, get_or_add_country, etc. specific imports for handle_add_client_from_stats_map might become obsolete.
from db import get_country_by_name, get_or_add_country, get_city_by_name_and_country_id, get_or_add_city

from dialogs.statistics_add_client_dialog import StatisticsAddClientDialog # Import the new dialog

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
    TemplateDialog, AddNewClientDialog, ManageProductMasterDialog
)
# Removed: SettingsDialog as OriginalSettingsDialog, TransporterDialog, FreightForwarderDialog
# from product_management.list_dialog import ProductListDialog # Removed
from product_management.page import ProductManagementPage # Added


from client_widget import ClientWidget
from project_management import MainDashboard as ProjectManagementDashboard
from statistics_module import StatisticsDashboard
from statistics_panel import CollapsibleStatisticsWidget

from utils import save_config
from company_management import CompanyTabWidget
from settings_page import SettingsPage # Import the new SettingsPage
from botpress_integration.ui_components import BotpressIntegrationUI # Import Botpress UI
from dialogs.carrier_map_dialog import CarrierMapDialog # Import CarrierMapDialog

from partners.partner_main_widget import PartnerMainWidget # Partner Management
from inventory_browser_widget import InventoryBrowserWidget # Inventory Management


from download_monitor_service import DownloadMonitorService
from dialogs.assign_document_dialog import AssignDocumentToClientDialog
from db.cruds.client_documents_crud import add_client_document # For assign dialog
import os # For path checks in download monitor init


class DocumentManager(QMainWindow):
    def __init__(self, app_root_dir, current_user_id):
        super().__init__()
        self.app_root_dir = app_root_dir
        self.current_user_id = current_user_id
        self.setWindowTitle(self.tr("Gestionnaire de Documents Client")); self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon.fromTheme("folder-documents"))
        
        self.config = CONFIG
        self.download_monitor_service = None # Initialize download monitor service

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

        self.product_management_page_instance = ProductManagementPage(parent=self)
        self.main_area_stack.addWidget(self.product_management_page_instance)

        # Instantiate SettingsPage and add to stack
        self.settings_page_instance = SettingsPage(
            main_config=self.config,
            app_root_dir=self.app_root_dir,
            current_user_id=self.current_user_id,
            parent=self
        )
        self.main_area_stack.addWidget(self.settings_page_instance)

        # Instantiate BotpressIntegrationUI and add to stack
        self.botpress_integration_ui_instance = BotpressIntegrationUI(parent=self, current_user_id=self.current_user_id)
        self.main_area_stack.addWidget(self.botpress_integration_ui_instance)

        # Instantiate InventoryBrowserWidget and add to stack
        self.inventory_browser_widget_instance = InventoryBrowserWidget(parent=self)
        self.main_area_stack.addWidget(self.inventory_browser_widget_instance)

        self.main_area_stack.setCurrentWidget(self.documents_page_widget)
        self.create_actions_main(); self.create_menus_main()
        
        self.load_clients_from_db_slot() # Initial load
        # if self.stats_widget: self.stats_widget.update_stats() # self.stats_widget removed
        # self.update_integrated_map() # Method removed
        self.check_timer = QTimer(self); self.check_timer.timeout.connect(self.check_old_clients_routine_slot); self.check_timer.start(3600000)
        self.init_or_update_download_monitor() # Initialize or update based on config

    def init_or_update_download_monitor(self): # Note: This method is already defined from the previous step, ensure this is an addition of new methods below it.
        if self.download_monitor_service is not None:
            logging.info("Stopping existing download monitor service...")
            self.download_monitor_service.stop()
            self.download_monitor_service = None
            logging.info("Existing download monitor service stopped.")

        enabled = self.config.get('download_monitor_enabled', False)
        monitor_path = self.config.get('download_monitor_path')

        if enabled and monitor_path and os.path.isdir(monitor_path):
            try:
                logging.info(f"Initializing download monitor for path: {monitor_path}")
                self.download_monitor_service = DownloadMonitorService(monitor_path)
                self.download_monitor_service.new_document_detected.connect(self.handle_new_document_detected)
                self.download_monitor_service.start()
                self.notify(self.tr("Download Monitoring"),
                            self.tr("Service started for folder: {0}").format(monitor_path),
                            type='INFO')
                logging.info(f"Download monitor service started for path: {monitor_path}")
            except Exception as e:
                logging.error(f"Failed to start download monitor service: {e}", exc_info=True)
                self.notify(self.tr("Download Monitoring Error"),
                            self.tr("Failed to start service: {0}").format(str(e)),
                            type='ERROR')
                if self.download_monitor_service: # ensure it's cleaned up if partially initialized
                    self.download_monitor_service.stop()
                    self.download_monitor_service = None
        elif enabled and (not monitor_path or not os.path.isdir(monitor_path)):
            logging.error(f"Download monitor enabled but path is invalid or not set: '{monitor_path}'")
            self.notify(self.tr("Download Monitoring Error"),
                        self.tr("Download monitor path is invalid or not set. Please check settings."),
                        type='ERROR')
        elif not enabled:
            logging.info("Download monitor is disabled in configuration.")
            # self.notify(self.tr("Download Monitoring"), self.tr("Service is disabled."), type='INFO') # Optional: notify if disabled

    @pyqtSlot(str)
    def handle_new_document_detected(self, file_path):
        logging.info(f"Main_window: New document detected by service: {file_path}")
        try:
            # Ensure clients_crud_instance and add_client_document are correctly referenced
            # clients_crud_instance is self.clients_crud_instance if available, or imported directly
            # add_client_document is imported directly
            dialog = AssignDocumentToClientDialog(
                file_path=file_path,
                current_user_id=self.current_user_id,
                clients_crud=clients_crud_instance,
                client_docs_crud_add_func=add_client_document, # Using the directly imported function
                parent=self
            )
            dialog.document_assigned.connect(self.handle_document_assigned_to_client)
            if dialog.exec_() == QDialog.Accepted:
                logging.info(f"Document assignment dialog accepted for {file_path}.")
            else:
                logging.info(f"Document assignment dialog cancelled for {file_path}.")
                # If cancelled, the file remains in the downloads folder.
                # Consider if any cleanup or notification is needed for the original file.
                # For now, leaving it as is.
        except Exception as e:
            logging.error(f"Error during handling of new document {file_path}: {e}", exc_info=True)
            self.notify(self.tr("Error Assigning Document"),
                        self.tr("An error occurred while trying to assign {0}: {1}").format(os.path.basename(file_path), str(e)),
                        type='ERROR')

    @pyqtSlot(str, str)
    def handle_document_assigned_to_client(self, client_id, new_document_id):
        logging.info(f"Main_window: Document {new_document_id} assigned to client {client_id}.")
        self.notify(self.tr("Document Assigned"),
                    self.tr("New document successfully assigned to client ID: {0} (Doc ID: {1})").format(client_id, new_document_id),
                    type='SUCCESS')

        # UI Refresh Logic
        try:
            for i in range(self.client_tabs_widget.count()):
                tab_widget_ref = self.client_tabs_widget.widget(i)
                if hasattr(tab_widget_ref, 'client_info') and \
                   tab_widget_ref.client_info.get("client_id") == client_id and \
                   hasattr(tab_widget_ref, 'refresh_documents_list'):
                    logging.info(f"Refreshing documents list for open tab of client {client_id}")
                    tab_widget_ref.refresh_documents_list() # Assuming this method exists on ClientWidget
                    break # Found and refreshed the relevant tab
        except Exception as e:
            logging.error(f"Error refreshing client tab after document assignment: {e}", exc_info=True)


    @pyqtSlot(str)
    def handle_add_client_from_stats_map(self, country_name_str):
        logging.info(f"Received request to add client for country: {country_name_str} from statistics map using new dialog.")        
        try:
            dialog = StatisticsAddClientDialog(initial_country_name=country_name_str, parent=self)

            if dialog.exec_() == QDialog.Accepted:
                new_client_data = dialog.get_data()
                logging.info(f"StatisticsAddClientDialog accepted. Data: {new_client_data}")

                if not new_client_data.get('country_id'):
                    QMessageBox.critical(self, self.tr("Erreur Pays"), self.tr("ID du pays non obtenu depuis le dialogue. Impossible de continuer."))
                    return

                client_data_for_db = {
                    "client_name": new_client_data["client_name"],
                    "company_name": new_client_data.get("company_name"),
                    "country_id": new_client_data["country_id"],
                    "city_id": new_client_data.get("city_id"),
                    "project_identifier": new_client_data.get("project_identifier"),
                    "primary_need_description": new_client_data.get("primary_need_description"),
                    "selected_languages": new_client_data.get("selected_languages"),
                    "created_by_user_id": self.current_user_id
                }

                logging.info(f"Proceeding to call handle_create_client_execution with data from new dialog: {client_data_for_db}")
                handle_create_client_execution(self, client_data_dict=client_data_for_db)
            else:
                logging.info("StatisticsAddClientDialog cancelled by user.")
        except Exception as e:
            logging.error(f"Error opening or executing StatisticsAddClientDialog for country {country_name_str}: {e}", exc_info=True)
            QMessageBox.critical(self,
                                 self.tr("Erreur Dialogue"),
                                 self.tr("Impossible d'ouvrir le dialogue 'Ajouter Client'. Veuillez consulter les logs de l'application pour plus de détails."))


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
        self.main_splitter = QSplitter(Qt.Horizontal, self.documents_page_widget) # Store as self.main_splitter

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

        # Country Filter
        country_filter_layout = QVBoxLayout()
        country_label = QLabel(self.tr("Pays:"))
        self.country_filter_combo = QComboBox()
        self.country_filter_combo.addItem(self.tr("Tous les pays"), None)
        self.load_countries_into_filter_combo() # Call to load countries
        self.country_filter_combo.currentIndexChanged.connect(self.filter_client_list_display_slot)
        country_filter_layout.addWidget(country_label)
        country_filter_layout.addWidget(self.country_filter_combo)
        filter_search_main_layout.addLayout(country_filter_layout)

        # Search Input
        search_layout = QVBoxLayout()
        self.search_label = QLabel(self.tr("Recherche:")) # Store label as instance member to toggle visibility
        self.search_label.setVisible(False) # Initially hidden
        search_layout.addWidget(self.search_label)

        search_bar_line_layout = QHBoxLayout()
        self.search_icon_btn = QPushButton()
        self.search_icon_btn.setIcon(QIcon.fromTheme("edit-find", QIcon(":/icons/search.svg"))) # Set icon
        # Removed setCheckable and setFixedWidth
        search_bar_line_layout.addWidget(self.search_icon_btn)

        self.search_input_field = QLineEdit(); self.search_input_field.setPlaceholderText(self.tr("Rechercher client..."))
        self.search_input_field.setVisible(False) # Initially hidden
        self.search_input_field.textChanged.connect(self.filter_client_list_display_slot)
        search_bar_line_layout.addWidget(self.search_input_field)

        search_layout.addLayout(search_bar_line_layout)
        filter_search_main_layout.addLayout(search_layout)

        self.search_icon_btn.clicked.connect(self.toggle_search_input_visibility) # Connect to clicked
        # Removed setVisible(True) for search_input_field and setChecked(True) for the button


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
        self.main_splitter.addWidget(left_pane_widget)

        # Right pane for client tabs (no change here, it's a QSplitter itself)
        right_pane_splitter = QSplitter(Qt.Vertical)
        self.client_tabs_widget = QTabWidget(); self.client_tabs_widget.setTabsClosable(True); self.client_tabs_widget.tabCloseRequested.connect(self.close_client_tab)
        right_pane_splitter.addWidget(self.client_tabs_widget)
        self.main_splitter.addWidget(right_pane_splitter)

        # Load or set default splitter sizes
        saved_splitter_state_hex = db_manager.get_setting('client_list_splitter_state', default_value=None)
        if saved_splitter_state_hex:
            try:
                splitter_state_byte_array = QByteArray.fromHex(saved_splitter_state_hex.encode('utf-8'))
                if not self.main_splitter.restoreState(splitter_state_byte_array):
                    logging.warning("Failed to restore splitter state, applying defaults.")
                    self.main_splitter.setSizes([int(self.width() * 0.20), int(self.width() * 0.80)])
                else:
                    logging.info("Client list splitter state restored.")
            except Exception as e:
                logging.error(f"Error restoring splitter state: {e}. Applying defaults.", exc_info=True)
                self.main_splitter.setSizes([int(self.width() * 0.20), int(self.width() * 0.80)])
        else:
            self.main_splitter.setSizes([int(self.width() * 0.20), int(self.width() * 0.80)])
            logging.info("Client list splitter: No saved state found, applied default sizes.")

        self.main_splitter.splitterMoved.connect(self.save_splitter_state)

        docs_page_layout = QVBoxLayout(self.documents_page_widget)
        docs_page_layout.addWidget(self.main_splitter) # Use self.main_splitter
        docs_page_layout.setContentsMargins(0,0,0,0)
        self.documents_page_widget.setLayout(docs_page_layout)

        self.main_area_stack.addWidget(self.documents_page_widget)

    def save_splitter_state(self, pos, index):
        """Saves the current state of the main_splitter."""
        try:
            splitter_state_byte_array = self.main_splitter.saveState()
            splitter_state_hex = splitter_state_byte_array.toHex().data().decode('utf-8')
            db_manager.set_setting('client_list_splitter_state', splitter_state_hex)
            logging.info(f"Client list splitter state saved (pos: {pos}, index: {index}).")
        except Exception as e:
            logging.error(f"Error saving splitter state: {e}", exc_info=True)

    def open_add_new_client_dialog(self):
        dialog = AddNewClientDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            client_data = dialog.get_data()
            if client_data: handle_create_client_execution(self, client_data_dict=client_data)

    def create_actions_main(self): 
        self.settings_action = QAction(QIcon(":/icons/modern/settings.svg"), self.tr("Paramètres"), self); self.settings_action.triggered.connect(self.show_settings_page) # Changed to show_settings_page
        self.template_action = QAction(QIcon(":/icons/modern/templates.svg"), self.tr("Gérer les Modèles"), self); self.template_action.triggered.connect(self.open_template_manager_dialog)
        self.status_action = QAction(QIcon(":/icons/check-square.svg"), self.tr("Gérer les Statuts"), self); self.status_action.triggered.connect(self.open_status_manager_dialog); self.status_action.setEnabled(False); self.status_action.setToolTip(self.tr("Fonctionnalité de gestion des statuts prévue pour une future version."))
        self.exit_action = QAction(QIcon(":/icons/log-out.svg"), self.tr("Quitter"), self); self.exit_action.setShortcut("Ctrl+Q"); self.exit_action.triggered.connect(self.close)
        self.project_management_action = QAction(QIcon(":/icons/dashboard.svg"), self.tr("Gestion de Projet"), self); self.project_management_action.triggered.connect(self.show_project_management_view)
        self.documents_view_action = QAction(QIcon(":/icons/modern/folder-docs.svg"), self.tr("Gestion Documents"), self); self.documents_view_action.triggered.connect(self.show_documents_view)
        self.product_list_action = QAction(QIcon(":/icons/book.svg"), self.tr("Product Management"), self); self.product_list_action.triggered.connect(self.show_product_management_page) # Connect to new method
        self.partner_management_action = QAction(QIcon(":/icons/team.svg"), self.tr("Partner Management"), self); self.partner_management_action.triggered.connect(self.show_partner_management_view)
        self.statistics_action = QAction(QIcon(":/icons/bar-chart.svg"), self.tr("Statistiques"), self); self.statistics_action.triggered.connect(self.show_statistics_view)
        self.open_carrier_map_action = QAction(QIcon(":/icons/map.svg"), self.tr("Carrier Map"), self) # Assuming map.svg or similar exists
        self.open_carrier_map_action.triggered.connect(self.open_carrier_map_dialog)
        self.botpress_integration_action = QAction(QIcon(":/icons/placeholder_icon.svg"), self.tr("Botpress Integration"), self) # Add a placeholder icon
        self.botpress_integration_action.triggered.connect(self.show_botpress_integration_view)
        self.inventory_browser_action = QAction(QIcon(":/icons/book.svg"), self.tr("Gestion Stock Atelier"), self) # Updated text

        self.inventory_browser_action.triggered.connect(self.show_inventory_browser_view)


    def create_menus_main(self): 
        menu_bar = self.menuBar(); file_menu = menu_bar.addMenu(self.tr("Fichier")); file_menu.addAction(self.settings_action); file_menu.addAction(self.template_action); file_menu.addAction(self.status_action); # file_menu.addAction(self.product_equivalency_action);
        file_menu.addSeparator(); file_menu.addAction(self.exit_action)

        modules_menu = menu_bar.addMenu(self.tr("Modules"))
        modules_menu.addAction(self.documents_view_action)
        modules_menu.addAction(self.project_management_action)
        modules_menu.addAction(self.product_list_action)
        modules_menu.addAction(self.partner_management_action)
        modules_menu.addAction(self.statistics_action)
        modules_menu.addAction(self.inventory_browser_action) # Add Inventory action
        modules_menu.addAction(self.botpress_integration_action) # Add Botpress action
        modules_menu.addSeparator() # Optional separator
        modules_menu.addAction(self.open_carrier_map_action)

        help_menu = menu_bar.addMenu(self.tr("Aide")); about_action = QAction(QIcon(":/icons/help-circle.svg"), self.tr("À propos"), self); about_action.triggered.connect(self.show_about_dialog); help_menu.addAction(about_action)

    def open_carrier_map_dialog(self):
        dialog = CarrierMapDialog(self)
        dialog.exec_()

    def show_project_management_view(self): self.main_area_stack.setCurrentWidget(self.project_management_widget_instance)
    def show_documents_view(self): self.main_area_stack.setCurrentWidget(self.documents_page_widget)
    def show_partner_management_view(self): self.main_area_stack.setCurrentWidget(self.partner_management_widget_instance)
    def show_statistics_view(self): self.main_area_stack.setCurrentWidget(self.statistics_dashboard_instance)
    def show_inventory_browser_view(self): self.main_area_stack.setCurrentWidget(self.inventory_browser_widget_instance)
    def show_botpress_integration_view(self): self.main_area_stack.setCurrentWidget(self.botpress_integration_ui_instance)

    def show_product_management_page(self):
        self.main_area_stack.setCurrentWidget(self.product_management_page_instance)

    def show_about_dialog(self): QMessageBox.about(self, self.tr("À propos"), self.tr("<b>Gestionnaire de Documents Client</b><br><br>Version 4.0<br>Application de gestion de documents clients avec templates Excel.<br><br>Développé par Saadiya Management (Concept)"))
        
    def execute_create_client_slot(self, client_data_dict=None):
        handle_create_client_execution(self, client_data_dict=client_data_dict)
        self.load_clients_from_db_slot()

    def load_clients_from_db_slot(self):
        status_id_filter = self.status_filter_combo.currentData()
        country_id_filter = self.country_filter_combo.currentData() # Get country filter
        archive_filter_data = self.client_archive_filter_combo.currentData()
        include_deleted_filter = False
        if archive_filter_data == "all_status_types": include_deleted_filter = True
        elif isinstance(archive_filter_data, bool): include_deleted_filter = archive_filter_data
        filters_for_crud = {};
        if status_id_filter is not None: filters_for_crud['status_id'] = status_id_filter
        if country_id_filter is not None: filters_for_crud['country_id'] = country_id_filter # Add to filters
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

    def toggle_search_input_visibility(self): # Renamed and removed 'checked' argument
        is_visible = not self.search_input_field.isVisible()
        self.search_input_field.setVisible(is_visible)
        self.search_label.setVisible(is_visible) # Toggle label visibility
        if is_visible:
            self.search_input_field.setFocus()
        # Removed button text change logic


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

    def load_countries_into_filter_combo(self):
        current_selection_data = self.country_filter_combo.currentData()
        self.country_filter_combo.clear()
        self.country_filter_combo.addItem(self.tr("Tous les pays"), None)
        try:
            countries = db_manager.get_all_countries() # Attempt to get countries
            if countries is None: countries = []
            for country_dict in countries:
                self.country_filter_combo.addItem(country_dict['country_name'], country_dict.get('country_id'))
            
            # Restore previous selection if possible
            index = self.country_filter_combo.findData(current_selection_data)
            if index != -1: self.country_filter_combo.setCurrentIndex(index)
            else: self.country_filter_combo.setCurrentIndex(0) # Default to "All countries"
        except AttributeError:
            logging.warning("db_manager.get_all_countries() function might not exist or returned an unexpected type. Country filter will be empty.")
            # Optionally, disable the combo box or show a message
            # self.country_filter_combo.setEnabled(False)
        except Exception as e:
            logging.error(self.tr("Erreur chargement pays pour filtre: {0}").format(str(e)))
            # self.country_filter_combo.setEnabled(False)

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

        logging.info(f"open_client_tab_by_id: client_id_to_open={client_id_to_open}, "
                     f"client_data_to_show name={client_data_to_show.get('client_name')}, "
                     f"email={client_data_to_show.get('email')}, phone={client_data_to_show.get('phone')}")

        # Ensure selected_languages is a list, even if it's null/empty from DB
        selected_languages_str = client_data_to_show.get('selected_languages')
        if isinstance(selected_languages_str, str) and selected_languages_str.strip():
            client_data_to_show['selected_languages'] = [lang.strip() for lang in selected_languages_str.split(',') if lang.strip()]
        elif not isinstance(client_data_to_show.get('selected_languages'), list): # If it's not a list already (e.g. None or empty string from .get())
            client_data_to_show['selected_languages'] = []


        for i in range(self.client_tabs_widget.count()):
            tab_widget_ref = self.client_tabs_widget.widget(i) 
            if hasattr(tab_widget_ref, 'client_info') and tab_widget_ref.client_info["client_id"] == client_id_to_open:
                logging.info(f"Refreshing existing tab for client ID {client_id_to_open}")
                self.client_tabs_widget.setCurrentIndex(i)
                if hasattr(tab_widget_ref, 'refresh_display'):
                    tab_widget_ref.refresh_display(client_data_to_show)
                return

        logging.info(f"Creating new tab for client ID {client_id_to_open}")
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

    def show_settings_page(self):
        self.main_area_stack.setCurrentWidget(self.settings_page_instance)
        # Ensure data is fresh when page is shown
        # SettingsPage's own _load_all_settings_from_config handles general/email tabs
        if hasattr(self.settings_page_instance, '_load_all_settings_from_config'):
            self.settings_page_instance._load_all_settings_from_config()
        # Transporters and Forwarders tabs load data from DB via their specific load methods
        if hasattr(self.settings_page_instance, '_load_transporters_table'):
            self.settings_page_instance._load_transporters_table()
        if hasattr(self.settings_page_instance, '_load_forwarders_table'):
            self.settings_page_instance._load_forwarders_table()
        # CompanyTabWidget loads its own data on init, but if a refresh is needed:
        if hasattr(self.settings_page_instance, 'company_tab') and \
           hasattr(self.settings_page_instance.company_tab, 'load_all_data'): # Assuming CompanyTabWidget has this
            self.settings_page_instance.company_tab.load_all_data()

        # After settings page is shown and potentially modified & saved by its own mechanism,
        # re-initialize the download monitor to reflect any changes.
        # This is a simplification; ideally, SettingsPage would emit a signal on save.
        self.init_or_update_download_monitor()

        logging.info("Switched to Settings Page and refreshed its data. Download monitor re-initialized.")
            
    def open_template_manager_dialog(self): TemplateDialog(self.config, self).exec_()
    def open_status_manager_dialog(self): QMessageBox.information(self, self.tr("Gestion des Statuts"), self.tr("Fonctionnalité à implémenter."))
    # def open_product_list_placeholder(self): ProductListDialog(self).exec_() # Removed
    def closeEvent(self, event):
        logging.info("Close event triggered. Stopping services and saving config.")
        if self.download_monitor_service:
            logging.info("Stopping download monitor service due to application close.")
            self.download_monitor_service.stop()
        save_config(self.config) # Ensure config is saved
        super().closeEvent(event)

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
