# -*- coding: utf-8 -*-
import sys # Used by __init__ indirectly via app_root_dir logic if it were here, but app_root_dir is imported
import os # Used by open_settings_dialog for makedirs

# PyQt5 imports used directly by DocumentManager UI and methods
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, # Added QApplication
    QPushButton, QLabel, QLineEdit, # QTextEdit (used by client_notes_edit indirectly via ClientWidget or dialogs)
    QListWidget, QListWidgetItem, # QListWidgetItem for add_client_to_list_widget
    QFileDialog, QMessageBox, QDialog, QFormLayout, QComboBox, # QDialog for dialog inheritance
    QInputDialog, QCompleter, QTabWidget, QAction, QMenu, QGroupBox, QProgressDialog, # Added QProgressDialog
    QStackedWidget, QDoubleSpinBox # QDoubleSpinBox for final_price_input
)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont
from PyQt5.QtCore import Qt, QUrl, QTimer

# Project-specific imports
import db as db_manager
import icons_rc # Import the compiled resources for icons
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
# Dialogs directly instantiated by DocumentManager
from dialogs import (
    SettingsDialog, TemplateDialog, AddNewClientDialog, # EditClientDialog is called from logic
    ProductEquivalencyDialog, # Added for product equivalency
    ManageProductMasterDialog # Added for global product management
)
from client_widget import ClientWidget # For client tabs
from projectManagement import MainDashboard as ProjectManagementDashboard # For PM tab
from statistics_module import StatisticsDashboard
from utils import save_config # For saving config in settings and closeEvent


class DocumentManager(QMainWindow):
    def __init__(self, app_root_dir): # app_root_dir is passed
        super().__init__()
        self.app_root_dir = app_root_dir # Store it
        self.setWindowTitle(self.tr("Gestionnaire de Documents Client")); self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon.fromTheme("folder-documents"))
        
        self.config = CONFIG 
        self.clients_data_map = {} 
        
        self.setup_ui_main() 

        self.project_management_widget_instance = ProjectManagementDashboard(parent=self, current_user=None)
        self.main_area_stack.addWidget(self.project_management_widget_instance)

        self.statistics_dashboard_instance = StatisticsDashboard(parent=self)
        self.main_area_stack.addWidget(self.statistics_dashboard_instance)

        self.main_area_stack.setCurrentWidget(self.documents_page_widget)

        self.create_actions_main() 
        self.create_menus_main() 

        # Set initial checked state for the default view action
        self.documents_view_action.setChecked(True)
        # Explicitly uncheck others, though default for checkable is false
        self.project_management_action.setChecked(False)
        self.statistics_action.setChecked(False)
        
        # Calls to refactored logic functions
        progress_dialog = QProgressDialog(self.tr("Chargement des clients..."), None, 0, 0, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setMinimumDuration(100) # Only show if loading takes > 100ms
        progress_dialog.setValue(0)

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            load_and_display_clients(self)
        finally:
            QApplication.restoreOverrideCursor()
            progress_dialog.close() # Ensure it's closed

        if self.stats_widget: # Ensure stats_widget is initialized
            self.stats_widget.update_stats() 
        
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_old_clients_routine_slot) # Slot for timer
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
        self.search_input_field = QLineEdit(); self.search_input_field.setPlaceholderText(self.tr("Rechercher client..."))
        self.search_input_field.textChanged.connect(self.filter_client_list_display_slot) 
        filter_search_layout.addWidget(self.search_input_field); left_layout.addLayout(filter_search_layout)
        
        self.client_list_widget = QListWidget(); self.client_list_widget.setAlternatingRowColors(True) 
        self.client_list_widget.setItemDelegate(StatusDelegate(self.client_list_widget))
        self.client_list_widget.itemClicked.connect(self.handle_client_list_click) 
        self.client_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.client_list_widget.customContextMenuRequested.connect(self.show_client_context_menu)
        left_layout.addWidget(self.client_list_widget)
        
        # Removed form_group_box and its contents from here.
        # Add a button to open the AddNewClientDialog
        self.add_new_client_button = QPushButton(self.tr("Ajouter un Nouveau Client"))
        self.add_new_client_button.setIcon(QIcon(":/icons/modern/user-add.svg")) # Conceptual: person outline with plus
        self.add_new_client_button.setObjectName("primaryButton")
        self.add_new_client_button.clicked.connect(self.open_add_new_client_dialog)
        left_layout.addWidget(self.add_new_client_button)

        content_layout.addWidget(left_panel, 1)
        
        self.client_tabs_widget = QTabWidget(); self.client_tabs_widget.setTabsClosable(True) 
        self.client_tabs_widget.tabCloseRequested.connect(self.close_client_tab) 
        content_layout.addWidget(self.client_tabs_widget, 2)

        self.main_area_stack.addWidget(self.documents_page_widget)
        # self.load_countries_into_combo() # This is now part of AddNewClientDialog
        
    def open_add_new_client_dialog(self):
        dialog = AddNewClientDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            client_data = dialog.get_data()
            if client_data:
                # Pass data to the existing logic handler
                handle_create_client_execution(self, client_data_dict=client_data)

    def create_actions_main(self): 
        self.settings_action = QAction(QIcon(":/icons/modern/settings.svg"), self.tr("Paramètres"), self); self.settings_action.triggered.connect(self.open_settings_dialog) # Conceptual: modern gear
        self.template_action = QAction(QIcon(":/icons/modern/templates.svg"), self.tr("Gérer les Modèles"), self); self.template_action.triggered.connect(self.open_template_manager_dialog) # Conceptual: stylized page with corner fold
        self.status_action = QAction(self.tr("Gérer les Statuts"), self); self.status_action.triggered.connect(self.open_status_manager_dialog) # No icon specified, can add one e.g. :/icons/modern/list-check.svg
        self.status_action.setEnabled(False)
        self.status_action.setToolTip(self.tr("Fonctionnalité de gestion des statuts prévue pour une future version."))
        self.exit_action = QAction(self.tr("Quitter"), self); self.exit_action.setShortcut("Ctrl+Q"); self.exit_action.triggered.connect(self.close) # No icon specified, can add one e.g. :/icons/modern/power.svg
        self.project_management_action = QAction(QIcon(":/icons/modern/dashboard.svg"), self.tr("Gestion de Projet"), self) # Conceptual: modern dashboard/kanban
        self.project_management_action.setCheckable(True)
        self.project_management_action.triggered.connect(self.show_project_management_view)
        self.documents_view_action = QAction(QIcon(":/icons/modern/folder-docs.svg"), self.tr("Gestion Documents"), self) # Conceptual: clean folder with document symbol
        self.documents_view_action.setCheckable(True)
        self.documents_view_action.triggered.connect(self.show_documents_view)
        
        self.statistics_action = QAction(QIcon(":/icons/bar-chart.svg"), self.tr("Statistiques Détaillées"), self)

        self.statistics_action.setCheckable(True)
        self.statistics_action.triggered.connect(self.show_statistics_view)

        self.product_equivalency_action = QAction(QIcon.fromTheme("document-properties", QIcon(":/icons/modern/link.svg")), self.tr("Gérer Équivalences Produits"), self)
        self.product_equivalency_action.triggered.connect(self.open_product_equivalency_dialog)

        self.manage_products_action = QAction(QIcon(":/icons/briefcase.svg"), self.tr("Gérer Produits Globaux"), self)
        self.manage_products_action.triggered.connect(self.open_manage_products_dialog)

    def create_menus_main(self): 
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu(self.tr("Fichier"))
        file_menu.addAction(self.settings_action); file_menu.addAction(self.template_action); file_menu.addAction(self.status_action)
        file_menu.addAction(self.product_equivalency_action)
        file_menu.addAction(self.manage_products_action) # Add the new action for products
        file_menu.addSeparator(); file_menu.addAction(self.exit_action)
        modules_menu = menu_bar.addMenu(self.tr("Modules"))
        modules_menu.addAction(self.documents_view_action)
        modules_menu.addAction(self.project_management_action)
        modules_menu.addAction(self.statistics_action)
        help_menu = menu_bar.addMenu(self.tr("Aide"))
        about_action = QAction(self.tr("À propos"), self); about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_project_management_view(self):
        self.main_area_stack.setCurrentWidget(self.project_management_widget_instance)
        self.project_management_action.setChecked(True)
        self.documents_view_action.setChecked(False)
        self.statistics_action.setChecked(False)

    def show_documents_view(self):
        self.main_area_stack.setCurrentWidget(self.documents_page_widget)
        self.documents_view_action.setChecked(True)
        self.project_management_action.setChecked(False)
        self.statistics_action.setChecked(False)
        
    def show_statistics_view(self):
        self.main_area_stack.setCurrentWidget(self.statistics_dashboard_instance)

        self.statistics_action.setChecked(True)
        self.documents_view_action.setChecked(False)
        self.project_management_action.setChecked(False)

    def show_about_dialog(self): 
        QMessageBox.about(self, self.tr("À propos"), self.tr("<b>Gestionnaire de Documents Client</b><br><br>Version 4.0<br>Application de gestion de documents clients avec templates Excel.<br><br>Développé par Saadiya Management (Concept)"))
        
    # Removed load_countries_into_combo, load_cities_for_country,
    # add_new_country_dialog, add_new_city_dialog as they are now in AddNewClientDialog.
                
    # Slots for refactored logic
    # Modified execute_create_client_slot to accept data if needed, or it will be handled by the logic function itself.
    def execute_create_client_slot(self, client_data_dict=None): # client_data_dict can be passed if needed by future refactors
        handle_create_client_execution(self, client_data_dict=client_data_dict) # Pass it to the handler

    def load_clients_from_db_slot(self): load_and_display_clients(self) # Renamed for clarity if used as slot
    def filter_client_list_display_slot(self): filter_and_display_clients(self) # Renamed
    def check_old_clients_routine_slot(self): perform_old_clients_check(self) # Renamed
    def open_edit_client_dialog_slot(self, client_id): handle_open_edit_client_dialog(self, client_id) # Renamed
    def set_client_status_archived_slot(self, client_id): archive_client_status(self, client_id) # Renamed
    def delete_client_permanently_slot(self, client_id): permanently_delete_client(self, client_id) # Renamed

    # Original methods calling the slots (if needed, or connect directly to slots)
    # These are now just wrappers if the signals are connected to these methods.
    # It's often cleaner to connect signals directly to the _slot methods if they are purely for that.
    def execute_create_client(self, client_data_dict=None): self.execute_create_client_slot(client_data_dict=client_data_dict) # Ensure it can take arg
    def load_clients_from_db(self): self.load_clients_from_db_slot()
    def filter_client_list_display(self): self.filter_client_list_display_slot()
    def check_old_clients_routine(self): self.check_old_clients_routine_slot()
    def open_edit_client_dialog(self, client_id): self.open_edit_client_dialog_slot(client_id)
    def set_client_status_archived(self, client_id): self.set_client_status_archived_slot(client_id)
    def delete_client_permanently(self, client_id): self.delete_client_permanently_slot(client_id)

    def add_client_to_list_widget(self, client_dict_data): 
        item = QListWidgetItem(client_dict_data["client_name"])
        item.setData(Qt.UserRole, client_dict_data.get("status", "N/A"))
        item.setData(Qt.UserRole + 1, client_dict_data["client_id"]) 
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
            print(self.tr("Erreur chargement statuts pour filtre: {0}").format(str(e))) # Should use logging
            
    def handle_client_list_click(self, item): 
        client_id_val = item.data(Qt.UserRole + 1) 
        if client_id_val: self.open_client_tab_by_id(client_id_val)
        
    def open_client_tab_by_id(self, client_id_to_open): 
        client_data_to_show = self.clients_data_map.get(client_id_to_open) 
        if not client_data_to_show: return
        for i in range(self.client_tabs_widget.count()):
            tab_widget_ref = self.client_tabs_widget.widget(i) 
            if hasattr(tab_widget_ref, 'client_info') and tab_widget_ref.client_info["client_id"] == client_id_to_open:
                self.client_tabs_widget.setCurrentIndex(i); return
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
        client_id_val = list_item.data(Qt.UserRole + 1) 
        menu = QMenu()
        open_action = menu.addAction(self.tr("Ouvrir Fiche Client")); open_action.triggered.connect(lambda: self.open_client_tab_by_id(client_id_val))
        # Connect context menu actions to SLOTS or directly to logic handlers if appropriate
        edit_action = menu.addAction(self.tr("Modifier Client")); edit_action.triggered.connect(lambda: self.open_edit_client_dialog_slot(client_id_val))
        open_folder_action = menu.addAction(self.tr("Ouvrir Dossier Client")); open_folder_action.triggered.connect(lambda: self.open_client_folder_fs(client_id_val))
        menu.addSeparator()
        archive_action = menu.addAction(self.tr("Archiver Client")); archive_action.triggered.connect(lambda: self.set_client_status_archived_slot(client_id_val))
        delete_action = menu.addAction(self.tr("Supprimer Client")); delete_action.triggered.connect(lambda: self.delete_client_permanently_slot(client_id_val))
        menu.exec_(self.client_list_widget.mapToGlobal(pos))
        
    def open_client_folder_fs(self, client_id_val): 
        if client_id_val in self.clients_data_map:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.clients_data_map[client_id_val]["base_folder_path"]))
            
    def open_settings_dialog(self): 
        dialog = SettingsDialog(self.config, self) # Pass self as parent
        if dialog.exec_() == QDialog.Accepted:
            new_conf = dialog.get_config() 
            self.config.update(new_conf) # self.config should be CONFIG from app_setup
            save_config(self.config) # save_config from utils
            os.makedirs(self.config["templates_dir"], exist_ok=True) 
            os.makedirs(self.config["clients_dir"], exist_ok=True)
            QMessageBox.information(self, self.tr("Paramètres Sauvegardés"), self.tr("Nouveaux paramètres enregistrés.")) # self for parent
            
    def open_template_manager_dialog(self): TemplateDialog(self.config, self).exec_() # Pass self as parent
        
    def open_status_manager_dialog(self): 
        QMessageBox.information(self, self.tr("Gestion des Statuts"), self.tr("Fonctionnalité de gestion des statuts personnalisés à implémenter."))
            
    def open_product_equivalency_dialog(self):
        dialog = ProductEquivalencyDialog(self) # Pass self as parent
        dialog.exec_()

    def open_manage_products_dialog(self):
        dialog = ManageProductMasterDialog(self.app_root_dir, self) # Pass app_root_dir and self as parent
        dialog.exec_()

    def closeEvent(self, event): 
        save_config(self.config) # save_config from utils, self.config is CONFIG
        super().closeEvent(event)

# If main() and other app setup logic is moved to main.py, this file should only contain DocumentManager
# and its necessary imports.
